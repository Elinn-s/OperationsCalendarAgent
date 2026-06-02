from __future__ import annotations

import sys
from pathlib import Path

SRC = Path(__file__).resolve().parent / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from storenotificationcircula.db.database import init_db
from storenotificationcircula.services.reminders import process_deadline_reminders, process_plan_reminders


def main() -> None:
    init_db()
    deadline_stats = process_deadline_reminders(send_emails=True)
    plan_stats = process_plan_reminders(send_emails=True)
    stats = {
        "checked": deadline_stats["checked"] + plan_stats["checked"],
        "sent": deadline_stats["sent"] + plan_stats["sent"],
        "failed": deadline_stats["failed"] + plan_stats["failed"],
        "skipped": deadline_stats["skipped"] + plan_stats["skipped"],
        "marked_overdue": deadline_stats["marked_overdue"] + plan_stats["marked_overdue"],
    }
    print(
        "reminders "
        f"checked={stats['checked']} "
        f"sent={stats['sent']} "
        f"failed={stats['failed']} "
        f"skipped={stats['skipped']} "
        f"marked_overdue={stats['marked_overdue']}"
    )


if __name__ == "__main__":
    main()

