import json
import os

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import F, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from google import genai
from google.genai import types
from PIL import Image

from .models import Category, Company, Item, Sale, StockIn, UserProfile


def get_user_company(request):
    """Return the company for the logged-in user, or None if not set up yet."""
    if not hasattr(request.user, "profile"):
        return None
    return request.user.profile.company


@login_required
def dashboard(request):
    company = get_user_company(request)
    if company is None:
        return redirect("setup_company")

    items = (
        Item.objects.filter(company=company)
        .select_related("category")
        .order_by("name")
    )
    categories = Category.objects.filter(company=company)
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
    total_inventory_val = sum(
        item.quantity_in_stock * item.buy_price for item in items
    )

    context = {
        "company": company,
        "items": items,
        "categories": categories,
        "recent_sales": recent_sales,
        "low_stock_count": low_stock_items.count(),
        "total_inventory_val": total_inventory_val,
        "today_sales_total": today_sales_total,
        "is_owner": request.user.profile.is_owner,
    }
    return render(request, "inventory/dashboard.html", context)


@login_required
def setup_company(request):
    """First-time setup: create a company and link the current user as Owner."""
    # If they already have a profile, send them to the dashboard
    if hasattr(request.user, "profile"):
        return redirect("dashboard")

    if request.method == "POST":
        name = request.POST.get("company_name", "").strip()

        if not name:
            messages.error(request, "Please enter a company / business name.")
            return render(request, "inventory/setup_company.html")

        if Company.objects.filter(name__iexact=name).exists():
            messages.error(
                request,
                "A company with that name already exists. Choose a different name or contact support.",
            )
            return render(request, "inventory/setup_company.html")

        company = Company.objects.create(name=name)
        UserProfile.objects.create(
            user=request.user,
            company=company,
            role=UserProfile.ROLE_OWNER,
        )

        messages.success(
            request,
            f"Welcome! Your company ‘{company.name}’ has been created. You are the Owner.",
        )
        return redirect("dashboard")

    return render(request, "inventory/setup_company.html")


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
            messages.error(
                request,
                f"Not enough stock for {item.name}. Only {item.quantity_in_stock} left.",
            )
            return redirect("dashboard")

        Sale.objects.create(
            company=company,
            item=item,
            quantity_sold=quantity,
            sell_price=sell_price,
        )
        item.quantity_in_stock -= quantity
        item.save()

        messages.success(
            request,
            f"Sold {quantity} × {item.name} for UGX {sell_price}.",
        )

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

        category = (
            Category.objects.filter(id=category_id, company=company).first()
            if category_id
            else None
        )

        item, created = Item.objects.get_or_create(
            company=company,
            name__iexact=item_name,
            defaults={
                "name": item_name,
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

        StockIn.objects.create(
            company=company, item=item, quantity_added=quantity
        )

        action = "Created and stocked" if created else "Restocked"
        messages.success(
            request,
            f"{action} {item.name}: +{quantity} units.",
        )

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
            messages.error(
                request,
                "GEMINI_API_KEY is not set. Add it to your .env file to use the scanner.",
            )
            return redirect("dashboard")

        try:
            img = Image.open(photo)
            client = genai.Client(api_key=api_key)

            prompt = """
Analyze this handwritten stock ledger page. Extract all products and return a strict JSON list.
Regardless of column arrangement or missing headers, identify:
- name: string
- buy_price: number (default to 0)
- sell_price: number (default to 0)
- quantity: integer (default to 1)

Example output:
[{"name": "Standing Fan", "buy_price": 10000, "sell_price": 20000, "quantity": 5}]
"""

            response = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=[prompt, img],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json"
                ),
            )

            items_data = json.loads(response.text)
            added_count = 0

            for entry in items_data:
                name = str(entry.get("name", "")).strip()
                if not name:
                    continue

                buy_price = float(entry.get("buy_price") or 0)
                sell_price = float(entry.get("sell_price") or 0)
                quantity = int(entry.get("quantity") or 1)

                item, created = Item.objects.get_or_create(
                    company=company,
                    name__iexact=name,
                    defaults={
                        "name": name,
                        "buy_price": buy_price,
                        "sell_price": sell_price,
                        "quantity_in_stock": 0,
                    },
                )

                item.quantity_in_stock += quantity
                if buy_price > 0:
                    item.buy_price = buy_price
                if sell_price > 0:
                    item.sell_price = sell_price
                item.save()

                StockIn.objects.create(
                    company=company, item=item, quantity_added=quantity
                )
                added_count += 1

            if added_count:
                messages.success(
                    request,
                    f"Successfully imported {added_count} item(s) from the ledger photo.",
                )
            else:
                messages.warning(
                    request,
                    "No products could be extracted from the image. Try a clearer photo.",
                )

        except Exception as e:
            messages.error(request, f"Error parsing ledger image: {e}")

    return redirect("dashboard")
