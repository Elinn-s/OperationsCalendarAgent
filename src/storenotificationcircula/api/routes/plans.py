from __future__ import annotations

import json
import re
import uuid
from datetime import date, datetime, timedelta
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from storenotificationcircula.db.database import generate_system_no, get_conn, log_action
from storenotificationcircula.services.ack import add_ack_recipients
from storenotificationcircula.services.reminders import process_deadline_reminders, process_plan_reminders

router = APIRouter()


class PlanPayload(BaseModel):
    activity_name: str
    notification_content: str = ""
    planned_publish_date: str | None = None
    make_reminder_date: str | None = None
    publish_reminder_date: str | None = None
    effective_start: str | None = None
    effective_end: str | None = None
    owner: str = ""
    status: str = "已预录"
    reminder_enabled: int = 1
    actor_email: str = ""
    reminder_email: str = ""


class PublishPayload(BaseModel):
    doc_ref: str = ""
    notice_type: str = "其他"
    department: str = ""
    title: str = ""
    target_scope: str = ""
    content: str = ""
    effective_start: str | None = None
    effective_end: str | None = None
    actor_email: str = ""
    reminder_email: str = ""


def _dict(row: Any) -> dict[str, Any]:
    return dict(row) if row else {}


def _extract_labeled_value(text: str, labels: list[str]) -> str:
    label_pattern = "|".join(re.escape(label) for label in labels)
    match = re.search(rf"(?:{label_pattern})\s*[:：]\s*([^\n，,；;]+)", text)
    return match.group(1).strip() if match else ""


def _extract_date(text: str) -> date | None:
    for pattern, fmt in [
        (r"\d{4}-\d{1,2}-\d{1,2}", "%Y-%m-%d"),
        (r"\d{4}/\d{1,2}/\d{1,2}", "%Y/%m/%d"),
        (r"\d{4}年\d{1,2}月\d{1,2}日", "%Y年%m月%d日"),
    ]:
        match = re.search(pattern, text)
        if match:
            return datetime.strptime(match.group(0), fmt).date()
    match = re.search(r"(\d{1,2})月(\d{1,2})日", text)
    if match:
        return date(date.today().year, int(match.group(1)), int(match.group(2)))
    return None


@router.post("/extract")
def extract_plan_from_text(body: dict[str, str]) -> dict[str, Any]:
    text = (body.get("text") or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="text is required")

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    activity_name = _extract_labeled_value(text, ["活动名称", "活动", "主题", "标题"])
    if not activity_name and lines:
        activity_name = re.sub(r"^(关于|请|需|计划)", "", lines[0]).strip(" ：:，,。")

    owner = _extract_labeled_value(text, ["责任人", "负责人", "owner", "联系人"])
    publish_date_text = _extract_labeled_value(text, ["发布日期", "计划发布日期", "发布时间", "发出时间", "发出日期"])
    planned_publish_date = _extract_date(publish_date_text or text) or (date.today() + timedelta(days=14))

    return {
        "activity_name": activity_name,
        "owner": owner,
        "notification_content": text,
        "planned_publish_date": planned_publish_date.isoformat(),
        "make_reminder_date": (planned_publish_date - timedelta(days=14)).isoformat(),
        "publish_reminder_date": (planned_publish_date - timedelta(days=7)).isoformat(),
        "status": "已预录",
    }


@router.get("")
def list_plans() -> list[dict[str, Any]]:
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT *
            FROM plans
            ORDER BY planned_publish_date IS NULL, planned_publish_date, created_at DESC
            """
        ).fetchall()
    return [_dict(row) for row in rows]


@router.post("")
def create_plan(payload: PlanPayload) -> dict[str, Any]:
    if not payload.activity_name.strip():
        raise HTTPException(status_code=400, detail="activity_name is required")
    now = datetime.now().isoformat()
    planned = payload.planned_publish_date or (date.today() + timedelta(days=14)).isoformat()
    make = payload.make_reminder_date or (date.fromisoformat(planned) - timedelta(days=14)).isoformat()
    publish = payload.publish_reminder_date or (date.fromisoformat(planned) - timedelta(days=7)).isoformat()
    with get_conn() as conn:
        cursor = conn.execute(
            """
            INSERT INTO plans
                (activity_name, notification_content, planned_publish_date, make_reminder_date,
                 publish_reminder_date, effective_start, effective_end, owner, reminder_email,
                 reminder_enabled, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                payload.activity_name.strip(),
                payload.notification_content.strip(),
                planned,
                make,
                publish,
                payload.effective_start,
                payload.effective_end,
                payload.owner.strip(),
                payload.reminder_email.strip(),
                1 if payload.reminder_enabled else 0,
                payload.status,
                now,
                now,
            ),
        )
        plan_id = cursor.lastrowid
    return {"id": plan_id, "status": "ok"}


