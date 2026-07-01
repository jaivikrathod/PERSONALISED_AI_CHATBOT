from django.contrib import admin

from .models import Question


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ("id", "short_question", "company", "is_archived", "created_at")
    search_fields = ("question", "answer")
    list_filter = ("is_archived", "company", "created_at")
    ordering = ("-created_at",)
    readonly_fields = ("created_at", "updated_at")

    fieldsets = (
        (None, {"fields": ("company", "question", "answer", "is_archived")}),
        ("Timestamps", {"fields": ("created_at", "updated_at")}),
    )

    @admin.display(description="Question")
    def short_question(self, obj):
        # Truncated preview for the changelist.
        return obj.question[:50]
