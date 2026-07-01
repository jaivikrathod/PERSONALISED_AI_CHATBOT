from django.contrib import admin

from .models import User


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "email",
        "gender",
        "type",
        "company",
        "active",
        "is_archived",
        "created_at",
    )
    search_fields = ("name", "email")
    list_filter = ("gender", "type", "active", "is_archived", "company", "created_at")
    ordering = ("-created_at",)
    readonly_fields = ("created_at", "updated_at")

    fieldsets = (
        (None, {"fields": ("name", "email", "gender", "dob", "company", "type")}),
        ("Status", {"fields": ("active", "is_archived")}),
        ("Timestamps", {"fields": ("created_at", "updated_at")}),
    )
