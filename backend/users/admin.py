from django.contrib import admin

from .models import CustomUser


class UserAdmin(admin.ModelAdmin):
    """Класс для представления модели пользователя в админ-зоне."""

    list_display = (
        "username",
        "email",
        "first_name",
        "last_name",
        "id",
    )
    list_filter = (
        "username",
        "email",
    )


admin.site.register(CustomUser, UserAdmin)
