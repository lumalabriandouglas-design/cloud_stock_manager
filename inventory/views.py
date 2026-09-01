import json
import os
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.db.models import F, Sum, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from google import genai
from google.genai import types
from PIL import Image

from .models import Category, Company, Item, Sale, StockIn, UserProfile


def get_user_company(request):
    if not hasattr(request.user, "profile"):
        return None
    return request.user.profile.company


def is_superuser(user):
    return user.is_authenticated and user.is_superuser


def owner_required(view_func):
    """Decorator: only company owners can access."""
    def wrapper(request, *args, **kwargs):
        company = get_user_company(request)
        if company is None:
            return redirect("setup_company")
        if not request.user.profile.is_owner and not request.user.is_superuser:
            messages.error(request, "Only company owners can perform this action.")
            return redirect("dashboard")
        return view_func(request, *args, **kwargs)
    return wrapper


# ───────────────────────────── Auth / Registration ─────────────────────────────

def register(request):
    """Public registration: create user + company in one step."""
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
        user = User.objects.create_user(
            username=username, email=email or "", password=password
        )
        UserProfile.objects.create(
            user=user, company=company, role=UserProfile.ROLE_OWNER
        )
        login(request, user)
        messages.success(request, f"Welcome! Your business ‘{company.name}’ is ready.")
        return redirect("dashboard")

    return render(request, "inventory/register.html")


@login_required
def setup_company(request):
    if hasattr(request.user, "profile"):
        return redirect("dashboard")

    if request.method == "POST":
        name = request.POST.get("company_name", "").strip()
        if not name:
            messages.error(request, "Please enter a company / business name.")
            return render(request, "inventory/setup_company.html")
        if Company.objects.filter(name__iexact=name).exists():
            messages.error(request, "A company with that name already exists.")
            return render(request, "inventory/setup_company.html")

        company = Company.objects.create(name=name)
        UserProfile.objects.create(
            user=request.user, company=company, role=UserProfile.ROLE_OWNER
        )
        messages.success(request, f"Company ‘{company.name}’ created. You are the Owner.")
        return redirect("dashboard")

    return render(request, "inventory/setup_company.html")


# ───────────────────────────── Dashboard ─────────────────────────────

@login_required
def dashboard(request):
    company = get_user_company(request)
    if company is None:
        if request.user.is_superuser:
            return redirect("platform_create_business")
        return redirect("setup_company")

    items = Item.objects.filter(company=company).select_related("category").order_by("name")
    categories = Category.objects.filter(company=company).order_by("name")
    recent_sales = (
        Sale.objects.filter(company=company)
        .select_related("item")
        .order_by("-sales_date")[:8]
    )

    today = timezone.now().date()
    today_sales_total = (
        Sale.objects.filter(company=company, sales_date__date=today).aggregate(
            total=Sum(F("quantity_sold") * F("sell_price"))
        )["total"]
        or 0
    )

    low_stock_items = items.filter(quantity_in_stock__lte=F("reorder_level"))
    total_inventory_val = sum(item.quantity_in_stock * item.buy_price for item in items)

    context = {
        "company": company,
        "items": items,
        "categories": categories,
        "recent_sales": recent_sales,
        "low_stock_count": low_stock_items.count(),
        "total_inventory_val": total_inventory_val,
        "today_sales_total": today_sales_total,
        "is_owner": request.user.profile.is_owner,
        "is_platform_admin": request.user.is_superuser,
    }
    return render(request, "inventory/dashboard.html", context)


# ───────────────────────────── Team Management (Owner only) ─────────────────────────────

@login_required
@owner_required
def manage_team(request):
    company = get_user_company(request)
    members = UserProfile.objects.filter(company=company).select_related("user").order_by("role", "user__username")

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "add":
            username = request.POST.get("username", "").strip()
            password = request.POST.get("password", "")
            role = request.POST.get("role", UserProfile.ROLE_STAFF)

            if not username or len(password) < 6:
                messages.error(request, "Username and password (min 6 chars) are required.")
            elif User.objects.filter(username__iexact=username).exists():
                messages.error(request, "That username is already taken.")
            else:
                user = User.objects.create_user(username=username, password=password)
                UserProfile.objects.create(user=user, company=company, role=role)
                messages.success(request, f"Added {username} as {role}.")

        elif action == "remove":
            profile_id = request.POST.get("profile_id")
            profile = get_object_or_404(UserProfile, id=profile_id, company=company)
            if profile.user == request.user:
                messages.error(request, "You cannot remove yourself.")
            elif profile.is_owner and UserProfile.objects.filter(company=company, role=UserProfile.ROLE_OWNER).count() <= 1:
                messages.error(request, "Cannot remove the last owner.")
            else:
                uname = profile.user.username
                profile.user.delete()  # cascades to profile
                messages.success(request, f"Removed {uname}.")

        return redirect("manage_team")

    return render(request, "inventory/manage_team.html", {
        "company": company,
        "members": members,
        "is_owner": True,
    })


