from django.db import models
from django.core.validators import MinValueValidator
from foodgram_project.settings import MAX_NAME_LENGTH


# Модель тег
class Tag(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(
        "Название тега", max_length=MAX_NAME_LENGTH, unique=True
    )
    slug = models.SlugField(
        "Слаг тега", max_length=MAX_NAME_LENGTH, unique=True
    )

    class Meta:
        ordering = ["id"]
        verbose_name = "Тег"
        verbose_name_plural = "Теги"

    def __str__(self):
        return self.name


# Модель Ингредиенты
class Ingredients(models.Model):
    pass


# Модель рецепты
class Recipes(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField("Название рецепта", max_length=MAX_NAME_LENGTH)
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
                1, "Время приготовления не может быть меньше 1 минуты"
            ),
        ],
    )
    text = models.TextField("Описание рецепта")
    # image =
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


# Модель ингридиенты для рецепта
class RecipeIngredients(models.Model):
    pass


# Модель список покупок
class Shopping_cart(models.Model):
    pass


# Модель избранное
class Favorite(models.Model):
    pass


# Модель подписки
class Subscriptions(models.Model):
    pass
