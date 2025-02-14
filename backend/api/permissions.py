from rest_framework.permissions import SAFE_METHODS, BasePermission


class AdminOrReadOnly(BasePermission):
    """Пермишен с правами доступа для администраторов."""
    def has_permission(self, request, view):
        return (request.method in SAFE_METHODS
                or request.user and request.user.is_superuser)


class AuthorOrReadOnly(BasePermission):
    """Пермишен с правами доступа для авторов."""
    def has_object_permission(self, request, view, obj):
        return (request.method in SAFE_METHODS
                or request.user == obj.author)


class AdminOrAuthor(BasePermission):
    """Пермишен с правами доступа для администраторов и авторов."""
    def has_object_permission(self, request, view, obj):
        return (request.method in SAFE_METHODS
                or request.user == obj.author or request.user.is_superuser)
