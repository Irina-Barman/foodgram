from rest_framework.permissions import SAFE_METHODS, BasePermission


class IsAdminOrReadOnly(BasePermission):
    """
    Разрешение, которое позволяет только администраторам
    выполнять любые запросы (POST, PUT, DELETE),а остальным (GET).
    """

    def has_permission(self, request, view):
        return request.method in SAFE_METHODS or (
            request.user and request.user.is_staff
        )


class IsOwnerOrReadOnly(BasePermission):
    """
    Разрешение, которое позволяет владельцам объекта выполнять любые операции
    (POST, PUT, DELETE),
    а все остальные пользователи могут только выполнять (GET).
    """

    def has_object_permission(self, request, view, obj):
        return request.method in SAFE_METHODS or obj.author == request.user
