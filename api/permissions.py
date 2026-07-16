from rest_framework import permissions


ADMIN_ROLE_NAMES = {"admin", "administrator"}
SUPERADMIN_ROLE_NAMES = {
    "superadmin",
    "super-admin",
    "super_admin",
    "super admin",
}


def normalize_role_name(value):
    if value is None:
        return ""
    return str(value).strip().lower()


def _iter_user_group_names(user):
    if not user or not getattr(user, "is_authenticated", False):
        return []
    return [normalize_role_name(group.name) for group in user.groups.all()]


def user_has_admin_group(user):
    group_names = set(_iter_user_group_names(user))
    return bool(group_names & ADMIN_ROLE_NAMES)


def user_has_superadmin_group(user):
    group_names = set(_iter_user_group_names(user))
    return bool(group_names & SUPERADMIN_ROLE_NAMES)


def is_admin_like(user):
    if not user or not getattr(user, "is_authenticated", False):
        return False

    if bool(getattr(user, "is_superuser", False)):
        return True
    if bool(getattr(user, "is_staff", False)):
        return True
    if user_has_superadmin_group(user):
        return True
    if user_has_admin_group(user):
        return True

    return False


def is_superadmin_like(user):
    if not user or not getattr(user, "is_authenticated", False):
        return False

    if bool(getattr(user, "is_superuser", False)):
        return True
    if user_has_superadmin_group(user):
        return True

    return False


class IsAdminOrSuperAdmin(permissions.BasePermission):
    message = "You do not have permission to perform this action."

    def has_permission(self, request, view):
        return is_admin_like(getattr(request, "user", None))


class IsSuperAdminOnly(permissions.BasePermission):
    message = "Super admin permission is required."

    def has_permission(self, request, view):
        return is_superadmin_like(getattr(request, "user", None))
