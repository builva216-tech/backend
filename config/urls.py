from django.contrib import admin
from django.urls import include, path

from apps.core.api.views import HealthCheckView
from apps.core.api.bug_reports import BugReportView

urlpatterns = [
    path("api/v1/support/bug-reports/", BugReportView.as_view(), name="bug-report"),
    path("api/v1/", include("apps.notifications.api")),
    path("admin/", admin.site.urls),
    path(
        "api/v1/health/",
        HealthCheckView.as_view(),
        name="health-check",
    ),
    path(
        "api/v1/auth/",
        include("apps.accounts.api.urls"),
    ),
    path(
        "api/v1/locations/",
        include("apps.locations.api.urls"),
    ),
    path(
        "api/v1/agencies/",
        include("apps.agencies.api.urls"),
    ),
    path(
        "api/v1/profiles/",
        include("apps.profiles.api.urls"),
    ),
    path(
        "api/v1/customer-verification/",
        include(
            "apps.customer_verifications.api.customer_urls"
        ),
    ),
    path(
        "api/v1/fleet/",
        include("apps.fleet.api.urls"),
    ),
    path(
        "api/v1/",
        include("apps.fleet.api.public_urls"),
    ),
    path(
        "api/v1/bookings/",
        include("apps.bookings.api.urls"),
    ),
    path(
        "api/v1/payments/",
        include("apps.payments.api.urls"),
    ),
    path(
        "api/v1/reviews/",
        include("apps.reviews.api.urls"),
    ),
    path(
        "api/v1/admin/customers/",
        include(
            "apps.customer_verifications.api.admin_urls"
        ),
    ),
    path(
        "api/v1/admin/",
        include("apps.admin_portal.api.urls"),
    ),
]
