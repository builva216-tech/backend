from django.contrib.auth import authenticate
from rest_framework import serializers
from rest_framework.exceptions import AuthenticationFailed, PermissionDenied
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import (
    ContactType,
    ContactVerificationChallenge,
    User,
    UserRole,
)
from apps.accounts.services import (
    confirm_contact_change,
    register_agency,
    register_customer,
    request_contact_change,
)

from .token_refresh import PasswordAwareTokenRefreshSerializer


class AuthUserSerializer(serializers.ModelSerializer):
    fullName = serializers.CharField(source="full_name")
    accountStatus = serializers.CharField(source="account_status")
    isEmailVerified = serializers.BooleanField(source="is_email_verified")

    class Meta:
        model = User
        fields = (
            "id",
            "fullName",
            "email",
            "phone",
            "role",
            "accountStatus",
            "isEmailVerified",
        )


def build_session_payload(user: User) -> dict:
    refresh = RefreshToken.for_user(user)
    refresh["sessionVersion"] = user.session_version

    return {
        "user": AuthUserSerializer(user).data,
        "accessToken": str(refresh.access_token),
        "refreshToken": str(refresh),
    }


class MobileLoginSerializer(serializers.Serializer):
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

        if user is None or not user.is_active:
            raise AuthenticationFailed("Invalid email or password.")

        if user.role == UserRole.ADMIN or user.is_staff:
            raise PermissionDenied(
                "Admin accounts cannot sign in to the Customer/Agency app."
            )

        return build_session_payload(user)


class CustomerRegistrationSerializer(serializers.Serializer):
    fullName = serializers.CharField(min_length=2, max_length=150)
    email = serializers.EmailField()
    phone = serializers.CharField(min_length=8, max_length=32)
    password = serializers.CharField(
        write_only=True,
        min_length=8,
        trim_whitespace=False,
    )

    def create(self, validated_data):
        user = register_customer(
            full_name=validated_data["fullName"],
            email=validated_data["email"],
            phone=validated_data["phone"],
            password=validated_data["password"],
        )
        return build_session_payload(user)


class AgencyRegistrationSerializer(serializers.Serializer):
    agencyName = serializers.CharField(min_length=2, max_length=160)
    responsiblePersonName = serializers.CharField(min_length=2, max_length=150)
    email = serializers.EmailField()
    phone = serializers.CharField(min_length=8, max_length=32)
    password = serializers.CharField(
        write_only=True,
        min_length=8,
        trim_whitespace=False,
    )
    governorateCode = serializers.CharField(min_length=5, max_length=5)
    city = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=80,
        default="",
    )

    def create(self, validated_data):
        user = register_agency(
            agency_name=validated_data["agencyName"],
            responsible_person_name=validated_data["responsiblePersonName"],
            email=validated_data["email"],
            phone=validated_data["phone"],
            password=validated_data["password"],
            governorate_code=validated_data["governorateCode"],
            city=validated_data.get("city", ""),
        )
        return build_session_payload(user)


class MobileTokenRefreshSerializer(serializers.Serializer):
    refreshToken = serializers.CharField(write_only=True)

    def validate(self, attrs):
        delegate = PasswordAwareTokenRefreshSerializer(
            data={"refresh": attrs["refreshToken"]}
        )
        delegate.is_valid(raise_exception=True)
        token_data = delegate.validated_data

        response = {
            "accessToken": token_data["access"],
        }

        if "refresh" in token_data:
            response["refreshToken"] = token_data["refresh"]

        return response


class LogoutSerializer(serializers.Serializer):
    refreshToken = serializers.CharField()

    def save(self, **kwargs):
        try:
            RefreshToken(self.validated_data["refreshToken"]).blacklist()
        except Exception as exc:
            raise serializers.ValidationError(
                {"refreshToken": ["Invalid or expired refresh token."]}
            ) from exc


class ContactVerificationSerializer(serializers.ModelSerializer):
    verificationId = serializers.UUIDField(source="id")
    customerId = serializers.UUIDField(source="user_id")
    type = serializers.CharField(source="contact_type")
    pendingValue = serializers.CharField(source="pending_value")
    createdAt = serializers.DateTimeField(source="created_at")
    expiresAt = serializers.DateTimeField(source="expires_at")
    resendAvailableAt = serializers.DateTimeField(source="resend_available_at")
    attemptsRemaining = serializers.IntegerField(source="attempts_remaining")

    class Meta:
        model = ContactVerificationChallenge
        fields = (
            "verificationId",
            "customerId",
            "type",
            "pendingValue",
            "status",
            "createdAt",
            "expiresAt",
            "resendAvailableAt",
            "attemptsRemaining",
        )


class ContactChangeRequestSerializer(serializers.Serializer):
    type = serializers.ChoiceField(choices=ContactType.choices)
    value = serializers.CharField(max_length=254)

    def create(self, validated_data):
        challenge, prototype_code = request_contact_change(
            user=self.context["request"].user,
            contact_type=validated_data["type"],
            value=validated_data["value"],
        )

        payload = {
            "verification": ContactVerificationSerializer(challenge).data,
        }

        if prototype_code is not None:
            payload["prototypeOtpCode"] = prototype_code

        return payload


class ContactChangeConfirmSerializer(serializers.Serializer):
    verificationId = serializers.UUIDField()
    otpCode = serializers.CharField(
        min_length=6,
        max_length=6,
        trim_whitespace=True,
    )

    def create(self, validated_data):
        return confirm_contact_change(
            user=self.context["request"].user,
            verification_id=str(validated_data["verificationId"]),
            otp_code=validated_data["otpCode"],
        )
