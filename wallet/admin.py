from django.contrib import admin
from .models import (
    Wallet,
    WalletTransaction,
    Payment
)



admin.site.register(Wallet)
admin.site.register(WalletTransaction)
admin.site.register(Payment)