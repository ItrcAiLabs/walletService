import uuid
from django.urls import reverse
from django.test import override_settings
from rest_framework import status
from rest_framework.test import APITestCase
from unittest.mock import patch
from ..models import OTPRequest, User


@override_settings(RATELIMIT_ENABLED=False)
class OTPFlowTests(APITestCase):
    def setUp(self):
        self.phone_number = "1234567890"
        self.otp_request_url = reverse("otp-request")
        self.otp_verify_url = reverse("otp-verify")
        self.register_complete_url = reverse("register-complete")

    @patch("accounts.services.send_otp_sms")
    @patch("accounts.services.generate_otp")
    def test_request_otp_success(self, mock_generate_otp, mock_send_sms):
        """
        Ensure we can request an OTP successfully.
        """
        mock_generate_otp.return_value = "112233"
        mock_send_sms.return_value = True
        data = {"phone_number": self.phone_number}
        response = self.client.post(self.otp_request_url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("request_id", response.data)
        self.assertTrue(
            OTPRequest.objects.filter(phone_number=self.phone_number).exists()
        )
        mock_send_sms.assert_called_once_with(self.phone_number, "112233")

    @patch("accounts.services.send_otp_sms")
    @patch("accounts.services.generate_otp", return_value="123456")
    def test_verify_otp_success_and_get_registration_token(
        self, mock_generate_otp, mock_send_sms
    ):
        """
        Ensure we can verify a valid OTP and get a registration token.
        """
        request_data = {"phone_number": self.phone_number}
        request_response = self.client.post(
            self.otp_request_url, request_data, format="json"
        )
        request_id = request_response.data["request_id"]

        verify_data = {
            "phone_number": self.phone_number,
            "otp": "123456",
            "request_id": request_id,
        }
        verify_response = self.client.post(
            self.otp_verify_url, verify_data, format="json"
        )

        self.assertEqual(
            verify_response.status_code, status.HTTP_200_OK, verify_response.data
        )
        self.assertIn("registration_token", verify_response.data)

        otp_request_obj = OTPRequest.objects.get(request_id=request_id)
        self.assertIsNotNone(otp_request_obj.registration_token)

    @patch("accounts.services.send_otp_sms")
    @patch("accounts.services.generate_otp", return_value="123456")
    def test_verify_otp_failure_invalid_otp(self, mock_generate_otp, mock_send_sms):
        """
        Ensure verifying with an invalid OTP fails.
        """
        request_response = self.client.post(
            self.otp_request_url, {"phone_number": self.phone_number}, format="json"
        )
        request_id = request_response.data["request_id"]

        verify_data = {
            "phone_number": self.phone_number,
            "otp": "654321",  # Wrong OTP
            "request_id": request_id,
        }
        verify_response = self.client.post(
            self.otp_verify_url, verify_data, format="json"
        )
        self.assertEqual(verify_response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch("accounts.services.send_otp_sms")
    @patch("accounts.services.generate_otp", return_value="123456")
    def test_complete_registration_success(self, mock_generate_otp, mock_send_sms):
        """
        Ensure a user can complete registration and gets logged in automatically.
        """
        request_response = self.client.post(
            self.otp_request_url, {"phone_number": self.phone_number}, format="json"
        )
        verify_response = self.client.post(
            self.otp_verify_url,
            {
                "phone_number": self.phone_number,
                "otp": "123456",
                "request_id": request_response.data["request_id"],
            },
            format="json",
        )
        registration_token = verify_response.data["registration_token"]

        register_data = {
            "registration_token": registration_token,
            "username": "newuser",
            "password": "ComplexPassword123!",
        }
        register_response = self.client.post(
            self.register_complete_url, register_data, format="json"
        )

        self.assertEqual(register_response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(User.objects.filter(username="newuser").exists())

        # Check for JWT tokens in response
        self.assertIn("access", register_response.data)
        self.assertIn("refresh", register_response.data)
        self.assertEqual(register_response.data["profile_incomplete"], True)

        self.assertFalse(
            OTPRequest.objects.filter(registration_token=registration_token).exists()
        )

    def test_complete_registration_failure_weak_password(self):
        """
        Ensure registration fails if the password does not meet the policy.
        """
        registration_token = uuid.uuid4()
        OTPRequest.objects.create(
            phone_number=self.phone_number,
            otp_hash="dummy",
            registration_token=registration_token,
        )

        register_data = {
            "registration_token": registration_token,
            "username": "newuser",
            "password": "weak",
        }
        register_response = self.client.post(
            self.register_complete_url, register_data, format="json"
        )

        self.assertEqual(register_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("password", register_response.data)
        self.assertFalse(User.objects.filter(username="newuser").exists())
