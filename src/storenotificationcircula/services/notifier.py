from __future__ import annotations

import os
import smtplib
from email.message import EmailMessage

from dotenv import load_dotenv

load_dotenv()


def _secret(key: str, default: str = "") -> str:
    value = os.getenv(key, default)
    if value:
        return value
    try:
        import streamlit as st

        return st.secrets.get(key, default)
    except Exception:
        return default


def send_email(to: str, subject: str, body: str) -> None:
    host = _secret("SMTP_HOST")
    port = int(_secret("SMTP_PORT", "587"))
    username = _secret("SMTP_USER")
    password = _secret("SMTP_PASSWORD")
    sender = _secret("SMTP_FROM", username)
    use_ssl = _secret("SMTP_SSL", "false").lower() in ("1", "true", "yes")
    use_tls = _secret("SMTP_STARTTLS", "true").lower() in ("1", "true", "yes")

    if not host or not sender:
        raise RuntimeError("SMTP_HOST / SMTP_FROM 未配置。")

    msg = EmailMessage()
    msg["From"] = sender
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)

    smtp_cls = smtplib.SMTP_SSL if use_ssl else smtplib.SMTP
    with smtp_cls(host, port, timeout=30) as server:
        if not use_ssl and use_tls:
            server.starttls()
        if username and password:
            server.login(username, password)
        server.send_message(msg)

def send_reminder(to: str, subject: str, body: str) -> None:
    send_email(to, subject, body)


def check_and_send_reminders() -> None:
    """Scan deadlines and send configured reminder emails."""
    from storenotificationcircula.services.reminders import process_deadline_reminders, process_plan_reminders

    process_deadline_reminders(send_emails=True)
    process_plan_reminders(send_emails=True)
