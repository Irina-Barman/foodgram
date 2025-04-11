from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from services.redict_url import redirect_to_original

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("api.urls", namespace="api")),
    path(
        "s/<str:short_code>/", redirect_to_original, name="short_link_redirect"
    ),
]
if settings.DEBUG:
    urlpatterns += static(
        settings.STATIC_URL, document_root=settings.STATIC_ROOT
    )
    urlpatterns += static(
        settings.MEDIA_URL, document_root=settings.MEDIA_ROOT
    )
