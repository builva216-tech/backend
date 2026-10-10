from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import UserRole

from ..services import (
    get_latest_customer_verification,
    submit_customer_verification,
)
from .serializers import (
    CustomerVerificationStatusSerializer,
    SubmitCustomerVerificationSerializer,
)


class IsCustomer(IsAuthenticated):
    def has_permission(self, request, view):
        return (
            super().has_permission(request, view)
            and request.user.role == UserRole.CUSTOMER
        )


class CustomerVerificationMeView(APIView):
    permission_classes = [IsCustomer]

    def get(self, request):
        submission = get_latest_customer_verification(
            user=request.user,
        )

        if submission is None:
            return Response(
                {"verification": None},
                status=status.HTTP_200_OK,
            )

        return Response(
            {
                "verification": (
                    CustomerVerificationStatusSerializer(
                        submission
                    ).data
                )
            },
            status=status.HTTP_200_OK,
        )


class CustomerVerificationSubmitView(APIView):
    permission_classes = [IsCustomer]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        serializer = SubmitCustomerVerificationSerializer(
            data=request.data
        )
        serializer.is_valid(raise_exception=True)

        submission = submit_customer_verification(
            user=request.user,
            cin_recto=serializer.validated_data["cinRecto"],
            cin_verso=serializer.validated_data["cinVerso"],
            selfie=serializer.validated_data["selfie"],
        )

        return Response(
            CustomerVerificationStatusSerializer(
                submission
            ).data,
            status=status.HTTP_201_CREATED,
        )
