from django.urls import path
from . import views
from . import features

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("sell/", features.sell, name="sell"),
    path("register/", views.register, name="register"),
    path("setup/", views.setup_company, name="setup_company"),
    path("today/", features.today, name="today"),

    path("accounts/google/", features.google_start, name="google_start"),
    path("accounts/google/callback/", features.google_callback, name="google_callback"),
    path("accounts/password-reset/", features.password_reset_request, name="password_reset_request"),
    path("accounts/password-reset/confirm/", features.password_reset_confirm, name="password_reset_confirm"),

    path("platform/", views.platform_admin, name="platform_admin"),
    path("platform/create-business/", views.platform_create_business, name="platform_create_business"),
    path("platform/activate/<int:sub_id>/", views.platform_activate_sub, name="platform_activate_sub"),
    path("platform/suspend/<int:sub_id>/", views.platform_suspend_sub, name="platform_suspend_sub"),
    path("platform/extend/<int:sub_id>/", views.platform_extend_sub, name="platform_extend_sub"),

    path("team/", views.manage_team, name="manage_team"),
    path("categories/", views.manage_categories, name="manage_categories"),
    path("items/<int:item_id>/edit/", views.edit_item, name="edit_item"),
    path("items/<int:item_id>/delete/", features.delete_item, name="delete_item"),
    path("shop/rename/", features.rename_shop, name="rename_shop"),
    path("reports/sales/", views.sales_report, name="sales_report"),

    path("billing/", views.billing, name="billing"),
    path("billing/claim/", views.claim_payment, name="claim_payment"),

    path("import/", views.import_inventory, name="import_inventory"),

    path("export/inventory/", views.export_inventory_csv, name="export_inventory_csv"),
    path("export/sales/", views.export_sales_csv, name="export_sales_csv"),

    path("record-sale/", views.record_sale, name="record_sale"),
    path("record-stock-in/", views.record_stock_in, name="record_stock_in"),
    path("scan-ledger/", views.scan_ledger, name="scan_ledger"),
]
