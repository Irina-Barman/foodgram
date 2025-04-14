from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response

from recipes.models import Recipe


class RecipeHandler:

    @staticmethod
    def __add_recipe(serializer_name, request, recipe):
        """Добавить рецепт."""
        serializer = serializer_name(
            data={"user": request.user.id, "recipe": recipe.id},
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @staticmethod
    def __delete_recipe(model, request, err_msg, recipe):
        """Удалить рецепт."""
        obj = model.objects.filter(user=request.user, recipe=recipe)
        if obj.exists():
            obj.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response({"error": err_msg}, status=status.HTTP_400_BAD_REQUEST)

    def __check_authentication(self, request):
        """Проверка аутентификации пользователя."""
        if not request.user.is_authenticated:
            return Response(
                {"detail": "Необходима аутентификация."},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        return None

    def __get_recipe(self, pk):
        """Получить рецепт по первичному ключу."""
        return get_object_or_404(Recipe, pk=pk)
