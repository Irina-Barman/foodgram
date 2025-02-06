from django.contrib.auth.models import AbstractUser
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.db import models

from .validators import validate_username_not_me
from foodgram_project.settings import (
    MAX_USERNAME_LENGTH,
    MAX_NAME_LENGTH,
    MAX_EMAIL_LENGTH,
)


class CustomUser (AbstractUser):
    """Кастомный класс User."""

    id = models.AutoField(primary_key=True)
    username = models.CharField(
        max_length=MAX_USERNAME_LENGTH,
        verbose_name="Имя пользователя",
        unique=True,
        validators=[
            UnicodeUsernameValidator(),
            validate_username_not_me,
        ],
    )
    email = models.EmailField(
        max_length=MAX_EMAIL_LENGTH,
        verbose_name="Email",
        unique=True,
    )
    first_name = models.CharField(
        max_length=MAX_NAME_LENGTH, verbose_name="Имя", blank=True
    )
    last_name = models.CharField(
        max_length=MAX_NAME_LENGTH, verbose_name="Фамилия", blank=True
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
