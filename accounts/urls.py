from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from . import views

urlpatterns = [
    path("otp/request/", views.OTPRequestView.as_view(), name="otp-request"),
    path("otp/verify/", views.OTPVerifyView.as_view(), name="otp-verify"),
    path(
        "register/complete/",
        views.RegistrationCompleteView.as_view(),
        name="register-complete",
    ),
    path("login/", views.CustomTokenObtainPairView.as_view(), name="token-obtain-pair"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token-refresh"),
    path(
        "password/reset/request/",
        views.PasswordResetRequestView.as_view(),
        name="password-reset-request",
    ),
    path(
        "password/reset/confirm/",
        views.PasswordResetConfirmView.as_view(),
        name="password-reset-confirm",
    ),
    path(
        "profile/complete/",
        views.CompleteProfileView.as_view(),
        name="profile-complete",
    ),
    path("profile/me/", views.RetrieveProfileView.as_view(), name="profile-me"),
    path(
        "profile/<int:id>/", views.UserProfileView.as_view(), name="user-profile-detail"
    ),
]
