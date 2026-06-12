from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from ai_tasks.services.scheduler import cleanup_finished_tasks


# class Command là lệnh quản trị 'cleanup_ai_tasks' để xóa AITaskProgress cũ đã kết thúc (completed/failed/cancelled).
# vd: python manage.py cleanup_ai_tasks --days 7.
class Command(BaseCommand):
    help = 'Xoa AITaskProgress cu hon N ngay co status completed/failed/cancelled.'

    # def add_arguments để khai báo --days (giữ lại task mới hơn N ngày) và --dry-run (chỉ liệt kê, không xóa).
    # vd: --days 30 --dry-run.
    def add_arguments(self, parser):
        parser.add_argument('--days', type=int, default=7,
                            help='Giu lai task created_at >= now-N ngay.')
        parser.add_argument('--dry-run', action='store_true',
                            help='Khong xoa, chi liet ke.')

    # def handle để đếm số task quá hạn rồi xóa (hoặc chỉ in nếu --dry-run); in kết quả.
    # vd: --dry-run -> 'Found N task(s)...'; chạy thật -> 'Deleted N record(s)'.
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
