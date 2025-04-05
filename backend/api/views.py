from django.contrib.auth import get_user_model
from django.http import JsonResponse
from django_filters.rest_framework import DjangoFilterBackend
from djoser.views import UserViewSet
from recipes.models import Favorites, Ingredient, Recipe, ShoppingCart, Tag
from rest_framework import filters, status
from rest_framework.decorators import action
from rest_framework.exceptions import AuthenticationFailed, ValidationError
from rest_framework.generics import (RetrieveUpdateDestroyAPIView,
                                     get_object_or_404)
from rest_framework.permissions import SAFE_METHODS, AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet
from services.pdf_generator import generate_pdf
from users.models import Subscription

from .filters import IngredientSearchFilter, RecipeFilter
from .pagination import LimitPagePagination
from .permissions import IsOwnerOrReadOnly
from .serializers import (AvatarSerializer, CustomUserSerializer,
                          FavoritesSerializer, IngredientSerializer,
                          RecipeListSerializer, RecipeWriteSerializer,
                          ShoppingCartSerializer, SubscriptionSerializer,
                          TagSerializer)

User = get_user_model()


class ShortLinkView(APIView):
    """Вьюсет для генерации короткой ссылки на рецепт."""

    def get(self, request, id):
        recipe = get_object_or_404(Recipe, id=id)
        base_url = request.build_absolute_uri("/")  # Получаем базовый URL
        short_link = (
            f"{base_url}/{recipe.id}/"  # Создание полной ссылки
        )
        return Response({"short-link": short_link}, status=status.HTTP_200_OK)


class CustomUserViewSet(UserViewSet):
    """Вьюсет для модели пользователя."""

    pagination_class = LimitPagePagination
    queryset = User.objects.all()
    serializer_class = CustomUserSerializer
    permission_classes = [AllowAny]

    @action(
        detail=False,
        methods=["get", "patch"],
        permission_classes=[IsAuthenticated],
    )
    def me(self, request):
        """Получает и обновляет информацию о текущем пользователе."""
        if request.method == "PATCH":
            serializer = self.serializer_class(
                request.user,
                data=request.data,
                partial=True,
                context={"request": request},
            )
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)

        serializer = self.serializer_class(
            request.user, context={"request": request}
        )
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=False, permission_classes=[IsOwnerOrReadOnly])
    def subscriptions(self, request):
        """Возвращает список подписок текущего пользователя."""
        queryset = self.request.user.subscriptions.all()
        recipes_limit = request.query_params.get("recipes_limit", None)

        if recipes_limit is not None:
            try:
                recipes_limit = int(recipes_limit)
            except ValueError:
                return Response(
                    {"error": "Некорректное значение для recipes_limit"},
                    status=400,
                )
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


class UserAvatarUpdateView(RetrieveUpdateDestroyAPIView):
    """Вьюсет аватара пользователя."""

    serializer_class = AvatarSerializer

    def get_object(self):
        """Получает текущего пользователя."""
        return get_object_or_404(User, pk=self.request.user.id)

    def patch(self, request, *args, **kwargs):
        """Обновляет аватар пользователя."""
        user = self.get_object()
        serializer = self.get_serializer(user, data=request.data, partial=True)
        if not serializer.is_valid():
            serializer.save()
            raise ValidationError(serializer.errors)
        return Response(
            {"status": "Аватар обновлен"}, status=status.HTTP_200_OK
        )

    def delete(self, request, *args, **kwargs):
        """Удаляет аватар пользователя."""
        try:
            user = get_object_or_404(User, pk=self.request.user.id)
            user.avatar.delete(save=False)
            user.save()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            return Response(e, status=status.HTTP_400_BAD_REQUEST)


class RecipeViewSet(ModelViewSet):
    """Вьюсет для модели рецепта."""

    queryset = Recipe.objects.all()
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
        recipe = serializer.save(author=self.request.user)
        return recipe

    def create(self, request, *args, **kwargs):
        """Создает новый рецепт, проверяя авторизацию пользователя."""
        if not request.user.is_authenticated:
            raise AuthenticationFailed("Пользователь не авторизован", code=401)

        return super().create(request, *args, **kwargs)

    @action(
        detail=False, methods=["get"], permission_classes=[IsAuthenticated]
    )
    def download_shopping_cart(self, request):
        if not request.user.is_authenticated:
            return JsonResponse(
                {"detail": "Пользователь не авторизован."},
                status=401,
            )
        shopping_cart_items = ShoppingCart.objects.filter(user=request.user)
        return generate_pdf(shopping_cart_items)


