from django.contrib.auth import get_user_model

from django_filters.rest_framework import (
    AllValuesMultipleFilter,
    BooleanFilter,
    FilterSet,
    ModelChoiceFilter,
)
from recipes.models import Recipe
from rest_framework.filters import SearchFilter

User = get_user_model()


class RecipeFilter(FilterSet):
    """"Фильтр для сортировки рецептов.""" ""

    author = ModelChoiceFilter(queryset=User.objects.all())
    tags = AllValuesMultipleFilter(field_name="tags__slug")
    is_favorited = BooleanFilter(method="filter_is_favorited")
    is_in_shopping_cart = BooleanFilter(method="filter_is_in_shopping_cart")

    class Meta:
        model = Recipe
        fields = ["author", "tags"]

    def filter_is_favorited(self, queryset, name, value):
        if value:
            return queryset.filter(in_favorites__user=self.request.user)
        return queryset

    def filter_is_in_shopping_cart(self, queryset, name, value):
        if value:
            return queryset.filter(shopping_cart__user=self.request.user)
        return queryset


class IngredientSearchFilter(SearchFilter):
    """Фильтр для поиска ингредиентов по названию"""

    search_param = "name"
