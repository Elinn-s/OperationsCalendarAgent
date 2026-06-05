from __future__ import annotations

import json
import tempfile
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field

from storenotificationcircula.db.database import generate_system_no, get_conn, log_action
from storenotificationcircula.services.ack import add_ack_recipients
from storenotificationcircula.services.dify_client import extract_fields
from storenotificationcircula.services.pdf_parser import extract_text
from storenotificationcircula.services.reminders import process_deadline_reminders

router = APIRouter()


class NotificationPayload(BaseModel):
    doc_ref: str = ""
    system_no: str = ""
    notice_type: str = "其他"
    issuer: str = ""
    owner: str = ""
    owner_role: str = ""
    department: str = ""
    title: str
    description: str = ""
    purpose: str = ""
    target_scope: str = ""
    impact_store: str = ""
    impact_region: str = ""
    impact_role: str = ""
    deadline: str | None = None
    effective_start: str | None = None
    effective_end: str | None = None
    status: str = "草稿"
    tags: list[str] = Field(default_factory=list)
    reminder_days: str = ""
    reminder_email: str = ""
    actor_email: str = ""


def _dict(row: Any) -> dict[str, Any]:
    return dict(row) if row else {}


def _sync_dates(payload: NotificationPayload) -> tuple[str | None, str | None]:
    deadline = payload.deadline or payload.effective_end
    effective_end = payload.effective_end or payload.deadline
    return deadline, effective_end


def _attach_default_reminder(notification_id: str, email: str) -> int:
    email = (email or "").strip().lower()
    if not email:
        return 0
    return add_ack_recipients(
        notification_id,
        [{"department": "默认提醒", "recipient_name": "当前登录邮箱", "email": email}],
    )


@router.get("")
def list_notifications(
    status: str | None = Query(default=None),
    owner: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
) -> list[dict[str, Any]]:
    sql = "SELECT * FROM notifications WHERE 1=1"
    params: list[Any] = []
    if status:
        sql += " AND status = ?"
        params.append(status)
    if owner:
        sql += " AND owner LIKE ?"
        params.append(f"%{owner}%")
    sql += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)
    with get_conn() as conn:
        return [_dict(row) for row in conn.execute(sql, params).fetchall()]


@router.post("/extract-pdf")
async def extract_pdf_fields(request: Request, filename: str = Query(default="upload.pdf")) -> dict[str, Any]:
    raw_bytes = await request.body()
    if not raw_bytes:
        raise HTTPException(status_code=400, detail="empty pdf body")

    tmp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(raw_bytes)
            tmp_path = Path(tmp.name)
        text = extract_text(tmp_path)
        fields = extract_fields(text)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        if tmp_path:
            tmp_path.unlink(missing_ok=True)

    return {"filename": filename, "text_length": len(text), "fields": fields}


@router.get("/{notification_id}")
def get_notification(notification_id: str) -> dict[str, Any]:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM notifications WHERE notification_id = ?",
            (notification_id,),
        ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="notification not found")
    return _dict(row)


