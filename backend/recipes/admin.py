from django.contrib import admin
from django.utils.safestring import mark_safe

from .models import (Favorites, Ingredient, Recipe, RecipeIngredient,
                     RecipeTag, ShoppingCart, Tag)


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "cooking_time_display",
        "author",
        "tags_display",
        "ingredients_display",
        "image_display",
        "favorites_count",
    )
    list_filter = ("name", "author__username", "tags__name")

    @mark_safe
    def cooking_time_display(self, obj):
        return f"{obj.cooking_time} мин"

    @mark_safe
    def tags_display(self, obj):
        return ", ".join([tag.name for tag in obj.tags.all()])

    @mark_safe
    def ingredients_display(self, obj):
        return ", ".join(
            [
                f"{ingredient.amount} {ingredient.ingredient.measurement_unit}"
                f" {ingredient.ingredient.name}"
                for ingredient in obj.recipeingredient_set.all()
            ]
        )

    @mark_safe
    def image_display(self, obj):
        if obj.image:
            return (
                f'<img src="{obj.image.url}" '
                'style="width: 50px; height: 50px; border-radius: 5%;" />'
            )
        return "Нет изображения"

    def favorites_count(self, obj):
        return obj.favorites.count()

    favorites_count.short_description = "В Избранном"


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "slug")
    search_fields = ("name", "slug")


@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "measurement_unit")
    search_fields = ("name",)


@admin.register(RecipeTag)
class RecipeTagAdmin(admin.ModelAdmin):
    list_display = ("recipe", "tag")
    search_fields = ("tag",)


@admin.register(RecipeIngredient)
class RecipeIngredientAdmin(admin.ModelAdmin):
    list_display = ("id", "recipe", "ingredient", "amount")
    search_fields = ("recipe__name", "ingredient__name")
    raw_id_fields = ("recipe", "ingredient")


@admin.register(Favorites)
class FavoritesRecipeAdmin(admin.ModelAdmin):
    list_display = ("id", "recipe", "user")
    search_fields = ("recipe__name", "user__username")
    raw_id_fields = ("recipe", "user")


@admin.register(ShoppingCart)
class ShoppingCartAdmin(admin.ModelAdmin):
    list_display = ("id", "recipe", "user")
    search_fields = ("recipe__name", "user__username")
    raw_id_fields = ("recipe", "user")
