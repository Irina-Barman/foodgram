from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework.validators import UniqueValidator
from djoser.serializers import UserCreateSerializer

from rest_framework import serializers
from drf_extra_fields.fields import Base64ImageField
from django.shortcuts import get_object_or_404

from users.models import Subscription
from .models import (
    Ingredient,
    Tag,
    Recipe,
    ShoppingCart,
    Favorite,
    RecipeIngredient,
)

from users.validators import validate_username_not_me

User = get_user_model()


class SignUpSerializer(UserCreateSerializer):
    """Сериализатор для регистрации пользователей."""

    username = serializers.CharField(
        validators=[
            UniqueValidator(queryset=User.objects.all()),
            validate_username_not_me,
        ]
    )
    email = serializers.EmailField(
        validators=[UniqueValidator(queryset=User.objects.all())]
    )

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
        extra_kwargs = {"password": {"write_only": True}}

    def validate(self, data):
        """Проверяет валидность данных при регистрации."""
        username = data["username"]
        email = data["email"]

        errors = {}
        if User.objects.filter(email=email).exists():
            errors["email"] = "Пользователь с таким email уже существует."
        if User.objects.filter(username=username).exists():
            errors["username"] = (
                "Пользователь с таким username уже существует."
            )

        if errors:
            raise serializers.ValidationError(errors)

        return data


class UserSerializer(serializers.ModelSerializer):
    """Сериализатор пользователя."""

    is_subscribed = serializers.SerializerMethodField()

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
        user = self.context.get("request").user
        return (
            user.is_authenticated
            and Subscription.objects.filter(user=user, author=obj).exists()
        )


class IngredientSerializer(serializers.ModelSerializer):
    """Сериализатор ингредиентов."""

    class Meta:
        model = Ingredient
        fields = ("id", "name", "measurement_unit")


class TagSerializer(serializers.ModelSerializer):
    """Сериализатор тегов."""

    class Meta:
        model = Tag
        fields = ("id", "name", "slug")


class ShortRecipeSerializer(serializers.ModelSerializer):
    """Сериализатор рецептов для краткого отображения."""

    class Meta:
        model = Recipe
        fields = ("id", "name", "image", "cooking_time")
        read_only_fields = ("id", "name", "image", "cooking_time")


class ShoppingCartSerializer(ShortRecipeSerializer):
    """Сериализатор списка покупок."""

    def validate(self, data):
        request = self.context.get("request")
        recipe_id = self.context.get("view").kwargs.get("recipe_id")
        recipe = get_object_or_404(Recipe, pk=recipe_id)

        if ShoppingCart.objects.filter(
            user=request.user, recipe=recipe
        ).exists():
            raise serializers.ValidationError("Рецепт уже в списке покупок")
        return data

    def create(self, validated_data):
        request = self.context.get("request")
        recipe_id = self.context.get("view").kwargs.get("recipe_id")
        recipe = get_object_or_404(Recipe, pk=recipe_id)
        ShoppingCart.objects.create(user=request.user, recipe=recipe)
        return recipe


class FavoriteSerializer(ShortRecipeSerializer):
    """Сериализатор избранного."""

    def validate(self, data):
        request = self.context.get("request")
        recipe_id = self.context.get("view").kwargs.get("recipe_id")
        recipe = get_object_or_404(Recipe, pk=recipe_id)

        if Favorite.objects.filter(user=request.user, recipe=recipe).exists():
            raise serializers.ValidationError(
                "Рецепт уже добавлен в избранное"
            )
        return data

    def create(self, validated_data):
        request = self.context.get("request")
        recipe_id = self.context.get("view").kwargs.get("recipe_id")
        recipe = get_object_or_404(Recipe, pk=recipe_id)
        Favorite.objects.create(user=request.user, recipe=recipe)
        return recipe


class RecipeIngredientSerializer(serializers.ModelSerializer):
    """Сериализатор модели соединяющей ингредиенты и рецепты."""

    id = serializers.IntegerField(source="ingredient.id")
    name = serializers.ReadOnlyField(source="ingredient.name")
    measurement_unit = serializers.ReadOnlyField(
        source="ingredient.measurement_unit"
    )

    class Meta:
        model = RecipeIngredient
        fields = ("id", "amount", "name", "measurement_unit")


