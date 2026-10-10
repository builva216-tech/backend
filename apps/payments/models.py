import uuid

from django.conf import settings
from django.db import models


class PaymentMethod(models.TextChoices):
    CASH = "cash", "Pay at agency / cash"


class PaymentStatus(models.TextChoices):
    DUE = "due", "Due"
    PAID = "paid", "Paid"
    REFUNDED = "refunded", "Refunded"


class Payment(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    booking = models.OneToOneField(
        "bookings.Booking",
        on_delete=models.PROTECT,
        related_name="payment",
    )
    method = models.CharField(
        max_length=20,
        choices=PaymentMethod.choices,
        default=PaymentMethod.CASH,
    )
    status = models.CharField(
        max_length=20,
        choices=PaymentStatus.choices,
        default=PaymentStatus.DUE,
        db_index=True,
    )
    rental_amount = models.DecimalField(
        max_digits=12,
        decimal_places=3,
    )
    deposit_amount = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        default=0,
    )
    invoice_number = models.CharField(
        max_length=40,
        unique=True,
    )
    receipt_number = models.CharField(
        max_length=40,
        unique=True,
        null=True,
        blank=True,
    )
    paid_at = models.DateTimeField(null=True, blank=True)
    refunded_at = models.DateTimeField(null=True, blank=True)
    collected_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="collected_payments",
    )
    notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self) -> str:
        return f"{self.invoice_number} - {self.status}"
