from rest_framework import serializers

from ..models import (
    AgencyCustomerRating,
    CustomerRentalReview,
)


class CustomerReviewWriteSerializer(serializers.Serializer):
    carRating = serializers.IntegerField(
        min_value=1,
        max_value=5,
    )
    agencyRating = serializers.IntegerField(
        min_value=1,
        max_value=5,
    )
    comment = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=2000,
        default="",
    )


class AgencyCustomerRatingWriteSerializer(
    serializers.Serializer
):
    punctualityRating = serializers.IntegerField(
        min_value=1,
        max_value=5,
    )
    carCareRating = serializers.IntegerField(
        min_value=1,
        max_value=5,
    )
    communicationRating = serializers.IntegerField(
        min_value=1,
        max_value=5,
    )
    privateComment = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=2000,
        default="",
    )


class CustomerRentalReviewSerializer(
    serializers.ModelSerializer
):
    bookingId = serializers.UUIDField(source="booking_id")
    customerId = serializers.UUIDField(source="customer_id")
    carId = serializers.UUIDField(source="car_id")
    agencyId = serializers.UUIDField(source="agency.user_id")
    carRating = serializers.IntegerField(source="car_rating")
    agencyRating = serializers.IntegerField(source="agency_rating")
    submittedAt = serializers.DateTimeField(source="created_at")

    class Meta:
        model = CustomerRentalReview
        fields = (
            "id",
            "bookingId",
            "customerId",
            "carId",
            "agencyId",
            "carRating",
            "agencyRating",
            "comment",
            "submittedAt",
        )


class AgencyCustomerRatingSerializer(
    serializers.ModelSerializer
):
    bookingId = serializers.UUIDField(source="booking_id")
    customerId = serializers.UUIDField(source="customer_id")
    agencyId = serializers.UUIDField(source="agency.user_id")
    punctualityRating = serializers.IntegerField(
        source="punctuality_rating"
    )
    carCareRating = serializers.IntegerField(
        source="car_care_rating"
    )
    communicationRating = serializers.IntegerField(
        source="communication_rating"
    )
    privateComment = serializers.CharField(
        source="private_comment"
    )
    submittedAt = serializers.DateTimeField(source="created_at")

    class Meta:
        model = AgencyCustomerRating
        fields = (
            "id",
            "bookingId",
            "customerId",
            "agencyId",
            "punctualityRating",
            "carCareRating",
            "communicationRating",
            "privateComment",
            "submittedAt",
        )
