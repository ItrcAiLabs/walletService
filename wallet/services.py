# wallet/services.py
from decimal import Decimal
from django.db import transaction
from .models import Wallet, WalletTransaction, Payment
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings
from .models import Payment
import requests

class WalletService:
    @staticmethod
    def charge_wallet(wallet: Wallet, amount: Decimal) -> Wallet:
        if amount <= 0:
            raise ValueError("The charge amount must be positive.")

        wallet.balance += amount
        wallet.save(update_fields=["balance", "updated_at"])

        WalletTransaction.objects.create(
            wallet=wallet,
            transaction_type="CHARGE",
            amount=amount,
            description="Wallet charged",
        )

        return wallet

    @staticmethod
    def transfer_funds(sender_wallet: Wallet, receiver_wallet_id: str, amount: Decimal):
        if sender_wallet.id == receiver_wallet_id:
            raise ValueError("Cannot transfer funds to your own wallet.")
        if amount <= 0:
            raise ValueError("The transfer amount must be positive.")

        with transaction.atomic():
            sender = Wallet.objects.select_for_update().get(id=sender_wallet.id)

            if sender.balance < amount:
                raise ValueError("Insufficient funds.")

            try:
                receiver = Wallet.objects.select_for_update().get(id=receiver_wallet_id)
            except Wallet.DoesNotExist:
                raise ValueError("Receiver's wallet not found.")

            sender.balance -= amount
            receiver.balance += amount

            sender.save(update_fields=["balance", "updated_at"])
            receiver.save(update_fields=["balance", "updated_at"])

            WalletTransaction.objects.create(
                wallet=sender,
                transaction_type="TRANSFER_OUT",
                amount=amount,
                description=f"Transferred to {receiver.user.username}",
            )
            WalletTransaction.objects.create(
                wallet=receiver,
                transaction_type="TRANSFER_IN",
                amount=amount,
                description=f"Received from {sender.user.username}",
            )

    @staticmethod
    def settle_funds(wallet: Wallet, amount: Decimal) -> Wallet:
        if amount <= 0:
            raise ValueError("The settlement amount must be positive.")

        with transaction.atomic():
            wallet_to_settle = Wallet.objects.select_for_update().get(id=wallet.id)

            if wallet_to_settle.balance < amount:
                raise ValueError("Insufficient funds for settlement.")

            wallet_to_settle.balance -= amount
            wallet_to_settle.save(update_fields=["balance", "updated_at"])

            WalletTransaction.objects.create(
                wallet=wallet_to_settle,
                transaction_type="SETTLEMENT",
                amount=amount,
                description="Settlement to bank",
            )

        return wallet_to_settle






# Zarinpal settings
ZARINPAL_MERCHANT_ID = '11111122222233333344444455555566666'
ZP_API_REQUEST = "https://sandbox.zarinpal.com/pg/v4/payment/request.json"
ZP_API_VERIFY = "https://sandbox.zarinpal.com/pg/v4/payment/verify.json"
ZP_API_STARTPAY = "https://sandbox.zarinpal.com/pg/StartPay/"
ZARINPAL_CALLBACK_URL = 'http://yourdomain.com/payment/verify/'


class PaymentRequestView(APIView):
    def post(self, request):
        serializer = PaymentRequestSerializer(data=request.data)
        if serializer.is_valid():
            amount = serializer.validated_data['amount']
            description = serializer.validated_data['description']
            email = serializer.validated_data.get('email', '')
            mobile = serializer.validated_data.get('mobile', '')

            payload = {
                "merchant_id": ZARINPAL_MERCHANT_ID,
                "amount": amount,
                "callback_url": ZARINPAL_CALLBACK_URL,
                "description": description,
                "metadata": {"email": email, "mobile": mobile}
            }

            try:
                response = requests.post(ZP_API_REQUEST, json=payload)
                
                result = response.json()
                print(result)
                if result['data']:
                    authority = result['data']['authority']
                    payment = Payment.objects.create(
                        wallet=request.wallet.id,
                        amount=amount,
                        description=description,
                        email=email,
                        mobile=mobile,
                        authority=authority,
                        status='pending'
                    )
                    payment_url = f"{ZP_API_STARTPAY}{authority}"
                    return Response({
                        "status": "success",
                        "payment_url": payment_url
                    }, status=status.HTTP_200_OK)
                else:
                    return Response({
                        "status": "error",
                        "errors": result['errors']
                    }, status=status.HTTP_400_BAD_REQUEST)
            except requests.RequestException as e:
                return Response({
                    "status": "error",
                    "errors": str(e)
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class PaymentVerifyView(APIView):
    def get(self, request):
        authority = request.query_params.get('Authority')
        payment_status = request.query_params.get('Status')

        if not authority or not payment_status:
            return Response({
                "status": "error",
                "errors": "Authority or Status parameters didnt given"
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            payment = Payment.objects.get(authority=authority)
        except Payment.DoesNotExist:
            return Response({
                "status": "error",
                "errors": "payment not found"
            }, status=status.HTTP_404_NOT_FOUND)

        if payment_status == 'OK':
            payload = {
                "merchant_id": ZARINPAL_MERCHANT_ID,
                "amount": payment.amount,
                "authority": authority
            }
            try:
                response = requests.post(ZP_API_VERIFY, json=payload)
                result = response.json()

                if result['data']['code'] == 100:
                    payment.status = 'success'
                    payment.save()
                    serializer = PaymentVerifySerializer(payment)
                    return Response({
                        "status": "success",
                        "data": serializer.data,
                        "ref_id": result['data']['ref_id']
                    }, status=status.HTTP_200_OK)
                else:
                    payment.status = 'failed'
                    payment.save()
                    return Response({
                        "status": "error",
                        "errors": result['errors']
                    }, status=status.HTTP_400_BAD_REQUEST)
            except requests.RequestException as e:
                payment.status = 'failed'
                payment.save()
                return Response({
                    "status": "error",
                    "errors": str(e)
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        else:
            payment.status = 'canceled'
            payment.save()
            return Response({
                "status": "error",
                "errors": "payment canceled"},
                status=status.HTTP_400_BAD_REQUEST)