from apps.agencies.subscriptions import require_management, require_booking_action
import math
from decimal import Decimal, ROUND_HALF_UP

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import (
    NotFound,
    PermissionDenied,
    ValidationError,
)

from apps.accounts.models import AccountStatus, UserRole
from apps.agencies.models import AgencyVerificationStatus
from apps.core.api.exceptions import Conflict
from apps.customer_verifications.models import (
    CustomerVerificationStatus,
    CustomerVerificationSubmission,
)
from apps.fleet.models import (
    Car,
    CarStatus,
    ExtraOption,
    InsuranceOption,
    PricingType,
)
from apps.fleet.services import car_has_block

from .models import (
    Booking,
    BookingExtra,
    BookingInsurance,
    BookingStatus,
    BookingStatusEvent,
)


MONEY_QUANTUM = Decimal("0.001")
BLOCKING_BOOKING_STATUSES = (
    BookingStatus.APPROVED,
    BookingStatus.CONFIRMED,
    BookingStatus.ACTIVE,
)


def money(value) -> Decimal:
    return Decimal(value).quantize(
        MONEY_QUANTUM,
        rounding=ROUND_HALF_UP,
    )


def require_customer(user) -> None:
    if (
        user is None
        or not user.is_authenticated
        or not user.is_active
        or user.role != UserRole.CUSTOMER
        or user.account_status != AccountStatus.ACTIVE
    ):
        raise PermissionDenied("Customer access required.")


def require_agency(user):
    from apps.fleet.services import require_agency_workspace
    return require_agency_workspace(user)


def require_approved_customer_kyc(user) -> None:
    if not CustomerVerificationSubmission.objects.filter(
        user=user,
        status=CustomerVerificationStatus.APPROVED,
    ).exists():
        raise PermissionDenied(
            "Approved identity verification is required before booking."
        )


def _validate_period(pickup_at, return_at) -> int:
    if return_at <= pickup_at:
        raise ValidationError(
            {"returnDate": ["Return time must be after pickup time."]}
        )

    if pickup_at < timezone.now():
        raise ValidationError(
            {"pickupDate": ["Pickup time must be in the future."]}
        )

    seconds = (return_at - pickup_at).total_seconds()
    return max(1, math.ceil(seconds / 86400))


def _validate_car_for_public_booking(car: Car) -> None:
    if (
        car.status != CarStatus.PUBLISHED
        or not car.is_available
        or car.agency.verification_status
        != AgencyVerificationStatus.APPROVED
        or car.agency.user.account_status != AccountStatus.ACTIVE
    ):
        raise Conflict("Car is not available for booking.")


def _overlapping_booking_exists(
    *,
    car: Car,
    pickup_at,
    return_at,
    exclude_booking_id=None,
) -> bool:
    queryset = Booking.objects.filter(
        car=car,
        status__in=BLOCKING_BOOKING_STATUSES,
        pickup_at__lt=return_at,
        return_at__gt=pickup_at,
    )
    if exclude_booking_id is not None:
        queryset = queryset.exclude(pk=exclude_booking_id)
    return queryset.exists()


def _load_selected_options(
    *,
    car: Car,
    extra_ids,
    insurance_id,
):
    extras = list(
        ExtraOption.objects.filter(
            agency=car.agency,
            id__in=extra_ids,
            is_active=True,
        )
    )

    if len(extras) != len(set(extra_ids)):
        raise ValidationError(
            {"extraIds": ["One or more extras are unavailable."]}
        )

    insurance = None
    if insurance_id:
        try:
            insurance = InsuranceOption.objects.get(
                agency=car.agency,
                pk=insurance_id,
                is_active=True,
            )
        except (InsuranceOption.DoesNotExist, ValueError) as exc:
            raise ValidationError(
                {"insuranceId": ["Insurance option is unavailable."]}
            ) from exc

    return extras, insurance


