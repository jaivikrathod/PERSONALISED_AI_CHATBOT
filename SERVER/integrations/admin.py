from django.contrib import admin

from .models import WidgetConfig


@admin.register(WidgetConfig)
class WidgetConfigAdmin(admin.ModelAdmin):
    list_display = ("chatbot", "title", "position", "enabled")
    list_filter = ("enabled", "position")
    readonly_fields = ("uuid", "created_at", "updated_at")
