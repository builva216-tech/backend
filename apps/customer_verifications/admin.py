from django.contrib import admin

from .models import CustomerVerificationSubmission


@admin.register(CustomerVerificationSubmission)
class CustomerVerificationSubmissionAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "attempt_number",
        "status",
        "reviewed_by",
        "reviewed_at",
        "submitted_at",
    )
    list_filter = (
        "status",
        "submitted_at",
    )
    search_fields = (
        "user__email",
        "user__full_name",
        "user__phone",
    )
    readonly_fields = (
        "id",
        "user",
        "attempt_number",
        "status",
        "cin_recto",
        "cin_verso",
        "selfie",
        "rejection_reason",
        "reviewed_by",
        "reviewed_at",
        "submitted_at",
        "updated_at",
    )

    def has_add_permission(self, request):
        return False
