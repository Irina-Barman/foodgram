from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.shortcuts import get_object_or_404
from rest_framework import filters, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import AccessToken

from api.permissions import IsAdmin
from .serializers import SignUpSerializer, TokenSerializer, UserSerializer

User = get_user_model()


class UserSignup(viewsets.GenericViewSet):
    """
    ViewSet для регистрации пользователей.
    Поддерживает создание пользователя и отправку кода подтверждения.
    """
    permission_classes = (permissions.AllowAny,)
    serializer_class = SignUpSerializer

    def create(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)

        username = serializer.validated_data.get("username")
        email = serializer.validated_data.get("email")

        user, _ = User.objects.get_or_create(
            username=username,
            email=email,
            defaults=serializer.validated_data
        )

        # Генерируем и отправляем код подтверждения
        confirmation_code = default_token_generator.make_token(user)
        send_mail(
            subject="Код подтверждения",
            message=f"Ваш код подтверждения: {confirmation_code}",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            fail_silently=False,
        )

        return Response(
            {
                "email": email,
                "username": username,
            },
            status=status.HTTP_200_OK,
        )


class UserTokenViewSet(viewsets.GenericViewSet):
    """
    ViewSet для получения JWT-токена.
    Проверяет код подтверждения и выдает токен доступа.
    """
    queryset = User.objects.all()
    serializer_class = TokenSerializer
    permission_classes = (permissions.AllowAny,)

    def create(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        username = serializer.validated_data.get("username")
        confirmation_code = serializer.validated_data.get("confirmation_code")
        user = get_object_or_404(User, username=username)

        if not default_token_generator.check_token(user, confirmation_code):
            return Response(
                {"confirmation_code": "Неверный код подтверждения"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        token = str(AccessToken.for_user(user))
        return Response({"token": token}, status=status.HTTP_200_OK)


class UserViewSet(viewsets.ModelViewSet):
    """
    ViewSet для работы с пользователями.
    Поддерживает операции CRUD для пользователей.
    Доступ только для администраторов, кроме эндпоинта /me/.
    """
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = (IsAdmin,)
    filter_backends = (filters.SearchFilter,)
    search_fields = ("username",)
    lookup_field = "username"
    http_method_names = ["get", "post", "patch", "delete"]

    @action(
        detail=False,
        methods=["get", "patch"],
        permission_classes=[permissions.IsAuthenticated],
    )
    def me(self, request):
        if request.method == "PATCH":
            serializer = self.serializer_class(
                request.user,
                data=request.data,
                partial=True,
                context={"request": request},
            )
            serializer.is_valid(raise_exception=True)
            serializer.save(role=request.user.role)
            return Response(serializer.data, status=status.HTTP_200_OK)
        serializer = self.serializer_class(request.user)
        return Response(serializer.data, status=status.HTTP_200_OK)
