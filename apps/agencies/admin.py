from django.contrib import admin, messages

from apps.core.api.exceptions import Conflict

from .models import AgencyProfile, SubscriptionPlan


@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'monthly_tnd', 'cars', 'branches', 'is_active')
    readonly_fields = ('code', 'revision', 'updated_at')

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def save_model(self, request, obj, form, change):
        obj.revision += 1
        super().save_model(request, obj, form, change)
from .services import approve_agency, reject_agency


@admin.register(AgencyProfile)
class AgencyProfileAdmin(admin.ModelAdmin):
    list_display = (
        "agency_name",
        "user",
        "governorate",
        "city",
        "verification_status",
        "reviewed_by",
        "reviewed_at",
        "created_at",
    )
    list_filter = ("verification_status", "governorate")
    search_fields = (
        "agency_name",
        "user__email",
        "user__full_name",
        "user__phone",
    )
    readonly_fields = (
        "created_at",
        "updated_at",
        "reviewed_by",
        "reviewed_at",
        "rejection_reason",
    )
    actions = ("approve_agencies", "reject_agencies")

    @admin.action(description="Approve selected pending agencies")
    def approve_agencies(self, request, queryset):
        approved_count = 0

        for agency in queryset:
            try:
                approve_agency(
                    agency_profile_id=agency.id,
                    reviewer=request.user,
                )
                approved_count += 1
            except Conflict:
                continue

        self.message_user(
            request,
            f"Approved {approved_count} pending agency account(s).",
            level=messages.SUCCESS,
        )

    @admin.action(description="Reject selected pending agencies")
    def reject_agencies(self, request, queryset):
        rejected_count = 0

        for agency in queryset:
            try:
                reject_agency(
                    agency_profile_id=agency.id,
                    reviewer=request.user,
                    rejection_reason="Rejected from Django Admin.",
                )
                rejected_count += 1
            except Conflict:
                continue

        self.message_user(
            request,
            f"Rejected {rejected_count} pending agency account(s).",
            level=messages.WARNING,
        )

from .models import AgencySubscription, AgencyBranch

@admin.register(AgencySubscription)
class AgencySubscriptionAdmin(admin.ModelAdmin):
    list_display = ('agency', 'plan', 'paid_until', 'suspended')
    readonly_fields = ('updated_at',)
    list_filter = ('plan', 'suspended')

@admin.register(AgencyBranch)
class AgencyBranchAdmin(admin.ModelAdmin):
    list_display = ('agency', 'name', 'city', 'is_active')


from .models import AgencySubscriptionRequest

@admin.register(AgencySubscriptionRequest)
class AgencySubscriptionRequestAdmin(admin.ModelAdmin):
    list_display = ('agency', 'plan', 'status', 'created_at')
    list_filter = ('status', 'plan')
    readonly_fields = ('agency', 'plan', 'created_at')
