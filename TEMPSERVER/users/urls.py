from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import UserViewSet, LoginView

# DefaultRouter auto-generates the CRUD routes for the viewset.
router = DefaultRouter()
router.register(r"users", UserViewSet, basename="user")

urlpatterns = [
    # Authentication.
    path("auth/login/", LoginView.as_view(), name="login"),
    path("", include(router.urls)),
]
