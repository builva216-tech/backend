import uuid

from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models

from .managers import UserManager


class UserRole(models.TextChoices):
    CUSTOMER = "customer", "Customer"
    AGENCY = "agency", "Agency"
    ADMIN = "admin", "Admin"


class AccountStatus(models.TextChoices):
    ACTIVE = "active", "Active"
    PENDING_VERIFICATION = "pendingVerification", "Pending verification"


class ContactType(models.TextChoices):
    PHONE = "phone", "Phone"
    EMAIL = "email", "Email"


class ContactVerificationStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    VERIFIED = "verified", "Verified"
    EXPIRED = "expired", "Expired"
    LOCKED = "locked", "Locked"
    SUPERSEDED = "superseded", "Superseded"


class User(AbstractBaseUser, PermissionsMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    full_name = models.CharField(max_length=150)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=32, unique=True)
    role = models.CharField(
        max_length=20,
        choices=UserRole.choices,
        db_index=True,
    )
    account_status = models.CharField(
        max_length=32,
        choices=AccountStatus.choices,
        default=AccountStatus.ACTIVE,
        db_index=True,
    )
    session_version = models.PositiveIntegerField(default=0)
    is_email_verified = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["full_name", "phone"]

    class Meta:
        ordering = ("-date_joined",)

    def __str__(self) -> str:
        return self.email


class ContactVerificationChallenge(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="contact_verification_challenges",
    )
    contact_type = models.CharField(
        max_length=10,
        choices=ContactType.choices,
        db_index=True,
    )
    pending_value = models.CharField(max_length=254)
    otp_hash = models.CharField(max_length=128)
    status = models.CharField(
        max_length=16,
        choices=ContactVerificationStatus.choices,
        default=ContactVerificationStatus.PENDING,
        db_index=True,
    )
    attempts_remaining = models.PositiveSmallIntegerField(default=5)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    resend_available_at = models.DateTimeField()
    verified_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [
            models.Index(
                fields=("user", "contact_type", "status"),
                name="acct_contact_usr_type_st_idx",
            ),
        ]

    def __str__(self) -> str:
        return (
            f"{self.user_id}:{self.contact_type}:{self.status}:"
            f"{self.created_at.isoformat()}"
        )


class PasswordRecoveryChallenge(models.Model):
    """Recovery capability; email and clear-text codes are never stored here."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="password_recovery_challenges",
    )
    email_fingerprint = models.CharField(max_length=64, db_index=True)
    password_fingerprint = models.CharField(max_length=64)
    purpose = models.CharField(
        max_length=10, choices=[("mobile", "Mobile"), ("admin", "Admin")]
    )
    code_hash = models.CharField(max_length=128)
    attempts_remaining = models.PositiveSmallIntegerField(default=5)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(db_index=True)
    used_at = models.DateTimeField(null=True, blank=True)
    emailed_at = models.DateTimeField(null=True, blank=True)
    notification_sent_at = models.DateTimeField(null=True, blank=True)
    delivery_attempts = models.PositiveSmallIntegerField(default=0)
    next_delivery_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(
                fields=["email_fingerprint", "created_at"],
                name="recovery_email_created_idx",
            )
        ]


class AccountAuditEvent(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        on_delete=models.SET_NULL,
        related_name="performed_account_audits",
    )
    subject = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        on_delete=models.SET_NULL,
        related_name="account_audits",
    )
    action = models.CharField(max_length=64, db_index=True)
    reason = models.CharField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
