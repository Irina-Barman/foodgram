from django.db import models
from foodgram_project.settings import MAX_NAME_LENGTH


# Модель теги
class Tags(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(
        "Название тега", max_length=MAX_NAME_LENGTH, unique=True
    )
    slug = models.SlugField(
        "Слаг тега", max_length=MAX_NAME_LENGTH, unique=True
    )


# Модель рецепты
class Recipes(models.Model):
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


# Модель Ингредиенты
class Ingredients(models.Model):
    pass
