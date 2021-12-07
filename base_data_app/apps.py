from django.apps import AppConfig


class BaseDataAppConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "base_data_app"
    verbose_name = "Base Data"
