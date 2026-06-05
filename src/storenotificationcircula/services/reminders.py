from __future__ import annotations

import os
import re
from datetime import date, datetime, timedelta
from typing import Any

from dotenv import load_dotenv

from storenotificationcircula.services.ack import app_base_url
from storenotificationcircula.db.database import get_conn
from storenotificationcircula.services.email.sender import send_email
from storenotificationcircula.services.email.settings import default_contact_emails, get_setting

load_dotenv()

EMAIL_PATTERN = re.compile(r"[^@\s,;，；]+@[^@\s,;，；]+\.[^@\s,;，；]+")


def _secret(key: str, default: str = "") -> str:
    return os.getenv(key, default)


def _reminder_days() -> set[int]:
    return _parse_days(_setting("notification_reminder_days", _secret("REMINDER_DAYS", "7")))


def _plan_reminder_days() -> set[int]:
    return _parse_days(_setting("plan_reminder_days", "7"))


def _parse_days(raw: str) -> set[int]:
    days: set[int] = set()
    for part in str(raw or "").replace("，", ",").split(","):
        part = part.strip()
        if not part:
            continue
        try:
            days.add(int(part))
        except ValueError:
            continue
    return days or {7}


def _setting(key: str, default: str = "") -> str:
    return get_setting(key, default)


def _row_reminder_days(row: dict[str, Any], default_days: set[int]) -> set[int]:
    raw = row.get("reminder_days")
    return _parse_days(raw) if raw else default_days


def _split_emails(raw: str) -> list[str]:
    return sorted({match.group(0).lower() for match in EMAIL_PATTERN.finditer(raw or "")})


def _notification_link(notification_id: str) -> str:
    return f"{app_base_url()}/app?notification_id={notification_id}"


def _already_logged(conn, notification_id: str, reminder_type: str, reminder_date: str, recipient_email: str) -> bool:
    row = conn.execute(
        """
        SELECT id
        FROM reminder_log
        WHERE notification_id = ?
          AND reminder_type = ?
          AND reminder_date = ?
          AND COALESCE(recipient_email, '') = ?
        LIMIT 1
        """,
        (notification_id, reminder_type, reminder_date, recipient_email or ""),
    ).fetchone()
    return bool(row)


