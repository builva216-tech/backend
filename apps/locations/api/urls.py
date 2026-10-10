from django.urls import path

from .views import GovernorateListView

app_name = "locations-api"

urlpatterns = [
    path("governorates/", GovernorateListView.as_view(), name="governorates"),
]