# ───────────────────────────── Categories ─────────────────────────────

@login_required
def manage_categories(request):
    company = get_user_company(request)
    if company is None:
        return redirect("setup_company")

    categories = Category.objects.filter(company=company).order_by("name")

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "add":
            name = request.POST.get("name", "").strip()
            if not name:
                messages.error(request, "Category name is required.")
            elif Category.objects.filter(company=company, name__iexact=name).exists():
                messages.error(request, "That category already exists.")
            else:
                Category.objects.create(company=company, name=name.title())
                messages.success(request, f"Category ‘{name}’ added.")

        elif action == "edit":
            cat_id = request.POST.get("category_id")
            name = request.POST.get("name", "").strip()
            cat = get_object_or_404(Category, id=cat_id, company=company)
            if name and not Category.objects.filter(company=company, name__iexact=name).exclude(id=cat.id).exists():
                cat.name = name.title()
                cat.save()
                messages.success(request, "Category updated.")
            else:
                messages.error(request, "Invalid or duplicate name.")

        elif action == "delete":
            cat_id = request.POST.get("category_id")
            cat = get_object_or_404(Category, id=cat_id, company=company)
            cat.delete()
            messages.success(request, "Category deleted.")

        return redirect("manage_categories")

    return render(request, "inventory/manage_categories.html", {
        "company": company,
        "categories": categories,
        "is_owner": request.user.profile.is_owner,
    })


# ───────────────────────────── Items (edit / adjust) ─────────────────────────────

@login_required
def edit_item(request, item_id):
    company = get_user_company(request)
    if company is None:
        return redirect("setup_company")

    item = get_object_or_404(Item, id=item_id, company=company)
    categories = Category.objects.filter(company=company).order_by("name")

    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        category_id = request.POST.get("category_id")
        buy_price = request.POST.get("buy_price") or 0
        sell_price = request.POST.get("sell_price") or 0
        reorder_level = request.POST.get("reorder_level") or 5
        qty_adjust = request.POST.get("qty_adjust")  # can be + or -

        if not name:
            messages.error(request, "Name is required.")
        elif Item.objects.filter(company=company, name__iexact=name).exclude(id=item.id).exists():
            messages.error(request, "Another item with that name already exists.")
        else:
            item.name = name
            item.category = Category.objects.filter(id=category_id, company=company).first() if category_id else None
            item.buy_price = buy_price
            item.sell_price = sell_price
            item.reorder_level = int(reorder_level)

            if qty_adjust:
                try:
                    delta = int(qty_adjust)
                    item.quantity_in_stock = max(0, item.quantity_in_stock + delta)
                    if delta > 0:
                        StockIn.objects.create(company=company, item=item, quantity_added=delta)
                except ValueError:
                    pass

            item.save()
            messages.success(request, f"‘{item.name}’ updated.")
            return redirect("dashboard")

    return render(request, "inventory/edit_item.html", {
        "company": company,
        "item": item,
        "categories": categories,
        "is_owner": request.user.profile.is_owner,
    })


# ───────────────────────────── Sales Report ─────────────────────────────

@login_required
def sales_report(request):
    company = get_user_company(request)
    if company is None:
        return redirect("setup_company")

    # Default: last 30 days
    days = int(request.GET.get("days", 30))
    since = timezone.now() - timezone.timedelta(days=days)

    sales = (
        Sale.objects.filter(company=company, sales_date__gte=since)
        .select_related("item")
        .order_by("-sales_date")
    )

    total_revenue = sum(s.line_total for s in sales)
    total_cost = sum(s.estimated_cost for s in sales)
    total_profit = total_revenue - total_cost
    total_qty = sum(s.quantity_sold for s in sales)

    context = {
        "company": company,
        "sales": sales,
        "days": days,
        "total_revenue": total_revenue,
        "total_cost": total_cost,
        "total_profit": total_profit,
        "total_qty": total_qty,
        "is_owner": request.user.profile.is_owner,
        "is_platform_admin": request.user.is_superuser,
    }
    return render(request, "inventory/sales_report.html", context)


# ───────────────────────────── Existing operations ─────────────────────────────

