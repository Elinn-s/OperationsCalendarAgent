from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from storenotificationcircula.db.database import get_conn
from storenotificationcircula.services.email.providers import detect_email_provider
from storenotificationcircula.services.email.sender import send_email
from storenotificationcircula.services.email.settings import get_setting, upsert_setting

router = APIRouter()


class SmtpPayload(BaseModel):
    name: str
    host: str
    port: int = 587
    username: str = ""
    password: str = ""
    sender: str = ""
    use_ssl: int = 0
    use_tls: int = 1
    is_default: int = 1


class ContactPayload(BaseModel):
    label: str = ""
    email: str
    kind: str = "收件人"
    is_default: int = 0


class ReminderSettingsPayload(BaseModel):
    notification_reminder_days: str = "7"
    plan_reminder_days: str = "7"


class TestEmailPayload(BaseModel):
    to_email: str
    smtp_id: int | None = None


def _dict(row: Any) -> dict[str, Any]:
    return dict(row) if row else {}


def _hide_password(account: dict[str, Any]) -> dict[str, Any]:
    has_password = 1 if account.get("password") else 0
    account.pop("password", None)
    account["has_password"] = has_password
    return account


def _last_insert_id(conn, cursor, table: str) -> int:
    value = getattr(cursor, "lastrowid", None)
    if value:
        return int(value)
    row = conn.execute(f"SELECT MAX(id) AS id FROM {table}").fetchone()
    return int(row["id"])


@router.get("")
def get_email_settings() -> dict[str, Any]:
    with get_conn() as conn:
        smtp_accounts = [_hide_password(_dict(row)) for row in conn.execute("SELECT * FROM smtp_accounts ORDER BY is_default DESC, id DESC").fetchall()]
        contacts = [_dict(row) for row in conn.execute("SELECT * FROM email_contacts ORDER BY is_default DESC, id DESC").fetchall()]
        logs = [
            _dict(row)
            for row in conn.execute(
                """
                SELECT notification_id, reminder_type, reminder_date, recipient_email, status, error, created_at
                FROM reminder_log
                ORDER BY created_at DESC
                LIMIT 20
                """
            ).fetchall()
        ]
    return {
        "smtp_accounts": smtp_accounts,
        "contacts": contacts,
        "settings": {
            "notification_reminder_days": get_setting("notification_reminder_days", "7"),
            "plan_reminder_days": get_setting("plan_reminder_days", "7"),
        },
        "reminder_logs": logs,
    }


@router.get("/provider")
def get_email_provider(email: str) -> dict[str, Any]:
    if "@" not in email:
        raise HTTPException(status_code=400, detail="email is invalid")
    return detect_email_provider(email)


@router.put("/settings")
def save_reminder_settings(payload: ReminderSettingsPayload) -> dict[str, str]:
    upsert_setting("notification_reminder_days", payload.notification_reminder_days.strip() or "7")
    upsert_setting("plan_reminder_days", payload.plan_reminder_days.strip() or "7")
    return {"status": "ok"}


