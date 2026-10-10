from django.contrib import admin

from .models import Governorate


@admin.register(Governorate)
class GovernorateAdmin(admin.ModelAdmin):
    list_display = (
        "code",
        "name_en",
        "name_fr",
        "name_ar",
        "is_active",
        "display_order",
    )
    list_filter = ("is_active",)
    search_fields = ("code", "name_en", "name_fr", "name_ar")
    ordering = ("display_order", "code")
