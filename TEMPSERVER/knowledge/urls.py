from rest_framework.routers import DefaultRouter

from .views import IngestionJobViewSet, KnowledgeDocumentViewSet, KnowledgeSourceViewSet

router = DefaultRouter()
router.register("knowledge-sources", KnowledgeSourceViewSet, basename="knowledge-source")
router.register("knowledge-documents", KnowledgeDocumentViewSet, basename="knowledge-document")
router.register("ingestion-jobs", IngestionJobViewSet, basename="ingestion-job")

urlpatterns = router.urls
