from django.urls import reverse
from django.test import override_settings
from rest_framework import status
from rest_framework.test import APITestCase
from ..models import User


@override_settings(RATELIMIT_ENABLED=False)
class ProfileCompletionTests(APITestCase):
    def setUp(self):
        self.password = "TestPassword123!"
        self.user = User.objects.create_user(username="user1", password=self.password)
        self.login_url = reverse("token-obtain-pair")
        self.complete_url = reverse("profile-complete")

    def authenticate(self):
        response = self.client.post(
            self.login_url,
            {"username": self.user.username, "password": self.password},
            format="json"
        )
        token = response.data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    def test_patch_single_field(self):
        self.authenticate()
        response = self.client.patch(self.complete_url, {"gender": "male"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertEqual(self.user.gender, "male")

    def test_complete_all_fields_marks_profile_complete(self):
        self.authenticate()
        data = {
            "first_name": "Ali",
            "last_name": "Rezaei",
            "email": "ali@example.com",
            "gender": "male",
            "job_title": "Engineer",
            "field_of_study": "Software",
            "company": "AI Labs",
            "bank_account_number": "IR123456789000000000000111"
        }
        response = self.client.patch(self.complete_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data["profile_incomplete"])
        self.assertEqual(response.data["missing_fields"], [])

    def test_patch_unauthenticated_fails(self):
        response = self.client.patch(self.complete_url, {"gender": "female"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_invalid_field_value(self):
        self.authenticate()
        long_iban = "IR" + "9" * 100  # Invalid, too long
        response = self.client.patch(self.complete_url, {"bank_account_number": long_iban}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("bank_account_number", response.data)
