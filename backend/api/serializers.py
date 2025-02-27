import re
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from rest_framework.validators import UniqueTogetherValidator
from djoser.serializers import UserCreateSerializer, UserSerializer
from django.db import transaction
from django.db.models import F

from rest_framework.serializers import (
    ModelSerializer,
    SerializerMethodField,
    ReadOnlyField,
    PrimaryKeyRelatedField,
    CharField,
    IntegerField,
)
from rest_framework.exceptions import ValidationError
from drf_extra_fields.fields import Base64ImageField

from recipes.models import (
    Tag,
    Recipe,
    Ingredient,
    RecipeIngredient,
    Favorites,
    ShoppingCart,
)
from users.models import Subscription


User = get_user_model()


class CustomUserSerializer(UserSerializer):
    """Сериализатор пользователей с дополнительными полями."""

    is_subscribed = SerializerMethodField()
    avatar = Base64ImageField(allow_null=True)

    class Meta:
        model = User
        fields = (
            "email",
            "id",
            "username",
            "first_name",
            "last_name",
            "is_subscribed",
            "avatar",
        )

    def get_is_subscribed(self, obj):
        """Проверка подписки пользователя"""
        user = self.context.get("request").user
        if user.is_anonymous:
            return False
        return Subscription.objects.filter(user=user, author=obj.id).exists()


class CustomCreateUserSerializer(UserCreateSerializer):
    """Сериализатор для регистрации пользователей."""

    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "username",
            "first_name",
            "last_name",
            "password",
        )

    def validate_username(self, value):
        if not re.match(r"^[\w.@+-]+$", value):
            raise ValidationError("Недопустимый формат имени пользователя.")
        return value

    def create(self, validated_data):
        user = User(
            email=validated_data["email"],
            username=validated_data["username"],
            first_name=validated_data["first_name"],
            last_name=validated_data["last_name"],
        )
        user.set_password(validated_data["password"])
        user.save()

        # Возвращаем созданного пользователя
        return user


class TagSerializer(ModelSerializer):
    """Сериализатор модели тега."""

    class Meta:
        model = Tag
        fields = "__all__"
        read_only_fields = ("id", "name", "slug")


class IngredientSerializer(ModelSerializer):
    """Сериализатор модели ингредиента."""

    class Meta:
        model = Ingredient
        fields = "__all__"
        read_only_fields = (
            "id",
            "name",
            "measurement_unit",
        )


class RecipeIngredientSerializer(ModelSerializer):
    """Сериализатор Ингредиенты в рецепте"""

    id = PrimaryKeyRelatedField(queryset=Ingredient.objects.all())
    name = CharField(source="ingredient.name", read_only=True)
    ingredient = IngredientSerializer()
    measurement_unit = CharField(source="ingredient.measurement_unit", read_only=True)
    amount = IntegerField()

    class Meta:
        model = RecipeIngredient
        fields = ["id", "name", "ingredient", "measurement_unit", "amount"]


