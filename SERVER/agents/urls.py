from rest_framework.routers import DefaultRouter

from .views import AgentAvailabilityViewSet, AssignmentViewSet

router = DefaultRouter()
router.register("availability", AgentAvailabilityViewSet, basename="agent-availability")
router.register("assignments", AssignmentViewSet, basename="agent-assignment")

urlpatterns = router.urls
