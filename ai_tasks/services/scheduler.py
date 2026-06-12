'''
/scheduler.py:1 đang có tác dụng thật.

  Nó xóa các AITaskProgress:

  - Đã completed.
  - Đã failed.
  - Đã cancelled.
  - Cũ hơn 7 ngày.
'''

import logging
from datetime import timedelta
from threading import Lock

from django.utils import timezone

from ai_tasks.models import (
    AITaskProgress,
    STATUS_CANCELLED,
    STATUS_COMPLETED,
    STATUS_FAILED,
)

logger = logging.getLogger(__name__)

_scheduler = None
_scheduler_lock = Lock()


# def cleanup_finished_tasks để xóa các AITaskProgress đã kết thúc và cũ hơn N ngày (dry_run chỉ đếm).
# vd: cleanup_finished_tasks(days=7) -> xóa task completed/failed/cancelled quá 7 ngày.
def cleanup_finished_tasks(*, days: int = 7, dry_run: bool = False) -> int:
    cutoff = timezone.now() - timedelta(days=max(int(days or 7), 1))
    qs = AITaskProgress.objects.filter(
        created_at__lt=cutoff,
        status__in=[STATUS_COMPLETED, STATUS_FAILED, STATUS_CANCELLED],
    )
    count = qs.count()
    if dry_run:
        return count
    deleted, _ = qs.delete()
    return deleted


# def _job_cleanup_ai_tasks là job định kỳ gọi cleanup_finished_tasks và ghi log số dòng đã xóa.
# vd: chạy mỗi 03:00 hằng ngày.
def _job_cleanup_ai_tasks():
    removed = cleanup_finished_tasks(days=7, dry_run=False)
    logger.info('[ai_tasks] cleanup job removed %s stale task row(s).', removed)


# def start_scheduler để khởi động APScheduler chạy job dọn task lúc 03:00 mỗi ngày (bỏ qua nếu chưa cài apscheduler); idempotent.
# vd: gọi ở app ready() -> tạo 1 BackgroundScheduler duy nhất.
def start_scheduler():
    global _scheduler
    with _scheduler_lock:
        if _scheduler is not None:
            return _scheduler
        try:
            from apscheduler.schedulers.background import BackgroundScheduler
            from apscheduler.triggers.cron import CronTrigger
        except ImportError:
            logger.warning('[ai_tasks] apscheduler khong cai, skip scheduler.')
            return None

        scheduler = BackgroundScheduler(
            daemon=True,
            timezone=str(timezone.get_current_timezone()),
        )
        scheduler.add_job(
            _job_cleanup_ai_tasks,
            trigger=CronTrigger(hour=3, minute=0),
            id='ai_tasks_cleanup',
            replace_existing=True,
            max_instances=1,
            coalesce=True,
        )
        scheduler.start()
        _scheduler = scheduler
        logger.info('[ai_tasks] APScheduler started (daily 03:00 cleanup).')
        return _scheduler


# def stop_scheduler để tắt scheduler nếu đang chạy (dùng khi reload/teardown).
# vd: gọi khi tắt app -> shutdown scheduler.
def stop_scheduler():
    global _scheduler
    with _scheduler_lock:
        if _scheduler is not None:
            try:
                _scheduler.shutdown(wait=False)
            finally:
                _scheduler = None
