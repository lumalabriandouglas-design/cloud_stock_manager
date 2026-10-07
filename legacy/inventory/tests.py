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
