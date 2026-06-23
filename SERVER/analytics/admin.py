from django.contrib import admin

from .models import ConversationMetrics, UnansweredQuestion


@admin.register(ConversationMetrics)
class ConversationMetricsAdmin(admin.ModelAdmin):
    list_display = (
        "company",
        "date",
        "total_conversations",
        "resolved_by_ai",
        "resolved_by_agent",
        "escalated_chats",
    )
    list_filter = ("company", "date")
    readonly_fields = ("uuid", "created_at", "updated_at")


@admin.register(UnansweredQuestion)
class UnansweredQuestionAdmin(admin.ModelAdmin):
    list_display = ("question", "company", "occurrence_count", "is_resolved", "updated_at")
    list_filter = ("is_resolved", "company")
    search_fields = ("question",)
    readonly_fields = ("uuid", "normalized", "created_at", "updated_at")
