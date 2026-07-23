from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import UserViewSet, LoginView, ManagedUserViewSet

# DefaultRouter auto-generates the CRUD routes for the viewset.
router = DefaultRouter()
router.register(r"users", UserViewSet, basename="user")
router.register(r"managed-users", ManagedUserViewSet, basename="managed-user")

urlpatterns = [
    # Authentication.
    path("auth/login/", LoginView.as_view(), name="login"),
    path("", include(router.urls)),
]
