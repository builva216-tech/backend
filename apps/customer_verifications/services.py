from django.db import transaction
from django.db.models import Max
from django.utils import timezone
from rest_framework.exceptions import NotFound, PermissionDenied

from apps.accounts.models import UserRole
from apps.core.api.exceptions import Conflict

from .models import (
    CustomerVerificationStatus,
    CustomerVerificationSubmission,
)


def _require_customer(user) -> None:
    if (
        user is None
        or not user.is_authenticated
        or not user.is_active
        or user.role != UserRole.CUSTOMER
    ):
        raise PermissionDenied("Customer access required.")


def _require_admin_reviewer(reviewer) -> None:
    if (
        reviewer is None
        or not reviewer.is_authenticated
        or not reviewer.is_active
        or reviewer.role != UserRole.ADMIN
        or not reviewer.is_staff
    ):
        raise PermissionDenied("Admin access required.")


@transaction.atomic
def submit_customer_verification(
    *,
    user,
    cin_recto,
    cin_verso,
    selfie,
) -> CustomerVerificationSubmission:
    _require_customer(user)

    # Lock the user row so two concurrent submissions cannot receive
    # the same attempt number or bypass the single-pending rule.
    user.__class__.objects.select_for_update().get(pk=user.pk)

    submissions = CustomerVerificationSubmission.objects.filter(
        user=user,
    )

    if submissions.filter(
        status=CustomerVerificationStatus.APPROVED
    ).exists():
        raise Conflict("Customer verification is already approved.")

    if submissions.filter(
        status=CustomerVerificationStatus.PENDING
    ).exists():
        raise Conflict(
            "A customer verification request is already pending."
        )

    latest_attempt = (
        submissions.aggregate(value=Max("attempt_number"))["value"]
        or 0
    )

    return CustomerVerificationSubmission.objects.create(
        user=user,
        attempt_number=latest_attempt + 1,
        cin_recto=cin_recto,
        cin_verso=cin_verso,
        selfie=selfie,
        status=CustomerVerificationStatus.PENDING,
    )


def get_latest_customer_verification(*, user):
    _require_customer(user)

    return (
        CustomerVerificationSubmission.objects.filter(user=user)
        .select_related("reviewed_by")
        .order_by("-attempt_number")
        .first()
    )


def _get_locked_submission(
    submission_id,
) -> CustomerVerificationSubmission:
    try:
        return (
            CustomerVerificationSubmission.objects
            .select_for_update(of=("self",))
            .select_related("user")
            .get(pk=submission_id)
        )
    except (
        CustomerVerificationSubmission.DoesNotExist,
        ValueError,
    ) as exc:
        raise NotFound(
            "Customer verification request was not found."
        ) from exc


@transaction.atomic
def approve_customer_verification(
    *,
    submission_id,
    reviewer,
) -> CustomerVerificationSubmission:
    _require_admin_reviewer(reviewer)

    submission = _get_locked_submission(submission_id)

    if submission.status != CustomerVerificationStatus.PENDING:
        raise Conflict(
            "Only pending customer verification requests "
            "can be approved."
        )

    now = timezone.now()

    submission.status = CustomerVerificationStatus.APPROVED
    submission.rejection_reason = ""
    submission.reviewed_by = reviewer
    submission.reviewed_at = now
    submission.save(
        update_fields=[
            "status",
            "rejection_reason",
            "reviewed_by",
            "reviewed_at",
            "updated_at",
        ]
    )

    # Customer account status is deliberately not overloaded with identity
    # verification state. Booking eligibility will query this verification
    # record when that business rule is enabled.
    return submission


@transaction.atomic
def reject_customer_verification(
    *,
    submission_id,
    reviewer,
    rejection_reason: str,
) -> CustomerVerificationSubmission:
    _require_admin_reviewer(reviewer)

    normalized_reason = rejection_reason.strip()

    if len(normalized_reason) < 3:
        raise Conflict("A rejection reason is required.")

    submission = _get_locked_submission(submission_id)

    if submission.status != CustomerVerificationStatus.PENDING:
        raise Conflict(
            "Only pending customer verification requests "
            "can be rejected."
        )

    now = timezone.now()

    submission.status = CustomerVerificationStatus.REJECTED
    submission.rejection_reason = normalized_reason
    submission.reviewed_by = reviewer
    submission.reviewed_at = now
    submission.save(
        update_fields=[
            "status",
            "rejection_reason",
            "reviewed_by",
            "reviewed_at",
            "updated_at",
        ]
    )

    return submission
