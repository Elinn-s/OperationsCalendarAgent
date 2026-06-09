from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel

from storenotificationcircula.services.auth import (
    SESSION_COOKIE_NAME,
    authenticate,
    cookie_secure,
    create_session,
    delete_session,
    get_user_by_session,
    session_max_age_seconds,
)

router = APIRouter()


class LoginPayload(BaseModel):
    email: str
    password: str


@router.post("/login")
def login(payload: LoginPayload, response: Response) -> dict[str, Any]:
    user = authenticate(payload.email, payload.password)
    if not user:
        raise HTTPException(status_code=401, detail="邮箱或密码不正确")
    token, _ = create_session(int(user["id"]))
    response.set_cookie(
        SESSION_COOKIE_NAME,
        token,
        httponly=True,
        max_age=session_max_age_seconds(),
        samesite="lax",
        secure=cookie_secure(),
    )
    return {"user": user}


@router.post("/logout")
def logout(request: Request, response: Response) -> dict[str, str]:
    delete_session(request.cookies.get(SESSION_COOKIE_NAME, ""))
    response.delete_cookie(SESSION_COOKIE_NAME, samesite="lax", secure=cookie_secure())
    return {"status": "ok"}


@router.get("/me")
def me(request: Request) -> dict[str, Any]:
    user = get_user_by_session(request.cookies.get(SESSION_COOKIE_NAME))
    if not user:
        raise HTTPException(status_code=401, detail="未登录")
    return {"user": user}
