from django.urls import path

from .views import (
    AgencyCustomerRatingByBookingView,
    AgencyCustomerRatingSubmitView,
    AgencyReputationView,
    CarReputationView,
    CustomerReviewByBookingView,
    CustomerReviewSubmitView,
    CustomerTrustView,
    ReviewBookingContextView,
)

app_name = "reviews-api"

urlpatterns = [
    path(
        "bookings/<uuid:booking_id>/context/",
        ReviewBookingContextView.as_view(),
        name="booking-context",
    ),
    path(
        "bookings/<uuid:booking_id>/customer-review/",
        CustomerReviewSubmitView.as_view(),
        name="customer-review-submit",
    ),
    path(
        "bookings/<uuid:booking_id>/customer-review/me/",
        CustomerReviewByBookingView.as_view(),
        name="customer-review-by-booking",
    ),
    path(
        "bookings/<uuid:booking_id>/agency-customer-rating/",
        AgencyCustomerRatingSubmitView.as_view(),
        name="agency-customer-rating-submit",
    ),
    path(
        "bookings/<uuid:booking_id>/agency-customer-rating/me/",
        AgencyCustomerRatingByBookingView.as_view(),
        name="agency-customer-rating-by-booking",
    ),
    path(
        "agencies/<uuid:agency_id>/",
        AgencyReputationView.as_view(),
        name="agency-reputation",
    ),
    path(
        "cars/<uuid:car_id>/",
        CarReputationView.as_view(),
        name="car-reputation",
    ),
    path(
        "customers/<uuid:customer_id>/",
        CustomerTrustView.as_view(),
        name="customer-trust",
    ),
]
