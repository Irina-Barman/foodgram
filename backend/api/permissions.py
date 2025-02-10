from rest_framework import permissions


class IsAdmin(permissions.BasePermission):
    """
    Разрешение для администраторов и суперпользователей.
    Полный доступ только администраторам и суперпользователям Django.
    """
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and (request.user.is_admin or request.user.is_superuser)
        )


class IsAdminOrReadOnly(permissions.BasePermission):
    """
    Разрешение для администраторов или только для чтения.
    Изменение контента доступно только администраторам.
    Чтение доступно всем.
    """
    def has_permission(self, request, view):
        return (
            request.method in permissions.SAFE_METHODS
            or (
                request.user.is_authenticated
                and request.user.is_admin
            )
        )

class IsAuthorOrAdminOrReadOnly(permissions.BasePermission):
    """
    Пользовательское разрешение для проверки прав доступа.

    Разрешает:
    - Чтение всем пользователям
    - Создание аутентифицированным пользователям
    - Изменение и удаление авторам контента и администраторам
    """
    def has_permission(self, request, view):
        return (
            request.method in permissions.SAFE_METHODS
            or request.user.is_authenticated
        )

    def has_object_permission(self, request, view, obj):
        return (
            request.method in permissions.SAFE_METHODS
            or obj.author == request.user
            or request.user.is_admin
        )
