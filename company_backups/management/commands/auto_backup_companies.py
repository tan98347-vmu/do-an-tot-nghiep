from django.core.management.base import BaseCommand

from company_backups.services.scheduler import run_due_auto_backups_now


class Command(BaseCommand):
    help = (
        'Chay ngay 1 luot kiem tra & tao auto backup cho cac cong ty da bat auto_enabled. '
        'Co the goi tu Windows Task Scheduler nhu fallback neu APScheduler khong chay.'
    )

    def handle(self, *args, **options):
        self.stdout.write('Running auto backup sweep...')
        run_due_auto_backups_now()
        self.stdout.write(self.style.SUCCESS('Done.'))
