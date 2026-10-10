import json
from decimal import Decimal
from datetime import date

from django.utils import timezone
from rest_framework import serializers

from apps.locations.models import Governorate

from ..models import (
    AvailabilityBlock,
    Car,
    CarCategory,
    CarFuelType,
    CarPhoto,
    CarStatus,
    CarTransmission,
    ExtraOption,
    InsuranceOption,
    PricingType,
)
from ..services import validate_governorate


class CarReadSerializer(serializers.ModelSerializer):
    branchId = serializers.UUIDField(source="branch_id", read_only=True, allow_null=True)
    agencyId = serializers.UUIDField(source="agency.user_id")
    fuelType = serializers.CharField(source="fuel_type")
    dailyPrice = serializers.SerializerMethodField()
    governorateCode = serializers.CharField(source="governorate_id")
    isAvailable = serializers.BooleanField(source="is_available")
    imageUrl = serializers.SerializerMethodField()
    galleryImageUrls = serializers.SerializerMethodField()
    conditionVideoUrl = serializers.SerializerMethodField()
    createdAt = serializers.DateTimeField(source="created_at")
    updatedAt = serializers.DateTimeField(source="updated_at")
    mileageKm = serializers.IntegerField(
        source="mileage_km",
        allow_null=True,
    )
    registrationExpiry = serializers.DateField(
        source="registration_expiry",
        allow_null=True,
    )
    insuranceExpiry = serializers.DateField(
        source="insurance_expiry",
        allow_null=True,
    )

    class Meta:
        model = Car
        fields = (
            "id",
            "agencyId",
            "branchId",
            "brand",
            "model",
            "year",
            "category",
            "transmission",
            "fuelType",
            "seats",
            "doors",
            "color",
            "mileageKm",
            "dailyPrice",
            "governorateCode",
            "city",
            "status",
            "isAvailable",
            "imageUrl",
            "galleryImageUrls",
            "conditionVideoUrl",
            "registrationExpiry",
            "insuranceExpiry",
            "createdAt",
            "updatedAt",
        )

    def get_dailyPrice(self, obj):
        return float(obj.daily_price)

    def _photo_url(self, obj, photo):
        return (
            f"/api/v1/cars/{obj.id}/photos/{photo.id}/"
        )

    def get_imageUrl(self, obj):
        photo = obj.photos.order_by("position", "created_at").first()
        return None if photo is None else self._photo_url(obj, photo)

    def get_galleryImageUrls(self, obj):
        return [
            self._photo_url(obj, photo)
            for photo in obj.photos.order_by("position", "created_at")
        ]

    def get_conditionVideoUrl(self, obj):
        if not obj.condition_video:
            return None
        return f"/api/v1/cars/{obj.id}/condition-video/"


class AgencyCarReadSerializer(CarReadSerializer):
    plateNumber = serializers.CharField(source="plate_number")

    class Meta(CarReadSerializer.Meta):
        fields = CarReadSerializer.Meta.fields + ("plateNumber",)


class CarWriteSerializer(serializers.Serializer):
    brand = serializers.CharField(min_length=2, max_length=80)
    model = serializers.CharField(min_length=1, max_length=80)
    year = serializers.IntegerField(min_value=1990)
    category = serializers.ChoiceField(choices=CarCategory.choices)
    transmission = serializers.ChoiceField(
        choices=CarTransmission.choices
    )
    fuelType = serializers.ChoiceField(choices=CarFuelType.choices)
    seats = serializers.IntegerField(min_value=1, max_value=99)
    doors = serializers.IntegerField(min_value=1, max_value=10)
    color = serializers.CharField(
        max_length=40,
        allow_blank=True,
        required=False,
        default="",
    )
    mileageKm = serializers.IntegerField(
        min_value=0,
        allow_null=True,
        required=False,
    )
    plateNumber = serializers.CharField(
        max_length=32,
        allow_blank=True,
        required=False,
        default="",
    )
    dailyPrice = serializers.DecimalField(
        max_digits=12,
        decimal_places=3,
        min_value=Decimal("0.001"),
    )
    governorateCode = serializers.CharField(max_length=10)
    city = serializers.CharField(
        max_length=80,
        allow_blank=True,
        required=False,
        default="",
    )
    status = serializers.ChoiceField(
        choices=CarStatus.choices,
        required=False,
        default=CarStatus.PUBLISHED,
    )
    isAvailable = serializers.BooleanField(required=False, default=True)
    registrationExpiry = serializers.DateField(
        required=False,
        allow_null=True,
    )
    insuranceExpiry = serializers.DateField(
        required=False,
        allow_null=True,
    )
    existingPhotoIds = serializers.CharField(
        required=False,
        allow_blank=True,
        default="[]",
    )

    def validate_year(self, value):
        maximum = timezone.now().year + 1
        if value > maximum:
            raise serializers.ValidationError(
                f"Year cannot be later than {maximum}."
            )
        return value

    def validate_governorateCode(self, value):
        return validate_governorate(value)

    def validate_existingPhotoIds(self, value):
        try:
            raw = json.loads(value or "[]")
        except json.JSONDecodeError as exc:
            raise serializers.ValidationError(
                "existingPhotoIds must be valid JSON."
            ) from exc

        if not isinstance(raw, list):
            raise serializers.ValidationError(
                "existingPhotoIds must be a list."
            )

        return [str(item).strip() for item in raw if str(item).strip()]


