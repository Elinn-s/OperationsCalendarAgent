from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from storenotificationcircula.db.database import get_conn
from storenotificationcircula.services.ack import confirm_ack_token, get_ack_by_token, get_ack_recipients, send_ack_email

router = APIRouter()


def _dict(row: Any) -> dict[str, Any]:
    return dict(row) if row else {}


@router.get("/{token}")
def get_acknowledgement(token: str) -> dict[str, Any]:
    row = get_ack_by_token(token)
    if not row:
        raise HTTPException(status_code=404, detail="acknowledgement not found")
    return _dict(row)


@router.post("/{token}/confirm")
def confirm_acknowledgement(token: str) -> dict[str, Any]:
    status, row = confirm_ack_token(token)
    if status == "not_found":
        raise HTTPException(status_code=404, detail="acknowledgement not found")
    return {"status": status, "acknowledgement": _dict(row)}


@router.post("/notifications/{notification_id}/send")
def send_notification_ack_emails(notification_id: str) -> dict[str, int]:
    with get_conn() as conn:
        notification = conn.execute(
            "SELECT * FROM notifications WHERE notification_id = ?",
            (notification_id,),
        ).fetchone()
    if not notification:
        raise HTTPException(status_code=404, detail="notification not found")

    stats = {"checked": 0, "sent": 0, "failed": 0, "skipped": 0}
    for raw_recipient in get_ack_recipients(notification_id):
        recipient = _dict(raw_recipient)
        stats["checked"] += 1
        if recipient.get("confirmed_at"):
            stats["skipped"] += 1
            continue
        ok, _ = send_ack_email(_dict(notification), recipient)
        if ok:
            stats["sent"] += 1
        else:
            stats["failed"] += 1
    return stats
