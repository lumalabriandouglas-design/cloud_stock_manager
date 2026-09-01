import csv
import json
import os

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.db.models import F, Q, Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from google import genai
from google.genai import types
from PIL import Image

from .models import ActivityLog, Category, Company, Item, Sale, StockIn, UserProfile


def get_profile(request):
    if not hasattr(request.user, "profile"):
        return None
    return request.user.profile


def get_user_company(request):
    profile = get_profile(request)
    return profile.company if profile else None


def is_superuser(user):
    return user.is_authenticated and user.is_superuser


def require_perm(perm_name):
    def decorator(view_func):
        def wrapper(request, *args, **kwargs):
            profile = get_profile(request)
            if profile is None:
                return redirect("setup_company")
            if not profile.has_perm(perm_name):
                messages.error(request, "You do not have permission for this action.")
                return redirect("dashboard")
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def perm_context(profile):
    if profile is None:
        return {}
    return {
        "can_manage_stock": profile.has_perm("can_manage_stock"),
        "can_edit_items": profile.has_perm("can_edit_items"),
        "can_view_reports": profile.has_perm("can_view_reports"),
        "can_manage_categories": profile.has_perm("can_manage_categories"),
        "can_manage_team": profile.has_perm("can_manage_team"),
        "is_owner": profile.is_owner,
    }


def log_activity(company, user, action, message):
    ActivityLog.objects.create(company=company, user=user, action=action, message=message)


# ───────────────────────────── Auth ─────────────────────────────

def register(request):
    if request.user.is_authenticated:
        return redirect("dashboard")

    if request.method == "POST":
        company_name = request.POST.get("company_name", "").strip()
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")
        password2 = request.POST.get("password2", "")
        email = request.POST.get("email", "").strip()

        errors = []
        if not company_name:
            errors.append("Business name is required.")
        if not username:
            errors.append("Username is required.")
        if len(password) < 6:
            errors.append("Password must be at least 6 characters.")
        if password != password2:
            errors.append("Passwords do not match.")
        if Company.objects.filter(name__iexact=company_name).exists():
            errors.append("A business with that name already exists.")
        if User.objects.filter(username__iexact=username).exists():
            errors.append("That username is already taken.")

        if errors:
            for e in errors:
                messages.error(request, e)
            return render(request, "inventory/register.html")

        company = Company.objects.create(name=company_name)
        user = User.objects.create_user(username=username, email=email or "", password=password)
        UserProfile.objects.create(
            user=user, company=company, role=UserProfile.ROLE_OWNER,
            can_manage_stock=True, can_edit_items=True, can_view_reports=True,
            can_manage_categories=True, can_manage_team=True,
        )
        login(request, user)
        messages.success(request, f"Welcome! Your business ‘{company.name}’ is ready. Start by adding your first products.")
        return redirect("dashboard")

    return render(request, "inventory/register.html")


@login_required
def setup_company(request):
    if hasattr(request.user, "profile"):
        return redirect("dashboard")

    if request.method == "POST":
        name = request.POST.get("company_name", "").strip()
        if not name:
            messages.error(request, "Please enter a company name.")
            return render(request, "inventory/setup_company.html")
        if Company.objects.filter(name__iexact=name).exists():
            messages.error(request, "A company with that name already exists.")
            return render(request, "inventory/setup_company.html")

        company = Company.objects.create(name=name)
        UserProfile.objects.create(
            user=request.user, company=company, role=UserProfile.ROLE_OWNER,
            can_manage_stock=True, can_edit_items=True, can_view_reports=True,
            can_manage_categories=True, can_manage_team=True,
        )
        messages.success(request, f"Company ‘{company.name}’ created. Add your first products below.")
        return redirect("dashboard")

    return render(request, "inventory/setup_company.html")


# ───────────────────────────── Dashboard ─────────────────────────────

