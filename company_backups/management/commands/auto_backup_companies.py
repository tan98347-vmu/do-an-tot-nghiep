from django.core.management.base import BaseCommand

from company_backups.services.scheduler import run_due_auto_backups_now


# class Command là lệnh quản trị 'auto_backup_companies': chạy ngay 1 lượt kiểm tra & tạo auto-backup cho các công ty đã bật auto_enabled (fallback khi APScheduler không chạy, có thể gọi từ Windows Task Scheduler).
# vd: python manage.py auto_backup_companies (đặt Task Scheduler chạy hằng ngày).
class Command(BaseCommand):
    help = (
        'Chay ngay 1 luot kiem tra & tao auto backup cho cac cong ty da bat auto_enabled. '
        'Co the goi tu Windows Task Scheduler nhu fallback neu APScheduler khong chay.'
    )

    # def handle gọi run_due_auto_backups_now() để thực thi một lượt auto-backup ngay lập tức.
    # vd: chạy lệnh -> các công ty tới hạn được sao lưu ngay.
    def handle(self, *args, **options):
        self.stdout.write('Running auto backup sweep...')
        run_due_auto_backups_now()
        self.stdout.write(self.style.SUCCESS('Done.'))
