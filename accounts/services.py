import logging
import os
from random import randint

try:
    from kavenegar import KavenegarAPI
except Exception:
    KavenegarAPI = None

logger = logging.getLogger(__name__)


def generate_otp() -> str:
    """
    Generate a random 5-digit OTP code as a string.
    """
    return str(randint(10000, 99999))


class KavenegarEngine:
    """
    Minimal wrapper around Kavenegar API to send SMS using predefined templates.
    Reads credentials from environment variables:
      - KAVENEGAR_API_KEY
      - KAVENEGAR_SENDER
    Falls back to stub logging if not configured.
    """

    # Map Kavenegar status codes to internal status values
    STATUS_MAP = {
        1: 1,  # Delivered
        2: 1,  # Delivered to phone
        4: 2,  # Pending
        5: 2,  # Pending
        6: 4,  # Failed
        10: 3,  # Canceled
        11: 4,  # Failed
        13: 4,  # Failed
        14: 4,  # Failed
        100: 4,  # Failed
    }

    def __init__(
        self, api_key: str | None = None, sender_number: str | None = None
    ) -> None:
        self.api_key = api_key or os.getenv("KAVENEGAR_API_KEY")
        self.sender_number = sender_number or os.getenv("KAVENEGAR_SENDER")

        self.is_configured = bool(
            self.api_key and self.sender_number and KavenegarAPI is not None
        )
        self.api = None
        if self.is_configured:
            try:
                self.api = KavenegarAPI(self.api_key)
            except Exception as exc:
                logger.warning("Kavenegar init failed: %s", exc)
                self.is_configured = False

    def send_by_template(
        self, phone_number: str, template: str, params: dict
    ) -> dict | None:
        """
        Send an SMS using a predefined Kavenegar template.
        Returns a normalized dict or None on failure.
        """
        if not self.is_configured or self.api is None:
            logger.info("--- SMS STUB ---")
            logger.info(
                "Template '%s' to %s with params %s", template, phone_number, params
            )
            logger.info("--- END SMS STUB ---")
            return {
                "status": 2,
                "status_text": "stub",
                "cost": 0,
                "sent_at": None,
                "unique_message_id": None,
            }

        try:
            args = {"receptor": phone_number, "template": template, "type": "sms"}
            args.update(params)
            result = self.api.verify_lookup(args)
            if result:
                item = result[0]
                status = self.STATUS_MAP.get(item.get("status"), 0)
                return {
                    "status": status,
                    "status_text": item.get("statustext"),
                    "cost": item.get("cost"),
                    "sent_at": item.get("date"),
                    "unique_message_id": item.get("messageid"),
                }
        except Exception as exc:
            logger.error("Kavenegar send_by_template failed: %s", exc)

        return None


def send_otp_sms(phone_number: str, otp: str) -> bool:
    """
    Send a one-time password via SMS using the 'turkleParsiazmaVerify' template.
    Falls back to stub logging if Kavenegar is not configured.
    """
    engine = KavenegarEngine()
    resp = engine.send_by_template(
        phone_number, "turkleParsiazmaVerify", {"token": otp}
    )
    success = bool(resp) and resp.get("status") in (1, 2)  # Delivered/Pending
    logger.info(
        "OTP SMS send result for %s: %s", phone_number, "OK" if success else "FAILED"
    )
    return success


def send_password_reset_email(email: str, reset_link: str) -> bool:
    """
    Scaffold for sending a password reset email.
    Replace with Django email backend integration in production.
    """
    logger.info("--- EMAIL STUB ---")
    logger.info("Sending password reset link to %s", email)
    logger.info("Link: %s", reset_link)
    logger.info("--- END EMAIL STUB ---")
    return True