class FavoritesViewSet(ModelViewSet):
    """Вьюсет списка избранных рецептов."""

    serializer_class = FavoritesSerializer
    queryset = Favorites.objects.all()
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        """Добавляет рецепт в список избранного."""
        recipe_id = self.kwargs["id"]
        recipe = get_object_or_404(Recipe, id=recipe_id)

        if Favorites.objects.filter(user=request.user, recipe=recipe).exists():
            return Response(
                {"detail": "Рецепт уже в избранном."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        Favorites.objects.create(user=request.user, recipe=recipe)
        serializer = FavoritesSerializer(recipe)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def delete(self, request, *args, **kwargs):
        """Удаляет рецепт из списка избранного."""
        recipe_id = self.kwargs["id"]
        user_id = request.user.id
        recipe = get_object_or_404(Recipe, id=recipe_id)
        favorite = Favorites.objects.filter(
            user__id=user_id, recipe=recipe
        ).first()
        if not favorite:
            return Response(
                {"detail": "Избранный рецепт не найден."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        favorite.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class TagViewSet(ReadOnlyModelViewSet):
    """Вьюсет для модели тега."""

    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permission_classes = (IsOwnerOrReadOnly,)


class IngredientViewSet(ReadOnlyModelViewSet):
    """Вьюсет для модели ингредиента."""

    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    permission_classes = (IsOwnerOrReadOnly,)
    filter_backends = [IngredientSearchFilter]
    search_fields = ["^name"]


class SubscriptionViewSet(ModelViewSet):
    """Вьюсет подписки"""

    serializer_class = SubscriptionSerializer
    pagination_class = LimitPagePagination
    permission_classes = [IsOwnerOrReadOnly]

    def validate_subscription(self, user, author):
        """Проверяет валидность подписки"""
        if not user.is_authenticated:
            raise AuthenticationFailed(
                "Пользователь не авторизован.", code=401
            )

        if user.id == author.id:
            return {
                "detail": "Нельзя подписаться на самого себя."
            }, status.HTTP_400_BAD_REQUEST

        return None

    def create(self, request, *args, **kwargs):
        """Создает новую подписку на автора."""
        user_id = self.kwargs["id"]
        author = get_object_or_404(User, id=user_id)
        validation_response = self.validate_subscription(request.user, author)

        if validation_response:
            return Response(*validation_response)

        if Subscription.objects.filter(
            user=request.user, author=author
        ).exists():
            return Response(
                {"detail": "Вы уже подписаны на данного автора."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        recipes_limit = request.query_params.get("recipes_limit", None)

        if recipes_limit is not None:
            try:
                recipes_limit = int(recipes_limit)
            except ValueError:
                return Response(
                    {"error": "Некорректное значение для recipes_limit"},
                    status=400,
                )

        subscribe = Subscription.objects.create(
            user=request.user, author=author
        )
        serializer = SubscriptionSerializer(
            subscribe,
            context={"request": request, "recipes_limit": recipes_limit},
        )

        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def delete(self, request, *args, **kwargs):
        """Удаляет подписку на автора."""
        author_id = self.kwargs["id"]
        author = get_object_or_404(User, id=author_id)
        validation_response = self.validate_subscription(request.user, author)

        if validation_response:
            return Response(*validation_response)
        subscription = Subscription.objects.filter(
            user=request.user, author=author
        ).first()

        if not subscription:
            return Response(
                {"detail": "Подписка не найдена."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        subscription.delete()
        return Response(
            {"detail": "Подписка удалена."}, status=status.HTTP_204_NO_CONTENT
        )


class ShoppingCartViewSet(ModelViewSet):
    """Вьюсет списка покупок."""

    serializer_class = ShoppingCartSerializer
    pagination_class = LimitPagePagination
    queryset = ShoppingCart.objects.all()
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        """Добавляет рецепт в список покупок."""
        recipe_id = self.kwargs["id"]
        recipe = get_object_or_404(Recipe, id=recipe_id)

        if ShoppingCart.objects.filter(
            user=request.user, recipe=recipe
        ).exists():
            return Response(
                {"detail": "Рецепт уже в корзине."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        ShoppingCart.objects.create(user=request.user, recipe=recipe)
        serializer = ShoppingCartSerializer(recipe)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def delete(self, request, *args, **kwargs):
        """Удаляет рецепт из списка покупок."""
        recipe_id = self.kwargs["id"]
        recipe = get_object_or_404(Recipe, id=recipe_id)
        user_id = request.user.id

        shopping_cart_item = ShoppingCart.objects.filter(
            user__id=user_id, recipe=recipe
        ).first()
        if not shopping_cart_item:
            return Response(
                {"detail": "Рецепт не найден в списке покупок."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        shopping_cart_item.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
