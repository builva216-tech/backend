import uuid
from pathlib import Path

from django.db import models


def customer_profile_image_upload_to(instance, filename: str) -> str:
    extension = Path(filename).suffix.lower() or ".jpg"
    return (
        f"customer_profiles/{instance.user_id}/"
        f"profile{extension}"
    )


class CustomerProfile(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    user = models.OneToOneField(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="customer_profile",
    )
    governorate = models.ForeignKey(
        "locations.Governorate",
        on_delete=models.PROTECT,
        related_name="customer_profiles",
        null=True,
        blank=True,
    )
    city = models.CharField(max_length=80, blank=True, default="")
    profile_image = models.ImageField(
        upload_to=customer_profile_image_upload_to,
        max_length=500,
        null=True,
        blank=True,
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-updated_at",)

    def __str__(self) -> str:
        return self.user.email
