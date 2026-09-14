from rest_framework.routers import DefaultRouter

from .views import DataSourceFieldViewSet, DataSourceViewSet

router = DefaultRouter()
router.register("data-sources", DataSourceViewSet, basename="data-source")
router.register("data-source-fields", DataSourceFieldViewSet, basename="data-source-field")

urlpatterns = router.urls
