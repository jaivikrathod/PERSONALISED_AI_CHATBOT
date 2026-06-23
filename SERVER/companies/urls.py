from rest_framework.routers import DefaultRouter

from .views import CompanyViewSet, UserCompanyViewSet

router = DefaultRouter()
router.register("companies", CompanyViewSet, basename="company")
router.register("memberships", UserCompanyViewSet, basename="membership")

urlpatterns = router.urls
