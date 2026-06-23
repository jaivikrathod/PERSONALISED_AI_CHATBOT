from rest_framework.routers import DefaultRouter

from .views import KnowledgeBaseViewSet, QuestionAnswerViewSet

router = DefaultRouter()
router.register("knowledge-bases", KnowledgeBaseViewSet, basename="knowledge-base")
router.register("qa", QuestionAnswerViewSet, basename="qa")

urlpatterns = router.urls
