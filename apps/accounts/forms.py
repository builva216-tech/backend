from django.contrib.auth.forms import UserChangeForm, UserCreationForm

from .models import User


class CarRentUserCreationForm(UserCreationForm):
    class Meta:
        model = User
        fields = (
            "email",
            "full_name",
            "phone",
            "role",
            "account_status",
            "is_email_verified",
            "is_staff",
            "is_active",
        )


class CarRentUserChangeForm(UserChangeForm):
    class Meta:
        model = User
        fields = (
            "email",
            "full_name",
            "phone",
            "role",
            "account_status",
            "is_email_verified",
            "is_active",
            "is_staff",
            "is_superuser",
            "groups",
            "user_permissions",
        )
