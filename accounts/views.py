from django.contrib.auth import get_user_model
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from django.utils.decorators import method_decorator
from django.views.decorators.debug import sensitive_post_parameters
from django_ratelimit.decorators import ratelimit
from rest_framework.permissions import IsAuthenticated
from rest_framework import serializers
from rest_framework import generics
from .serializers import ProfileCompletionSerializer

from . import serializers
import logging

logger = logging.getLogger(__name__)
User = get_user_model()

# MODIFIED: Rates are now less sensitive for production
otp_ratelimit = method_decorator(
    ratelimit(key="ip", rate="2000/h", method="POST", block=True), name="dispatch"
)
auth_ratelimit = method_decorator(
    ratelimit(key="ip", rate="6000/h", method="POST", block=True), name="dispatch"
)
sensitive_data_decorator = method_decorator(
    sensitive_post_parameters("password", "otp", "token"), name="dispatch"
)


@otp_ratelimit
@sensitive_data_decorator
class OTPRequestView(generics.GenericAPIView):
    permission_classes = [AllowAny]
    serializer_class = serializers.OTPRequestSerializer
    queryset = User.objects.none()

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        otp_request = serializer.save()
        return Response(
            {
                "message": "OTP has been sent to your phone number.",
                "request_id": otp_request.request_id,
            },
            status=status.HTTP_201_CREATED,
        )


@otp_ratelimit
@sensitive_data_decorator
class OTPVerifyView(generics.GenericAPIView):
    permission_classes = [AllowAny]
    serializer_class = serializers.OTPVerifySerializer
    # FIX:
    queryset = User.objects.none()
    # renderer_classes = [JSONRenderer]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.save()
        return Response(data, status=status.HTTP_200_OK)


@auth_ratelimit
@sensitive_data_decorator
class RegistrationCompleteView(generics.CreateAPIView):
    """
    Endpoint to complete user registration.
    On success, it automatically logs the user in and returns JWT tokens.
    """

    permission_classes = [AllowAny]
    serializer_class = serializers.RegistrationCompleteSerializer
    queryset = User.objects.none()

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        refresh = RefreshToken.for_user(user)
        profile_status = user.get_profile_completion_status()

        data = {
            "refresh": str(refresh),
            "access": str(refresh.access_token),
            "profile_incomplete": not profile_status["is_complete"],
        }
        if not profile_status["is_complete"]:
            data["missing_fields"] = profile_status["missing_fields"]

        return Response(data, status=status.HTTP_201_CREATED)


@auth_ratelimit
@sensitive_data_decorator
class CustomTokenObtainPairView(generics.GenericAPIView):
    permission_classes = [AllowAny]
    serializer_class = serializers.CustomTokenObtainPairSerializer
    queryset = User.objects.none()

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.validated_data, status=status.HTTP_200_OK)


@auth_ratelimit
class PasswordResetRequestView(generics.GenericAPIView):
    permission_classes = [AllowAny]
    serializer_class = serializers.PasswordResetRequestSerializer
    queryset = User.objects.none()

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {
                "message": "If an account with that username exists, a password reset link has been sent to the associated email."
            },
            status=status.HTTP_200_OK,
        )


@auth_ratelimit
@sensitive_data_decorator
class PasswordResetConfirmView(generics.GenericAPIView):
    permission_classes = [AllowAny]
    serializer_class = serializers.PasswordResetConfirmSerializer
    queryset = User.objects.none()

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {
                "message": "Your password has been reset successfully. You can now log in with your new password."
            },
            status=status.HTTP_200_OK,
        )


class CompleteProfileView(generics.UpdateAPIView):
    """
    View for authenticated users to complete their profile after login.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = serializers.ProfileCompletionSerializer

    def get_object(self):
        return self.request.user

    def patch(self, request, *args, **kwargs):
        response = super().patch(request, *args, **kwargs)
        profile_status = self.request.user.get_profile_completion_status()

        return Response(
            {
                "message": "Profile updated successfully.",
                "profile_incomplete": not profile_status["is_complete"],
                "missing_fields": profile_status["missing_fields"],
            },
            status=response.status_code,
        )


class RetrieveProfileView(generics.RetrieveAPIView):
    """
    GET: view for see profile
    """

    permission_classes = [IsAuthenticated]
    serializer_class = ProfileCompletionSerializer

    def get_object(self):
        return self.request.user


class UserProfileView(generics.RetrieveAPIView):
    """
    Retrieve the public profile of a specific user.
    Only accessible to authenticated users
    """

    permission_classes = [IsAuthenticated]
    serializer_class = serializers.ProfileCompletionSerializer
    queryset = User.objects.all()
    lookup_field = "id"
