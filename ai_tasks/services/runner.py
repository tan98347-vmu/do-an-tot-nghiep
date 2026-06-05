from __future__ import annotations

import logging
import threading
from typing import Callable

from django.db import close_old_connections
from django.utils import timezone

from ai_tasks.models import (
    AITaskProgress,
    STATUS_CANCELLED,
    STATUS_COMPLETED,
    STATUS_FAILED,
    STATUS_QUEUED,
    STATUS_RUNNING,
    validate_deeplink,
)

log = logging.getLogger(__name__)

TASK_HANDLERS: dict[str, Callable[[AITaskProgress, dict], None]] = {}


def register_handler(kind: str, fn: Callable[[AITaskProgress, dict], None]) -> None:
    TASK_HANDLERS[kind] = fn


def dispatch_task(
    kind: str,
    user,
    payload: dict,
    *,
    deeplink: str,
    title: str,
    client_request_id: str | None = None,
    related_entity_type: str = '',
    related_entity_id: int | None = None,
) -> str:
    validate_deeplink(deeplink)
    payload = payload if isinstance(payload, dict) else {}
    normalized_request_id = (client_request_id or '').strip()
    if normalized_request_id:
        existing = AITaskProgress.objects.filter(
            user=user,
            client_request_id=normalized_request_id,
        ).first()
        if existing is not None:
            return str(existing.task_id)

    task = AITaskProgress.objects.create(
        user=user,
        task_type=kind,
        status=STATUS_QUEUED,
        deeplink=deeplink,
        title_summary=(title or '').strip()[:255],
        client_request_id=normalized_request_id,
        related_entity_type=(related_entity_type or '').strip()[:32],
        related_entity_id=related_entity_id,
        result={'request_payload': payload},
    )
    thread = threading.Thread(
        target=_run_task,
        args=(str(task.task_id), payload),
        daemon=True,
        name=f'ai_task_dispatch_{task.task_id}',
    )
    thread.start()
    return str(task.task_id)


def update_task_progress(task_id: str, *, percent: int, stage: str = '', detail: str = '') -> None:
    AITaskProgress.objects.filter(task_id=task_id).exclude(
        status__in=[STATUS_COMPLETED, STATUS_FAILED, STATUS_CANCELLED],
    ).update(
        status=STATUS_RUNNING,
        progress_percent=max(0, min(100, int(percent))),
        progress_stage=str(stage or '')[:64],
        progress_detail=str(detail or '')[:255],
        updated_at=timezone.now(),
    )


def complete_task(task_id: str, *, result: dict) -> None:
    qs = AITaskProgress.objects.filter(task_id=task_id)
    task = qs.values('cancel_requested').first()
    now = timezone.now()
    if task and task['cancel_requested']:
        qs.update(
            status=STATUS_CANCELLED,
            progress_detail='Đã dừng theo yêu cầu.',
            completed_at=now,
            updated_at=now,
        )
        return
    qs.update(
        status=STATUS_COMPLETED,
        result=result if isinstance(result, dict) else {},
        progress_percent=100,
        completed_at=now,
        updated_at=now,
        error_message='',
    )


def fail_task(task_id: str, *, error_message: str) -> None:
    qs = AITaskProgress.objects.filter(task_id=task_id)
    task = qs.values('cancel_requested').first()
    now = timezone.now()
    if task and task['cancel_requested']:
        qs.update(
            status=STATUS_CANCELLED,
            progress_detail='Đã dừng theo yêu cầu.',
            completed_at=now,
            updated_at=now,
        )
        return
    qs.update(
        status=STATUS_FAILED,
        error_message=str(error_message or 'Unknown error')[:2000],
        completed_at=now,
        updated_at=now,
    )


def _run_task(task_id: str, payload: dict) -> None:
    try:
        task = AITaskProgress.objects.get(task_id=task_id)
        if task.cancel_requested:
            fail_task(task_id, error_message='Task was cancelled before start.')
            return
        task.status = STATUS_RUNNING
        task.updated_at = timezone.now()
        task.save(update_fields=['status', 'updated_at'])
        handler = TASK_HANDLERS.get(task.task_type)
        if handler is None:
            fail_task(task_id, error_message=f'No handler registered for "{task.task_type}".')
            return
        handler(task, payload)
    except Exception as exc:
        log.exception('Background task failed: %s', task_id)
        fail_task(task_id, error_message=str(exc))
    finally:
        close_old_connections()


def _not_integrated_handler(task: AITaskProgress, payload: dict) -> None:
    raise RuntimeError(
        f'Task kind "{task.task_type}" is exposed by r3 but has not been integrated by its owning module yet.',
    )


for _default_kind in (
    'voice_chat',
    'bulk_template_upload',
    'document_summary',
    'compliance_check',
    'word_ai_edit',
    'company_backup_export',
):
    TASK_HANDLERS.setdefault(_default_kind, _not_integrated_handler)
