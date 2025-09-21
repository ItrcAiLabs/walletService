import re
from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _
from django.conf import settings


class MinimumLengthValidator:
    def __init__(self, min_length=10):
        self.min_length = min_length

    def validate(self, password, user=None):
        if len(password) < self.min_length:
            raise ValidationError(
                _("This password must contain at least %(min_length)d characters."),
                code="password_too_short",
                params={"min_length": self.min_length},
            )

    def get_help_text(self):
        return _("Your password must contain at least %(min_length)d characters.") % {
            "min_length": self.min_length
        }


class ComplexityValidator:
    def validate(self, password, user=None):
        if not re.search(r"[A-Z]", password):
            raise ValidationError(
                _("Password must contain at least one uppercase letter."),
                code="password_no_upper",
            )
        if not re.search(r"[a-z]", password):
            raise ValidationError(
                _("Password must contain at least one lowercase letter."),
                code="password_no_lower",
            )
        if not re.search(r"[0-9]", password):
            raise ValidationError(
                _("Password must contain at least one digit."), code="password_no_digit"
            )
        if not re.search(r"[\W_]", password):  # Non-alphanumeric
            raise ValidationError(
                _("Password must contain at least one special character."),
                code="password_no_special",
            )

    def get_help_text(self):
        return _(
            "Your password must contain at least one uppercase letter, one lowercase letter, one digit, and one special character."
        )


class PasswordHistoryValidator:
    def validate(self, password, user=None):
        # MODIFIED: Skip check if user is not saved yet (has no pk)
        if not user or not user.pk:
            return

        limit = settings.PREVIOUS_PASSWORD_COUNT
        previous_passwords = user.password_history.all()[:limit]

        from django.contrib.auth.hashers import check_password

        for record in previous_passwords:
            if check_password(password, record.password_hash):
                raise ValidationError(
                    _("You cannot reuse one of your last %(limit)d passwords."),
                    code="password_reused",
                    params={"limit": limit},
                )

    def get_help_text(self):
        return _("You cannot reuse one of your last %(limit)d passwords.") % {
            "limit": settings.PREVIOUS_PASSWORD_COUNT
        }
