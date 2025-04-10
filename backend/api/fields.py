from base64 import b64decode

from django.core.files.base import ContentFile
from rest_framework.serializers import Field, ImageField

from .serializers import RecipeSerializer
from recipes.models import Recipe


class Base64ImageField(ImageField):
    def to_internal_value(self, data):
        if isinstance(data, str) and data.startswith("data:image"):
            format, imgstr = data.split(";base64,")
            ext = format.split("/")[-1]
            data = ContentFile(b64decode(imgstr), name="temp." + ext)

        return super().to_internal_value(data)


class RecipeSubscriptionUserField(Field):
    """Сериализатор для вывода рецептов в подписках."""

    def get_attribute(self, instance):
        """Получение списка рецептов, принадлежащих автору."""
        return Recipe.objects.filter(author=instance.author)

    def to_representation(self, recipes_list):
        """Преобразование списка в удобный для представления формат."""
        serializer = RecipeSerializer(recipes_list, many=True)
        return serializer.data
