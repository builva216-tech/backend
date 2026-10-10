from django.urls import path

from .admin_views import (
    AdminCustomerVerificationApproveView,
    AdminCustomerVerificationDetailView,
    AdminCustomerVerificationDocumentView,
    AdminCustomerVerificationListView,
    AdminCustomerVerificationRejectView,
)

app_name = "admin-customer-verification-api"

urlpatterns = [
    path(
        "",
        AdminCustomerVerificationListView.as_view(),
        name="list",
    ),
    path(
        "<uuid:submission_id>/",
        AdminCustomerVerificationDetailView.as_view(),
        name="detail",
    ),
    path(
        "<uuid:submission_id>/approve/",
        AdminCustomerVerificationApproveView.as_view(),
        name="approve",
    ),
    path(
        "<uuid:submission_id>/reject/",
        AdminCustomerVerificationRejectView.as_view(),
        name="reject",
    ),
    path(
        "<uuid:submission_id>/documents/<slug:document_type>/",
        AdminCustomerVerificationDocumentView.as_view(),
        name="document",
    ),
]
