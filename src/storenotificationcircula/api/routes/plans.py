from __future__ import annotations

import re
from datetime import date, datetime, timedelta
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from storenotificationcircula.db.database import get_conn
from storenotificationcircula.services.email.settings import get_setting
from storenotificationcircula.services.reminders import process_plan_reminders

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
    reminder_days: str = ""
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


def _default_plan_reminder_days() -> int:
    raw = get_setting("plan_reminder_days", "7")
    days = []
    for part in raw.replace("，", ",").split(","):
        try:
            days.append(int(part.strip()))
        except ValueError:
            continue
    return max(days) if days else 7


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
        "publish_reminder_date": (planned_publish_date - timedelta(days=_default_plan_reminder_days())).isoformat(),
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
    reminder_days = payload.reminder_days.strip()
    publish_offset = _default_plan_reminder_days()
    if reminder_days:
        try:
            publish_offset = max(int(part.strip()) for part in reminder_days.replace("，", ",").split(",") if part.strip())
        except ValueError:
            publish_offset = _default_plan_reminder_days()
    publish = payload.publish_reminder_date or (date.fromisoformat(planned) - timedelta(days=publish_offset)).isoformat()
    with get_conn() as conn:
        cursor = conn.execute(
            """
            INSERT INTO plans
                (activity_name, notification_content, planned_publish_date, make_reminder_date,
                 publish_reminder_date, effective_start, effective_end, owner, reminder_email,
                 reminder_enabled, reminder_days, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                payload.reminder_days.strip(),
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
        existing = conn.execute(
            "SELECT id, publish_reminder_date, reminder_enabled, reminder_days, remind_7d_sent FROM plans WHERE id = ?",
            (plan_id,),
        ).fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="plan not found")
        reset_7d_sent = (
            (existing["publish_reminder_date"] or "") != (payload.publish_reminder_date or "")
            or int(existing["reminder_enabled"] if existing["reminder_enabled"] is not None else 1) != (1 if payload.reminder_enabled else 0)
            or (existing["reminder_days"] or "") != (payload.reminder_days or "")
        )
        conn.execute(
            """
            UPDATE plans
            SET activity_name = ?, notification_content = ?, planned_publish_date = ?,
                make_reminder_date = ?, publish_reminder_date = ?, effective_start = ?,
                effective_end = ?, owner = ?, reminder_email = ?, reminder_enabled = ?,
                reminder_days = ?, status = ?, remind_7d_sent = ?, updated_at = ?
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
                payload.reminder_days.strip(),
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