@router.post("")
def create_notification(payload: NotificationPayload) -> dict[str, Any]:
    if not payload.title.strip():
        raise HTTPException(status_code=400, detail="title is required")

    now = datetime.now().isoformat()
    notification_id = str(uuid.uuid4())
    system_no = payload.system_no.strip() or generate_system_no()
    deadline, effective_end = _sync_dates(payload)
    actor = payload.actor_email or payload.reminder_email or "API"

    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO notifications
                (notification_id, doc_ref, system_no, notice_type, issuer, owner, owner_role,
                 department, title, description, purpose, target_scope, impact_store,
                 impact_region, impact_role, deadline, effective_start, effective_end,
                 status, tags, reminder_days, file_path, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, '', ?, ?)
            """,
            (
                notification_id,
                payload.doc_ref.strip(),
                system_no,
                payload.notice_type.strip() or "其他",
                payload.issuer.strip(),
                payload.owner.strip(),
                payload.owner_role.strip(),
                payload.department.strip(),
                payload.title.strip(),
                payload.description.strip(),
                payload.purpose.strip(),
                payload.target_scope.strip(),
                payload.impact_store.strip(),
                payload.impact_region.strip(),
                payload.impact_role.strip(),
                deadline,
                payload.effective_start,
                effective_end,
                payload.status.strip() or "草稿",
                json.dumps(payload.tags, ensure_ascii=False),
                payload.reminder_days.strip(),
                now,
                now,
            ),
        )

    added_recipients = _attach_default_reminder(notification_id, payload.reminder_email or payload.actor_email)
    log_action(notification_id, "API新增通告", "Fetch前端创建", actor)
    return {
        "notification_id": notification_id,
        "system_no": system_no,
        "added_recipients": added_recipients,
    }


@router.put("/{notification_id}")
def update_notification(notification_id: str, payload: NotificationPayload) -> dict[str, Any]:
    if not payload.title.strip():
        raise HTTPException(status_code=400, detail="title is required")

    deadline, effective_end = _sync_dates(payload)
    if payload.effective_start and effective_end and effective_end < payload.effective_start:
        raise HTTPException(status_code=400, detail="deadline cannot be earlier than effective_start")

    now = datetime.now().isoformat()
    actor = payload.actor_email or payload.reminder_email or "API"

    with get_conn() as conn:
        existing = conn.execute(
            "SELECT notification_id FROM notifications WHERE notification_id = ?",
            (notification_id,),
        ).fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="notification not found")
        conn.execute(
            """
            UPDATE notifications
            SET doc_ref = ?, system_no = ?, notice_type = ?, issuer = ?, owner = ?,
                owner_role = ?, department = ?, title = ?, description = ?, purpose = ?,
                target_scope = ?, impact_store = ?, impact_region = ?, impact_role = ?,
                deadline = ?, effective_start = ?, effective_end = ?, status = ?,
                tags = ?, reminder_days = ?, updated_at = ?
            WHERE notification_id = ?
            """,
            (
                payload.doc_ref.strip(),
                payload.system_no.strip(),
                payload.notice_type.strip() or "其他",
                payload.issuer.strip(),
                payload.owner.strip(),
                payload.owner_role.strip(),
                payload.department.strip(),
                payload.title.strip(),
                payload.description.strip(),
                payload.purpose.strip(),
                payload.target_scope.strip(),
                payload.impact_store.strip(),
                payload.impact_region.strip(),
                payload.impact_role.strip(),
                deadline,
                payload.effective_start,
                effective_end,
                payload.status.strip() or "草稿",
                json.dumps(payload.tags, ensure_ascii=False),
                payload.reminder_days.strip(),
                now,
                notification_id,
            ),
        )

    added_recipients = _attach_default_reminder(notification_id, payload.reminder_email or payload.actor_email)
    log_action(notification_id, "API修改通告", "Fetch前端保存", actor)
    return {"status": "ok", "added_recipients": added_recipients}


@router.post("/{notification_id}/scan-reminders")
def scan_notification_reminders(notification_id: str) -> dict[str, int]:
    with get_conn() as conn:
        existing = conn.execute(
            "SELECT notification_id FROM notifications WHERE notification_id = ?",
            (notification_id,),
        ).fetchone()
    if not existing:
        raise HTTPException(status_code=404, detail="notification not found")
    return process_deadline_reminders(send_emails=True, notification_id=notification_id)


@router.delete("/{notification_id}")
def delete_notification(notification_id: str, actor_email: str = Query(default="")) -> dict[str, str]:
    with get_conn() as conn:
        existing = conn.execute(
            "SELECT notification_id FROM notifications WHERE notification_id = ?",
            (notification_id,),
        ).fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="notification not found")
        conn.execute("DELETE FROM audit_log WHERE notification_id = ?", (notification_id,))
        conn.execute("DELETE FROM reminder_log WHERE notification_id = ?", (notification_id,))
        conn.execute("DELETE FROM email_log WHERE notification_id = ?", (notification_id,))
        conn.execute("DELETE FROM ack_recipients WHERE notification_id = ?", (notification_id,))
        conn.execute("DELETE FROM notifications WHERE notification_id = ?", (notification_id,))
    return {"status": "deleted"}


@router.get("/{notification_id}/history")
def get_notification_history(notification_id: str) -> list[dict[str, Any]]:
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT timestamp AS time, '操作' AS type, actor AS actor, action AS action, detail AS detail
            FROM audit_log
            WHERE notification_id = ?
            UNION ALL
            SELECT sent_at AS time, '邮件' AS type, recipient_email AS actor, subject AS action, status || COALESCE('：' || error, '') AS detail
            FROM email_log
            WHERE notification_id = ?
            UNION ALL
            SELECT created_at AS time, '自动提醒' AS type, recipient_email AS actor, reminder_type AS action, status || COALESCE('：' || error, '') AS detail
            FROM reminder_log
            WHERE notification_id = ?
            ORDER BY time DESC
            """,
            (notification_id, notification_id, notification_id),
        ).fetchall()
    return [_dict(row) for row in rows]
