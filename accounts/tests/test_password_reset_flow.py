# ==============================================================================
# accounts/tests/test_password_reset_flow.py
# ==============================================================================
import time
from django.urls import reverse
from django.test import override_settings
from rest_framework import status
from rest_framework.test import APITestCase
from unittest.mock import patch
from django.core.signing import TimestampSigner
from ..models import User, PasswordHistory
from django.conf import settings


@override_settings(RATELIMIT_ENABLED=False)
class PasswordResetFlowTests(APITestCase):
    def setUp(self):
        self.password = "InitialPass123!"
        self.user = User.objects.create_user(
            username="resetuser", password=self.password, email="reset@test.com"
        )
        PasswordHistory.objects.create(user=self.user, password_hash=self.user.password)
        self.reset_request_url = reverse("password-reset-request")
        self.reset_confirm_url = reverse("password-reset-confirm")

    @patch("accounts.services.send_password_reset_email")
    def test_password_reset_request_success(self, mock_send_email):
        """
        Ensure a password reset email can be requested.
        """
        data = {"username": self.user.username}
        response = self.client.post(self.reset_request_url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_send_email.assert_called_once()

    @patch("accounts.services.send_password_reset_email")
    def test_password_reset_request_non_existent_user(self, mock_send_email):
        """
        Ensure the endpoint doesn't reveal if a user exists.
        """
        data = {"username": "nonexistentuser"}
        response = self.client.post(self.reset_request_url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_send_email.assert_not_called()

    def test_password_reset_confirm_success(self):
        """
        Ensure a password can be reset with a valid token.
        """
        signer = TimestampSigner()
        token = signer.sign(str(self.user.pk))
        new_password = "NewPassword456!"

        data = {
            "token": token,
            "username": self.user.username,
            "password": new_password,
        }
        response = self.client.post(self.reset_confirm_url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(new_password))
        self.assertEqual(self.user.password_history.count(), 2)

    def test_password_reset_confirm_failure_expired_token(self):
        """
        Ensure an expired token cannot be used to reset a password.
        """
        signer = TimestampSigner()
        token = signer.sign(str(self.user.pk))

        future_timestamp = (
            time.time() + (settings.PASSWORD_RESET_TOKEN_EXPIRATION_MINUTES * 60) + 5
        )

        with patch("time.time", return_value=future_timestamp):
            data = {
                "token": token,
                "username": self.user.username,
                "password": "NewPassword456!",
            }
            response = self.client.post(self.reset_confirm_url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("expired", response.data["non_field_errors"][0].lower())

    def test_password_reset_failure_reusing_old_password(self):
        """
        Ensure a user cannot reset their password to a previously used one.
        """
        signer = TimestampSigner()
        token = signer.sign(str(self.user.pk))

        data = {
            "token": token,
            "username": self.user.username,
            "password": self.password,
        }
        response = self.client.post(self.reset_confirm_url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("reuse", response.data["password"][0])
