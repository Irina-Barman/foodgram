from django.urls import include, path, re_path
from rest_framework.routers import DefaultRouter

from .views import (CustomUserViewSet, FavoritesViewSet, IngredientViewSet,
                    RecipeViewSet, ShoppingCartViewSet, ShortLinkView,
                    SubscriptionViewSet, TagViewSet, UserAvatarUpdateView)

app_name = "api"
router_v1 = DefaultRouter()
router_v1.register("tags", TagViewSet)
router_v1.register("users", CustomUserViewSet)
router_v1.register("ingredients", IngredientViewSet)
router_v1.register("recipes", RecipeViewSet)
router_v1.register("shopping_cart", ShoppingCartViewSet)

urlpatterns = [
    path("", include(router_v1.urls)),
    path("", include("djoser.urls")),
    re_path(r"^auth/", include("djoser.urls.authtoken")),
    path(
        "recipes/<int:id>/favorite/",
        FavoritesViewSet,
        name="favorite",
    ),
    path(
        "recipes/<str:id>/get-link/", ShortLinkView.as_view(), name="get-link"
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
    path(
        "users/me/avatar/",
        UserAvatarUpdateView.as_view(),
        name="user_avatar_update",
    ),
]
