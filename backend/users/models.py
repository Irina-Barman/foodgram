from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.db import models

from users.validators import validate_username_not_me


class CustomUser(AbstractUser):
    """Кастомный класс User."""

    id = models.AutoField(primary_key=True)
    username = models.CharField(
        max_length=settings.MAX_USERNAME_LENGTH,
        verbose_name="Имя пользователя",
        unique=True,
        validators=[
            UnicodeUsernameValidator(),
            validate_username_not_me,
        ],
    )
    email = models.EmailField(
        max_length=settings.MAX_EMAIL_LENGTH,
        verbose_name="Email",
        unique=True,
    )
    first_name = models.CharField(
        max_length=settings.MAX_NAME_LENGTH, verbose_name="Имя", blank=True
    )
    last_name = models.CharField(
        max_length=settings.MAX_NAME_LENGTH, verbose_name="Фамилия", blank=True
    )
    avatar = models.ImageField(
        upload_to='avatars/',
        blank=True,
        null=True,
        verbose_name="Аватар"
    )

    class Meta:
        verbose_name = "Пользователь"
        verbose_name_plural = "Пользователи"
        ordering = ("id",)
        constraints = [
            models.UniqueConstraint(
                fields=["username", "email"],
                name="unique_username_email_constraint",
            )
        ]

    @property
    def is_admin(self):
        return self.is_superuser or self.is_admin


class Subscription(models.Model):
    """Модель подписки."""

    id = models.AutoField(primary_key=True)
    user = models.ForeignKey(
        CustomUser,
        verbose_name="Подписчик",
        on_delete=models.CASCADE,
        related_name="follower",
    )
    author = models.ForeignKey(
        CustomUser,
        verbose_name="Автор рецепта",
        on_delete=models.CASCADE,
        related_name="following",
    )

    class Meta:
        verbose_name = "Подписка"
        verbose_name_plural = "Подписки"
        constraints = [
            models.UniqueConstraint(
                fields=["user", "author"], name="unique_follow"
            ),
            models.CheckConstraint(
                name="user_is_not_author",
                check=~models.Q(user=models.F("author")),
            ),
        ]

    def __str__(self):
        return f"{self.user.username} подписан на {self.author.username}"
