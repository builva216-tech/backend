from django.contrib import admin

from .models import (
    AvailabilityBlock,
    Car,
    CarPhoto,
    ExtraOption,
    InsuranceOption,
)


class CarPhotoInline(admin.TabularInline):
    model = CarPhoto
    extra = 0


@admin.register(Car)
class CarAdmin(admin.ModelAdmin):
    list_display = (
        "brand",
        "model",
        "agency",
        "year",
        "status",
        "is_available",
        "daily_price",
        "governorate",
    )
    list_filter = (
        "status",
        "is_available",
        "category",
        "governorate",
    )
    search_fields = (
        "brand",
        "model",
        "agency__agency_name",
        "plate_number",
    )
    inlines = (CarPhotoInline,)


admin.site.register(AvailabilityBlock)
admin.site.register(ExtraOption)
admin.site.register(InsuranceOption)
