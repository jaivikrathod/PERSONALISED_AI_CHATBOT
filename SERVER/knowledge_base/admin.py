from django.contrib import admin

from .models import KnowledgeBase, QuestionAnswer, QuestionEmbedding


@admin.register(KnowledgeBase)
class KnowledgeBaseAdmin(admin.ModelAdmin):
    list_display = ("title", "company", "is_active", "is_deleted", "created_at")
    list_filter = ("is_active", "is_deleted", "company")
    search_fields = ("title", "description")
    readonly_fields = ("uuid", "created_at", "updated_at")


@admin.register(QuestionAnswer)
class QuestionAnswerAdmin(admin.ModelAdmin):
    list_display = ("question", "knowledge_base", "embedding_status", "is_deleted", "created_at")
    list_filter = ("embedding_status", "is_deleted")
    search_fields = ("question", "answer")
    readonly_fields = ("uuid", "embedding_status", "created_at", "updated_at")


@admin.register(QuestionEmbedding)
class QuestionEmbeddingAdmin(admin.ModelAdmin):
    list_display = ("qa", "company", "model_name", "created_at")
    readonly_fields = ("uuid", "created_at", "updated_at")
