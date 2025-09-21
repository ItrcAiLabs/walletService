from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from decimal import Decimal
from accounts.models import User
from wallet.models import WalletTransaction


class WalletTests(APITestCase):
    """
    Comprehensive tests for the Wallet app:
    - Wallet auto-creation
    - Initial bonus
    - Charging
    - Transfers
    - Settlements
    - Transaction history
    """

    def setUp(self):
        self.user1 = User.objects.create_user(username="user1", password="password123")
        self.user2 = User.objects.create_user(username="user2", password="password123")
        self.wallet1 = self.user1.wallet
        self.wallet2 = self.user2.wallet

    def test_wallet_auto_creation_with_bonus(self):
        """Each new user should get a wallet with a 50,000 bonus."""
        self.assertEqual(self.wallet1.balance, Decimal("50000.00"))
        self.assertEqual(self.wallet2.balance, Decimal("50000.00"))

        tx = self.wallet1.transactions.first()
        self.assertEqual(tx.transaction_type, "CHARGE")
        self.assertEqual(tx.amount, Decimal("50000.00"))

    def test_charge_wallet_success_and_failure(self):
        self.client.force_authenticate(user=self.user1)
        charge_url = reverse("wallet:wallet_charge")

        # Success
        response = self.client.post(charge_url, {"amount": "1000.00"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.wallet1.refresh_from_db()
        self.assertEqual(self.wallet1.balance, Decimal("51000.00"))

        # Invalid (negative amount)
        response = self.client.post(charge_url, {"amount": "-10.00"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_transfer_success_and_failures(self):
        self.client.force_authenticate(user=self.user1)
        transfer_url = reverse("wallet:wallet_transfer")

        # Success transfer
        response = self.client.post(
            transfer_url,
            {"receiver_wallet_id": str(self.wallet2.id), "amount": "500.00"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.wallet1.refresh_from_db()
        self.wallet2.refresh_from_db()
        self.assertEqual(self.wallet1.balance, Decimal("49500.00"))
        self.assertEqual(self.wallet2.balance, Decimal("50500.00"))

        # Failure: insufficient funds
        response = self.client.post(
            transfer_url,
            {"receiver_wallet_id": str(self.wallet2.id), "amount": "9999999.00"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Failure: transfer to self
        response = self.client.post(
            transfer_url,
            {"receiver_wallet_id": str(self.wallet1.id), "amount": "100.00"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Failure: invalid wallet
        response = self.client.post(
            transfer_url,
            {
                "receiver_wallet_id": "00000000-0000-0000-0000-000000000000",
                "amount": "100.00",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_settlement_success_and_failures(self):
        self.client.force_authenticate(user=self.user1)
        settle_url = reverse("wallet:wallet_settle")

        # Success
        response = self.client.post(settle_url, {"amount": "1000.00"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.wallet1.refresh_from_db()
        self.assertEqual(self.wallet1.balance, Decimal("49000.00"))

        # Failure: insufficient funds
        response = self.client.post(settle_url, {"amount": "9999999.00"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Failure: negative amount
        response = self.client.post(settle_url, {"amount": "-10.00"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_transaction_history_limit(self):
        """Should return the last 10 transactions only."""
        self.client.force_authenticate(user=self.user1)
        charge_url = reverse("wallet:wallet_charge")

        # Make 15 charges
        for i in range(15):
            self.client.post(charge_url, {"amount": "1.00"}, format="json")

        transactions_url = reverse("wallet:wallet_transactions")
        response = self.client.get(transactions_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertEqual(len(data), 10)  # last 10 only

        # Verify the latest transaction is the most recent
        latest_tx = (
            WalletTransaction.objects.filter(wallet=self.wallet1)
            .order_by("-created_at")
            .first()
        )
        self.assertEqual(str(latest_tx.id), data[0]["id"])
