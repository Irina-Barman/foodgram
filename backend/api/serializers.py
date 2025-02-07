from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.validators import UnicodeUsernameValidator
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

from ..users.validators import validate_username_not_me


User = get_user_model()


class SignUpSerializer(serializers.Serializer):
    """Сериализатор для регистрации пользователей."""

    username = serializers.CharField(
        max_length=settings.MAX_USERNAME_LENGTH,
        required=True,
        validators=[
            UnicodeUsernameValidator(),
            validate_username_not_me,
        ],
    )
    email = serializers.EmailField(
        max_length=settings.MAX_EMAIL_LENGTH, required=True
    )

    def validate(self, data):
        """Проверяет валидность данных при регистрации."""
        username = data.get("username")
        email = data.get("email")

        email_exists = User.objects.filter(email=email).exists()
        username_exists = User.objects.filter(username=username).exists()

        error_msg = {}
        if email_exists:
            error_msg["email"] = "Пользователь с таким email уже существует."
        if username_exists:
            error_msg["username"] = (
                "Пользователь с таким username уже существует."
            )

        if error_msg:
            raise serializers.ValidationError(error_msg)

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
        )

    def get_is_subscribed(self, obj):
        user = self.context.get("request").user
        if user.is_authenticated:
            return Subscription.objects.filter(user=user, author=obj).exists()
        return False


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
    """Сериализатор рецептов для простого короткого отображения."""

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

    tags = TagSerializer(many=True)
    ingredients = RecipeIngredientSerializer(
        many=True, source="recipeingredient_set"
    )
    author = serializers.StringRelatedField()
    image = Base64ImageField()
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()

    class Meta:
        model = Recipe
        fields = (
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
        )

    def get_is_in_shopping_cart(self, obj):
        request = self.context.get("request")
        return ShoppingCart.objects.filter(
            user=request.user, recipe=obj
        ).exists()

    def get_is_favorited(self, obj):
        request = self.context.get("request")
        return Favorite.objects.filter(user=request.user, recipe=obj).exists()


class RecipeCreateSerializer(serializers.ModelSerializer):
    """Сериализатор создания рецептов."""

    tags = serializers.PrimaryKeyRelatedField(
        queryset=Tag.objects.all(), many=True
    )
    ingredients = RecipeIngredientSerializer(
        many=True, source="recipeingredient_set"
    )
    image = Base64ImageField()

    class Meta:
        model = Recipe
        fields = (
            "tags",
            "ingredients",
            "name",
            "image",
            "text",
            "cooking_time",
        )

    def validate(self, data):
        tags = data.get("tags", [])
        ingredients = data.get("recipeingredient_set", [])

        if not tags:
            raise serializers.ValidationError("Выберите тег")

        if not ingredients:
            raise serializers.ValidationError("Выберите ингридиеты")

        ingredient_ids = [
            ingredient["ingredient"]["id"] for ingredient in ingredients
        ]
        if len(ingredient_ids) != len(set(ingredient_ids)):
            raise serializers.ValidationError(
                "Ингредиенты не должны повторяться"
            )

        return data

    def create_ingredients(self, recipe, ingredients):
        RecipeIngredient.objects.bulk_create(
            [
                RecipeIngredient(
                    recipe=recipe,
                    ingredient_id=ingredient["ingredient"]["id"],
                    amount=ingredient["amount"],
                )
                for ingredient in ingredients
            ]
        )

    def create(self, validated_data):
        tags = validated_data.pop("tags")
        ingredients = validated_data.pop("recipeingredient_set")
        recipe = Recipe.objects.create(
            author=self.context["request"].user, **validated_data
        )
        recipe.tags.set(tags)
        self.create_ingredients(recipe, ingredients)
        return recipe

    def update(self, instance, validated_data):
        tags = validated_data.pop("tags")
        ingredients = validated_data.pop("recipeingredient_set")

        instance.tags.set(tags)
        RecipeIngredient.objects.filter(recipe=instance).delete()
        self.create_ingredients(instance, ingredients)

        return super().update(instance, validated_data)

    def to_representation(self, instance):
        return RecipeReadSerializer(instance, context=self.context).data


class FollowSerializer(serializers.ModelSerializer):
    """Сериализатор подписок."""

    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            "email",
            "id",
            "username",
            "first_name",
            "last_name",
            "recipes",
            "recipes_count",
        )

    def get_recipes(self, obj):
        limit = self.context["request"].query_params.get("recipes_limit")
        queryset = Recipe.objects.filter(author=obj)
        if limit:
            queryset = queryset[: int(limit)]
        return ShortRecipeSerializer(queryset, many=True).data

    def get_recipes_count(self, obj):
        return Recipe.objects.filter(author=obj).count()
