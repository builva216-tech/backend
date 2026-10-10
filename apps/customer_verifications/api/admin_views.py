from django.db.models import Q
from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.api.permissions import IsAdminStaff
from apps.core.api.protected_files import protected_file_response, BinaryFileView

from ..models import (
    CustomerVerificationStatus,
    CustomerVerificationSubmission,
)
from ..services import (
    approve_customer_verification,
    reject_customer_verification,
)
from .serializers import (
    AdminCustomerVerificationSerializer,
    RejectCustomerVerificationSerializer,
)


class AdminCustomerVerificationPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "pageSize"
    max_page_size = 100


def _get_submission_or_none(submission_id):
    try:
        return (
            CustomerVerificationSubmission.objects
            .select_related(
                "user",
                "reviewed_by",
            )
            .get(pk=submission_id)
        )
    except (
        CustomerVerificationSubmission.DoesNotExist,
        ValueError,
    ):
        return None


class AdminCustomerVerificationListView(APIView):
    permission_classes = [IsAdminStaff]

    def get(self, request):
        requested_status = request.query_params.get(
            "status",
            CustomerVerificationStatus.PENDING,
        ).strip()

        valid_statuses = {
            choice.value
            for choice in CustomerVerificationStatus
            if choice != CustomerVerificationStatus.SUPERSEDED
        }

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

        queryset = (
            CustomerVerificationSubmission.objects
            .select_related(
                "user",
                "reviewed_by",
            )
            .filter(status=requested_status)
            .order_by("-submitted_at")
        )

        search = request.query_params.get("search", "").strip()

        if search:
            queryset = queryset.filter(
                Q(user__full_name__icontains=search)
                | Q(user__email__icontains=search)
                | Q(user__phone__icontains=search)
            )

        paginator = AdminCustomerVerificationPagination()
        page = paginator.paginate_queryset(
            queryset,
            request,
            view=self,
        )

        serializer = AdminCustomerVerificationSerializer(
            page,
            many=True,
        )

        return paginator.get_paginated_response(serializer.data)


class AdminCustomerVerificationDetailView(APIView):
    permission_classes = [IsAdminStaff]

    def get(self, request, submission_id):
        submission = _get_submission_or_none(submission_id)

        if submission is None:
            return Response(
                {
                    "detail": (
                        "Customer verification request was not found."
                    )
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response(
            AdminCustomerVerificationSerializer(submission).data,
            status=status.HTTP_200_OK,
        )


class AdminCustomerVerificationApproveView(APIView):
    permission_classes = [IsAdminStaff]

    def post(self, request, submission_id):
        submission = approve_customer_verification(
            submission_id=submission_id,
            reviewer=request.user,
        )

        submission = _get_submission_or_none(submission.id)

        return Response(
            AdminCustomerVerificationSerializer(submission).data,
            status=status.HTTP_200_OK,
        )


class AdminCustomerVerificationRejectView(APIView):
    permission_classes = [IsAdminStaff]

    def post(self, request, submission_id):
        serializer = RejectCustomerVerificationSerializer(
            data=request.data
        )
        serializer.is_valid(raise_exception=True)

        submission = reject_customer_verification(
            submission_id=submission_id,
            reviewer=request.user,
            rejection_reason=serializer.validated_data["reason"],
        )

        submission = _get_submission_or_none(submission.id)

        return Response(
            AdminCustomerVerificationSerializer(submission).data,
            status=status.HTTP_200_OK,
        )


class AdminCustomerVerificationDocumentView(BinaryFileView):
    permission_classes = [IsAdminStaff]

    _field_by_document_type = {
        "cin-recto": "cin_recto",
        "cin-verso": "cin_verso",
        "selfie": "selfie",
    }

    def get(
        self,
        request,
        submission_id,
        document_type,
    ):
        field_name = self._field_by_document_type.get(
            document_type
        )

        if field_name is None:
            return Response(
                {"detail": "Verification document was not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        submission = _get_submission_or_none(submission_id)

        if submission is None:
            return Response(
                {
                    "detail": (
                        "Customer verification request was not found."
                    )
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        document = getattr(submission, field_name)

        if not document or not document.name:
            return Response(
                {"detail": "Verification document was not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        return protected_file_response(document)
