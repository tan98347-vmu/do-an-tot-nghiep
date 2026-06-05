import os
from django.apps import AppConfig


class CompanyBackupsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'company_backups'
    verbose_name = 'Sao luu du lieu doanh nghiep'

    def ready(self):
        if os.environ.get('RUN_MAIN') != 'true' and not os.environ.get('COMPANY_BACKUPS_FORCE_START'):
            return
        if os.environ.get('COMPANY_BACKUPS_DISABLE_SCHEDULER') == '1':
            return
        try:
            from company_backups.services.scheduler import start_scheduler
            start_scheduler()
        except Exception as exc:
            import logging
            logging.getLogger(__name__).warning(
                '[company_backups] scheduler start failed: %s', exc,
            )
