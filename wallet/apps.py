# wallet/apps.py
from django.apps import AppConfig


class WalletConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "wallet"
    verbose_name = "Wallet Management"

    def ready(self):
        import wallet.signals  # noqa: F401
