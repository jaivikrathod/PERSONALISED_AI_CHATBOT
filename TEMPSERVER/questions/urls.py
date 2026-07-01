from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import QuestionViewSet

# DefaultRouter auto-generates the CRUD routes for the viewset.
router = DefaultRouter()
router.register(r"questions", QuestionViewSet, basename="question")

urlpatterns = [
    path("", include(router.urls)),
]
