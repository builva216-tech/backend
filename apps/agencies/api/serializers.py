import uuid
from pathlib import Path
from PIL import Image, UnidentifiedImageError

from rest_framework import serializers

from apps.agencies.models import (
    AgencyProfile,
    AgencyVerificationSubmission,
)

MAX_VERIFICATION_FILE_BYTES = 10 * 1024 * 1024
ALLOWED_DOCUMENT_EXTENSIONS = {
    ".pdf",
    ".jpg",
    ".jpeg",
    ".png",
}
ALLOWED_IMAGE_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
}


def _validate_file(file, *, image_only: bool = False):
    if file.size <= 0:
        raise serializers.ValidationError("The selected file is empty.")

    if file.size > MAX_VERIFICATION_FILE_BYTES:
        raise serializers.ValidationError(
            "Each verification file must be 10 MB or smaller."
        )

    extension = Path(file.name).suffix.lower()
    allowed = ALLOWED_IMAGE_EXTENSIONS if image_only else ALLOWED_DOCUMENT_EXTENSIONS

    if extension not in allowed:
        raise serializers.ValidationError("Unsupported verification file format.")

    position = file.tell()
    try:
        if extension == '.pdf':
            if not file.read(5).startswith(b'%PDF-'):
                raise serializers.ValidationError('The selected file is not a PDF document.')
        else:
            image = Image.open(file)
            if image.width * image.height > 25_000_000:
                raise serializers.ValidationError('The image dimensions are too large.')
            image.verify()
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError):
        raise serializers.ValidationError('The selected file is not a valid image.') from None
    finally:
        file.seek(position)
    return file


def validate_document(file):
    return _validate_file(file)


def validate_image(file):
    return _validate_file(file, image_only=True)


class CurrentAgencyProfileSerializer(serializers.ModelSerializer):
    isVerified = serializers.SerializerMethodField()
    updatedAt = serializers.DateTimeField(source="updated_at")
    profileImage = serializers.SerializerMethodField()
    agencyId = serializers.UUIDField(source="user_id")
    agencyName = serializers.CharField(source="agency_name")
    responsiblePersonName = serializers.CharField(source="user.full_name")
    email = serializers.EmailField(source="user.email")
    phone = serializers.CharField(source="user.phone")
    governorateCode = serializers.CharField(source="governorate_id")
    fleetSize = serializers.SerializerMethodField()

    class Meta:
        model = AgencyProfile
        fields = (
            "agencyId",
            "agencyName",
            "responsiblePersonName",
            "email",
            "phone",
            "governorateCode",
            "city",
            "bio",
            "services",
            "fleetSize",
            "updatedAt",
            "isVerified",
            "profileImage",
        )

    def get_isVerified(self, obj):
        return bool(
            obj.verification_status == "approved"
            and obj.user.is_active
            and obj.user.account_status == "active"
        )

    def get_profileImage(self, obj):
        return (
            f"/api/v1/agencies/{obj.user_id}/profile-image/"
            if obj.profile_image
            else None
        )

    def get_fleetSize(self, obj):
        related = getattr(obj, "cars", None)
        if related is None:
            return 0
        return related.exclude(status="archived").count()


class PublicAgencyProfileSerializer(serializers.ModelSerializer):
    isVerified = serializers.SerializerMethodField()
    agencyId = serializers.UUIDField(source="user_id")
    displayName = serializers.CharField(source="agency_name")
    governorateCode = serializers.CharField(source="governorate_id")
    governorateNameAr = serializers.CharField(source="governorate.name_ar")
    governorateNameFr = serializers.CharField(source="governorate.name_fr")
    governorateNameEn = serializers.CharField(source="governorate.name_en")
    updatedAt = serializers.DateTimeField(source="updated_at")
    profileImage = serializers.SerializerMethodField()

    class Meta:
        model = AgencyProfile
        fields = (
            "agencyId",
            "displayName",
            "governorateCode",
            "governorateNameAr",
            "governorateNameFr",
            "governorateNameEn",
            "city",
            "bio",
            "services",
            "profileImage",
            "updatedAt",
            "isVerified",
        )

    def get_isVerified(self, obj):
        return bool(
            obj.verification_status == "approved"
            and obj.user.is_active
            and obj.user.account_status == "active"
        )

    def get_profileImage(self, obj):
        if not obj.profile_image:
            return None
        return f"/api/v1/agencies/{obj.user_id}/profile-image/"


class SubmitAgencyVerificationSerializer(serializers.Serializer):
    businessRegistration = serializers.FileField(
        write_only=True,
        validators=[validate_document],
    )
    taxIdentification = serializers.FileField(
        write_only=True,
        validators=[validate_document],
    )
    responsiblePersonCinRecto = serializers.ImageField(
        write_only=True,
        validators=[validate_image],
    )
    responsiblePersonCinVerso = serializers.ImageField(
        write_only=True,
        validators=[validate_image],
    )
    addressProof = serializers.FileField(
        write_only=True,
        validators=[validate_document],
    )


class AgencyVerificationStatusSerializer(serializers.ModelSerializer):
    submissionId = serializers.UUIDField(source="id")
    agencyId = serializers.UUIDField(source="agency_profile.user_id")
    attemptNumber = serializers.IntegerField(source="attempt_number")
    adminNote = serializers.CharField(source="rejection_reason")
    submittedAt = serializers.DateTimeField(source="submitted_at")
    reviewedAt = serializers.DateTimeField(
        source="reviewed_at",
        allow_null=True,
    )

    class Meta:
        model = AgencyVerificationSubmission
        fields = (
            "submissionId",
            "agencyId",
            "attemptNumber",
            "status",
            "adminNote",
            "submittedAt",
            "reviewedAt",
        )


class AgencyProfileWriteSerializer(serializers.Serializer):
    agencyId = serializers.UUIDField(required=False)
    agencyName = serializers.CharField(min_length=2, max_length=160, required=False)
    governorateCode = serializers.CharField(max_length=5, required=False)
    city = serializers.CharField(max_length=80, allow_blank=True, required=False)
    bio = serializers.CharField(max_length=500, allow_blank=True, required=False)
    services = serializers.ListField(
        child=serializers.CharField(min_length=2, max_length=40),
        max_length=10,
        required=False,
    )
    profileImage = serializers.ImageField(required=False, allow_empty_file=False)
    removeProfileImage = serializers.BooleanField(required=False, default=False)
    expectedUpdatedAt = serializers.DateTimeField(required=False)

    def validate_governorateCode(self, value):
        from apps.fleet.services import validate_governorate

        return validate_governorate(value).pk

    def validate_services(self, value):
        if len({item.casefold() for item in value}) != len(value):
            raise serializers.ValidationError("Use unique services.")
        return value

    def validate_profileImage(self, value):
        if value.size > 2 * 1024 * 1024:
            raise serializers.ValidationError("Profile images must be 2 MB or smaller.")
        if getattr(value.image, "format", "") not in {"JPEG", "PNG", "WEBP"}:
            raise serializers.ValidationError("Use a JPEG, PNG or WEBP image.")
        extensions = {"JPEG": "jpg", "PNG": "png", "WEBP": "webp"}
        value.name = f"{uuid.uuid4()}.{extensions[value.image.format]}"
        return value

    def validate(self, attrs):
        if attrs.get("profileImage") and attrs.get("removeProfileImage"):
            raise serializers.ValidationError(
                "Choose an image upload or removal, not both."
            )
        return attrs
