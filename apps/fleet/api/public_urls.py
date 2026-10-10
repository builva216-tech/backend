from django.urls import path

from .views import (
    PublicAgencyOptionsView,
    PublicCarConditionVideoView,
    PublicCarDetailView,
    PublicCarListView,
    PublicCarPhotoView,
)

app_name = "fleet-public-api"

urlpatterns = [
    path(
        "cars/",
        PublicCarListView.as_view(),
        name="cars",
    ),
    path(
        "cars/<uuid:car_id>/",
        PublicCarDetailView.as_view(),
        name="car-detail",
    ),
    path(
        "cars/<uuid:car_id>/photos/<uuid:photo_id>/",
        PublicCarPhotoView.as_view(),
        name="car-photo",
    ),
    path(
        "cars/<uuid:car_id>/condition-video/",
        PublicCarConditionVideoView.as_view(),
        name="car-video",
    ),
    path(
        "agencies/<uuid:agency_id>/options/",
        PublicAgencyOptionsView.as_view(),
        name="agency-options",
    ),
]
