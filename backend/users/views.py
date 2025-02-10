from djoser.views import UserViewSet
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated

from api.pagination import CustomPagination
from api.serializers import Subscription


# UserViewSet из Djoser
class CustomUserViewSet(UserViewSet):
    pagination_class = CustomPagination

    @action(detail=False, permission_classes=[IsAuthenticated])
    def subscriptions(self, request):
        """Просмотр подписок пользователя"""
        queryset = self.request.user.subscription.all()
        page = self.paginate_queryset(queryset)
        serializer = Subscription(
            page, many=True, context={"request": request}
        )
        return self.get_paginated_response(serializer.data)