def calculate_quote(
    *,
    car: Car,
    pickup_at,
    return_at,
    extra_ids,
    insurance_id,
) -> dict:
    rental_days = _validate_period(pickup_at, return_at)
    _validate_car_for_public_booking(car)

    if car_has_block(
        car=car,
        starts_at=pickup_at,
        ends_at=return_at,
    ):
        raise Conflict("Car is blocked for the selected period.")

    extras, insurance = _load_selected_options(
        car=car,
        extra_ids=extra_ids,
        insurance_id=insurance_id,
    )

    daily_price = money(car.daily_price)
    base_price = money(daily_price * rental_days)

    extras_total = Decimal("0")
    extra_lines = []

    for option in extras:
        quantity = (
            rental_days
            if option.pricing_type == PricingType.PER_DAY
            else 1
        )
        total = money(option.price * quantity)
        extras_total += total
        extra_lines.append(
            {
                "option": option,
                "quantity": quantity,
                "total": total,
            }
        )

    insurance_total = Decimal("0")
    security_deposit = Decimal("0")

    if insurance is not None:
        insurance_total = money(
            insurance.daily_price * rental_days
        )
        security_deposit = money(
            insurance.security_deposit
        )

    total_price = money(
        base_price + extras_total + insurance_total
    )

    return {
        "rental_days": rental_days,
        "daily_price": daily_price,
        "base_price": base_price,
        "extras_total": money(extras_total),
        "insurance_total": money(insurance_total),
        "total_price": total_price,
        "security_deposit": security_deposit,
        "extra_lines": extra_lines,
        "insurance": insurance,
    }


@transaction.atomic
def create_booking(
    *,
    user,
    car_id,
    pickup_at,
    return_at,
    extra_ids,
    insurance_id,
    customer_note: str,
) -> Booking:
    require_customer(user)
    require_approved_customer_kyc(user)

    try:
        car = (
            Car.objects.select_for_update()
            .select_related(
                "agency",
                "agency__user",
                "governorate",
            )
            .get(pk=car_id)
        )
    except (Car.DoesNotExist, ValueError) as exc:
        raise NotFound("Car was not found.") from exc

    require_management(car.agency)
    quote = calculate_quote(
        car=car,
        pickup_at=pickup_at,
        return_at=return_at,
        extra_ids=extra_ids,
        insurance_id=insurance_id,
    )

    booking = Booking.objects.create(
        car=car,
        agency=car.agency,
        customer=user,
        pickup_at=pickup_at,
        return_at=return_at,
        rental_days=quote["rental_days"],
        daily_price_snapshot=quote["daily_price"],
        base_price=quote["base_price"],
        extras_total=quote["extras_total"],
        insurance_total=quote["insurance_total"],
        total_price=quote["total_price"],
        security_deposit=quote["security_deposit"],
        pickup_governorate=car.governorate,
        pickup_city=car.city,
        payment_method="cash",
        status=BookingStatus.REQUESTED,
        customer_note=customer_note.strip(),
    )

    for line in quote["extra_lines"]:
        option = line["option"]
        BookingExtra.objects.create(
            booking=booking,
            option_id_snapshot=option.id,
            name=option.name,
            pricing_type=option.pricing_type,
            unit_price=option.price,
            unit_cost=option.estimated_cost,
            quantity=line["quantity"],
            total_price=line["total"],
        )

    insurance = quote["insurance"]
    if insurance is not None:
        BookingInsurance.objects.create(
            booking=booking,
            option_id_snapshot=insurance.id,
            name=insurance.name,
            daily_price=insurance.daily_price,
            daily_cost=insurance.estimated_daily_cost,
            total_price=quote["insurance_total"],
            security_deposit=quote["security_deposit"],
        )

    BookingStatusEvent.objects.create(
        booking=booking,
        from_status="",
        to_status=BookingStatus.REQUESTED,
        actor=user,
        note="Booking requested.",
    )

    return booking


def _locked_booking(booking_id) -> Booking:
    try:
        return (
            Booking.objects.select_for_update()
            .select_related(
                "car",
                "agency",
                "agency__user",
                "customer",
                "pickup_governorate",
            )
            .get(pk=booking_id)
        )
    except (Booking.DoesNotExist, ValueError) as exc:
        raise NotFound("Booking was not found.") from exc


