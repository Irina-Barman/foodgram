from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator
from django.db import models


User = get_user_model()


class Tag(models.Model):
    """Модель для тэгов."""

    name = models.CharField(
        "Тэг",
        max_length=settings.MAX_TAG_LENGTH,
        unique=True,
    )
    slug = models.SlugField(
        max_length=settings.MAX_TAG_SLUG_LENGTH,
        verbose_name="Имя для ссылки",
        null=False,
        unique=True,
    )

    class Meta:
        verbose_name = "Тэг"
        verbose_name_plural = "Тэги"
        ordering = ("name",)

    def __str__(self):
        return self.name


class Ingredient(models.Model):
    """Модель для ингредиентов."""

    name = models.CharField(
        "Ингредиент",
        max_length=settings.MAX_INGREDIENTS_NAME_LENGTH,
    )
    measurement_unit = models.CharField(
        "Единица измерения",
        max_length=settings.MAX_UNIT_LENGTH,
        help_text="Укажите единицу измерения",
    )

    class Meta:
        verbose_name = "Ингредиент"
        verbose_name_plural = "Ингредиенты"
        ordering = ("name",)

    def __str__(self):
        return f"{self.name}: {self.measurement_unit}"


class Recipe(models.Model):
    """Модель рецептов."""

    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="recipes",
        verbose_name="Автор рецепта",
    )
    name = models.CharField(
        "Название",
        max_length=settings.MAX_RECIPES_NAME_LENGTH,
    )
    image = models.ImageField(
        "Изображение",
    )
    text = models.TextField(
        "Описание",
    )
    ingredients = models.ManyToManyField(
        Ingredient,
        verbose_name="Список ингредиентов",
        through="AmountIngredient",
        related_name="recipes",
    )
    tags = models.ManyToManyField(
        Tag,
        related_name="recipes",
        verbose_name="Тег",
    )
    cooking_time = models.PositiveSmallIntegerField(
        "Время приготовления (в минутах)",
        validators=[
            MinValueValidator(
                settings.MIN_TIME,
                message=(
                    f"Время приготовления не может быть меньше "
                    f"{settings.MIN_TIME}",
                ),
            ),
        ],
    )

    class Meta:
        verbose_name = "Рецепт"
        verbose_name_plural = "Рецепты"

    def __str__(self):
        return self.name


class AmountIngredient(models.Model):
    """Модель количества ингредиентов для рецепта."""

    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        verbose_name="Рецепт",
        related_name="amount_ingredient",
    )
    ingredients = models.ForeignKey(
        Ingredient,
        on_delete=models.CASCADE,
        verbose_name="Ингредиент",
        related_name="amount_ingredient",
    )
    amount = models.PositiveSmallIntegerField(
        verbose_name="Количество",
        default=0,
        validators=[
            MinValueValidator(
                settings.MIN_INGREDIENT_AMOUNT,
                message=(
                    f"Количество не может быть меньше "
                    f"{settings.MIN_INGREDIENT_AMOUNT}",
                ),
            ),
        ],
    )

    class Meta:
        verbose_name = "Ингредиент"
        verbose_name_plural = "Количество ингредиентов"

    def __str__(self):
        return f"{self.amount} {self.ingredients}"


class Favorite(models.Model):
    """Модель списка избранного."""

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name="Пользователь",
        related_name="favorite",
    )
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        verbose_name="Рецепт",
        related_name="favorite",
    )

    class Meta:
        verbose_name = "Избранный рецепт"
        verbose_name_plural = "Избранные рецепты"


class ShoppingCart(models.Model):
    """Модель списка покупок."""

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name="Пользователь",
        related_name="shopping_cart",
    )
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        verbose_name="Рецепт",
        related_name="shopping_cart",
    )

    class Meta:
        verbose_name = "Список покупок"
        verbose_name_plural = "Списки покупок"
