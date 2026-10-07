from django.urls import path
from . import views
from . import features
from . import debts
from .ajax import ajax_json

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("sell/", features.sell, name="sell"),
    path("register/", views.register, name="register"),
    path("setup/", views.setup_company, name="setup_company"),
    path("today/", features.today, name="today"),

    path("accounts/google/", features.google_start, name="google_start"),
    path("accounts/google/callback/", features.google_callback, name="google_callback"),
    path("accounts/google/link/", features.finish_google, name="finish_google"),
    path("accounts/password-reset/", features.password_reset_request, name="password_reset_request"),
    path("accounts/password-reset/confirm/", features.password_reset_confirm, name="password_reset_confirm"),

    path("platform/", views.platform_admin, name="platform_admin"),
    path("platform/create-business/", views.platform_create_business, name="platform_create_business"),
    path("platform/activate/<int:sub_id>/", views.platform_activate_sub, name="platform_activate_sub"),
    path("platform/suspend/<int:sub_id>/", views.platform_suspend_sub, name="platform_suspend_sub"),
    path("platform/extend/<int:sub_id>/", views.platform_extend_sub, name="platform_extend_sub"),

    path("team/", views.manage_team, name="manage_team"),
    path("categories/", views.manage_categories, name="manage_categories"),
    path("items/<int:item_id>/edit/", ajax_json(views.edit_item), name="edit_item"),
    path("items/<int:item_id>/delete/", ajax_json(features.delete_item), name="delete_item"),
    path("shop/rename/", features.rename_shop, name="rename_shop"),
    path("reports/sales/", views.sales_report, name="sales_report"),

    path("billing/", views.billing, name="billing"),
    path("billing/claim/", views.claim_payment, name="claim_payment"),

    path("import/", views.import_inventory, name="import_inventory"),

    path("export/inventory/", views.export_inventory_csv, name="export_inventory_csv"),
    path("export/sales/", views.export_sales_csv, name="export_sales_csv"),

    path("record-sale/", ajax_json(views.record_sale), name="record_sale"),
    path("sales/<int:sale_id>/edit/", ajax_json(views.edit_sale), name="edit_sale"),
    path("sales/<int:sale_id>/delete/", ajax_json(views.delete_sale), name="delete_sale"),
    path("record-stock-in/", ajax_json(views.record_stock_in), name="record_stock_in"),
    path("debts/", debts.debt_list, name="debts"),
    path("debts/add/", debts.debt_add, name="debt_add"),
    path("debts/<int:debt_id>/", debts.debt_detail, name="debt_detail"),
    path("debts/<int:debt_id>/pay/", ajax_json(debts.debt_pay), name="debt_pay"),
    path("debts/<int:debt_id>/delete/", debts.debt_delete, name="debt_delete"),
    path("scan-ledger/", views.scan_ledger, name="scan_ledger"),
]
