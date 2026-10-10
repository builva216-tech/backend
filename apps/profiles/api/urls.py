from django.urls import path

from .views import (
    CustomerProfileImageView,
    CustomerProfileMeView,
)

app_name = "profiles-api"

urlpatterns = [
    path(
        "customer/me/",
        CustomerProfileMeView.as_view(),
        name="customer-me",
    ),
    path(
        "customer/me/profile-image/",
        CustomerProfileImageView.as_view(),
        name="customer-profile-image",
    ),
]
