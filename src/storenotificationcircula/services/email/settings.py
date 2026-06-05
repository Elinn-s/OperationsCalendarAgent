from __future__ import annotations

import os
from typing import Any

from dotenv import load_dotenv

from storenotificationcircula.db.database import get_conn

load_dotenv()


def secret(key: str, default: str = "") -> str:
    return os.getenv(key, default)


def get_setting(key: str, default: str = "") -> str:
    try:
        with get_conn() as conn:
            row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
            if row and row["value"]:
                return row["value"]
    except Exception:
        pass
    return default


def upsert_setting(key: str, value: str) -> None:
    with get_conn() as conn:
        if conn.dialect == "postgres":
            conn.execute(
                """
                INSERT INTO settings (key, value)
                VALUES (?, ?)
                ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value
                """,
                (key, value),
            )
        else:
            conn.execute(
                """
                INSERT INTO settings (key, value)
                VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
                """,
                (key, value),
            )


def default_contact_emails() -> list[str]:
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT email
            FROM email_contacts
            WHERE is_default = 1
            ORDER BY id
            """
        ).fetchall()
    return sorted({row["email"].strip().lower() for row in rows if row["email"]})


def get_default_smtp_account(account_id: int | None = None) -> dict[str, Any]:
    with get_conn() as conn:
        row = None
        if account_id:
            row = conn.execute("SELECT * FROM smtp_accounts WHERE id = ?", (account_id,)).fetchone()
        if not row:
            row = conn.execute("SELECT * FROM smtp_accounts WHERE is_default = 1 ORDER BY id DESC LIMIT 1").fetchone()
        if row:
            return dict(row)

    username = secret("SMTP_USER")
    return {
        "id": None,
        "name": "ENV SMTP",
        "host": secret("SMTP_HOST"),
        "port": int(secret("SMTP_PORT", "587")),
        "username": username,
        "password": secret("SMTP_PASSWORD"),
        "sender": secret("SMTP_FROM", username),
        "use_ssl": 1 if secret("SMTP_SSL", "false").lower() in ("1", "true", "yes") else 0,
        "use_tls": 1 if secret("SMTP_STARTTLS", "true").lower() in ("1", "true", "yes") else 0,
        "is_default": 1,
    }
