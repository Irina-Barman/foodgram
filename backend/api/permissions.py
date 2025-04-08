from rest_framework.permissions import SAFE_METHODS, BasePermission


class IsAdminOrReadOnly(BasePermission):
    """Разрешение для администраторов или только или только чтение."""
    def has_permission(self, request, view):
        return (
            request.method in SAFE_METHODS
            or request.user
            and request.user.is_staff
        )


class IsOwnerOrReadOnly(BasePermission):
    """Разрешение для автора или только чтение."""

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False  # Неавторизованный пользователь получает 401
        return request.method in SAFE_METHODS or request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        return request.method in SAFE_METHODS or obj.author == request.user