class AvailabilityBlockSerializer(serializers.ModelSerializer):
    startsAt = serializers.DateTimeField(source="starts_at")
    endsAt = serializers.DateTimeField(source="ends_at")
    createdAt = serializers.DateTimeField(source="created_at")

    class Meta:
        model = AvailabilityBlock
        fields = (
            "id",
            "startsAt",
            "endsAt",
            "reason",
            "createdAt",
        )


class AvailabilityBlockWriteSerializer(serializers.Serializer):
    startsAt = serializers.DateTimeField()
    endsAt = serializers.DateTimeField()
    reason = serializers.CharField(
        max_length=160,
        allow_blank=True,
        required=False,
        default="",
    )


class ExtraOptionSerializer(serializers.ModelSerializer):
    pricingType = serializers.CharField(source="pricing_type")
    estimatedCost = serializers.SerializerMethodField()
    createdAt = serializers.DateTimeField(source="created_at")
    updatedAt = serializers.DateTimeField(source="updated_at")

    class Meta:
        model = ExtraOption
        fields = (
            "id",
            "name",
            "description",
            "pricingType",
            "price",
            "estimatedCost",
            "is_active",
            "createdAt",
            "updatedAt",
        )

    def get_estimatedCost(self, obj):
        return float(obj.estimated_cost)


class InsuranceOptionSerializer(serializers.ModelSerializer):
    dailyPrice = serializers.SerializerMethodField()
    estimatedDailyCost = serializers.SerializerMethodField()
    securityDeposit = serializers.SerializerMethodField()
    createdAt = serializers.DateTimeField(source="created_at")
    updatedAt = serializers.DateTimeField(source="updated_at")

    class Meta:
        model = InsuranceOption
        fields = (
            "id",
            "name",
            "description",
            "dailyPrice",
            "estimatedDailyCost",
            "securityDeposit",
            "is_active",
            "createdAt",
            "updatedAt",
        )

    def get_dailyPrice(self, obj):
        return float(obj.daily_price)

    def get_estimatedDailyCost(self, obj):
        return float(obj.estimated_daily_cost)

    def get_securityDeposit(self, obj):
        return float(obj.security_deposit)


class ExtraOptionWriteSerializer(serializers.Serializer):
    name = serializers.CharField(min_length=2, max_length=80)
    description = serializers.CharField(
        max_length=240,
        allow_blank=True,
        required=False,
        default="",
    )
    pricingType = serializers.ChoiceField(
        choices=PricingType.choices
    )
    price = serializers.DecimalField(
        max_digits=12,
        decimal_places=3,
        min_value=Decimal("0"),
    )
    estimatedCost = serializers.DecimalField(
        max_digits=12,
        decimal_places=3,
        min_value=Decimal("0"),
        required=False,
        default=Decimal("0"),
    )
    isActive = serializers.BooleanField(required=False, default=True)


class InsuranceOptionWriteSerializer(serializers.Serializer):
    name = serializers.CharField(min_length=2, max_length=80)
    description = serializers.CharField(
        max_length=240,
        allow_blank=True,
        required=False,
        default="",
    )
    dailyPrice = serializers.DecimalField(
        max_digits=12,
        decimal_places=3,
        min_value=Decimal("0"),
    )
    estimatedDailyCost = serializers.DecimalField(
        max_digits=12,
        decimal_places=3,
        min_value=Decimal("0"),
        required=False,
        default=Decimal("0"),
    )
    securityDeposit = serializers.DecimalField(
        max_digits=12,
        decimal_places=3,
        min_value=Decimal("0"),
        required=False,
        default=Decimal("0"),
    )
    isActive = serializers.BooleanField(required=False, default=True)
