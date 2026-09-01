from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('record-sale/', views.record_sale, name='record_sale'),
    path('record-stock-in/', views.record_stock_in, name='record_stock_in'),
    path('scan-ledger/', views.scan_ledger, name='scan_ledger'),
]