from rest_framework import serializers

from apps.locations.models import Governorate
from apps.profiles.models import CustomerProfile


class CustomerProfileSerializer(serializers.ModelSerializer):
    customerId = serializers.UUIDField(source="user_id")
    displayName = serializers.CharField(source="user.full_name")
    governorateCode = serializers.SerializerMethodField()
    profileImage = serializers.SerializerMethodField()
    updatedAt = serializers.DateTimeField(source="updated_at")

    class Meta:
        model = CustomerProfile
        fields = (
            "customerId",
            "displayName",
            "governorateCode",
            "city",
            "profileImage",
            "updatedAt",
        )

    def get_governorateCode(self, obj):
        return obj.governorate_id or ""

    def get_profileImage(self, obj):
        if not obj.profile_image:
            return None
        return "/api/v1/profiles/customer/me/profile-image/"


class CustomerProfileUpdateSerializer(serializers.Serializer):
    displayName = serializers.CharField(
        min_length=2,
        max_length=80,
        required=False,
    )
    governorateCode = serializers.CharField(
        max_length=10,
        allow_blank=True,
        required=False,
    )
    city = serializers.CharField(
        max_length=80,
        allow_blank=True,
        required=False,
    )
    profileImage = serializers.ImageField(
        required=False,
        allow_null=True,
    )

    def validate_governorateCode(self, value):
        normalized = value.strip().upper()

        if not normalized:
            return None

        try:
            return Governorate.objects.get(
                code=normalized,
                is_active=True,
            )
        except Governorate.DoesNotExist as exc:
            raise serializers.ValidationError(
                "Select a valid governorate."
            ) from exc
