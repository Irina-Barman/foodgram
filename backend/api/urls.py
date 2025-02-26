from django.urls import path, re_path, include
from rest_framework.routers import DefaultRouter

from .views import (
    IngredientViewSet,
    RecipeViewSet,
    TagViewSet,
    CustomUserViewSet,
    FavoritesViewSet,
    SubscriptionViewSet,
    ShoppingCartViewSet,
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
        "recipes/<int:id>/favorite/",
        FavoritesViewSet.as_view({"post": "create", "delete": "delete"}),
        name="favorite",
    ),
    path(
        "users/<int:id>/subscribe/",
        SubscriptionViewSet.as_view({"post": "create", "delete": "delete"}),
        name="subscribe",
    ),
    path(
        "recipes/<int:id>/shopping_cart/",
        ShoppingCartViewSet.as_view({"post": "create", "delete": "delete"}),
        name="shopping_cart",
    ),
]
