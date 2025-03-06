from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models


HELP_TEXT = "Обязательное поле. Максимальное количество символов: "


class CustomUser(AbstractUser):
    """Модель пользователя."""
    REQUIRED_FIELDS = ["id", "email", "first_name", "last_name"]

    username = models.CharField(
        max_length=getattr(settings, "MAX_USERNAME_LENGTH", 150),
        unique=True,
        verbose_name="Логин пользователя",
        help_text=(
            f"{HELP_TEXT}{getattr(settings, 'MAX_USERNAME_LENGTH', 150)}"
        ),
    )
    password = models.CharField(
        max_length=getattr(settings, "MAX_PASSWORD_LENGTH", 300),
        blank=False,
        verbose_name="Пароль пользователя",
        help_text=(
            f"{HELP_TEXT}{getattr(settings, 'MAX_PASSWORD_LENGTH', 300)}"
        ),
    )
    email = models.EmailField(
        max_length=getattr(settings, "MAX_EMAIL_LENGTH", 254),
        unique=True,
        verbose_name="Электронная почта",
        help_text=(f"{HELP_TEXT}{getattr(settings, 'MAX_EMAIL_LENGTH', 254)}"),
    )
    first_name = models.CharField(
        max_length=getattr(settings, "MAX_USERNAME_LENGTH", 150),
        verbose_name="Имя пользователя",
        help_text=(
            f"{HELP_TEXT}{getattr(settings, 'MAX_USERNAME_LENGTH', 150)}"
        ),
    )
    last_name = models.CharField(
        max_length=getattr(settings, "MAX_USERNAME_LENGTH", 150),
        verbose_name="Фамилия пользователя",
        help_text=(
            f"{HELP_TEXT}{getattr(settings, 'MAX_USERNAME_LENGTH', 150)}"
        ),
    )
    avatar = models.ImageField(
        upload_to="users/", blank=True, null=True, verbose_name="Аватар"
    )

    class Meta:
        ordering = ("username",)

    def __str__(self):
        return self.username


class Subscription(models.Model):
    """Модель подписки."""
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name="subscriptions",
        verbose_name="Подписчик",
    )
    author = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name="subscribers",
        verbose_name="Автор",
    )

    class Meta:
        ordering = ['-id']
        constraints = [
            models.UniqueConstraint(
                fields=["user", "author"], name="subscriptions_unique"
            )
        ]

    def __str__(self):
        return f"Подписка {self.user} на {self.author}"
