from django.urls import reverse
from django.test import override_settings
from rest_framework import status
from rest_framework.test import APITestCase
from ..models import User


@override_settings(RATELIMIT_ENABLED=False)
class TokenRefreshTests(APITestCase):
    def setUp(self):
        self.password = "MyTestPass456!"
        self.user = User.objects.create_user(
            username="refreshtest",
            password=self.password,
            email="refresh@example.com",
            first_name="Ref",
            last_name="User",
            gender="other",
            job_title="Tester",
            field_of_study="QA",
            company="Test Inc",
            bank_account_number="IR123456789000000000000123"
        )
        self.login_url = reverse("token-obtain-pair")
        self.refresh_url = reverse("token-refresh")

    def get_tokens(self):
        response = self.client.post(
            self.login_url,
            {"username": self.user.username, "password": self.password},
            format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        return response.data["access"], response.data["refresh"]

    def test_valid_refresh_token_returns_new_access(self):
        _, refresh_token = self.get_tokens()
        response = self.client.post(
            self.refresh_url,
            {"refresh": refresh_token},
            format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)

    def test_invalid_refresh_token_returns_401(self):
        invalid_token = "this.is.not.a.valid.token"
        response = self.client.post(
            self.refresh_url,
            {"refresh": invalid_token},
            format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertIn("detail", response.data)
        self.assertIn("token", response.data["detail"].lower())