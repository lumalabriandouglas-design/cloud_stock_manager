from django.urls import path
from . import views

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("setup/", views.setup_company, name="setup_company"),
    path("platform/create-business/", views.platform_create_business, name="platform_create_business"),
    path("record-sale/", views.record_sale, name="record_sale"),
    path("record-stock-in/", views.record_stock_in, name="record_stock_in"),
    path("scan-ledger/", views.scan_ledger, name="scan_ledger"),
]
