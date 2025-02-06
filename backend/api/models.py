from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.core.validators import MinValueValidator, RegexValidator
from django.db import models

from users.validators import validate_username_not_me


class CustomUser(AbstractUser):
    """Кастомный класс User."""
    id = models.AutoField(primary_key=True)
    username = models.CharField(
        max_length=settings.MAX_USERNAME_LENGTH,
        verbose_name="Имя пользователя",
        unique=True,
        validators=[
            UnicodeUsernameValidator(),
            validate_username_not_me,
        ],
    )
    email = models.EmailField(
        max_length=settings.MAX_EMAIL_LENGTH,
        verbose_name="Email",
        unique=True,
    )
    first_name = models.CharField(
        max_length=settings.MAX_NAME_LENGTH, verbose_name="Имя", blank=True
    )
    last_name = models.CharField(
        max_length=settings.MAX_NAME_LENGTH, verbose_name="Фамилия", blank=True
    )

    class Meta:
        verbose_name = "Пользователь"
        verbose_name_plural = "Пользователи"
        ordering = ("id",)
        constraints = [
            models.UniqueConstraint(
                fields=["username", "email"],
                name="unique_username_email_constraint",
            )
        ]

    @property
    def is_admin(self):
        return self.is_superuser or self.is_admin


class Tag(models.Model):
    """Модель тег."""
    id = models.AutoField(primary_key=True)
    name = models.CharField(
        "Название тега", max_length=settings.MAX_TAG_LENGTH, unique=True
    )
    slug = models.SlugField(
        "Слаг тега", max_length=settings.MAX_TAG_LENGTH, unique=True
    )

    class Meta:
        ordering = ["id"]
        verbose_name = "Тег"
        verbose_name_plural = "Теги"

    def __str__(self):
        return self.name


class Ingredient(models.Model):
    """Модель Ингредиенты."""
    id = models.AutoField(primary_key=True)
    name = models.CharField(
        "Название ингридиента", max_length=settings.MAX_INGREDIENTS_NAME_LENGTH
    )
    measurement_unit = models.CharField(
        "Единица измерения", max_length=settings.MAX_MEASUREMENT_UNIT_LENGTH
    )

    class Meta:
        ordering = ["id"]
        verbose_name = "Ингредиент"
        verbose_name_plural = "Ингредиенты"
        constraints = [
            models.UniqueConstraint(
                fields=["name", "measurement_unit"], name="unique_ingredient"
            )
        ]

    def __str__(self):
        return f"{self.name} {self.measurement_unit}"


class Recipe(models.Model):
    """Модель рецепты."""

    id = models.AutoField(primary_key=True)
    name = models.CharField(
        "Название рецепта", max_length=settings.MAX_RECIPE_NAME_LENGTH
    )
    ingredients = models.ManyToManyField(
        Ingredient,
        through="RecipeIngredient",
        verbose_name="Ингредиенты",
        related_name="recipes",
    )
    cooking_time = models.PositiveIntegerField(
        "Время приготовления в мин",
        validators=[
            MinValueValidator(
                settings.MIN_TIME,
                f"Время приготовления не может быть меньше {settings.MIN_TIME} минут",
            ),
        ],
    )
    text = models.TextField("Описание рецепта")
    image = models.ImageField("Изображение")
    author = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        verbose_name="Автор",
        related_name="recipes",
    )
    pub_date = models.DateTimeField(auto_now_add=True)
    tags = models.ManyToManyField(
        Tag,
        verbose_name="Теги",
    )


class RecipeIngredient(models.Model):
    """Связующая модель ингридиенты для рецепта."""

    id = models.AutoField(primary_key=True)
    ingredient = models.ForeignKey(
        Ingredient,
        on_delete=models.CASCADE,
    )
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
    )
    amount = models.PositiveIntegerField(
        "Количество",
        validators=[
            RegexValidator(r"^[0-9]+$", "Значение должно быть целым числом")
        ],
    )

    class Meta:
        verbose_name = "Ингредиент"
        verbose_name_plural = "Ингредиенты"
        constraints = [
            models.UniqueConstraint(
                fields=["recipe", "ingredient"],
                name="unique_ingredients_recipe",
            )
        ]

    def __str__(self):
        return f"{self.recipe.name}:{self.ingredient.name}"


class ShoppingCart(models.Model):
    """Модель список покупок."""

    id = models.AutoField(primary_key=True)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE)

    class Meta:
        verbose_name = "Список покупок"
        verbose_name_plural = "Списки покупок"
        constraints = [
            models.UniqueConstraint(
                fields=["user", "recipe"], name="unique_recipe_list"
            )
        ]

    def __str__(self):
        return f"Список покупок пользователя {self.user.username}"


class Favorite(models.Model):
    """Модель избранное."""

    id = models.AutoField(primary_key=True)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE)

    class Meta:
        verbose_name = "Список избранного"
        verbose_name_plural = "Списки избранного"
        constraints = [
            models.UniqueConstraint(
                fields=["user", "recipe"], name="unique_recipe_favorites"
            )
        ]

    def __str__(self):
        return f"Список избранных рецептов {self.user.username}"


class Subscription(models.Model):
    """Модель подписки."""

    id = models.AutoField(primary_key=True)
    user = models.ForeignKey(
        CustomUser,
        verbose_name="Подписчик",
        on_delete=models.CASCADE,
        related_name="follower",
    )
    author = models.ForeignKey(
        CustomUser,
        verbose_name="Автор рецепта",
        on_delete=models.CASCADE,
        related_name="following",
    )

    class Meta:
        verbose_name = "Подписка"
        verbose_name_plural = "Подписки"
        constraints = [
            models.UniqueConstraint(
                fields=["user", "author"], name="unique_follow"
            ),
            models.CheckConstraint(
                name="user_is_not_author",
                check=~models.Q(user=models.F("author")),
            ),
        ]

    def __str__(self):
        return f"{self.user.username} подписан на {self.author.username}"
