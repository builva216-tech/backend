from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .forms import CarRentUserChangeForm, CarRentUserCreationForm
from .models import ContactVerificationChallenge, User


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    add_form = CarRentUserCreationForm
    form = CarRentUserChangeForm
    model = User

    ordering = ("-date_joined",)
    list_display = (
        "email",
        "full_name",
        "phone",
        "role",
        "account_status",
        "is_email_verified",
        "is_staff",
        "is_active",
    )
    list_filter = (
        "role",
        "account_status",
        "is_email_verified",
        "is_staff",
        "is_active",
    )
    search_fields = ("email", "full_name", "phone")
    readonly_fields = ("date_joined", "updated_at", "last_login")

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        (
            "Profile",
            {
                "fields": (
                    "full_name",
                    "phone",
                    "role",
                    "account_status",
                    "is_email_verified",
                )
            },
        ),
        (
            "Permissions",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        (
            "Dates",
            {
                "fields": (
                    "last_login",
                    "date_joined",
                    "updated_at",
                )
            },
        ),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "email",
                    "full_name",
                    "phone",
                    "role",
                    "account_status",
                    "is_email_verified",
                    "password1",
                    "password2",
                    "is_staff",
                    "is_active",
                ),
            },
        ),
    )


@admin.register(ContactVerificationChallenge)
class ContactVerificationChallengeAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "contact_type",
        "pending_value",
        "status",
        "attempts_remaining",
        "created_at",
        "expires_at",
    )
    list_filter = ("contact_type", "status")
    search_fields = (
        "user__email",
        "user__phone",
        "pending_value",
    )
    readonly_fields = (
        "id",
        "user",
        "contact_type",
        "pending_value",
        "otp_hash",
        "status",
        "attempts_remaining",
        "created_at",
        "expires_at",
        "resend_available_at",
        "verified_at",
    )

    def has_add_permission(self, request):
        return False
