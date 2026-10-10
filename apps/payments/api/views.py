from apps.agencies.subscriptions import require_booking_action
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import UserRole
from apps.bookings.models import BookingStatus

from ..models import Payment, PaymentStatus
from ..services import mark_cash_paid
from .pdf import payment_pdf_response
from .serializers import (
    MarkCashPaidSerializer,
    PaymentSerializer,
)


def _payment_queryset():
    return Payment.objects.select_related(
        "booking",
        "booking__agency",
        "booking__agency__user",
        "booking__customer",
    )


class CustomerPaymentListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.role != UserRole.CUSTOMER:
            return Response(
                {"detail": "Customer access required."},
                status=status.HTTP_403_FORBIDDEN,
            )

        queryset = _payment_queryset().filter(
            booking__customer=request.user
        )
        return Response(
            PaymentSerializer(queryset, many=True).data
        )


class AgencyPaymentListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.role != UserRole.AGENCY:
            return Response(
                {"detail": "Agency access required."},
                status=status.HTTP_403_FORBIDDEN,
            )

        queryset = _payment_queryset().filter(
            booking__agency__user=request.user
        )
        return Response(
            PaymentSerializer(queryset, many=True).data
        )


class AgencyMarkCashPaidView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, payment_id):
        booking = get_object_or_404(_payment_queryset(), pk=payment_id, booking__agency__user=request.user).booking
        require_booking_action(request.user.agency_profile, booking, 'mark-paid')
        serializer = MarkCashPaidSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        payment = mark_cash_paid(
            payment_id=payment_id,
            collector=request.user,
            notes=serializer.validated_data.get("notes", ""),
        )

        return Response(PaymentSerializer(payment).data)


class PaymentInvoiceView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, payment_id):
        payment = get_object_or_404(
            _payment_queryset(),
            pk=payment_id,
        )

        if not _can_access(request.user, payment):
            return Response(
                {"detail": "Payment access denied."},
                status=status.HTTP_403_FORBIDDEN,
            )

        return payment_pdf_response(
            payment=payment,
            document_type="invoice",
        )


class PaymentReceiptView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, payment_id):
        payment = get_object_or_404(
            _payment_queryset(),
            pk=payment_id,
        )

        if not _can_access(request.user, payment):
            return Response(
                {"detail": "Payment access denied."},
                status=status.HTTP_403_FORBIDDEN,
            )

        if payment.status != PaymentStatus.PAID:
            return Response(
                {"detail": "Receipt is available after payment."},
                status=status.HTTP_409_CONFLICT,
            )

        return payment_pdf_response(
            payment=payment,
            document_type="receipt",
        )


def _can_access(user, payment) -> bool:
    if user.role == UserRole.ADMIN and user.is_staff:
        return True

    if (
        user.role == UserRole.CUSTOMER
        and payment.booking.customer_id == user.id
    ):
        return True

    if (
        user.role == UserRole.AGENCY
        and payment.booking.agency.user_id == user.id
    ):
        return True

    return False
