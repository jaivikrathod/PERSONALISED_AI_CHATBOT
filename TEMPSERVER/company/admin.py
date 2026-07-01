from django.contrib import admin

from .models import Company


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ("name", "email", "mobile", "created_at", "updated_at")
    search_fields = ("name", "email", "mobile")
    list_filter = ("created_at", "updated_at")
    ordering = ("name",)
    readonly_fields = ("created_at", "updated_at")

    fieldsets = (
        (None, {"fields": ("name", "email", "mobile", "address")}),
        ("Timestamps", {"fields": ("created_at", "updated_at")}),
    )