@login_required
def dashboard(request):
    profile = get_profile(request)
    if profile is None:
        if request.user.is_superuser:
            return redirect("platform_create_business")
        return redirect("setup_company")

    company = profile.company
    items = Item.objects.filter(company=company).select_related("category").order_by("name")
    categories = Category.objects.filter(company=company).order_by("name")

    # Search & filters
    q = request.GET.get("q", "").strip()
    category_id = request.GET.get("category", "")
    low_only = request.GET.get("low") == "1"

    if q:
        items = items.filter(Q(name__icontains=q) | Q(category__name__icontains=q))
    if category_id:
        items = items.filter(category_id=category_id)
    if low_only:
        items = items.filter(quantity_in_stock__lte=F("reorder_level"))

    recent_sales = (
        Sale.objects.filter(company=company)
        .select_related("item")
        .order_by("-sales_date")[:6]
    )
    recent_activity = ActivityLog.objects.filter(company=company).select_related("user")[:8]

    today = timezone.now().date()
    today_sales_total = (
        Sale.objects.filter(company=company, sales_date__date=today)
        .aggregate(total=Sum(F("quantity_sold") * F("sell_price")))["total"] or 0
    )
    low_stock_count = Item.objects.filter(
        company=company, quantity_in_stock__lte=F("reorder_level")
    ).count()
    total_inventory_val = sum(
        i.quantity_in_stock * i.buy_price
        for i in Item.objects.filter(company=company)
    )

    context = {
        "company": company,
        "items": items,
        "categories": categories,
        "recent_sales": recent_sales,
        "recent_activity": recent_activity,
        "low_stock_count": low_stock_count,
        "total_inventory_val": total_inventory_val,
        "today_sales_total": today_sales_total,
        "profile": profile,
        "is_platform_admin": request.user.is_superuser,
        "q": q,
        "selected_category": category_id,
        "low_only": low_only,
        **perm_context(profile),
    }
    return render(request, "inventory/dashboard.html", context)


# ───────────────────────────── CSV Exports ─────────────────────────────

@login_required
@require_perm("can_view_reports")
def export_inventory_csv(request):
    company = get_user_company(request)
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="{company.name}_inventory.csv"'

    writer = csv.writer(response)
    writer.writerow(["Name", "Category", "Buy Price", "Sell Price", "Quantity", "Reorder Level"])
    for item in Item.objects.filter(company=company).select_related("category").order_by("name"):
        writer.writerow([
            item.name,
            item.category.name if item.category else "",
            item.buy_price,
            item.sell_price,
            item.quantity_in_stock,
            item.reorder_level,
        ])
    return response


@login_required
@require_perm("can_view_reports")
def export_sales_csv(request):
    company = get_user_company(request)
    days = int(request.GET.get("days", 30))
    since = timezone.now() - timezone.timedelta(days=days)

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="{company.name}_sales.csv"'

    writer = csv.writer(response)
    writer.writerow(["Date", "Product", "Qty", "Unit Price", "Revenue", "Est. Cost", "Est. Profit"])
    for s in Sale.objects.filter(company=company, sales_date__gte=since).select_related("item").order_by("-sales_date"):
        writer.writerow([
            s.sales_date.strftime("%Y-%m-%d %H:%M"),
            s.item.name,
            s.quantity_sold,
            s.sell_price,
            s.line_total,
            s.estimated_cost,
            s.estimated_profit,
        ])
    return response


# ───────────────────────────── Team ─────────────────────────────

