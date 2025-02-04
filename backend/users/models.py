from django.contrib.auth.models import AbstractUser
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from .validators import validate_username_not_me
from foodgram_project.settings import (
    MAX_USERNAME_LENGTH,
    MAX_NAME_LENGTH,
    MAX_EMAIL_LENGTH,
    MAX_ROLE_LENGTH,
)


class CustomUser(AbstractUser):
    """Кастомный класс User."""

    class UserRoles(models.TextChoices):
        GUEST = "guest", _("Гость")
        USER = "user", _("Пользователь")
        ADMIN = "admin", _("Администратор")

    id = models.AutoField(primary_key=True)

    username = models.CharField(
        max_length=MAX_USERNAME_LENGTH,
        verbose_name=_("Имя пользователя"),
        validators=[
            UnicodeUsernameValidator(),
            validate_username_not_me,
        ],
    )
    email = models.EmailField(
        max_length=MAX_EMAIL_LENGTH,
        verbose_name=_("Email"),
        unique=True,
    )
    first_name = models.CharField(
        max_length=MAX_NAME_LENGTH, verbose_name=_("Имя"), blank=True
    )
    last_name = models.CharField(
        max_length=MAX_NAME_LENGTH, verbose_name=_("Фамилия"), blank=True
    )

    role = models.CharField(
        max_length=MAX_ROLE_LENGTH,
        verbose_name=_("Роль"),
        choices=UserRoles.choices,
        default=UserRoles.GUEST,
    )

    class Meta:
        verbose_name = _("Пользователь")
        verbose_name_plural = _("Пользователи")
        ordering = ("id",)
        constraints = [
            models.UniqueConstraint(
                fields=["username", "email"],
                name="unique_username_email",
            )
        ]

    def __str__(self):
        return self.username

    @property
    def is_admin(self):
        return self.role == self.UserRoles.ADMIN or self.is_superuser

    @property
    def is_guest(self):
        return self.role == self.UserRoles.GUEST
