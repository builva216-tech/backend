import uuid

from django.conf import settings
from django.db import models


class CustomerRentalReview(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    booking = models.OneToOneField(
        "bookings.Booking",
        on_delete=models.PROTECT,
        related_name="customer_review",
    )
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="rental_reviews_authored",
    )
    car = models.ForeignKey(
        "fleet.Car",
        on_delete=models.PROTECT,
        related_name="customer_reviews",
    )
    agency = models.ForeignKey(
        "agencies.AgencyProfile",
        on_delete=models.PROTECT,
        related_name="customer_reviews",
    )
    car_rating = models.PositiveSmallIntegerField()
    agency_rating = models.PositiveSmallIntegerField()
    comment = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self) -> str:
        return f"{self.booking_id} - customer review"


class AgencyCustomerRating(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    booking = models.OneToOneField(
        "bookings.Booking",
        on_delete=models.PROTECT,
        related_name="agency_customer_rating",
    )
    agency = models.ForeignKey(
        "agencies.AgencyProfile",
        on_delete=models.PROTECT,
        related_name="customer_ratings_authored",
    )
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="agency_ratings_received",
    )
    punctuality_rating = models.PositiveSmallIntegerField()
    car_care_rating = models.PositiveSmallIntegerField()
    communication_rating = models.PositiveSmallIntegerField()
    private_comment = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)

    @property
    def trust_score(self) -> float:
        return (
            (self.punctuality_rating * 0.30)
            + (self.car_care_rating * 0.50)
            + (self.communication_rating * 0.20)
        )

    def __str__(self) -> str:
        return f"{self.booking_id} - agency customer rating"
