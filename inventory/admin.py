from django.contrib import admin
from .models import Category, Company, Item, Sale, StockIn, UserProfile

admin.site.site_header = "SaaS Inventory Management Admin"
admin.site.site_title = "Inventory Portal Admin"
admin.site.index_title = "System Administration"


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
  list_display = ("name", "created_at")
  search_fields = ("name",)


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
  list_display = ("user", "company")
  list_filter = ("company",)
  search_fields = ("user__username", "user__email", "company__name")


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
  list_display = ("name", "company")
  list_filter = ("company",)
  search_fields = ("name", "company__name")


@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
  list_display = (
      "name",
      "company",
      "category",
      "quantity_in_stock",
      "buy_price",
      "sell_price",
  )
  list_filter = ("company", "category")
  search_fields = ("name", "company__name")
  readonly_fields = ("quantity_in_stock",)


@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
  list_display = (
      "item",
      "company",
      "quantity_sold",
      "sell_price",
      "sales_date",
  )
  list_filter = ("company", "sales_date")
  search_fields = ("item__name", "company__name")
  fields = ("company", "item", "quantity_sold", "sell_price")


@admin.register(StockIn)
class StockInAdmin(admin.ModelAdmin):
  list_display = ("item", "company", "quantity_added", "entry_date")
  list_filter = ("company", "entry_date")
  search_fields = ("item__name", "company__name")
  fields = ("company", "item", "quantity_added")