from django.urls import path
from . import views

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("register/", views.register, name="register"),
    path("setup/", views.setup_company, name="setup_company"),
    path("platform/create-business/", views.platform_create_business, name="platform_create_business"),

    path("team/", views.manage_team, name="manage_team"),
    path("categories/", views.manage_categories, name="manage_categories"),
    path("items/<int:item_id>/edit/", views.edit_item, name="edit_item"),
    path("reports/sales/", views.sales_report, name="sales_report"),

    path("export/inventory/", views.export_inventory_csv, name="export_inventory_csv"),
    path("export/sales/", views.export_sales_csv, name="export_sales_csv"),

    path("record-sale/", views.record_sale, name="record_sale"),
    path("record-stock-in/", views.record_stock_in, name="record_stock_in"),
    path("scan-ledger/", views.scan_ledger, name="scan_ledger"),
]
