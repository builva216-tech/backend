from django.urls import path

from .customer_views import (
    CustomerVerificationMeView,
    CustomerVerificationSubmitView,
)

app_name = "customer-verification-api"

urlpatterns = [
    path(
        "me/",
        CustomerVerificationMeView.as_view(),
        name="me",
    ),
    path(
        "submissions/",
        CustomerVerificationSubmitView.as_view(),
        name="submit",
    ),
]
