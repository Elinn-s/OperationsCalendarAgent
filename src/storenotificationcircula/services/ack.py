from __future__ import annotations

import csv
import os
import re
import uuid
from datetime import datetime
from io import StringIO
from typing import Any

from dotenv import load_dotenv

from storenotificationcircula.db.database import get_conn
from storenotificationcircula.services.notifier import send_email

load_dotenv()

EMAIL_PATTERN = re.compile(r"[^@\s,;，；]+@[^@\s,;，；]+\.[^@\s,;，；]+")


def _secret(key: str, default: str = "") -> str:
    return os.getenv(key, default)


def app_base_url() -> str:
    return _secret("APP_BASE_URL", "http://localhost:8000").rstrip("/")


def build_ack_link(token: str) -> str:
    return f"{app_base_url()}/app?ack_token={token}"


def parse_recipients(raw_text: str) -> list[dict[str, str]]:
    """Parse lines like 部门,姓名,email or 姓名,email or email."""
    recipients: list[dict[str, str]] = []
    for raw_line in raw_text.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        email_match = EMAIL_PATTERN.search(line)
        if not email_match:
            continue
        email = email_match.group(0).strip()

        normalized = line.replace("，", ",").replace("；", ",").replace(";", ",")
        try:
            parts = next(csv.reader(StringIO(normalized)))
        except Exception:
            parts = [part.strip() for part in normalized.split(",")]
        parts = [part.strip() for part in parts if part.strip() and part.strip() != email]

        department = ""
        recipient_name = ""
        if len(parts) >= 2:
            department, recipient_name = parts[0], parts[1]
        elif len(parts) == 1:
            recipient_name = parts[0]

        recipients.append(
            {
                "department": department,
                "recipient_name": recipient_name,
                "email": email,
            }
        )
    return recipients


def add_ack_recipients(notification_id: str, recipients: list[dict[str, str]]) -> int:
    now = datetime.now().isoformat()
    inserted = 0
    with get_conn() as conn:
        existing = conn.execute(
            "SELECT email FROM ack_recipients WHERE notification_id = ?",
            (notification_id,),
        ).fetchall()
        existing_emails = {row["email"].lower() for row in existing}
        for recipient in recipients:
            email = recipient["email"].strip().lower()
            if not email or email in existing_emails:
                continue
            conn.execute(
                """
                INSERT INTO ack_recipients
                    (notification_id, department, recipient_name, email, token, status, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, '未发送', ?, ?)
                """,
                (
                    notification_id,
                    recipient.get("department", "").strip(),
                    recipient.get("recipient_name", "").strip(),
                    email,
                    uuid.uuid4().hex,
                    now,
                    now,
                ),
            )
            existing_emails.add(email)
            inserted += 1
    return inserted


def get_ack_recipients(notification_id: str) -> list[dict[str, Any]]:
    with get_conn() as conn:
        return conn.execute(
            """
            SELECT *
            FROM ack_recipients
            WHERE notification_id = ?
            ORDER BY created_at, id
            """,
            (notification_id,),
        ).fetchall()


def ack_summary(notification_id: str) -> dict[str, int]:
    rows = get_ack_recipients(notification_id)
    total = len(rows)
    confirmed = sum(1 for row in rows if row["confirmed_at"])
    sent = sum(1 for row in rows if row["sent_at"])
    return {"total": total, "sent": sent, "confirmed": confirmed}


def delete_ack_recipient(recipient_id: int) -> None:
    with get_conn() as conn:
        conn.execute("DELETE FROM ack_recipients WHERE id = ?", (recipient_id,))


def get_ack_by_token(token: str) -> dict[str, Any] | None:
    with get_conn() as conn:
        return conn.execute(
            """
            SELECT ar.*, n.title, n.system_no, n.deadline, n.effective_end
            FROM ack_recipients ar
            LEFT JOIN notifications n ON n.notification_id = ar.notification_id
            WHERE ar.token = ?
            """,
            (token,),
        ).fetchone()


