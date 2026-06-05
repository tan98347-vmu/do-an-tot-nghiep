from django.utils import timezone

from word_ai.models import WordEditJobStatus, WordWorkerStatus
from word_ai.services.event_log_service import append_job_event


IN_PROGRESS_STATUSES = {
    WordEditJobStatus.CLAIMED,
    WordEditJobStatus.EDITING,
    WordEditJobStatus.UPLOADING,
}


def mark_claimed(job, *, worker):
    job.status = WordEditJobStatus.CLAIMED
    job.current_worker = worker
    job.current_slot_label = worker.slot_label
    job.claimed_at = timezone.now()
    job.error_code = ''
    job.error_detail = ''
    job.save(
        update_fields=[
            'status',
            'current_worker',
            'current_slot_label',
            'claimed_at',
            'error_code',
            'error_detail',
            'updated_at',
        ]
    )
    worker.status = WordWorkerStatus.BUSY
    worker.save(update_fields=['status', 'updated_at'])
    append_job_event(
        job,
        worker=worker,
        step='claim',
        status=job.status,
        message='Worker claimed the job.',
    )
    return job


def mark_in_progress(job, *, worker, status, step, message='', payload=None, level='info'):
    if status not in IN_PROGRESS_STATUSES:
        raise ValueError(f'Unsupported in-progress status: {status}')
    job.status = status
    job.current_worker = worker
    job.current_slot_label = worker.slot_label
    job.save(
        update_fields=[
            'status',
            'current_worker',
            'current_slot_label',
            'updated_at',
        ]
    )
    worker.status = WordWorkerStatus.BUSY
    worker.save(update_fields=['status', 'updated_at'])
    append_job_event(
        job,
        worker=worker,
        step=step,
        status=job.status,
        message=message,
        payload=payload or {},
        level=level,
    )
    return job


def mark_failed(
    job,
    *,
    error_code,
    error_detail='',
    worker=None,
    step='failed',
    payload=None,
    tool_transcript=None,
    verification_summary=None,
):
    job.status = WordEditJobStatus.FAILED
    job.error_code = error_code
    job.error_detail = error_detail
    job.failed_at = timezone.now()
    update_fields = [
        'status',
        'error_code',
        'error_detail',
        'failed_at',
        'updated_at',
    ]
    if tool_transcript is not None:
        job.tool_transcript = list(tool_transcript or [])
        update_fields.append('tool_transcript')
    if verification_summary is not None:
        job.verification_summary = dict(verification_summary or {})
        update_fields.append('verification_summary')
    job.save(update_fields=update_fields)
    if worker:
        worker.status = WordWorkerStatus.IDLE
        worker.save(update_fields=['status', 'updated_at'])
    append_job_event(
        job,
        worker=worker,
        step=step,
        status=job.status,
        message=error_detail or error_code,
        payload={
            'error_code': error_code,
            'error_detail': error_detail,
            **(payload or {}),
        },
        level='error',
    )
    return job


def mark_needs_review(job, *, reason, worker=None):
    job.status = WordEditJobStatus.NEEDS_REVIEW
    job.error_code = 'needs_review'
    job.error_detail = reason
    job.failed_at = timezone.now()
    job.save(
        update_fields=[
            'status',
            'error_code',
            'error_detail',
            'failed_at',
            'updated_at',
        ]
    )
    append_job_event(
        job,
        worker=worker,
        step='planning',
        status=job.status,
        message='Job requires manual review.',
        payload={'reason': reason},
        level='warning',
    )
    return job


def mark_cancelled(job, *, user=None):
    job.status = WordEditJobStatus.CANCELLED
    job.cancelled_at = timezone.now()
    job.save(update_fields=['status', 'cancelled_at', 'updated_at'])
    append_job_event(
        job,
        step='cancel',
        status=job.status,
        message='Job cancelled by user.',
        payload={'cancelled_by_user_id': getattr(user, 'id', None)},
    )
    return job


def mark_completed(job, *, summary='', change_note='', worker=None):
    job.status = WordEditJobStatus.COMPLETED
    job.result_summary = summary
    job.change_note = change_note
    job.completed_at = timezone.now()
    job.save(
        update_fields=[
            'status',
            'result_summary',
            'change_note',
            'completed_at',
            'updated_at',
        ]
    )
    if worker:
        worker.status = WordWorkerStatus.IDLE
        worker.save(update_fields=['status', 'updated_at'])
    append_job_event(
        job,
        worker=worker,
        step='complete',
        status=job.status,
        message='Worker completed the job.',
        payload={'summary': summary, 'change_note': change_note},
    )
    return job
