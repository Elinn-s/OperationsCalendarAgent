from __future__ import annotations

from fastapi import APIRouter

from storenotificationcircula.services.reminders import process_deadline_reminders, process_plan_reminders

router = APIRouter()


@router.post("/run")
def run_reminders(send_emails: bool = True) -> dict[str, int]:
    deadline_stats = process_deadline_reminders(send_emails=send_emails)
    plan_stats = process_plan_reminders(send_emails=send_emails)
    return {
        "checked": deadline_stats["checked"] + plan_stats["checked"],
        "sent": deadline_stats["sent"] + plan_stats["sent"],
        "failed": deadline_stats["failed"] + plan_stats["failed"],
        "skipped": deadline_stats["skipped"] + plan_stats["skipped"],
        "marked_overdue": deadline_stats["marked_overdue"] + plan_stats["marked_overdue"],
        "deadline_checked": deadline_stats["checked"],
        "plan_checked": plan_stats["checked"],
    }
