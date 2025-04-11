import re

from django.contrib.auth import get_user_model
from djoser.serializers import UserCreateSerializer, UserSerializer
from rest_framework.exceptions import ValidationError
from rest_framework.serializers import (
    CharField,
    Field,
    IntegerField,
    ModelSerializer,
    PrimaryKeyRelatedField,
    ReadOnlyField,
    SerializerMethodField,
)
from rest_framework.validators import UniqueTogetherValidator

from .fields import Base64ImageField
from recipes.models import (
    Favorites,
    Ingredient,
    Recipe,
    RecipeIngredient,
    ShoppingCart,
    ShortRecipeURL,
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


class RecipeSerializer(ModelSerializer):
    """Сериализатор для модели Recipe."""

    class Meta:
        model = Recipe
        fields = ("id", "name", "image", "cooking_time")

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation["image"] = (
            instance.image.url if instance.image else None
        )
        return representation


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


class RecipeSubscriptionUserField(Field):
    """Сериализатор для вывода рецептов в подписках."""

    def get_attribute(self, instance):
        """Получение списка рецептов, принадлежащих автору."""
        return Recipe.objects.filter(author=instance.author)

    def to_representation(self, recipes_list):
        """Преобразование списка в удобный для представления формат."""
        serializer = RecipeSerializer(recipes_list, many=True)
        return serializer.data


class AddIngredientSerializer(ModelSerializer):
    """
    Сериализатор для поля ingredient модели Recipe - создание ингредиентов.
    """

    id = PrimaryKeyRelatedField(queryset=Ingredient.objects.all())
    amount = IntegerField()

    class Meta:
        model = RecipeIngredient
        fields = ("id", "amount")

    def validate_amount(self, value):
        if value <= 0:
            raise ValidationError(
                {"amount": "Количество должно быть больше 0!"}
            )
        return value


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
        if not value:
            raise ValidationError({"ingredients": "Нужно выбрать ингредиент!"})
        ingredient_ids = [ingredient["id"] for ingredient in value]
        if len(ingredient_ids) != len(set(ingredient_ids)):
            raise ValidationError(
                {"ingredients": "Ингредиенты не должны повторяться!"}
            )
        return value

    def validate_tags(self, value):
        if not value:
            raise ValidationError({"tags": "Нужно выбрать тег!"})
        if len(value) != len(set(value)):
            raise ValidationError({"tags": "Теги повторяются!"})
        return value

    def to_representation(self, instance):
        # Используем сериализатор для получения рецепта
        return RecipeListSerializer(instance).data

    def add_tags_ingredients(self, ingredients, tags, model):
        recipe_ingredients = [
            RecipeIngredient(
                recipe=model,
                ingredient=ingredient["id"],
                amount=ingredient["amount"],
            )
            for ingredient in ingredients
        ]

        # Используем bulk_create для создания всех объектов за один запрос
        RecipeIngredient.objects.bulk_create(recipe_ingredients)
        model.tags.set(tags)

    def create(self, validated_data):
        ingredients = validated_data.pop("ingredients")
        tags = validated_data.pop("tags")
        recipe = super().create(validated_data)
        self.add_tags_ingredients(ingredients, tags, recipe)
        return recipe

    def update(self, instance, validated_data):
        ingredients = validated_data.pop("ingredients", None)
        tags = validated_data.pop("tags", None)

        if ingredients is None:
            raise ValidationError(
                {"ingredients": "Нужно выбрать ингредиенты!"}
            )
        if tags is None:
            raise ValidationError({"tags": "Нужно выбрать теги!"})

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

    def get_recipes_count(self, obj):
        """Получение количества рецептов автора."""
        return obj.author.recipes.count()

    def get_avatar(self, obj):
        """Получение URL аватара автора."""
        return obj.author.avatar.url if obj.author.avatar else None

    def get_is_subscribed(self, obj):
        """Проверка, подписан ли пользователь на автора."""
        return Subscription.objects.filter(
            user=obj.user, author=obj.author
        ).exists()


class BaseRecipeSerializer(ModelSerializer):
    """Общий базовый сериализатор для рецептов в избранном и корзине."""

    id = IntegerField()
    name = CharField()
    image = Base64ImageField(max_length=None, use_url=False)
    cooking_time = IntegerField()

    class Meta:
        abstract = True
        fields = ("id", "name", "image", "cooking_time")


class FavoritesSerializer(BaseRecipeSerializer):
    """Сериализатор для списка избранных рецептов."""

    class Meta(BaseRecipeSerializer.Meta):
        model = Favorites
        fields = BaseRecipeSerializer.Meta.fields
        validators = [
            UniqueTogetherValidator(
                queryset=Favorites.objects.all(), fields=("user", "recipe")
            )
        ]


class ShoppingCartSerializer(BaseRecipeSerializer):
    """Сериализатор для списка покупок."""

    class Meta(BaseRecipeSerializer.Meta):
        model = ShoppingCart
        fields = BaseRecipeSerializer.Meta.fields
        validators = [
            UniqueTogetherValidator(
                queryset=ShoppingCart.objects.all(), fields=("user", "recipe")
            )
        ]


class ShortRecipeURLSerializer(ModelSerializer):
    "Сереализатор короткой ссылки рецепта."
    short_link = SerializerMethodField()

    class Meta:
        model = Recipe
        fields = ["short_link"]

    def get_short_link(self, obj: ShortRecipeURL):
        request = self.context.get("request")
        short_code = obj.short_url.short_code
        return request.build_absolute_uri(f"/s/{short_code}/")

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation["short-link"] = representation.pop("short_link")
        return representation
