from urllib import request

from django_filters.rest_framework import (AllValuesMultipleFilter,
                                           BooleanFilter, FilterSet)
from recipes.models import Recipe
from rest_framework.filters import SearchFilter


class RecipesFilter(FilterSet):
    """"Фильтр для сортировки рецептов."""""
    tags = AllValuesMultipleFilter(field_name='tags__slug',
                                   label='tags')
    favorite = BooleanFilter(method='get_favorite')
    shopping_cart = BooleanFilter(method='get_shopping_cart')

    class Meta:
        model = Recipe
        fields = ('author', 'tags', 'favorite',
                  'shopping_cart')

    def get_favorite(self, queryset, name, value):
        if value:
            return queryset.filter(favorite__user=self.request.user)
        return queryset.exclude(favorite__user=self.request.user)

    def get_shopping_cart(self, queryset, name, value):
        if value:
            return Recipe.objects.filter(shopping_cart__user=self.request.user)


class IngredientSearchFilter(SearchFilter):
    search_param = 'name'
