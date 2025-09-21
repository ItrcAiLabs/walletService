from rest_framework import serializers
from django.contrib.auth import get_user_model, password_validation
from django.contrib.auth.hashers import make_password, check_password
from django.core.signing import TimestampSigner, BadSignature, SignatureExpired
from django.core.exceptions import ValidationError
from django.conf import settings
from datetime import timedelta
from .models import OTPRequest, PasswordHistory
from . import services
import logging

User = get_user_model()
logger = logging.getLogger(__name__)


class OTPRequestSerializer(serializers.Serializer):
    phone_number = serializers.CharField(max_length=15)

    def create(self, validated_data):
        phone = validated_data["phone_number"]
        otp = services.generate_otp()
        otp_hash = make_password(otp)

        OTPRequest.objects.filter(phone_number=phone).delete()

        otp_request = OTPRequest.objects.create(phone_number=phone, otp_hash=otp_hash)

        services.send_otp_sms(phone, otp)

        logger.info(f"OTP generated for {phone}. Request ID: {otp_request.request_id}")
        return otp_request


class OTPVerifySerializer(serializers.Serializer):
    phone_number = serializers.CharField(max_length=15)
    otp = serializers.CharField(max_length=6, write_only=True)
    request_id = serializers.UUIDField(write_only=True)
    registration_token = serializers.CharField(read_only=True)

    def validate(self, attrs):
        phone = attrs["phone_number"]
        otp = attrs["otp"]
        request_id = attrs["request_id"]

        try:
            otp_request = OTPRequest.objects.get(
                request_id=request_id, phone_number=phone
            )
        except OTPRequest.DoesNotExist:
            raise serializers.ValidationError("Invalid request ID or phone number.")

        if otp_request.is_expired(settings.OTP_EXPIRATION_MINUTES):
            otp_request.delete()
            raise serializers.ValidationError(
                "OTP has expired. Please request a new one."
            )

        if not check_password(otp, otp_request.otp_hash):
            raise serializers.ValidationError("Invalid OTP.")

        attrs["otp_request_instance"] = otp_request
        return attrs

    def create(self, validated_data):
        otp_request = validated_data["otp_request_instance"]
        return {"registration_token": str(otp_request.registration_token)}


class RegistrationCompleteSerializer(serializers.ModelSerializer):
    registration_token = serializers.UUIDField(write_only=True)

    class Meta:
        model = User
        fields = ("registration_token", "username", "password")
        extra_kwargs = {
            "password": {"write_only": True, "style": {"input_type": "password"}},
        }

    def validate_password(self, value):
        password_validation.validate_password(value)
        return value

    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("This username is already taken.")
        return value

    def validate(self, attrs):
        """
        ‌ validate on registration_token و phone_number
        """
        token = attrs.get("registration_token")

        try:
            otp_request = OTPRequest.objects.get(registration_token=token)
        except OTPRequest.DoesNotExist:
            raise serializers.ValidationError(
                {"registration_token": "Invalid or expired registration token."}
            )

        if otp_request.is_expired(settings.REGISTRATION_TOKEN_EXPIRATION_MINUTES):
            otp_request.delete()
            raise serializers.ValidationError(
                {"registration_token": "Registration token has expired."}
            )

        phone = otp_request.phone_number
        if User.objects.filter(phone_number=phone).exists():
            raise serializers.ValidationError(
                {"phone_number": "This phone number is already registered."}
            )

        # Attach to context for use in create()
        self.context["otp_request"] = otp_request
        return attrs

    def create(self, validated_data):
        otp_request = self.context["otp_request"]

        user = User.objects.create_user(
            username=validated_data["username"],
            password=validated_data["password"],
            phone_number=otp_request.phone_number,
        )

        PasswordHistory.objects.create(user=user, password_hash=user.password)

        otp_request.delete()

        logger.info(f"User '{user.username}' created successfully.")
        return user


class CustomTokenObtainPairSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)
    access = serializers.CharField(read_only=True)
    refresh = serializers.CharField(read_only=True)
    profile_incomplete = serializers.BooleanField(read_only=True)
    missing_fields = serializers.ListField(
        child=serializers.CharField(), read_only=True, required=False
    )

    def validate(self, attrs):
        from rest_framework_simplejwt.tokens import RefreshToken

        username = attrs.get("username")
        password = attrs.get("password")

        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            raise serializers.ValidationError(
                "No active account found with the given credentials."
            )

        if not user.check_password(password):
            raise serializers.ValidationError(
                "No active account found with the given credentials."
            )

        if not user.is_active:
            raise serializers.ValidationError("User account is disabled.")

        refresh = RefreshToken.for_user(user)

        profile_status = user.get_profile_completion_status()

        data = {
            "refresh": str(refresh),
            "access": str(refresh.access_token),
            "profile_incomplete": not profile_status["is_complete"],
        }

        if not profile_status["is_complete"]:
            data["missing_fields"] = profile_status["missing_fields"]

        return data


class PasswordResetRequestSerializer(serializers.Serializer):
    username = serializers.CharField()

    def save(self):
        try:
            user = User.objects.get(
                username=self.validated_data["username"], is_active=True
            )
        except User.DoesNotExist:
            logger.warning(
                f"Password reset requested for non-existent user: {self.validated_data['username']}"
            )
            return

        if not user.email:
            logger.error(
                f"Password reset failed for user '{user.username}': No email is registered."
            )
            return

        signer = TimestampSigner()
        token = signer.sign(str(user.pk))

        reset_link = f"https://your-frontend.com/reset-password?token={token}"

        services.send_password_reset_email(user.email, reset_link)
        logger.info(f"Password reset link sent for user '{user.username}'.")


class PasswordResetConfirmSerializer(serializers.Serializer):
    token = serializers.CharField(write_only=True)
    username = serializers.CharField(write_only=True)
    password = serializers.CharField(write_only=True, style={"input_type": "password"})

    def validate(self, attrs):
        signer = TimestampSigner()
        try:
            user_pk = signer.unsign(
                attrs["token"],
                max_age=timedelta(
                    minutes=settings.PASSWORD_RESET_TOKEN_EXPIRATION_MINUTES
                ),
            )
            user_id = int(user_pk)
        except SignatureExpired:
            raise serializers.ValidationError(
                {"non_field_errors": ["The password reset link has expired."]}
            )
        except BadSignature:
            raise serializers.ValidationError(
                {"non_field_errors": ["Invalid password reset link."]}
            )

        try:
            user = User.objects.get(
                pk=user_id, username=attrs["username"], is_active=True
            )
        except User.DoesNotExist:
            raise serializers.ValidationError(
                {"non_field_errors": ["Invalid user or token."]}
            )

        try:
            password_validation.validate_password(attrs["password"], user=user)
        except ValidationError as e:
            raise serializers.ValidationError({"password": e.messages})

        attrs["user"] = user
        return attrs

    def save(self):
        user = self.validated_data["user"]
        password = self.validated_data["password"]

        user.set_password(password)
        user.save()

        PasswordHistory.objects.create(user=user, password_hash=user.password)

        history_limit = settings.PREVIOUS_PASSWORD_COUNT
        old_passwords = user.password_history.all()[history_limit:]
        for old_pass in old_passwords:
            old_pass.delete()

        logger.info(f"Password for user '{user.username}' has been successfully reset.")
        return user


class ProfileCompletionSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "first_name",
            "last_name",
            "email",
            "gender",
            "job_title",
            "field_of_study",
            "company",
            "bank_account_number",
        ]

    def validate_email(self, value):
        if (
            value
            and User.objects.exclude(pk=self.instance.pk).filter(email=value).exists()
        ):
            raise serializers.ValidationError("This email is already registered.")
        return value

    def update(self, instance, validated_data):
        for field, value in validated_data.items():
            setattr(instance, field, value)
        instance.save()
        return instance
