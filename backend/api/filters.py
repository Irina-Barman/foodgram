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
        tag_slugs = self.request.GET.getlist(
            "tags"
        )  # Получаем список тегов из запроса
        if not tag_slugs:  # Если теги не указаны, возвращаем весь queryset
            return queryset

        # Фильтруем по выбранным тегам
        return queryset.filter(tags__slug__in=tag_slugs).distinct()

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
