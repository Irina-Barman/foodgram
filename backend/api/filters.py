import django_filters
from django.contrib.auth import get_user_model
from django_filters.rest_framework import (
    BooleanFilter,
    FilterSet,
    ModelChoiceFilter,
)
from recipes.models import Recipe
from rest_framework.filters import SearchFilter

User = get_user_model()


class RecipeFilter(FilterSet):
    """Фильтр для сортировки рецептов."""
    author = ModelChoiceFilter(queryset=User.objects.all())
    tags = django_filters.CharFilter(method="filter_tags")
    is_favorited = BooleanFilter(method="filter_is_favorited")
    is_in_shopping_cart = BooleanFilter(method="filter_is_in_shopping_cart")

    class Meta:
        model = Recipe
        fields = ["author", "tags", "is_favorited", "is_in_shopping_cart"]

    def filter_tags(self, queryset, name, value):
        """Фильтрация по тегам."""
        if not value:  # Если теги не указаны, возвращаем все рецепты
            return queryset

        # Разделяем теги по запятой, если они передаются в виде строки
        tags = value.split(',') if ',' in value else [value]
        return queryset.filter(tags__slug__in=tags).distinct()

    def filter_is_favorited(self, queryset, name, value):
        """Фильтрация по избранным рецептам."""
        request = self.request
        if request and request.user.is_authenticated and value:
            return queryset.filter(in_favorites__user=request.user)
        return queryset

    def filter_is_in_shopping_cart(self, queryset, name, value):
        """Фильтрация по списку покупок."""
        request = self.request
        if request and request.user.is_authenticated and value:
            return queryset.filter(shopping_cart__user=request.user)
        return queryset


class IngredientSearchFilter(SearchFilter):
    """Фильтр для поиска ингредиентов по названию."""
    search_param = "name"
