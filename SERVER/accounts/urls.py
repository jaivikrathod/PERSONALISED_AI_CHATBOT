from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView, TokenVerifyView

from .views import LoginView, RegisterView, UserViewSet

router = DefaultRouter()
router.register("users", UserViewSet, basename="user")
router.register("auth", RegisterView, basename="auth")

urlpatterns = [
    path("auth/login/", LoginView.as_view(), name="login"),
    path("auth/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("auth/token/verify/", TokenVerifyView.as_view(), name="token_verify"),
    path("", include(router.urls)),
]
