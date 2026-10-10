from django.db.models import Q
from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.api.permissions import IsAdminStaff
from apps.accounts.api.serializers import (
    AuthUserSerializer,
    LogoutSerializer,
)
from apps.accounts.api.throttles import AuthIdentityThrottle, AuthIpThrottle
from apps.agencies.models import (
    AgencyProfile,
    AgencyVerificationStatus,
    AgencyVerificationSubmission,
)
from apps.agencies.services import (
    approve_agency,
    reject_agency,
)
from apps.bookings.api.serializers import BookingSerializer
from apps.bookings.models import Booking
from apps.core.api.protected_files import protected_file_response, BinaryFileView
from apps.customer_verifications.models import (
    CustomerVerificationStatus,
    CustomerVerificationSubmission,
)
from apps.fleet.api.serializers import AgencyCarReadSerializer
from apps.fleet.models import Car
from apps.payments.api.serializers import PaymentSerializer
from apps.payments.models import Payment

from .serializers import (
    AdminAgencyVerificationSerializer,
    AdminLoginSerializer,
    AdminTokenRefreshSerializer,
    RejectAgencySerializer,
)


class AdminAgencyPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "pageSize"
    max_page_size = 100


def _agency_queryset():
    return (
        AgencyProfile.objects.select_related(
            "user",
            "governorate",
            "reviewed_by",
        )
        .prefetch_related("verification_submissions")
        .order_by("-created_at")
    )


class AdminLoginView(APIView):
    throttle_classes = (
        AuthIpThrottle,
        AuthIdentityThrottle,
    )
    permission_classes = (AllowAny,)
    authentication_classes = ()

    def post(self, request):
        serializer = AdminLoginSerializer(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)

        return Response(
            serializer.validated_data,
            status=status.HTTP_200_OK,
        )


class AdminTokenRefreshView(APIView):
    def get_authenticate_header(self, request):
        return "Bearer"

    permission_classes = (AllowAny,)
    authentication_classes = ()

    def post(self, request):
        serializer = AdminTokenRefreshSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        return Response(
            serializer.validated_data,
            status=status.HTTP_200_OK,
        )


class AdminMeView(APIView):
    permission_classes = (IsAdminStaff,)

    def get(self, request):
        return Response(
            AuthUserSerializer(request.user).data,
            status=status.HTTP_200_OK,
        )


class AdminLogoutView(APIView):
    permission_classes = (IsAdminStaff,)

    def post(self, request):
        serializer = LogoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(status=status.HTTP_204_NO_CONTENT)


class AdminOverviewView(APIView):
    permission_classes = (IsAdminStaff,)

    def get(self, request):
        return Response(
            {
                "pendingAgencies": (
                    AgencyVerificationSubmission.objects.filter(
                        status="pending"
                    ).count()
                ),
                "pendingCustomers": (
                    CustomerVerificationSubmission.objects.filter(
                        status=CustomerVerificationStatus.PENDING
                    ).count()
                ),
                "activeCars": (
                    Car.objects.filter(
                        status="published",
                        is_available=True,
                        agency__verification_status="approved",
                        agency__user__account_status="active",
                        agency__user__is_active=True,
                    ).count()
                ),
                "requestedBookings": (
                    Booking.objects.filter(status="requested").count()
                ),
                "activeRentals": (Booking.objects.filter(status="active").count()),
                "paymentsDue": (Payment.objects.filter(status="due").count()),
                "paymentsPaid": (Payment.objects.filter(status="paid").count()),
            }
        )


