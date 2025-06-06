from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import Group
from django.utils.safestring import mark_safe
from rest_framework.authtoken.models import TokenProxy

from .models import CustomUser, Subscription

admin.site.unregister(Group)
admin.site.unregister(TokenProxy)


@admin.register(CustomUser)
class UserAdmin(BaseUserAdmin):
    """Класс для представления модели пользователя в админ-зоне."""

    list_display = (
        "username",
        "email",
        "first_name",
        "last_name",
        "id",
        "avatar_display",
        "password",
    )
    list_filter = (
        "username",
        "email",
    )

    def avatar_display(self, obj):
        """Метод для отображения аватара пользователя."""
        if obj.avatar:
            return mark_safe(
                f'<img src="{obj.avatar.url}" '
                f'style="width: 50px; height: 50px; border-radius: 50%;" />'
            )
        return ""

    avatar_display.short_description = "Аватар"


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    """Класс для представления модели подписок в админ-зоне."""

    list_display = ("user", "author", "id")
    search_fields = ("user__username", "author__username")
    list_filter = ("id",)
