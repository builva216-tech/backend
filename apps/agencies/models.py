import uuid
from pathlib import Path

from django.conf import settings
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator


class AgencyVerificationStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    APPROVED = "approved", "Approved"
    REJECTED = "rejected", "Rejected"


class AgencyVerificationSubmissionStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    APPROVED = "approved", "Approved"
    REJECTED = "rejected", "Rejected"
    SUPERSEDED = "superseded", "Superseded"


class AgencyProfile(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="agency_profile",
    )
    agency_name = models.CharField(max_length=160)
    governorate = models.ForeignKey(
        "locations.Governorate",
        on_delete=models.PROTECT,
        related_name="agencies",
    )
    city = models.CharField(max_length=80, blank=True, default="")
    bio = models.TextField(blank=True, default="", max_length=500)
    services = models.JSONField(default=list, blank=True)
    profile_image = models.ImageField(
        upload_to="agency_profiles/",
        blank=True,
        null=True,
        max_length=500,
    )
    verification_status = models.CharField(
        max_length=20,
        choices=AgencyVerificationStatus.choices,
        default=AgencyVerificationStatus.PENDING,
        db_index=True,
    )
    rejection_reason = models.TextField(blank=True, default="")
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_agency_profiles",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self) -> str:
        return self.agency_name


def _agency_document_upload_to(
    instance,
    filename: str,
    document_name: str,
) -> str:
    extension = Path(filename).suffix.lower() or ".bin"
    return (
        "agency_verifications/"
        f"{instance.agency_profile.user_id}/"
        f"{instance.id}/"
        f"{document_name}{extension}"
    )


def business_registration_upload_to(instance, filename: str) -> str:
    return _agency_document_upload_to(
        instance,
        filename,
        "business_registration",
    )


def tax_identification_upload_to(instance, filename: str) -> str:
    return _agency_document_upload_to(
        instance,
        filename,
        "tax_identification",
    )


def responsible_person_cin_recto_upload_to(
    instance,
    filename: str,
) -> str:
    return _agency_document_upload_to(
        instance,
        filename,
        "responsible_person_cin_recto",
    )


def responsible_person_cin_verso_upload_to(
    instance,
    filename: str,
) -> str:
    return _agency_document_upload_to(
        instance,
        filename,
        "responsible_person_cin_verso",
    )


def address_proof_upload_to(instance, filename: str) -> str:
    return _agency_document_upload_to(
        instance,
        filename,
        "address_proof",
    )


class AgencyVerificationSubmission(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    agency_profile = models.ForeignKey(
        AgencyProfile,
        on_delete=models.CASCADE,
        related_name="verification_submissions",
    )
    attempt_number = models.PositiveIntegerField()
    status = models.CharField(
        max_length=20,
        choices=AgencyVerificationSubmissionStatus.choices,
        default=AgencyVerificationSubmissionStatus.PENDING,
        db_index=True,
    )

    business_registration = models.FileField(
        upload_to=business_registration_upload_to,
        max_length=500,
    )
    tax_identification = models.FileField(
        upload_to=tax_identification_upload_to,
        max_length=500,
    )
    responsible_person_cin_recto = models.ImageField(
        upload_to=responsible_person_cin_recto_upload_to,
        max_length=500,
    )
    responsible_person_cin_verso = models.ImageField(
        upload_to=responsible_person_cin_verso_upload_to,
        max_length=500,
    )
    address_proof = models.FileField(
        upload_to=address_proof_upload_to,
        max_length=500,
    )

    rejection_reason = models.TextField(blank=True, default="")
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_agency_verification_submissions",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-submitted_at",)
        constraints = [
            models.UniqueConstraint(
                fields=("agency_profile", "attempt_number"),
                name="ag_ver_profile_attempt_uniq",
            ),
        ]
        indexes = [
            models.Index(
                fields=("agency_profile", "status"),
                name="ag_ver_profile_status_idx",
            ),
            models.Index(
                fields=("status", "submitted_at"),
                name="ag_ver_status_sub_idx",
            ),
        ]

    def __str__(self) -> str:
        return (
            f"{self.agency_profile.agency_name} - "
            f"attempt {self.attempt_number} - {self.status}"
        )


class AgencyCustomerRecord(models.Model):
    """Private agency service notes, not a platform-wide customer risk score."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    agency = models.ForeignKey(
        AgencyProfile, on_delete=models.CASCADE, related_name="customer_records"
    )
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="agency_service_records",
    )
    alias = models.CharField(max_length=80, blank=True, default="")
    notes = models.TextField(max_length=4000, blank=True, default="")
    tags = models.JSONField(default=list, blank=True)
    tasks = models.JSONField(default=list, blank=True)
    revision = models.PositiveIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["agency", "customer"], name="unique_agency_customer_record"
            )
        ]


class SubscriptionPlan(models.Model):
    code = models.CharField(max_length=20, primary_key=True, choices=[('small', 'Small'), ('medium', 'Medium'), ('enterprise', 'Enterprise')])
    name = models.CharField(max_length=80)
    monthly_tnd = models.DecimalField(max_digits=9, decimal_places=2, validators=[MinValueValidator(0)])
    price_text = models.CharField(max_length=120, blank=True)
    description = models.CharField(max_length=500, blank=True)
    cars = models.PositiveIntegerField(validators=[MinValueValidator(1), MaxValueValidator(100000)])
    branches = models.PositiveIntegerField(validators=[MinValueValidator(1), MaxValueValidator(10000)])
    is_active = models.BooleanField(default=True)
    recommended = models.BooleanField(default=False)
    revision = models.PositiveIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['monthly_tnd', 'code']

    def __str__(self):
        return self.name


class AgencySubscription(models.Model):
    """Trial derives from agency registration; payment activation is admin-only."""
    agency = models.OneToOneField(AgencyProfile, on_delete=models.CASCADE, related_name='subscription', primary_key=True)
    plan = models.CharField(max_length=20, choices=[('small', 'Small'), ('medium', 'Medium'), ('enterprise', 'Enterprise')], default='medium')
    paid_until = models.DateTimeField(null=True, blank=True)
    suspended = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.agency.agency_name}: {self.plan}'


class AgencyBranch(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    agency = models.ForeignKey(AgencyProfile, on_delete=models.CASCADE, related_name='branches')
    name = models.CharField(max_length=120)
    address = models.CharField(max_length=300, blank=True)
    governorate = models.ForeignKey('locations.Governorate', on_delete=models.PROTECT)
    city = models.CharField(max_length=80, blank=True)
    latitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    longitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ('created_at',)
        constraints = [models.UniqueConstraint(fields=['agency', 'name'], name='unique_agency_branch_name')]

    def __str__(self):
        return f'{self.agency.agency_name} — {self.name}'


class AgencySubscriptionRequest(models.Model):
    agency = models.ForeignKey(AgencyProfile, on_delete=models.CASCADE, related_name='subscription_requests')
    plan = models.CharField(max_length=20, choices=AgencySubscription._meta.get_field('plan').choices)
    status = models.CharField(max_length=20, choices=(('requested', 'Requested'), ('resolved', 'Resolved')), default='requested')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('-created_at',)
        constraints = [models.UniqueConstraint(fields=('agency',), condition=models.Q(status='requested'), name='one_pending_subscription_request')]
