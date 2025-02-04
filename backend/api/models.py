from django.db import models
from django.core.validators import MinValueValidator
from foodgram_project.settings import (
    MAX_RECIPES_NAME_LENGTH,
    MAX_INGREDIENTS_NAME_LENGTH,
    MAX_TAG_LENGTH,
    MAX_MEASUREMENT_UNIT_LENGTH,
    MIN_TIME,
)


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
class Ingredients(models.Model):
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
class Recipes(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(
        "Название рецепта", max_length=MAX_RECIPES_NAME_LENGTH
    )
    ingredients = models.ManyToManyField(
        Ingredients,
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
    image = models.ImageField(
        "Ссылка на изображение", upload_to=""  # указать!!!
    )
    author = models.ForeignKey(
        "CustomUser ",
        on_delete=models.CASCADE,
        verbose_name="Автор",
        related_name="recipes",
    )
    pub_date = models.DateTimeField(auto_now_add=True)
    tags = models.ManyToManyField(
        "Tag",
        verbose_name="Теги",
    )


# Связующая модель ингридиенты для рецепта
class RecipeIngredients(models.Model):
    # id = models.AutoField(primary_key=True)
    # ingredients =
    # recipes =
    # amount =
    pass


# Модель список покупок
class Shopping_cart(models.Model):
    # id = models.AutoField(primary_key=True)
    # user =
    # recipes =
    pass


# Модель избранное
class Favorite(models.Model):
    # id = models.AutoField(primary_key=True)
    # user =
    # recipes =
    pass


# Модель подписки
class Subscriptions(models.Model):
    # id = models.AutoField(primary_key=True)
    # user =
    # author =
    pass
