from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from storenotificationcircula.db.database import get_conn

router = APIRouter()


class TemplatePayload(BaseModel):
    name: str
    description: str = ""
    content: str


def _dict(row: Any) -> dict[str, Any]:
    return dict(row) if row else {}


@router.get("")
def list_templates() -> list[dict[str, Any]]:
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM templates ORDER BY created_at DESC, id DESC").fetchall()
    return [_dict(row) for row in rows]


@router.post("")
def create_template(payload: TemplatePayload) -> dict[str, Any]:
    if not payload.name.strip():
        raise HTTPException(status_code=400, detail="template name is required")
    if not payload.content.strip():
        raise HTTPException(status_code=400, detail="template content is required")
    with get_conn() as conn:
        cursor = conn.execute(
            """
            INSERT INTO templates (name, description, content, variables, created_at)
            VALUES (?, ?, ?, '[]', ?)
            """,
            (
                payload.name.strip(),
                payload.description.strip(),
                payload.content.strip(),
                datetime.now().isoformat(),
            ),
        )
        template_id = cursor.lastrowid
    return {"id": template_id, "status": "ok"}


@router.delete("/{template_id}")
def delete_template(template_id: int) -> dict[str, str]:
    with get_conn() as conn:
        existing = conn.execute("SELECT id FROM templates WHERE id = ?", (template_id,)).fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="template not found")
        conn.execute("DELETE FROM templates WHERE id = ?", (template_id,))
    return {"status": "deleted"}
