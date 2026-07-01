from django.contrib import admin

from .models import VectorJob


@admin.register(VectorJob)
class VectorJobAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "company",
        "status",
        "total_questions",
        "processed_questions",
        "failed_questions",
        "started_at",
        "completed_at",
        "created_at",
    )
    search_fields = ("company__name", "error_message")
    list_filter = ("status", "company", "created_at")
    ordering = ("-created_at",)
    readonly_fields = (
        "company",
        "status",
        "total_questions",
        "processed_questions",
        "failed_questions",
        "started_at",
        "completed_at",
        "error_message",
        "created_at",
        "updated_at",
    )
