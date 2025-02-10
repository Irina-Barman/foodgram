import base64
from django.core.files.base import ContentFile
from djoser.views import UserViewSet

from rest_framework.decorators import action
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from api.pagination import CustomPagination
from api.serializers import SubscriptionSerializer


# UserViewSet из Djoser
class CustomUserViewSet(UserViewSet):
    pagination_class = CustomPagination

    @action(detail=False, permission_classes=[IsAuthenticated])
    def subscriptions(self, request):
        """Просмотр подписок пользователя"""
        queryset = request.user.subscription.all()
        page = self.paginate_queryset(queryset)
        serializer = SubscriptionSerializer(
            page, many=True, context={"request": request}
        )
        return self.get_paginated_response(serializer.data)

    @action(
        detail=False,
        methods=["put", "delete"],
        permission_classes=[IsAuthenticated],
    )
    def avatar(self, request):
        """Добавление или удаление аватара текущего пользователя."""
        user = request.user

        if request.method == "PUT":
            avatar_data = request.data.get("avatar")
            if avatar_data:
                try:
                    # Извлекаем данные из строки Base64
                    format, imgstr = avatar_data.split(";base64,")
                    ext = format.split("/")[-1]  # Получаем расширение файла
                    # Декодируем строку Base64
                    img_data = base64.b64decode(imgstr)
                    # Сохраняем изображение
                    file_name = (
                        f"avatar_{user.id}.{ext}"  # Формируем имя файла
                    )
                    user.avatar.save(
                        file_name, ContentFile(img_data), save=True
                    )

                    # Возвращаем URL аватара
                    return Response(
                        {"avatar": user.avatar.url}, status=status.HTTP_200_OK
                    )
                except Exception as e:
                    return Response(
                        {"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST
                    )

            return Response(
                {"detail": "Поле avatar обязательно."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        elif request.method == "DELETE":
            if user.avatar:
                user.avatar.delete(save=False)  # Удаляем файл аватара
                user.avatar = None  # Обнуляем поле аватара
                user.save()
                return Response(status=status.HTTP_204_NO_CONTENT)

            return Response(
                {"detail": "Аватар не найден."},
                status=status.HTTP_404_NOT_FOUND,
            )
