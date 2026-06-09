from __future__ import annotations

import base64
import hashlib
import hmac
import os
import secrets
from datetime import datetime, timedelta
from typing import Any

from dotenv import load_dotenv

from storenotificationcircula.db.database import get_conn

load_dotenv()

SESSION_COOKIE_NAME = "ops_agent_session"


def _secret(key: str, default: str = "") -> str:
    return os.getenv(key, default)


def session_max_age_seconds() -> int:
    try:
        return max(int(_secret("AUTH_SESSION_SECONDS", "86400")), 300)
    except ValueError:
        return 86400


def cookie_secure() -> bool:
    return _secret("AUTH_COOKIE_SECURE", "false").strip().lower() in {"1", "true", "yes", "on"}


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    rounds = 180_000
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, rounds)
    return "pbkdf2_sha256${}${}${}".format(
        rounds,
        base64.b64encode(salt).decode("ascii"),
        base64.b64encode(digest).decode("ascii"),
    )


def verify_password(password: str, password_hash: str) -> bool:
    try:
        algorithm, raw_rounds, raw_salt, raw_digest = password_hash.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        rounds = int(raw_rounds)
        salt = base64.b64decode(raw_salt.encode("ascii"))
        expected = base64.b64decode(raw_digest.encode("ascii"))
    except Exception:
        return False
    actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, rounds)
    return hmac.compare_digest(actual, expected)


def public_user(row: Any) -> dict[str, Any]:
    return {
        "id": row["id"],
        "email": row["email"],
        "display_name": row["display_name"] or row["email"],
    }


def authenticate(email: str, password: str) -> dict[str, Any] | None:
    with get_conn() as conn:
        row = conn.execute(
            """
            SELECT id, email, password_hash, display_name, is_active
            FROM app_users
            WHERE email = ?
            """,
            (email.strip().lower(),),
        ).fetchone()
    if not row or not int(row["is_active"] or 0):
        return None
    if not verify_password(password, row["password_hash"]):
        return None
    return public_user(row)


def create_session(user_id: int) -> tuple[str, datetime]:
    token = secrets.token_urlsafe(32)
    now = datetime.now()
    expires_at = now + timedelta(seconds=session_max_age_seconds())
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO app_sessions (token, user_id, expires_at, created_at) VALUES (?, ?, ?, ?)",
            (token, user_id, expires_at.isoformat(), now.isoformat()),
        )
    return token, expires_at


def delete_session(token: str) -> None:
    if not token:
        return
    with get_conn() as conn:
        conn.execute("DELETE FROM app_sessions WHERE token = ?", (token,))


def get_user_by_session(token: str | None) -> dict[str, Any] | None:
    if not token:
        return None
    now = datetime.now().isoformat()
    with get_conn() as conn:
        row = conn.execute(
            """
            SELECT u.id, u.email, u.display_name, u.is_active, s.expires_at
            FROM app_sessions s
            JOIN app_users u ON u.id = s.user_id
            WHERE s.token = ?
            """,
            (token,),
        ).fetchone()
        if not row:
            return None
        if str(row["expires_at"]) <= now or not int(row["is_active"] or 0):
            conn.execute("DELETE FROM app_sessions WHERE token = ?", (token,))
            return None
    return public_user(row)
