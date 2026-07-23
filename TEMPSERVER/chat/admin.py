from django.contrib import admin

from .models import ChatMessage, ChatSession


@admin.register(ChatSession)
class ChatSessionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "company",
        "agent_needed",
        "agent",
        "status",
        "closed_at",
        "created_at",
    )

    list_filter = (
        "status",
        "agent_needed",
        "created_at",
    )

    search_fields = (
        "company__name",
        "agent__name",
    )


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "session",
        "sent_by_us",
        "is_ai",
        "this_user",
        "message_type",
        "created_at",
    )

    list_filter = (
        "sent_by_us",
        "is_ai",
        "message_type",
        "created_at",
    )

    search_fields = (
        "message",
        "customer_user_name",
        "customer_user_email",
    )