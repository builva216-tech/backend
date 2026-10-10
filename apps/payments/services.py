from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied

from apps.accounts.models import UserRole
from apps.core.api.exceptions import Conflict

from .models import Payment, PaymentMethod, PaymentStatus


def _invoice_number(booking) -> str:
    stamp = timezone.now().strftime("%Y%m%d")
    return f"INV-{stamp}-{str(booking.id).split('-')[0].upper()}"


def _receipt_number(payment) -> str:
    stamp = timezone.now().strftime("%Y%m%d")
    return f"RCT-{stamp}-{str(payment.id).split('-')[0].upper()}"


@transaction.atomic
def ensure_cash_payment(*, booking) -> Payment:
    payment, _ = Payment.objects.get_or_create(
        booking=booking,
        defaults={
            "method": PaymentMethod.CASH,
            "status": PaymentStatus.DUE,
            "rental_amount": booking.total_price,
            "deposit_amount": booking.security_deposit,
            "invoice_number": _invoice_number(booking),
        },
    )
    return payment


@transaction.atomic
def mark_cash_paid(
    *,
    payment_id,
    collector,
    notes: str = "",
) -> Payment:
    if (
        collector is None
        or not collector.is_authenticated
        or not collector.is_active
        or collector.role != UserRole.AGENCY
    ):
        raise PermissionDenied("Agency access required.")

    payment = (
        Payment.objects.select_for_update()
        .select_related("booking__agency__user")
        .get(pk=payment_id)
    )

    if payment.booking.agency.user_id != collector.id:
        raise PermissionDenied(
            "This payment does not belong to your agency."
        )

    if payment.status == PaymentStatus.PAID:
        return payment

    if payment.status != PaymentStatus.DUE:
        raise Conflict("This payment cannot be marked as paid.")

    payment.status = PaymentStatus.PAID
    payment.paid_at = timezone.now()
    payment.collected_by = collector
    payment.notes = notes.strip()
    payment.receipt_number = _receipt_number(payment)
    payment.save()
    return payment
