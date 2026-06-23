from django.contrib import admin

from .models import Chatbot, Visitor


@admin.register(Chatbot)
class ChatbotAdmin(admin.ModelAdmin):
    list_display = ("name", "company", "active", "created_at")
    list_filter = ("active", "company")
    search_fields = ("name",)
    readonly_fields = ("uuid", "widget_token", "created_at", "updated_at")


@admin.register(Visitor)
class VisitorAdmin(admin.ModelAdmin):
    list_display = ("__str__", "chatbot", "session_id", "created_at")
    search_fields = ("name", "email", "session_id")
    readonly_fields = ("uuid", "created_at", "updated_at")
