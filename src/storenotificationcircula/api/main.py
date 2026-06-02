from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from storenotificationcircula.api.routes import acknowledgements, health, notifications, plans, reminders
from storenotificationcircula.db.database import init_db

app = FastAPI(title="Store Notification Circulation API", version="0.1.0")
PUBLIC_DIR = Path(__file__).resolve().parents[3] / "public"


@app.on_event("startup")
def _startup() -> None:
    init_db()


app.include_router(health.router)
app.include_router(notifications.router, prefix="/notifications", tags=["notifications"])
app.include_router(plans.router, prefix="/plans", tags=["plans"])
app.include_router(acknowledgements.router, prefix="/ack", tags=["acknowledgements"])
app.include_router(reminders.router, prefix="/reminders", tags=["reminders"])

if PUBLIC_DIR.exists():
    app.mount("/public", StaticFiles(directory=PUBLIC_DIR), name="public")


@app.get("/app", include_in_schema=False)
def frontend_app() -> FileResponse:
    return FileResponse(PUBLIC_DIR / "page.html")
