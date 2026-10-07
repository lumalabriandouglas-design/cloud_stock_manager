"""Local/test only: create a demo shop with sample debts.

    python manage.py seed_debt_demo

Refuses to run unless DEBUG is on or --force is given, so it can't touch production by accident.
"""

from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from inventory.models import Company, Debt, DebtPayment, Item, Sale, Subscription, UserProfile


class Command(BaseCommand):
    help = "Seed a demo business (owner: demo_owner / demo-pass-123) with customer and supplier debts."

    def add_arguments(self, parser):
        parser.add_argument("--force", action="store_true")

    def handle(self, *args, **opts):
        if not settings.DEBUG and not opts["force"]:
            raise CommandError("Refusing to seed outside DEBUG. Use --force on a local/test database only.")
        today = timezone.localdate()
        Company.objects.filter(name="Demo Duka").delete()
        User.objects.filter(username="demo_owner").delete()
        company = Company.objects.create(name="Demo Duka")
        Subscription.start_trial(company)
        owner = User.objects.create_user("demo_owner", "demo@example.com", "demo-pass-123")
        UserProfile.objects.create(user=owner, company=company, role=UserProfile.ROLE_OWNER)

        sugar = Item.objects.create(company=company, name="Sugar 1kg", buy_price=4200, sell_price=5000, quantity_in_stock=40)
        soap = Item.objects.create(company=company, name="Bar soap", buy_price=2500, sell_price=3500, quantity_in_stock=60)
        Sale.objects.create(company=company, item=sugar, quantity_sold=6, sell_price=5000)
        Sale.objects.create(company=company, item=soap, quantity_sold=10, sell_price=3500)

        def add(direction, name, phone, amount, due_in, notes, payments=()):
            d = Debt.objects.create(company=company, direction=direction, party_name=name, party_phone=phone,
                                    amount=Decimal(amount), notes=notes, created_by=owner,
                                    due_date=today + timedelta(days=due_in) if due_in is not None else None)
            for amt, ago in payments:
                DebtPayment.objects.create(debt=d, amount=Decimal(amt), paid_on=today - timedelta(days=ago), note="Cash", recorded_by=owner)
            d.refresh_settled()

        O, S = Debt.OWED_TO_SHOP, Debt.SHOP_OWES
        add(O, "Mama Grace", "0772 111222", 45000, 5, "Sugar and soap on credit", [(20000, 3)])
        add(O, "Okello John", "0701 333444", 30000, -4, "2 bags of sugar")  # overdue
        add(O, "Nakato Sarah", "0756 555666", 18000, 12, "Cooking oil")
        add(O, "Ssali Peter", "", 60000, 20, "School term supplies", [(15000, 6), (10000, 1)])
        add(S, "Kakira Sugar Distributors", "0414 777888", 1200000, 9, "Weekly sugar stock", [(400000, 2)])
        add(S, "Mukwano Soap Depot", "0392 999000", 350000, 14, "Soap and detergent")
        add(S, "Bodaboda delivery (Musa)", "0780 121212", 40000, -2, "Deliveries for September")  # overdue

        self.stdout.write(self.style.SUCCESS("Seeded Demo Duka. Log in as demo_owner / demo-pass-123"))
