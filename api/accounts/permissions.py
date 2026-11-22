from rest_framework.permissions import BasePermission

from .models import User


class HasRole(BasePermission):
    """Allows only logged-in, active users whose role is in allowed_roles."""

    allowed_roles = ()

    def has_permission(self, request, view):
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and user.is_active
            and user.role in self.allowed_roles
        )


class IsAdminRole(HasRole):
    allowed_roles = (User.Role.ADMIN,)


class IsFrontDesk(HasRole):
    allowed_roles = (User.Role.RECEPTIONIST, User.Role.ADMIN)


class IsProviderRole(HasRole):
    allowed_roles = (User.Role.PROVIDER,)


class IsAnyStaff(HasRole):
    allowed_roles = (User.Role.ADMIN, User.Role.RECEPTIONIST, User.Role.PROVIDER)