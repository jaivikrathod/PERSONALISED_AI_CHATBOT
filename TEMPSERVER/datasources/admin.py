from django.contrib import admin

from .models import DataSource, DataSourceField, DataSourceSync


class DataSourceFieldInline(admin.TabularInline):
    model = DataSourceField
    extra = 0
    fields = ("name", "data_type", "is_exposed", "is_filterable", "is_sortable", "is_returned", "cardinality")
    readonly_fields = ("cardinality",)


@admin.register(DataSource)
class DataSourceAdmin(admin.ModelAdmin):
    list_display = ("id", "display_name", "name", "chatbot", "row_count", "is_published", "last_synced_at")
    list_filter = ("is_published", "adapter")
    search_fields = ("name", "display_name")
    readonly_fields = ("row_count", "last_synced_at", "created_at", "updated_at")
    inlines = [DataSourceFieldInline]


@admin.register(DataSourceSync)
class DataSourceSyncAdmin(admin.ModelAdmin):
    list_display = ("id", "data_source", "mode", "rows_in", "rows_upserted", "rows_rejected", "started_at")
    readonly_fields = [f.name for f in DataSourceSync._meta.fields]
