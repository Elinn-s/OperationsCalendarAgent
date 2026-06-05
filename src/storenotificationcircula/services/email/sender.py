from __future__ import annotations

import smtplib
from email.message import EmailMessage
from typing import Any

from storenotificationcircula.services.email.settings import get_default_smtp_account


def send_email(to: str, subject: str, body: str, account_id: int | None = None) -> None:
    account: dict[str, Any] = get_default_smtp_account(account_id)
    host = account.get("host") or ""
    port = int(account.get("port") or 587)
    username = account.get("username") or ""
    password = account.get("password") or ""
    sender = account.get("sender") or username
    use_ssl = bool(account.get("use_ssl"))
    use_tls = bool(account.get("use_tls"))

    if not host or not sender:
        raise RuntimeError("SMTP host / sender 未配置。")

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