class RecipeSerializer(ModelSerializer):
    """Сериализатор модели рецепта."""

    image = Base64ImageField()
    tags = TagSerializer(read_only=True, many=True)
    ingredients = RecipeIngredientSerializer(
        many=True, source="recipe_ingredients", read_only=True
    )
    author = CustomUserSerializer(read_only=True)
    is_favorited = SerializerMethodField(read_only=True)
    is_in_shopping_cart = SerializerMethodField(read_only=True)

    class Meta:
        model = Recipe
        fields = [
            "id",
            "tags",
            "author",
            "ingredients",
            "is_favorited",
            "is_in_shopping_cart",
            "name",
            "image",
            "text",
            "cooking_time",
        ]

    def get_is_favorited(self, obj):
        """Проверка наличия рецепта в избранном"""
        user = self.context.get("request").user
        if user.is_anonymous:
            return False
        return Favorites.objects.filter(user=user, recipe=obj).exists()

    def get_is_in_shopping_cart(self, obj):
        """Проверка наличия рецепта в списке покупок"""
        user = self.context.get("request").user
        if user.is_anonymous:
            return False
        return ShoppingCart.objects.filter(user=user, recipe=obj).exists()

    def validate(self, data):
        """Метод для валидации данных перед созданием рецепта"""
        ingredients = self.initial_data.get("ingredients")
        if not ingredients:
            raise ValidationError(
                {"ingredients": "В рецепте отсутствуют ингредиенты"}
            )

        ingredient_ids = set()
        for ingredient_item in ingredients:
            ingredient_id = ingredient_item.get("id")
            if ingredient_id in ingredient_ids:
                raise ValidationError("Ингредиент уже добавлен в рецепт")

            amount = ingredient_item.get("amount")
            if not isinstance(amount, (int, float)) or amount <= 0:
                raise ValidationError("Неправильное количество ингредиента")

            ingredient_ids.add(ingredient_id)

        return data

    def create_ingredients(self, ingredients, recipe):
        """Добавление ингредиентов"""
        
        for ingredient in ingredients:
            amount = ingredient["amount"]
            if RecipeIngredient.objects.filter(
                recipe=recipe,
                ingredients=get_object_or_404(RecipeIngredient, id=ingredient["id"]),
            ).exists():
                amount += F("amount")
            RecipeIngredient.objects.update_or_create(
                recipe=recipe,
                ingredients=get_object_or_404(RecipeIngredient, id=ingredient["id"]),
                defaults={"amount": amount},
            )

    @transaction.atomic
    def create(self, validated_data):
        """Создание рецепта"""
        tags_data = validated_data.pop("tags", [])
        ingredients_data = validated_data.pop("ingredients", [])
        image = validated_data.pop("image", None)

        recipe = Recipe.objects.create(image=image, **validated_data)
        self.create_ingredients(ingredients_data, recipe)
        recipe.tags.set(tags_data)
        return recipe

    @transaction.atomic
    def update(self, recipe, validated_data):
        ingredients = validated_data.pop("ingredients", [])
        tags = validated_data.pop("tags", [])

        RecipeIngredient.objects.filter(recipe=recipe).delete()
        self.create_ingredients(ingredients, recipe)
        recipe.tags.set(tags)
        return super().update(recipe, validated_data)


class ShortRecipeSerializer(ModelSerializer):
    """Сериализатор сокращенного отображения рецепта."""

    image = Base64ImageField()

    class Meta:
        model = Recipe
        fields = ("id", "name", "image", "cooking_time")
        read_only_fields = ("id", "name", "image", "cooking_time")


class SubscriptionSerializer(CustomUserSerializer):
    """Сериализатор модели подписки."""

    email = ReadOnlyField(source="author.email")
    id = ReadOnlyField(source="author.id")
    username = ReadOnlyField(source="author.username")
    first_name = ReadOnlyField(source="author.first_name")
    last_name = ReadOnlyField(source="author.last_name")
    is_subscribed = SerializerMethodField()
    recipe = SerializerMethodField()
    recipe_count = SerializerMethodField()

    class Meta:
        model = Subscription
        fields = (
            "email",
            "id",
            "username",
            "first_name",
            "last_name",
            "is_subscribed",
            "recipe",
            "recipe_count",
        )

    def validate(self, data):
        author = self.instance
        user = self.context.get("request").user
        if Subscription.objects.filter(user=user, author=author).exists():
            raise ValidationError("Вы уже подписаны на данного автора")
        if user == author:
            raise ValidationError("Нельзя подписаться на самого себя")
        return data

    def get_recipes(self, obj):
        """Получение рецептов автора"""
        author = self.instance
        request = self.context.get("request")
        limit = request.GET.get("recipe_limit")
        queryset = Recipe.objects.filter(author=author)
        if limit:
            queryset = queryset[: int(limit)]
        return ShortRecipeSerializer(queryset, many=True).data

    def get_recipe_count(self, obj):
        return obj.recipe.count()


class FavoritesSerializer(ModelSerializer):
    """Сериализатор Списки избранных рецептов"""

    id = IntegerField()
    name = CharField()
    image = Base64ImageField(
        max_length=None,
        use_url=False,
    )
    cooking_time = IntegerField()

    class Meta:
        model = Favorites
        fields = ["id", "name", "image", "cooking_time"]
        validators = UniqueTogetherValidator(
            queryset=Favorites.objects.all(), fields=("user", "recipe")
        )


class ShoppingCartSerializer(ModelSerializer):
    """Сериализатор Список покупок"""

    id = IntegerField()
    name = CharField()
    image = Base64ImageField(max_length=None, use_url=False)
    cooking_time = IntegerField()

    class Meta:
        model = ShoppingCart
        fields = ["id", "name", "image", "cooking_time"]
        validators = [
            UniqueTogetherValidator(
                queryset=ShoppingCart.objects.all(), fields=("user", "recipe")
            )
        ]
