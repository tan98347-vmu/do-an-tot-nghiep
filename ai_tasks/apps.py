import logging
import os

from django.apps import AppConfig


class AiTasksConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'ai_tasks'
    verbose_name = 'AI Task progress tracking'

    def ready(self):
        # === BEGIN R3: install dispatch handlers (idempotent, safe in tests) ===
        try:
            from ai_tasks.services.handlers import install_handlers
            install_handlers()
        except Exception as exc:
            logging.getLogger(__name__).warning(
                '[ai_tasks] install_handlers failed: %s', exc,
            )
        # === END R3 ===

        if (
            os.environ.get('RUN_MAIN') != 'true'
            and not os.environ.get('AI_TASKS_FORCE_START')
        ):
            return
        if os.environ.get('AI_TASKS_DISABLE_SCHEDULER') == '1':
            return
        try:
            from ai_tasks.services.scheduler import start_scheduler

            start_scheduler()
        except Exception as exc:
            logging.getLogger(__name__).warning(
                '[ai_tasks] scheduler start failed: %s',
                exc,
            )
