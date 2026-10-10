from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.api.permissions import IsCustomer
from apps.accounts.api.throttles import AuthIdentityThrottle, AuthIpThrottle

from .serializers import (
    AgencyRegistrationSerializer,
    AuthUserSerializer,
    ContactChangeConfirmSerializer,
    ContactChangeRequestSerializer,
    CustomerRegistrationSerializer,
    LogoutSerializer,
    MobileLoginSerializer,
    MobileTokenRefreshSerializer,
)


class MobileLoginView(APIView):
    throttle_classes = [AuthIpThrottle, AuthIdentityThrottle]
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        serializer = MobileLoginSerializer(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        return Response(
            serializer.validated_data,
            status=status.HTTP_200_OK,
        )


class CustomerRegistrationView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        serializer = CustomerRegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        session = serializer.save()
        return Response(session, status=status.HTTP_201_CREATED)


class AgencyRegistrationView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        serializer = AgencyRegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        session = serializer.save()
        return Response(session, status=status.HTTP_201_CREATED)


class MobileTokenRefreshView(APIView):
    def get_authenticate_header(self, request):
        return "Bearer"

    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        serializer = MobileTokenRefreshSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(
            serializer.validated_data,
            status=status.HTTP_200_OK,
        )


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(AuthUserSerializer(request.user).data)


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = LogoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ContactChangeRequestView(APIView):
    permission_classes = [IsAuthenticated, IsCustomer]

    def post(self, request):
        serializer = ContactChangeRequestSerializer(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        payload = serializer.save()
        return Response(payload, status=status.HTTP_201_CREATED)


class ContactChangeConfirmView(APIView):
    permission_classes = [IsAuthenticated, IsCustomer]

    def post(self, request):
        serializer = ContactChangeConfirmSerializer(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(
            AuthUserSerializer(user).data,
            status=status.HTTP_200_OK,
        )
