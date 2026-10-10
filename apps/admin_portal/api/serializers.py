from django.contrib.auth import authenticate
from rest_framework import serializers
from rest_framework.exceptions import (
    AuthenticationFailed,
    PermissionDenied,
)
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.api.serializers import AuthUserSerializer
from apps.accounts.api.token_refresh import PasswordAwareTokenRefreshSerializer
from apps.accounts.models import User, UserRole
from apps.agencies.models import (
    AgencyProfile,
)


def _require_admin_user(user: User | None) -> User:
    if user is None or not user.is_active:
        raise AuthenticationFailed("Invalid admin credentials.")

    if user.role != UserRole.ADMIN or not user.is_staff:
        raise PermissionDenied("Admin access required.")

    return user


def _build_admin_session_payload(user: User) -> dict:
    refresh = RefreshToken.for_user(user)
    refresh["sessionVersion"] = user.session_version

    return {
        "user": AuthUserSerializer(user).data,
        "accessToken": str(refresh.access_token),
        "refreshToken": str(refresh),
    }


class AdminLoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(
        write_only=True,
        trim_whitespace=False,
    )

    def validate(self, attrs):
        email = attrs["email"].strip().lower()
        password = attrs["password"]

        user = authenticate(
            request=self.context.get("request"),
            email=email,
            password=password,
        )
        user = _require_admin_user(user)
        return _build_admin_session_payload(user)


class AdminTokenRefreshSerializer(serializers.Serializer):
    refreshToken = serializers.CharField(write_only=True)

    def validate(self, attrs):
        raw_refresh_token = attrs["refreshToken"].strip()

        try:
            source_refresh = RefreshToken(raw_refresh_token)
            user_id = source_refresh["user_id"]
            user = User.objects.filter(pk=user_id).first()
        except Exception as exc:
            raise AuthenticationFailed("Invalid or expired refresh token.") from exc

        _require_admin_user(user)

        delegate = PasswordAwareTokenRefreshSerializer(
            data={"refresh": raw_refresh_token}, context={"purpose": "admin"}
        )
        delegate.is_valid(raise_exception=True)
        token_data = delegate.validated_data

        payload = {"accessToken": token_data["access"]}

        if "refresh" in token_data:
            payload["refreshToken"] = token_data["refresh"]

        return payload


class AdminReviewerSerializer(serializers.ModelSerializer):
    fullName = serializers.CharField(source="full_name")

    class Meta:
        model = User
        fields = (
            "id",
            "fullName",
            "email",
        )


class AdminAgencyVerificationSerializer(serializers.ModelSerializer):
    agencyProfileId = serializers.UUIDField(source="id")
    userId = serializers.UUIDField(source="user_id")
    agencyName = serializers.CharField(source="agency_name")
    responsiblePersonName = serializers.CharField(source="user.full_name")
    email = serializers.EmailField(source="user.email")
    phone = serializers.CharField(source="user.phone")
    accountStatus = serializers.CharField(source="user.account_status")
    governorateCode = serializers.CharField(source="governorate.code")
    governorateNameAr = serializers.CharField(source="governorate.name_ar")
    governorateNameFr = serializers.CharField(source="governorate.name_fr")
    governorateNameEn = serializers.CharField(source="governorate.name_en")
    verificationStatus = serializers.CharField(source="verification_status")
    rejectionReason = serializers.CharField(source="rejection_reason")
    reviewedBy = AdminReviewerSerializer(
        source="reviewed_by",
        read_only=True,
        allow_null=True,
    )
    reviewedAt = serializers.DateTimeField(
        source="reviewed_at",
        allow_null=True,
    )
    createdAt = serializers.DateTimeField(source="created_at")
    updatedAt = serializers.DateTimeField(source="updated_at")

    # Canonical RC7 contract used by Admin Web.
    hasSubmittedDocuments = serializers.SerializerMethodField()
    latestSubmission = serializers.SerializerMethodField()

    # Legacy fields are retained temporarily so older Admin builds do not
    # break while moving to the canonical nested contract.
    documentsSubmitted = serializers.SerializerMethodField()
    attemptNumber = serializers.SerializerMethodField()
    documents = serializers.SerializerMethodField()

    class Meta:
        model = AgencyProfile
        fields = (
            "agencyProfileId",
            "userId",
            "agencyName",
            "responsiblePersonName",
            "email",
            "phone",
            "accountStatus",
            "governorateCode",
            "governorateNameAr",
            "governorateNameFr",
            "governorateNameEn",
            "city",
            "verificationStatus",
            "rejectionReason",
            "reviewedBy",
            "reviewedAt",
            "createdAt",
            "updatedAt",
            "hasSubmittedDocuments",
            "latestSubmission",
            "documentsSubmitted",
            "attemptNumber",
            "documents",
        )

    def _latest_submission(self, obj):
        prefetched = getattr(
            obj,
            "_latest_verification_submission",
            None,
        )

        if prefetched is not None:
            return prefetched

        return (
            obj.verification_submissions.select_related("reviewed_by")
            .order_by("-attempt_number")
            .first()
        )

    def _document_paths(self, obj, submission):
        if submission is None:
            return None

        base = f"/api/v1/admin/agencies/{obj.id}/documents"

        return {
            "businessRegistration": (f"{base}/business-registration/"),
            "taxIdentification": (f"{base}/tax-identification/"),
            "responsibleCinRecto": (f"{base}/responsible-person-cin-recto/"),
            "responsibleCinVerso": (f"{base}/responsible-person-cin-verso/"),
            "addressProof": f"{base}/address-proof/",
        }

    def _submission_payload(self, obj, submission):
        if submission is None:
            return None

        reviewer = (
            None
            if submission.reviewed_by is None
            else AdminReviewerSerializer(submission.reviewed_by).data
        )

        return {
            "submissionId": str(submission.id),
            "attemptNumber": submission.attempt_number,
            "status": submission.status,
            "rejectionReason": submission.rejection_reason,
            "reviewedBy": reviewer,
            "reviewedAt": submission.reviewed_at,
            "submittedAt": submission.submitted_at,
            "updatedAt": submission.updated_at,
            "documents": self._document_paths(
                obj,
                submission,
            ),
        }

    def get_hasSubmittedDocuments(self, obj):
        return self._latest_submission(obj) is not None

    def get_latestSubmission(self, obj):
        return self._submission_payload(
            obj,
            self._latest_submission(obj),
        )

    def get_documentsSubmitted(self, obj):
        return self.get_hasSubmittedDocuments(obj)

    def get_attemptNumber(self, obj):
        submission = self._latest_submission(obj)
        return None if submission is None else submission.attempt_number

    def get_documents(self, obj):
        submission = self._latest_submission(obj)
        paths = self._document_paths(
            obj,
            submission,
        )

        if submission is None or paths is None:
            return None

        # Legacy flat shape.
        return {
            "submissionId": str(submission.id),
            "status": submission.status,
            "businessRegistration": paths["businessRegistration"],
            "taxIdentification": paths["taxIdentification"],
            "responsiblePersonCinRecto": paths["responsibleCinRecto"],
            "responsiblePersonCinVerso": paths["responsibleCinVerso"],
            "addressProof": paths["addressProof"],
        }


class RejectAgencySerializer(serializers.Serializer):
    reason = serializers.CharField(
        min_length=3,
        max_length=1000,
        trim_whitespace=True,
    )
