# wallet/views.py
from rest_framework import status, generics
from rest_framework.generics import GenericAPIView
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .serializers import (
    WalletSerializer,
    WalletTransactionSerializer,
    ChargeWalletSerializer,
    TransferSerializer,
    SettlementSerializer,
    PaymentRequestSerializer,
    PaymentVerifySerializer,
)
from .services import WalletService
from .models import WalletTransaction, Payment
from decimal import Decimal
import requests


ZARINPAL_MERCHANT_ID = 'cb2833bb-f8d9-4535-9b16-b68202fc686a'
ZP_API_REQUEST = "https://sandbox.zarinpal.com/pg/v4/payment/request.json"
ZP_API_VERIFY = "https://sandbox.zarinpal.com/pg/v4/payment/verify.json"
ZP_API_STARTPAY = "https://sandbox.zarinpal.com/pg/StartPay/"
ZARINPAL_CALLBACK_URL = 'http://127.0.0.1:8000'




class WalletDetailView(generics.RetrieveAPIView):
    serializer_class = WalletSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user.wallet


class WalletTransactionsView(generics.ListAPIView):
    serializer_class = WalletTransactionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return WalletTransaction.objects.filter(
            wallet=self.request.user.wallet
        ).order_by("-created_at")[:10]


class ChargeWalletView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request, *args, **kwargs):
        serializer = ChargeWalletSerializer(data=request.data)
        if serializer.is_valid():
            amount = serializer.validated_data["amount"]
            try:
                WalletService.charge_wallet(request.user.wallet, amount)
                return Response(
                    {"message": "Wallet charged successfully."},
                    status=status.HTTP_200_OK,
                )
            except Exception as e:
                return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PaymentRequestView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = PaymentRequestSerializer
    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data = request.data)
        if serializer.is_valid():
            amount = serializer.validated_data["amount"] 
            description = serializer.validated_data.get("description", "Charge Wallet")
            email = serializer.validated_data.get("email", request.user.email or "")
            mobile = serializer.validated_data.get("mobile", request.user.phone_number or "")
            

            payload = {
                "merchant_id": ZARINPAL_MERCHANT_ID,
                "amount": amount,
                "description": description,
                "callback_url": ZARINPAL_CALLBACK_URL,
                "metadata": {"email": email, "mobile": mobile},
             }
            
            try:
                # Send request to ZarinPal
                response = requests.post(ZP_API_REQUEST, json=payload)
                result = response.json()
                """
                response is something like this :

                {
                "data": {
                    "authority": "S000000000000000000000000000000e3wwm",
                    "fee": 1000,
                    "fee_type": "Merchant",
                    "code": 100,
                    "message": "Success"
                    },
                "errors": []
                }
                """

                if result.get("data") and result["data"].get("code") == 100:
                    authority = result["data"]["authority"]
                    payment_url = f"{ZP_API_STARTPAY}{authority}"
                    
                    payment = Payment.objects.create(
                        wallet=request.user.wallet,
                        amount=amount,
                        status="pending",
                        authority=authority,
                    )

                    return Response(
                        {
                            "status": "success",
                            "payment_url": payment_url,
                            "authority": authority,
                        },
                        status=status.HTTP_200_OK,
                    )
                else:
                    errors = result.get("errors", "Unknown error")
                    return Response(
                        {"status": "error", "errors": errors},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
            except requests.RequestException as e:
                return Response(
                    {"status": "error", "errors": str(e)},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)



class PaymentVerifyView(APIView):
    permission_classes=[IsAuthenticated]
    serializer_class = PaymentVerifySerializer
    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data = request.data)
        if serializer.is_valid():
            amount = serializer.validated_data["amount"] 
            authority = serializer.validated_data["authority"]

            verifyload = {
                "merchant_id": ZARINPAL_MERCHANT_ID,
                "amount": amount,
                "authority":authority
             }
            
            try:
                response = requests.post(ZP_API_VERIFY, json=verifyload)
                result = response.json()
                """
                response is something like this :
                {
                    "data": {
                        "wages": null,
                        "code": 101,
                        "message": "Verified",
                        "card_hash": "0866A6EAEA5CB085E4CF6EF19296BF19647552DD5F96F1E530DB3AE61837EFE7",
                        "card_pan": "999999******9999",
                        "ref_id": 10955701,
                        "fee_type": "Merchant",
                        "fee": 1000,
                        "shaparak_fee": 1200,
                        "order_id": null
                    },
                    "errors": []
                }
                """

                if result.get("data") and result["data"].get("code") in [100,101]:
                    wallet = request.user.wallet

                    WalletTransaction.objects.create(
                        wallet=wallet,
                        transaction_type="CHARGE",
                        amount=amount, 
                        description=f"Payment verified with authority {authority}",
                    )
                    

                    return Response(
                       {
                            "status": "success",
                            "message": "Transaction created successfully",
                            "authority": authority,
                        },
                        status=status.HTTP_200_OK,
                    )
                else:
                    errors = result.get("errors", "Unknown error")
                    return Response(
                        {"status": "error", "errors": errors},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
            except requests.RequestException as e:
                return Response(
                    {"status": "error", "errors": str(e)},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)










class TransferView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = TransferSerializer(data=request.data)
        if serializer.is_valid():
            data = serializer.validated_data
            try:
                WalletService.transfer_funds(
                    sender_wallet=request.user.wallet,
                    receiver_wallet_id=data["receiver_wallet_id"],
                    amount=data["amount"],
                )
                return Response(
                    {"message": "Transfer completed successfully."},
                    status=status.HTTP_200_OK,
                )
            except ValueError as e:
                return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class SettlementView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = SettlementSerializer(data=request.data)
        if serializer.is_valid():
            amount = serializer.validated_data["amount"]
            try:
                WalletService.settle_funds(request.user.wallet, amount)
                return Response(
                    {"message": "Settlement request submitted successfully."},
                    status=status.HTTP_200_OK,
                )
            except ValueError as e:
                return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
