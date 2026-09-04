"""Features ported from the Node shop: Google login, reset codes, invites, today."""

from __future__ import annotations

import hashlib
import json
import os
import secrets
import urllib.parse
import urllib.request
from datetime import timedelta

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .models import (
    ActivityLog,
    Company,
    Item,
    PasswordResetCode,
    Sale,
    StaffInvite,
    UserProfile,
)
from .views import get_profile, log_activity, perm_context, require_perm


def _hash_code(code: str) -> str:
    return hashlib.sha256(code.encode()).hexdigest()


def apply_invite(user: User) -> bool:
    email = (user.email or "").strip().lower()
    if not email:
        return False
    invite = StaffInvite.objects.filter(email=email).select_related("company").first()
    if not invite or hasattr(user, "profile"):
        return False
    UserProfile.objects.create(
        user=user,
        company=invite.company,
        role=invite.role,
        can_manage_stock=invite.can_manage_stock,
        can_edit_items=invite.can_edit_items,
        can_view_reports=invite.can_view_reports,
        can_manage_categories=invite.can_manage_categories,
        can_manage_team=invite.can_manage_team,
    )
    invite.delete()
    return True


def google_enabled() -> bool:
    return bool(os.getenv("GOOGLE_CLIENT_ID") and os.getenv("GOOGLE_CLIENT_SECRET"))


def google_start(request):
    client_id = os.getenv("GOOGLE_CLIENT_ID", "")
    if not client_id:
        messages.error(request, "Google sign-in is not configured yet.")
        return redirect("login")
    redirect_uri = request.build_absolute_uri("/accounts/google/callback/")
    params = urllib.parse.urlencode(
        {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": "openid email profile",
            "prompt": "select_account",
        }
    )
    return redirect(f"https://accounts.google.com/o/oauth2/v2/auth?{params}")


def google_callback(request):
    code = request.GET.get("code", "")
    if not code:
        messages.error(request, "Google sign-in was cancelled.")
        return redirect("login")
    client_id = os.getenv("GOOGLE_CLIENT_ID", "")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET", "")
    redirect_uri = request.build_absolute_uri("/accounts/google/callback/")
    token_body = urllib.parse.urlencode(
        {
            "code": code,
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
        }
    ).encode()
    try:
        with urllib.request.urlopen(
            urllib.request.Request(
                "https://oauth2.googleapis.com/token",
                data=token_body,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            ),
            timeout=15,
        ) as resp:
            token = json.loads(resp.read().decode())
        access = token.get("access_token")
        if not access:
            raise RuntimeError("no access token")
        with urllib.request.urlopen(
            urllib.request.Request(
                "https://www.googleapis.com/oauth2/v2/userinfo",
                headers={"Authorization": f"Bearer {access}"},
            ),
            timeout=15,
        ) as resp:
            info = json.loads(resp.read().decode())
    except Exception:
        messages.error(request, "Google sign-in failed. Try email and password.")
        return redirect("login")

    email = (info.get("email") or "").strip().lower()
    if not email:
        messages.error(request, "Google did not share an email address.")
        return redirect("login")
    name = (info.get("name") or email.split("@")[0]).strip()
    user = User.objects.filter(email__iexact=email).first()
    if user is None:
        base = email.split("@")[0][:20]
        username = base
        n = 1
        while User.objects.filter(username__iexact=username).exists():
            n += 1
            username = f"{base}{n}"
        user = User.objects.create_user(username=username, email=email, first_name=name[:30])
        user.set_unusable_password()
        user.save()
    apply_invite(user)
    login(request, user)
    if hasattr(user, "profile"):
        messages.success(request, f"Signed in with Google as {email}.")
        return redirect("dashboard")
    messages.info(request, "Create your shop to finish signing up.")
    return redirect("setup_company")


def password_reset_request(request):
    preview_code = None
    if request.method == "POST":
        ident = request.POST.get("identifier", "").strip()
        user = (
            User.objects.filter(email__iexact=ident).first()
            if "@" in ident
            else User.objects.filter(username__iexact=ident).first()
        )
        if user:
            PasswordResetCode.objects.filter(user=user, used=False).update(used=True)
            code = f"{secrets.randbelow(900000) + 100000}"
            PasswordResetCode.objects.create(
                user=user,
                code_hash=_hash_code(code),
                expires_at=timezone.now() + timedelta(minutes=15),
            )
            sent = False
            if os.getenv("EMAIL_HOST") and user.email:
                try:
                    send_mail(
                        "Cloud Stock Manager reset code",
                        f"Your reset code is {code}. It expires in 15 minutes.",
                        None,
                        [user.email],
                        fail_silently=True,
                    )
                    sent = True
                except Exception:
                    sent = False
            if not sent:
                preview_code = code
        messages.success(request, "If that account exists, a 6-digit code is ready.")
        return render(
            request,
            "inventory/password_reset.html",
            {"mode": "confirm", "identifier": ident, "preview_code": preview_code},
        )
    return render(request, "inventory/password_reset.html", {"mode": "request"})


