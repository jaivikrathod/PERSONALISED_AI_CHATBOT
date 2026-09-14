from django.contrib import admin

from .models import IngestionJob, KnowledgeDocument, KnowledgeSource


@admin.register(KnowledgeSource)
class KnowledgeSourceAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "kind", "chatbot", "status", "last_indexed_at")
    list_filter = ("kind", "status")


@admin.register(KnowledgeDocument)
class KnowledgeDocumentAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "external_ref", "source", "status", "updated_at")
    list_filter = ("status", "file_type")
    exclude = ("raw_text",)


@admin.register(IngestionJob)
class IngestionJobAdmin(admin.ModelAdmin):
    list_display = ("id", "filename", "source", "status", "done_steps", "total_steps", "created_at")
    list_filter = ("status",)
    exclude = ("payload",)
