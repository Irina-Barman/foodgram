from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.db.models import Sum
import base64
from django.core.files.base import ContentFile
from django.http import HttpResponse
from django_filters.rest_framework import DjangoFilterBackend
from djoser.views import UserViewSet
from recipes.models import (
    AmountIngredient,
    Favorite,
    Ingredient,
    Recipe,
    ShoppingCart,
    Tag,
)
from rest_framework import filters, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from users.models import Subscription

from .filters import IngredientSearchFilter, RecipesFilter
from .pagination import LimitPagePagination
from .permissions import AdminOrAuthor, AdminOrReadOnly
from .serializers import (
    SubscriptionSerializer,
    IngredientSerializer,
    RecipeCreateSerializer,
    RecipeForSubscriptionSerializer,
    RecipeSerializer,
    TagSerializer,
    CustomUserSerializer,
)


User = get_user_model()


class CustomUserViewSet(UserViewSet):
    """Вьюсет для модели пользователей."""

    queryset = User.objects.all().order_by('username')
    serializer_class = CustomUserSerializer
    pagination_class = LimitPagePagination
    filter_backends = (
        DjangoFilterBackend,
        filters.SearchFilter,
    )
    search_fields = ("username", "email")
    permission_classes = (AllowAny,)  # Доступ для всех

    def subscribed(self, subscription_user):
        if self.request.user == subscription_user:
            return Response(
                {"message": "Нельзя подписаться на себя"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        subscriber, created = Subscription.objects.get_or_create(
            user=self.request.user, author=subscription_user
        )
        serializer = SubscriptionSerializer(subscriber)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def unsubscribed(self, subscription_user):
        subscription = get_object_or_404(
            Subscription, user=self.request.user, author=subscription_user
        )
        subscription.delete()
        return Response(
            {"message": "Вы успешно отписаны"}, status=status.HTTP_200_OK
        )

    @action(
        detail=False, methods=["get"], permission_classes=[IsAuthenticated]
    )
    def me(self, request):
        user = request.user
        if isinstance(user, AnonymousUser):
            return Response(
                {"detail": "Необходима аутентификация."}, status=401
            )

        serializer = CustomUserSerializer(user)
        return Response(serializer.data)

    @action(
        detail=True,
        methods=["post", "delete"],
        permission_classes=[permissions.IsAuthenticated],
    )
    def subscribe(self, request, id):
        subscription_user = get_object_or_404(User, id=id)
        if request.method == "DELETE":
            return self.unsubscribed(subscription_user)
        return self.subscribed(subscription_user)

    @action(
        detail=False,
        methods=["get"],
        permission_classes=[permissions.AllowAny],  # Доступ для всех
    )
    def subscriptions(self, request):
        subscriptions = Subscription.objects.filter(user=self.request.user)
        pages = self.paginate_queryset(subscriptions)
        serializer = SubscriptionSerializer(pages, many=True)
        return self.get_paginated_response(serializer.data)

    @action(
        detail=False,
        methods=["put", "delete"],
        permission_classes=[permissions.IsAuthenticated],
    )
    def avatar(self, request):
        """Добавление или удаление аватара текущего пользователя."""
        user = request.user

        if request.method == "PUT":
            avatar_data = request.data.get("avatar")
            if avatar_data:
                try:
                    # Извлекаем данные из строки Base64
                    format, imgstr = avatar_data.split(";base64,")
                    ext = format.split("/")[-1]  # Получаем расширение файла
                    # Декодируем строку Base64
                    img_data = base64.b64decode(imgstr)
                    # Сохраняем изображение
                    file_name = (
                        f"avatar_{user.id}.{ext}"  # Формируем имя файла
                    )
                    user.avatar.save(
                        file_name, ContentFile(img_data), save=True
                    )

                    # Возвращаем URL аватара
                    return Response(
                        {"avatar": user.avatar.url}, status=status.HTTP_200_OK
                    )
                except Exception as e:
                    return Response(
                        {"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST
                    )

            return Response(
                {"detail": "Поле avatar обязательно."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        elif request.method == "DELETE":
            if user.avatar:
                user.avatar.delete(save=False)  # Удаляем файл аватара
                user.avatar = None  # Обнуляем поле аватара
                user.save()
                return Response(status=status.HTTP_204_NO_CONTENT)

            return Response(
                {"detail": "Аватар не найден."},
                status=status.HTTP_404_NOT_FOUND,
            )


class TagViewSet(viewsets.ModelViewSet):
    """Вьюсет для модели тэгов."""

    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    pagination_class = None
    permission_classes = (AdminOrReadOnly,)


class IngredientViewSet(viewsets.ModelViewSet):
    """Вьюсет для модели ингредиентов."""

    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    permission_classes = (AdminOrReadOnly,)
    pagination_class = None
    filter_backends = (IngredientSearchFilter,)
    search_fields = ("^name",)


class RecipeViewSet(viewsets.ModelViewSet):
    """Вьюсет для рецептов."""

    queryset = Recipe.objects.all()
    permission_classes = (AdminOrAuthor,)
    pagination_class = LimitPagePagination
    filter_backends = (DjangoFilterBackend,)
    filterset_class = RecipesFilter

    def get_serializer_class(self):
        if self.action == "list":
            return RecipeSerializer
        if self.action == "retrieve":
            return RecipeSerializer
        return RecipeCreateSerializer

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
        recipe = get_object_or_404(Recipe, pk=pk)
        if request.method == "POST":
            Favorite.objects.create(user=request.user, recipe=recipe)
            serializer = RecipeForSubscriptionSerializer(recipe)
            return Response(
                data=serializer.data, status=status.HTTP_201_CREATED
            )
        deleted = get_object_or_404(Favorite, user=request.user, recipe=recipe)
        deleted.delete()
        return Response(
            {"message": "Рецепт успешно удален из избранного"},
            status=status.HTTP_200_OK,
        )

    @action(
        detail=True,
        methods=["post", "delete"],
        permission_classes=[IsAuthenticated],
    )
    def shopping_cart(self, request, pk):
        recipe = get_object_or_404(Recipe, pk=pk)
        if request.method == "POST":
            ShoppingCart.objects.create(user=request.user, recipe=recipe)
            serializer = RecipeForSubscriptionSerializer(recipe)
            return Response(
                data=serializer.data, status=status.HTTP_201_CREATED
            )
        deleted = get_object_or_404(
            ShoppingCart, user=request.user, recipe=recipe
        )
        deleted.delete()
        return Response(
            {"message": "Рецепт успешно удален из списка покупок"},
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=["get"])
    def download_shopping_cart(self, request):
        user = request.user
        ingredients = (
            AmountIngredient.objects.filter(recipe__shopping_cart__user=user)
            .values("ingredients__name", "ingredients__measurement_unit")
            .annotate(amount=Sum("amount"))
        )
        data = ingredients.values_list(
            "ingredients__name", "ingredients__measurement_unit", "amount"
        )
        shopping_cart = "Список покупок:\n"
        for name, measure, amount in data:
            shopping_cart += f"{name.capitalize()} {amount} {measure},\n"
        response = HttpResponse(shopping_cart, content_type="text/plain")
        return response
