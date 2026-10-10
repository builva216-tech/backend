from django.db import transaction
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.accounts.models import UserRole
from apps.bookings.models import Booking, BookingStatus
from apps.core.api.exceptions import Conflict

from .models import (
    AgencyCustomerRating,
    CustomerRentalReview,
)


def _validate_rating(value: int, field_name: str) -> int:
    if value < 1 or value > 5:
        raise ValidationError(
            {field_name: ["Rating must be between 1 and 5."]}
        )
    return value


@transaction.atomic
def submit_customer_review(
    *,
    user,
    booking_id,
    car_rating: int,
    agency_rating: int,
    comment: str,
) -> CustomerRentalReview:
    if (
        user is None
        or not user.is_authenticated
        or user.role != UserRole.CUSTOMER
    ):
        raise PermissionDenied("Customer access required.")

    booking = (
        Booking.objects.select_for_update()
        .select_related("car", "agency", "customer")
        .get(pk=booking_id)
    )

    if booking.customer_id != user.id:
        raise PermissionDenied(
            "This booking does not belong to your account."
        )

    if booking.status != BookingStatus.COMPLETED:
        raise Conflict(
            "Reviews are available only after a completed rental."
        )

    if CustomerRentalReview.objects.filter(
        booking=booking
    ).exists():
        raise Conflict("This rental was already reviewed.")

    return CustomerRentalReview.objects.create(
        booking=booking,
        customer=user,
        car=booking.car,
        agency=booking.agency,
        car_rating=_validate_rating(
            car_rating,
            "carRating",
        ),
        agency_rating=_validate_rating(
            agency_rating,
            "agencyRating",
        ),
        comment=comment.strip()[:2000],
    )


@transaction.atomic
def submit_agency_customer_rating(
    *,
    user,
    booking_id,
    punctuality_rating: int,
    car_care_rating: int,
    communication_rating: int,
    private_comment: str,
) -> AgencyCustomerRating:
    if (
        user is None
        or not user.is_authenticated
        or user.role != UserRole.AGENCY
    ):
        raise PermissionDenied("Agency access required.")

    booking = (
        Booking.objects.select_for_update()
        .select_related("agency__user", "customer")
        .get(pk=booking_id)
    )

    if booking.agency.user_id != user.id:
        raise PermissionDenied(
            "This booking does not belong to your agency."
        )

    if booking.status != BookingStatus.COMPLETED:
        raise Conflict(
            "Customer ratings are available only after a completed rental."
        )

    if AgencyCustomerRating.objects.filter(
        booking=booking
    ).exists():
        raise Conflict(
            "This customer was already rated for this rental."
        )

    return AgencyCustomerRating.objects.create(
        booking=booking,
        agency=booking.agency,
        customer=booking.customer,
        punctuality_rating=_validate_rating(
            punctuality_rating,
            "punctualityRating",
        ),
        car_care_rating=_validate_rating(
            car_care_rating,
            "carCareRating",
        ),
        communication_rating=_validate_rating(
            communication_rating,
            "communicationRating",
        ),
        private_comment=private_comment.strip()[:2000],
    )
