from django.http import HttpResponse
from django.shortcuts import redirect

from recipes.models import ShortLink


def get_full_url(url: str) -> str:
    """
    Достаем полную ссылку по short_url
    Если ссылки нет в базе или она не активна
    возвращаем ошибку.
    Если все ок, то добавляем к счетчику статистики 1
    и возвращаем полную ссылку.
    """
    try:
        token = ShortLink.objects.get(short_url__exact=url)
        if not token.is_active:
            raise KeyError("Ссылка больше не доступна")
    except ShortLink.DoesNotExist:
        raise KeyError("Попробуйте другой url")
    token.requests_count += 1
    token.save()
    return token.full_url


def redirection(request, short_url):
    """Перенаправляем пользователя по ссылке"""
    try:
        full_link = get_full_url(
            short_url
        )  # получает полный адрес по короткой ссылке
        return redirect(full_link)  # перенаправляем пользователя по ссылке
    except Exception as e:
        return HttpResponse(e.args)
