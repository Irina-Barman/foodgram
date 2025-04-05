from api.constants import (MAX_EMAIL_LENGTH, MAX_PASSWORD_LENGTH,
                           MAX_USERNAME_LENGTH)
from django.contrib.auth.models import AbstractUser
from django.db import models

HELP_TEXT = "Обязательное поле. Максимальное количество символов: "


class CustomUser(AbstractUser):
    """Модель пользователя."""

    REQUIRED_FIELDS = ["id", "email", "first_name", "last_name"]

    username = models.CharField(
        max_length=MAX_USERNAME_LENGTH,
        unique=True,
        verbose_name="Логин пользователя",
        help_text=(f"{HELP_TEXT}{MAX_USERNAME_LENGTH}"),
    )
    password = models.CharField(
        max_length=MAX_PASSWORD_LENGTH,
        blank=False,
        verbose_name="Пароль пользователя",
        help_text=(f"{HELP_TEXT}{MAX_PASSWORD_LENGTH}"),
    )
    email = models.EmailField(
        max_length=MAX_EMAIL_LENGTH,
        unique=True,
        verbose_name="Электронная почта",
        help_text=(f"{HELP_TEXT}{MAX_EMAIL_LENGTH}"),
    )
    first_name = models.CharField(
        max_length=MAX_USERNAME_LENGTH,
        verbose_name="Имя пользователя",
        help_text=(f"{HELP_TEXT}{MAX_USERNAME_LENGTH}"),
    )
    last_name = models.CharField(
        max_length=MAX_USERNAME_LENGTH,
        verbose_name="Фамилия пользователя",
        help_text=(f"{HELP_TEXT}{MAX_USERNAME_LENGTH}"),
    )
    avatar = models.ImageField(
        upload_to="users/", blank=True, null=True, verbose_name="Аватар"
    )

    class Meta:
        ordering = ("username",)
        verbose_name = "Пользователь"
        verbose_name_plural = "Пользователи"

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
        ordering = ["-id"]
        constraints = [
            models.UniqueConstraint(
                fields=("user", "author"), name="subscriptions_unique"
            )
        ]
        verbose_name = "Подписка"
        verbose_name_plural = "Подписки"

    def __str__(self):
        return f"Подписка {self.user} на {self.author}"
