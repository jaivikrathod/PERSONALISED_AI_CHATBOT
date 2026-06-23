from rest_framework.routers import DefaultRouter

from .views import ChatbotViewSet, VisitorViewSet

router = DefaultRouter()
router.register("chatbots", ChatbotViewSet, basename="chatbot")
router.register("visitors", VisitorViewSet, basename="visitor")

urlpatterns = router.urls
