import re

from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from djoser.serializers import UserCreateSerializer, UserSerializer
from rest_framework.exceptions import ValidationError
from rest_framework.serializers import (
    CharField,
    IntegerField,
    ModelSerializer,
    PrimaryKeyRelatedField,
    ReadOnlyField,
    SerializerMethodField,
)
from rest_framework.validators import UniqueTogetherValidator

from .fields import Base64ImageField, RecipeSubscriptionUserField
from recipes.models import (
    Favorites,
    Ingredient,
    Recipe,
    RecipeIngredient,
    ShoppingCart,
    Tag,
)
from users.models import Subscription

User = get_user_model()


class CustomUserSerializer(UserSerializer):
    """
    Сериализатор пользователей с дополнительными полями подписки и аватара.
    """

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
        """Проверяет, подписан ли текущий пользователь на автора."""
        user = self.context.get("request").user
        if user.is_authenticated:
            return Subscription.objects.filter(user=user, author=obj).exists()
        return False


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
        """Проверяет, соответствует ли имя пользователя допустимому формату."""
        if not re.match(r"^[\w.@+-]+$", value):
            raise ValidationError("Недопустимый формат имени пользователя.")
        return value

    def create(self, validated_data):
        """Создает нового пользователя и хеширует пароль."""
        user = User(
            email=validated_data["email"],
            username=validated_data["username"],
            first_name=validated_data["first_name"],
            last_name=validated_data["last_name"],
        )
        user.set_password(validated_data["password"])
        user.save()
        return user


class TagSerializer(ModelSerializer):
    """Сериализатор модели тега."""

    class Meta:
        model = Tag
        fields = ("id", "name", "slug")


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
    """Сериализатор для связаной модели Recipe и Ingredient."""

    id = ReadOnlyField(source="ingredient.id")
    name = ReadOnlyField(source="ingredient.name")
    measurement_unit = ReadOnlyField(source="ingredient.measurement_unit")

    class Meta:
        model = RecipeIngredient
        fields = ("id", "name", "measurement_unit", "amount")


class RecipeListSerializer(ModelSerializer):
    """
    Сериализатор для модели Recipe - чтение данных.
    Находится ли рецепт в избранном, списке покупок.
    Получение списка ингредиентов с добавленным полем
    amount из промежуточной модели.
    """

    author = CustomUserSerializer()
    tags = TagSerializer(many=True, read_only=True)
    ingredients = RecipeIngredientSerializer(
        many=True, source="recipe_ingredients", read_only=True
    )
    is_favorited = SerializerMethodField()
    is_in_shopping_cart = SerializerMethodField()

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

    def get_is_favorited(self, obj):
        user = self.context.get("request").user
        if not user.is_anonymous:
            return Favorites.objects.filter(recipe=obj, user=user).exists()
        return False

    def get_is_in_shopping_cart(self, obj):
        user = self.context.get("request").user
        if not user.is_anonymous:
            return ShoppingCart.objects.filter(recipe=obj, user=user).exists()
        return False


class AddIngredientSerializer(ModelSerializer):
    """
    Сериализатор для поля ingredient модели Recipe - создание ингредиентов.
    """

    id = PrimaryKeyRelatedField(queryset=Ingredient.objects.all())
    amount = IntegerField()

    class Meta:
        model = RecipeIngredient
        fields = ("id", "amount")


class RecipeWriteSerializer(ModelSerializer):
    """Сериализатор для модели Recipe - запись / обновление / удаление."""

    ingredients = AddIngredientSerializer(many=True, write_only=True)
    tags = PrimaryKeyRelatedField(queryset=Tag.objects.all(), many=True)
    image = Base64ImageField()
    author = CustomUserSerializer(read_only=True)

    class Meta:
        model = Recipe
        fields = (
            "ingredients",
            "tags",
            "image",
            "name",
            "text",
            "cooking_time",
            "author",
        )

    def validate_ingredients(self, value):
        ingredients = value
        if not ingredients:
            raise ValidationError({"ingredients": "Нужно выбрать ингредиент!"})
        ingredients_list = []
        for item in ingredients:
            ingredient = get_object_or_404(Ingredient, name=item["id"])
            if ingredient in ingredients_list:
                raise ValidationError(
                    {"ingredients": "Ингридиенты повторяются!"}
                )
            if int(item["amount"]) <= 0:
                raise ValidationError(
                    {"amount": "Количество должно быть больше 0!"}
                )
            ingredients_list.append(ingredient)
        return value

    def validate_tags(self, value):
        tags = value
        if not value:
            raise ValidationError({"tags": "Нужно выбрать тег!"})
        tags_list = []
        for tag in tags:
            if tag in tags_list:
                raise ValidationError({"tags": "Теги повторяются!"})
            tags_list.append(tag)
        return value

    def to_representation(self, instance):
        ingredients = super().to_representation(instance)
        ingredients["ingredients"] = RecipeIngredientSerializer(
            instance.recipe_ingredients.all(), many=True
        ).data
        return ingredients

    def add_tags_ingredients(self, ingredients, tags, model):
        for ingredient in ingredients:
            RecipeIngredient.objects.update_or_create(
                recipe=model,
                ingredient=ingredient["id"],
                amount=ingredient["amount"],
            )
        model.tags.set(tags)

    def create(self, validated_data):
        ingredients = validated_data.pop("ingredients")
        tags = validated_data.pop("tags")
        recipe = super().create(validated_data)
        self.add_tags_ingredients(ingredients, tags, recipe)
        return recipe

    def update(self, instance, validated_data):
        if 'ingredients' not in validated_data:
            raise ValidationError(
                {"ingredients": "Нужно выбрать ингредиенты!"}
            )
        if 'tags' not in validated_data:
            raise ValidationError({"tags": "Нужно выбрать теги!"})

        ingredients = validated_data.pop("ingredients")
        tags = validated_data.pop("tags")
        instance.ingredients.clear()
        self.add_tags_ingredients(ingredients, tags, instance)
        return super().update(instance, validated_data)


