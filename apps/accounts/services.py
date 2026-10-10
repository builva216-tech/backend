import re
import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.mail import send_mail
from django.core.validators import validate_email
from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.agencies.models import AgencyProfile, AgencyVerificationStatus
from apps.core.api.exceptions import (
    Conflict,
    DeliveryUnavailable,
    Gone,
    Locked,
    TooManyRequests,
    UnprocessableEntity,
)
from apps.locations.models import Governorate

from .models import (
    AccountStatus,
    ContactType,
    ContactVerificationChallenge,
    ContactVerificationStatus,
    User,
    UserRole,
)

CONTACT_OTP_LENGTH = 6
CONTACT_OTP_MAXIMUM_ATTEMPTS = 5
CONTACT_OTP_VALIDITY = timedelta(minutes=5)
CONTACT_OTP_RESEND_DELAY = timedelta(seconds=60)


def normalize_email(value: str) -> str:
    return value.strip().lower()


def normalize_phone(value: str) -> str:
    return re.sub(r"[\s\-\(\)]", "", value.strip())


def normalize_optional_city(value: str) -> str:
    return value.strip()


def validate_phone(value: str) -> None:
    if not re.fullmatch(r"\+?\d{8,15}", value):
        raise ValidationError({"phone": ["Enter a valid phone number."]})


def validate_unique_identity(*, email: str, phone: str) -> None:
    if User.objects.filter(email=email).exists():
        raise Conflict("This email is already in use.")

    if User.objects.filter(phone=phone).exists():
        raise Conflict("This phone number is already in use.")


def validate_account_password(password: str) -> None:
    try:
        validate_password(password)
    except DjangoValidationError as exc:
        raise ValidationError({"password": list(exc.messages)}) from exc


@transaction.atomic
def register_customer(
    *,
    full_name: str,
    email: str,
    phone: str,
    password: str,
) -> User:
    normalized_email = normalize_email(email)
    normalized_phone = normalize_phone(phone)

    try:
        validate_email(normalized_email)
    except DjangoValidationError as exc:
        raise ValidationError({"email": ["Enter a valid email address."]}) from exc

    validate_phone(normalized_phone)
    validate_unique_identity(
        email=normalized_email,
        phone=normalized_phone,
    )
    validate_account_password(password)

    return User.objects.create_user(
        full_name=full_name.strip(),
        email=normalized_email,
        phone=normalized_phone,
        password=password,
        role=UserRole.CUSTOMER,
        account_status=AccountStatus.ACTIVE,
    )


@transaction.atomic
def register_agency(
    *,
    agency_name: str,
    responsible_person_name: str,
    email: str,
    phone: str,
    password: str,
    governorate_code: str,
    city: str,
) -> User:
    normalized_email = normalize_email(email)
    normalized_phone = normalize_phone(phone)
    normalized_governorate_code = governorate_code.strip().upper()
    normalized_city = normalize_optional_city(city)

    try:
        validate_email(normalized_email)
    except DjangoValidationError as exc:
        raise ValidationError({"email": ["Enter a valid email address."]}) from exc

    validate_phone(normalized_phone)
    validate_unique_identity(
        email=normalized_email,
        phone=normalized_phone,
    )
    validate_account_password(password)

    try:
        governorate = Governorate.objects.get(
            code=normalized_governorate_code,
            is_active=True,
        )
    except Governorate.DoesNotExist as exc:
        raise ValidationError(
            {"governorateCode": ["Please select a valid Tunisian governorate."]}
        ) from exc

    user = User.objects.create_user(
        full_name=responsible_person_name.strip(),
        email=normalized_email,
        phone=normalized_phone,
        password=password,
        role=UserRole.AGENCY,
        account_status=AccountStatus.PENDING_VERIFICATION,
    )

    AgencyProfile.objects.create(
        user=user,
        agency_name=agency_name.strip(),
        governorate=governorate,
        city=normalized_city,
        verification_status=AgencyVerificationStatus.PENDING,
    )

    return user


def _require_customer(user: User) -> None:
    if (
        not user.is_authenticated
        or not user.is_active
        or user.role != UserRole.CUSTOMER
    ):
        raise PermissionDenied("This operation is available to customer accounts only.")


def _normalize_contact_value(*, contact_type: str, value: str) -> str:
    if contact_type == ContactType.EMAIL:
        normalized = normalize_email(value)
        try:
            validate_email(normalized)
        except DjangoValidationError as exc:
            raise UnprocessableEntity("Enter a valid email address.") from exc
        return normalized

    if contact_type == ContactType.PHONE:
        normalized = normalize_phone(value)
        if not re.fullmatch(r"\+?\d{8,15}", normalized):
            raise UnprocessableEntity("Enter a valid phone number.")
        return normalized

    raise UnprocessableEntity("Unsupported contact type.")


def _ensure_contact_is_available(
    *,
    user: User,
    contact_type: str,
    pending_value: str,
) -> None:
    if contact_type == ContactType.EMAIL:
        current_value = normalize_email(user.email)
        if current_value == pending_value:
            raise Conflict("This is already your current email address.")

        if User.objects.exclude(pk=user.pk).filter(email=pending_value).exists():
            raise Conflict("This email is already in use.")
        return

    current_value = normalize_phone(user.phone)
    if current_value == pending_value:
        raise Conflict("This is already your current phone number.")

    if User.objects.exclude(pk=user.pk).filter(phone=pending_value).exists():
        raise Conflict("This phone number is already in use.")