@login_required
@require_perm("can_manage_team")
def manage_team(request):
    profile = get_profile(request)
    company = profile.company
    members = UserProfile.objects.filter(company=company).select_related("user").order_by("role", "user__username")

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "add":
            username = request.POST.get("username", "").strip()
            password = request.POST.get("password", "")
            role = request.POST.get("role", UserProfile.ROLE_STAFF)
            can_manage_stock = request.POST.get("can_manage_stock") == "on"
            can_edit_items = request.POST.get("can_edit_items") == "on"
            can_view_reports = request.POST.get("can_view_reports") == "on"
            can_manage_categories = request.POST.get("can_manage_categories") == "on"
            can_manage_team = request.POST.get("can_manage_team") == "on"

            if not username or len(password) < 6:
                messages.error(request, "Username and password (min 6 chars) required.")
            elif User.objects.filter(username__iexact=username).exists():
                messages.error(request, "Username already taken.")
            else:
                user = User.objects.create_user(username=username, password=password)
                UserProfile.objects.create(
                    user=user, company=company, role=role,
                    can_manage_stock=can_manage_stock or role == UserProfile.ROLE_OWNER,
                    can_edit_items=can_edit_items or role == UserProfile.ROLE_OWNER,
                    can_view_reports=can_view_reports or role == UserProfile.ROLE_OWNER,
                    can_manage_categories=can_manage_categories or role == UserProfile.ROLE_OWNER,
                    can_manage_team=can_manage_team or role == UserProfile.ROLE_OWNER,
                )
                messages.success(request, f"Added {username}.")

        elif action == "update_perms":
            member = get_object_or_404(UserProfile, id=request.POST.get("profile_id"), company=company)
            if member.is_owner:
                messages.error(request, "Cannot change permissions of an Owner.")
            else:
                member.can_manage_stock = request.POST.get("can_manage_stock") == "on"
                member.can_edit_items = request.POST.get("can_edit_items") == "on"
                member.can_view_reports = request.POST.get("can_view_reports") == "on"
                member.can_manage_categories = request.POST.get("can_manage_categories") == "on"
                member.can_manage_team = request.POST.get("can_manage_team") == "on"
                member.save()
                messages.success(request, f"Permissions updated for {member.user.username}.")

        elif action == "remove":
            member = get_object_or_404(UserProfile, id=request.POST.get("profile_id"), company=company)
            if member.user == request.user:
                messages.error(request, "You cannot remove yourself.")
            elif member.is_owner and UserProfile.objects.filter(company=company, role=UserProfile.ROLE_OWNER).count() <= 1:
                messages.error(request, "Cannot remove the last owner.")
            else:
                uname = member.user.username
                member.user.delete()
                messages.success(request, f"Removed {uname}.")

        return redirect("manage_team")

    return render(request, "inventory/manage_team.html", {
        "company": company, "members": members, "profile": profile, **perm_context(profile),
    })


# ───────────────────────────── Categories ─────────────────────────────

@login_required
@require_perm("can_manage_categories")
def manage_categories(request):
    profile = get_profile(request)
    company = profile.company
    categories = Category.objects.filter(company=company).order_by("name")

    if request.method == "POST":
        action = request.POST.get("action")
        if action == "add":
            name = request.POST.get("name", "").strip()
            if not name:
                messages.error(request, "Name required.")
            elif Category.objects.filter(company=company, name__iexact=name).exists():
                messages.error(request, "Category already exists.")
            else:
                Category.objects.create(company=company, name=name.title())
                messages.success(request, "Category added.")
        elif action == "edit":
            cat = get_object_or_404(Category, id=request.POST.get("category_id"), company=company)
            name = request.POST.get("name", "").strip()
            if name and not Category.objects.filter(company=company, name__iexact=name).exclude(id=cat.id).exists():
                cat.name = name.title()
                cat.save()
                messages.success(request, "Updated.")
            else:
                messages.error(request, "Invalid or duplicate name.")
        elif action == "delete":
            cat = get_object_or_404(Category, id=request.POST.get("category_id"), company=company)
            cat.delete()
            messages.success(request, "Deleted.")
        return redirect("manage_categories")

    return render(request, "inventory/manage_categories.html", {
        "company": company, "categories": categories, "profile": profile, **perm_context(profile),
    })


# ───────────────────────────── Edit Item ─────────────────────────────

