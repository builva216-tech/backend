from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.accounts.models import AccountStatus, UserRole
from apps.agencies.models import AgencyVerificationStatus
from apps.locations.models import Governorate

from .models import (
    AvailabilityBlock,
    Car,
    CarStatus,
)


def require_agency_workspace(user):
    """Private workspace access is independent of public verification.

    Writes still enforce subscriptions at their API/service entry points.
    Public catalogue and customer booking checks still require approval.
    """
    if (user is None or not user.is_authenticated or not user.is_active
            or user.role != UserRole.AGENCY):
        raise PermissionDenied("Agency workspace access required.")
    return user.agency_profile


# Existing callers retain their interface; public approval is checked separately.
def require_approved_agency(user):
    return require_agency_workspace(user)


def validate_governorate(code: str) -> Governorate:
    normalized = code.strip().upper()

    try:
        return Governorate.objects.get(
            code=normalized,
            is_active=True,
        )
    except Governorate.DoesNotExist as exc:
        raise ValidationError(
            {"governorateCode": ["Select a valid governorate."]}
        ) from exc


def car_has_block(
    *,
    car: Car,
    starts_at,
    ends_at,
) -> bool:
    return AvailabilityBlock.objects.filter(
        car=car,
        starts_at__lt=ends_at,
        ends_at__gt=starts_at,
    ).exists()


@transaction.atomic
def create_availability_block(
    *,
    user,
    car: Car,
    starts_at,
    ends_at,
    reason: str,
) -> AvailabilityBlock:
    profile = require_approved_agency(user)

    if car.agency_id != profile.id:
        raise PermissionDenied("This car does not belong to your agency.")

    if ends_at <= starts_at:
        raise ValidationError(
            {"endsAt": ["End time must be after start time."]}
        )

    if ends_at <= timezone.now():
        raise ValidationError(
            {"endsAt": ["Availability block must end in the future."]}
        )

    return AvailabilityBlock.objects.create(
        car=car,
        starts_at=starts_at,
        ends_at=ends_at,
        reason=reason.strip()[:160],
    )


def can_publish_car(car: Car) -> bool:
    return (
        car.is_available
        and car.status != CarStatus.ARCHIVED
        and car.photos.exists()
        and car.daily_price > 0
    )
