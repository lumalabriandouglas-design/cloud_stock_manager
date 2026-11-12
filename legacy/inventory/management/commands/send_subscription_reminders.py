from django.core.management.base import BaseCommand, CommandError

from inventory.reminders import send_subscription_reminders


class Command(BaseCommand):
    help = (
        "Email shop owners when a free trial or subscription is ending. "
        "Sends once while the due date is 1–3 days away, and once on the due "
        "date (Africa/Kampala calendar). Each reminder is stored against that "
        "due moment so it is not sent again. Schedule daily on Railway as a "
        "separate cron service, not in the web start command: "
        "0 5 * * *  (08:00 East Africa Time)  "
        "python manage.py send_subscription_reminders"
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show who would be emailed without sending or recording reminders.",
        )

    def handle(self, *args, **options):
        result = send_subscription_reminders(dry_run=options["dry_run"])
        if result["disabled"]:
            raise CommandError(
                "EMAIL_HOST is not set, so no reminder was sent or recorded. "
                "Set EMAIL_HOST, EMAIL_PORT, EMAIL_USE_TLS, EMAIL_HOST_USER, "
                "EMAIL_HOST_PASSWORD, and DEFAULT_FROM_EMAIL — the same SMTP "
                "settings low-stock emails already use — then run this command "
                "again. Schedule it daily at 08:00 Africa/Kampala (05:00 UTC, "
                "cron '0 5 * * *') as its own Railway cron service with start "
                "command: python manage.py send_subscription_reminders"
            )
        if options["dry_run"]:
            if not result["planned"]:
                self.stdout.write("No reminders to send.")
            for item in result["planned"]:
                kind = "due today" if item["kind"] == "due" else "ending soon"
                self.stdout.write(
                    f"{item['company']}: {kind} ({item['due']}) → {', '.join(item['to'])}"
                )
            self.stdout.write(
                f"Dry run: {len(result['planned'])} email(s), "
                f"{result['skipped_no_email']} shop(s) skipped with no owner email."
            )
            return
        self.stdout.write(
            f"Sent {result['sent_upcoming']} advance reminder(s) and "
            f"{result['sent_due']} due-date reminder(s). "
            f"Skipped {result['skipped_no_email']} shop(s) with no owner email."
        )
        for error in result["errors"]:
            self.stderr.write(error)
        if result["failed"]:
            raise CommandError(
                f"{result['failed']} reminder(s) failed to send and were not recorded, "
                "so the next run can retry them."
            )