@router.post("/smtp")
def create_smtp_account(payload: SmtpPayload) -> dict[str, Any]:
    if not payload.name.strip() or not payload.host.strip():
        raise HTTPException(status_code=400, detail="name and host are required")
    now = datetime.now().isoformat()
    with get_conn() as conn:
        if payload.is_default:
            conn.execute("UPDATE smtp_accounts SET is_default = 0")
        cursor = conn.execute(
            """
            INSERT INTO smtp_accounts
                (name, host, port, username, password, sender, use_ssl, use_tls, is_default, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                payload.name.strip(),
                payload.host.strip(),
                payload.port,
                payload.username.strip(),
                payload.password,
                payload.sender.strip(),
                1 if payload.use_ssl else 0,
                1 if payload.use_tls else 0,
                1 if payload.is_default else 0,
                now,
                now,
            ),
        )
        account_id = _last_insert_id(conn, cursor, "smtp_accounts")
    return {"id": account_id, "status": "ok"}


@router.put("/smtp/{account_id}")
def update_smtp_account(account_id: int, payload: SmtpPayload) -> dict[str, str]:
    now = datetime.now().isoformat()
    with get_conn() as conn:
        existing = conn.execute("SELECT id, password FROM smtp_accounts WHERE id = ?", (account_id,)).fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="smtp account not found")
        if payload.is_default:
            conn.execute("UPDATE smtp_accounts SET is_default = 0 WHERE id <> ?", (account_id,))
        conn.execute(
            """
            UPDATE smtp_accounts
            SET name = ?, host = ?, port = ?, username = ?, password = ?, sender = ?,
                use_ssl = ?, use_tls = ?, is_default = ?, updated_at = ?
            WHERE id = ?
            """,
            (
                payload.name.strip(),
                payload.host.strip(),
                payload.port,
                payload.username.strip(),
                payload.password or existing["password"],
                payload.sender.strip(),
                1 if payload.use_ssl else 0,
                1 if payload.use_tls else 0,
                1 if payload.is_default else 0,
                now,
                account_id,
            ),
        )
    return {"status": "ok"}


@router.delete("/smtp/{account_id}")
def delete_smtp_account(account_id: int) -> dict[str, str]:
    with get_conn() as conn:
        conn.execute("DELETE FROM smtp_accounts WHERE id = ?", (account_id,))
    return {"status": "deleted"}


@router.post("/contacts")
def create_contact(payload: ContactPayload) -> dict[str, Any]:
    if "@" not in payload.email:
        raise HTTPException(status_code=400, detail="email is invalid")
    now = datetime.now().isoformat()
    with get_conn() as conn:
        cursor = conn.execute(
            """
            INSERT INTO email_contacts (label, email, kind, is_default, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (payload.label.strip(), payload.email.strip().lower(), payload.kind.strip() or "收件人", 1 if payload.is_default else 0, now, now),
        )
        contact_id = _last_insert_id(conn, cursor, "email_contacts")
    return {"id": contact_id, "status": "ok"}


@router.put("/contacts/{contact_id}")
def update_contact(contact_id: int, payload: ContactPayload) -> dict[str, str]:
    if "@" not in payload.email:
        raise HTTPException(status_code=400, detail="email is invalid")
    now = datetime.now().isoformat()
    with get_conn() as conn:
        existing = conn.execute("SELECT id FROM email_contacts WHERE id = ?", (contact_id,)).fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="contact not found")
        conn.execute(
            """
            UPDATE email_contacts
            SET label = ?, email = ?, kind = ?, is_default = ?, updated_at = ?
            WHERE id = ?
            """,
            (
                payload.label.strip(),
                payload.email.strip().lower(),
                payload.kind.strip() or "收件人",
                1 if payload.is_default else 0,
                now,
                contact_id,
            ),
        )
    return {"status": "ok"}


@router.delete("/contacts/{contact_id}")
def delete_contact(contact_id: int) -> dict[str, str]:
    with get_conn() as conn:
        conn.execute("DELETE FROM email_contacts WHERE id = ?", (contact_id,))
    return {"status": "deleted"}


@router.delete("/reminder-logs")
def clear_reminder_logs() -> dict[str, int | str]:
    with get_conn() as conn:
        count_row = conn.execute("SELECT COUNT(*) AS count FROM reminder_log").fetchone()
        deleted = int(count_row["count"]) if count_row else 0
        conn.execute("DELETE FROM reminder_log")
    return {"status": "deleted", "deleted": deleted}


@router.post("/test")
def test_email(payload: TestEmailPayload) -> dict[str, str]:
    if "@" not in payload.to_email:
        raise HTTPException(status_code=400, detail="to_email is invalid")
    try:
        send_email(payload.to_email.strip().lower(), "營運通告系統測試郵件", "這是一封 SMTP 對接測試郵件。", payload.smtp_id)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"测试发送失败：{exc}") from exc
    return {"status": "sent"}
