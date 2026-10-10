from rest_framework import serializers
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.recovery import confirm_password_recovery, request_password_recovery

from .throttles import RecoveryConfirmThrottle, RecoveryIpThrottle


class RecoveryRequestSerializer(serializers.Serializer):
    email = serializers.EmailField(max_length=254)


class RecoveryConfirmSerializer(serializers.Serializer):
    challengeId = serializers.UUIDField()
    code = serializers.RegexField(r"^\d{8}$", trim_whitespace=True)
    newPassword = serializers.CharField(
        min_length=8, max_length=256, trim_whitespace=False, write_only=True
    )


class PasswordRecoveryRequestView(APIView):
    permission_classes = (AllowAny,)
    authentication_classes = ()
    throttle_classes = (RecoveryIpThrottle,)
    purpose = "mobile"

    def post(self, request):
        serializer = RecoveryRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(
            request_password_recovery(
                email=serializer.validated_data["email"], purpose=self.purpose
            ),
            status=202,
        )


class PasswordRecoveryConfirmView(APIView):
    permission_classes = (AllowAny,)
    authentication_classes = ()
    throttle_classes = (RecoveryConfirmThrottle,)
    purpose = "mobile"

    def post(self, request):
        serializer = RecoveryConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        values = serializer.validated_data
        return Response(
            confirm_password_recovery(
                challenge_id=values["challengeId"],
                code=values["code"],
                password=values["newPassword"],
                purpose=self.purpose,
            )
        )


class AdminPasswordRecoveryRequestView(PasswordRecoveryRequestView):
    purpose = "admin"


class AdminPasswordRecoveryConfirmView(PasswordRecoveryConfirmView):
    purpose = "admin"