class AvatarSerializer(ModelSerializer):
    "Сереализатор аватара пользователя."

    avatar = Base64ImageField(required=True, allow_null=True)

    class Meta:
        model = User
        fields = ("avatar",)

    def update(self, instance, validated_data):
        """Обновление аватара пользователя."""
        instance.avatar = validated_data.get("avatar", instance.avatar)
        instance.save()
        return instance


class SubscriptionSerializer(ModelSerializer):
    """Сериализатор для подписок."""

    recipes = RecipeSubscriptionUserField()
    recipes_count = SerializerMethodField(read_only=True)
    id = ReadOnlyField(source="author.id")
    email = ReadOnlyField(source="author.email")
    username = ReadOnlyField(source="author.username")
    first_name = ReadOnlyField(source="author.first_name")
    last_name = ReadOnlyField(source="author.last_name")
    avatar = SerializerMethodField()
    is_subscribed = SerializerMethodField()

    class Meta:
        model = User
        fields = (
            "avatar",
            "email",
            "id",
            "username",
            "first_name",
            "last_name",
            "is_subscribed",
            "recipes",
            "recipes_count",
            "avatar",
        )

    def to_representation(self, instance):
        """Преобразование представления экземпляра с учетом лимита рецептов."""
        representation = super().to_representation(instance)
        recipes_limit = self.context.get("recipes_limit")

        if recipes_limit is not None:
            representation["recipes"] = representation["recipes"][
                : int(recipes_limit)
            ]

        return representation

    def get_recipes(self, obj):
        """Получение списка рецептов автора с учетом лимита."""
        recipes = obj.author.recipes.all()
        limit = self.context["request"].query_params.get("recipes_limit", None)
        if limit:
            recipes = recipes[: int(limit)]
        return [
            {
                "id": recipe.id,
                "name": recipe.name,
                "image": recipe.image.url,
                "cooking_time": recipe.cooking_time,
            }
            for recipe in recipes
        ]

    def get_recipes_count(self, obj):
        """Получение количества рецептов автора."""
        return Recipe.objects.filter(author=obj.author).count()

    def get_avatar(self, obj):
        """Получение URL аватара автора."""
        if obj.author.avatar:
            return obj.author.avatar.url
        return None

    def get_is_subscribed(self, obj):
        """Проверка, подписан ли пользователь на автора."""
        return Subscription.objects.filter(
            user=obj.user, author=obj.author
        ).exists()


class FavoritesSerializer(ModelSerializer):
    """Сериализатор для списка избранных рецептов."""

    id = IntegerField()
    name = CharField()
    image = Base64ImageField(
        max_length=None,
        use_url=False,
    )
    cooking_time = IntegerField()

    class Meta:
        model = Favorites
        fields = ("id", "name", "image", "cooking_time")
        validators = UniqueTogetherValidator(
            queryset=Favorites.objects.all(), fields=("user", "recipe")
        )


class ShoppingCartSerializer(ModelSerializer):
    """Сериализатор для списка покупок."""

    id = IntegerField()
    name = CharField()
    image = Base64ImageField(max_length=None, use_url=False)
    cooking_time = IntegerField()

    class Meta:
        model = ShoppingCart
        fields = ("id", "name", "image", "cooking_time")
        validators = [
            UniqueTogetherValidator(
                queryset=ShoppingCart.objects.all(), fields=("user", "recipe")
            )
        ]
