# Chức năng web liên quan: Văn bản của tôi, Văn bản chia sẻ trong nhóm, Văn bản chia sẻ công khai, Văn bản yêu thích, Văn bản đã lưu trữ, Tất cả văn bản (Admin), Hòm thư và Yêu cầu phê duyệt.
# Vai trò backend trong luồng: Tệp này giữ phần logic backend dùng chung cho danh sách văn bản, chi tiết văn bản, version, preview, chia sẻ, ký số và hòm thư, để các flow ở các tab danh sách văn bản, màn chi tiết văn bản, preview hoặc tải file, lịch sử version, vùng khởi động ký số và màn Hòm thư không phải lặp lại cùng một rule ở nhiều nơi.
# Đầu vào/đầu ra chính: Giữ các helper, cấu hình và rule backend dùng lại ở nhiều flow khác nhau.
# Người dùng sẽ thấy trên web: Người dùng sẽ thấy dữ liệu, badge trạng thái, quyền nút và thông báo trên các chức năng Văn bản của tôi, Văn bản chia sẻ trong nhóm, Văn bản chia sẻ công khai, Văn bản yêu thích, Văn bản đã lưu trữ, Tất cả văn bản (Admin), Hòm thư và Yêu cầu phê duyệt thay đổi đúng theo kết quả nghiệp vụ.

import shutil
import uuid
from pathlib import Path
from unittest.mock import patch

from django.conf import settings
from django.contrib.auth.models import User
from django.core.files.base import ContentFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from accounts.models import Company, CompanyStatus, CompanyUserMembership
from documents.models import DOC_STATUS_FINAL, Document, DocumentMailboxEntry, DocumentMailboxThread, SHARE_ACTIVE
from signing.models import (
    PACKET_ACTIVE,
    PACKET_COMPLETED,
    PROPOSAL_APPROVED,
    SIGNATURE_MODE_PDF_PKCS7,
    TASK_AVAILABLE,
    TASK_SIGNED,
    SignedPdfDocument,
    SigningPacket,
    SigningProposal,
    SigningProposalSigner,
    SigningTask,
)

# [Web] `MailboxFlowTests` gom một cụm xử lý backend dùng chung cho nhóm màn Văn bản và Hòm thư.

