import django_filters
from django.contrib.auth import get_user_model
from django_filters.rest_framework import (
    BooleanFilter,
    FilterSet,
    ModelChoiceFilter,
)
from rest_framework.filters import SearchFilter
from recipes.models import Recipe


User = get_user_model()


class RecipeFilter(FilterSet):
    """"Фильтр для сортировки рецептов.""" ""
    queryset = Recipe.objects.prefetch_related('tags', 'ingredients').all()
    author = ModelChoiceFilter(queryset=User.objects.all())
    tags = django_filters.CharFilter(method="filter_tags")
    is_favorited = BooleanFilter(method="filter_is_favorited")
    is_in_shopping_cart = BooleanFilter(method="filter_is_in_shopping_cart")

    class Meta:
        model = Recipe
        fields = ["author", "tags"]
        
    def filter_tags(self, queryset, name, value):
        tag_slugs = self.request.GET.getlist("tags")
        return queryset.filter(tags__slug__in=tag_slugs).distinct()

    def filter_is_favorited(self, queryset, name, value):
        if self.request.user.is_authenticated:
            if value:
                return queryset.filter(in_favorites__user=self.request.user)
        return queryset

    def filter_is_in_shopping_cart(self, queryset, name, value):
        if self.request.user.is_authenticated:
            if value:
                return queryset.filter(shopping_cart__user=self.request.user)
        return queryset


class IngredientSearchFilter(SearchFilter):
    """Фильтр для поиска ингредиентов по названию"""
    search_param = "name"
