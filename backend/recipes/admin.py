from django.contrib import admin
from django.contrib.admin import register
from django.contrib.auth.models import Group

from .models import (AmountIngredient, Favorite, Ingredient, Recipe,
                     ShoppingCart, Tag)

admin.site.unregister(Group)


class IngredientRecipeInLine(admin.TabularInline):
    model = Recipe.ingredients.through
    extra = 3


@register(Tag, AmountIngredient)
class OtherAdmin(admin.ModelAdmin):
    pass


@register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    list_display = ('name', 'measurement_unit',)
    list_filter = ('name',)
    save_on_top = True


@register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    list_display = ('name', 'author',)
    list_filter = ('name', 'author__username', 'tags__name')
    save_on_top = True
    inlines = (IngredientRecipeInLine, )


@register(ShoppingCart)
class ShoppingCartAdmin(admin.ModelAdmin):
    list_display = ('user', 'recipe',)
    list_filter = ('user',)
    save_on_top = True


@register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ('user', 'recipe',)
    list_filter = ('user',)
    save_on_top = True
