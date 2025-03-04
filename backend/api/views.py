from django.contrib.auth import get_user_model
from rest_framework.generics import (
    RetrieveUpdateDestroyAPIView,
    get_object_or_404,
)
from rest_framework import filters, status

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.permissions import AllowAny
from django.http import HttpResponse
from django.db.models import Sum
from rest_framework.exceptions import AuthenticationFailed, NotFound
from rest_framework.generics import ValidationError

from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from djoser.views import UserViewSet

from .filters import IngredientSearchFilter, RecipeFilter
from recipes.models import Tag, Recipe, Ingredient, Favorites, ShoppingCart
from users.models import Subscription
from .serializers import (
    AvatarSerializer,
    TagSerializer,
    ShoppingCartSerializer,
    IngredientSerializer,
    SubscriptionSerializer,
    RecipeSerializer,
    RecipeIngredient,
    FavoritesSerializer,
    CustomUserSerializer,
)
from .pagination import LimitPagePagination
from .permissions import IsOwnerOrReadOnly


User = get_user_model()


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
        """Получение и обновление информации о текущем пользователе."""
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
        """Просмотр подписок пользователя"""
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
    "Вьюсет аватара"
    serializer_class = AvatarSerializer

    def get_object(self):
        return get_object_or_404(User, pk=self.request.user.id)

    def patch(self, request, *args, **kwargs):
        user = self.get_object()
        serializer = self.get_serializer(user, data=request.data, partial=True)

        if not serializer.is_valid():
            serializer.save()
            raise ValidationError(serializer.errors)
        return Response(
            {"status": "Аватар обновлен"}, status=status.HTTP_200_OK
        )

    def delete(self, request, *args, **kwargs):
        try:
            user = get_object_or_404(User, pk=self.request.user.id)
            user.avatar.delete(save=False)
            user.save()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            return Response(e, status=status.HTTP_400_BAD_REQUEST)


class RecipeViewSet(ModelViewSet):
    """Вьюсет для модели рецепта."""

    serializer_class = RecipeSerializer
    queryset = Recipe.objects.all()
    pagination_class = LimitPagePagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_class = RecipeFilter
    filterset_fields = ["author", "tags",
                        "is_favorited", "is_in_shopping_cart"]
    permission_classes = [IsOwnerOrReadOnly]

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    def create(self, request, *args, **kwargs):
        """Создание нового рецепта"""
        if not request.user.is_authenticated:
            raise AuthenticationFailed("Пользователь не авторизован", code=401)

        return super().create(request, *args, **kwargs)

    @action(
        methods=["GET"], detail=False, permission_classes=[IsAuthenticated]
    )
    def download_shopping_cart(self, request):
        """Скачивание списка покупок"""
        ingredients = (
            RecipeIngredient.objects.filter(
                recipe__in=request.user.shopping_cart.all()
            )
            .values("ingredient__name", "ingredient__measurement_unit")
            .annotate(total_amount=Sum("amount"))
        )

        shopping_cart = "\n".join(
            f"{ingredient['ingredient__name']} - {ingredient['total_amount']} {ingredient['ingredient__measurement_unit']}"
            for ingredient in ingredients
        )

        response = HttpResponse(shopping_cart, content_type="text/plain")
        response["Content-Disposition"] = (
            'attachment; filename="shoppinglist.txt"'
        )
        return response


class FavoritesViewSet(ModelViewSet):
    """ViewSet Списки избранных рецептов
    Добавление /
    удаление из списка
    """

    serializer_class = FavoritesSerializer
    queryset = Favorites.objects.all()
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        """Добавление рецепта в список избранного"""
        recipe_id = self.kwargs["id"]
        recipe = get_object_or_404(Recipe, id=recipe_id)

        # Проверка на существование
        if Favorites.objects.filter(user=request.user, recipe=recipe).exists():
            return Response(
                {"detail": "Recipe is already in favorites."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        Favorites.objects.create(user=request.user, recipe=recipe)
        serializer = FavoritesSerializer(recipe)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def delete(self, request, *args, **kwargs):
        """Удаление рецепта из списка избранного"""
        recipe_id = self.kwargs["id"]
        user_id = request.user.id
        favorite = Favorites.objects.filter(
            user__id=user_id, recipe__id=recipe_id
        ).first()

        if not favorite:
            return Response(
                {"detail": "Favorite recipe not found."},
                status=status.HTTP_404_NOT_FOUND,
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

    def create(self, request, *args, **kwargs):
        # Проверка авторизации
        if not request.user.is_authenticated:
            raise AuthenticationFailed("Пользователь не авторизован.", code=401)

        user_id = self.kwargs["id"]
        user = get_object_or_404(User, id=user_id)
        
        if request.user.id == user.id:
            return Response(
                {"detail": "Нельзя подписаться на самого себя."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Проверка, существует ли уже подписка
        if Subscription.objects.filter(user=request.user, author=user).exists():
            return Response(
                {"detail": "Вы уже подписаны на данного автора."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Получаем лимит рецептов из запроса
        recipes_limit = request.query_params.get("recipes_limit", None)

        if recipes_limit is not None:
            try:
                recipes_limit = int(recipes_limit)
            except ValueError:
                return Response(
                    {"error": "Некорректное значение для recipes_limit"},
                    status=400,
                )

        # Создание новой подписки
        subscribe = Subscription.objects.create(user=request.user, author=user)
        
        # Передаем контекст с лимитом в сериализатор
        serializer = SubscriptionSerializer(subscribe, context={"request": request, "recipes_limit": recipes_limit})
        
        return Response(serializer.data, status=status.HTTP_201_CREATED)


    def delete(self, request, *args, **kwargs):
        """Удаление подписки"""
        if not request.user.is_authenticated:
            raise AuthenticationFailed("Пользователь не авторизован.", code=401)
        
        author_id = self.kwargs["id"]
        user_id = request.user.id

        # Проверяем, существует ли автор
        author = get_object_or_404(User, id=author_id)

        # Пытаемся найти подписку
        subscription = Subscription.objects.filter(user=request.user, author=author).first()

        # Если подписка не найдена, возвращаем 404
        if not subscription:
            raise NotFound("Подписка не найдена.")

        # Удаляем подписку
        subscription.delete()
        
        return Response(
            {"detail": "Подписка успешно удалена."},
            status=status.HTTP_204_NO_CONTENT,
        )


class ShoppingCartViewSet(ModelViewSet):
    """ViewSet Список покупок
    Добавление рецепта в список покупок /
    удаление рецепта из списка покупок /
    скачивание списка покупок
    """

    serializer_class = ShoppingCartSerializer
    pagination_class = LimitPagePagination
    queryset = ShoppingCart.objects.all()
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        """Добавление рецепта в список покупок"""
        recipe_id = self.kwargs["id"]
        recipe = get_object_or_404(Recipe, id=recipe_id)

        # Проверка на существование
        if ShoppingCart.objects.filter(
            user=request.user, recipe=recipe
        ).exists():
            return Response(
                {"detail": "Recipe is already in shopping cart."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        ShoppingCart.objects.create(user=request.user, recipe=recipe)
        serializer = ShoppingCartSerializer(recipe)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def delete(self, request, *args, **kwargs):
        """Удаление рецепта из
        списка покупок
        """
        recipe_id = self.kwargs["id"]
        user_id = request.user.id
        ShoppingCart.objects.filter(
            user__id=user_id, recipe__id=recipe_id
        ).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
