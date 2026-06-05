import json

from django.core.management.base import BaseCommand, CommandError

from word_ai.models import WordEditJob


def _ascii_json(value):
    return json.dumps(value, ensure_ascii=True, indent=2, sort_keys=True)


class Command(BaseCommand):
    help = 'Print the detailed Word AI planner/runtime trace for a job.'

    def add_arguments(self, parser):
        parser.add_argument('job_id', type=int)

    def handle(self, *args, **options):
        job_id = options['job_id']
        job = WordEditJob.objects.select_related(
            'document',
            'requested_by',
            'current_worker',
        ).prefetch_related('events').filter(pk=job_id).first()
        if job is None:
            raise CommandError(f'Word AI job {job_id} does not exist.')

        summary = {
            'job_id': job.id,
            'document_id': job.document_id,
            'document_title': job.document.title,
            'status': job.status,
            'instruction': job.instruction,
            'plan_mode': job.plan_mode,
            'edit_mode': job.edit_mode,
            'mcp_session_id': job.mcp_session_id,
            'llm_model_name': job.llm_model_name,
            'prompt_version': job.prompt_version,
            'error_code': job.error_code,
            'error_detail': job.error_detail,
            'created_at': job.created_at.isoformat() if job.created_at else '',
            'updated_at': job.updated_at.isoformat() if job.updated_at else '',
            'plan_payload': job.plan_payload,
            'execution_payload': job.execution_payload,
            'tool_transcript': job.tool_transcript,
            'verification_summary': job.verification_summary,
            'artifact_manifest': job.artifact_manifest,
            'document_checksums': job.document_checksums,
        }
        events = [
            {
                'id': event.id,
                'created_at': event.created_at.isoformat() if event.created_at else '',
                'level': event.level,
                'step': event.step,
                'status': event.status,
                'message': event.message,
                'worker_key': event.worker.worker_key if event.worker else '',
                'payload': event.payload,
            }
            for event in job.events.all()
        ]

        self.stdout.write(_ascii_json({'job': summary, 'events': events}))
