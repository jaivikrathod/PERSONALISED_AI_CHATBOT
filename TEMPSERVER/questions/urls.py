from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import QuestionViewSet, UnansweredMessageViewSet

# DefaultRouter auto-generates the CRUD routes for the viewset.
router = DefaultRouter()
router.register(r"questions", QuestionViewSet, basename="question")
router.register(
    r"unanswered-messages",
    UnansweredMessageViewSet,
    basename="unanswered-message",
)

urlpatterns = [
    path("", include(router.urls)),
]
