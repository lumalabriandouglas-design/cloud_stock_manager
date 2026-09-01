import json
import os
from django.contrib.auth.decorators import login_required
from django.db.models import F, Sum
from django.shortcuts import redirect, render
from django.utils import timezone
from google import genai
from google.genai import types
from PIL import Image

from .models import Category, Item, Sale, StockIn


@login_required
def dashboard(request):
  # Extract the active company for the logged-in user
  company = request.user.profile.company

  items = Item.objects.filter(company=company).select_related('category').order_by('name')
  categories = Category.objects.filter(company=company)
  recent_sales = (
      Sale.objects.filter(company=company)
      .select_related('item')
      .order_by('-sales_date')[:8]
  )

  today = timezone.now().date()
  today_sales_total = (
      Sale.objects.filter(company=company, sales_date__date=today).aggregate(
          total=Sum(F('quantity_sold') * F('sell_price'))
      )['total']
      or 0
  )

  low_stock_items = items.filter(quantity_in_stock__lte=F('reorder_level'))
  total_inventory_val = sum(
      item.quantity_in_stock * item.buy_price for item in items
  )

  context = {
      'company': company,
      'items': items,
      'categories': categories,
      'recent_sales': recent_sales,
      'low_stock_count': low_stock_items.count(),
      'total_inventory_val': total_inventory_val,
      'today_sales_total': today_sales_total,
  }
  return render(request, 'inventory/dashboard.html', context)


@login_required
def record_sale(request):
  if request.method == 'POST':
    company = request.user.profile.company
    item_id = request.POST.get('item_id')
    quantity = int(request.POST.get('quantity', 1))
    custom_price = request.POST.get('sell_price')

    if item_id:
      item = Item.objects.get(id=item_id, company=company)
      sell_price = custom_price if custom_price else item.sell_price

      if item.quantity_in_stock >= quantity:
        Sale.objects.create(
            company=company,
            item=item,
            quantity_sold=quantity,
            sell_price=sell_price,
        )
        item.quantity_in_stock -= quantity
        item.save()

  return redirect('dashboard')


@login_required
def record_stock_in(request):
  if request.method == 'POST':
    company = request.user.profile.company
    item_name = request.POST.get('item_name', '').strip()
    category_id = request.POST.get('category_id')
    buy_price = request.POST.get('buy_price') or 0
    sell_price = request.POST.get('sell_price') or 0
    quantity = int(request.POST.get('quantity', 0))

    if item_name and quantity > 0:
      category = (
          Category.objects.filter(id=category_id, company=company).first()
          if category_id
          else None
      )
      item, created = Item.objects.get_or_create(
          company=company,
          name__iexact=item_name,
          defaults={
              'name': item_name,
              'category': category,
              'buy_price': buy_price,
              'sell_price': sell_price,
              'quantity_in_stock': 0,
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

  return redirect('dashboard')


@login_required
def scan_ledger(request):
  if request.method == 'POST' and request.FILES.get('ledger_photo'):
    company = request.user.profile.company
    photo = request.FILES['ledger_photo']

    try:
      img = Image.open(photo)
      api_key = os.getenv('GEMINI_API_KEY')

      if api_key:
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
            model='gemini-2.5-flash',
            contents=[prompt, img],
            config=types.GenerateContentConfig(response_mime_type='application/json'),
        )

        items_data = json.loads(response.text)

        for entry in items_data:
          name = str(entry.get('name', '')).strip()
          if not name:
            continue

          buy_price = float(entry.get('buy_price') or 0)
          sell_price = float(entry.get('sell_price') or 0)
          quantity = int(entry.get('quantity') or 1)

          item, created = Item.objects.get_or_create(
              company=company,
              name__iexact=name,
              defaults={
                  'name': name,
                  'buy_price': buy_price,
                  'sell_price': sell_price,
                  'quantity_in_stock': 0,
              },
          )

          item.quantity_in_stock += quantity
          if buy_price > 0:
            item.buy_price = buy_price
          if sell_price > 0:
            item.sell_price = sell_price
          item.save()

    except Exception as e:
      print(f'Error parsing ledger image: {e}')

  return redirect('dashboard')