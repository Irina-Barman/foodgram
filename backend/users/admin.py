from django.contrib import admin
from django.contrib.admin import register

from .models import Subscription, CustomUser


@register(CustomUser)
class PersonAdmin(admin.ModelAdmin):
    list_display = ('username', 'first_name',
                    'last_name', 'email', 'password')
    list_filter = ('first_name', 'email',)
    save_on_top = True


@register(Subscription)
class FollowAdmin(admin.ModelAdmin):
    list_display = ('author', 'user',)
    search_fields = ('user', 'author',)
    list_per_page = 20
    save_on_top = True
