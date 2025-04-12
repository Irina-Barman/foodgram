from django.contrib.auth import get_user_model
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
from .serializers import (
    AvatarSerializer,
    CustomUserSerializer,
    IngredientSerializer,
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
    permission_classes = [IsOwnerOrReadOnly]

    def get_serializer_class(self):
        if self.request.method in SAFE_METHODS:
            return RecipeListSerializer
        return RecipeWriteSerializer

    def perform_create(self, serializer):
        """Сохраняет рецепт с автором текущего пользователя."""
        return serializer.save(author=self.request.user)

    def create(self, request, *args, **kwargs):
        """Создает новый рецепт, проверяя авторизацию пользователя."""
        self.permission_classes = [IsAuthenticated]
        self.check_permissions(request)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        recipe = self.perform_create(serializer)
        response_serializer = RecipeListSerializer(
            recipe, context={"request": request}
        )
        return Response(
            response_serializer.data, status=status.HTTP_201_CREATED
        )

    def update(self, request, *args, **kwargs):
        """Обновляет существующий рецепт."""
        instance = self.get_object()
        serializer = self.get_serializer(
            instance, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        response_serializer = RecipeListSerializer(
            instance, context={"request": request}
        )
        return Response(response_serializer.data)

    @action(
        detail=True, methods=["post"], permission_classes=[IsAuthenticated]
    )
    def favorite(self, request, pk=None):
        """Добавляет рецепт в список избранного."""
        recipe = get_object_or_404(Recipe, pk=pk)
        Favorites.objects.get_or_create(user=request.user, recipe=recipe)
        return Response(
            {"detail": "Рецепт добавлен в избранное."},
            status=status.HTTP_201_CREATED,
        )

    @favorite.mapping.delete
    def unfavorite(self, request, pk=None):
        """Удаляет рецепт из списка избранного."""
        recipe = get_object_or_404(Recipe, pk=pk)
        favorite_item = Favorites.objects.filter(
            user=request.user, recipe=recipe
        )
        if favorite_item.exists():
            favorite_item.delete()
            return Response(
                {"detail": "Рецепт удален из избранного."},
                status=status.HTTP_204_NO_CONTENT,
            )
        return Response(
            {"detail": "Рецепт не найден в избранном."},
            status=status.HTTP_404_NOT_FOUND,
        )

    @action(
        detail=False, methods=["get"], permission_classes=[IsAuthenticated]
    )
    def download_shopping_cart(self, request):
        """Генерирует PDF для корзины покупок."""
        shopping_cart_items = (
            ShoppingCart.objects.filter(user=request.user)
            .select_related("recipe")
            .prefetch_related("recipe__recipe_ingredients__ingredient")
        )

        ingredients = {}
        for cart_item in shopping_cart_items:
            for recipe_ingredient in cart_item.recipe.recipe_ingredients.all():
                ingredient_name = recipe_ingredient.ingredient.name
                ingredient_amount = recipe_ingredient.amount
                ingredient_unit = recipe_ingredient.ingredient.measurement_unit

                if ingredient_name in ingredients:
                    ingredients[ingredient_name]["amount"] += ingredient_amount
                else:
                    ingredients[ingredient_name] = {
                        "amount": ingredient_amount,
                        "unit": ingredient_unit,
                    }
        ingredient_list = [
            {"name": name, "amount": data["amount"], "unit": data["unit"]}
            for name, data in ingredients.items()
        ]

        return generate_pdf(ingredient_list)


class BaseRecipeViewSet(APIView):
    """Базовый вьюсет для работы с рецептами в избранном и корзине."""

    permission_classes = [IsOwnerOrReadOnly, IsAuthenticated]

    def handle_post(self, request, recipe_id, model, serializer_class):
        """Обрабатывает POST запрос для добавления рецепта в модель."""
        recipe = get_object_or_404(Recipe, id=recipe_id)

        if model.objects.filter(user=request.user, recipe=recipe).exists():
            return Response(
                {"detail": "Рецепт уже в списке."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        model.objects.create(user=request.user, recipe=recipe)
        serializer = serializer_class(recipe)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def handle_delete(self, request, recipe_id, model):
        """Обрабатывает DELETE запрос для удаления рецепта из модели."""
        recipe = get_object_or_404(Recipe, id=recipe_id)

        deleted, _ = model.objects.filter(
            user=request.user, recipe=recipe
        ).delete()
        if not deleted:
            raise ValidationError("Рецепт не найден в списке.")

        return Response(status=status.HTTP_204_NO_CONTENT)


class ShoppingCartViewSet(BaseRecipeViewSet):
    """Вьюсет списка покупок."""

    serializer_class = ShoppingCartSerializer
    queryset = ShoppingCart.objects.all()

    def post(self, request, *args, **kwargs):
        """Добавляет рецепт в список покупок."""
        recipe_id = self.kwargs["id"]
        return self.handle_post(
            request, recipe_id, ShoppingCart, self.serializer_class
        )

    def delete(self, request, *args, **kwargs):
        """Удаляет рецепт из списка покупок."""
        recipe_id = self.kwargs["id"]
        return self.handle_delete(request, recipe_id, ShoppingCart)


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
