from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.authentication import JWTAuthentication


class AccountSessionAuthentication(JWTAuthentication):
    def get_user(self, validated_token):
        user = super().get_user(validated_token)
        if validated_token.get("sessionVersion", 0) != user.session_version:
            raise AuthenticationFailed("Session expired. Sign in again.")
        return user
