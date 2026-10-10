from .workspace_views import SubscriptionRequestView
from .workspace_views import SubscriptionView, BranchListView, BranchDetailView, BranchCarView, PublicBranchesView
from django.urls import path

from .crm_views import AgencyCrmListView, AgencyCrmRecordView
from .views import (
    AgencyVerificationMeView,
    AgencyVerificationSubmitView,
    CurrentAgencyProfileView,
    PublicAgencyProfileImageView,
    PublicAgencyProfileView,
)

app_name = "agencies-api"

urlpatterns = [
    path('subscription/request/', SubscriptionRequestView.as_view(), name='subscription-request'),
    path('subscription/', SubscriptionView.as_view(), name='subscription'),
    path('branches/', BranchListView.as_view(), name='branches'),
    path('branches/<uuid:branch_id>/', BranchDetailView.as_view(), name='branch-detail'),
    path('branches/<uuid:branch_id>/cars/<uuid:car_id>/', BranchCarView.as_view(), name='branch-car'),
    path('<uuid:agency_id>/branches/', PublicBranchesView.as_view(), name='public-branches'),
    path("crm/records/", AgencyCrmListView.as_view(), name="crm-list"),
    path(
        "crm/records/<uuid:customer_id>/",
        AgencyCrmRecordView.as_view(),
        name="crm-record",
    ),
    path(
        "me/",
        CurrentAgencyProfileView.as_view(),
        name="me",
    ),
    path(
        "verification/me/",
        AgencyVerificationMeView.as_view(),
        name="verification-me",
    ),
    path(
        "verification/submissions/",
        AgencyVerificationSubmitView.as_view(),
        name="verification-submit",
    ),
    path(
        "<uuid:agency_id>/public/",
        PublicAgencyProfileView.as_view(),
        name="public-profile",
    ),
    path(
        "<uuid:agency_id>/profile-image/",
        PublicAgencyProfileImageView.as_view(),
        name="profile-image",
    ),
]