@router.put("/{plan_id}")
def update_plan(plan_id: int, payload: PlanPayload) -> dict[str, str]:
    if not payload.activity_name.strip():
        raise HTTPException(status_code=400, detail="activity_name is required")
    now = datetime.now().isoformat()
    with get_conn() as conn:
        existing = conn.execute("SELECT id, publish_reminder_date, reminder_enabled, remind_7d_sent FROM plans WHERE id = ?", (plan_id,)).fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="plan not found")
        reset_7d_sent = (
            (existing["publish_reminder_date"] or "") != (payload.publish_reminder_date or "")
            or int(existing["reminder_enabled"] if existing["reminder_enabled"] is not None else 1) != (1 if payload.reminder_enabled else 0)
        )
        conn.execute(
            """
            UPDATE plans
            SET activity_name = ?, notification_content = ?, planned_publish_date = ?,
                make_reminder_date = ?, publish_reminder_date = ?, effective_start = ?,
                effective_end = ?, owner = ?, reminder_email = ?, reminder_enabled = ?,
                status = ?, remind_7d_sent = ?, updated_at = ?
            WHERE id = ?
            """,
            (
                payload.activity_name.strip(),
                payload.notification_content.strip(),
                payload.planned_publish_date,
                payload.make_reminder_date,
                payload.publish_reminder_date,
                payload.effective_start,
                payload.effective_end,
                payload.owner.strip(),
                payload.reminder_email.strip(),
                1 if payload.reminder_enabled else 0,
                payload.status,
                0 if reset_7d_sent else existing["remind_7d_sent"],
                now,
                plan_id,
            ),
        )
    return {"status": "ok"}


@router.delete("/{plan_id}")
def delete_plan(plan_id: int) -> dict[str, str]:
    with get_conn() as conn:
        existing = conn.execute("SELECT id FROM plans WHERE id = ?", (plan_id,)).fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="plan not found")
        conn.execute("DELETE FROM plans WHERE id = ?", (plan_id,))
    return {"status": "deleted"}


@router.post("/{plan_id}/scan-reminders")
def scan_plan_reminders(plan_id: int) -> dict[str, int]:
    with get_conn() as conn:
        existing = conn.execute("SELECT id FROM plans WHERE id = ?", (plan_id,)).fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="plan not found")
    return process_plan_reminders(send_emails=True, plan_id=plan_id)


@router.post("/{plan_id}/publish")
def publish_plan(plan_id: int, payload: PublishPayload) -> dict[str, Any]:
    now = datetime.now().isoformat()
    with get_conn() as conn:
        plan = conn.execute("SELECT * FROM plans WHERE id = ?", (plan_id,)).fetchone()
        if not plan:
            raise HTTPException(status_code=404, detail="plan not found")

        notification_id = str(uuid.uuid4())
        system_no = generate_system_no()
        title = payload.title.strip() or plan["activity_name"]
        content = payload.content.strip() or plan["notification_content"] or ""
        effective_start = payload.effective_start or plan["effective_start"] or date.today().isoformat()
        effective_end = payload.effective_end or plan["effective_end"] or plan["planned_publish_date"]

        conn.execute(
            """
            INSERT INTO notifications
                (notification_id, doc_ref, system_no, notice_type, issuer, owner, department,
                 title, description, purpose, target_scope, deadline, effective_start,
                 effective_end, status, tags, file_path, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, '执行中', ?, '', ?, ?)
            """,
            (
                notification_id,
                payload.doc_ref.strip(),
                system_no,
                payload.notice_type.strip() or "其他",
                payload.department.strip(),
                plan["owner"] or "",
                payload.department.strip(),
                title,
                content,
                content,
                payload.target_scope.strip(),
                effective_end,
                effective_start,
                effective_end,
                json.dumps(["预录发布"], ensure_ascii=False),
                now,
                now,
            ),
        )
        conn.execute(
            "UPDATE plans SET status = '已发布', linked_notification_id = ?, updated_at = ? WHERE id = ?",
            (notification_id, now, plan_id),
        )

    email = payload.reminder_email or payload.actor_email
    if email:
        add_ack_recipients(
            notification_id,
            [{"department": "默认提醒", "recipient_name": "当前登录邮箱", "email": email}],
        )
    log_action(notification_id, "API预录发布", f"预录活动: {title}", payload.actor_email or "API")
    stats = process_deadline_reminders(send_emails=True, notification_id=notification_id)
    return {"notification_id": notification_id, "system_no": system_no, "reminder_stats": stats}
