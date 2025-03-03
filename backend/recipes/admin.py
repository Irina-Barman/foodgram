from django.contrib import admin
from django.db.models import Count

from .models import (
    Tag,
    Recipe,
    Ingredient,
    RecipeIngredient,
    RecipeTag,
    Favorites,
    ShoppingCart,
)



class RecipeAdmin(admin.ModelAdmin):
    list_display = ('name', 'author',)
    list_filter = ('name', 'author__username', 'tags__name')


class TagAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "slug")
    search_fields = ("name", "slug")


class IngredientAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "measurement_unit")
    search_fields = ("name",)

class RecipeTagAdmin(admin.ModelAdmin):
    list_display = ("recipe", "tag")
    search_fields = ("tag",)

class RecipeIngredientAdmin(admin.ModelAdmin):
    list_display = ("id", "recipe", "ingredient", "amount")
    search_fields = ("recipe__name", "ingredient__name")
    raw_id_fields = ("recipe", "ingredient")


class FavoritesRecipeAdmin(admin.ModelAdmin):
    list_display = ("id", "recipe", "user")
    search_fields = ("recipe__name", "user__username")
    raw_id_fields = ("recipe", "user")


class ShoppingCartAdmin(admin.ModelAdmin):
    list_display = ("id", "recipe", "user")
    search_fields = ("recipe__name", "user__username")
    raw_id_fields = ("recipe", "user")


admin.site.register(Recipe, RecipeAdmin)
admin.site.register(Tag, TagAdmin)
admin.site.register(Ingredient, IngredientAdmin)
admin.site.register(RecipeTag, RecipeTagAdmin)
admin.site.register(RecipeIngredient, RecipeIngredientAdmin)
admin.site.register(Favorites, FavoritesRecipeAdmin)
admin.site.register(ShoppingCart, ShoppingCartAdmin)
