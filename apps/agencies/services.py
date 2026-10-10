from django.db import transaction
from django.db.models import Max
from django.utils import timezone
from rest_framework.exceptions import NotFound, PermissionDenied

from apps.accounts.models import AccountAuditEvent, AccountStatus, UserRole
from apps.core.api.exceptions import Conflict

from .models import (
    AgencyProfile,
    AgencyVerificationStatus,
    AgencyVerificationSubmission,
    AgencyVerificationSubmissionStatus,
)


def _require_agency(user) -> None:
    if (
        user is None
        or not user.is_authenticated
        or not user.is_active
        or user.role != UserRole.AGENCY
    ):
        raise PermissionDenied("Agency access required.")


def _require_admin_reviewer(reviewer) -> None:
    if (
        reviewer is None
        or not reviewer.is_authenticated
        or not reviewer.is_active
        or reviewer.role != UserRole.ADMIN
        or not reviewer.is_staff
    ):
        raise PermissionDenied("Admin access required.")


def get_latest_agency_verification(*, user):
    _require_agency(user)
    return (
        AgencyVerificationSubmission.objects.filter(agency_profile__user=user)
        .select_related("reviewed_by", "agency_profile")
        .order_by("-attempt_number")
        .first()
    )


@transaction.atomic
def submit_agency_verification(
    *,
    user,
    business_registration,
    tax_identification,
    responsible_person_cin_recto,
    responsible_person_cin_verso,
    address_proof,
) -> AgencyVerificationSubmission:
    _require_agency(user)

    profile = AgencyProfile.objects.select_for_update().get(user=user)

    submissions = AgencyVerificationSubmission.objects.filter(
        agency_profile=profile,
    )

    if submissions.filter(status=AgencyVerificationSubmissionStatus.APPROVED).exists():
        raise Conflict("Agency verification is already approved.")

    if submissions.filter(status=AgencyVerificationSubmissionStatus.PENDING).exists():
        raise Conflict("An agency verification request is already pending.")

    attempt_number = (
        submissions.aggregate(value=Max("attempt_number"))["value"] or 0
    ) + 1

    profile.verification_status = AgencyVerificationStatus.PENDING
    profile.rejection_reason = ""
    profile.reviewed_by = None
    profile.reviewed_at = None
    profile.save(
        update_fields=[
            "verification_status",
            "rejection_reason",
            "reviewed_by",
            "reviewed_at",
            "updated_at",
        ]
    )

    return AgencyVerificationSubmission.objects.create(
        agency_profile=profile,
        attempt_number=attempt_number,
        business_registration=business_registration,
        tax_identification=tax_identification,
        responsible_person_cin_recto=(responsible_person_cin_recto),
        responsible_person_cin_verso=(responsible_person_cin_verso),
        address_proof=address_proof,
        status=AgencyVerificationSubmissionStatus.PENDING,
    )


def _get_locked_agency_profile(
    agency_profile_id,
) -> AgencyProfile:
    try:
        return (
            AgencyProfile.objects.select_for_update(of=("self",))
            .select_related("user", "governorate")
            .get(pk=agency_profile_id)
        )
    except (AgencyProfile.DoesNotExist, ValueError) as exc:
        raise NotFound("Agency profile was not found.") from exc


def _get_locked_pending_submission(
    agency: AgencyProfile,
) -> AgencyVerificationSubmission:
    submission = (
        AgencyVerificationSubmission.objects.select_for_update(of=("self",))
        .filter(
            agency_profile=agency,
            status=AgencyVerificationSubmissionStatus.PENDING,
        )
        .order_by("-attempt_number")
        .first()
    )

    if submission is None:
        raise Conflict(
            "The agency must submit all verification documents "
            "before it can be reviewed."
        )

    return submission


@transaction.atomic
def approve_agency(
    *,
    agency_profile_id,
    reviewer,
) -> AgencyProfile:
    _require_admin_reviewer(reviewer)
    agency = _get_locked_agency_profile(agency_profile_id)

    if agency.verification_status != AgencyVerificationStatus.PENDING:
        raise Conflict("Only pending agency verification requests can be approved.")

    submission = _get_locked_pending_submission(agency)
    for field_name in ('business_registration', 'tax_identification', 'responsible_person_cin_recto',
                       'responsible_person_cin_verso', 'address_proof'):
        document = getattr(submission, field_name)
        if not document or not document.storage.exists(document.name):
            raise Conflict('A verification file is missing. Request new uploads before approving.')
    now = timezone.now()

    submission.status = AgencyVerificationSubmissionStatus.APPROVED
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

    agency.verification_status = AgencyVerificationStatus.APPROVED
    agency.rejection_reason = ""
    agency.reviewed_by = reviewer
    agency.reviewed_at = now
    agency.save(
        update_fields=[
            "verification_status",
            "rejection_reason",
            "reviewed_by",
            "reviewed_at",
            "updated_at",
        ]
    )

    agency.user.account_status = AccountStatus.ACTIVE
    agency.user.save(
        update_fields=[
            "account_status",
            "updated_at",
        ]
    )

    AccountAuditEvent.objects.create(
        actor=reviewer,
        subject=agency.user,
        action="agency_" + agency.verification_status,
        reason=agency.rejection_reason[:500],
    )
    return agency


@transaction.atomic
def reject_agency(
    *,
    agency_profile_id,
    reviewer,
    rejection_reason: str,
) -> AgencyProfile:
    _require_admin_reviewer(reviewer)
    normalized_reason = rejection_reason.strip()

    if len(normalized_reason) < 3:
        raise Conflict("A rejection reason is required.")

    agency = _get_locked_agency_profile(agency_profile_id)

    if agency.verification_status != AgencyVerificationStatus.PENDING:
        raise Conflict("Only pending agency verification requests can be rejected.")

    submission = _get_locked_pending_submission(agency)
    now = timezone.now()

    submission.status = AgencyVerificationSubmissionStatus.REJECTED
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

    agency.verification_status = AgencyVerificationStatus.REJECTED
    agency.rejection_reason = normalized_reason
    agency.reviewed_by = reviewer
    agency.reviewed_at = now
    agency.save(
        update_fields=[
            "verification_status",
            "rejection_reason",
            "reviewed_by",
            "reviewed_at",
            "updated_at",
        ]
    )

    agency.user.account_status = AccountStatus.PENDING_VERIFICATION
    agency.user.save(
        update_fields=[
            "account_status",
            "updated_at",
        ]
    )

    AccountAuditEvent.objects.create(
        actor=reviewer,
        subject=agency.user,
        action="agency_" + agency.verification_status,
        reason=agency.rejection_reason[:500],
    )
    return agency
