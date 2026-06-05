import shutil
import uuid
from pathlib import Path

from django.conf import settings
from django.contrib.auth.models import User
from django.core.files.base import ContentFile
from django.test import TestCase, override_settings
from django.urls import reverse

from accounts.models import Company, CompanyStatus, CompanyUserMembership
from ai_tasks.models import AITaskProgress, STATUS_COMPLETED
from document_templates.models import DocumentTemplate, TemplateReviewNotification
from documents.models import (
    DOC_STATUS_FINAL,
    MAILBOX_STATUS_VIEW,
    SHARE_ACTIVE,
    Document,
    DocumentMailboxEntry,
    DocumentMailboxThread,
)
from prompts.models import PROMPT_STATUS_PENDING, Prompt
from signing.models import (
    PACKET_ACTIVE,
    PROPOSAL_APPROVED,
    SIGNATURE_MODE_PDF_PKCS7,
    TASK_AVAILABLE,
    SigningPacket,
    SigningProposal,
    SigningTask,
)


@override_settings(SIGNING_DEFAULT_SIGNATURE_MODE='pdf_pkcs7')
class AggregateNotificationApiTests(TestCase):
    PDF_BYTES = b'%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF'

    def _make_media_root(self):
        media_root = Path(settings.BASE_DIR) / '.codex-tmp-pyc' / f'test-notify-{uuid.uuid4().hex}'
        media_root.mkdir(parents=True, exist_ok=True)
        return media_root

    def _create_company(self, code='notify-tests'):
        return Company.objects.create(
            code=code,
            name='Notify Tests',
            status=CompanyStatus.ACTIVE,
        )

    def _assign_company(self, user, company, *, role='company_user'):
        return CompanyUserMembership.objects.create(
            company=company,
            user=user,
            local_username=user.username,
            role=role,
            is_active=True,
        )

    def _create_document(self, owner, title):
        document = Document.objects.create(
            title=title,
            owner=owner,
            status=DOC_STATUS_FINAL,
            share_status=SHARE_ACTIVE,
            visibility='private',
            version_number=1,
        )
        document.output_file.save(
            f'{title.lower().replace(" ", "_")}.docx',
            ContentFile(b'docx-binary-placeholder'),
            save=True,
        )
        return document

    def test_aggregate_notifications_include_actionable_sources(self):
        company = self._create_company()
        owner = User.objects.create_user(username='owner', password='secret')
        sender = User.objects.create_user(username='sender', password='secret')
        reviewer = User.objects.create_user(username='reviewer', password='secret')
        self._assign_company(owner, company)
        self._assign_company(sender, company)
        self._assign_company(reviewer, company)

        template = DocumentTemplate.objects.create(
            owner=owner,
            title='Mau hop dong',
            description='',
            content='<p>Noi dung</p>',
            source_type=DocumentTemplate.SOURCE_MANUAL,
            status='approved',
            visibility='private',
        )
        notification = TemplateReviewNotification.objects.create(
            recipient=owner,
            template=template,
            action='reject',
            actor=reviewer,
            comment='Can bo sung thong tin',
        )

        task = AITaskProgress.objects.create(
            user=owner,
            task_type='summary',
            status=STATUS_COMPLETED,
            title_summary='Tom tat hop dong',
            deeplink='/documents/99',
            result={},
        )

        media_root = self._make_media_root()
        try:
            with override_settings(MEDIA_ROOT=str(media_root)):
                document = self._create_document(sender, 'Thong bao ky so')
                proposal = SigningProposal.objects.create(
                    document=document,
                    source_version_number=document.version_number,
                    proposed_by=sender,
                    proposal_note='demo',
                    status=PROPOSAL_APPROVED,
                )
                packet = SigningPacket(
                    proposal=proposal,
                    document=document,
                    source_version_number=document.version_number,
                    source_docx_sha256='abc123',
                    pdf_hash='pdfhash',
                    signature_mode=SIGNATURE_MODE_PDF_PKCS7,
                    status=PACKET_ACTIVE,
                    current_step=1,
                )
                packet.pdf_snapshot.save('snapshot.pdf', ContentFile(self.PDF_BYTES), save=False)
                packet.working_pdf.save('working.pdf', ContentFile(self.PDF_BYTES), save=False)
                packet.save()
                SigningTask.objects.create(
                    packet=packet,
                    signer_user=owner,
                    display_role='Nguoi ky',
                    step_no=1,
                    sort_order=0,
                    required=True,
                    signature_field_name='Sig1',
                    status=TASK_AVAILABLE,
                )

                thread = DocumentMailboxThread.objects.create(
                    document=document,
                    created_by=sender,
                    source_version_number=document.version_number,
                    source_docx_sha256='abc123',
                    status=MAILBOX_STATUS_VIEW,
                )
                DocumentMailboxEntry.objects.create(
                    thread=thread,
                    forwarded_by=sender,
                    forwarded_to=owner,
                    status=MAILBOX_STATUS_VIEW,
                    note='Vui long xem va xu ly',
                )

                self.client.force_login(owner)
                response = self.client.get(reverse('api:aggregate_notification_list'))
                self.assertEqual(response.status_code, 200, response.content)

                source_types = {item['source_type'] for item in response.json()}
                self.assertIn('template_review', source_types)
                self.assertIn('ai_task_terminal', source_types)
                self.assertIn('signing_task', source_types)
                self.assertIn('mailbox_pending', source_types)

                count_response = self.client.get(reverse('api:aggregate_notification_unread_count'))
                self.assertEqual(count_response.status_code, 200, count_response.content)
                self.assertEqual(count_response.json()['count'], 4)

                mark_template_response = self.client.post(
                    reverse('api:aggregate_notification_mark_read'),
                    data={'source_type': 'template_review', 'source_id': str(notification.pk)},
                    content_type='application/json',
                )
                self.assertEqual(mark_template_response.status_code, 200, mark_template_response.content)

                mark_task_response = self.client.post(
                    reverse('api:aggregate_notification_mark_read'),
                    data={'source_type': 'ai_task_terminal', 'source_id': str(task.task_id)},
                    content_type='application/json',
                )
                self.assertEqual(mark_task_response.status_code, 200, mark_task_response.content)

                count_response = self.client.get(reverse('api:aggregate_notification_unread_count'))
                self.assertEqual(count_response.json()['count'], 2)
        finally:
            shutil.rmtree(media_root, ignore_errors=True)

    def test_aggregate_notifications_include_pending_approval_queue(self):
        company = self._create_company('notify-admin')
        admin = User.objects.create_superuser(
            username='notify-admin',
            password='secret',
            email='notify-admin@example.com',
        )
        owner = User.objects.create_user(username='notify-owner', password='secret')
        self._assign_company(admin, company, role='company_admin')
        self._assign_company(owner, company)

        DocumentTemplate.objects.create(
            owner=owner,
            title='Mau cho duyet',
            description='',
            content='<p>Noi dung</p>',
            source_type=DocumentTemplate.SOURCE_MANUAL,
            status='pending',
            visibility='public',
        )
        Prompt.objects.create(
            title='Prompt cho duyet',
            owner=owner,
            status=PROMPT_STATUS_PENDING,
        )

        self.client.force_login(admin)
        response = self.client.get(reverse('api:aggregate_notification_list'))
        self.assertEqual(response.status_code, 200, response.content)

        approval_items = [
            item for item in response.json() if item['source_type'] == 'approval_queue'
        ]
        self.assertEqual(len(approval_items), 1)
        self.assertEqual(approval_items[0]['deeplink'], '/pending-approvals')
