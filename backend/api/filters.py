from django_filters import rest_framework as filters
from rest_framework.filters import SearchFilter
from django.contrib.auth import get_user_model
from .models import Tag, Recipe

User = get_user_model()


class RecipesFilter(filters.FilterSet):
    """Фильтрует рецепты по избранному, автору, списку покупок и тегам."""

    is_favorited = filters.BooleanFilter(method="filter_favorited")
    is_in_shopping_cart = filters.BooleanFilter(
        method="filter_in_shopping_cart"
    )
    author = filters.ModelChoiceFilter(queryset=User.objects.all())
    tags = filters.ModelMultipleChoiceFilter(
        queryset=Tag.objects.all(), to_field_name="slug"
    )

    class Meta:
        model = Recipe
        fields = ["is_favorited", "is_in_shopping_cart", "author", "tags"]

    def filter_favorited(self, queryset, name, value):
        if value:
            return queryset.filter(favorite__user=self.request.user)
        return queryset

    def filter_in_shopping_cart(self, queryset, name, value):
        if value:
            return queryset.filter(shoppingcart__user=self.request.user)
        return queryset


class IngredientSearchFilter(SearchFilter):
    """Фильтр для поиска ингредиентов по названию."""

    search_param = "name"

    def get_search_terms(self, request):
        search_terms = super().get_search_terms(request)
        return [term.lower() for term in search_terms]
