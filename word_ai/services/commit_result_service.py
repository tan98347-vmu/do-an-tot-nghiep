from django.core.files.base import ContentFile
from django.db import transaction

from documents.models import DocumentVersion
from documents.pdf_preview import schedule_document_preview_regeneration
from word_ai.services.event_log_service import append_job_event
from word_ai.services.job_transition_service import mark_completed


def commit_job_result(
    *,
    job,
    worker,
    uploaded_file,
    summary='',
    change_note='',
    content_text='',
    tool_transcript=None,
    verification_summary=None,
    artifact_manifest=None,
    document_checksums=None,
):
    if job.result_version_id and job.status == 'completed':
        return job.result_version

    file_bytes = uploaded_file.read()
    if hasattr(uploaded_file, 'seek'):
        uploaded_file.seek(0)

    version_name = f'document_{job.document_id}_v{job.document.version_number + 1}.docx'
    current_name = f'document_{job.document_id}_current.docx'

    with transaction.atomic():
        document = job.document.__class__.objects.select_for_update().get(pk=job.document_id)
        new_version_number = document.version_number + 1

        version = DocumentVersion(
            document=document,
            version_number=new_version_number,
            content=content_text or document.content or '',
            change_note=change_note or summary or 'Word AI edit',
            variables_used=document.versions.order_by('-version_number').first().variables_used
            if document.versions.exists()
            else {},
            created_by=job.requested_by,
        )
        version.save()
        version.output_file.save(version_name, ContentFile(file_bytes), save=True)

        document.version_number = new_version_number
        if content_text:
            document.content = content_text
        document.output_file.save(current_name, ContentFile(file_bytes), save=False)
        document.save(update_fields=['version_number', 'content', 'output_file', 'updated_at'])

        job.artifact_file.save(version_name, ContentFile(file_bytes), save=False)
        job.result_version = version
        job.tool_transcript = list(tool_transcript or [])
        job.verification_summary = dict(verification_summary or {})
        job.artifact_manifest = dict(artifact_manifest or {})
        job.document_checksums = dict(document_checksums or {})
        job.save(
            update_fields=[
                'artifact_file',
                'result_version',
                'tool_transcript',
                'verification_summary',
                'artifact_manifest',
                'document_checksums',
                'updated_at',
            ]
        )

    append_job_event(
        job,
        worker=worker,
        step='commit',
        status='version_created',
        message='Created a new document version from worker output.',
        payload={
            'version_number': new_version_number,
            'tool_transcript_count': len(job.tool_transcript or []),
            'verification_summary_keys': sorted((job.verification_summary or {}).keys()),
            'artifact_manifest_keys': sorted((job.artifact_manifest or {}).keys()),
            'document_checksums_keys': sorted((job.document_checksums or {}).keys()),
        },
    )
    schedule_document_preview_regeneration(document)
    mark_completed(job, worker=worker, summary=summary, change_note=change_note)
    return version
