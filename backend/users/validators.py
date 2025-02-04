from django.core.exceptions import ValidationError


def validate_username_not_me(value):
    """
    Проверяет, что username не равен 'me'.
    Args:
        value (str): Проверяемое значение username
    Raises:
        ValidationError: Если username равен 'me'
    """
    if value.lower() == 'me':
        raise ValidationError(
            'Использовать имя "me" в качестве username запрещено'
        )