def password_reset_confirm(request):
    if request.method != "POST":
        return redirect("password_reset_request")
    ident = request.POST.get("identifier", "").strip()
    code = request.POST.get("code", "").strip()
    password = request.POST.get("password", "")
    confirm = request.POST.get("password2", "")
    if password != confirm or len(password) < 6:
        messages.error(request, "Passwords must match and be at least 6 characters.")
        return render(request, "inventory/password_reset.html", {"mode": "confirm", "identifier": ident})
    user = (
        User.objects.filter(email__iexact=ident).first()
        if "@" in ident
        else User.objects.filter(username__iexact=ident).first()
    )
    row = None
    if user:
        row = (
            PasswordResetCode.objects.filter(
                user=user,
                code_hash=_hash_code(code),
                used=False,
                expires_at__gt=timezone.now(),
            )
            .order_by("-created_at")
            .first()
        )
    if not row:
        messages.error(request, "That code is wrong or has expired.")
        return render(request, "inventory/password_reset.html", {"mode": "confirm", "identifier": ident})
    user.set_password(password)
    user.save()
    row.used = True
    row.save()
    messages.success(request, "Password updated. Sign in with the new one.")
    return redirect("login")


@login_required
@require_perm("can_view_reports")
def today(request):
    profile = get_profile(request)
    if profile is None:
        return redirect("setup_company")
    company = profile.company
    now = timezone.localtime()
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week = start - timedelta(days=6)
    today_sales = Sale.objects.filter(company=company, sales_date__gte=start).select_related("item")
    week_sales = Sale.objects.filter(company=company, sales_date__gte=week)
    items = Item.objects.filter(company=company)
    low = [it for it in items if it.quantity_in_stock <= it.reorder_level]
    today_total = sum(s.line_total for s in today_sales)
    week_amount = sum(s.line_total for s in week_sales)
    value = sum(it.quantity_in_stock * it.buy_price for it in items)
    return render(
        request,
        "inventory/today.html",
        {
            "company": company,
            "profile": profile,
            "today_sales": today_sales.order_by("-sales_date"),
            "today_total": today_total,
            "week_total": week_amount,
            "low_items": low,
            "product_count": items.count(),
            "inventory_value": value,
            **perm_context(profile),
        },
    )


@login_required
@require_perm("can_edit_items")
@require_POST
def delete_item(request, item_id):
    profile = get_profile(request)
    company = profile.company
    item = get_object_or_404(Item, id=item_id, company=company)
    if Sale.objects.filter(item=item).exists():
        messages.error(request, "This product has sales. Edit it instead of deleting.")
        return redirect("edit_item", item_id=item.id)
    name = item.name
    item.delete()
    log_activity(company, request.user, ActivityLog.ACTION_ITEM_EDIT, f"Deleted {name}")
    messages.success(request, f"Removed {name}.")
    return redirect("dashboard")


@login_required
@require_POST
def rename_shop(request):
    profile = get_profile(request)
    if profile is None or not profile.is_owner:
        messages.error(request, "Only the owner can rename the shop.")
        return redirect("dashboard")
    name = request.POST.get("company_name", "").strip()
    if not name:
        messages.error(request, "Enter a shop name.")
        return redirect("dashboard")
    if Company.objects.filter(name__iexact=name).exclude(id=profile.company_id).exists():
        messages.error(request, "Another shop already uses that name.")
        return redirect("dashboard")
    profile.company.name = name
    profile.company.save()
    messages.success(request, "Shop name updated.")
    return redirect("dashboard")


@login_required
def sell(request):
    profile = get_profile(request)
    if profile is None:
        return redirect("setup_company")
    company = profile.company
    now = timezone.localtime()
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    items = Item.objects.filter(company=company).order_by("name")
    today_sales = Sale.objects.filter(company=company, sales_date__gte=start).select_related("item").order_by("-sales_date")
    today_total = sum(s.line_total for s in today_sales)
    return render(
        request,
        "inventory/sell.html",
        {
            "company": company,
            "profile": profile,
            "items": items,
            "today_sales": today_sales,
            "today_total": today_total,
            "sub_active": company.is_subscription_active(),
            **perm_context(profile),
        },
    )
