"""Subscription and trial reminder emails.

Uses the same Django SMTP setup as low-stock alerts (EMAIL_HOST and related
variables). Each shop gets at most one advance email and one due-date email
per due moment. Extending or renewing changes that moment, so the next period
can be reminded again.
"""

import os

from django.core.mail import send_mail
from django.utils import timezone
from django.utils.dateformat import format as date_format

from .models import Subscription, UserProfile


def email_configured():
    return bool((os.getenv("EMAIL_HOST") or "").strip())


def format_due(due):
    """Calendar date in the project timezone (Africa/Kampala)."""
    return date_format(timezone.localtime(due), "d M Y")


def owner_emails(company):
    """Owner addresses already stored on the shop. Staff are not included."""
    profiles = UserProfile.objects.filter(
        company=company, role=UserProfile.ROLE_OWNER
    ).select_related("user")
    seen = set()
    emails = []
    for profile in profiles:
        email = (profile.user.email or "").strip()
        key = email.lower()
        if email and key not in seen:
            seen.add(key)
            emails.append(email)
    return emails


def _same_moment(saved, due):
    if saved is None or due is None:
        return False
    return abs((saved - due).total_seconds()) < 1


def reminder_message(sub, kind, due):
    company = sub.company.name
    when = format_due(due)
    period = "free trial" if sub.status == Subscription.STATUS_TRIAL else "subscription"
    if kind == "due":
        subject = f"{company}: your {period} ends today"
        when_line = f"ends today, {when}"
    else:
        subject = f"{company}: your {period} ends on {when}"
        when_line = f"ends on {when}"
    body = (
        f"Hello,\n\n"
        f"This is a reminder that the {period} for {company} {when_line}.\n\n"
        f"Renew from the Billing page in Cloud Stock Manager so the shop can "
        f"keep recording sales and stock.\n\n"
        f"Thank you."
    )
    return subject, body


def send_subscription_reminders(today=None, dry_run=False):
    """Send due reminders. Returns a result dict and never raises for one shop.

    today is the Africa/Kampala calendar day to judge against. dry_run lists
    what would be sent and does not email or record a reminder.
    """
    today = today or timezone.localdate()
    result = {
        "disabled": False,
        "sent_upcoming": 0,
        "sent_due": 0,
        "skipped_no_email": 0,
        "failed": 0,
        "errors": [],
        "planned": [],
    }
    if not dry_run and not email_configured():
        result["disabled"] = True
        return result

    subs = (
        Subscription.objects.select_related("company")
        .filter(
            status__in=[
                Subscription.STATUS_TRIAL,
                Subscription.STATUS_ACTIVE,
                Subscription.STATUS_PENDING,
                Subscription.STATUS_PAST_DUE,
            ]
        )
        .order_by("company__name")
    )
    for sub in subs:
        due = sub.due_at
        if due is None:
            continue
        days = (timezone.localtime(due).date() - today).days
        if days == 0:
            kind = "due"
            field = "reminded_due_for"
            already = _same_moment(sub.reminded_due_for, due)
        elif 1 <= days <= Subscription.REMINDER_LEAD_DAYS:
            kind = "upcoming"
            field = "reminded_upcoming_for"
            already = _same_moment(sub.reminded_upcoming_for, due)
        else:
            continue
        if already:
            continue
        emails = owner_emails(sub.company)
        if not emails:
            result["skipped_no_email"] += 1
            continue
        subject, body = reminder_message(sub, kind, due)
        if dry_run:
            result["planned"].append({
                "company": sub.company.name,
                "kind": kind,
                "to": emails,
                "due": format_due(due),
                "subject": subject,
            })
            continue
        try:
            send_mail(subject, body, None, emails, fail_silently=False)
        except Exception as exc:
            result["failed"] += 1
            result["errors"].append(f"{sub.company.name}: {exc}")
            continue
        Subscription.objects.filter(pk=sub.pk).update(**{field: due})
        if kind == "due":
            result["sent_due"] += 1
        else:
            result["sent_upcoming"] += 1
    return result
