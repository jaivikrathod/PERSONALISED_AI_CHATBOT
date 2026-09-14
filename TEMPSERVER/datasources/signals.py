"""Declaration-cache invalidation: any write to a published source's registry
rows recompiles its tool. Bulk writes skip signals, so the code that does them
(`ingest.py`) calls `refresh_tool` itself."""

from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .models import DataSource, DataSourceField
from .publishing import refresh_tool


@receiver(post_save, sender=DataSource)
def source_saved(sender, instance, raw=False, **kwargs):
    if not raw and instance.is_published:
        refresh_tool(instance)


@receiver(post_save, sender=DataSourceField)
@receiver(post_delete, sender=DataSourceField)
def field_changed(sender, instance, raw=False, **kwargs):
    if raw:
        return
    source = DataSource.objects.filter(id=instance.data_source_id, is_published=True).first()
    if source is not None:
        refresh_tool(source)
