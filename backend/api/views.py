from django.contrib.auth import get_user_model
from django.db.models import Sum
from django_filters.rest_framework import DjangoFilterBackend
from djoser.views import UserViewSet
from rest_framework import filters, status
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import SAFE_METHODS, AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet

from .filters import IngredientSearchFilter, RecipeFilter
from .pagination import LimitPagePagination
from .permissions import IsAdminOrReadOnly, IsOwnerOrReadOnly
from .recipe_actions import RecipeActions
from .serializers import (
    AvatarSerializer,
    CustomUserSerializer,
    FavoritesSerializer,
    IngredientSerializer,
    RecipeIngredient,
    RecipeListSerializer,
    RecipeWriteSerializer,
    ShoppingCartSerializer,
    ShortRecipeURLSerializer,
    SubscriptionSerializer,
    TagSerializer,
)
from recipes.models import (
    Favorites,
    Ingredient,
    Recipe,
    ShoppingCart,
    ShortRecipeURL,
    Tag,
)
from services.pdf_generator import generate_pdf
from users.models import Subscription

User = get_user_model()


class CustomUserViewSet(UserViewSet):
    """Вьюсет для модели пользователя."""

    pagination_class = LimitPagePagination
    queryset = User.objects.all()
    serializer_class = CustomUserSerializer
    permission_classes = [AllowAny]

    def _change_avatar(self, data):
        instance = self.get_instance()
        serializer = AvatarSerializer(instance, data=data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return serializer

    def _get_recipes_limit(self, request):
        """Обрабатывает параметр recipes_limit."""
        recipes_limit = request.query_params.get("recipes_limit", None)
        if recipes_limit is not None:
            try:
                return int(recipes_limit)
            except ValueError:
                raise ValidationError(
                    "Некорректное значение для recipes_limit"
                )
        return None

    @action(
        detail=False, methods=["get"], permission_classes=[IsAuthenticated]
    )
    def me(self, request):
        """Получает информацию о текущем пользователе."""
        user = request.user
        serializer = self.serializer_class(user, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    @me.mapping.patch
    def update_me(self, request):
        """Обновляет информацию о текущем пользователе."""
        user = request.user
        serializer = self.serializer_class(
            user,
            data=request.data,
            partial=True,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(
        methods=["put"],
        detail=False,
        permission_classes=[IsAuthenticated],
        url_path="me/avatar",
        url_name="me-avatar",
    )
    def avatar(self, request):
        """Добавляет аватар."""
        serializer = self._change_avatar(request.data)
        return Response(serializer.data)

    @avatar.mapping.delete
    def delete_avatar(self, request):
        """Удаляет аватар."""
        data = request.data
        if "avatar" not in data:
            data = {"avatar": None}
        self._change_avatar(data)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=True,
        methods=["post"],
        url_path="subscribe",
        permission_classes=[IsAuthenticated],
    )
    def subscribe(self, request, id=None):
        """Создает подписку на автора."""
        author = get_object_or_404(User, id=id)

        if request.user.id == author.id:
            return Response(
                {"detail": "Нельзя подписаться на самого себя."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if Subscription.objects.filter(
            user=request.user, author=author
        ).exists():
            return Response(
                {"detail": "Вы уже подписаны на данного автора."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        recipes_limit = self._get_recipes_limit(request)

        subscribe = Subscription.objects.create(
            user=request.user, author=author
        )
        serializer = SubscriptionSerializer(
            subscribe,
            context={"request": request, "recipes_limit": recipes_limit},
        )

        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @subscribe.mapping.delete
    def unsubscribe(self, request, id=None):
        """Удаляет подписку на автора."""
        author = get_object_or_404(User, id=id)

        deleted, _ = Subscription.objects.filter(
            user=request.user, author=author
        ).delete()

        if not deleted:
            raise ValidationError("Подписка не найдена.")

        return Response(
            {"detail": "Подписка удалена."}, status=status.HTTP_204_NO_CONTENT
        )

    @action(detail=False, permission_classes=[IsOwnerOrReadOnly])
    def subscriptions(self, request):
        """Возвращает список подписок текущего пользователя с учетом лимита."""
        queryset = self.request.user.subscriptions.all()
        recipes_limit = self._get_recipes_limit(request)

        if recipes_limit is not None:
            queryset = queryset[:recipes_limit]

        context = (
            {"recipes_limit": recipes_limit}
            if recipes_limit is not None
            else {}
        )
        page = self.paginate_queryset(queryset)

        if page is not None:
            serializer = SubscriptionSerializer(
                page, many=True, context=context
            )
            return self.get_paginated_response(serializer.data)

        serializer = SubscriptionSerializer(
            queryset, many=True, context=context
        )
        return Response(serializer.data)


class RecipeViewSet(ModelViewSet):
    """Вьюсет для модели рецепта."""

    queryset = (
        Recipe.objects.all()
        .select_related("author")
        .prefetch_related("recipe_ingredients", "recipe_tags")
    )
    pagination_class = LimitPagePagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_class = RecipeFilter

    def get_serializer_class(self):
        if self.request.method in SAFE_METHODS:
            return RecipeListSerializer
        return RecipeWriteSerializer

    def get_permissions(self):
        if self.request.method in ["PUT", "PATCH", "DELETE"]:
            return [IsOwnerOrReadOnly()]
        elif self.request.method in ["POST"]:
            return [IsAuthenticated()]
        elif self.request.method in ["GET"]:
            return [AllowAny()]
        return super().get_permissions()

    def perform_create(self, serializer):
        """Сохраняет рецепт с автором текущего пользователя."""
        recipe = serializer.save(author=self.request.user)
        return recipe

    def perform_update(self, serializer):
        """Обновляет рецепт."""
        serializer.save()

    @action(detail=True, methods=["post"])
    def favorite(self, request, pk=None):
        """Добавляет рецепт в список избранного."""
        return RecipeActions.add_to_list(
            request,
            pk,
            Favorites,
            FavoritesSerializer,
            "Этот рецепт уже в списке избранного.",
        )

    @favorite.mapping.delete
    def unfavorite(self, request, pk=None):
        """Удаляет рецепт из списка избранного."""
        return RecipeActions.remove_from_list(
            request, pk, Favorites, "Рецепт не найден в избранном."
        )

    @action(detail=True, methods=["post"])
    def shopping_cart(self, request, pk=None):
        """Добавляет рецепт в список покупок."""
        return RecipeActions.add_to_list(
            request,
            pk,
            ShoppingCart,
            ShoppingCartSerializer,
            "Рецепт уже в списке покупок.",
        )

    @shopping_cart.mapping.delete
    def remove_from_shopping_cart(self, request, pk=None):
        """Удаляет рецепт из списка покупок."""
        return RecipeActions.remove_from_list(
            request, pk, ShoppingCart, "Рецепт не найден в списке покупок."
        )

    @action(detail=False, methods=["get"])
    def download_shopping_cart(self, request):
        """Генерирует PDF для корзины покупок."""
        ingredients = (
            RecipeIngredient.objects.filter(
                recipe__shopping_cart__user=request.user
            )
            .values("ingredient__name", "ingredient__measurement_unit")
            .annotate(total_amount=Sum("amount"))
        )

        ingredient_list = [
            {
                "name": ingredient["ingredient__name"],
                "amount": ingredient["total_amount"],
                "unit": ingredient["ingredient__measurement_unit"],
            }
            for ingredient in ingredients
        ]

        return generate_pdf(ingredient_list)


class TagViewSet(ReadOnlyModelViewSet):
    """Вьюсет для модели тега."""

    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permission_classes = (IsAdminOrReadOnly,)

    def handle_exception(self, exc):
        if isinstance(exc, PermissionDenied):
            return Response(
                {"detail": "У вас недостаточно прав."},
                status=status.HTTP_405_METHOD_NOT_ALLOWED,
            )
        return super().handle_exception(exc)


class IngredientViewSet(ReadOnlyModelViewSet):
    """Вьюсет для модели ингредиента."""

    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    permission_classes = (IsAdminOrReadOnly,)
    filter_backends = [IngredientSearchFilter]
    search_fields = ["^name"]

    def handle_exception(self, exc):
        if isinstance(exc, PermissionDenied):
            return Response(
                {"detail": "У вас недостаточно прав."},
                status=status.HTTP_405_METHOD_NOT_ALLOWED,
            )
        return super().handle_exception(exc)


class ShotLinkView(APIView):
    """Вьюсет короткой ссылки на рецепт."""

    permission_classes = [AllowAny]

    @staticmethod
    def get(request, id):
        try:
            recipe = Recipe.objects.get(pk=id)
            if not hasattr(recipe, "short_url"):
                ShortRecipeURL.objects.create(recipe=recipe)
            serializer = ShortRecipeURLSerializer(
                recipe, context={"request": request}
            )
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Recipe.DoesNotExist:
            return Response(
                {"detail": "Рецепт не найден."},
                status=status.HTTP_404_NOT_FOUND,
            )
