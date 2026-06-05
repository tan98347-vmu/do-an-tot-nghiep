from __future__ import annotations

from django.core.management.base import BaseCommand


def _normalize_text(value) -> str:
    return ' '.join(str(value or '').strip().lower().split())


def _detect_usage_scopes(prompt) -> list[str]:
    haystack = ' | '.join(
        _normalize_text(value)
        for value in [
            getattr(prompt, 'title', ''),
            getattr(getattr(prompt, 'category', None), 'name', ''),
            getattr(prompt, 'tags', ''),
            getattr(prompt, 'system_content', ''),
            getattr(prompt, 'rules_content', ''),
        ]
        if value
    )

    scopes: list[str] = []

    if any(token in haystack for token in ('tom tat', 'summary', 'tong hop')):
        scopes.append('summary')
    if any(token in haystack for token in ('word ai', 'rewrite', 'edit', 'chinh sua', 'viet lai')):
        scopes.append('word_ai_edit')
    if any(token in haystack for token in ('chat', 'assistant', 'tro ly', 'hoi thoai')):
        scopes.append('chat')
    if any(token in haystack for token in ('compliance', 'tuan thu', 'checklist')):
        scopes.append('compliance_check')

    if not scopes:
        scopes.append('template_fill')

    ordered = []
    for scope in ('template_fill', 'summary', 'word_ai_edit', 'chat', 'compliance_check'):
        if scope in scopes and scope not in ordered:
            ordered.append(scope)
    return ordered


class Command(BaseCommand):
    help = 'Backfill Prompt.usage_scope cho du lieu cu theo heuristics title/category/tags.'

    def add_arguments(self, parser):
        parser.add_argument('--batch', type=int, default=500)
        parser.add_argument('--dry-run', action='store_true')

    def handle(self, *args, **options):
        from prompts.models import Prompt

        batch_size = int(options['batch'])
        dry_run = bool(options['dry_run'])

        qs = Prompt.objects.select_related('category').order_by('pk')
        processed = 0
        updated = 0

        for prompt in qs.iterator(chunk_size=batch_size):
            current_scopes = list(getattr(prompt, 'usage_scope', []) or [])
            if current_scopes and current_scopes != ['template_fill']:
                processed += 1
                continue

            new_scopes = _detect_usage_scopes(prompt)
            if current_scopes == new_scopes:
                processed += 1
                continue

            if not dry_run:
                prompt.usage_scope = new_scopes
                prompt.save(update_fields=['usage_scope', 'updated_at'])
            updated += 1
            processed += 1

            if processed % batch_size == 0:
                self.stdout.write(f'... processed {processed} prompt(s), updated={updated}')

        self.stdout.write(
            self.style.SUCCESS(
                f'Hoan tat backfill prompt scopes. processed={processed} updated={updated} dry_run={dry_run}'
            )
        )
