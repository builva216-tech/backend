from django.urls import path
from .settings_views import AdminPlanListView, AdminPlanDetailView, AdminBugReportListView, AdminBugReportDetailView, AdminStoredUploadView

from apps.accounts.api.recovery_views import (
    AdminPasswordRecoveryConfirmView,
    AdminPasswordRecoveryRequestView,
)

from .views import (
    AdminAgencyApproveView,
    AdminAgencyDetailView,
    AdminAgencyDocumentView,
    AdminAgencyListView,
    AdminAgencyRejectView,
    AdminBookingListView,
    AdminCarListView,
    AdminLoginView,
    AdminLogoutView,
    AdminMeView,
    AdminOverviewView,
    AdminPaymentListView,
    AdminTokenRefreshView,
)
from .workspace_views import (
    AdminAccountAccessView,
    AdminAccountListView,
    AdminAuditListView,
    AdminBusinessAnalyticsView,
)

app_name = "admin-portal-api"

urlpatterns = [
    path('uploads/<path:upload_name>/', AdminStoredUploadView.as_view(), name='stored-upload'),
    path('plans/', AdminPlanListView.as_view(), name='plans'),
    path('plans/<slug:code>/', AdminPlanDetailView.as_view(), name='plan-detail'),
    path('bug-reports/', AdminBugReportListView.as_view(), name='bug-reports'),
    path('bug-reports/<uuid:report_id>/', AdminBugReportDetailView.as_view(), name='bug-report-detail'),
    path("analytics/", AdminBusinessAnalyticsView.as_view(), name="analytics"),
    path("accounts/", AdminAccountListView.as_view(), name="accounts"),
    path(
        "accounts/<uuid:user_id>/access/",
        AdminAccountAccessView.as_view(),
        name="account-access",
    ),
    path("audit/", AdminAuditListView.as_view(), name="audit"),
    path(
        "auth/password-recovery/request/",
        AdminPasswordRecoveryRequestView.as_view(),
        name="password-recovery-request",
    ),
    path(
        "auth/password-recovery/confirm/",
        AdminPasswordRecoveryConfirmView.as_view(),
        name="password-recovery-confirm",
    ),
    path("auth/token/", AdminLoginView.as_view(), name="token"),
    path(
        "auth/token/refresh/",
        AdminTokenRefreshView.as_view(),
        name="token-refresh",
    ),
    path("auth/me/", AdminMeView.as_view(), name="me"),
    path("auth/logout/", AdminLogoutView.as_view(), name="logout"),
    path("overview/", AdminOverviewView.as_view(), name="overview"),
    path("agencies/", AdminAgencyListView.as_view(), name="agency-list"),
    path(
        "agencies/<uuid:agency_profile_id>/",
        AdminAgencyDetailView.as_view(),
        name="agency-detail",
    ),
    path(
        "agencies/<uuid:agency_profile_id>/approve/",
        AdminAgencyApproveView.as_view(),
        name="agency-approve",
    ),
    path(
        "agencies/<uuid:agency_profile_id>/reject/",
        AdminAgencyRejectView.as_view(),
        name="agency-reject",
    ),
    path(
        "agencies/<uuid:agency_profile_id>/documents/<slug:document_type>/",
        AdminAgencyDocumentView.as_view(),
        name="agency-document",
    ),
    path("cars/", AdminCarListView.as_view(), name="cars"),
    path("bookings/", AdminBookingListView.as_view(), name="bookings"),
    path("payments/", AdminPaymentListView.as_view(), name="payments"),
]
