from django.http import HttpResponse
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import UserRole
from apps.profiles.models import CustomerProfile

from .serializers import (
    CustomerProfileSerializer,
    CustomerProfileUpdateSerializer,
)


class CustomerProfileMeView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def _require_customer(self, request):
        if request.user.role != UserRole.CUSTOMER:
            return None
        profile, _ = CustomerProfile.objects.get_or_create(
            user=request.user
        )
        return profile

    def get(self, request):
        profile = self._require_customer(request)
        if profile is None:
            return Response(
                {"detail": "Customer access required."},
                status=status.HTTP_403_FORBIDDEN,
            )
        return Response(CustomerProfileSerializer(profile).data)

    def patch(self, request):
        profile = self._require_customer(request)
        if profile is None:
            return Response(
                {"detail": "Customer access required."},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = CustomerProfileUpdateSerializer(
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        if "displayName" in data:
            request.user.full_name = data["displayName"].strip()
            request.user.save(
                update_fields=["full_name", "updated_at"]
            )

        if "governorateCode" in data:
            profile.governorate = data["governorateCode"]

        if "city" in data:
            profile.city = data["city"].strip()

        if "profileImage" in data:
            profile.profile_image = data["profileImage"]

        profile.save()

        return Response(CustomerProfileSerializer(profile).data)


class CustomerProfileImageView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.role != UserRole.CUSTOMER:
            return Response(
                {"detail": "Customer access required."},
                status=status.HTTP_403_FORBIDDEN,
            )

        profile, _ = CustomerProfile.objects.get_or_create(
            user=request.user
        )

        if not profile.profile_image:
            return Response(
                {"detail": "Profile image was not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        profile.profile_image.open("rb")
        try:
            payload = profile.profile_image.read()
        finally:
            profile.profile_image.close()

        response = HttpResponse(payload, content_type="image/jpeg")
        response["Cache-Control"] = "private, max-age=300"
        return response
