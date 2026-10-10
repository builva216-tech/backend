from rest_framework import serializers

from apps.accounts.models import User

from ..models import CustomerVerificationSubmission


MAX_IMAGE_SIZE_BYTES = 10 * 1024 * 1024


def validate_verification_image(image):
    if image.size > MAX_IMAGE_SIZE_BYTES:
        raise serializers.ValidationError(
            "Each verification image must be 10 MB or smaller."
        )

    return image


class SubmitCustomerVerificationSerializer(serializers.Serializer):
    cinRecto = serializers.ImageField(
        write_only=True,
        validators=[validate_verification_image],
    )
    cinVerso = serializers.ImageField(
        write_only=True,
        validators=[validate_verification_image],
    )
    selfie = serializers.ImageField(
        write_only=True,
        validators=[validate_verification_image],
    )


class CustomerVerificationStatusSerializer(serializers.ModelSerializer):
    submissionId = serializers.UUIDField(source="id")
    attemptNumber = serializers.IntegerField(source="attempt_number")
    rejectionReason = serializers.CharField(
        source="rejection_reason"
    )
    reviewedAt = serializers.DateTimeField(
        source="reviewed_at",
        allow_null=True,
    )
    submittedAt = serializers.DateTimeField(source="submitted_at")
    updatedAt = serializers.DateTimeField(source="updated_at")

    class Meta:
        model = CustomerVerificationSubmission
        fields = (
            "submissionId",
            "attemptNumber",
            "status",
            "rejectionReason",
            "reviewedAt",
            "submittedAt",
            "updatedAt",
        )


class AdminCustomerReviewerSerializer(serializers.ModelSerializer):
    fullName = serializers.CharField(source="full_name")

    class Meta:
        model = User
        fields = (
            "id",
            "fullName",
            "email",
        )


class AdminCustomerVerificationSerializer(serializers.ModelSerializer):
    submissionId = serializers.UUIDField(source="id")
    userId = serializers.UUIDField(source="user_id")
    fullName = serializers.CharField(source="user.full_name")
    email = serializers.EmailField(source="user.email")
    phone = serializers.CharField(source="user.phone")
    accountStatus = serializers.CharField(
        source="user.account_status"
    )
    isEmailVerified = serializers.BooleanField(
        source="user.is_email_verified"
    )
    attemptNumber = serializers.IntegerField(source="attempt_number")
    rejectionReason = serializers.CharField(
        source="rejection_reason"
    )
    reviewedBy = AdminCustomerReviewerSerializer(
        source="reviewed_by",
        read_only=True,
        allow_null=True,
    )
    reviewedAt = serializers.DateTimeField(
        source="reviewed_at",
        allow_null=True,
    )
    submittedAt = serializers.DateTimeField(source="submitted_at")
    updatedAt = serializers.DateTimeField(source="updated_at")
    documents = serializers.SerializerMethodField()

    class Meta:
        model = CustomerVerificationSubmission
        fields = (
            "submissionId",
            "userId",
            "fullName",
            "email",
            "phone",
            "accountStatus",
            "isEmailVerified",
            "attemptNumber",
            "status",
            "rejectionReason",
            "reviewedBy",
            "reviewedAt",
            "submittedAt",
            "updatedAt",
            "documents",
        )

    def get_documents(self, obj):
        base = (
            f"/api/v1/admin/customers/{obj.id}/documents"
        )

        return {
            "cinRecto": f"{base}/cin-recto/",
            "cinVerso": f"{base}/cin-verso/",
            "selfie": f"{base}/selfie/",
        }


class RejectCustomerVerificationSerializer(serializers.Serializer):
    reason = serializers.CharField(
        min_length=3,
        max_length=1000,
        trim_whitespace=True,
    )
