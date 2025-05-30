import random
import string

from django.contrib.auth import get_user_model
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from api.constants import (
    MAX_INGREDIENTS_NAME_LENGTH,
    MAX_RECIPES_NAME_LENGTH,
    MAX_TAG_LENGTH,
    MAX_TAG_SLUG_LENGTH,
    MAX_TIME,
    MAX_UNIT_LENGTH,
    MAX_VALUE,
    MIN_TIME,
    MIN_VALUE,
    URL_LENGTH,
)

User = get_user_model()


class Tag(models.Model):
    """Модель тэга."""

    name = models.CharField(
        max_length=MAX_TAG_LENGTH,
        unique=True,
        verbose_name="Имя тэга",
    )
    slug = models.SlugField(
        max_length=MAX_TAG_SLUG_LENGTH,
        unique=True,
        verbose_name="Имя для ссылки",
    )

    class Meta:
        verbose_name = "Тег"
        verbose_name_plural = "Теги"

    def __str__(self):
        return self.name


class Ingredient(models.Model):
    """Модель ингредиента."""

    name = models.CharField(
        max_length=MAX_INGREDIENTS_NAME_LENGTH,
        unique=True,
        verbose_name="Название ингредиента",
    )
    measurement_unit = models.CharField(
        max_length=MAX_UNIT_LENGTH,
        verbose_name="Единица измерения ингредиента",
        help_text="Укажите единицу измерения",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("name", "measurement_unit"), name="unique_ingredient"
            )
        ]
        verbose_name = "Ингредиент"
        verbose_name_plural = "Ингредиенты"

    def __str__(self):
        return f"{self.name} ({self.measurement_unit})"


class Recipe(models.Model):
    """Модель рецептов."""

    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="recipes",
        verbose_name="Автор рецепта",
    )
    name = models.CharField(
        max_length=MAX_RECIPES_NAME_LENGTH,
        verbose_name="Название рецепта",
    )
    image = models.ImageField(
        upload_to="recipes/images/", verbose_name="Изображение блюда"
    )
    text = models.TextField(
        verbose_name="Описание рецепта",
    )
    ingredients = models.ManyToManyField(
        Ingredient,
        through="RecipeIngredient",
        related_name="recipes",
        verbose_name="Список ингредиентов",
    )
    tags = models.ManyToManyField(
        Tag,
        related_name="recipes",
        verbose_name="Тег",
        through="RecipeTag",
    )
    cooking_time = models.PositiveSmallIntegerField(
        verbose_name="Время приготовления (в минутах)",
        validators=[
            MinValueValidator(
                MIN_TIME,
                message=(
                    f"Время приготовления не может быть меньше {MIN_TIME}",
                ),
            ),
            MaxValueValidator(
                MAX_TIME,
                message=(
                    f"Время приготовления не может быть больше {MAX_TIME}",
                ),
            ),
        ],
    )
    pub_date = models.DateTimeField(
        auto_now_add=True, verbose_name="Дата публикации"
    )

    class Meta:
        ordering = ("-pub_date",)
        verbose_name = "Рецепт"
        verbose_name_plural = "Рецепты"

    def __str__(self):
        return self.name


class RecipeTag(models.Model):
    """Промежуточная модель для связи рецепта и тега."""

    recipe = models.ForeignKey(
        Recipe, on_delete=models.CASCADE, related_name="recipe_tags"
    )
    tag = models.ForeignKey(Tag, on_delete=models.CASCADE)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("recipe", "tag"), name="recipetag_unique"
            )
        ]
        verbose_name = "Тег рецепта"
        verbose_name_plural = "Теги рецепта"

    def __str__(self):
        return f"Рецепт {self.recipe} имеет тег {self.tag}"


class RecipeIngredient(models.Model):
    """Промежуточная модель для связи рецепта и ингредиента."""

    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name="recipe_ingredients",
        verbose_name="Рецепт",
    )
    ingredient = models.ForeignKey(
        Ingredient,
        on_delete=models.CASCADE,
        related_name="recipe_ingredients",
        verbose_name="Ингредиент",
    )
    amount = models.PositiveSmallIntegerField(
        verbose_name="Количество",
        validators=[
            MaxValueValidator(MAX_VALUE),
            MinValueValidator(MIN_VALUE),
        ],
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("recipe", "ingredient"), name="recipeingredient_unique"
            )
        ]
        verbose_name = "Ингредиент рецепта"
        verbose_name_plural = "Ингредиенты рецепта"

    def __str__(self):
        return f"Рецепт {self.recipe} содержит {self.ingredient}"


class Favorites(models.Model):
    """Модель избранного."""

    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name="in_favorites",
        verbose_name="Рецепт",
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="favorites",
        verbose_name="Пользователь",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("recipe", "user"), name="userfavorites_unique"
            )
        ]
        verbose_name = "Избранный рецепт"
        verbose_name_plural = "Избранные рецепты"

    def __str__(self):
        return f"Рецепт {self.recipe} в избранном {self.user}"


class ShoppingCart(models.Model):
    """Модель списка продуктов."""

    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name="shopping_cart",
        verbose_name="Рецепт",
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="shopping_cart",
        verbose_name="Пользователь",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("recipe", "user"), name="usershoppingcart_unique"
            )
        ]
        verbose_name = "Список покупок"
        verbose_name_plural = "Списки покупок"

    def __str__(self):
        return f"Рецепт {self.recipe} в корзине {self.user}"


def generate_short_code(length=URL_LENGTH):
    characters = string.ascii_letters + string.digits
    return "".join(random.choice(characters) for _ in range(length))


class ShortRecipeURL(models.Model):
    recipe = models.OneToOneField(
        Recipe,
        on_delete=models.CASCADE,
        related_name="short_url",
        verbose_name="Рецепт",
    )
    short_code = models.CharField(
        max_length=6,
        unique=True,
        default=generate_short_code,
        verbose_name="Код",
    )
    created_at = models.DateTimeField(
        auto_now_add=True, verbose_name="Время создания"
    )

    class Meta:
        verbose_name = "Короткая ссылка"
        verbose_name_plural = "Короткие ссылки"

    def __str__(self):
        return f"{self.short_code} -> {self.recipe.name}"
