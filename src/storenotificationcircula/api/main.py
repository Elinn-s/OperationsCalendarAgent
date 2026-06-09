from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from storenotificationcircula.api.routes import acknowledgements, auth, email_settings, health, notifications, plans, reminders
from storenotificationcircula.db.database import init_db
from storenotificationcircula.services.auth import SESSION_COOKIE_NAME, auth_enabled, get_user_by_session

app = FastAPI(title="Store Notification Circulation API", version="0.1.0")
PUBLIC_DIR = Path(__file__).resolve().parents[3] / "public"


@app.on_event("startup")
def _startup() -> None:
    init_db()


@app.middleware("http")
async def require_login(request: Request, call_next):
    if not auth_enabled():
        return await call_next(request)
    protected_prefixes = ("/notifications", "/plans", "/ack/notifications", "/reminders", "/email-settings")
    if request.url.path.startswith(protected_prefixes):
        user = get_user_by_session(request.cookies.get(SESSION_COOKIE_NAME))
        if not user:
            return JSONResponse({"detail": "未登录"}, status_code=401)
        request.state.user = user
    return await call_next(request)


app.include_router(health.router)
app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(notifications.router, prefix="/notifications", tags=["notifications"])
app.include_router(plans.router, prefix="/plans", tags=["plans"])
app.include_router(acknowledgements.router, prefix="/ack", tags=["acknowledgements"])
app.include_router(reminders.router, prefix="/reminders", tags=["reminders"])
app.include_router(email_settings.router, prefix="/email-settings", tags=["email-settings"])

if PUBLIC_DIR.exists():
    app.mount("/public", StaticFiles(directory=PUBLIC_DIR), name="public")


@app.get("/app", include_in_schema=False)
def frontend_app() -> FileResponse:
    return FileResponse(PUBLIC_DIR / "page.html")
