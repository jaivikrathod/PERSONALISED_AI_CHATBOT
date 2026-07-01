from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import VectorizeCompanyView, VectorJobViewSet

# Read-only routes for inspecting jobs.
router = DefaultRouter()
router.register(r"vector-jobs", VectorJobViewSet, basename="vector-job")

urlpatterns = [
    # Trigger vectorization for a company.
    path(
        "vectorize/<int:company_id>/",
        VectorizeCompanyView.as_view(),
        name="vectorize-company",
    ),
    path("", include(router.urls)),
]
