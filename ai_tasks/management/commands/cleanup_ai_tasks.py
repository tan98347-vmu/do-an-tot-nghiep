from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from ai_tasks.services.scheduler import cleanup_finished_tasks


class Command(BaseCommand):
    help = 'Xoa AITaskProgress cu hon N ngay co status completed/failed/cancelled.'

    def add_arguments(self, parser):
        parser.add_argument('--days', type=int, default=7,
                            help='Giu lai task created_at >= now-N ngay.')
        parser.add_argument('--dry-run', action='store_true',
                            help='Khong xoa, chi liet ke.')

    def handle(self, *args, **options):
        days = int(options['days'])
        dry = bool(options['dry_run'])
        cutoff = timezone.now() - timedelta(days=days)
        count = cleanup_finished_tasks(days=days, dry_run=True)
        self.stdout.write(self.style.NOTICE(
            f'Found {count} task(s) older than {days} days (cutoff={cutoff.isoformat()}).'
        ))
        if dry:
            self.stdout.write(self.style.WARNING('Dry-run: skipping delete.'))
            return
        deleted = cleanup_finished_tasks(days=days, dry_run=False)
        self.stdout.write(self.style.SUCCESS(f'Deleted {deleted} record(s).'))
