# wallet/urls.py
from django.urls import path
from .views import (
    WalletDetailView,
    WalletTransactionsView,
    ChargeWalletView,
    TransferView,
    SettlementView,
    PaymentRequestView,
    PaymentVerifyView
)


app_name = "wallet"

urlpatterns = [
    path("", WalletDetailView.as_view(), name="wallet_detail"),
    path("transactions/", WalletTransactionsView.as_view(), name="wallet_transactions"),
    path("charge/", ChargeWalletView.as_view(), name="wallet_charge"),
    path("transfer/", TransferView.as_view(), name="wallet_transfer"),
    path("settle/", SettlementView.as_view(), name="wallet_settle"),
    path("payment/request/",PaymentRequestView.as_view(), name="payment_request"),
    path("payment/verify/",PaymentVerifyView.as_view(), name="payment_verify")
]