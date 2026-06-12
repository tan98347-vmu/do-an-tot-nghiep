import logging
from datetime import timedelta
from threading import Lock

from django.utils import timezone

logger = logging.getLogger(__name__)

_scheduler = None
_scheduler_lock = Lock()


# def _job_run_due_auto_backups là job định kỳ: duyệt các công ty bật auto_enabled; công ty nào đã tới hạn (quá auto_interval_days kể từ lần auto gần nhất) thì tạo backup auto (đủ thành phần), cập nhật mốc thời gian, rồi dọn bớt theo retention.
# vd: công ty A đặt 30 ngày, lần cuối 31 ngày trước -> tạo 1 backup auto + xóa bản cũ vượt số lượng giữ lại.
def _job_run_due_auto_backups():
    from company_backups.models import (
        CompanyBackupSettings, KIND_AUTO,
    )
    from company_backups.services.components import ALL_COMPONENTS
    from company_backups.services.manager import create_backup, enforce_retention

    now = timezone.now()
    qs = CompanyBackupSettings.objects.filter(auto_enabled=True)
    for s in qs.select_related('company'):
        company = s.company
        if not company or s.company_id is None:
            continue
        interval = max(int(s.auto_interval_days or 30), 1)
        if s.last_auto_run_at and (now - s.last_auto_run_at) < timedelta(days=interval):
            continue
        try:
            logger.info('[company_backups] auto backup start company=%s', company.code)
            create_backup(
                company=company,
                components=list(ALL_COMPONENTS),
                kind=KIND_AUTO,
                user=None,
                async_run=False,
            )
            s.last_auto_run_at = now
            s.save(update_fields=['last_auto_run_at', 'updated_at'])
            removed = enforce_retention(company, s.retention_count, kind=KIND_AUTO)
            logger.info(
                '[company_backups] auto backup done company=%s pruned=%d',
                company.code, removed,
            )
        except Exception as exc:
            logger.exception(
                '[company_backups] auto backup failed company=%s: %s',
                company.code, exc,
            )


# def run_due_auto_backups_now chạy ngay 1 lượt job auto-backup (dùng cho management command và test).
# vd: gọi từ lệnh auto_backup_companies hoặc Windows Task Scheduler.
def run_due_auto_backups_now():
    """Public helper cho management command & test."""
    _job_run_due_auto_backups()


# def start_scheduler khởi động APScheduler chạy job auto-backup mỗi 6 giờ (bỏ qua nếu chưa cài apscheduler); idempotent — chỉ tạo 1 scheduler.
# vd: app ready() -> nền tự kiểm tra & sao lưu công ty tới hạn mỗi 6h.
def start_scheduler():
    global _scheduler
    with _scheduler_lock:
        if _scheduler is not None:
            return _scheduler
        try:
            from apscheduler.schedulers.background import BackgroundScheduler
            from apscheduler.triggers.interval import IntervalTrigger
        except ImportError:
            logger.warning('[company_backups] apscheduler khong cai, skip scheduler.')
            return None

        scheduler = BackgroundScheduler(daemon=True, timezone=str(timezone.get_current_timezone()))
        scheduler.add_job(
            _job_run_due_auto_backups,
            trigger=IntervalTrigger(hours=6),
            id='company_backups_auto_run',
            replace_existing=True,
            max_instances=1,
            coalesce=True,
        )
        scheduler.start()
        _scheduler = scheduler
        logger.info('[company_backups] APScheduler started (interval 6h).')
        return _scheduler


# def stop_scheduler tắt scheduler nếu đang chạy (dùng khi reload/teardown).
# vd: gọi khi tắt app -> shutdown scheduler.
def stop_scheduler():
    global _scheduler
    with _scheduler_lock:
        if _scheduler is not None:
            try:
                _scheduler.shutdown(wait=False)
            finally:
                _scheduler = None