def _log_reminder(
    conn,
    notification_id: str,
    reminder_type: str,
    reminder_date: str,
    recipient_email: str,
    status: str,
    error: str = "",
) -> None:
    conn.execute(
        """
        INSERT INTO reminder_log
            (notification_id, reminder_type, reminder_date, recipient_email, status, error, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            notification_id,
            reminder_type,
            reminder_date,
            recipient_email,
            status,
            error,
            datetime.now().isoformat(),
        ),
    )


def _notice_title(row: dict[str, Any]) -> str:
    return row.get("title") or row.get("system_no") or row.get("doc_ref") or "通告"


def _target_recipients(conn, row: dict[str, Any]) -> list[str]:
    ack_rows = conn.execute(
        """
        SELECT email
        FROM ack_recipients
        WHERE notification_id = ? AND confirmed_at IS NULL
        """,
        (row["notification_id"],),
    ).fetchall()
    emails = {ack["email"].strip().lower() for ack in ack_rows if ack["email"]}
    emails.update(_split_emails(row.get("owner") or ""))
    emails.update(_split_emails(row.get("issuer") or ""))
    return sorted(emails) or default_contact_emails()


def _escalation_recipients() -> list[str]:
    return _split_emails(_secret("ESCALATION_EMAILS", ""))


def _send_or_log(
    conn,
    row: dict[str, Any],
    recipient: str,
    reminder_type: str,
    subject: str,
    body: str,
) -> tuple[int, int]:
    today_key = date.today().isoformat()
    if _already_logged(conn, row["notification_id"], reminder_type, today_key, recipient):
        return 0, 0
    try:
        send_email(recipient, subject, body)
    except Exception as exc:
        _log_reminder(conn, row["notification_id"], reminder_type, today_key, recipient, "失败", str(exc))
        return 0, 1
    _log_reminder(conn, row["notification_id"], reminder_type, today_key, recipient, "成功")
    return 1, 0


def _plan_link(plan_id: int) -> str:
    return f"{app_base_url()}/app?plan_id={plan_id}"


def _plan_recipients(row: dict[str, Any]) -> list[str]:
    recipients = set(_split_emails(row.get("reminder_email") or ""))
    recipients.update(_split_emails(row.get("owner") or ""))
    recipients.update(_escalation_recipients())
    return sorted(recipients) or default_contact_emails()


def _send_plan_reminder(
    recipients: list[str],
    subject: str,
    body: str,
    send_emails: bool,
) -> tuple[int, int, int]:
    if not recipients:
        return 0, 0, 1
    if not send_emails:
        return 0, 0, len(recipients)

    sent = failed = 0
    for recipient in recipients:
        try:
            send_email(recipient, subject, body)
        except Exception:
            failed += 1
        else:
            sent += 1
    return sent, failed, 0


def process_plan_reminders(send_emails: bool = True, plan_id: int | None = None) -> dict[str, int]:
    """Send pre-registration reminders for editing and publishing notices."""
    stats = {
        "checked": 0,
        "sent": 0,
        "failed": 0,
        "skipped": 0,
        "marked_overdue": 0,
    }
    today = date.today()

    with get_conn() as conn:
        sql = """
            SELECT *
            FROM plans
            WHERE status IN ('已预录', '已编写')
              AND COALESCE(reminder_enabled, 1) = 1
        """
        params: list[Any] = []
        if plan_id is not None:
            sql += " AND id = ?"
            params.append(plan_id)
        sql += " ORDER BY planned_publish_date IS NULL, planned_publish_date"
        rows = conn.execute(sql, params).fetchall()

        for raw_row in rows:
            row = dict(raw_row)
            stats["checked"] += 1
            plan_days = max(_row_reminder_days(row, _plan_reminder_days()))
            publish_reminder_date = row.get("publish_reminder_date")
            if not publish_reminder_date and row.get("planned_publish_date"):
                try:
                    publish_reminder_date = (date.fromisoformat(str(row["planned_publish_date"])[:10]) - timedelta(days=plan_days)).isoformat()
                except ValueError:
                    publish_reminder_date = ""
            reminders = [
                ("remind_7d_sent", "预录DDL提醒", publish_reminder_date, "记得编写通告/发布通告"),
            ]
            for flag_column, reminder_type, reminder_date, action_text in reminders:
                if row.get(flag_column):
                    continue
                if not reminder_date:
                    stats["skipped"] += 1
                    continue
                try:
                    due_date = date.fromisoformat(str(reminder_date)[:10])
                except ValueError:
                    stats["skipped"] += 1
                    continue
                if due_date > today:
                    continue

                title = row.get("activity_name") or "预录备忘"
                recipients = _plan_recipients(row)
                subject = f"[预录备忘] {reminder_type}：{title}"
                body = (
                    f"{action_text}。\n\n"
                    f"活动/通告：{title}\n"
                    f"DDL：{row.get('planned_publish_date') or '未设置'}\n"
                    f"负责人：{row.get('owner') or '未填'}\n"
                    f"查看链接：{_plan_link(row['id'])}\n"
                )
                sent, failed, skipped = _send_plan_reminder(recipients, subject, body, send_emails)
                stats["sent"] += sent
                stats["failed"] += failed
                stats["skipped"] += skipped
                if sent > 0:
                    conn.execute(
                        f"UPDATE plans SET {flag_column} = 1, updated_at = ? WHERE id = ?",
                        (datetime.now().isoformat(), row["id"]),
                    )

    return stats


def process_deadline_reminders(send_emails: bool = True, notification_id: str | None = None) -> dict[str, int]:
    """Scan deadlines, send due reminders, mark overdue, and log actions.

    This function is intentionally idempotent per day/type/recipient through reminder_log.
    It can run on page load or from Windows Task Scheduler.
    """
    stats = {
        "checked": 0,
        "sent": 0,
        "failed": 0,
        "skipped": 0,
        "marked_overdue": 0,
    }
    today = date.today()
    reminder_days = _reminder_days()

    with get_conn() as conn:
        sql = """
            SELECT *
            FROM notifications
            WHERE status IN ('执行中', '已回执')
              AND COALESCE(deadline, effective_end) IS NOT NULL
        """
        params: list[str] = []
        if notification_id:
            sql += " AND notification_id = ?"
            params.append(notification_id)
        rows = conn.execute(sql, params).fetchall()

        for raw_row in rows:
            row = dict(raw_row)
            stats["checked"] += 1
            try:
                deadline = date.fromisoformat(str(row.get("deadline") or row.get("effective_end"))[:10])
            except ValueError:
                stats["skipped"] += 1
                continue

            days_left = (deadline - today).days
            title = _notice_title(row)
            link = _notification_link(row["notification_id"])
            recipients = _target_recipients(conn, row)

            reminder_days = _row_reminder_days(row, _reminder_days())
            if days_left < 0:
                reminder_type = "逾期升级"
                recipients = sorted(set(recipients + _escalation_recipients()))
                subject = f"[逾期升级] {title}"
                body = (
                    f"以下通告已逾期，请尽快处理：\n\n"
                    f"通告：{title}\n"
                    f"通告编号：{row.get('system_no') or '未编号'}\n"
                    f"截止日期：{deadline.isoformat()}\n"
                    f"负责人：{row.get('owner') or '未填'}\n"
                    f"查看链接：{link}\n"
                )
            elif days_left == 0:
                reminder_type = "截止当日提醒"
                recipients = sorted(set(recipients + _escalation_recipients()))
                subject = f"[截止当日提醒] {title}"
                body = (
                    f"以下通告今天截止，请确认执行/回执状态：\n\n"
                    f"通告：{title}\n"
                    f"通告编号：{row.get('system_no') or '未编号'}\n"
                    f"负责人：{row.get('owner') or '未填'}\n"
                    f"查看链接：{link}\n"
                )
            elif days_left in reminder_days:
                reminder_type = f"提前 {days_left} 天提醒"
                recipients = sorted(set(recipients + _escalation_recipients()))
                subject = f"[提前 {days_left} 天截止提醒] {title}"
                body = (
                    f"以下通告将在 {days_left} 天后截止：\n\n"
                    f"通告：{title}\n"
                    f"通告编号：{row.get('system_no') or '未编号'}\n"
                    f"截止日期：{deadline.isoformat()}\n"
                    f"负责人：{row.get('owner') or '未填'}\n"
                    f"查看链接：{link}\n"
                )
            else:
                continue

            if not recipients:
                if not _already_logged(conn, row["notification_id"], reminder_type, today.isoformat(), ""):
                    _log_reminder(conn, row["notification_id"], reminder_type, today.isoformat(), "", "跳过", "无可发送邮箱")
                stats["skipped"] += 1
                continue

            if not send_emails:
                stats["skipped"] += len(recipients)
                continue

            for recipient in recipients:
                sent, failed = _send_or_log(conn, row, recipient, reminder_type, subject, body)
                stats["sent"] += sent
                stats["failed"] += failed

    return stats
