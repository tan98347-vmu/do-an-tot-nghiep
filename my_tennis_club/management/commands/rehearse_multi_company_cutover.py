from django.contrib.auth.models import User
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import transaction

from accounts.models import Company
from ai_engine.models import ChatSession, KnowledgeBase
from document_templates.models import DocumentTemplate, TemplateCategory
from documents.models import Document
from signing.models import SignedPdfDocument


def _run_optional_command(stdout, style, *args):
    try:
        with transaction.atomic():
            call_command(*args, stdout=stdout)
    except Exception as exc:
        stdout.write(style.WARNING(f'{" ".join(str(arg) for arg in args)} warning: {exc}'))
        return False
    return True


class Command(BaseCommand):
    help = 'Run a lightweight cutover rehearsal for multi-company mode.'

    def add_arguments(self, parser):
        parser.add_argument('--apply-reindex', action='store_true')

    def handle(self, *args, **options):
        before_counts = {
            'users': User.objects.count(),
            'template_categories': TemplateCategory.objects.count(),
            'templates': DocumentTemplate.objects.count(),
            'documents': Document.objects.count(),
            'chat_sessions': ChatSession.objects.count(),
            'knowledge_bases': KnowledgeBase.objects.count(),
            'signed_pdfs': SignedPdfDocument.objects.count(),
        }

        call_command('seed_default_company', stdout=self.stdout)
        call_command('backfill_company_scope', stdout=self.stdout)
        _run_optional_command(self.stdout, self.style, 'rebuild_rag_index', '--dry-run')
        if options.get('apply_reindex'):
            _run_optional_command(self.stdout, self.style, 'rebuild_rag_index')

        default_company = Company.get_default()
        after_counts = {
            'users': User.objects.count(),
            'template_categories': TemplateCategory.objects.filter(company=default_company).count(),
            'templates': DocumentTemplate.objects.filter(company=default_company).count(),
            'documents': Document.objects.filter(company=default_company).count(),
            'chat_sessions': ChatSession.objects.filter(company=default_company).count(),
            'knowledge_bases': KnowledgeBase.objects.filter(company=default_company).count(),
            'signed_pdfs': SignedPdfDocument.objects.filter(company=default_company).count(),
        }

        self.stdout.write(self.style.SUCCESS('cutover rehearsal summary'))
        for key, before_value in before_counts.items():
            after_value = after_counts.get(key, 0)
            self.stdout.write(f' - {key}: before={before_value} | after_default_company={after_value}')
