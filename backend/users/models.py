from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models import F, Q


HELP_TEXT = "Обязательное поле. Максимальное количество символов: "


class CustomUser(AbstractUser):
    """Модель для пользователей."""

    username = models.CharField(
        "Уникальный юзернейм",
        max_length=settings.MAX_USERNAME_LENGTH,
        blank=False,
        unique=True,
        help_text=(f"{HELP_TEXT}{settings.MAX_USERNAME_LENGTH}"),
    )
    password = models.CharField(
        "Пароль",
        max_length=settings.MAX_PASSWORD_LENGTH,
        blank=False,
        help_text=HELP_TEXT,
    )
    email = models.EmailField(
        "Адрес электронной почты",
        max_length=settings.MAX_EMAIL_LENGTH,
        blank=False,
        unique=True,
        help_text=(f"{HELP_TEXT}{settings.MAX_EMAIL_LENGTH}"),
    )
    first_name = models.CharField(
        "Имя",
        max_length=settings.MAX_USERNAME_LENGTH,
        blank=False,
        help_text=(f"{HELP_TEXT}{settings.MAX_USERNAME_LENGTH}"),
    )
    last_name = models.CharField(
        "Фамилия",
        max_length=settings.MAX_USERNAME_LENGTH,
        blank=False,
        help_text=(f"{HELP_TEXT}{settings.MAX_USERNAME_LENGTH}"),
    )
    avatar = models.ImageField(
        upload_to="avatars/", blank=True, null=True, verbose_name="Аватар"
    )

    class Meta:
        verbose_name = "Пользователь"
        verbose_name_plural = "Пользователи"

    def __str__(self):
        return f"{self.username}: {self.first_name}"


class Subscription(models.Model):
    """Модель для подписчиков."""

    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name="subscriber",
        verbose_name="Подписчик",
    )
    author = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name="subscription",
        verbose_name="Автор",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "author"],
                name="unique_subscription",
            ),
            models.CheckConstraint(
                check=~Q(user=F("author")),
                name="cannot_subscription_self",
            ),
        ]
        ordering = ["-id"]
        verbose_name = "Подписка"
        verbose_name_plural = "Подписки"

    def __str__(self):
        return f"{self.user} подписался на {self.author}"
