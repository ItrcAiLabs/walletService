from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, OTPRequest, PasswordHistory


class CustomUserAdmin(UserAdmin):
    # Fields to display in the user list view
    list_display = (
        "username",
        "email",
        "phone_number",
        "first_name",
        "last_name",
        "is_staff",
    )
    # Fields to enable searching by
    search_fields = ("username", "email", "phone_number")


class OTPRequestAdmin(admin.ModelAdmin):
    # Fields to display in the OTPRequest list view
    list_display = ("phone_number", "request_id", "created_at")
    # Fields that are read-only in the admin detail view
    readonly_fields = (
        "request_id",
        "phone_number",
        "otp_hash",
        "registration_token",
        "created_at",
    )
    # Fields to enable searching by
    search_fields = ("phone_number",)


class PasswordHistoryAdmin(admin.ModelAdmin):
    # Fields to display in the PasswordHistory list view
    list_display = ("user", "created_at")
    # Fields to enable searching by user username
    search_fields = ("user__username",)


# Register models with the admin site
admin.site.register(User, CustomUserAdmin)
admin.site.register(OTPRequest, OTPRequestAdmin)
admin.site.register(PasswordHistory, PasswordHistoryAdmin)
