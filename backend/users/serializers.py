from django.contrib.auth.validators import UnicodeUsernameValidator
from rest_framework import serializers

from users.models import CustomUser
from api.models import Subscription
from .validators import validate_username_not_me
from foodgram_project.settings import MAX_USERNAME_LENGTH, MAX_EMAIL_LENGTH


class SignUpSerializer(serializers.Serializer):
    """
    Сериализатор для регистрации пользователей.
    Проверяет валидность username и email, обеспечивает уникальность данных.
    """

    username = serializers.CharField(
        max_length=MAX_USERNAME_LENGTH,
        required=True,
        validators=[
            UnicodeUsernameValidator(),
            validate_username_not_me,
        ],
    )
    email = serializers.EmailField(max_length=MAX_EMAIL_LENGTH, required=True)

    def validate(self, data):
        """
        Проверяет валидность данных при регистрации.
        """
        username = data.get("username")
        email = data.get("email")

        email_exists = CustomUser.objects.filter(email=email).exists()
        username_exists = CustomUser.objects.filter(username=username).exists()

        error_msg = {}
        if email_exists:
            error_msg["email"] = "Пользователь с таким email уже существует."
        if username_exists:
            error_msg["username"] = (
                "Пользователь с таким username уже существует."
            )

        if error_msg:
            raise serializers.ValidationError(error_msg)

        return data


class UserSerializer(serializers.ModelSerializer):
    is_subscribed = serializers.SerializerMethodField()

    class Meta:
        model = CustomUser
        fields = (
            "email",
            "id",
            "username",
            "first_name",
            "last_name",
            "is_subscribed",
        )

    def get_is_subscribed(self, obj):
        user = self.context.get("request").user
        if user.is_authenticated:
            return Subscription.objects.filter(user=user, author=obj).exists()
        return False


class TokenSerializer(serializers.Serializer):
    """
    Сериализатор для получения JWT-токена.

    Проверяет валидность username и кода подтверждения.
    """

    username = serializers.CharField(
        max_length=MAX_USERNAME_LENGTH,
        required=True,
        validators=[
            UnicodeUsernameValidator(),
            validate_username_not_me,
        ],
    )
    confirmation_code = serializers.CharField(required=True)


class SubscriptionSerializer(serializers.ModelSerializer):
    """Сериализатор подписок"""
    pass
