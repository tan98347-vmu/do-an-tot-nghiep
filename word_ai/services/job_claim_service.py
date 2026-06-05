from django.db import transaction
from django.utils import timezone

from word_ai.models import WordEditJob, WordEditJobStatus, WordWorker, WordWorkerStatus
from word_ai.services.edit_mode_service import (
    DIRECT_EDIT_MODE,
    is_direct_addin_mcp_mode,
)
from word_ai.services.event_log_service import append_job_event
from word_ai.services.job_transition_service import mark_claimed, mark_failed, mark_needs_review
from word_ai.services.native_word_execution_payload_service import build_native_word_execution_payload


def claim_next_job(*, worker_key, slot_label, host_name='', metadata=None):
    with transaction.atomic():
        worker, _ = WordWorker.objects.select_for_update().get_or_create(
            worker_key=worker_key,
            defaults={
                'slot_label': slot_label,
                'host_name': host_name,
                'status': WordWorkerStatus.IDLE,
                'metadata': metadata or {},
            },
        )
        worker.slot_label = slot_label
        worker.host_name = host_name or worker.host_name
        worker.metadata = metadata or worker.metadata
        worker.last_seen_at = timezone.now()
        worker.save(update_fields=['slot_label', 'host_name', 'metadata', 'last_seen_at', 'updated_at'])

    queued_jobs = WordEditJob.objects.select_related('document', 'requested_by').filter(
        status=WordEditJobStatus.QUEUED
    ).order_by('created_at', 'id')

    for job in queued_jobs:
        try:
            if job.edit_mode == DIRECT_EDIT_MODE:
                mark_needs_review(job, reason='legacy_direct_edit_removed_from_production_runtime')
                continue
            if is_direct_addin_mcp_mode(job.edit_mode) and not job.execution_payload:
                if not job.plan_payload:
                    job.plan_payload = {
                        'mode': 'tool_loop',
                        'summary': 'Native Word tool-loop bootstrap context.',
                        'warnings': [],
                    }
                    job.plan_mode = 'tool_loop'
                execution_payload = build_native_word_execution_payload(job, job.plan_payload)
                job.mcp_session_id = execution_payload['session_id']
                job.execution_payload = execution_payload
                job.save(update_fields=['plan_payload', 'plan_mode', 'mcp_session_id', 'execution_payload', 'updated_at'])
            return mark_claimed(job, worker=worker), worker
        except Exception as exc:
            mark_failed(job, worker=worker, error_code='plan_failed', error_detail=str(exc), step='planning')
            continue

    worker.status = WordWorkerStatus.IDLE
    worker.save(update_fields=['status', 'updated_at'])
    return None, worker
