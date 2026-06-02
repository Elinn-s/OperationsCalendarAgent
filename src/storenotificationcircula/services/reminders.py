from __future__ import annotations

import os
import re
from datetime import date, datetime, timedelta
from typing import Any

from dotenv import load_dotenv

from storenotificationcircula.services.ack import app_base_url
from storenotificationcircula.db.database import get_conn
from storenotificationcircula.services.notifier import send_email

load_dotenv()

EMAIL_PATTERN = re.compile(r"[^@\s,;，；]+@[^@\s,;，；]+\.[^@\s,;，；]+")


def _secret(key: str, default: str = "") -> str:
    value = os.getenv(key, default)
    if value:
        return value
    try:
        import streamlit as st

        return st.secrets.get(key, default)
    except Exception:
        return default


def _reminder_days() -> set[int]:
    raw = _secret("REMINDER_DAYS", "7")
    days: set[int] = set()
    for part in raw.replace("，", ",").split(","):
        part = part.strip()
        if not part:
            continue
        try:
            days.add(int(part))
        except ValueError:
            continue
    return days or {7}


def _split_emails(raw: str) -> list[str]:
    return sorted({match.group(0).lower() for match in EMAIL_PATTERN.finditer(raw or "")})


def _notification_link(notification_id: str) -> str:
    return f"{app_base_url()}/Import_Notification?history_id={notification_id}"


def _already_logged(conn, notification_id: str, reminder_type: str, reminder_date: str, recipient_email: str) -> bool:
    if reminder_type == "提前一周提醒":
        row = conn.execute(
            """
            SELECT id
            FROM reminder_log
            WHERE notification_id = ?
              AND reminder_type = ?
              AND COALESCE(recipient_email, '') = ?
            LIMIT 1
            """,
            (notification_id, reminder_type, recipient_email or ""),
        ).fetchone()
        return bool(row)

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
    return sorted(emails)


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
    return sorted(recipients)


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
            publish_reminder_date = row.get("publish_reminder_date")
            if not publish_reminder_date and row.get("planned_publish_date"):
                try:
                    publish_reminder_date = (date.fromisoformat(str(row["planned_publish_date"])[:10]) - timedelta(days=7)).isoformat()
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
            WHERE status IN ('执行中', '已回执', '已逾期')
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

            if days_left < 0:
                if row.get("status") != "已逾期":
                    conn.execute(
                        "UPDATE notifications SET status = '已逾期', updated_at = ? WHERE notification_id = ?",
                        (datetime.now().isoformat(), row["notification_id"]),
                    )
                    conn.execute(
                        """
                        INSERT INTO audit_log (notification_id, action, detail, actor, timestamp)
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        (
                            row["notification_id"],
                            "自动标记逾期",
                            f"截止日期 {deadline.isoformat()} 已过期",
                            "系统",
                            datetime.now().isoformat(),
                        ),
                    )
                    stats["marked_overdue"] += 1
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
            elif 0 < days_left <= max(reminder_days):
                reminder_type = "提前一周提醒"
                recipients = sorted(set(recipients + _escalation_recipients()))
                subject = f"[提前一周截止提醒] {title}"
                body = (
                    f"以下通告将在一周内截止（剩余 {days_left} 天）：\n\n"
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
