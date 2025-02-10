from django.urls import path, include


app_name = "api"

urlpatterns = [
    path('api/auth/', include('djoser.urls.authtoken')),  # для токенов
    path('api/auth/', include('djoser.urls')),
]
