from django.contrib import admin

from .models import (
    Booking,
    BookingExtra,
    BookingInsurance,
    BookingStatusEvent,
)


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "car",
        "agency",
        "customer",
        "pickup_at",
        "return_at",
        "status",
        "total_price",
    )
    list_filter = ("status", "pickup_governorate")
    search_fields = (
        "id",
        "customer__email",
        "agency__agency_name",
        "car__brand",
        "car__model",
    )


admin.site.register(BookingExtra)
admin.site.register(BookingInsurance)
admin.site.register(BookingStatusEvent)
