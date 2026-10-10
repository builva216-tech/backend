from django.urls import path

from .recovery_views import PasswordRecoveryConfirmView, PasswordRecoveryRequestView
from .views import (
    AgencyRegistrationView,
    ContactChangeConfirmView,
    ContactChangeRequestView,
    CustomerRegistrationView,
    LogoutView,
    MeView,
    MobileLoginView,
    MobileTokenRefreshView,
)

app_name = "accounts-api"

urlpatterns = [
    path(
        "password-recovery/request/",
        PasswordRecoveryRequestView.as_view(),
        name="password-recovery-request",
    ),
    path(
        "password-recovery/confirm/",
        PasswordRecoveryConfirmView.as_view(),
        name="password-recovery-confirm",
    ),
    path("token/", MobileLoginView.as_view(), name="token"),
    path(
        "token/refresh/",
        MobileTokenRefreshView.as_view(),
        name="token-refresh",
    ),
    path(
        "register/customer/",
        CustomerRegistrationView.as_view(),
        name="register-customer",
    ),
    path(
        "register/agency/",
        AgencyRegistrationView.as_view(),
        name="register-agency",
    ),
    path("me/", MeView.as_view(), name="me"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path(
        "contact/change/request/",
        ContactChangeRequestView.as_view(),
        name="contact-change-request",
    ),
    path(
        "contact/change/confirm/",
        ContactChangeConfirmView.as_view(),
        name="contact-change-confirm",
    ),
]
