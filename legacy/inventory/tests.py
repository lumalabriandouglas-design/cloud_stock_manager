import os
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .debts import debt_totals
from .models import Company, Debt, DebtPayment, Subscription, UserProfile


def make_shop(name, username, role=UserProfile.ROLE_OWNER, **perms):
    company = Company.objects.create(name=name)
    Subscription.start_trial(company)
    user = User.objects.create_user(username, f"{username}@x.test", "pw-12345!")
    UserProfile.objects.create(user=user, company=company, role=role, **perms)
    return company, user


class DebtModelTests(TestCase):
    def setUp(self):
        self.company, self.owner = make_shop("Shop A", "owner_a")

    def test_remaining_and_settle_on_zero(self):
        d = Debt.objects.create(company=self.company, direction=Debt.OWED_TO_SHOP, party_name="Grace", amount=Decimal("100"))
        DebtPayment.objects.create(debt=d, amount=Decimal("40"))
        d.refresh_settled()
        self.assertEqual(d.remaining, Decimal("60"))
        self.assertFalse(d.is_settled)
        DebtPayment.objects.create(debt=d, amount=Decimal("60"))
        d.refresh_settled()
        self.assertEqual(d.remaining, Decimal("0"))
        self.assertTrue(d.is_settled)

    def test_overdue(self):
        d = Debt.objects.create(company=self.company, direction=Debt.SHOP_OWES, party_name="Supplier",
                                amount=Decimal("10"), due_date=timezone.localdate() - timedelta(days=1))
        self.assertTrue(d.is_overdue)

    def test_totals_per_direction(self):
        Debt.objects.create(company=self.company, direction=Debt.OWED_TO_SHOP, party_name="A", amount=Decimal("100"))
        s = Debt.objects.create(company=self.company, direction=Debt.SHOP_OWES, party_name="B", amount=Decimal("500"),
                                due_date=timezone.localdate() - timedelta(days=3))
        DebtPayment.objects.create(debt=s, amount=Decimal("200"))
        t = debt_totals(self.company)
        self.assertEqual(t[Debt.OWED_TO_SHOP]["unpaid"], Decimal("100"))
        self.assertEqual(t[Debt.SHOP_OWES]["unpaid"], Decimal("300"))
        self.assertEqual(t[Debt.SHOP_OWES]["overdue"], 1)


