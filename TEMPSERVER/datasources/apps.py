from django.apps import AppConfig


class DatasourcesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "datasources"

    def ready(self):
        from . import signals  # noqa: F401
