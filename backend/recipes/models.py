from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

User = get_user_model()


class Tag(models.Model):
    """Модель тэга."""
    name = models.CharField(
        max_length=getattr(settings, "MAX_TAG_LENGTH", 32),
        unique=True,
        verbose_name="Имя тэга",
    )
    slug = models.SlugField(
        max_length=getattr(settings, "MAX_TAG_SLUG_LENGTH", 200),
        unique=True,
        verbose_name="Имя для ссылки",
    )

    def __str__(self):
        return self.name


class Ingredient(models.Model):
    """Модель ингредиента."""
    name = models.CharField(
        max_length=getattr(settings, "MAX_INGREDIENTS_NAME_LENGTH", 128),
        unique=True,
        verbose_name="Название ингредиента",
    )
    measurement_unit = models.CharField(
        max_length=getattr(settings, "MAX_UNIT_LENGTH", 40),
        verbose_name="Единица измерения ингредиента",
        help_text="Укажите единицу измерения",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["name", "measurement_unit"], name="unique_ingredient"
            )
        ]

    def __str__(self):
        return self.name


class Recipe(models.Model):
    """Модель рецептов."""
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="recipes",
        verbose_name="Автор рецепта",
    )
    name = models.CharField(
        max_length=getattr(settings, "MAX_RECIPES_NAME_LENGTH", 256),
        verbose_name="Название рецепта",
    )
    image = models.ImageField(
        upload_to="recipes/", verbose_name="Изображение блюда"
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
                getattr(settings, "MIN_TIME", 1),
                message=(
                    f"Время приготовления не может быть меньше "
                    f"{(getattr(settings, 'MIN_TIME', 1),)}",
                ),
            ),
        ],
    )
    pub_date = models.DateTimeField(
        auto_now_add=True, verbose_name="Дата публикации"
    )

    class Meta:
        ordering = ("-pub_date",)

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
                fields=["recipe", "tag"], name="recipetag_unique"
            )
        ]

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
        validators=[MaxValueValidator(1000), MinValueValidator(1)],
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["recipe", "ingredient"], name="recipeingredient_unique"
            )
        ]

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
                fields=["recipe", "user"], name="userfavorites_unique"
            )
        ]

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
                fields=["recipe", "user"], name="usershoppingcart_unique"
            )
        ]

    def __str__(self):
        return f"Рецепт {self.recipe} в корзине {self.user}"
