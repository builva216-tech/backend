from rest_framework.permissions import BasePermission

from apps.accounts.models import UserRole


class IsCustomer(BasePermission):
    message = "Customer access required."

    def has_permission(self, request, view):
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and user.is_active
            and user.role == UserRole.CUSTOMER
        )


class IsAgency(BasePermission):
    message = "Agency access required."

    def has_permission(self, request, view):
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and user.is_active
            and user.role == UserRole.AGENCY
        )


class IsAdminStaff(BasePermission):
    message = "Admin access required."

    def has_permission(self, request, view):
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and user.is_active
            and user.role == UserRole.ADMIN
            and user.is_staff
        )