@login_required
@require_perm("can_edit_items")
def edit_item(request, item_id):
    profile = get_profile(request)
    company = profile.company
    item = get_object_or_404(Item, id=item_id, company=company)
    categories = Category.objects.filter(company=company).order_by("name")

    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        category_id = request.POST.get("category_id")
        buy_price = request.POST.get("buy_price") or 0
        sell_price = request.POST.get("sell_price") or 0
        reorder_level = request.POST.get("reorder_level") or 5
        qty_adjust = request.POST.get("qty_adjust")

        if not name:
            messages.error(request, "Name required.")
        elif Item.objects.filter(company=company, name__iexact=name).exclude(id=item.id).exists():
            messages.error(request, "Name already used.")
        else:
            old_qty = item.quantity_in_stock
            item.name = name
            item.category = Category.objects.filter(id=category_id, company=company).first() if category_id else None
            item.buy_price = buy_price
            item.sell_price = sell_price
            item.reorder_level = int(reorder_level)

            if qty_adjust and profile.has_perm("can_manage_stock"):
                try:
                    delta = int(qty_adjust)
                    item.quantity_in_stock = max(0, item.quantity_in_stock + delta)
                    if delta > 0:
                        StockIn.objects.create(company=company, item=item, quantity_added=delta)
                except ValueError:
                    pass

            item.save()
            log_activity(company, request.user, ActivityLog.ACTION_ITEM_EDIT, f"Updated {item.name}")
            messages.success(request, f"‘{item.name}’ updated.")
            return redirect("dashboard")

    return render(request, "inventory/edit_item.html", {
        "company": company, "item": item, "categories": categories, "profile": profile, **perm_context(profile),
    })


# ───────────────────────────── Reports ─────────────────────────────

@login_required
@require_perm("can_view_reports")
def sales_report(request):
    profile = get_profile(request)
    company = profile.company
    days = int(request.GET.get("days", 30))
    since = timezone.now() - timezone.timedelta(days=days)

    sales = Sale.objects.filter(company=company, sales_date__gte=since).select_related("item").order_by("-sales_date")
    total_revenue = sum(s.line_total for s in sales)
    total_cost = sum(s.estimated_cost for s in sales)
    total_profit = total_revenue - total_cost
    total_qty = sum(s.quantity_sold for s in sales)

    return render(request, "inventory/sales_report.html", {
        "company": company, "sales": sales, "days": days,
        "total_revenue": total_revenue, "total_cost": total_cost,
        "total_profit": total_profit, "total_qty": total_qty,
        "profile": profile, "is_platform_admin": request.user.is_superuser,
        **perm_context(profile),
    })


# ───────────────────────────── Operations ─────────────────────────────

@login_required
@require_perm("can_manage_stock")
def record_sale(request):
    if request.method == "POST":
        company = get_user_company(request)
        item_id = request.POST.get("item_id")
        quantity = int(request.POST.get("quantity", 1))
        custom_price = request.POST.get("sell_price")

        if not item_id:
            messages.error(request, "Select an item.")
            return redirect("dashboard")

        item = get_object_or_404(Item, id=item_id, company=company)
        sell_price = custom_price if custom_price else item.sell_price

        if item.quantity_in_stock < quantity:
            messages.error(request, f"Only {item.quantity_in_stock} left of {item.name}.")
            return redirect("dashboard")

        Sale.objects.create(company=company, item=item, quantity_sold=quantity, sell_price=sell_price)
        item.quantity_in_stock -= quantity
        item.save()
        log_activity(company, request.user, ActivityLog.ACTION_SALE, f"Sold {quantity}× {item.name}")
        messages.success(request, f"Sold {quantity} × {item.name}.")

    return redirect("dashboard")


@login_required
@require_perm("can_manage_stock")
def record_stock_in(request):
    if request.method == "POST":
        company = get_user_company(request)
        item_name = request.POST.get("item_name", "").strip()
        category_id = request.POST.get("category_id")
        buy_price = request.POST.get("buy_price") or 0
        sell_price = request.POST.get("sell_price") or 0
        quantity = int(request.POST.get("quantity", 0))

        if not item_name or quantity <= 0:
            messages.error(request, "Name and positive quantity required.")
            return redirect("dashboard")

        normalized = " ".join(item_name.split()).title()
        category = Category.objects.filter(id=category_id, company=company).first() if category_id else None

        item, created = Item.objects.get_or_create(
            company=company, name=normalized,
            defaults={"category": category, "buy_price": buy_price, "sell_price": sell_price, "quantity_in_stock": 0},
        )
        item.quantity_in_stock += quantity
        if buy_price:
            item.buy_price = buy_price
        if sell_price:
            item.sell_price = sell_price
        if category and not item.category:
            item.category = category
        item.save()
        StockIn.objects.create(company=company, item=item, quantity_added=quantity)
        log_activity(company, request.user, ActivityLog.ACTION_STOCK_IN, f"+{quantity} {item.name}")
        messages.success(request, f"{'Created' if created else 'Restocked'} {item.name}: +{quantity}")

    return redirect("dashboard")


