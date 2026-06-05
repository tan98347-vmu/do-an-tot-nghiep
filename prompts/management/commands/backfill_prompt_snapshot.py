from django.core.management.base import BaseCommand
from django.db.models import Q
from django.utils import timezone


class Command(BaseCommand):
    help = 'Backfill Document.applied_prompt_snapshot tu Prompt cu cho cac Document chua co snapshot.'

    def add_arguments(self, parser):
        parser.add_argument('--batch', type=int, default=500)
        parser.add_argument('--dry-run', action='store_true')

    def handle(self, *args, **options):
        from documents.models import Document

        batch_size = int(options['batch'])
        dry_run = bool(options['dry_run'])

        qs = (
            Document.all_objects
            .filter(prompt__isnull=False)
            .filter(Q(applied_prompt_snapshot__isnull=True) | Q(applied_prompt_snapshot={}))
            .order_by('pk')
        )
        total = qs.count()
        self.stdout.write(self.style.NOTICE(
            f'Found {total} document(s) needing snapshot backfill (batch={batch_size}, dry_run={dry_run}).'
        ))

        processed = 0
        for doc in qs.iterator(chunk_size=batch_size):
            prompt = doc.prompt
            snapshot = {
                'prompt_id': prompt.pk,
                'title': prompt.title,
                'system_content': prompt.system_content or '',
                'rules_content': prompt.rules_content or '',
                'raw_user_text': (getattr(prompt, 'original_raw_text', '') or '')[:4096],
                'sanitized_user_text': '',
                'safety_score': float(getattr(prompt, 'safety_score', 0.0) or 0.0),
                'safety_flags': list(getattr(prompt, 'safety_flags', []) or []),
                'sanitized_at': timezone.now().isoformat(),
                'backfilled': True,
            }
            if not dry_run:
                doc.applied_prompt_snapshot = snapshot
                doc.save(update_fields=['applied_prompt_snapshot', 'updated_at'])
            processed += 1
            if processed % batch_size == 0:
                self.stdout.write(f'... processed {processed}/{total}')

        self.stdout.write(self.style.SUCCESS(
            f'Done. Processed {processed} document(s). dry_run={dry_run}'
        ))
