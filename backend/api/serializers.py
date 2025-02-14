from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from djoser.serializers import UserCreateSerializer, UserSerializer
from drf_extra_fields.fields import Base64ImageField
from recipes.models import (
    AmountIngredient,
    Favorite,
    Ingredient,
    Recipe,
    ShoppingCart,
    Tag,
)
from rest_framework.serializers import (
    CharField,
    EmailField,
    IntegerField,
    ModelSerializer,
    PrimaryKeyRelatedField,
    ReadOnlyField,
    SerializerMethodField,
    ValidationError,
)
from rest_framework.validators import UniqueValidator
from users.models import Subscription


User = get_user_model()


class CreateUserSerializer(UserCreateSerializer):
    """Сериализатор для регистрации пользователей."""

    username = CharField(
        validators=[UniqueValidator(queryset=User.objects.all())]
    )
    email = EmailField(
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


class UserSerializer(UserSerializer):
    """Сериализатор пользователей."""

    is_subscribed = SerializerMethodField()

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
        return (
            user.is_authenticated
            and Subscription.objects.filter(user=user, author=obj).exists()
        )


class TagSerializer(ModelSerializer):
    """Сериализатор для тэгов."""

    class Meta:
        model = Tag
        fields = "__all__"


class IngredientSerializer(ModelSerializer):
    """Сериализатор для ингредиентов."""

    class Meta:
        model = Ingredient
        fields = "__all__"


class IngredientCreateSerializer(ModelSerializer):
    """Сериализатор для добавления ингредиентов при создании рецепта."""

    id = IntegerField()

    class Meta:
        model = AmountIngredient
        fields = ("id", "amount")


class ReadIngredientsInRecipeSerializer(ModelSerializer):
    """Сериализатор для чтения ингредиентов в рецепте."""

    id = ReadOnlyField(source="ingredients.id")
    name = ReadOnlyField(source="ingredients.name")
    measurement_unit = ReadOnlyField(source="ingredients.measurement_unit")

    class Meta:
        model = AmountIngredient
        fields = (
            "id",
            "name",
            "measurement_unit",
            "amount",
        )


class RecipeSerializer(ModelSerializer):
    """Сериализатор для рецептов."""

    author = UserSerializer(read_only=True)
    ingredients = SerializerMethodField()
    tags = TagSerializer(many=True)
    is_in_shopping_cart = SerializerMethodField()
    is_favorited = SerializerMethodField()
    image = Base64ImageField()

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
        user = self.context.get("request").user
        return (
            user.is_authenticated
            and ShoppingCart.objects.filter(user=user, recipe=obj).exists()
        )

    def get_is_favorited(self, obj):
        user = self.context.get("request").user
        return (
            user.is_authenticated
            and Favorite.objects.filter(user=user, recipe=obj).exists()
        )

    @staticmethod
    def get_ingredients(obj):
        ingredients = AmountIngredient.objects.filter(recipe=obj)
        return ReadIngredientsInRecipeSerializer(ingredients, many=True).data


class RecipeCreateSerializer(ModelSerializer):
    """Сериализатор для создания рецептов."""

    ingredients = IngredientCreateSerializer(many=True)
    tags = PrimaryKeyRelatedField(queryset=Tag.objects.all(), many=True)
    image = Base64ImageField()
    name = CharField(max_length=200)
    cooking_time = IntegerField()
    author = UserSerializer(read_only=True)

    class Meta:
        model = Recipe
        fields = (
            "id",
            "ingredients",
            "tags",
            "image",
            "name",
            "text",
            "cooking_time",
            "author",
        )

    def create_ingredients(self, ingredients, recipe):
        for ingredient in ingredients:
            amount = ingredient["amount"]
            ingredient_instance = get_object_or_404(
                Ingredient, id=ingredient["id"]
            )
            AmountIngredient.objects.update_or_create(
                recipe=recipe,
                ingredients=ingredient_instance,
                defaults={"amount": amount},
            )

    def create(self, validated_data):
        ingredients_data = validated_data.pop("ingredients")
        tags_data = validated_data.pop("tags")
        recipe = Recipe.objects.create(
            author=self.context["request"].user, **validated_data
        )

        # Создаем связи для тегов
        recipe.tags.set(tags_data)

        # Создаем ингредиенты
        self.create_ingredients(ingredients_data, recipe)

        return recipe

    def validate_cooking_time(self, value):
        if value <= 0:
            raise ValidationError(
                "Время приготовления должно быть положительным."
            )
        return value

    def validate_ingredients(self, value):
        if not value:
            raise ValidationError(
                "Необходимо указать хотя бы один ингредиент."
            )
        return value


class SubscriptionSerializer(ModelSerializer):
    """Сериализатор для подписок на авторов рецептов."""

    recipes = RecipeSerializer(many=True, read_only=True)
    email = ReadOnlyField(source="author.email")
    id = ReadOnlyField(source="author.id")
    username = ReadOnlyField(source="author.username")

    class Meta:
        model = Subscription
        fields = ("id", "email", "username", "recipes")

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation["recipes"] = RecipeSerializer(
            instance.recipes.all(), many=True
        ).data
        return representation
