from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.settings import api_settings
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.utils import get_md5_hash_password

from apps.accounts.models import User, UserRole


class PasswordAwareTokenRefreshSerializer(TokenRefreshSerializer):
    def validate(self, attrs):
        try:
            token = RefreshToken(attrs["refresh"])
        except TokenError as exc:
            raise AuthenticationFailed("Session expired. Sign in again.") from exc
        user = User.objects.filter(
            id=token.get(api_settings.USER_ID_CLAIM), is_active=True
        ).first()
        purpose = self.context.get("purpose", "mobile")
        eligible = bool(
            user
            and (
                (purpose == "admin" and user.role == UserRole.ADMIN and user.is_staff)
                or (
                    purpose == "mobile"
                    and user.role in [UserRole.CUSTOMER, UserRole.AGENCY]
                )
            )
        )
        if (
            not eligible
            or token.get("sessionVersion", 0) != user.session_version
            or token.get(api_settings.REVOKE_TOKEN_CLAIM)
            != get_md5_hash_password(user.password)
        ):
            raise AuthenticationFailed("Session expired. Sign in again.")
        try:
            return super().validate(attrs)
        except TokenError as exc:
            raise AuthenticationFailed("Session expired. Sign in again.") from exc
