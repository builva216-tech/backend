from rest_framework import serializers

from ..models import Payment


class PaymentSerializer(serializers.ModelSerializer):
    bookingId = serializers.UUIDField(source="booking_id")
    rentalAmount = serializers.SerializerMethodField()
    depositAmount = serializers.SerializerMethodField()
    invoiceNumber = serializers.CharField(source="invoice_number")
    receiptNumber = serializers.CharField(
        source="receipt_number",
        allow_null=True,
    )
    paidAt = serializers.DateTimeField(
        source="paid_at",
        allow_null=True,
    )
    createdAt = serializers.DateTimeField(source="created_at")

    class Meta:
        model = Payment
        fields = (
            "id",
            "bookingId",
            "method",
            "status",
            "rentalAmount",
            "depositAmount",
            "invoiceNumber",
            "receiptNumber",
            "paidAt",
            "createdAt",
        )

    def get_rentalAmount(self, obj):
        return float(obj.rental_amount)

    def get_depositAmount(self, obj):
        return float(obj.deposit_amount)


class MarkCashPaidSerializer(serializers.Serializer):
    notes = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=1000,
        default="",
    )