@transaction.atomic
def request_contact_change(
    *,
    user: User,
    contact_type: str,
    value: str,
) -> tuple[ContactVerificationChallenge, str | None]:
    _require_customer(user)
    user = User.objects.select_for_update().get(pk=user.pk)
    if contact_type == ContactType.PHONE and not settings.DEBUG:
        raise DeliveryUnavailable(
            "Phone verification needs an SMS provider. Contact support to update your number."
        )

    normalized_value = _normalize_contact_value(
        contact_type=contact_type,
        value=value,
    )

    _ensure_contact_is_available(
        user=user,
        contact_type=contact_type,
        pending_value=normalized_value,
    )

    now = timezone.now()

    active_challenge = (
        ContactVerificationChallenge.objects.select_for_update()
        .filter(
            user=user,
            contact_type=contact_type,
            status=ContactVerificationStatus.PENDING,
        )
        .order_by("-created_at")
        .first()
    )

    if active_challenge is not None and now < active_challenge.resend_available_at:
        seconds = max(
            1,
            int((active_challenge.resend_available_at - now).total_seconds()),
        )
        raise TooManyRequests(
            f"Please wait {seconds} seconds before requesting another code."
        )

    if active_challenge is not None:
        active_challenge.status = ContactVerificationStatus.SUPERSEDED
        active_challenge.save(update_fields=["status"])

    otp_code = "".join(str(secrets.randbelow(10)) for _ in range(CONTACT_OTP_LENGTH))

    challenge = ContactVerificationChallenge.objects.create(
        user=user,
        contact_type=contact_type,
        pending_value=normalized_value,
        otp_hash=make_password(otp_code),
        status=ContactVerificationStatus.PENDING,
        attempts_remaining=CONTACT_OTP_MAXIMUM_ATTEMPTS,
        expires_at=now + CONTACT_OTP_VALIDITY,
        resend_available_at=now + CONTACT_OTP_RESEND_DELAY,
    )

    if contact_type == ContactType.EMAIL and not settings.DEBUG:
        try:
            sent = send_mail(
                "Verify your CarRent TN email change",
                f"Your verification code is {otp_code}. It expires in 5 minutes. Do not share it.",
                settings.DEFAULT_FROM_EMAIL,
                [normalized_value],
                fail_silently=False,
            )
            if sent != 1:
                raise RuntimeError("Email not accepted")
        except Exception as exc:
            raise DeliveryUnavailable(
                "Email verification is unavailable. Please try again later."
            ) from exc
    # Development-only convenience. Production responses never contain an OTP.
    prototype_code = otp_code if settings.DEBUG else None

    return challenge, prototype_code


def confirm_contact_change(*, user: User, verification_id: str, otp_code: str) -> User:
    _require_customer(user)
    error = None
    try:
        with transaction.atomic():
            user = User.objects.select_for_update().get(pk=user.pk)
            try:
                challenge = (
                    ContactVerificationChallenge.objects.select_for_update().get(
                        pk=verification_id, user=user
                    )
                )
            except (ContactVerificationChallenge.DoesNotExist, ValueError) as exc:
                raise UnprocessableEntity(
                    "Verification request was not found."
                ) from exc
            now = timezone.now()
            if challenge.status == ContactVerificationStatus.LOCKED:
                error = Locked("Too many incorrect attempts. Request a new code.")
            elif challenge.status != ContactVerificationStatus.PENDING:
                error = Conflict("This verification request is no longer active.")
            elif now >= challenge.expires_at:
                challenge.status = ContactVerificationStatus.EXPIRED
                challenge.save(update_fields=["status"])
                error = Gone("Verification code has expired. Request a new code.")
            else:
                normalized_code = otp_code.strip()
                valid = (
                    len(normalized_code) == CONTACT_OTP_LENGTH
                    and normalized_code.isdigit()
                    and check_password(normalized_code, challenge.otp_hash)
                )
                if not valid:
                    challenge.attempts_remaining = max(
                        0, challenge.attempts_remaining - 1
                    )
                    challenge.status = (
                        ContactVerificationStatus.LOCKED
                        if not challenge.attempts_remaining
                        else ContactVerificationStatus.PENDING
                    )
                    challenge.save(update_fields=["attempts_remaining", "status"])
                    error = (
                        Locked("Too many incorrect attempts. Request a new code.")
                        if not challenge.attempts_remaining
                        else UnprocessableEntity(
                            f"Incorrect code. {challenge.attempts_remaining} attempts remaining."
                        )
                    )
                else:
                    _ensure_contact_is_available(
                        user=user,
                        contact_type=challenge.contact_type,
                        pending_value=challenge.pending_value,
                    )
                    if challenge.contact_type == ContactType.EMAIL:
                        user.email = challenge.pending_value
                        user.is_email_verified = True
                    else:
                        user.phone = challenge.pending_value
                    user.save()
                    challenge.status = ContactVerificationStatus.VERIFIED
                    challenge.verified_at = now
                    challenge.save(update_fields=["status", "verified_at"])
    except IntegrityError as exc:
        raise Conflict("This contact is already in use.") from exc
    # Failed OTP attempts and expiry state must commit before raising.
    if error is not None:
        raise error
    return user