@override_settings(SIGNING_DEFAULT_SIGNATURE_MODE='pdf_pkcs7')
class MailboxFlowTests(TestCase):
    PDF_BYTES = b'%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF'

    # [Web] `_make_media_root` là bước nội bộ của class để hỗ trợ dữ liệu hoặc trạng thái mà nhóm màn Văn bản và Hòm thư đang cần.

    def _make_media_root(self):
        media_root = Path(settings.BASE_DIR) / '.codex-tmp-pyc' / f'test-mailbox-{uuid.uuid4().hex}'
        media_root.mkdir(parents=True, exist_ok=True)
        return media_root

    def _create_company(self, code):
        return Company.objects.create(
            code=code,
            name=code.replace('-', ' ').title(),
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

    # [Web] `_create_document` là bước nội bộ của class để hỗ trợ dữ liệu hoặc trạng thái mà nhóm màn Văn bản và Hòm thư đang cần.

    def _create_document(self, owner, title='Mailbox document'):
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

    # [Web] `_create_signed_pdf` là bước nội bộ của class để hỗ trợ dữ liệu hoặc trạng thái mà nhóm màn Văn bản và Hòm thư đang cần.

    def _create_signed_pdf(self, document, proposer, signer, *, title_suffix='signed'):
        proposal = SigningProposal.objects.create(
            document=document,
            source_version_number=document.version_number,
            proposed_by=proposer,
            proposal_note='demo',
            status=PROPOSAL_APPROVED,
        )
        proposal_signer = SigningProposalSigner.objects.create(
            proposal=proposal,
            signer_user=signer,
            display_role='Nguoi ky',
            step_no=1,
            sort_order=0,
            required=True,
        )
        packet = SigningPacket(
            proposal=proposal,
            document=document,
            source_version_number=document.version_number,
            source_docx_sha256='abc123',
            pdf_hash='pdfhash',
            signature_mode=SIGNATURE_MODE_PDF_PKCS7,
            status=PACKET_COMPLETED,
            current_step=1,
            completed_at=timezone.now(),
        )
        packet.pdf_snapshot.save(f'snapshot_{signer.username}.pdf', ContentFile(self.PDF_BYTES), save=False)
        packet.working_pdf.save(f'working_{signer.username}.pdf', ContentFile(self.PDF_BYTES), save=False)
        packet.save()
        task = SigningTask.objects.create(
            packet=packet,
            proposal_signer=proposal_signer,
            signer_user=signer,
            display_role='Nguoi ky',
            step_no=1,
            sort_order=0,
            required=True,
            signature_field_name=f'Signature_{signer.username}',
            status=TASK_SIGNED,
            signed_at=timezone.now(),
        )
        signed_pdf = SignedPdfDocument(
            packet=packet,
            title=f'{document.title} {title_suffix} {signer.username}',
            owner=document.owner,
            source_document=document,
            source_version_number=document.version_number,
            file_hash=f'hash-{signer.username}',
            signature_mode=SIGNATURE_MODE_PDF_PKCS7,
            verification_status='safe',
            verification_checked_at=timezone.now(),
            signature_count=1,
        )
        signed_pdf.signed_pdf_file.save(f'signed_{signer.username}.pdf', ContentFile(self.PDF_BYTES), save=False)
        signed_pdf.save()
        return signed_pdf, task

    # [Web] `_create_active_task` là bước nội bộ của class để hỗ trợ dữ liệu hoặc trạng thái mà nhóm màn Văn bản và Hòm thư đang cần.

    def _create_active_task(self, document, proposer, signer):
        proposal = SigningProposal.objects.create(
            document=document,
            source_version_number=document.version_number,
            proposed_by=proposer,
            proposal_note='mailbox sign',
            status=PROPOSAL_APPROVED,
        )
        proposal_signer = SigningProposalSigner.objects.create(
            proposal=proposal,
            signer_user=signer,
            display_role='Nguoi xu ly hom thu',
            step_no=1,
            sort_order=0,
            required=True,
            group_context='mailbox',
        )
        packet = SigningPacket(
            proposal=proposal,
            document=document,
            source_version_number=document.version_number,
            source_docx_sha256='abc123',
            pdf_hash='pdfhash-active',
            signature_mode=SIGNATURE_MODE_PDF_PKCS7,
            status=PACKET_ACTIVE,
            current_step=1,
        )
        packet.pdf_snapshot.save(f'active_snapshot_{signer.username}.pdf', ContentFile(self.PDF_BYTES), save=False)
        packet.working_pdf.save(f'active_working_{signer.username}.pdf', ContentFile(self.PDF_BYTES), save=False)
        packet.save()
        return SigningTask.objects.create(
            packet=packet,
            proposal_signer=proposal_signer,
            signer_user=signer,
            display_role='Nguoi xu ly hom thu',
            group_context='mailbox',
            step_no=1,
            sort_order=0,
            required=True,
            signature_field_name=f'Pending_{signer.username}',
            status=TASK_AVAILABLE,
        )

    # [Web] `_safe_report` là bước nội bộ của class để hỗ trợ dữ liệu hoặc trạng thái mà nhóm màn Văn bản và Hòm thư đang cần.

    def _safe_report(self, signed_doc):
        return {
            'status': 'safe',
            'is_safe': True,
            'is_access_allowed': True,
            'summary': f'{signed_doc.title} is safe.',
            'checked_at': timezone.now().isoformat(),
            'signature_mode': signed_doc.signature_mode,
            'signature_count': signed_doc.signature_count,
            'expected_hash': signed_doc.file_hash,
            'actual_hash': signed_doc.file_hash,
            'signer_reports': [],
            'steps': [],
        }

    # [Web] `_tampered_report` là bước nội bộ của class để hỗ trợ dữ liệu hoặc trạng thái mà nhóm màn Văn bản và Hòm thư đang cần.

    def _tampered_report(self, signed_doc):
        return {
            'status': 'tampered',
            'is_safe': False,
            'is_access_allowed': False,
            'summary': f'{signed_doc.title} was modified.',
            'checked_at': timezone.now().isoformat(),
            'signature_mode': signed_doc.signature_mode,
            'signature_count': signed_doc.signature_count,
            'expected_hash': signed_doc.file_hash,
            'actual_hash': 'tampered',
            'signer_reports': [],
            'steps': [],
        }

    # [Web] `test_initial_forward_uses_latest_safe_signed_pdf_even_if_actor_did_not_sign` là bước nội bộ của class để hỗ trợ dữ liệu hoặc trạng thái mà nhóm màn Văn bản và Hòm thư đang cần.

    def test_initial_forward_uses_latest_safe_signed_pdf_even_if_actor_did_not_sign(self):
        owner = User.objects.create_user(username='owner', password='secret')
        signer = User.objects.create_user(username='signer', password='secret')
        recipient = User.objects.create_user(username='recipient', password='secret')

        media_root = self._make_media_root()
        try:
            with override_settings(MEDIA_ROOT=str(media_root)):
                document = self._create_document(owner, 'Forward first hop')
                signed_pdf, _ = self._create_signed_pdf(document, owner, signer)

                self.client.force_login(owner)
                with patch('signing.services.get_signed_pdf_integrity_report', side_effect=self._safe_report):
                    response = self.client.post(
                        reverse('api:document_forward', args=[document.pk]),
                        data={'user_ids': [recipient.id], 'note': 'forward now'},
                        content_type='application/json',
                    )

                self.assertEqual(response.status_code, 201)
                thread = DocumentMailboxThread.objects.get(document=document)
                entry = thread.entries.get(forwarded_to=recipient)
                self.assertEqual(thread.source_signed_pdf_id, signed_pdf.id)
                self.assertEqual(entry.signed_pdf_id, signed_pdf.id)
                self.assertEqual(entry.forwarded_by_id, owner.id)
        finally:
            shutil.rmtree(media_root, ignore_errors=True)

    # [Web] `test_mailbox_forward_requires_recipient_signature_before_forwarding_next` là bước nội bộ của class để hỗ trợ dữ liệu hoặc trạng thái mà nhóm màn Văn bản và Hòm thư đang cần.

    def test_mailbox_forward_requires_recipient_signature_before_forwarding_next(self):
        owner = User.objects.create_user(username='owner', password='secret')
        signer = User.objects.create_user(username='signer', password='secret')
        recipient = User.objects.create_user(username='recipient', password='secret')
        next_user = User.objects.create_user(username='next_user', password='secret')

        media_root = self._make_media_root()
        try:
            with override_settings(MEDIA_ROOT=str(media_root)):
                document = self._create_document(owner, 'Forward second hop')
                self._create_signed_pdf(document, owner, signer, title_suffix='base')

                with patch('signing.services.get_signed_pdf_integrity_report', side_effect=self._safe_report):
                    thread = DocumentMailboxThread.objects.create(
                        document=document,
                        created_by=owner,
                        source_version_number=document.version_number,
                        source_docx_sha256='abc',
                        source_signed_pdf=SignedPdfDocument.objects.first(),
                        status='forward',
                        last_action_by=owner,
                        last_action_at=timezone.now(),
                        last_action_summary='forward',
                    )
                    entry = DocumentMailboxEntry.objects.create(
                        thread=thread,
                        forwarded_by=owner,
                        forwarded_to=recipient,
                        signed_pdf=SignedPdfDocument.objects.first(),
                        status='view',
                    )

                    self.client.force_login(recipient)
                    blocked = self.client.post(
                        reverse('api:mailbox_entry_forward', args=[entry.pk]),
                        data={'user_ids': [next_user.id], 'note': 'try without signing'},
                        content_type='application/json',
                    )

                    self.assertEqual(blocked.status_code, 400)
                    self.assertIn('chinh ban ky', blocked.json()['detail'])

                    recipient_signed_pdf, _ = self._create_signed_pdf(document, recipient, recipient, title_suffix='recipient')
                    allowed = self.client.post(
                        reverse('api:mailbox_entry_forward', args=[entry.pk]),
                        data={'user_ids': [next_user.id], 'note': 'forward after signing'},
                        content_type='application/json',
                    )

                self.assertEqual(allowed.status_code, 200)
                entry.refresh_from_db()
                self.assertEqual(entry.status, 'forward')
                next_entry = DocumentMailboxEntry.objects.get(parent_entry=entry, forwarded_to=next_user)
                self.assertEqual(next_entry.signed_pdf_id, recipient_signed_pdf.id)
        finally:
            shutil.rmtree(media_root, ignore_errors=True)

    # [Web] `test_mailbox_endpoints_work_for_recipient_without_signed_pdf_global_access` là bước nội bộ của class để hỗ trợ dữ liệu hoặc trạng thái mà nhóm màn Văn bản và Hòm thư đang cần.

    def test_mailbox_endpoints_work_for_recipient_without_signed_pdf_global_access(self):
        owner = User.objects.create_user(username='owner', password='secret')
        signer = User.objects.create_user(username='signer', password='secret')
        recipient = User.objects.create_user(username='recipient', password='secret')

        media_root = self._make_media_root()
        try:
            with override_settings(MEDIA_ROOT=str(media_root)):
                document = self._create_document(owner, 'Mailbox access')
                signed_pdf, _ = self._create_signed_pdf(document, owner, signer)
                thread = DocumentMailboxThread.objects.create(
                    document=document,
                    created_by=owner,
                    source_version_number=document.version_number,
                    source_docx_sha256='abc',
                    source_signed_pdf=signed_pdf,
                    status='forward',
                    last_action_by=owner,
                    last_action_at=timezone.now(),
                    last_action_summary='forward',
                )
                entry = DocumentMailboxEntry.objects.create(
                    thread=thread,
                    forwarded_by=owner,
                    forwarded_to=recipient,
                    signed_pdf=signed_pdf,
                    status='view',
                )

                self.client.force_login(recipient)
                detail_response = self.client.get(reverse('api:signed_pdf_detail', args=[signed_pdf.pk]))
                with patch('documents.mailbox_services.get_signed_pdf_integrity_report', side_effect=self._safe_report):
                    verify_response = self.client.get(reverse('api:mailbox_thread_verify', args=[thread.pk]))
                    preview_response = self.client.get(reverse('api:mailbox_thread_preview_pdf', args=[thread.pk]))
                    entry_verify_response = self.client.get(reverse('api:mailbox_entry_verify', args=[entry.pk]))

                self.assertEqual(detail_response.status_code, 404)
                self.assertEqual(verify_response.status_code, 200)
                self.assertEqual(preview_response.status_code, 200)
                self.assertEqual(entry_verify_response.status_code, 200)
        finally:
            shutil.rmtree(media_root, ignore_errors=True)

    # [Web] `test_mailbox_preview_blocks_tampered_pdf` là bước nội bộ của class để hỗ trợ dữ liệu hoặc trạng thái mà nhóm màn Văn bản và Hòm thư đang cần.

    def test_mailbox_preview_blocks_tampered_pdf(self):
        owner = User.objects.create_user(username='owner', password='secret')
        signer = User.objects.create_user(username='signer', password='secret')
        recipient = User.objects.create_user(username='recipient', password='secret')

        media_root = self._make_media_root()
        try:
            with override_settings(MEDIA_ROOT=str(media_root)):
                document = self._create_document(owner, 'Mailbox tampered')
                signed_pdf, _ = self._create_signed_pdf(document, owner, signer)
                thread = DocumentMailboxThread.objects.create(
                    document=document,
                    created_by=owner,
                    source_version_number=document.version_number,
                    source_docx_sha256='abc',
                    source_signed_pdf=signed_pdf,
                    status='forward',
                    last_action_by=owner,
                    last_action_at=timezone.now(),
                    last_action_summary='forward',
                )
                entry = DocumentMailboxEntry.objects.create(
                    thread=thread,
                    forwarded_by=owner,
                    forwarded_to=recipient,
                    signed_pdf=signed_pdf,
                    status='view',
                )

                self.client.force_login(recipient)
                with patch('documents.mailbox_services.get_signed_pdf_integrity_report', side_effect=self._tampered_report):
                    thread_preview = self.client.get(reverse('api:mailbox_thread_preview_pdf', args=[thread.pk]))
                    entry_preview = self.client.get(reverse('api:mailbox_entry_preview_pdf', args=[entry.pk]))

                self.assertEqual(thread_preview.status_code, 409)
                self.assertEqual(entry_preview.status_code, 409)
        finally:
            shutil.rmtree(media_root, ignore_errors=True)

    # [Web] `test_mailbox_entry_sign_endpoint_returns_task_payload` là bước nội bộ của class để hỗ trợ dữ liệu hoặc trạng thái mà nhóm màn Văn bản và Hòm thư đang cần.

    def test_mailbox_entry_sign_endpoint_returns_task_payload(self):
        owner = User.objects.create_user(username='owner', password='secret')
        signer = User.objects.create_user(username='signer', password='secret')
        recipient = User.objects.create_user(username='recipient', password='secret')

        media_root = self._make_media_root()
        try:
            with override_settings(MEDIA_ROOT=str(media_root)):
                document = self._create_document(owner, 'Mailbox sign endpoint')
                signed_pdf, _ = self._create_signed_pdf(document, owner, signer)
                thread = DocumentMailboxThread.objects.create(
                    document=document,
                    created_by=owner,
                    source_version_number=document.version_number,
                    source_docx_sha256='abc',
                    source_signed_pdf=signed_pdf,
                    status='forward',
                    last_action_by=owner,
                    last_action_at=timezone.now(),
                    last_action_summary='forward',
                )
                entry = DocumentMailboxEntry.objects.create(
                    thread=thread,
                    forwarded_by=owner,
                    forwarded_to=recipient,
                    signed_pdf=signed_pdf,
                    status='view',
                )
                task = self._create_active_task(document, recipient, recipient)

                self.client.force_login(recipient)
                with patch(
                    'api.views.documents.ensure_mailbox_entry_signing_task',
                    return_value={
                        'proposal': task.packet.proposal,
                        'packet': task.packet,
                        'task': task,
                        'created': True,
                        'already_signed': False,
                        'signed_pdf': None,
                    },
                ):
                    response = self.client.post(reverse('api:mailbox_entry_sign', args=[entry.pk]))

                self.assertEqual(response.status_code, 201)
                payload = response.json()
                self.assertTrue(payload['created'])
                self.assertFalse(payload['already_signed'])
                self.assertEqual(payload['task']['id'], task.id)
                self.assertEqual(payload['packet_id'], task.packet_id)
        finally:
            shutil.rmtree(media_root, ignore_errors=True)

    # [Web] `test_document_detail_and_list_include_signing_status` là bước nội bộ của class để hỗ trợ dữ liệu hoặc trạng thái mà nhóm màn Văn bản và Hòm thư đang cần.

    def test_document_detail_and_list_include_signing_status(self):
        owner = User.objects.create_user(username='owner', password='secret')
        signer = User.objects.create_user(username='signer', password='secret')

        media_root = self._make_media_root()
        try:
            with override_settings(MEDIA_ROOT=str(media_root)):
                unsigned_document = self._create_document(owner, 'Unsigned document')
                signed_document = self._create_document(owner, 'Signed document')
                self._create_signed_pdf(signed_document, owner, signer)

                self.client.force_login(owner)
                unsigned_detail = self.client.get(reverse('api:document_detail', args=[unsigned_document.pk]))
                signed_detail = self.client.get(reverse('api:document_detail', args=[signed_document.pk]))
                doc_list = self.client.get(reverse('api:document_list'))

                self.assertEqual(unsigned_detail.status_code, 200)
                self.assertEqual(unsigned_detail.json()['signing_status'], 'unsigned')
                self.assertFalse(unsigned_detail.json()['can_forward_now'])

                self.assertEqual(signed_detail.status_code, 200)
                self.assertEqual(signed_detail.json()['signing_status'], 'signed')
                self.assertTrue(signed_detail.json()['can_forward_now'])

                listed = {item['title']: item for item in doc_list.json()}
                self.assertEqual(listed['Unsigned document']['signing_status'], 'unsigned')
                self.assertEqual(listed['Signed document']['signing_status'], 'signed')
        finally:
            shutil.rmtree(media_root, ignore_errors=True)

    def test_mailbox_forward_rejects_recipient_from_other_company(self):
        company_a = self._create_company('company-a')
        company_b = self._create_company('company-b')
        owner = User.objects.create_user(username='owner_a', password='secret')
        signer = User.objects.create_user(username='signer_a', password='secret')
        outsider = User.objects.create_user(username='outsider_b', password='secret')
        self._assign_company(owner, company_a)
        self._assign_company(signer, company_a)
        self._assign_company(outsider, company_b)

        media_root = self._make_media_root()
        try:
            with override_settings(MEDIA_ROOT=str(media_root)):
                document = self._create_document(owner, 'Cross company mailbox')
                self._create_signed_pdf(document, owner, signer)

                self.client.force_login(owner)
                with patch('signing.services.get_signed_pdf_integrity_report', side_effect=self._safe_report):
                    response = self.client.post(
                        reverse('api:document_forward', args=[document.pk]),
                        data={'user_ids': [outsider.id], 'note': 'cross-tenant'},
                        content_type='application/json',
                    )

                self.assertEqual(response.status_code, 400)
                self.assertIn('cong ty', response.json()['detail'])
                self.assertFalse(DocumentMailboxThread.objects.filter(document=document).exists())
        finally:
            shutil.rmtree(media_root, ignore_errors=True)
