from django.urls import include, path, re_path
from rest_framework.routers import DefaultRouter

from .views import (
    CustomUserViewSet,
    IngredientViewSet,
    RecipeViewSet,
    ShotLinkView,
    TagViewSet,
)

app_name = "api"
router_v1 = DefaultRouter()
router_v1.register("tags", TagViewSet)
router_v1.register("users", CustomUserViewSet)
router_v1.register("ingredients", IngredientViewSet)
router_v1.register("recipes", RecipeViewSet)

urlpatterns = [
    path("", include(router_v1.urls)),
    path("", include("djoser.urls")),
    re_path(r"^auth/", include("djoser.urls.authtoken")),
    path(
        "recipes/<str:id>/get-link/", ShotLinkView.as_view(), name="get-link"
    ),
]
