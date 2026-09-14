from django.contrib import admin

from .models import Chatbot, Tool


class ToolInline(admin.TabularInline):
    model = Tool
    extra = 0
    fields = ("name", "tool_type", "is_active", "requires_confirmation", "schema_version")
    show_change_link = True


@admin.register(Chatbot)
class ChatbotAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "slug", "company", "is_active", "created_at")
    list_filter = ("is_active", "company")
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}
    readonly_fields = ("created_at", "updated_at")
    inlines = [ToolInline]


@admin.register(Tool)
class ToolAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "tool_type", "chatbot", "is_active", "schema_version")
    list_filter = ("tool_type", "is_active")
    search_fields = ("name", "description")
    readonly_fields = ("created_at", "updated_at")