def confirm_ack_token(token: str) -> tuple[str, dict[str, Any] | None]:
    now = datetime.now().isoformat()
    with get_conn() as conn:
        row = conn.execute(
            """
            SELECT ar.*, n.title, n.system_no, n.deadline, n.effective_end
            FROM ack_recipients ar
            LEFT JOIN notifications n ON n.notification_id = ar.notification_id
            WHERE ar.token = ?
            """,
            (token,),
        ).fetchone()
        if not row:
            return "not_found", None
        if row["confirmed_at"]:
            return "already_confirmed", row
        conn.execute(
            """
            UPDATE ack_recipients
            SET status = '已回执', confirmed_at = ?, updated_at = ?
            WHERE token = ?
            """,
            (now, now, token),
        )
        conn.execute(
            """
            INSERT INTO audit_log (notification_id, action, detail, actor, timestamp)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                row["notification_id"],
                "确认回执",
                f"{row['department'] or '未填部门'} / {row['recipient_name'] or row['email']}",
                row["email"],
                now,
            ),
        )
        remaining = conn.execute(
            """
            SELECT COUNT(*) AS pending_count
            FROM ack_recipients
            WHERE notification_id = ? AND confirmed_at IS NULL
            """,
            (row["notification_id"],),
        ).fetchone()
        if remaining and int(remaining["pending_count"] or 0) == 0:
            conn.execute(
                """
                UPDATE notifications
                SET status = '已回执', updated_at = ?
                WHERE notification_id = ? AND status IN ('执行中')
                """,
                (now, row["notification_id"]),
            )
        updated = dict(row)
        updated["confirmed_at"] = now
        updated["status"] = "已回执"
        return "confirmed", updated


def _log_email(
    notification_id: str,
    ack_recipient_id: int,
    recipient_email: str,
    subject: str,
    status: str,
    error: str = "",
) -> None:
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO email_log
                (notification_id, ack_recipient_id, recipient_email, subject, status, error, sent_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                notification_id,
                ack_recipient_id,
                recipient_email,
                subject,
                status,
                error,
                datetime.now().isoformat(),
            ),
        )


def send_ack_email(notification: dict[str, Any], recipient: dict[str, Any]) -> tuple[bool, str]:
    title = notification["title"] or notification["system_no"] or "通告"
    subject = f"请确认回执：{title}"
    link = build_ack_link(recipient["token"])
    body = f"""您好，

请确认已收到并知悉以下通告：

通告标题：{title}
通告编号：{notification["system_no"] or "未编号"}
截止日期：{notification.get("deadline") or notification["effective_end"] or "无截止日期"}

请点击以下链接完成回执：
{link}

如已完成回执，请忽略重复提醒。
"""
    try:
        send_email(recipient["email"], subject, body)
    except Exception as exc:
        error = str(exc)
        _log_email(notification["notification_id"], recipient["id"], recipient["email"], subject, "失败", error)
        with get_conn() as conn:
            conn.execute(
                "UPDATE ack_recipients SET status = '发送失败', updated_at = ? WHERE id = ?",
                (datetime.now().isoformat(), recipient["id"]),
            )
            conn.execute(
                """
                INSERT INTO audit_log (notification_id, action, detail, actor, timestamp)
                VALUES (?, ?, ?, ?, ?)
                """,
                (notification["notification_id"], "发送回执邮件失败", recipient["email"], "系统", datetime.now().isoformat()),
            )
        return False, error

    now = datetime.now().isoformat()
    with get_conn() as conn:
        conn.execute(
            "UPDATE ack_recipients SET status = '已发送', sent_at = ?, updated_at = ? WHERE id = ?",
            (now, now, recipient["id"]),
        )
        conn.execute(
            """
            INSERT INTO audit_log (notification_id, action, detail, actor, timestamp)
            VALUES (?, ?, ?, ?, ?)
            """,
            (notification["notification_id"], "发送回执邮件", recipient["email"], "系统", now),
        )
    _log_email(notification["notification_id"], recipient["id"], recipient["email"], subject, "成功")
    return True, ""
