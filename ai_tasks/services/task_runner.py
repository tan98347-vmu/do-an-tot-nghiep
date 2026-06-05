"""
Universal background task runner cho 9 tinh nang AI.
Thread + DB-poll pattern, ke thua tu company_backups/services/manager.py.
"""

import logging
import threading
import time
from threading import Lock
from typing import Any, Callable, Iterable, Optional

from django.contrib.auth.models import User
from django.db import close_old_connections, transaction
from django.utils import timezone

from ai_tasks.models import (
    AITaskProgress,
    CANCEL_MODE_HARD, CANCEL_MODE_SOFT,
    STATUS_CANCELLED, STATUS_COMPLETED, STATUS_FAILED,
    STATUS_QUEUED, STATUS_RUNNING,
)

logger = logging.getLogger(__name__)


class TaskCancelled(Exception):
    """Goi tu fn chinh khi check_cancel phat hien cancel_requested."""
    pass


_hard_sessions: dict[str, list] = {}
_hard_sessions_lock = Lock()

_stream_buffers: dict[str, list[str]] = {}
_stream_last_flush: dict[str, float] = {}
_stream_lock = Lock()


def create_task(
    *,
    user: User,
    task_type: str,
    cancel_mode: str = CANCEL_MODE_SOFT,
    related_entity_type: str = '',
    related_entity_id: Optional[int] = None,
) -> AITaskProgress:
    return AITaskProgress.objects.create(
        user=user,
        task_type=task_type,
        cancel_mode=cancel_mode,
        related_entity_type=related_entity_type,
        related_entity_id=related_entity_id,
        status=STATUS_QUEUED,
    )


def update_progress(task_id, percent: int, stage: str, detail: str = '') -> None:
    try:
        AITaskProgress.objects.filter(task_id=task_id).update(
            progress_percent=max(0, min(100, int(percent))),
            progress_stage=str(stage or '')[:64],
            progress_detail=str(detail or '')[:255],
            status=STATUS_RUNNING,
        )
    except Exception:
        logger.exception('[ai_tasks] update_progress failed task_id=%s', task_id)


def _task_cancel_snapshot(task_id) -> tuple[bool, str, str]:
    row = (
        AITaskProgress.objects
        .filter(task_id=task_id)
        .values_list('cancel_requested', 'cancel_mode', 'status')
        .first()
    )
    if not row:
        return False, CANCEL_MODE_SOFT, ''
    return bool(row[0]), str(row[1] or CANCEL_MODE_SOFT), str(row[2] or '')


def _task_is_force_cancelled(task_id) -> bool:
    cancel_requested, cancel_mode, current_status = _task_cancel_snapshot(task_id)
    return current_status == STATUS_CANCELLED or (
        cancel_requested and cancel_mode == CANCEL_MODE_HARD
    )


def check_cancel(task_id, *, include_hard: bool = False) -> None:
    """Raise TaskCancelled neu DB co cancel_requested + cancel_mode='soft'."""
    try:
        cancel_requested, cancel_mode, current_status = _task_cancel_snapshot(task_id)
        if current_status == STATUS_CANCELLED and include_hard:
            raise TaskCancelled('Task cancelled by user')
        if cancel_requested and (
            cancel_mode == CANCEL_MODE_SOFT
            or (include_hard and cancel_mode == CANCEL_MODE_HARD)
        ):
            raise TaskCancelled('Task cancelled by user')
    except TaskCancelled:
        raise
    except Exception:
        logger.exception('[ai_tasks] check_cancel failed task_id=%s', task_id)


def mark_completed(task_id, result: Optional[dict] = None) -> None:
    AITaskProgress.objects.filter(task_id=task_id).exclude(status=STATUS_CANCELLED).update(
        status=STATUS_COMPLETED,
        progress_percent=100,
        progress_stage='Hoan tat',
        progress_detail='',
        result=result or {},
        completed_at=timezone.now(),
        error_message='',
    )
    _flush_stream_buffer(task_id, force=True)
    _cleanup_task_resources(task_id)


def mark_failed(task_id, error: str) -> None:
    AITaskProgress.objects.filter(task_id=task_id).exclude(status=STATUS_CANCELLED).update(
        status=STATUS_FAILED,
        error_message=str(error or 'Unknown error')[:2000],
        progress_detail=f'Loi: {error}'[:255],
        completed_at=timezone.now(),
    )
    _flush_stream_buffer(task_id, force=True)
    _cleanup_task_resources(task_id)


