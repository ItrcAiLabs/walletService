from django.urls import reverse
from django.test import override_settings
from rest_framework import status
from rest_framework.test import APITestCase
from ..models import User


@override_settings(RATELIMIT_ENABLED=False)
class AuthFlowTests(APITestCase):
    def setUp(self):
        self.login_url = reverse("token-obtain-pair")
        self.password = "ComplexPassword123!"
        self.complete_user = User.objects.create_user(
            username="completeuser",
            password=self.password,
            email="complete@test.com",
            first_name="Test",
            last_name="User",
            gender="male",
            job_title="Engineer",
            field_of_study="Computer Science",
            company="Tech Co",
            bank_account_number="IR123456789000000000000111"
        )
        self.incomplete_user = User.objects.create_user(
            username="incompleteuser", password=self.password
        )

    def test_login_success_complete_profile(self):
        """
        Ensure a user with a complete profile can log in successfully.
        """
        data = {"username": self.complete_user.username, "password": self.password}
        response = self.client.post(self.login_url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)
        self.assertEqual(response.data["profile_incomplete"], False)
        self.assertNotIn("missing_fields", response.data)

    def test_login_success_incomplete_profile(self):
        """
        Ensure login response indicates an incomplete profile for the relevant user.
        """
        data = {"username": self.incomplete_user.username, "password": self.password}
        response = self.client.post(self.login_url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertEqual(response.data["profile_incomplete"], True)
        self.assertIn("missing_fields", response.data)
        self.assertIn("email", response.data["missing_fields"])
        self.assertIn("first_name", response.data["missing_fields"])
        self.assertIn("last_name", response.data["missing_fields"])

    def test_login_failure_wrong_password(self):
        """
        Ensure login fails with an incorrect password.
        """
        data = {"username": self.complete_user.username, "password": "WrongPassword!"}
        response = self.client.post(self.login_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)