# wallet/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from accounts.models import User
from .models import Wallet, WalletTransaction
from decimal import Decimal


@receiver(post_save, sender=User)
def create_user_wallet(sender, instance, created, **kwargs):
    if created:
        # create wallet with initial balance
        wallet = Wallet.objects.create(
            user=instance, balance=Decimal("50000.00")  # initial free credit
        )

        # log welcome transaction
        WalletTransaction.objects.create(
            wallet=wallet,
            transaction_type="CHARGE",
            amount=Decimal("50000.00"),
            description="Welcome bonus credit",
        )