def mark_cancelled(task_id) -> None:
    AITaskProgress.objects.filter(task_id=task_id).update(
        status=STATUS_CANCELLED,
        progress_detail='Da dung theo yeu cau',
        completed_at=timezone.now(),
    )
    _flush_stream_buffer(task_id, force=True)
    _cleanup_task_resources(task_id)


def append_stream_chunk(task_id, chunk: str) -> None:
    """Buffer chunk in-memory, flush DB moi 100ms de tranh hot write."""
    if not chunk:
        return
    task_id_str = str(task_id)
    with _stream_lock:
        _stream_buffers.setdefault(task_id_str, []).append(chunk)
        last = _stream_last_flush.get(task_id_str, 0.0)
        now = time.monotonic()
        if (now - last) >= 0.1:
            buf = _stream_buffers.pop(task_id_str, [])
            _stream_last_flush[task_id_str] = now
        else:
            return
    _persist_chunks(task_id_str, buf)


def _flush_stream_buffer(task_id, force: bool = False) -> None:
    task_id_str = str(task_id)
    with _stream_lock:
        buf = _stream_buffers.pop(task_id_str, [])
        _stream_last_flush.pop(task_id_str, None)
    if buf:
        _persist_chunks(task_id_str, buf)


def _persist_chunks(task_id_str: str, chunks: list[str]) -> None:
    if not chunks:
        return
    try:
        with transaction.atomic():
            task = (
                AITaskProgress.objects
                .select_for_update()
                .filter(task_id=task_id_str)
                .first()
            )
            if not task:
                return
            current = list(task.streaming_chunks or [])
            current.extend(chunks)
            task.streaming_chunks = current
            task.save(update_fields=['streaming_chunks', 'updated_at'])
    except Exception:
        logger.exception('[ai_tasks] persist_chunks failed task_id=%s', task_id_str)


def register_hard_session(task_id, session) -> None:
    """Dang ky requests.Session de close tu cancel handler."""
    task_id_str = str(task_id)
    with _hard_sessions_lock:
        _hard_sessions.setdefault(task_id_str, []).append(session)


def close_hard_session(task_id) -> None:
    task_id_str = str(task_id)
    with _hard_sessions_lock:
        sessions = _hard_sessions.pop(task_id_str, [])
    for session in sessions:
        try:
            session.close()
        except Exception:
            pass


def _cleanup_task_resources(task_id) -> None:
    task_id_str = str(task_id)
    with _hard_sessions_lock:
        _hard_sessions.pop(task_id_str, None)
    with _stream_lock:
        _stream_buffers.pop(task_id_str, None)
        _stream_last_flush.pop(task_id_str, None)


def request_cancel(task_id) -> bool:
    """Set flag cancel + close hard session neu cancel_mode=hard."""
    updated = AITaskProgress.objects.filter(task_id=task_id).update(cancel_requested=True)
    if not updated:
        return False
    row = (
        AITaskProgress.objects
        .filter(task_id=task_id)
        .values_list('cancel_mode', 'status')
        .first()
    )
    if row and row[0] == CANCEL_MODE_HARD:
        close_hard_session(task_id)
        AITaskProgress.objects.filter(task_id=task_id).update(
            status=STATUS_CANCELLED,
            progress_detail='Da dung (hard) theo yeu cau',
            completed_at=timezone.now(),
        )
        _flush_stream_buffer(task_id, force=True)
    return True


def run_in_thread(
    task: AITaskProgress,
    fn: Callable,
    *args,
    on_success: Optional[Callable[[Any], dict]] = None,
    **kwargs,
) -> None:
    """
    Spawn daemon thread chay fn(task_id, *args, **kwargs).
    fn co the raise TaskCancelled / Exception. Tu dong mark task accordingly.
    on_success(result_from_fn) -> dict de map ket qua thanh JSON luu vao task.result.
    """

    task_id = task.task_id
    AITaskProgress.objects.filter(task_id=task_id).update(status=STATUS_RUNNING)

    def _worker():
        try:
            ret = fn(task_id, *args, **kwargs)
            payload = on_success(ret) if on_success else (ret if isinstance(ret, dict) else {'result': ret})
            if _task_is_force_cancelled(task_id):
                mark_cancelled(task_id)
            else:
                mark_completed(task_id, payload)
        except TaskCancelled:
            mark_cancelled(task_id)
        except Exception as exc:
            if _task_is_force_cancelled(task_id):
                mark_cancelled(task_id)
            else:
                logger.exception('[ai_tasks] thread fn failed task_id=%s', task_id)
                mark_failed(task_id, f'{type(exc).__name__}: {exc}')
        finally:
            close_old_connections()

    thread = threading.Thread(
        target=_worker,
        daemon=True,
        name=f'ai_task_{task_id}',
    )
    thread.start()
