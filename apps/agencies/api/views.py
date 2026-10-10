from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.exceptions import NotFound
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.api.permissions import IsAgency
from apps.accounts.models import AccountStatus
from apps.agencies.models import (
    AgencyProfile,
    AgencyVerificationStatus,
)
from apps.agencies.services import (
    get_latest_agency_verification,
    submit_agency_verification,
)
from apps.core.api.protected_files import protected_file_response, BinaryFileView

from .serializers import (
    AgencyProfileWriteSerializer,
    AgencyVerificationStatusSerializer,
    CurrentAgencyProfileSerializer,
    PublicAgencyProfileSerializer,
    SubmitAgencyVerificationSerializer,
)


class CurrentAgencyProfileView(APIView):
    parser_classes = (
        JSONParser,
        FormParser,
        MultiPartParser,
    )
    permission_classes = (
        IsAuthenticated,
        IsAgency,
    )

    def get(self, request):
        profile = AgencyProfile.objects.select_related("user", "governorate").get(
            user=request.user
        )
        return Response(CurrentAgencyProfileSerializer(profile).data)

    def patch(self, request):
        from apps.fleet.services import require_approved_agency

        approved = require_approved_agency(request.user)
        from apps.agencies.subscriptions import require_management
        require_management(approved)
        serializer = AgencyProfileWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        values = serializer.validated_data
        if "agencyId" in values and values["agencyId"] != request.user.id:
            raise NotFound("Agency workspace not found.")
        with transaction.atomic():
            profile = (
                AgencyProfile.objects.select_for_update()
                .select_related("user", "governorate")
                .get(pk=approved.pk)
            )
            if (
                "expectedUpdatedAt" in values
                and values["expectedUpdatedAt"] != profile.updated_at
            ):
                return Response(
                    {
                        "detail": "Profile changed elsewhere. Reload before saving again."
                    },
                    status=409,
                )
            mapping = {
                "agencyName": "agency_name",
                "governorateCode": "governorate_id",
                "city": "city",
                "bio": "bio",
                "services": "services",
            }
            for incoming, field in mapping.items():
                if incoming in values:
                    setattr(profile, field, values[incoming])
            # Keep previous storage objects until normal retention cleanup. Never
            # remove an image before a successful database commit.
            if values.get("removeProfileImage"):
                profile.profile_image = None
            if "profileImage" in values:
                profile.profile_image = values["profileImage"]
            profile.save()
            if "governorateCode" in values:
                profile.refresh_from_db()
        return Response(CurrentAgencyProfileSerializer(profile).data)


class PublicAgencyProfileView(APIView):
    permission_classes = (AllowAny,)
    authentication_classes = ()

    def get(self, request, agency_id):
        profile = get_object_or_404(
            AgencyProfile.objects.select_related(
                "user",
                "governorate",
            ),
            user_id=agency_id,
            verification_status=AgencyVerificationStatus.APPROVED,
            user__account_status=AccountStatus.ACTIVE,
            user__is_active=True,
        )

        return Response(PublicAgencyProfileSerializer(profile).data)


class PublicAgencyProfileImageView(BinaryFileView):
    permission_classes = (AllowAny,)
    authentication_classes = ()

    def get(self, request, agency_id):
        profile = get_object_or_404(
            AgencyProfile,
            user_id=agency_id,
            verification_status=AgencyVerificationStatus.APPROVED,
            user__account_status=AccountStatus.ACTIVE,
            user__is_active=True,
        )

        if not profile.profile_image:
            return Response(
                {"detail": "Agency profile image was not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        response = protected_file_response(profile.profile_image)
        response["Cache-Control"] = "public, max-age=0, must-revalidate"
        return response


class AgencyVerificationMeView(APIView):
    permission_classes = (
        IsAuthenticated,
        IsAgency,
    )

    def get(self, request):
        submission = get_latest_agency_verification(
            user=request.user,
        )

        if submission is None:
            return Response(
                {
                    "verification": None,
                    "profileStatus": (request.user.agency_profile.verification_status),
                }
            )

        return Response(
            {
                "verification": (AgencyVerificationStatusSerializer(submission).data),
                "profileStatus": (request.user.agency_profile.verification_status),
            }
        )


class AgencyVerificationSubmitView(APIView):
    permission_classes = (
        IsAuthenticated,
        IsAgency,
    )
    parser_classes = (
        MultiPartParser,
        FormParser,
    )

    def post(self, request):
        serializer = SubmitAgencyVerificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        submission = submit_agency_verification(
            user=request.user,
            business_registration=(serializer.validated_data["businessRegistration"]),
            tax_identification=(serializer.validated_data["taxIdentification"]),
            responsible_person_cin_recto=(
                serializer.validated_data["responsiblePersonCinRecto"]
            ),
            responsible_person_cin_verso=(
                serializer.validated_data["responsiblePersonCinVerso"]
            ),
            address_proof=(serializer.validated_data["addressProof"]),
        )

        return Response(
            AgencyVerificationStatusSerializer(submission).data,
            status=status.HTTP_201_CREATED,
        )