@login_required
def record_sale(request):
    if request.method == "POST":
        company = get_user_company(request)
        if company is None:
            return redirect("setup_company")

        item_id = request.POST.get("item_id")
        quantity = int(request.POST.get("quantity", 1))
        custom_price = request.POST.get("sell_price")

        if not item_id:
            messages.error(request, "Please select an item.")
            return redirect("dashboard")

        item = get_object_or_404(Item, id=item_id, company=company)
        sell_price = custom_price if custom_price else item.sell_price

        if item.quantity_in_stock < quantity:
            messages.error(request, f"Not enough stock for {item.name}. Only {item.quantity_in_stock} left.")
            return redirect("dashboard")

        Sale.objects.create(company=company, item=item, quantity_sold=quantity, sell_price=sell_price)
        item.quantity_in_stock -= quantity
        item.save()
        messages.success(request, f"Sold {quantity} × {item.name} for UGX {sell_price}.")

    return redirect("dashboard")


@login_required
def record_stock_in(request):
    if request.method == "POST":
        company = get_user_company(request)
        if company is None:
            return redirect("setup_company")

        item_name = request.POST.get("item_name", "").strip()
        category_id = request.POST.get("category_id")
        buy_price = request.POST.get("buy_price") or 0
        sell_price = request.POST.get("sell_price") or 0
        quantity = int(request.POST.get("quantity", 0))

        if not item_name or quantity <= 0:
            messages.error(request, "Product name and a positive quantity are required.")
            return redirect("dashboard")

        # Normalize name the same way as the model
        normalized = " ".join(item_name.split()).title()

        category = Category.objects.filter(id=category_id, company=company).first() if category_id else None

        item, created = Item.objects.get_or_create(
            company=company,
            name=normalized,
            defaults={
                "category": category,
                "buy_price": buy_price,
                "sell_price": sell_price,
                "quantity_in_stock": 0,
            },
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
        action = "Created and stocked" if created else "Restocked"
        messages.success(request, f"{action} {item.name}: +{quantity} units.")

    return redirect("dashboard")


@login_required
def scan_ledger(request):
    if request.method == "POST" and request.FILES.get("ledger_photo"):
        company = get_user_company(request)
        if company is None:
            return redirect("setup_company")

        photo = request.FILES["ledger_photo"]
        api_key = os.getenv("GEMINI_API_KEY")

        if not api_key:
            messages.error(request, "GEMINI_API_KEY is not set.")
            return redirect("dashboard")

        try:
            img = Image.open(photo)
            client = genai.Client(api_key=api_key)
            prompt = """Analyze this handwritten stock ledger page. Extract all products and return a strict JSON list.
Identify: name (string), buy_price (number, default 0), sell_price (number, default 0), quantity (integer, default 1).
Example: [{"name": "Standing Fan", "buy_price": 10000, "sell_price": 20000, "quantity": 5}]"""

            response = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=[prompt, img],
                config=types.GenerateContentConfig(response_mime_type="application/json"),
            )

            items_data = json.loads(response.text)
            added_count = 0

            for entry in items_data:
                name = str(entry.get("name", "")).strip()
                if not name:
                    continue
                normalized = " ".join(name.split()).title()
                buy_price = float(entry.get("buy_price") or 0)
                sell_price = float(entry.get("sell_price") or 0)
                quantity = int(entry.get("quantity") or 1)

                item, created = Item.objects.get_or_create(
                    company=company,
                    name=normalized,
                    defaults={"buy_price": buy_price, "sell_price": sell_price, "quantity_in_stock": 0},
                )
                item.quantity_in_stock += quantity
                if buy_price > 0:
                    item.buy_price = buy_price
                if sell_price > 0:
                    item.sell_price = sell_price
                item.save()
                StockIn.objects.create(company=company, item=item, quantity_added=quantity)
                added_count += 1

            if added_count:
                messages.success(request, f"Imported {added_count} item(s) from the ledger.")
            else:
                messages.warning(request, "No products could be extracted.")

        except Exception as e:
            messages.error(request, f"Error parsing ledger: {e}")

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
            errors.append("Company name is required.")
        if not username:
            errors.append("Username is required.")
        if not password or len(password) < 6:
            errors.append("Password must be at least 6 characters.")
        if Company.objects.filter(name__iexact=company_name).exists():
            errors.append("A company with that name already exists.")
        if User.objects.filter(username__iexact=username).exists():
            errors.append("That username is already taken.")

        if errors:
            for e in errors:
                messages.error(request, e)
            return render(request, "inventory/platform_create_business.html", {"companies": Company.objects.all().order_by("-created_at")})

        company = Company.objects.create(name=company_name)
        user = User.objects.create_user(username=username, email=email or "", password=password)
        UserProfile.objects.create(user=user, company=company, role=UserProfile.ROLE_OWNER)

        messages.success(request, f"Business ‘{company.name}’ created. Owner login: {username}")
        return redirect("platform_create_business")

    companies = Company.objects.all().order_by("-created_at")
    return render(request, "inventory/platform_create_business.html", {"companies": companies})
