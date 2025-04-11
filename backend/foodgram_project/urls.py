from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from services import short_link_redirec

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("api.urls", namespace="api")),
    path("<str:short_url>", short_link_redirec.redirection),
]
if settings.DEBUG:
    urlpatterns += static(
        settings.STATIC_URL, document_root=settings.STATIC_ROOT
    )
    urlpatterns += static(
        settings.MEDIA_URL, document_root=settings.MEDIA_ROOT
    )