def _record_transition(
    *,
    booking: Booking,
    actor,
    from_status: str,
    to_status: str,
    note: str = "",
):
    BookingStatusEvent.objects.create(
        booking=booking,
        from_status=from_status,
        to_status=to_status,
        actor=actor,
        note=note.strip(),
    )


@transaction.atomic
def agency_transition(
    *,
    user,
    booking_id,
    action: str,
    note: str = "",
) -> Booking:
    profile = require_agency(user)
    booking = _locked_booking(booking_id)

    if booking.agency_id != profile.id:
        raise PermissionDenied(
            "This booking does not belong to your agency."
        )

    require_booking_action(profile, booking, action)
    now = timezone.now()
    old = booking.status

    if action == "approve":
        if old != BookingStatus.REQUESTED:
            raise Conflict("Only requested bookings can be approved.")

        if car_has_block(
            car=booking.car,
            starts_at=booking.pickup_at,
            ends_at=booking.return_at,
        ) or _overlapping_booking_exists(
            car=booking.car,
            pickup_at=booking.pickup_at,
            return_at=booking.return_at,
            exclude_booking_id=booking.id,
        ):
            raise Conflict(
                "The car is no longer available for this period."
            )

        booking.status = BookingStatus.APPROVED
        booking.agency_responded_at = now
        booking.agency_note = note.strip()

        from apps.payments.services import ensure_cash_payment
        ensure_cash_payment(booking=booking)

    elif action == "reject":
        if old != BookingStatus.REQUESTED:
            raise Conflict("Only requested bookings can be rejected.")
        if len(note.strip()) < 3:
            raise ValidationError(
                {"reason": ["A rejection reason is required."]}
            )
        booking.status = BookingStatus.REJECTED
        booking.agency_responded_at = now
        booking.agency_note = note.strip()

    elif action == "pickup":
        if old != BookingStatus.CONFIRMED:
            raise Conflict(
                "Only confirmed bookings can be marked active."
            )
        booking.status = BookingStatus.ACTIVE
        booking.pickup_completed_at = now

    elif action == "return":
        if old != BookingStatus.ACTIVE:
            raise Conflict(
                "Only active bookings can be completed."
            )
        booking.status = BookingStatus.COMPLETED
        booking.returned_at = now

    else:
        raise ValidationError({"action": ["Unsupported action."]})

    booking.save()
    _record_transition(
        booking=booking,
        actor=user,
        from_status=old,
        to_status=booking.status,
        note=note,
    )
    return booking


@transaction.atomic
def customer_confirm(
    *,
    user,
    booking_id,
) -> Booking:
    require_customer(user)
    booking = _locked_booking(booking_id)

    if booking.customer_id != user.id:
        raise PermissionDenied(
            "This booking does not belong to your account."
        )

    if booking.status == BookingStatus.CONFIRMED:
        return booking

    if booking.status != BookingStatus.APPROVED:
        raise Conflict(
            "Only approved bookings can be confirmed."
        )

    old = booking.status
    booking.status = BookingStatus.CONFIRMED
    booking.confirmed_at = timezone.now()
    booking.save(
        update_fields=[
            "status",
            "confirmed_at",
            "updated_at",
        ]
    )
    _record_transition(
        booking=booking,
        actor=user,
        from_status=old,
        to_status=booking.status,
        note="Customer confirmed the approved rental.",
    )
    return booking


@transaction.atomic
def customer_cancel(
    *,
    user,
    booking_id,
) -> Booking:
    require_customer(user)
    booking = _locked_booking(booking_id)

    if booking.customer_id != user.id:
        raise PermissionDenied(
            "This booking does not belong to your account."
        )

    if booking.status not in (
        BookingStatus.REQUESTED,
        BookingStatus.APPROVED,
        BookingStatus.CONFIRMED,
    ):
        raise Conflict(
            "This booking can no longer be cancelled."
        )

    old = booking.status
    booking.status = BookingStatus.CANCELLED
    booking.cancelled_at = timezone.now()
    booking.save(
        update_fields=[
            "status",
            "cancelled_at",
            "updated_at",
        ]
    )
    _record_transition(
        booking=booking,
        actor=user,
        from_status=old,
        to_status=booking.status,
        note="Cancelled by customer.",
    )
    return booking