@login_required
@require_perm("can_manage_stock")
def scan_ledger(request):
    if request.method == "POST" and request.FILES.get("ledger_photo"):
        company = get_user_company(request)
        photo = request.FILES["ledger_photo"]
        api_key = os.getenv("GEMINI_API_KEY")

        if not api_key:
            messages.error(request, "GEMINI_API_KEY not set.")
            return redirect("dashboard")

        try:
            img = Image.open(photo)
            client = genai.Client(api_key=api_key)
            prompt = """Analyze this handwritten stock ledger. Return strict JSON list of products with:
name (string), buy_price (number default 0), sell_price (number default 0), quantity (integer default 1).
Example: [{"name": "Standing Fan", "buy_price": 10000, "sell_price": 20000, "quantity": 5}]"""

            response = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=[prompt, img],
                config=types.GenerateContentConfig(response_mime_type="application/json"),
            )

            items_data = json.loads(response.text)
            added = 0
            for entry in items_data:
                name = str(entry.get("name", "")).strip()
                if not name:
                    continue
                normalized = " ".join(name.split()).title()
                buy = float(entry.get("buy_price") or 0)
                sell = float(entry.get("sell_price") or 0)
                qty = int(entry.get("quantity") or 1)

                item, _ = Item.objects.get_or_create(
                    company=company, name=normalized,
                    defaults={"buy_price": buy, "sell_price": sell, "quantity_in_stock": 0},
                )
                item.quantity_in_stock += qty
                if buy > 0:
                    item.buy_price = buy
                if sell > 0:
                    item.sell_price = sell
                item.save()
                StockIn.objects.create(company=company, item=item, quantity_added=qty)
                added += 1

            if added:
                log_activity(company, request.user, ActivityLog.ACTION_STOCK_IN, f"AI scan imported {added} item(s)")
                messages.success(request, f"Imported {added} item(s).")
            else:
                messages.warning(request, "No products extracted.")
        except Exception as e:
            messages.error(request, f"Scan error: {e}")

    return redirect("dashboard")


# ───────────────────────────── Platform Admin ─────────────────────────────

@login_required
@user_passes_test(is_superuser)
def platform_create_business(request):
    if request.method == "POST":
        company_name = request.POST.get("company_name", "").strip()
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")
        email = request.POST.get("email", "").strip()

        errors = []
        if not company_name:
            errors.append("Company name required.")
        if not username:
            errors.append("Username required.")
        if not password or len(password) < 6:
            errors.append("Password min 6 characters.")
        if Company.objects.filter(name__iexact=company_name).exists():
            errors.append("Company name taken.")
        if User.objects.filter(username__iexact=username).exists():
            errors.append("Username taken.")

        if errors:
            for e in errors:
                messages.error(request, e)
        else:
            company = Company.objects.create(name=company_name)
            user = User.objects.create_user(username=username, email=email or "", password=password)
            UserProfile.objects.create(
                user=user, company=company, role=UserProfile.ROLE_OWNER,
                can_manage_stock=True, can_edit_items=True, can_view_reports=True,
                can_manage_categories=True, can_manage_team=True,
            )
            messages.success(request, f"Created ‘{company.name}’ – owner: {username}")
            return redirect("platform_create_business")

    companies = Company.objects.all().order_by("-created_at")
    return render(request, "inventory/platform_create_business.html", {"companies": companies})
