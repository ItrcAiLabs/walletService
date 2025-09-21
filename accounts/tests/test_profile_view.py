from django.urls import reverse
from django.test import override_settings
from rest_framework import status
from rest_framework.test import APITestCase
from ..models import User


@override_settings(RATELIMIT_ENABLED=False)
class ProfileViewTests(APITestCase):
    def setUp(self):
        self.password = "ComplexPass123!"
        self.user1 = User.objects.create_user(
            username="user1",
            password=self.password,
            email="user1@example.com",
            first_name="User",
            last_name="One",
            gender="male",
            job_title="Engineer",
            field_of_study="Computer Science",
            company="Tech Co",
            bank_account_number="IR123456789000000000000001"
        )
        self.user2 = User.objects.create_user(
            username="user2",
            password=self.password,
            email="user2@example.com",
            first_name="User",
            last_name="Two",
            gender="female",
            job_title="Designer",
            field_of_study="Arts",
            company="Design Co",
            bank_account_number="IR123456789000000000000002"
        )
        self.login_url = reverse("token-obtain-pair")

    def authenticate(self, user):
        response = self.client.post(
            self.login_url,
            {"username": user.username, "password": self.password},
            format="json"
        )
        token = response.data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    def test_view_own_profile(self):
        self.authenticate(self.user1)
        url = reverse("profile-me")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["email"], self.user1.email)
        self.assertEqual(response.data["first_name"], self.user1.first_name)

    def test_view_other_user_profile(self):
        self.authenticate(self.user1)
        url = reverse("user-profile-detail", args=[self.user2.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["email"], self.user2.email)
        self.assertEqual(response.data["company"], self.user2.company)

    def test_unauthenticated_cannot_view_profile(self):
        url = reverse("profile-me")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        url = reverse("user-profile-detail", args=[self.user1.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_profile_data_integrity(self):
        self.authenticate(self.user2)
        url = reverse("profile-me")
        response = self.client.get(url)
        self.assertEqual(response.data["gender"], "female")
        self.assertEqual(response.data["job_title"], "Designer")
        self.assertEqual(response.data["company"], "Design Co")
