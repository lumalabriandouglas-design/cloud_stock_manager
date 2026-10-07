"""Debt book: customers who owe the shop, and suppliers the shop owes."""

from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import DecimalField, Sum, Value
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .models import ActivityLog, Debt, DebtPayment
from .views import get_profile, log_activity, perm_context, require_perm

TABS = {Debt.OWED_TO_SHOP: "Owed to shop", Debt.SHOP_OWES: "Shop owes"}
ZERO = Value(Decimal("0"), output_field=DecimalField(max_digits=14, decimal_places=2))


def _money(raw) -> Decimal | None:
    try:
        value = Decimal(str(raw or "").replace(",", "").strip())
    except InvalidOperation:
        return None
    if value <= 0 or value.as_tuple().exponent < -2 or value >= Decimal("10000000000"):
        return None
    return value


def _date(raw) -> date | None:
    raw = (raw or "").strip()
    if not raw:
        return None
    try:
        return date.fromisoformat(raw)
    except ValueError:
        return None


def annotated(company, direction=None):
    qs = Debt.objects.filter(company=company)
    if direction:
        qs = qs.filter(direction=direction)
    return qs.annotate(_paid=Coalesce(Sum("payments__amount"), ZERO))


def debt_totals(company) -> dict:
    """Unpaid totals per direction plus overdue counts, for the Debts page and Reports."""
    today = timezone.localdate()
    out = {}
    for direction in TABS:
        open_debts = [d for d in annotated(company, direction).filter(settled_at__isnull=True)]
        out[direction] = {
            "unpaid": sum((d.remaining for d in open_debts), Decimal("0")),
            "open": len(open_debts),
            "overdue": sum(1 for d in open_debts if d.due_date and d.due_date < today),
            "overdue_amount": sum((d.remaining for d in open_debts if d.due_date and d.due_date < today), Decimal("0")),
        }
    return out


def debt_collected(company, since) -> Decimal:
    """Customer ('Owed to shop') payments received on or after `since`, by payment date.

    Supplier payments ('Shop owes') are money going out and never count as revenue.
    """
    since_date = since.date() if hasattr(since, "date") else since
    total = DebtPayment.objects.filter(
        debt__company=company, debt__direction=Debt.OWED_TO_SHOP, paid_on__gte=since_date,
    ).aggregate(t=Sum("amount"))["t"]
    return total or Decimal("0")


def _ctx(request, profile, **extra):
    return {"company": profile.company, "profile": profile, **perm_context(profile), **extra}


@login_required
def debt_list(request):
    profile = get_profile(request)
    if profile is None:
        return redirect("setup_company")
    tab = request.GET.get("tab", Debt.OWED_TO_SHOP)
    if tab not in TABS:
        tab = Debt.OWED_TO_SHOP
    show_settled = request.GET.get("settled") == "1"
    qs = annotated(profile.company, tab)
    if not show_settled:
        qs = qs.filter(settled_at__isnull=True)
    debts = sorted(qs, key=lambda d: (d.is_settled, not d.is_overdue, d.due_date or date.max, d.party_name.lower()))
    return render(request, "inventory/debts.html", _ctx(
        request, profile, tab=tab, tab_label=TABS[tab], tabs=TABS, debts=debts,
        totals=debt_totals(profile.company), show_settled=show_settled,
    ))


@login_required
@require_perm("can_manage_stock")
def debt_add(request):
    profile = get_profile(request)
    direction = request.POST.get("direction") or request.GET.get("tab") or Debt.OWED_TO_SHOP
    if direction not in TABS:
        direction = Debt.OWED_TO_SHOP
    form = {"direction": direction}
    if request.method == "POST":
        form = {k: request.POST.get(k, "").strip() for k in ("party_name", "party_phone", "amount", "notes", "due_date")}
        form["direction"] = direction
        amount = _money(form["amount"])
        due = _date(form["due_date"])
        errors = []
        if not form["party_name"]:
            errors.append("Enter a name.")
        if amount is None:
            errors.append("Enter an amount above 0.")
        if form["due_date"] and due is None:
            errors.append("Enter a valid due date.")
        if not errors:
            debt = Debt.objects.create(
                company=profile.company, direction=direction, party_name=form["party_name"][:120],
                party_phone=form["party_phone"][:30], amount=amount, notes=form["notes"][:255],
                due_date=due, created_by=request.user,
            )
            log_activity(profile.company, request.user, ActivityLog.ACTION_OTHER,
                         f"Debt added: {debt.party_name} ({TABS[direction].lower()})")
            messages.success(request, f"Added {debt.party_name}.")
            return redirect(f"/debts/?tab={direction}")
        for e in errors:
            messages.error(request, e)
    return render(request, "inventory/debt_form.html", _ctx(request, profile, form=form, tabs=TABS))


@login_required
def debt_detail(request, debt_id):
    profile = get_profile(request)
    if profile is None:
        return redirect("setup_company")
    debt = get_object_or_404(Debt, id=debt_id, company=profile.company)
    return render(request, "inventory/debt_detail.html", _ctx(
        request, profile, debt=debt, payments=debt.payments.select_related("recorded_by"),
        tab_label=TABS[debt.direction], today=timezone.localdate(),
    ))


@login_required
@require_perm("can_manage_stock")
@require_POST
def debt_pay(request, debt_id):
    profile = get_profile(request)
    debt = get_object_or_404(Debt, id=debt_id, company=profile.company)
    amount = _money(request.POST.get("amount"))
    paid_on = _date(request.POST.get("paid_on")) or timezone.localdate()
    if debt.is_settled:
        messages.error(request, "This debt is already settled.")
    elif amount is None:
        messages.error(request, "Enter a payment above 0.")
    elif amount > debt.remaining:
        messages.error(request, f"That is more than the balance ({debt.remaining:,.0f}).")
    else:
        DebtPayment.objects.create(debt=debt, amount=amount, paid_on=paid_on,
                                   note=request.POST.get("note", "").strip()[:255], recorded_by=request.user)
        debt.refresh_settled()
        log_activity(profile.company, request.user, ActivityLog.ACTION_OTHER,
                     f"Debt payment: {debt.party_name} {amount:,.0f}")
        messages.success(request, "Settled in full." if debt.is_settled else f"Payment saved. {debt.remaining:,.0f} left.")
    return redirect("debt_detail", debt_id=debt.id)


@login_required
@require_POST
def debt_delete(request, debt_id):
    profile = get_profile(request)
    if profile is None or not profile.is_owner:
        messages.error(request, "Only the owner can delete a debt.")
        return redirect("debts")
    debt = get_object_or_404(Debt, id=debt_id, company=profile.company)
    direction = debt.direction
    log_activity(profile.company, request.user, ActivityLog.ACTION_OTHER, f"Debt deleted: {debt.party_name}")
    debt.delete()
    messages.success(request, "Debt deleted.")
    return redirect(f"/debts/?tab={direction}")
