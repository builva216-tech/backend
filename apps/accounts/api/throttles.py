from django.utils.crypto import salted_hmac
from rest_framework.throttling import SimpleRateThrottle


class AuthIpThrottle(SimpleRateThrottle):
    scope = "auth_ip"

    def get_cache_key(self, request, view):
        return self.cache_format % {
            "scope": self.scope,
            "ident": self.get_ident(request),
        }


class AuthIdentityThrottle(SimpleRateThrottle):
    scope = "auth_identity"

    def get_cache_key(self, request, view):
        email = str(request.data.get("email", "")).strip().lower()
        identity = salted_hmac("auth-throttle", email, algorithm="sha256").hexdigest()
        return self.cache_format % {"scope": self.scope, "ident": identity}


class RecoveryIpThrottle(AuthIpThrottle):
    scope = "recovery_ip"


class RecoveryConfirmThrottle(AuthIpThrottle):
    scope = "recovery_confirm"