class DebtViewTests(TestCase):
    def setUp(self):
        self.company, self.owner = make_shop("Shop A", "owner_a")
        self.other_company, self.other = make_shop("Shop B", "owner_b")
        self.debt = Debt.objects.create(company=self.company, direction=Debt.OWED_TO_SHOP, party_name="Grace", amount=Decimal("100"))

    def test_add_debt(self):
        self.client.force_login(self.owner)
        r = self.client.post(reverse("debt_add"), {"direction": Debt.SHOP_OWES, "party_name": "Kakira", "amount": "1,200,000", "due_date": "2026-12-01"})
        self.assertEqual(r.status_code, 302)
        d = Debt.objects.get(party_name="Kakira")
        self.assertEqual(d.amount, Decimal("1200000"))
        self.assertEqual(d.direction, Debt.SHOP_OWES)

    def test_add_debt_rejects_bad_amount(self):
        self.client.force_login(self.owner)
        self.client.post(reverse("debt_add"), {"direction": Debt.OWED_TO_SHOP, "party_name": "X", "amount": "-5"})
        self.assertFalse(Debt.objects.filter(party_name="X").exists())

    def test_part_payment_then_settle(self):
        self.client.force_login(self.owner)
        self.client.post(reverse("debt_pay", args=[self.debt.id]), {"amount": "30"})
        self.debt.refresh_from_db()
        self.assertEqual(self.debt.remaining, Decimal("70"))
        self.client.post(reverse("debt_pay", args=[self.debt.id]), {"amount": "70"})
        self.debt.refresh_from_db()
        self.assertTrue(self.debt.is_settled)

    def test_overpayment_rejected(self):
        self.client.force_login(self.owner)
        self.client.post(reverse("debt_pay", args=[self.debt.id]), {"amount": "150"})
        self.assertEqual(self.debt.payments.count(), 0)

    def test_list_tabs(self):
        self.client.force_login(self.owner)
        r = self.client.get(reverse("debts") + "?tab=owed_to_shop")
        self.assertContains(r, "Grace")
        r = self.client.get(reverse("debts") + "?tab=shop_owes")
        self.assertNotContains(r, "Grace")

    def test_other_business_cannot_see_or_pay(self):
        self.client.force_login(self.other)
        self.assertNotContains(self.client.get(reverse("debts")), "Grace")
        self.assertEqual(self.client.get(reverse("debt_detail", args=[self.debt.id])).status_code, 404)
        self.assertEqual(self.client.post(reverse("debt_pay", args=[self.debt.id]), {"amount": "10"}).status_code, 404)
        self.assertEqual(self.debt.payments.count(), 0)

    def test_anonymous_redirected(self):
        r = self.client.get(reverse("debts"))
        self.assertEqual(r.status_code, 302)

    def test_staff_can_view_and_pay_but_not_delete(self):
        staff = User.objects.create_user("staff_a", "s@x.test", "pw-12345!")
        UserProfile.objects.create(user=staff, company=self.company, role=UserProfile.ROLE_STAFF)
        self.client.force_login(staff)
        self.assertContains(self.client.get(reverse("debts")), "Grace")
        self.client.post(reverse("debt_pay", args=[self.debt.id]), {"amount": "10"})
        self.assertEqual(self.debt.payments.count(), 1)
        self.client.post(reverse("debt_delete", args=[self.debt.id]))
        self.assertTrue(Debt.objects.filter(id=self.debt.id).exists())

    def test_staff_without_stock_perm_cannot_add(self):
        staff = User.objects.create_user("viewer", "v@x.test", "pw-12345!")
        UserProfile.objects.create(user=staff, company=self.company, role=UserProfile.ROLE_STAFF, can_manage_stock=False)
        self.client.force_login(staff)
        self.client.post(reverse("debt_add"), {"direction": Debt.OWED_TO_SHOP, "party_name": "Y", "amount": "5"})
        self.assertFalse(Debt.objects.filter(party_name="Y").exists())

    def test_owner_can_delete(self):
        self.client.force_login(self.owner)
        self.client.post(reverse("debt_delete", args=[self.debt.id]))
        self.assertFalse(Debt.objects.filter(id=self.debt.id).exists())

    def test_reports_show_totals(self):
        self.client.force_login(self.owner)
        r = self.client.get(reverse("sales_report"))
        self.assertContains(r, "Customers owe shop")
        self.assertContains(r, "Shop owes suppliers")


