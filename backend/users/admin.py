from django.contrib import admin

from .models import CustomUser, Subscription


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


class SubscriptionAdmin(admin.ModelAdmin):
    """Класс для представления модели подписок в админ-зоне."""

    list_display = ("user", "author", "id")
    search_fields = ("user__username", "author__username")
    list_filter = ("id",)


admin.site.register(CustomUser, UserAdmin)
admin.site.register(Subscription, SubscriptionAdmin)
