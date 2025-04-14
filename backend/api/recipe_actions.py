from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response

from recipes.models import Recipe


class RecipeActions:
    @staticmethod
    def add_to_list(request, pk, model, serializer, already_exists_message):
        """Добавляет рецепт в указанный список (избранное или корзину)."""
        recipe = get_object_or_404(Recipe, pk=pk)

        if model.objects.filter(user=request.user, recipe=recipe).exists():
            return Response(
                {"detail": already_exists_message},
                status=status.HTTP_400_BAD_REQUEST,
            )

        model.objects.create(user=request.user, recipe=recipe)
        response_serializer = serializer(recipe, context={"request": request})
        return Response(
            response_serializer.data,
            status=status.HTTP_201_CREATED,
        )

    @staticmethod
    def remove_from_list(request, pk, model, not_found_message):
        """Удаляет рецепт из указанного списка (избранное или корзина)."""
        recipe = get_object_or_404(Recipe, pk=pk)

        if not request.user.is_authenticated:
            return Response(
                {"detail": "Необходима аутентификация."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        item = model.objects.filter(user=request.user, recipe=recipe)

        if item.exists():
            item.delete()
            return Response(
                {"detail": "Рецепт удален."},
                status=status.HTTP_204_NO_CONTENT,
            )

        return Response(
            {"detail": not_found_message},
            status=status.HTTP_400_BAD_REQUEST,
        )