class DebtCollectedRevenueTests(TestCase):
    def setUp(self):
        from .models import Item, Sale
        self.company, self.owner = make_shop("Shop R", "owner_r")
        item = Item.objects.create(company=self.company, name="Sugar", buy_price=4000, sell_price=5000, quantity_in_stock=10)
        Sale.objects.create(company=self.company, item=item, quantity_sold=2, sell_price=5000)  # 10,000 sales
        today = timezone.localdate()
        cust = Debt.objects.create(company=self.company, direction=Debt.OWED_TO_SHOP, party_name="Grace", amount=Decimal("50000"))
        DebtPayment.objects.create(debt=cust, amount=Decimal("20000"), paid_on=today - timedelta(days=2))
        DebtPayment.objects.create(debt=cust, amount=Decimal("7000"), paid_on=today - timedelta(days=20))
        supp = Debt.objects.create(company=self.company, direction=Debt.SHOP_OWES, party_name="Kakira", amount=Decimal("900000"))
        DebtPayment.objects.create(debt=supp, amount=Decimal("300000"), paid_on=today - timedelta(days=1))
        other, _ = make_shop("Shop Other", "owner_o")
        od = Debt.objects.create(company=other, direction=Debt.OWED_TO_SHOP, party_name="X", amount=Decimal("99999"))
        DebtPayment.objects.create(debt=od, amount=Decimal("99999"), paid_on=today)
        self.client.force_login(self.owner)

    def test_collected_counts_customer_payments_in_period(self):
        r = self.client.get(reverse("sales_report") + "?days=30")
        self.assertEqual(r.context["sales_revenue"], Decimal("10000"))
        self.assertEqual(r.context["debt_collected"], Decimal("27000"))
        self.assertEqual(r.context["total_revenue"], Decimal("37000"))
        self.assertContains(r, "Debt collected")

    def test_period_filters_by_payment_date(self):
        r = self.client.get(reverse("sales_report") + "?days=7")
        self.assertEqual(r.context["debt_collected"], Decimal("20000"))
        self.assertEqual(r.context["total_revenue"], Decimal("30000"))

    def test_supplier_payments_never_revenue(self):
        r = self.client.get(reverse("sales_report") + "?days=365")
        self.assertEqual(r.context["debt_collected"], Decimal("27000"))

    def test_profit_not_double_counted(self):
        r = self.client.get(reverse("sales_report") + "?days=30")
        self.assertEqual(r.context["total_profit"], Decimal("2000"))

    def test_debt_section_at_bottom(self):
        html = self.client.get(reverse("sales_report")).content.decode()
        self.assertGreater(html.index("Customers owe shop"), html.index("Transactions"))


AJAX = {"HTTP_X_REQUESTED_WITH": "XMLHttpRequest"}


class NoReloadSaveTests(TestCase):
    def setUp(self):
        from .models import Item
        self.company, self.owner = make_shop("Shop N", "owner_n")
        self.item = Item.objects.create(company=self.company, name="Soap", buy_price=2500, sell_price=3500, quantity_in_stock=10)
        self.client.force_login(self.owner)

    def test_record_sale_json(self):
        r = self.client.post(reverse("record_sale"), {"item_id": self.item.id, "quantity": "2"}, **AJAX)
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertTrue(data["ok"])
        self.assertEqual(data["redirect"], reverse("sell"))
        self.assertIn("Sold", data["messages"][0]["text"])
        self.item.refresh_from_db()
        self.assertEqual(self.item.quantity_in_stock, 8)

    def test_record_sale_error_json(self):
        r = self.client.post(reverse("record_sale"), {"item_id": self.item.id, "quantity": "99"}, **AJAX)
        self.assertEqual(r.status_code, 400)
        self.assertFalse(r.json()["ok"])
        self.assertEqual(r.json()["messages"][0]["level"], "error")

    def test_without_js_still_redirects(self):
        r = self.client.post(reverse("record_sale"), {"item_id": self.item.id, "quantity": "1"})
        self.assertEqual(r.status_code, 302)

    def test_edit_item_json(self):
        r = self.client.post(reverse("edit_item", args=[self.item.id]), {
            "name": "Bar soap", "unit": "pcs", "buy_price": "2600", "sell_price": "3600", "reorder_level": "2", "qty_adjust": "5"}, **AJAX)
        self.assertTrue(r.json()["ok"])
        self.item.refresh_from_db()
        self.assertEqual(self.item.name.lower(), "bar soap")
        self.assertEqual(self.item.quantity_in_stock, 15)

    def test_delete_item_json(self):
        r = self.client.post(reverse("delete_item", args=[self.item.id]), **AJAX)
        self.assertTrue(r.json()["ok"])
        self.assertEqual(r.json()["redirect"], reverse("dashboard"))

    def test_stock_in_json(self):
        r = self.client.post(reverse("record_stock_in"), {"item_id": self.item.id, "item_name": "Soap", "quantity": "3", "unit": "pcs"}, **AJAX)
        self.assertTrue(r.json()["ok"])
        self.item.refresh_from_db()
        self.assertEqual(self.item.quantity_in_stock, 13)

    def test_debt_payment_json(self):
        d = Debt.objects.create(company=self.company, direction=Debt.OWED_TO_SHOP, party_name="G", amount=Decimal("100"))
        r = self.client.post(reverse("debt_pay", args=[d.id]), {"amount": "40"}, **AJAX)
        self.assertTrue(r.json()["ok"])
        r = self.client.post(reverse("debt_pay", args=[d.id]), {"amount": "500"}, **AJAX)
        self.assertEqual(r.status_code, 400)

    def test_permission_still_enforced(self):
        staff = User.objects.create_user("nostock", "n@x.test", "pw-12345!")
        UserProfile.objects.create(user=staff, company=self.company, role=UserProfile.ROLE_STAFF, can_manage_stock=False)
        self.client.force_login(staff)
        r = self.client.post(reverse("record_sale"), {"item_id": self.item.id, "quantity": "1"}, **AJAX)
        self.assertFalse(r.json()["ok"])
        self.item.refresh_from_db()
        self.assertEqual(self.item.quantity_in_stock, 10)

    def test_other_shop_gets_404(self):
        _, other = make_shop("Shop Z", "owner_z")
        self.client.force_login(other)
        r = self.client.post(reverse("edit_item", args=[self.item.id]), {"name": "x"}, **AJAX)
        self.assertEqual(r.status_code, 404)

    def test_csrf_enforced(self):
        from django.test import Client
        c = Client(enforce_csrf_checks=True)
        c.force_login(self.owner)
        r = c.post(reverse("record_sale"), {"item_id": self.item.id, "quantity": "1"}, **AJAX)
        self.assertEqual(r.status_code, 403)

    def test_pages_have_live_regions(self):
        self.assertContains(self.client.get(reverse("sell")), 'id="sell-today" data-live')
        self.assertContains(self.client.get(reverse("dashboard")), 'id="dash-inventory" data-live')


