import re
from base64 import b64decode

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.db import transaction
from django.shortcuts import get_object_or_404
from djoser.serializers import UserCreateSerializer, UserSerializer
from recipes.models import (
    Favorites,
    Ingredient,
    Recipe,
    RecipeIngredient,
    ShoppingCart,
    Tag,
)
from rest_framework.exceptions import ValidationError
from rest_framework.serializers import (
    CharField,
    Field,
    ImageField,
    IntegerField,
    ModelSerializer,
    PrimaryKeyRelatedField,
    ReadOnlyField,
    SerializerMethodField,
)
from rest_framework.validators import UniqueTogetherValidator
from users.models import Subscription

User = get_user_model()


class Base64ImageField(ImageField):
    def to_internal_value(self, data):
        if isinstance(data, str) and data.startswith("data:image"):
            format, imgstr = data.split(";base64,")
            ext = format.split("/")[-1]
            data = ContentFile(b64decode(imgstr), name="temp." + ext)

        return super().to_internal_value(data)


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
        fields = ["id", "name", "slug"]


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
    """Сериализатор для ингредиентов в рецепте."""

    id = PrimaryKeyRelatedField(queryset=Ingredient.objects.all())
    name = CharField(source="ingredient.name", read_only=True)
    measurement_unit = CharField(
        source="ingredient.measurement_unit", read_only=True
    )
    amount = IntegerField()

    class Meta:
        model = RecipeIngredient
        fields = ["id", "name", "measurement_unit", "amount"]


class RecipeSerializer(ModelSerializer):
    """Сериализатор модели рецепта."""

    image = Base64ImageField()
    tags = TagSerializer(many=True, read_only=True)
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
        request = self.context.get("request")
        ingredients = self.initial_data.get("ingredients", [])
        tags = self.initial_data.get("tags", [])
        name = data.get("name")
        cooking_time = data.get("cooking_time")
        image = data.get("image")

        if not request.user.is_authenticated:
            raise ValidationError(
                {"detail": "Пользователь не авторизован"}, code=401
            )

        if not ingredients:
            raise ValidationError(
                {"ingredients": "В рецепте отсутствуют ингредиенты"}
            )

        if not tags:
            raise ValidationError({"tags": "В рецепте отсутствуют теги"})

        if not image:
            raise ValidationError({"image": "Поле image не может быть пустым"})

        # Проверка уникальности тегов
        tag_slugs = {tag.get("slug") for tag in tags}
        existing_tags = Tag.objects.filter(slug__in=tag_slugs)
        if len(existing_tags) != len(tag_slugs):
            raise ValidationError({"tags": "Некоторые теги не существуют"})

        # Проверка ингредиентов
        ingredient_ids = set()
        for ingredient_item in ingredients:
            ingredient_id = ingredient_item.get("id")
            amount = ingredient_item.get("amount")

            if ingredient_id in ingredient_ids:
                raise ValidationError("Ингредиент уже добавлен в рецепт")

            if not Ingredient.objects.filter(id=ingredient_id).exists():
                raise ValidationError(
                    {"ingredients": f"Ингредиента с id {ingredient_id} нет"}
                )

            try:
                amount = int(amount)
                if amount <= 0:
                    raise ValidationError(
                        "Количество ингредиента должно быть положительным"
                    )
            except (ValueError, TypeError):
                raise ValidationError(
                    "Количество ингредиента должно быть целым числом"
                )

            ingredient_ids.add(ingredient_id)

        # Проверка времени приготовления
        try:
            cooking_time = int(cooking_time)
            if cooking_time <= 0:
                raise ValidationError(
                    "Время должно быть положительным целым числом"
                )
        except (ValueError, TypeError):
            raise ValidationError(
                "Время приготовления должно быть целым числом"
            )

        # Проверка на существование рецепта с таким же именем
        recipe_id = self.context.get("view").kwargs.get(
            "pk"
        )  # Получаем ID рецепта из URL
        if recipe_id:
            # Если это обновление, пропускаем проверку
            existing_recipe = (
                Recipe.objects.filter(name=name, author=request.user)
                .exclude(id=recipe_id)
                .exists()
            )
        else:
            # Если это создание, просто проверяем
            existing_recipe = Recipe.objects.filter(
                name=name, author=request.user
            ).exists()

        if existing_recipe:
            raise ValidationError(
                {"name": "Рецепт с таким именем уже существует"}
            )

        return data

    def create_ingredients(self, ingredients, recipe):
        """Добавление ингредиентов."""
        for ingredient in ingredients:
            ingredient_instance = get_object_or_404(
                Ingredient, id=ingredient["id"]
            )
            amount = ingredient["amount"]
            existing_recipe_ingredient = RecipeIngredient.objects.filter(
                recipe=recipe,
                ingredients=ingredient_instance,
            ).first()

            if existing_recipe_ingredient:
                amount += existing_recipe_ingredient.amount
                existing_recipe_ingredient.amount = amount
                existing_recipe_ingredient.save()
            else:
                RecipeIngredient.objects.create(
                    recipe=recipe,
                    ingredients=ingredient_instance,
                    amount=amount,
                )

    def create_tags(self, tags, recipe):
        """Добавление тегов."""
        tag_slugs = [tag["slug"] for tag in tags]
        existing_tags = Tag.objects.filter(slug__in=tag_slugs)
        recipe.tags.set(existing_tags)

    @transaction.atomic
    def create(self, validated_data):
        """Создание рецепта."""
        tags_data = validated_data.pop("tags", [])
        ingredients_data = validated_data.pop("ingredients", [])
        image = validated_data.pop("image", None)

        recipe = Recipe.objects.create(image=image, **validated_data)
        self.create_ingredients(ingredients_data, recipe)
        self.create_tags(
            tags_data, recipe
        )  # Добавляем вызов для создания тегов
        return recipe

    @transaction.atomic
    def update(self, recipe, validated_data):
        """Обновление существующего рецепта."""
        ingredients = validated_data.pop("ingredients", [])
        tags = validated_data.pop("tags", [])

        # Удаляем старые ингредиенты и теги
        RecipeIngredient.objects.filter(recipe=recipe).delete()
        recipe.tags.clear()

        # Создаем новые ингредиенты и теги
        self.create_ingredients(ingredients, recipe)
        self.create_tags(tags, recipe)  # Обновляем теги

        return super().update(recipe, validated_data)


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


class RecipeSubscriptionUserField(Field):
    """Сериализатор для вывода рецептов в подписках."""

    def get_attribute(self, instance):
        """Получение списка рецептов, принадлежащих автору."""
        return Recipe.objects.filter(author=instance.author)

    def to_representation(self, recipes_list):
        """Преобразование списка в удобный для представления формат."""
        recipes_data = []
        for recipes in recipes_list:
            recipes_data.append(
                {
                    "id": recipes.id,
                    "name": recipes.name,
                    "image": recipes.image.url if recipes.image else None,
                    "cooking_time": recipes.cooking_time,
                }
            )
        return recipes_data


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
        fields = ["id", "name", "image", "cooking_time"]
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
        fields = ["id", "name", "image", "cooking_time"]
        validators = [
            UniqueTogetherValidator(
                queryset=ShoppingCart.objects.all(), fields=("user", "recipe")
            )
        ]
