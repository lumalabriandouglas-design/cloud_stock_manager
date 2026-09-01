from django.core.management.base import BaseCommand
from inventory.models import Company


class Command(BaseCommand):
    help = "Delete ALL companies and related data (items, sales, stock, profiles). Use with caution!"

    def add_arguments(self, parser):
        parser.add_argument(
            "--no-input",
            action="store_true",
            help="Skip confirmation prompt",
        )

    def handle(self, *args, **options):
        count = Company.objects.count()

        if count == 0:
            self.stdout.write(self.style.WARNING("No companies found. Nothing to delete."))
            return

        if not options["no_input"]:
            self.stdout.write(
                self.style.WARNING(
                    f"This will permanently delete {count} company/companies and ALL related data "
                    f"(items, sales, stock entries, user profiles)."
                )
            )
            confirm = input("Type 'yes' to continue: ")
            if confirm.lower() != "yes":
                self.stdout.write(self.style.ERROR("Aborted."))
                return

        Company.objects.all().delete()
        self.stdout.write(
            self.style.SUCCESS(f"Successfully deleted {count} company/companies and all related data.")
        )
