from django.db import transaction
from rest_framework.exceptions import PermissionDenied, ValidationError

from accounts.permissions import can_edit_document, get_accessible_prompts
from accounts.tenancy import get_user_company
from documents.models import Document
from prompts.models import Prompt
from word_ai.models import WordEditJob, WordEditJobStatus
from word_ai.services.config_service import current_llm_snapshot
from word_ai.services.edit_mode_service import normalize_word_ai_edit_mode
from word_ai.services.event_log_service import append_job_event
from word_ai.services.worker_runtime_service import (
    ACTIVE_WORKER_MAX_AGE_SECONDS,
    active_word_worker_count,
)


ACTIVE_JOB_STATUSES = {
    WordEditJobStatus.QUEUED,
    WordEditJobStatus.CLAIMED,
    WordEditJobStatus.EDITING,
    WordEditJobStatus.UPLOADING,
}


def create_word_edit_job(
    *,
    user,
    document_id,
    instruction,
    prompt_id=None,
    edit_mode='direct_addin_mcp',
    track_changes=False,
    preferred_slot='',
):
    company = get_user_company(user)
    document_qs = Document.objects.filter(pk=document_id)
    if company is not None:
        document_qs = document_qs.filter(company=company)
    document = document_qs.first()
    if document is None:
        raise ValidationError({'document_id': 'Document does not exist.'})
    if not can_edit_document(user, document):
        raise PermissionDenied('You do not have permission to edit this document.')
    if not instruction.strip():
        raise ValidationError({'instruction': 'Instruction is required.'})
    try:
        normalized_edit_mode = normalize_word_ai_edit_mode(edit_mode)
    except ValueError as exc:
        raise ValidationError({'edit_mode': str(exc)}) from exc
    if WordEditJob.objects.filter(document=document, status__in=ACTIVE_JOB_STATUSES).exists():
        raise ValidationError({'document_id': 'This document already has an active Word AI job.'})

    applied_prompt = None
    instruction_text = instruction.strip()
    if prompt_id:
        applied_prompt = Prompt.objects.filter(pk=prompt_id).first()
        if applied_prompt is None:
            raise ValidationError({'prompt_id': 'Prompt does not exist.'})
        if not get_accessible_prompts(user).filter(pk=prompt_id).exists():
            raise PermissionDenied('You do not have permission to use this prompt.')
        if 'word_ai_edit' not in (applied_prompt.usage_scope or []):
            raise ValidationError({'prompt_id': 'Prompt not scoped for word_ai_edit.'})

        prompt_sections = [
            str(applied_prompt.system_content or '').strip(),
            str(applied_prompt.rules_content or '').strip(),
            instruction_text,
        ]
        instruction_text = '\n\n'.join(section for section in prompt_sections if section)

    snapshot = current_llm_snapshot(user=user)
    with transaction.atomic():
        job = WordEditJob.objects.create(
            document=document,
            company=document.company,
            requested_by=user,
            instruction=instruction_text,
            applied_prompt=applied_prompt,
            edit_mode=normalized_edit_mode,
            track_changes=bool(track_changes),
            preferred_slot=(preferred_slot or '').strip(),
            **snapshot,
        )
    append_job_event(
        job,
        step='create',
        status=job.status,
        message='Word AI job created.',
        payload={
            'edit_mode': job.edit_mode,
            'applied_prompt_id': getattr(applied_prompt, 'id', None),
            'applied_prompt_title': getattr(applied_prompt, 'title', ''),
            'preferred_slot': job.preferred_slot,
            'track_changes': job.track_changes,
        },
    )
    active_worker_count = active_word_worker_count()
    if active_worker_count <= 0:
        append_job_event(
            job,
            level='warning',
            step='dispatch',
            status=job.status,
            message='No active Word worker is connected. The job will stay queued until the local agent heartbeats.',
            payload={
                'active_worker_count': active_worker_count,
                'heartbeat_timeout_seconds': ACTIVE_WORKER_MAX_AGE_SECONDS,
            },
        )
    return job
