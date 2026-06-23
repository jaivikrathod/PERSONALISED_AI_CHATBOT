from django.contrib import admin

from .models import Company, UserCompany


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ("name", "email", "status", "is_deleted", "created_at")
    list_filter = ("status", "is_deleted")
    search_fields = ("name", "email")
    readonly_fields = ("uuid", "created_at", "updated_at")


@admin.register(UserCompany)
class UserCompanyAdmin(admin.ModelAdmin):
    list_display = ("user", "company", "role", "created_at")
    list_filter = ("role", "company")
    search_fields = ("user__email", "company__name")
    readonly_fields = ("uuid", "created_at", "updated_at")
