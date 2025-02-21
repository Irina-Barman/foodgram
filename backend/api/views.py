from django.contrib.auth import get_user_model
from django.db.models import Sum
from rest_framework.exceptions import PermissionDenied
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

    queryset = User.objects.all().order_by("username")
    serializer_class = CustomUserSerializer
    pagination_class = LimitPagePagination
    filter_backends = (DjangoFilterBackend, filters.SearchFilter)
    search_fields = ("username", "email")
    permission_classes = [AllowAny]  # Доступ для всех

    def user_list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        serializer = self.get_serializer(page, many=True)
        return (
            self.get_paginated_response(serializer.data)
            if page
            else Response(serializer.data)
        )

    def subscribed(self, subscription_user):
        if self.request.user == subscription_user:
            return self.error_response(
                "Нельзя подписаться на себя", status.HTTP_400_BAD_REQUEST
            )

        subscription, created = Subscription.objects.get_or_create(
            user=self.request.user, author=subscription_user
        )
        if not created:
            return self.error_response(
                "Вы уже подписаны на этого пользователя.",
                status.HTTP_400_BAD_REQUEST,
            )

        serializer = SubscriptionSerializer(subscription)
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
        serializer = CustomUserSerializer(
            request.user, context={"request": request}
        )
        return Response(serializer.data)

    @action(
        detail=True,
        methods=["post", "delete"],
        permission_classes=[IsAuthenticated],
    )
    def subscribe(self, request, id):
        subscription_user = get_object_or_404(User, id=id)
        return (
            self.unsubscribed(subscription_user)
            if request.method == "DELETE"
            else self.subscribed(subscription_user)
        )

    @action(detail=False, methods=["get"], permission_classes=[AllowAny])
    def subscriptions(self, request):
        subscriptions = Subscription.objects.filter(user=self.request.user)
        pages = self.paginate_queryset(subscriptions)
        serializer = SubscriptionSerializer(pages, many=True)
        return self.get_paginated_response(serializer.data)

    @action(
        detail=True,
        methods=["put", "delete"],
        permission_classes=[IsAuthenticated],
)
    def avatar(self, request, pk=None):
        user = self.request.user
        if request.method == "PUT":
            return self.handle_avatar_upload(user, request.data.get("avatar"))
        elif request.method == "DELETE":
            return self.handle_avatar_delete(user)

    def handle_avatar_upload(self, user, avatar_data):
        """Обработка загрузки аватара."""
        if avatar_data:  # Если данные аватара предоставлены
            try:
                format, imgstr = avatar_data.split(";base64,")
                ext = format.split("/")[-1]
                img_data = base64.b64decode(imgstr)
                file_name = f"avatar_{user.id}.{ext}"
                user.avatar.save(file_name, ContentFile(img_data), save=True)
                return Response(
                    {"avatar": user.avatar.url}, status=status.HTTP_200_OK
                )
            except Exception as e:
                return self.error_response(
                    str(e), status=status.HTTP_400_BAD_REQUEST
                )
        else:
            return Response(
                {"detail": "Нет данных для загрузки аватара."},
                status=status.HTTP_400_BAD_REQUEST,
            )

    def handle_avatar_delete(self, user):
        """Обработка удаления аватара."""
        if user.avatar:
            user.avatar.delete(save=False)
            user.avatar = None
            user.save()
            return Response(status=status.HTTP_204_NO_CONTENT)
        return self.error_response(
            "Аватар не найден.", status=status.HTTP_404_NOT_FOUND
        )

    def error_response(self, message, status_code):
        """Универсальный метод для обработки ошибок."""
        return Response({"detail": message}, status=status_code)


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

    queryset = Recipe.objects.all().order_by("name")
    permission_classes = (AdminOrAuthor,)
    pagination_class = LimitPagePagination
    filter_backends = (DjangoFilterBackend,)
    filterset_class = RecipesFilter

    def toggle_recipe(self, request, recipe_model, recipe):
        """Обработчик для добавления/удаления рецепта из избранного или списка покупок."""
        if request.method == "POST":
            if recipe_model.objects.filter(
                user=request.user, recipe=recipe
            ).exists():
                return Response(
                    {"message": "Рецепт уже в списке."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            recipe_model.objects.create(user=request.user, recipe=recipe)
            serializer = RecipeForSubscriptionSerializer(recipe)
            return Response(
                data=serializer.data, status=status.HTTP_201_CREATED
            )

        instance = get_object_or_404(
            recipe_model, user=request.user, recipe=recipe
        )
        instance.delete()
        return Response(
            {"message": "Рецепт успешно удален."}, status=status.HTTP_200_OK
        )

    def get_serializer_class(self):
        if self.action in ["list", "retrieve"]:
            return RecipeSerializer
        return RecipeCreateSerializer

    def perform_create(self, serializer):
        if self.request.user.is_authenticated:
            serializer.save(author=self.request.user)
        else:
            raise PermissionDenied(
                "Вы должны быть аутентифицированы для создания рецепта."
            )

    def perform_update(self, serializer):
        serializer.save(author=self.request.user)

    @action(
        detail=True,
        methods=["post", "delete"],
        permission_classes=[IsAuthenticated],
    )
    def favorite(self, request, pk):
        recipe = get_object_or_404(Recipe, pk=pk)
        return self.toggle_recipe(request, Favorite, recipe)

    @action(
        detail=True,
        methods=["post", "delete"],
        permission_classes=[IsAuthenticated],
    )
    def shopping_cart(self, request, pk):
        recipe = get_object_or_404(Recipe, pk=pk)
        return self.toggle_recipe(request, ShoppingCart, recipe)

    @action(
        detail=False, methods=["get"], permission_classes=[IsAuthenticated]
    )
    def download_shopping_cart(self, request):
        user = request.user
        ingredients = (
            AmountIngredient.objects.filter(recipe__shopping_cart__user=user)
            .values("ingredients__name", "ingredients__measurement_unit")
            .annotate(amount=Sum("amount"))
        )
        shopping_cart = "Список покупок:\n"
        for ingredient in ingredients:
            shopping_cart += f"{ingredient['ingredients__name'].capitalize()} {ingredient['amount']} {ingredient['ingredients__measurement_unit']},\n"

        response = HttpResponse(shopping_cart, content_type="text/plain")
        response["Content-Disposition"] = (
            'attachment; filename="shopping_cart.txt"'
        )
        return response
