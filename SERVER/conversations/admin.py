from django.contrib import admin

from .models import Conversation, Message


class MessageInline(admin.TabularInline):
    model = Message
    extra = 0
    readonly_fields = ("sender_type", "sender_agent", "message", "created_at")
    can_delete = False


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ("uuid", "company", "chatbot", "status", "last_confidence", "created_at")
    list_filter = ("status", "company")
    search_fields = ("uuid",)
    readonly_fields = ("uuid", "created_at", "updated_at")
    inlines = [MessageInline]


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ("conversation", "sender_type", "sender_agent", "created_at")
    list_filter = ("sender_type",)
    search_fields = ("message",)
    readonly_fields = ("uuid", "created_at", "updated_at")
