from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models import F, Q


HELP_TEXT = "Обязательное поле. Максимальное количество символов: "


class CustomUser(AbstractUser):
    """Модель для пользователей."""

    username = models.CharField(
        "Уникальный юзернейм",
        max_length=getattr(settings, "MAX_USERNAME_LENGTH", 150),
        blank=False,
        unique=True,
        help_text=(
            f"{HELP_TEXT}{getattr(settings, 'MAX_USERNAME_LENGTH', 150)}"
        ),
    )
    password = models.CharField(
        "Пароль",
        max_length=getattr(settings, "MAX_PASSWORD_LENGTH", 300),
        blank=False,
        help_text=HELP_TEXT,
    )
    email = models.EmailField(
        "Адрес электронной почты",
        max_length=getattr(settings, "MAX_EMAIL_LENGTH", 254),
        blank=False,
        unique=True,
        help_text=(f"{HELP_TEXT}{getattr(settings, 'MAX_EMAIL_LENGTH', 254)}"),
    )
    first_name = models.CharField(
        "Имя",
        max_length=getattr(settings, "MAX_USERNAME_LENGTH", 150),
        blank=False,
        help_text=(
            f"{HELP_TEXT}{getattr(settings, 'MAX_USERNAME_LENGTH', 150)}"
        ),
    )
    last_name = models.CharField(
        "Фамилия",
        max_length=getattr(settings, "MAX_USERNAME_LENGTH", 150),
        blank=False,
        help_text=(
            f"{HELP_TEXT}{getattr(settings, 'MAX_USERNAME_LENGTH', 150)}"
        ),
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
                name="Вы уже подписаны на данного автора",
            ),
            models.CheckConstraint(
                check=~Q(user=F("author")), name="Нельзя подписаться на себя"
            ),
        ]
        ordering = ["-id"]
        verbose_name = "Подписка"
        verbose_name_plural = "Подписки"

        def __str__(self):
            return f"{self.user} подписался на {self.author}"
