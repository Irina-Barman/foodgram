from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import (
    IsAuthenticated,
    IsAuthenticatedOrReadOnly,
)
from rest_framework.decorators import action

from django_filters.rest_framework import DjangoFilterBackend
from django.shortcuts import get_object_or_404
from django.http import HttpResponse
from django.db.models import Sum

from api.serializers import (
    IngredientSerializer,
    TagSerializer,
    RecipeReadSerializer,
    ShoppingCartSerializer,
    FavoriteSerializer,
    RecipeCreateUpdateSerializer,
    ShortRecipeSerializer,
)
from .models import (
    Ingredient,
    Tag,
    Recipe,
    ShoppingCart,
    Favorite,
    RecipeIngredient,
)
from .pagination import CustomPagination
from .filters import RecipesFilter


class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    """Получение конкретного ингредиента, списка ингредиентов."""

    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer


class TagViewSet(viewsets.ReadOnlyModelViewSet):
    """Получение конкретного тега, списка тегов."""

    queryset = Tag.objects.all()
    serializer_class = TagSerializer


class RecipeViewSet(viewsets.ModelViewSet):
    """Вьюсет для рецептов."""

    queryset = Recipe.objects.all()
    permission_classes = (IsAuthenticatedOrReadOnly,)
    pagination_class = CustomPagination
    filter_backends = (DjangoFilterBackend,)
    filterset_class = RecipesFilter

    def get_serializer_class(self):
        if self.action in ["list", "retrieve"]:
            return RecipeReadSerializer
        return RecipeCreateUpdateSerializer

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    def perform_update(self, serializer):
        serializer.save(author=self.request.user)

    @action(
        detail=True,
        methods=["post", "delete"],
        permission_classes=[IsAuthenticated],
    )
    def favorite(self, request, pk):
        """Добавить или удалить рецепт из избранного."""
        recipe = get_object_or_404(Recipe, pk=pk)
        if request.method == "POST":
            favorite, created = Favorite.objects.get_or_create(
                user=request.user, recipe=recipe
            )
            if created:
                serializer = ShortRecipeSerializer(recipe)
                return Response(
                    data=serializer.data, status=status.HTTP_201_CREATED
                )
            return Response(
                {"error": "Рецепт уже в избранном"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        favorite = get_object_or_404(
            Favorite, user=request.user, recipe=recipe
        )
        favorite.delete()
        return Response(
            {"message": "Рецепт успешно удален из избранного"},
            status=status.HTTP_204_NO_CONTENT,
        )

    @action(
        detail=True,
        methods=["post", "delete"],
        permission_classes=[IsAuthenticated],
    )
    def shopping_cart(self, request, pk):
        """Добавить или удалить рецепт из списка покупок."""
        recipe = get_object_or_404(Recipe, pk=pk)
        if request.method == "POST":
            shopping_cart_item, created = ShoppingCart.objects.get_or_create(
                user=request.user, recipe=recipe
            )
            if created:
                serializer = ShortRecipeSerializer(recipe)
                return Response(
                    data=serializer.data, status=status.HTTP_201_CREATED
                )
            return Response(
                {"error": "Рецепт уже в корзине покупок"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        shopping_cart_item = get_object_or_404(
            ShoppingCart, user=request.user, recipe=recipe
        )
        shopping_cart_item.delete()
        return Response(
            {"message": "Рецепт успешно удален из списка покупок"},
            status=status.HTTP_204_NO_CONTENT,
        )

    @action(detail=False, methods=["get"])
    def download_shopping_cart(self, request):
        """Скачать список покупок."""
        user = request.user
        ingredients = (
            RecipeIngredient.objects.filter(recipe__shoppingcart__user=user)
            .values("ingredient__name", "ingredient__measurement_unit")
            .annotate(amount=Sum("amount"))
        )

        if not ingredients:
            return Response(
                {"message": "Список покупок пуст"},
                status=status.HTTP_204_NO_CONTENT,
            )

        shopping_cart = "Список покупок:\n"
        for item in ingredients:
            shopping_cart += f"{item['ingredient__name'].capitalize()} {item['amount']} {item['ingredient__measurement_unit']}\n"

        response = HttpResponse(shopping_cart, content_type="text/plain")
        response["Content-Disposition"] = (
            'attachment; filename="shopping_cart.txt"'
        )
        return response


class ShoppingCartViewSet(viewsets.ModelViewSet):
    """Вьюсет для корзины покупок."""

    queryset = ShoppingCart.objects.all()
    serializer_class = ShoppingCartSerializer
    permission_classes = [IsAuthenticated]

    def list(self, request):
        """Получить список рецептов в корзине."""
        user = request.user
        queryset = Recipe.objects.filter(shoppingcart__user=user)
        serializer = ShortRecipeSerializer(queryset, many=True)
        return Response(serializer.data)

    def create(self, request):
        """Добавить рецепт в корзину."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(user=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def destroy(self, request, pk):
        """Удалить рецепт из корзины."""
        shopping_cart_item = get_object_or_404(
            ShoppingCart, pk=pk, user=request.user
        )
        shopping_cart_item.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class FavoriteViewSet(viewsets.ModelViewSet):
    """Вьюсет для избранных рецептов."""

    queryset = Favorite.objects.all()
    serializer_class = FavoriteSerializer
    permission_classes = [IsAuthenticated]

    def list(self, request):
        """Получить список избранных рецептов."""
        user = request.user
        queryset = Recipe.objects.filter(favorite__user=user)
        serializer = ShortRecipeSerializer(queryset, many=True)
        return Response(serializer.data)

    def create(self, request):
        """Добавить рецепт в избранное."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(user=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def destroy(self, request, pk):
        """Удалить рецепт из избранного."""
        favorite_item = get_object_or_404(Favorite, pk=pk, user=request.user)
        favorite_item.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
