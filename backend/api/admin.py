from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin
from api.models import (
    Ingredient,
    Tag,
    Recipe,
    RecipeIngredient,
    ShoppingCart,
    Favorite,
)
from users.models import CustomUser, Subscription

User = get_user_model()


class CustomUserAdmin(UserAdmin):
    """Админка для кастомного пользователя."""

    model = CustomUser
    list_display = (
        "username",
        "email",
        "first_name",
        "last_name",
        "is_staff",
        "is_active",
    )
    list_filter = ("is_staff", "is_active")
    search_fields = ("username", "email", "first_name", "last_name")
    ordering = ("username",)
    fieldsets = UserAdmin.fieldsets + ((None, {"fields": ("avatar",)}),)


class IngredientAdmin(admin.ModelAdmin):
    list_display = ("name", "measurement_unit")
    empty_value_display = "-пусто-"
    list_filter = ("name",)


class TagAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")
    empty_value_display = "-пусто-"


class RecipeIngredientInline(admin.TabularInline):
    model = RecipeIngredient
    extra = 1


class RecipeAdmin(admin.ModelAdmin):
    list_display = ("name", "author", "count_favorited")
    list_filter = ("name", "author", "tags")
    empty_value_display = "-пусто-"
    inlines = (RecipeIngredientInline,)

    def count_favorited(self, obj):
        """Метод выводит общее число добавлений рецепта в избранное"""
        return obj.favorite_set.count()


class ShoppingListAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "recipe",
    )
    search_fields = ("user__username",)
    list_filter = ("user",)


class RecipeFavoritesAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "recipe",
    )
    search_fields = ("user__username",)
    list_filter = ("user",)


class SubscriptionAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "author",
    )
    search_fields = ("user__username", "author__username")
    list_filter = ("user", "author")


admin.site.register(User, CustomUserAdmin)
admin.site.register(Tag, TagAdmin)
admin.site.register(Ingredient, IngredientAdmin)
admin.site.register(Recipe, RecipeAdmin)
admin.site.register(ShoppingCart, ShoppingListAdmin)
admin.site.register(Favorite, RecipeFavoritesAdmin)
admin.site.register(Subscription, SubscriptionAdmin)
