from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from storenotificationcircula.services.ack import confirm_ack_token, get_ack_by_token

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
