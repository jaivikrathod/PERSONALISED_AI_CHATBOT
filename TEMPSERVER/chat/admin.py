from django.contrib import admin

from .models import ChatMessage, ChatSession


@admin.register(ChatSession)
class ChatSessionAdmin(admin.ModelAdmin):
    list_display = ("id", "company", "agent_required", "assigned_agent", "status", "closed_at", "created_at")
    list_filter = ("status", "agent_required", "created_at")
    search_fields = ("company__name", "assigned_agent__name")


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ("id", "session", "sender_type", "sender_id", "message_type", "created_at")
    list_filter = ("sender_type", "message_type", "created_at")
    search_fields = ("message",)