def local_day(when):
    from django.utils.dateformat import format as date_format
    return date_format(timezone.localtime(when), "d M Y")


class SubscriptionDueTests(TestCase):
    def test_trial_is_due_at_trial_end(self):
        company, _ = make_shop("Trial Shop", "trial_owner")
        sub = company.sub
        self.assertEqual(sub.due_at, sub.trial_ends_at)
        self.assertEqual(sub.due_state, "ok")

    def test_paid_period_replaces_trial_end(self):
        company, _ = make_shop("Paid Shop", "paid_owner")
        sub = company.sub
        sub.activate_for_month()
        sub.refresh_from_db()
        self.assertEqual(sub.due_at, sub.current_period_end)
        self.assertGreater(sub.current_period_end, sub.trial_ends_at)

    def test_pending_without_paid_period_keeps_trial_end(self):
        company, _ = make_shop("Pending Shop", "pending_owner")
        sub = company.sub
        sub.claim_payment(phone="0700", tx_id="abc")
        sub.refresh_from_db()
        self.assertEqual(sub.status, Subscription.STATUS_PENDING)
        self.assertEqual(sub.due_at, sub.trial_ends_at)

    def test_active_without_dates_has_no_due_date(self):
        company, _ = make_shop("Open Shop", "open_owner")
        sub = company.sub
        sub.status = Subscription.STATUS_ACTIVE
        sub.trial_ends_at = None
        sub.current_period_end = None
        sub.save()
        self.assertIsNone(sub.due_at)
        self.assertEqual(sub.due_state, "none")


class PlatformDueDateTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser("root", "root@x.test", "pw-12345!")
        self.client.force_login(self.admin)
        self.trial, _ = make_shop("Kampala Grocers", "kg_owner")
        self.trial.sub.trial_ends_at = timezone.now() + timedelta(days=2)
        self.trial.sub.save()
        self.overdue, _ = make_shop("Old Duka", "old_owner")
        self.overdue.sub.status = Subscription.STATUS_ACTIVE
        self.overdue.sub.current_period_end = timezone.now() - timedelta(days=1)
        self.overdue.sub.save()
        self.blank = Company.objects.create(name="No Plan")
        self.today_shop, _ = make_shop("Closes Today", "today_owner")
        later_today = timezone.now() + timedelta(minutes=30)
        if timezone.localtime(later_today).date() != timezone.localdate():
            later_today = timezone.now() + timedelta(seconds=30)
        self.today_shop.sub.trial_ends_at = later_today
        self.today_shop.sub.save()

    def test_each_company_shows_its_due_date(self):
        response = self.client.get(reverse("platform_admin"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Due date")
        self.assertContains(response, "Kampala Grocers")
        self.assertContains(response, local_day(self.trial.sub.trial_ends_at))
        self.assertContains(response, "Due soon")
        self.assertContains(response, local_day(self.overdue.sub.current_period_end))
        self.assertContains(response, "Overdue")
        self.assertContains(response, "Due today")
        self.assertContains(response, "No due date")
        self.assertContains(response, "No Plan")

    def test_kampala_date_not_utc_date(self):
        from datetime import datetime, timezone as dt_timezone
        company, _ = make_shop("Timezone Shop", "tz_owner")
        # 22:00 UTC is 01:00 the next morning in Africa/Kampala.
        company.sub.trial_ends_at = datetime(2026, 12, 1, 22, 0, tzinfo=dt_timezone.utc)
        company.sub.save()
        response = self.client.get(reverse("platform_admin"))
        self.assertContains(response, "02 Dec 2026")
        self.assertNotContains(response, "01 Dec 2026")

    def test_staff_cannot_open_platform(self):
        _, owner = make_shop("Staff Shop", "staff_shop_owner")
        self.client.force_login(owner)
        self.assertEqual(self.client.get(reverse("platform_admin")).status_code, 302)


class SubscriptionReminderTests(TestCase):
    def setUp(self):
        from django.test.utils import override_settings
        self.email_override = override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
        self.email_override.enable()
        self._old_host = os.environ.get("EMAIL_HOST")
        os.environ["EMAIL_HOST"] = "smtp.test"
        self.company, self.owner = make_shop("Acme Duka", "acme_owner")
        self.owner.email = "owner@acme.test"
        self.owner.save()
        self.sub = self.company.sub

    def tearDown(self):
        self.email_override.disable()
        if self._old_host is None:
            os.environ.pop("EMAIL_HOST", None)
        else:
            os.environ["EMAIL_HOST"] = self._old_host

    def _due_in(self, days):
        self.sub.trial_ends_at = timezone.now() + timedelta(days=days)
        self.sub.status = Subscription.STATUS_TRIAL
        self.sub.save()

    def test_advance_email_once_then_due_date_email_once(self):
        from django.core import mail
        from django.core.management import call_command
        self._due_in(3)
        call_command("send_subscription_reminders")
        self.assertEqual(len(mail.outbox), 1)
        message = mail.outbox[0]
        self.assertEqual(message.to, ["owner@acme.test"])
        self.assertIn("Acme Duka", message.subject)
        self.assertIn("free trial", message.body)
        self.assertIn(local_day(self.sub.trial_ends_at), message.body)
        self.assertIn("ends on", message.body)
        self.assertNotIn("15,000", message.body)
        self.assertNotIn("0781", message.body)
        call_command("send_subscription_reminders")
        self.assertEqual(len(mail.outbox), 1)
        self.sub.refresh_from_db()
        self.assertIsNotNone(self.sub.reminded_upcoming_for)

        self._due_in(0)
        call_command("send_subscription_reminders")
        self.assertEqual(len(mail.outbox), 2)
        self.assertIn("ends today", mail.outbox[1].subject)
        self.assertIn("Acme Duka", mail.outbox[1].body)
        call_command("send_subscription_reminders")
        self.assertEqual(len(mail.outbox), 2)

    def test_outside_the_window_and_already_overdue_are_quiet(self):
        from django.core import mail
        from inventory.reminders import send_subscription_reminders
        self._due_in(4)
        send_subscription_reminders()
        self._due_in(-2)
        send_subscription_reminders()
        self.assertEqual(len(mail.outbox), 0)

    def test_skips_missing_email_and_staff_then_sends_when_owner_email_exists(self):
        from django.core import mail
        from inventory.reminders import send_subscription_reminders
        self.owner.email = ""
        self.owner.save()
        User.objects.create_user("acme_staff", "staff@acme.test", "pw-12345!")
        UserProfile.objects.create(user=User.objects.get(username="acme_staff"), company=self.company, role=UserProfile.ROLE_STAFF)
        self._due_in(1)
        result = send_subscription_reminders()
        self.assertEqual(result["skipped_no_email"], 1)
        self.assertEqual(len(mail.outbox), 0)
        self.sub.refresh_from_db()
        self.assertIsNone(self.sub.reminded_upcoming_for)
        self.owner.email = "owner@acme.test"
        self.owner.save()
        send_subscription_reminders()
        self.assertEqual(mail.outbox[0].to, ["owner@acme.test"])

    def test_two_owners_one_email_and_suspended_is_skipped(self):
        from django.core import mail
        from inventory.reminders import send_subscription_reminders
        second = User.objects.create_user("acme_owner_2", "second@acme.test", "pw-12345!")
        UserProfile.objects.create(user=second, company=self.company, role=UserProfile.ROLE_OWNER)
        self._due_in(2)
        send_subscription_reminders()
        self.assertEqual(len(mail.outbox), 1)
        self.assertCountEqual(mail.outbox[0].to, ["owner@acme.test", "second@acme.test"])
        mail.outbox.clear()
        suspended, user = make_shop("Paused Shop", "paused_owner")
        user.email = "paused@x.test"
        user.save()
        suspended.sub.status = Subscription.STATUS_SUSPENDED
        suspended.sub.current_period_end = timezone.now() + timedelta(days=1)
        suspended.sub.save()
        self.sub.status = Subscription.STATUS_ACTIVE
        self.sub.current_period_end = timezone.now() + timedelta(days=20)
        self.sub.save()
        send_subscription_reminders()
        self.assertEqual(len(mail.outbox), 0)

    def test_new_period_can_be_reminded_again(self):
        from django.core import mail
        from inventory.reminders import send_subscription_reminders
        self.sub.status = Subscription.STATUS_ACTIVE
        self.sub.current_period_end = timezone.now() + timedelta(days=2)
        self.sub.save()
        send_subscription_reminders()
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("subscription", mail.outbox[0].body)
        self.sub.current_period_end = timezone.now() + timedelta(days=2, hours=1)
        self.sub.save()
        send_subscription_reminders()
        self.assertEqual(len(mail.outbox), 2)

    def test_failed_send_is_not_recorded(self):
        from unittest.mock import patch
        from inventory.reminders import send_subscription_reminders
        self._due_in(2)
        with patch("inventory.reminders.send_mail", side_effect=OSError("smtp down")):
            result = send_subscription_reminders()
        self.assertEqual(result["failed"], 1)
        self.sub.refresh_from_db()
        self.assertIsNone(self.sub.reminded_upcoming_for)

    def test_without_email_host_nothing_is_marked(self):
        from django.core.management.base import CommandError
        from django.core.management import call_command
        from inventory.reminders import send_subscription_reminders
        os.environ.pop("EMAIL_HOST", None)
        self._due_in(1)
        result = send_subscription_reminders()
        self.assertTrue(result["disabled"])
        self.sub.refresh_from_db()
        self.assertIsNone(self.sub.reminded_upcoming_for)
        with self.assertRaises(CommandError):
            call_command("send_subscription_reminders")

    def test_dry_run_does_not_send_or_record(self):
        from io import StringIO
        from django.core import mail
        from django.core.management import call_command
        os.environ.pop("EMAIL_HOST", None)
        self._due_in(1)
        out = StringIO()
        call_command("send_subscription_reminders", "--dry-run", stdout=out)
        self.assertIn("owner@acme.test", out.getvalue())
        self.assertEqual(len(mail.outbox), 0)
        self.sub.refresh_from_db()
        self.assertIsNone(self.sub.reminded_upcoming_for)
