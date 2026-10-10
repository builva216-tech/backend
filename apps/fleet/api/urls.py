from django.urls import path

from .views import (
    AgencyAvailabilityBlockDetailView,
    AgencyAvailabilityBlockListCreateView,
    AgencyCarDetailView,
    AgencyCarListCreateView,
    AgencyExtraOptionDetailView,
    AgencyExtraOptionListCreateView,
    AgencyInsuranceOptionDetailView,
    AgencyInsuranceOptionListCreateView,
)

app_name = "fleet-api"

urlpatterns = [
    path(
        "cars/",
        AgencyCarListCreateView.as_view(),
        name="agency-cars",
    ),
    path(
        "cars/<uuid:car_id>/",
        AgencyCarDetailView.as_view(),
        name="agency-car-detail",
    ),
    path(
        "cars/<uuid:car_id>/availability-blocks/",
        AgencyAvailabilityBlockListCreateView.as_view(),
        name="availability-blocks",
    ),
    path(
        "cars/<uuid:car_id>/availability-blocks/<uuid:block_id>/",
        AgencyAvailabilityBlockDetailView.as_view(),
        name="availability-block-detail",
    ),
    path(
        "extras/",
        AgencyExtraOptionListCreateView.as_view(),
        name="extras",
    ),
    path(
        "extras/<uuid:option_id>/",
        AgencyExtraOptionDetailView.as_view(),
        name="extra-detail",
    ),
    path(
        "insurance/",
        AgencyInsuranceOptionListCreateView.as_view(),
        name="insurance",
    ),
    path(
        "insurance/<uuid:option_id>/",
        AgencyInsuranceOptionDetailView.as_view(),
        name="insurance-detail",
    ),
]
