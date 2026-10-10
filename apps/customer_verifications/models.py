import uuid
from pathlib import Path

from django.conf import settings
from django.db import models


class CustomerVerificationStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    APPROVED = "approved", "Approved"
    REJECTED = "rejected", "Rejected"
    SUPERSEDED = "superseded", "Superseded"


def _document_upload_to(instance, filename: str, document_name: str) -> str:
    extension = Path(filename).suffix.lower() or ".jpg"

    return (
        "customer_verifications/"
        f"{instance.user_id}/"
        f"{instance.id}/"
        f"{document_name}{extension}"
    )


def cin_recto_upload_to(instance, filename: str) -> str:
    return _document_upload_to(instance, filename, "cin_recto")


def cin_verso_upload_to(instance, filename: str) -> str:
    return _document_upload_to(instance, filename, "cin_verso")


def selfie_upload_to(instance, filename: str) -> str:
    return _document_upload_to(instance, filename, "selfie")


class CustomerVerificationSubmission(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="customer_verification_submissions",
    )
    attempt_number = models.PositiveIntegerField()
    status = models.CharField(
        max_length=20,
        choices=CustomerVerificationStatus.choices,
        default=CustomerVerificationStatus.PENDING,
        db_index=True,
    )

    # These files are intentionally NOT exposed through public MEDIA URLs.
    # Admins read them through authenticated API endpoints only.
    cin_recto = models.ImageField(
        upload_to=cin_recto_upload_to,
        max_length=500,
    )
    cin_verso = models.ImageField(
        upload_to=cin_verso_upload_to,
        max_length=500,
    )
    selfie = models.ImageField(
        upload_to=selfie_upload_to,
        max_length=500,
    )

    rejection_reason = models.TextField(
        blank=True,
        default="",
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_customer_verifications",
    )
    reviewed_at = models.DateTimeField(
        null=True,
        blank=True,
    )
    submitted_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-submitted_at",)
        constraints = [
            models.UniqueConstraint(
                fields=("user", "attempt_number"),
                name="cust_ver_usr_attempt_uniq",
            ),
        ]
        indexes = [
            models.Index(
                fields=("user", "status"),
                name="cust_ver_usr_status_idx",
            ),
            models.Index(
                fields=("status", "submitted_at"),
                name="cust_ver_st_sub_idx",
            ),
        ]

    def __str__(self) -> str:
        return (
            f"{self.user.email} - "
            f"attempt {self.attempt_number} - "
            f"{self.status}"
        )
