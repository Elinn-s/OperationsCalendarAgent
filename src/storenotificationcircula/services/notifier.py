from __future__ import annotations

from storenotificationcircula.services.email.sender import send_email

def send_reminder(to: str, subject: str, body: str) -> None:
    send_email(to, subject, body)


def check_and_send_reminders() -> None:
    """Scan deadlines and send configured reminder emails."""
    from storenotificationcircula.services.reminders import process_deadline_reminders, process_plan_reminders

    process_deadline_reminders(send_emails=True)
    process_plan_reminders(send_emails=True)
