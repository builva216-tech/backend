import uuid
from pathlib import Path

from django.db import models


class CarCategory(models.TextChoices):
    ECONOMY = "economy", "Economy"
    COMPACT = "compact", "Compact"
    SEDAN = "sedan", "Sedan"
    SUV = "suv", "SUV"
    LUXURY = "luxury", "Luxury"
    VAN = "van", "Van"


class CarTransmission(models.TextChoices):
    MANUAL = "manual", "Manual"
    AUTOMATIC = "automatic", "Automatic"


class CarFuelType(models.TextChoices):
    PETROL = "petrol", "Petrol"
    DIESEL = "diesel", "Diesel"
    HYBRID = "hybrid", "Hybrid"
    ELECTRIC = "electric", "Electric"


class CarStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    PUBLISHED = "published", "Published"
    ARCHIVED = "archived", "Archived"


class PricingType(models.TextChoices):
    PER_DAY = "perDay", "Per day"
    ONE_TIME = "oneTime", "One time"


def car_photo_upload_to(instance, filename: str) -> str:
    extension = Path(filename).suffix.lower() or ".jpg"
    return (
        f"fleet/{instance.car.agency.user_id}/"
        f"{instance.car_id}/photos/{instance.id}{extension}"
    )


def condition_video_upload_to(instance, filename: str) -> str:
    extension = Path(filename).suffix.lower() or ".mp4"
    return (
        f"fleet/{instance.agency.user_id}/"
        f"{instance.id}/condition_video{extension}"
    )


class Car(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    agency = models.ForeignKey(
        "agencies.AgencyProfile",
        on_delete=models.CASCADE,
        related_name="cars",
    )
    branch = models.ForeignKey('agencies.AgencyBranch', on_delete=models.PROTECT, null=True, blank=True, related_name='cars')
    brand = models.CharField(max_length=80)
    model = models.CharField(max_length=80)
    year = models.PositiveSmallIntegerField()
    category = models.CharField(
        max_length=20,
        choices=CarCategory.choices,
        db_index=True,
    )
    transmission = models.CharField(
        max_length=20,
        choices=CarTransmission.choices,
    )
    fuel_type = models.CharField(
        max_length=20,
        choices=CarFuelType.choices,
    )
    seats = models.PositiveSmallIntegerField(default=5)
    doors = models.PositiveSmallIntegerField(default=4)
    color = models.CharField(max_length=40, blank=True, default="")
    mileage_km = models.PositiveIntegerField(null=True, blank=True)
    plate_number = models.CharField(
        max_length=32,
        blank=True,
        default="",
    )
    daily_price = models.DecimalField(
        max_digits=12,
        decimal_places=3,
    )
    governorate = models.ForeignKey(
        "locations.Governorate",
        on_delete=models.PROTECT,
        related_name="cars",
    )
    city = models.CharField(max_length=80, blank=True, default="")
    status = models.CharField(
        max_length=20,
        choices=CarStatus.choices,
        default=CarStatus.DRAFT,
        db_index=True,
    )
    is_available = models.BooleanField(default=True, db_index=True)
    registration_expiry = models.DateField(null=True, blank=True)
    insurance_expiry = models.DateField(null=True, blank=True)
    condition_video = models.FileField(
        upload_to=condition_video_upload_to,
        max_length=500,
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [
            models.Index(
                fields=("status", "is_available"),
                name="fleet_car_status_avail_idx",
            ),
            models.Index(
                fields=("governorate", "category"),
                name="fleet_car_gov_cat_idx",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.brand} {self.model} ({self.year})"


class CarPhoto(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    car = models.ForeignKey(
        Car,
        on_delete=models.CASCADE,
        related_name="photos",
    )
    image = models.ImageField(
        upload_to=car_photo_upload_to,
        max_length=500,
    )
    position = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("position", "created_at")


class AvailabilityBlock(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    car = models.ForeignKey(
        Car,
        on_delete=models.CASCADE,
        related_name="availability_blocks",
    )
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    reason = models.CharField(max_length=160, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("starts_at",)
        indexes = [
            models.Index(
                fields=("car", "starts_at", "ends_at"),
                name="fleet_avail_car_range_idx",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.car_id}: {self.starts_at} - {self.ends_at}"


class ExtraOption(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    agency = models.ForeignKey(
        "agencies.AgencyProfile",
        on_delete=models.CASCADE,
        related_name="extra_options",
    )
    name = models.CharField(max_length=80)
    description = models.CharField(max_length=240, blank=True, default="")
    pricing_type = models.CharField(
        max_length=20,
        choices=PricingType.choices,
        default=PricingType.PER_DAY,
    )
    price = models.DecimalField(max_digits=12, decimal_places=3)
    estimated_cost = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        default=0,
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("name",)
        constraints = [
            models.UniqueConstraint(
                fields=("agency", "name"),
                name="fleet_extra_agency_name_uniq",
            ),
        ]


class InsuranceOption(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    agency = models.ForeignKey(
        "agencies.AgencyProfile",
        on_delete=models.CASCADE,
        related_name="insurance_options",
    )
    name = models.CharField(max_length=80)
    description = models.CharField(max_length=240, blank=True, default="")
    daily_price = models.DecimalField(
        max_digits=12,
        decimal_places=3,
    )
    estimated_daily_cost = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        default=0,
    )
    security_deposit = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        default=0,
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("name",)
        constraints = [
            models.UniqueConstraint(
                fields=("agency", "name"),
                name="fleet_ins_agency_name_uniq",
            ),
        ]
