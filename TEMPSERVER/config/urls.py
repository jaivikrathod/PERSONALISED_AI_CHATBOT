from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("company.urls")),
    path("api/", include("users.urls")),
    path("api/", include("questions.urls")),
    path("api/", include("vector_question.urls")),
]