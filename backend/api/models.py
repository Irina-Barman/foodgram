from django.db.models import F, Q
from django.db import models
from django.core.validators import MinValueValidator, RegexValidator
from foodgram_project.settings import (
    MAX_RECIPES_NAME_LENGTH,
    MAX_INGREDIENTS_NAME_LENGTH,
    MAX_TAG_LENGTH,
    MAX_MEASUREMENT_UNIT_LENGTH,
    MIN_TIME,
)
from users.models import CustomUser


# Модель тег
class Tag(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(
        "Название тега", max_length=MAX_TAG_LENGTH, unique=True
    )
    slug = models.SlugField(
        "Слаг тега", max_length=MAX_TAG_LENGTH, unique=True
    )

    class Meta:
        ordering = ["id"]
        verbose_name = "Тег"
        verbose_name_plural = "Теги"

    def __str__(self):
        return self.name


# Модель Ингредиенты
class Ingredient(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(
        "Название ингридиента", max_length=MAX_INGREDIENTS_NAME_LENGTH
    )
    measurement_unit = models.CharField(
        "Единица измерения", max_length=MAX_MEASUREMENT_UNIT_LENGTH
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


# Модель рецепты
class Recipe(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(
        "Название рецепта", max_length=MAX_RECIPES_NAME_LENGTH
    )
    ingredients = models.ManyToManyField(
        Ingredient,
        through="RecipeIngredients",
        verbose_name="Ингредиенты",
        related_name="recipes",
    )
    cooking_time = models.PositiveIntegerField(
        "Время приготовления в мин",
        validators=[
            MinValueValidator(
                MIN_TIME,
                f"Время приготовления не может быть меньше {MIN_TIME} минуты",
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


# Связующая модель ингридиенты для рецепта
class RecipeIngredients(models.Model):
    id = models.AutoField(primary_key=True)
    ingredients = models.ForeignKey(
        Ingredient,
        on_delete=models.CASCADE,
    )
    recipes = models.ForeignKey(
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
                fields=["recipes", "ingredients"],
                name="unique_ingredients_recipes",
            )
        ]

    def __str__(self):
        return f"{self.recipes.name}:{self.ingredients.name}"


# Модель список покупок
class Shopping_cart(models.Model):
    id = models.AutoField(primary_key=True)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    recipes = models.ForeignKey(Recipe, on_delete=models.CASCADE)

    class Meta:
        verbose_name = "Список покупок"
        verbose_name_plural = "Списки покупок"
        constraints = [
            models.UniqueConstraint(
                fields=["user", "recipes"], name="unique_recipes_list"
            )
        ]

    def __str__(self):
        return f"Список покупок пользователя {self.user.username}"


# Модель избранное
class Favorite(models.Model):
    id = models.AutoField(primary_key=True)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    recipes = models.ForeignKey(Recipe, on_delete=models.CASCADE)

    class Meta:
        verbose_name = "Список избранного"
        verbose_name_plural = "Списки избранного"
        constraints = [
            models.UniqueConstraint(
                fields=["user", "recipes"], name="unique_recipes_favorites"
            )
        ]

    def __str__(self):
        return f"Список избранных рецептов {self.user.username}"

    pass


# Модель подписки
class Subscription(models.Model):
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
        constraints = [
            models.UniqueConstraint(
                fields=["user", "author"],
                name="Вы уже подписаны на данного автора",
            ),
            models.CheckConstraint(
                check=~Q(user=F("author")), name="Нельзя подписаться на себя"
            ),
        ]
        ordering = ["-id"]
        verbose_name = "Подписка"
        verbose_name_plural = "Подписки"

        def __str__(self):
            return f"{self.user} подписался на {self.author}"
