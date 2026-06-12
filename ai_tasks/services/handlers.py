"""r3/M6 + r5 — Register cac task kind cho dispatch_task.

Cac handler nhe tai day; logic nang van nam o module nghiep vu, handler chi orchestrate.

note: file này hiện không phân luồng tác vụ UI thực tế nào và gần như là code chưa được sử dụng trong production flow.
"""

from __future__ import annotations

import logging

from ai_tasks.models import AITaskProgress
from ai_tasks.services.runner import (
    complete_task,
    fail_task,
    register_handler,
    update_task_progress,
)

log = logging.getLogger(__name__)


# --- echo (smoke test) ---
# def _echo_handler là handler smoke-test: cập nhật tiến độ rồi hoàn tất với chính payload (echo).
# vd: payload={'x':1} -> result={'echo':{'x':1}}.
def _echo_handler(task: AITaskProgress, payload: dict) -> None:
    update_task_progress(task.task_id, percent=50, stage='echo', detail='processing')
    complete_task(task.task_id, result={'echo': payload})


# --- company_backup_export (r5/M10) ---
# def _company_backup_export_handler là handler chạy pipeline xuất backup công ty chạy ngầm (đồng bộ trong handler để báo tiến độ).
# vd: payload={'company_id':1,'components':[...],'kind':'manual'} -> tạo backup và trả backup_id.
def _company_backup_export_handler(task: AITaskProgress, payload: dict) -> None:
    """Pipeline backup chay ngam.

    payload schema: {'company_id': int, 'components': [str], 'kind': 'manual'|'auto'}
    """
    from accounts.models import Company
    from company_backups.services.manager import create_backup

    company_id = int(payload.get('company_id') or 0)
    if not company_id:
        fail_task(task.task_id, error_message='Thieu company_id')
        return

    company = Company.objects.filter(pk=company_id).first()
    if company is None:
        fail_task(task.task_id, error_message=f'Company #{company_id} khong ton tai')
        return

    components = list(payload.get('components') or [])
    kind = (payload.get('kind') or 'manual').strip()

    update_task_progress(task.task_id, percent=5, stage='dispatch', detail='Khoi tao backup')
    try:
        record = create_backup(
            company=company,
            components=components,
            kind=kind,
            user=task.user,
            async_run=False,  # chay sync trong handler de progress di qua task
        )
    except Exception as exc:
        log.exception('[handlers] backup pipeline failed')
        fail_task(task.task_id, error_message=str(exc))
        return

    complete_task(
        task.task_id,
        result={
            'backup_id': record.pk,
            'file_path': record.file_path,
            'size_bytes': record.size_bytes,
            'is_encrypted': bool(getattr(record, 'encryption_meta', None)),
            'signature_status': getattr(record, 'signature_status', 'unsigned'),
        },
    )


# Map kind -> handler. Goi `install_handlers()` o app ready().
_DEFAULT_HANDLERS = {
    'echo': _echo_handler,
    'company_backup_export': _company_backup_export_handler,
}


# def install_handlers để đăng ký toàn bộ handler mặc định (idempotent), gọi ở app ready().
# vd: gọi 1 lần khi khởi động -> 'echo' và 'company_backup_export' sẵn sàng nhận dispatch.
def install_handlers() -> None:
    """Register tat ca handler. Idempotent."""
    for kind, fn in _DEFAULT_HANDLERS.items():
        register_handler(kind, fn)
    log.info('[ai_tasks] Registered %d handlers: %s', len(_DEFAULT_HANDLERS), list(_DEFAULT_HANDLERS))
