import uuid

from django.conf import settings
from django.db import models


class BookingStatus(models.TextChoices):
    REQUESTED = "requested", "Requested"
    APPROVED = "approved", "Approved"
    CONFIRMED = "confirmed", "Confirmed"
    ACTIVE = "active", "Active"
    COMPLETED = "completed", "Completed"
    REJECTED = "rejected", "Rejected"
    CANCELLED = "cancelled", "Cancelled"


class Booking(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    car = models.ForeignKey(
        "fleet.Car",
        on_delete=models.PROTECT,
        related_name="bookings",
    )
    agency = models.ForeignKey(
        "agencies.AgencyProfile",
        on_delete=models.PROTECT,
        related_name="bookings",
    )
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="customer_bookings",
    )
    pickup_at = models.DateTimeField()
    return_at = models.DateTimeField()
    rental_days = models.PositiveIntegerField()
    daily_price_snapshot = models.DecimalField(
        max_digits=12,
        decimal_places=3,
    )
    base_price = models.DecimalField(
        max_digits=12,
        decimal_places=3,
    )
    extras_total = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        default=0,
    )
    insurance_total = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        default=0,
    )
    total_price = models.DecimalField(
        max_digits=12,
        decimal_places=3,
    )
    security_deposit = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        default=0,
    )
    pickup_governorate = models.ForeignKey(
        "locations.Governorate",
        on_delete=models.PROTECT,
        related_name="booking_pickups",
    )
    pickup_city = models.CharField(
        max_length=80,
        blank=True,
        default="",
    )
    payment_method = models.CharField(
        max_length=20,
        default="cash",
    )
    status = models.CharField(
        max_length=20,
        choices=BookingStatus.choices,
        default=BookingStatus.REQUESTED,
        db_index=True,
    )
    customer_note = models.TextField(blank=True, default="")
    agency_note = models.TextField(blank=True, default="")
    agency_responded_at = models.DateTimeField(null=True, blank=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    pickup_completed_at = models.DateTimeField(null=True, blank=True)
    returned_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [
            models.Index(
                fields=("car", "status", "pickup_at", "return_at"),
                name="booking_car_status_range_idx",
            ),
            models.Index(
                fields=("agency", "status"),
                name="booking_agency_status_idx",
            ),
            models.Index(
                fields=("customer", "status"),
                name="booking_cust_status_idx",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.id} - {self.status}"


class BookingExtra(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    booking = models.ForeignKey(
        Booking,
        on_delete=models.CASCADE,
        related_name="extras",
    )
    option_id_snapshot = models.UUIDField(null=True, blank=True)
    name = models.CharField(max_length=80)
    pricing_type = models.CharField(max_length=20)
    unit_price = models.DecimalField(
        max_digits=12,
        decimal_places=3,
    )
    unit_cost = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        default=0,
    )
    quantity = models.PositiveIntegerField(default=1)
    total_price = models.DecimalField(
        max_digits=12,
        decimal_places=3,
    )


class BookingInsurance(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    booking = models.OneToOneField(
        Booking,
        on_delete=models.CASCADE,
        related_name="insurance",
    )
    option_id_snapshot = models.UUIDField(null=True, blank=True)
    name = models.CharField(max_length=80)
    daily_price = models.DecimalField(
        max_digits=12,
        decimal_places=3,
    )
    daily_cost = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        default=0,
    )
    total_price = models.DecimalField(
        max_digits=12,
        decimal_places=3,
    )
    security_deposit = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        default=0,
    )


class BookingStatusEvent(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    booking = models.ForeignKey(
        Booking,
        on_delete=models.CASCADE,
        related_name="status_events",
    )
    from_status = models.CharField(
        max_length=20,
        blank=True,
        default="",
    )
    to_status = models.CharField(max_length=20)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="booking_status_events",
    )
    note = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("created_at",)
