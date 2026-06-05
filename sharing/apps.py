from django.apps import AppConfig


class SharingConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'sharing'
    verbose_name = 'Co che chia se thong nhat'

    def ready(self):
        from . import signals  # noqa: F401
