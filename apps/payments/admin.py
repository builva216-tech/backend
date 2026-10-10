from django.contrib import admin

from .models import Payment


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = (
        "invoice_number",
        "booking",
        "method",
        "status",
        "rental_amount",
        "deposit_amount",
        "paid_at",
    )
    list_filter = ("status", "method")
    search_fields = (
        "invoice_number",
        "receipt_number",
        "booking__id",
    )
