# wallet/serializers.py
from rest_framework import serializers
from decimal import Decimal
from .models import Wallet, WalletTransaction


class WalletSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField()

    class Meta:
        model = Wallet
        fields = ["id", "user", "balance", "currency", "updated_at"]


class WalletTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = WalletTransaction
        fields = ["id", "transaction_type", "amount", "description", "created_at"]


class ChargeWalletSerializer(serializers.Serializer):
    amount = serializers.DecimalField(
        max_digits=12, decimal_places=2, min_value=Decimal("1.00")
    )


class TransferSerializer(serializers.Serializer):
    receiver_wallet_id = serializers.UUIDField()
    amount = serializers.DecimalField(
        max_digits=12, decimal_places=2, min_value=Decimal("1.00")
    )


class SettlementSerializer(serializers.Serializer):
    amount = serializers.DecimalField(
        max_digits=12, decimal_places=2, min_value=Decimal("1.00")
    )
class PaymentRequestSerializer(serializers.Serializer):
    amount = serializers.IntegerField()
    description = serializers.CharField()
    email = serializers.EmailField()
    mobile = serializers.CharField()

class PaymentVerifySerializer(serializers.Serializer):
    amount = serializers.IntegerField()
    authority = serializers.CharField()