class AdminAgencyListView(APIView):
    permission_classes = (IsAdminStaff,)

    def get(self, request):
        requested_status = request.query_params.get(
            "status",
            AgencyVerificationStatus.PENDING,
        ).strip()

        valid_statuses = {choice.value for choice in AgencyVerificationStatus}

        if requested_status not in valid_statuses:
            return Response(
                {
                    "detail": (
                        "Invalid verification status. "
                        "Use pending, approved, or rejected."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        queryset = _agency_queryset().filter(verification_status=requested_status)

        if (
            requested_status == AgencyVerificationStatus.PENDING
            and request.query_params.get("submittedOnly") == "true"
        ):
            queryset = queryset.filter(
                verification_submissions__status="pending"
            ).distinct()

        search = request.query_params.get("search", "").strip()

        if search:
            queryset = queryset.filter(
                Q(agency_name__icontains=search)
                | Q(user__full_name__icontains=search)
                | Q(user__email__icontains=search)
                | Q(user__phone__icontains=search)
                | Q(city__icontains=search)
            )

        paginator = AdminAgencyPagination()
        page = paginator.paginate_queryset(
            queryset,
            request,
            view=self,
        )

        return paginator.get_paginated_response(
            AdminAgencyVerificationSerializer(
                page,
                many=True,
            ).data
        )


class AdminAgencyDetailView(APIView):
    permission_classes = (IsAdminStaff,)

    def get(self, request, agency_profile_id):
        try:
            agency = _agency_queryset().get(pk=agency_profile_id)
        except AgencyProfile.DoesNotExist:
            return Response(
                {"detail": "Agency profile was not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response(AdminAgencyVerificationSerializer(agency).data)


class AdminAgencyApproveView(APIView):
    permission_classes = (IsAdminStaff,)

    def post(self, request, agency_profile_id):
        agency = approve_agency(
            agency_profile_id=agency_profile_id,
            reviewer=request.user,
        )
        agency = _agency_queryset().get(pk=agency.id)
        return Response(AdminAgencyVerificationSerializer(agency).data)


class AdminAgencyRejectView(APIView):
    permission_classes = (IsAdminStaff,)

    def post(self, request, agency_profile_id):
        serializer = RejectAgencySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        agency = reject_agency(
            agency_profile_id=agency_profile_id,
            reviewer=request.user,
            rejection_reason=serializer.validated_data["reason"],
        )
        agency = _agency_queryset().get(pk=agency.id)

        return Response(AdminAgencyVerificationSerializer(agency).data)


class AdminAgencyDocumentView(BinaryFileView):
    permission_classes = (IsAdminStaff,)

    _field_by_type = {
        "business-registration": "business_registration",
        "tax-identification": "tax_identification",
        "responsible-person-cin-recto": ("responsible_person_cin_recto"),
        "responsible-person-cin-verso": ("responsible_person_cin_verso"),
        "address-proof": "address_proof",
    }

    def get(
        self,
        request,
        agency_profile_id,
        document_type,
    ):
        field_name = self._field_by_type.get(document_type)

        if field_name is None:
            return Response(
                {"detail": "Verification document was not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        agency = AgencyProfile.objects.filter(pk=agency_profile_id).first()

        if agency is None:
            return Response(
                {"detail": "Agency profile was not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        submission = agency.verification_submissions.order_by("-attempt_number").first()

        if submission is None:
            return Response(
                {"detail": "Agency documents were not submitted."},
                status=status.HTTP_404_NOT_FOUND,
            )

        return protected_file_response(getattr(submission, field_name))


class AdminCarListView(APIView):
    permission_classes = (IsAdminStaff,)

    def get(self, request):
        queryset = (
            Car.objects.select_related("agency", "agency__user", "governorate")
            .prefetch_related("photos")
            .order_by("-created_at")[:200]
        )
        return Response(AgencyCarReadSerializer(queryset, many=True).data)


class AdminBookingListView(APIView):
    permission_classes = (IsAdminStaff,)

    def get(self, request):
        queryset = (
            Booking.objects.select_related(
                "car",
                "agency",
                "agency__user",
                "customer",
                "pickup_governorate",
                "payment",
            )
            .prefetch_related("extras")
            .order_by("-created_at")[:200]
        )
        return Response(BookingSerializer(queryset, many=True).data)


class AdminPaymentListView(APIView):
    permission_classes = (IsAdminStaff,)

    def get(self, request):
        queryset = Payment.objects.select_related(
            "booking",
            "booking__agency",
            "booking__customer",
        ).order_by("-created_at")[:200]
        return Response(PaymentSerializer(queryset, many=True).data)