class RecipeReadSerializer(serializers.ModelSerializer):
    """Сериализатор чтения рецептов."""

    tags = TagSerializer(many=True, read_only=True)
    author = UserSerializer(read_only=True)
    ingredients = RecipeIngredientSerializer(many=True, read_only=True)
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()

    class Meta:
        model = Recipe
        fields = (
            "id",
            "name",
            "image",
            "text",
            "cooking_time",
            "tags",
            "author",
            "ingredients",
            "is_favorited",
            "is_in_shopping_cart",
        )

    def get_is_favorited(self, obj):
        user = self.context.get("request").user
        if user.is_authenticated:
            return Favorite.objects.filter(user=user, recipe=obj).exists()
        return False

    def get_is_in_shopping_cart(self, obj):
        user = self.context.get("request").user
        if user.is_authenticated:
            return ShoppingCart.objects.filter(user=user, recipe=obj).exists()
        return False


class RecipeCreateUpdateSerializer(serializers.ModelSerializer):
    """Сериализатор для создания и обновления рецептов."""

    tags = serializers.PrimaryKeyRelatedField(
        queryset=Tag.objects.all(), many=True
    )
    ingredients = RecipeIngredientSerializer(many=True)
    image = Base64ImageField()

    class Meta:
        model = Recipe
        fields = (
            "name",
            "text",
            "tags",
            "ingredients",
            "image",
            "cooking_time",
        )

    def validate(self, data):
        """Проверяет наличие тегов и ингредиентов."""
        tags = data.get("tags", [])
        ingredients = data.get("ingredients", [])

        if not tags:
            raise serializers.ValidationError("Выберите хотя бы один тег.")

        if not ingredients:
            raise serializers.ValidationError(
                "Добавьте хотя бы один ингредиент."
            )

        ingredient_ids = {ingredient["id"] for ingredient in ingredients}
        if len(ingredient_ids) != len(ingredients):
            raise serializers.ValidationError(
                "Ингредиенты не должны повторяться."
            )

        return data

    def create(self, validated_data):
        """Создаёт новый рецепт и его ингредиенты."""
        tags = validated_data.pop("tags")
        ingredients_data = validated_data.pop("ingredients")
        recipe = Recipe.objects.create(**validated_data)

        recipe.tags.set(tags)

        for ingredient_data in ingredients_data:
            RecipeIngredient.objects.create(recipe=recipe, **ingredient_data)

        return recipe

    def update(self, instance, validated_data):
        """Обновляет существующий рецепт и его ингредиенты."""
        tags = validated_data.pop("tags", None)
        ingredients_data = validated_data.pop("ingredients", None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if tags is not None:
            instance.tags.set(tags)

        if ingredients_data is not None:
            instance.recipeingredient_set.all().delete()
            for ingredient_data in ingredients_data:
                RecipeIngredient.objects.create(
                    recipe=instance, **ingredient_data
                )

        return instance


class SubscriptionSerializer(serializers.ModelSerializer):
    """Сериализатор для модели подписки."""

    user = UserSerializer(read_only=True)  # Подписчик
    author = UserSerializer(read_only=True)  # Автор рецепта

    class Meta:
        model = Subscription
        fields = ("id", "user", "author")

    def create(self, validated_data):
        """Создает новую подписку."""
        user = self.context["request"].user
        author = validated_data["author"]

        # Проверяем, существует ли уже подписка
        if Subscription.objects.filter(user=user, author=author).exists():
            raise serializers.ValidationError(
                "Вы уже подписаны на этого пользователя."
            )

        # Создаем подписку
        subscription = Subscription.objects.create(user=user, author=author)
        return subscription

    def validate(self, data):
        """Проверяет корректность данных для создания подписки."""
        user = self.context["request"].user
        author = data.get("author")

        if author == user:
            raise serializers.ValidationError(
                "Нельзя подписаться на самого себя."
            )

        return data
