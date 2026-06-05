from io import StringIO
import json
import shutil
import uuid
from pathlib import Path

from django.contrib.auth.models import User
from django.core.files.base import ContentFile
from django.core.management import call_command
from django.test import TestCase
from django.test.utils import override_settings

from accounts.company_services import create_company_user
from accounts.models import (
    Company,
    CompanyRole,
    CompanyStatus,
    CompanyUserMembership,
    CompanyAIConfig,
    Department,
    UserGroup,
)
from ai_engine.models import ChatSession, KnowledgeBase
from document_templates.models import DocumentTemplate, TemplateCategory
from documents.models import Document
from signing.models import SigningSystemConfig
from word_ai.models import WordEditJob


class MultiCompanyManagementCommandTests(TestCase):
    def test_seed_platform_admin_is_idempotent(self):
        first = StringIO()
        second = StringIO()

        call_command(
            'seed_platform_admin',
            '--username',
            'platform_seed',
            '--email',
            'platform-seed@example.com',
            '--password',
            'seed-pass-123',
            stdout=first,
        )
        call_command(
            'seed_platform_admin',
            '--username',
            'platform_seed',
            '--email',
            'platform-seed@example.com',
            '--password',
            'seed-pass-123',
            stdout=second,
        )

        user = User.objects.get(username='platform_seed')
        self.assertTrue(user.is_superuser)
        self.assertTrue(user.is_staff)
        self.assertTrue(user.check_password('seed-pass-123'))
        self.assertTrue(user.profile.is_platform_admin_account)
        self.assertIn('platform admin created', first.getvalue())
        self.assertIn('platform admin updated', second.getvalue())

    def test_seed_default_company_creates_active_company_and_ai_config(self):
        out = StringIO()

        call_command('seed_default_company', stdout=out)

        company = Company.get_default()
        self.assertEqual(company.status, CompanyStatus.ACTIVE)
        self.assertTrue(CompanyAIConfig.objects.filter(company=company).exists())
        self.assertIn('default company ready', out.getvalue())

    def test_backfill_company_scope_populates_legacy_records(self):
        user = User.objects.create_user(
            username='legacy_user',
            password='secret123',
            email='legacy@example.com',
            first_name='Legacy',
            last_name='User',
        )
        user.profile.ma_nhan_vien = 'LEG-001'
        user.profile.save(update_fields=['ma_nhan_vien'])

        department = Department.objects.create(name='Legacy Dept', code='LD')
        group = UserGroup.objects.create(name='Legacy Group')
        category = TemplateCategory.objects.create(name='Legacy Category')
        template = DocumentTemplate.objects.create(
            owner=user,
            title='Legacy Template',
            content='Noi dung mau',
            category=category,
        )
        document = Document.objects.create(
            owner=user,
            title='Legacy Document',
            content='Noi dung van ban',
            template=template,
            category=category,
            visibility='private',
            share_status='active',
        )
        kb = KnowledgeBase.objects.create(
            owner=user,
            title='Legacy KB',
            content='Noi dung tri thuc',
        )
        session = ChatSession.objects.create(user=user, title='Legacy Chat')
        signing_config = SigningSystemConfig.objects.create()
        word_job = WordEditJob.objects.create(
            document=document,
            requested_by=user,
            instruction='Cap nhat van ban',
        )

        out = StringIO()
        call_command('backfill_company_scope', stdout=out)

        default_company = Company.get_default()
        membership = CompanyUserMembership.objects.get(user=user)
        self.assertEqual(membership.company_id, default_company.id)
        department.refresh_from_db()
        group.refresh_from_db()
        category.refresh_from_db()
        template.refresh_from_db()
        document.refresh_from_db()
        kb.refresh_from_db()
        session.refresh_from_db()
        signing_config.refresh_from_db()
        word_job.refresh_from_db()
        user.profile.refresh_from_db()
        self.assertEqual(user.profile.company_id, default_company.id)
        self.assertEqual(department.company_id, default_company.id)
        self.assertEqual(group.company_id, default_company.id)
        self.assertEqual(category.company_id, default_company.id)
        self.assertEqual(template.company_id, default_company.id)
        self.assertEqual(document.company_id, default_company.id)
        self.assertEqual(kb.company_id, default_company.id)
        self.assertEqual(session.company_id, default_company.id)
        self.assertEqual(signing_config.company_id, default_company.id)
        self.assertEqual(word_job.company_id, default_company.id)
        self.assertIn('backfill done', out.getvalue())

    def test_bootstrap_company_admin_resets_existing_admin(self):
        company = Company.objects.create(
            code='bootstrap-company',
            name='Bootstrap Company',
            status=CompanyStatus.ACTIVE,
        )
        bootstrap = create_company_user(
            company=company,
            local_username='admin',
            email='bootstrap@example.com',
            password='old-secret-123',
            role=CompanyRole.COMPANY_ADMIN,
            full_name='Bootstrap Admin',
        )

        out = StringIO()
        call_command('bootstrap_company_admin', '--company-id', str(company.pk), stdout=out)

        bootstrap.membership.refresh_from_db()
        bootstrap.user.refresh_from_db()
        self.assertTrue(bootstrap.membership.must_change_password)
        self.assertIn('bootstrap admin ready', out.getvalue())

    def test_export_company_bundle_exports_only_target_company_media_and_records(self):
        company_a = Company.objects.create(
            code='export-a',
            name='Export A',
            status=CompanyStatus.ACTIVE,
        )
        company_b = Company.objects.create(
            code='export-b',
            name='Export B',
            status=CompanyStatus.ACTIVE,
        )
        employee_a = create_company_user(
            company=company_a,
            local_username='employee_a',
            email='employee-a@example.com',
            password='secret12345',
            role=CompanyRole.COMPANY_USER,
            full_name='Employee A',
        )
        employee_b = create_company_user(
            company=company_b,
            local_username='employee_b',
            email='employee-b@example.com',
            password='secret12345',
            role=CompanyRole.COMPANY_USER,
            full_name='Employee B',
        )

        base_dir = Path('.codex-runtime') / f'command-export-{uuid.uuid4().hex}'
        media_root = base_dir / 'media-root'
        output_dir = base_dir / 'output'
        media_root.mkdir(parents=True, exist_ok=True)
        output_dir.mkdir(parents=True, exist_ok=True)

        try:
            with override_settings(MEDIA_ROOT=str(media_root.resolve())):
                employee_a.user.profile.avatar.save(
                    'avatar-a.png',
                    ContentFile(b'avatar-a'),
                    save=True,
                )
                employee_b.user.profile.avatar.save(
                    'avatar-b.png',
                    ContentFile(b'avatar-b'),
                    save=True,
                )

                out = StringIO()
                call_command(
                    'export_company_bundle',
                    '--company-code',
                    company_a.code,
                    '--output-dir',
                    str(output_dir),
                    stdout=out,
                )

                bundle_dir = output_dir / f'company_{company_a.code}'
                manifest = json.loads((bundle_dir / 'manifest.json').read_text(encoding='utf-8'))
                memberships = json.loads(
                    (bundle_dir / 'data' / 'accounts__CompanyUserMembership.json').read_text(encoding='utf-8')
                )
                avatar_a = bundle_dir / 'media' / employee_a.user.profile.avatar.name
                avatar_b = bundle_dir / 'media' / employee_b.user.profile.avatar.name

                self.assertEqual(manifest['company']['code'], company_a.code)
                self.assertEqual(len(memberships), 1)
                self.assertEqual(
                    memberships[0]['fields']['local_username'],
                    'employee_a',
                )
                self.assertTrue(avatar_a.exists())
                self.assertFalse(avatar_b.exists())
                self.assertIn('company export ready', out.getvalue())
        finally:
            shutil.rmtree(base_dir, ignore_errors=True)

    def test_rehearse_multi_company_cutover_outputs_summary(self):
        user = User.objects.create_user(
            username='rehearsal-user',
            password='secret123',
            email='rehearsal@example.com',
        )
        TemplateCategory.objects.create(name='Rehearsal Category')
        DocumentTemplate.objects.create(
            owner=user,
            title='Rehearsal Template',
            content='Noi dung mau',
        )
        Document.objects.create(
            owner=user,
            title='Rehearsal Document',
            content='Noi dung van ban',
            visibility='private',
            share_status='active',
        )
        ChatSession.objects.create(user=user, title='Rehearsal Chat')
        KnowledgeBase.objects.create(owner=user, title='Rehearsal KB', content='Tri thuc')

        out = StringIO()
        call_command('rehearse_multi_company_cutover', stdout=out)

        rendered = out.getvalue()
        self.assertIn('cutover rehearsal summary', rendered)
        self.assertIn('users: before=', rendered)
        self.assertIn('templates: before=', rendered)
