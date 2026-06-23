from django.contrib import admin

from .models import AgentAvailability, ConversationAssignment


@admin.register(AgentAvailability)
class AgentAvailabilityAdmin(admin.ModelAdmin):
    list_display = ("user", "online", "last_seen", "max_active_chats")
    list_filter = ("online",)
    search_fields = ("user__email",)


@admin.register(ConversationAssignment)
class ConversationAssignmentAdmin(admin.ModelAdmin):
    list_display = ("conversation", "agent", "is_active", "assigned_at", "released_at")
    list_filter = ("is_active",)
    readonly_fields = ("uuid", "created_at", "updated_at")
