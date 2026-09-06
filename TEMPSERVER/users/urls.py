from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    LoginView,
    LogoutView,
    ManagedUserViewSet,
    MeView,
    RegisterView,
    UserViewSet,
)

# DefaultRouter auto-generates the CRUD routes for the viewset.
router = DefaultRouter()
router.register(r"users", UserViewSet, basename="user")
router.register(r"managed-users", ManagedUserViewSet, basename="managed-user")

urlpatterns = [
    # Authentication. `register` and `login` are the only open endpoints here.
    path("auth/register/", RegisterView.as_view(), name="register"),
    path("auth/login/", LoginView.as_view(), name="login"),
    path("auth/logout/", LogoutView.as_view(), name="logout"),
    path("auth/me/", MeView.as_view(), name="me"),
    path("", include(router.urls)),
]
