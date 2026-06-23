from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    ConversationsSeriesView,
    MetricsViewSet,
    OverviewView,
    TopFaqsView,
    UnansweredQuestionViewSet,
)

router = DefaultRouter()
router.register("metrics", MetricsViewSet, basename="metrics")
router.register("unanswered", UnansweredQuestionViewSet, basename="unanswered")

urlpatterns = [
    # Dashboard / analytics-page endpoints consumed by the frontend.
    path("overview/", OverviewView.as_view(), name="analytics-overview"),
    path(
        "conversations-series/",
        ConversationsSeriesView.as_view(),
        name="analytics-conversations-series",
    ),
    path("top-faqs/", TopFaqsView.as_view(), name="analytics-top-faqs"),
    *router.urls,
]
