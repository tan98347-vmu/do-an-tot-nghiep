# Chức năng web liên quan: Yêu cầu ký, PDF đã ký, Hòm thư và Ủy quyền ký số.
# Vai trò backend trong luồng: Tệp này giữ phần logic backend dùng chung cho đề xuất ký, nhiệm vụ ký, PDF đã ký, xác minh chữ ký và ủy quyền ký số, để các flow ở màn Yêu cầu ký, chi tiết ký, PDF đã ký, dialog đề xuất ký, dialog chọn người ký và màn Ủy quyền ký số không phải lặp lại cùng một rule ở nhiều nơi.
# Đầu vào/đầu ra chính: Giữ các helper, cấu hình và rule backend dùng lại ở nhiều flow khác nhau.
# Người dùng sẽ thấy trên web: Người dùng sẽ thấy dữ liệu, badge trạng thái, quyền nút và thông báo trên các chức năng Yêu cầu ký, PDF đã ký, Hòm thư và Ủy quyền ký số thay đổi đúng theo kết quả nghiệp vụ.

import shutil
import uuid
from pathlib import Path
from unittest.mock import patch

import fitz
from django.conf import settings
from django.core.files.base import ContentFile
from django.test import TestCase, override_settings
from django.contrib.auth.models import User
from django.urls import reverse

from accounts.models import Company, CompanyStatus, CompanyUserMembership, Department
from accounts.storage_paths import company_storage_slug
from accounts.permissions import can_delete_document, can_edit_document, get_accessible_documents
from documents.mailbox_services import MailboxFlowError
from documents.models import DOC_STATUS_DRAFT, DOC_STATUS_FINAL, SHARE_ACTIVE, Document
from signing.permissions import (
    can_review_signing_proposals,
    can_view_signed_pdf,
    get_accessible_signed_pdfs,
    get_pending_hr_proposals,
)
from signing.assistant_quick_sign import (
    AssistantQuickSignError,
    build_quick_sign_plan_payload,
    execute_quick_sign_and_forward,
    prepare_quick_sign_plan,
    refresh_quick_sign_plan,
)
from signing.models import AssistantQuickSignPlan, SignedPdfDocument
from signing.services import SigningFlowError, approve_signing_proposal, create_signing_proposal, sign_task

# [Web] `SigningFlowTests` gom một cụm xử lý backend dùng chung cho nhóm màn Yêu cầu ký, PDF đã ký và Ủy quyền ký số.

@override_settings(SIGNING_DEFAULT_SIGNATURE_MODE='internal_approval')
class SigningFlowTests(TestCase):
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

    def _build_preview_pdf(self, media_root, filename='preview.pdf'):
        preview_pdf_path = media_root / filename
        pdf = fitz.open()
        pdf.new_page()
        pdf.save(preview_pdf_path)
        pdf.close()
        return preview_pdf_path

    # [Web] `test_approved_proposal_creates_tasks_for_all_selected_signers` là bước nội bộ của class để hỗ trợ dữ liệu hoặc trạng thái mà nhóm màn Yêu cầu ký, PDF đã ký và Ủy quyền ký số đang cần.

    def test_approved_proposal_creates_tasks_for_all_selected_signers(self):
        owner = User.objects.create_user(username='owner', password='secret')
        reviewer = User.objects.create_user(username='reviewer', password='secret')
        signer_one = User.objects.create_user(username='signer_one', password='secret')
        signer_two = User.objects.create_user(username='signer_two', password='secret')

        media_root = Path(settings.BASE_DIR) / '.codex-tmp-pyc' / f'test-media-{uuid.uuid4().hex}'
        media_root.mkdir(parents=True, exist_ok=True)
        try:
            with override_settings(MEDIA_ROOT=str(media_root)):
                document = Document.objects.create(
                    title='Hop dong test',
                    owner=owner,
                    status=DOC_STATUS_FINAL,
                    share_status=SHARE_ACTIVE,
                    visibility='private',
                )
                document.output_file.save(
                    'hop_dong_test.docx',
                    ContentFile(b'docx-binary-placeholder'),
                    save=True,
                )

                proposal = create_signing_proposal(
                    document,
                    owner,
                    [
                        {
                            'user': signer_one,
                            'display_role': 'Nguoi ky 1',
                            'step_no': 1,
                            'required': True,
                            'group_context': '',
                        },
                        {
                            'user': signer_two,
                            'display_role': 'Nguoi ky 2',
                            'step_no': 2,
                            'required': True,
                            'group_context': '',
                        },
                    ],
                    proposal_note='demo',
                )

                preview_pdf_path = media_root / 'preview.pdf'
                pdf = fitz.open()
                pdf.new_page()
                pdf.save(preview_pdf_path)
                pdf.close()

                with patch('signing.services.build_document_preview_pdf', return_value=preview_pdf_path):
                    packet = approve_signing_proposal(proposal, reviewer, 'ok')

                tasks = list(
                    packet.tasks.order_by('step_no', 'sort_order', 'id').values(
                        'signer_user__username',
                        'status',
                        'step_no',
                    )
                )
                self.assertEqual(
                    tasks,
                    [
                        {
                            'signer_user__username': 'signer_one',
                            'status': 'available',
                            'step_no': 1,
                        },
                        {
                            'signer_user__username': 'signer_two',
                            'status': 'blocked',
                            'step_no': 2,
                        },
                    ],
                )
        finally:
            shutil.rmtree(media_root, ignore_errors=True)

    # [Web] `test_signer_can_view_document_detail_for_current_signing_packet` là bước nội bộ của class để hỗ trợ dữ liệu hoặc trạng thái mà nhóm màn Yêu cầu ký, PDF đã ký và Ủy quyền ký số đang cần.

    def test_signer_can_view_document_detail_for_current_signing_packet(self):
        owner = User.objects.create_user(username='owner', password='secret')
        reviewer = User.objects.create_user(username='reviewer', password='secret')
        signer = User.objects.create_user(username='signer', password='secret')

        media_root = Path(settings.BASE_DIR) / '.codex-tmp-pyc' / f'test-media-{uuid.uuid4().hex}'
        media_root.mkdir(parents=True, exist_ok=True)
        try:
            with override_settings(MEDIA_ROOT=str(media_root)):
                document = Document.objects.create(
                    title='To trinh can xem',
                    owner=owner,
                    status=DOC_STATUS_FINAL,
                    share_status=SHARE_ACTIVE,
                    visibility='private',
                )
                document.output_file.save(
                    'to_trinh_can_xem.docx',
                    ContentFile(b'docx-binary-placeholder'),
                    save=True,
                )

                proposal = create_signing_proposal(
                    document,
                    owner,
                    [
                        {
                            'user': signer,
                            'display_role': 'Nguoi ky',
                            'step_no': 1,
                            'required': True,
                            'group_context': '',
                        },
                    ],
                    proposal_note='demo',
                )

                preview_pdf_path = media_root / 'preview.pdf'
                pdf = fitz.open()
                pdf.new_page()
                pdf.save(preview_pdf_path)
                pdf.close()

                with patch('signing.services.build_document_preview_pdf', return_value=preview_pdf_path):
                    approve_signing_proposal(proposal, reviewer, 'ok')

                self.assertTrue(get_accessible_documents(signer).filter(pk=document.pk).exists())

                self.client.force_login(signer)
                response = self.client.get(reverse('api:document_detail', args=[document.pk]))
                self.assertEqual(response.status_code, 200)
        finally:
            shutil.rmtree(media_root, ignore_errors=True)

    # [Web] `test_invalidated_packet_signer_loses_document_access` là bước nội bộ của class để hỗ trợ dữ liệu hoặc trạng thái mà nhóm màn Yêu cầu ký, PDF đã ký và Ủy quyền ký số đang cần.

    def test_invalidated_packet_signer_loses_document_access(self):
        owner = User.objects.create_user(username='owner', password='secret')
        reviewer = User.objects.create_user(username='reviewer', password='secret')
        old_signer = User.objects.create_user(username='old_signer', password='secret')
        new_signer = User.objects.create_user(username='new_signer', password='secret')

        media_root = Path(settings.BASE_DIR) / '.codex-tmp-pyc' / f'test-media-{uuid.uuid4().hex}'
        media_root.mkdir(parents=True, exist_ok=True)
        try:
            with override_settings(MEDIA_ROOT=str(media_root)):
                document = Document.objects.create(
                    title='Van ban doi signer',
                    owner=owner,
                    status=DOC_STATUS_FINAL,
                    share_status=SHARE_ACTIVE,
                    visibility='private',
                )
                document.output_file.save(
                    'van_ban_doi_signer.docx',
                    ContentFile(b'docx-binary-placeholder'),
                    save=True,
                )

                proposal_one = create_signing_proposal(
                    document,
                    owner,
                    [
                        {
                            'user': old_signer,
                            'display_role': 'Nguoi ky cu',
                            'step_no': 1,
                            'required': True,
                            'group_context': '',
                        },
                    ],
                    proposal_note='lan 1',
                )

                preview_pdf_path = media_root / 'preview.pdf'
                pdf = fitz.open()
                pdf.new_page()
                pdf.save(preview_pdf_path)
                pdf.close()

                with patch('signing.services.build_document_preview_pdf', return_value=preview_pdf_path):
                    approve_signing_proposal(proposal_one, reviewer, 'ok')

                self.assertTrue(get_accessible_documents(old_signer).filter(pk=document.pk).exists())

                create_signing_proposal(
                    document,
                    owner,
                    [
                        {
                            'user': new_signer,
                            'display_role': 'Nguoi ky moi',
                            'step_no': 1,
                            'required': True,
                            'group_context': '',
                        },
                    ],
                    proposal_note='lan 2',
                )

                self.assertFalse(get_accessible_documents(old_signer).filter(pk=document.pk).exists())
                self.assertFalse(get_accessible_documents(new_signer).filter(pk=document.pk).exists())
        finally:
            shutil.rmtree(media_root, ignore_errors=True)

    # [Web] `test_signers_and_proposer_can_view_completed_signed_pdf` là bước nội bộ của class để hỗ trợ dữ liệu hoặc trạng thái mà nhóm màn Yêu cầu ký, PDF đã ký và Ủy quyền ký số đang cần.

    def test_signers_and_proposer_can_view_completed_signed_pdf(self):
        proposer = User.objects.create_user(username='proposer', password='secret')
        reviewer = User.objects.create_user(username='reviewer', password='secret')
        signer = User.objects.create_user(username='signer', password='secret')

        media_root = Path(settings.BASE_DIR) / '.codex-tmp-pyc' / f'test-media-{uuid.uuid4().hex}'
        media_root.mkdir(parents=True, exist_ok=True)
        try:
            with override_settings(MEDIA_ROOT=str(media_root)):
                document = Document.objects.create(
                    title='Phieu ky xong',
                    owner=proposer,
                    status=DOC_STATUS_FINAL,
                    share_status=SHARE_ACTIVE,
                    visibility='private',
                )
                document.output_file.save(
                    'phieu_ky_xong.docx',
                    ContentFile(b'docx-binary-placeholder'),
                    save=True,
                )

                proposal = create_signing_proposal(
                    document,
                    proposer,
                    [
                        {
                            'user': signer,
                            'display_role': 'Nguoi ky chinh',
                            'step_no': 1,
                            'required': True,
                            'group_context': '',
                        },
                    ],
                    proposal_note='demo',
                )

                preview_pdf_path = media_root / 'preview.pdf'
                pdf = fitz.open()
                pdf.new_page()
                pdf.save(preview_pdf_path)
                pdf.close()

                with patch('signing.services.build_document_preview_pdf', return_value=preview_pdf_path):
                    packet = approve_signing_proposal(proposal, reviewer, 'ok')

                task = packet.tasks.get(signer_user=signer)
                with patch('signing.services._append_signature_stamp', return_value=None):
                    result = sign_task(task, signer, 'secret')
                    signed_doc = result['signed_pdf']

                self.assertIsNotNone(signed_doc)
                self.assertTrue(get_accessible_signed_pdfs(signer).filter(pk=signed_doc.pk).exists())
                self.assertTrue(get_accessible_signed_pdfs(proposer).filter(pk=signed_doc.pk).exists())
                self.assertTrue(can_view_signed_pdf(signer, signed_doc))
                self.assertTrue(can_view_signed_pdf(proposer, signed_doc))

                self.client.force_login(proposer)
                detail_response = self.client.get(reverse('api:signed_pdf_detail', args=[signed_doc.pk]))
                verify_response = self.client.get(reverse('api:signed_pdf_verify', args=[signed_doc.pk]))
                preview_response = self.client.get(reverse('api:signed_pdf_preview_pdf', args=[signed_doc.pk]))
                self.assertEqual(detail_response.status_code, 200)
                self.assertEqual(verify_response.status_code, 200)
                self.assertEqual(preview_response.status_code, 200)
                self.assertEqual(verify_response.json()['status'], 'internal_approval')
                self.assertEqual(len(detail_response.json()['signing_events']), 1)
                self.assertEqual(detail_response.json()['signing_events'][0]['signer_name'], 'signer')
                self.assertTrue(detail_response.json()['signing_events'][0]['signed_at'])
        finally:
            shutil.rmtree(media_root, ignore_errors=True)

    # [Web] `test_signed_pdf_preview_and_download_fail_when_file_is_tampered` là bước nội bộ của class để hỗ trợ dữ liệu hoặc trạng thái mà nhóm màn Yêu cầu ký, PDF đã ký và Ủy quyền ký số đang cần.

    def test_signed_pdf_preview_and_download_fail_when_file_is_tampered(self):
        proposer = User.objects.create_user(username='proposer', password='secret')
        reviewer = User.objects.create_user(username='reviewer', password='secret')
        signer = User.objects.create_user(username='signer', password='secret')

        media_root = Path(settings.BASE_DIR) / '.codex-tmp-pyc' / f'test-media-{uuid.uuid4().hex}'
        media_root.mkdir(parents=True, exist_ok=True)
        try:
            with override_settings(MEDIA_ROOT=str(media_root)):
                document = Document.objects.create(
                    title='PDF bi sua',
                    owner=proposer,
                    status=DOC_STATUS_FINAL,
                    share_status=SHARE_ACTIVE,
                    visibility='private',
                )
                document.output_file.save(
                    'pdf_bi_sua.docx',
                    ContentFile(b'docx-binary-placeholder'),
                    save=True,
                )

                proposal = create_signing_proposal(
                    document,
                    proposer,
                    [
                        {
                            'user': signer,
                            'display_role': 'Nguoi ky',
                            'step_no': 1,
                            'required': True,
                            'group_context': '',
                        },
                    ],
                    proposal_note='demo',
                )

                preview_pdf_path = media_root / 'preview.pdf'
                pdf = fitz.open()
                pdf.new_page()
                pdf.save(preview_pdf_path)
                pdf.close()

                with patch('signing.services.build_document_preview_pdf', return_value=preview_pdf_path):
                    packet = approve_signing_proposal(proposal, reviewer, 'ok')

                task = packet.tasks.get(signer_user=signer)
                with patch('signing.services._append_signature_stamp', return_value=None):
                    result = sign_task(task, signer, 'secret')
                    signed_doc = result['signed_pdf']

                Path(signed_doc.signed_pdf_file.path).write_bytes(b'tampered-pdf')

                self.client.force_login(proposer)
                verify_response = self.client.get(reverse('api:signed_pdf_verify', args=[signed_doc.pk]))
                preview_response = self.client.get(reverse('api:signed_pdf_preview_pdf', args=[signed_doc.pk]))
                download_response = self.client.get(reverse('api:signed_pdf_download', args=[signed_doc.pk]))

                self.assertEqual(verify_response.status_code, 409)
                self.assertEqual(preview_response.status_code, 409)
                self.assertEqual(download_response.status_code, 409)
                self.assertFalse(verify_response.json()['is_safe'])
                self.assertIn('thay doi', preview_response.json()['detail'])
        finally:
            shutil.rmtree(media_root, ignore_errors=True)

    # [Web] `test_owner_cannot_edit_or_delete_document_after_signing_starts` là bước nội bộ của class để hỗ trợ dữ liệu hoặc trạng thái mà nhóm màn Yêu cầu ký, PDF đã ký và Ủy quyền ký số đang cần.

    def test_owner_cannot_edit_or_delete_document_after_signing_starts(self):
        owner = User.objects.create_user(username='owner', password='secret')
        reviewer = User.objects.create_user(username='reviewer', password='secret')
        signer = User.objects.create_user(username='signer', password='secret')

        media_root = Path(settings.BASE_DIR) / '.codex-tmp-pyc' / f'test-media-{uuid.uuid4().hex}'
        media_root.mkdir(parents=True, exist_ok=True)
        try:
            with override_settings(MEDIA_ROOT=str(media_root)):
                document = Document.objects.create(
                    title='Van ban bi khoa sua',
                    owner=owner,
                    status=DOC_STATUS_FINAL,
                    share_status=SHARE_ACTIVE,
                    visibility='private',
                    notes='ban dau',
                )
                document.output_file.save(
                    'van_ban_bi_khoa_sua.docx',
                    ContentFile(b'docx-binary-placeholder'),
                    save=True,
                )

                proposal = create_signing_proposal(
                    document,
                    owner,
                    [
                        {
                            'user': signer,
                            'display_role': 'Nguoi ky',
                            'step_no': 1,
                            'required': True,
                            'group_context': '',
                        },
                    ],
                    proposal_note='demo',
                )

                preview_pdf_path = media_root / 'preview.pdf'
                pdf = fitz.open()
                pdf.new_page()
                pdf.save(preview_pdf_path)
                pdf.close()

                with patch('signing.services.build_document_preview_pdf', return_value=preview_pdf_path):
                    approve_signing_proposal(proposal, reviewer, 'ok')

                self.assertFalse(can_edit_document(owner, document))
                self.assertFalse(can_delete_document(owner, document))

                self.client.force_login(owner)
                patch_response = self.client.patch(
                    reverse('api:document_detail', args=[document.pk]),
                    data='{"notes":"da sua"}',
                    content_type='application/json',
                )
                delete_response = self.client.delete(reverse('api:document_detail', args=[document.pk]))

                document.refresh_from_db()
                self.assertEqual(patch_response.status_code, 409)
                self.assertEqual(delete_response.status_code, 409)
                self.assertEqual(document.notes, 'ban dau')
        finally:
            shutil.rmtree(media_root, ignore_errors=True)

    def test_signing_proposal_reject_requires_reason(self):
        company = self._create_company('reject-proposal')
        owner = User.objects.create_user(username='reject_owner', password='secret')
        reviewer = User.objects.create_user(username='reject_reviewer', password='secret')
        signer = User.objects.create_user(username='reject_signer', password='secret')
        self._assign_company(owner, company)
        self._assign_company(reviewer, company)
        self._assign_company(signer, company)
        Department.objects.create(company=company, name='Nhan su', code='HR-REJECT', manager=reviewer)

        media_root = Path(settings.BASE_DIR) / '.codex-tmp-pyc' / f'test-media-{uuid.uuid4().hex}'
        media_root.mkdir(parents=True, exist_ok=True)
        try:
            with override_settings(MEDIA_ROOT=str(media_root)):
                document = Document.objects.create(
                    title='De xuat can ly do tu choi',
                    owner=owner,
                    status=DOC_STATUS_FINAL,
                    share_status=SHARE_ACTIVE,
                    visibility='private',
                )
                document.output_file.save(
                    'proposal_reject_reason.docx',
                    ContentFile(b'docx-binary-placeholder'),
                    save=True,
                )
                proposal = create_signing_proposal(
                    document,
                    owner,
                    [
                        {
                            'user': signer,
                            'display_role': 'Nguoi ky',
                            'step_no': 1,
                            'required': True,
                            'group_context': '',
                        },
                    ],
                    proposal_note='demo',
                )

                self.client.force_login(reviewer)
                response = self.client.post(
                    reverse('api:signing_proposal_reject', args=[proposal.pk]),
                    data={},
                )
                self.assertEqual(response.status_code, 400, response.content)
                self.assertEqual(response.json()['detail'], 'Phai co ly do tu choi de xuat ky.')
        finally:
            shutil.rmtree(media_root, ignore_errors=True)

    def test_signing_task_reject_requires_reason(self):
        company = self._create_company('reject-task')
        owner = User.objects.create_user(username='reject_task_owner', password='secret')
        reviewer = User.objects.create_user(username='reject_task_reviewer', password='secret')
        signer = User.objects.create_user(username='reject_task_signer', password='secret')
        self._assign_company(owner, company)
        self._assign_company(reviewer, company)
        self._assign_company(signer, company)
        Department.objects.create(company=company, name='Nhan su', code='HR-TASK', manager=reviewer)

        media_root = Path(settings.BASE_DIR) / '.codex-tmp-pyc' / f'test-media-{uuid.uuid4().hex}'
        media_root.mkdir(parents=True, exist_ok=True)
        try:
            with override_settings(MEDIA_ROOT=str(media_root)):
                document = Document.objects.create(
                    title='Yeu cau ky can ly do tu choi',
                    owner=owner,
                    status=DOC_STATUS_FINAL,
                    share_status=SHARE_ACTIVE,
                    visibility='private',
                )
                document.output_file.save(
                    'task_reject_reason.docx',
                    ContentFile(b'docx-binary-placeholder'),
                    save=True,
                )
                proposal = create_signing_proposal(
                    document,
                    owner,
                    [
                        {
                            'user': signer,
                            'display_role': 'Nguoi ky',
                            'step_no': 1,
                            'required': True,
                            'group_context': '',
                        },
                    ],
                    proposal_note='demo',
                )

                preview_pdf_path = media_root / 'preview.pdf'
                pdf = fitz.open()
                pdf.new_page()
                pdf.save(preview_pdf_path)
                pdf.close()

                with patch('signing.services.build_document_preview_pdf', return_value=preview_pdf_path):
                    packet = approve_signing_proposal(proposal, reviewer, 'ok')

                task = packet.tasks.get(signer_user=signer)
                self.client.force_login(signer)
                response = self.client.post(
                    reverse('api:signing_task_reject', args=[task.pk]),
                    data={},
                )
                self.assertEqual(response.status_code, 400, response.content)
                self.assertEqual(response.json()['detail'], 'Phai co ly do tu choi yeu cau ky.')
        finally:
            shutil.rmtree(media_root, ignore_errors=True)

    def test_cross_company_signer_is_rejected(self):
        company_a = self._create_company('signing-a')
        company_b = self._create_company('signing-b')
        owner = User.objects.create_user(username='owner_a', password='secret')
        outsider = User.objects.create_user(username='outsider_b', password='secret')
        self._assign_company(owner, company_a)
        self._assign_company(outsider, company_b)

        media_root = Path(settings.BASE_DIR) / '.codex-tmp-pyc' / f'test-media-{uuid.uuid4().hex}'
        media_root.mkdir(parents=True, exist_ok=True)
        try:
            with override_settings(MEDIA_ROOT=str(media_root)):
                document = Document.objects.create(
                    title='Cross company signer',
                    owner=owner,
                    status=DOC_STATUS_FINAL,
                    share_status=SHARE_ACTIVE,
                    visibility='private',
                )
                document.output_file.save(
                    'cross_company_signer.docx',
                    ContentFile(b'docx-binary-placeholder'),
                    save=True,
                )

                with self.assertRaises(SigningFlowError):
                    create_signing_proposal(
                        document,
                        owner,
                        [
                            {
                                'user': outsider,
                                'display_role': 'Signer',
                                'step_no': 1,
                                'required': True,
                                'group_context': '',
                            },
                        ],
                        proposal_note='cross-company',
                    )
        finally:
            shutil.rmtree(media_root, ignore_errors=True)

    def test_quick_sign_plan_execute_signs_and_forwards(self):
        company = self._create_company('quick-sign-success')
        actor = User.objects.create_user(username='quick_actor', password='secret')
        recipient = User.objects.create_user(username='quick_recipient', password='secret')
        self._assign_company(actor, company)
        self._assign_company(recipient, company)

        media_root = Path(settings.BASE_DIR) / '.codex-tmp-pyc' / f'test-quick-sign-{uuid.uuid4().hex}'
        media_root.mkdir(parents=True, exist_ok=True)
        try:
            with override_settings(MEDIA_ROOT=str(media_root)):
                document = Document.objects.create(
                    title='Quick sign success',
                    owner=actor,
                    status=DOC_STATUS_FINAL,
                    share_status=SHARE_ACTIVE,
                    visibility='private',
                )
                document.output_file.save('quick_sign_success.docx', ContentFile(b'docx-binary-placeholder'), save=True)
                preview_pdf_path = self._build_preview_pdf(media_root, 'quick-sign-success.pdf')

                with patch('signing.services.build_document_preview_pdf', return_value=preview_pdf_path), patch(
                    'signing.services._append_signature_stamp',
                    return_value=None,
                ):
                    plan = prepare_quick_sign_plan(document, actor, recipient)
                    completed = execute_quick_sign_and_forward(plan, actor, reauth_password='secret')

                self.assertEqual(completed.status, AssistantQuickSignPlan.Status.COMPLETED)
                self.assertIsNotNone(completed.signed_pdf_id)
                self.assertIsNotNone(completed.mailbox_thread_id)
                mailbox_entry = completed.mailbox_thread.entries.get(forwarded_to=recipient)
                self.assertEqual(mailbox_entry.signed_pdf_id, completed.signed_pdf_id)
        finally:
            shutil.rmtree(media_root, ignore_errors=True)

    def test_quick_sign_plan_auto_finalizes_owned_draft_document(self):
        company = self._create_company('quick-sign-auto-final')
        actor = User.objects.create_user(username='quick_actor_auto_final', password='secret')
        recipient = User.objects.create_user(username='quick_recipient_auto_final', password='secret')
        self._assign_company(actor, company)
        self._assign_company(recipient, company)

        media_root = Path(settings.BASE_DIR) / '.codex-tmp-pyc' / f'test-quick-sign-auto-final-{uuid.uuid4().hex}'
        media_root.mkdir(parents=True, exist_ok=True)
        try:
            with override_settings(MEDIA_ROOT=str(media_root)):
                document = Document.objects.create(
                    title='Quick sign auto finalize',
                    owner=actor,
                    status=DOC_STATUS_DRAFT,
                    share_status=SHARE_ACTIVE,
                    visibility='private',
                )
                document.output_file.save(
                    'quick_sign_auto_finalize.docx',
                    ContentFile(b'docx-binary-placeholder'),
                    save=True,
                )
                preview_pdf_path = self._build_preview_pdf(media_root, 'quick-sign-auto-final.pdf')

                with patch('signing.services.build_document_preview_pdf', return_value=preview_pdf_path):
                    plan = prepare_quick_sign_plan(document, actor, recipient)

                document.refresh_from_db()
                self.assertEqual(document.status, DOC_STATUS_FINAL)
                self.assertEqual(plan.status, AssistantQuickSignPlan.Status.READY)
                self.assertTrue(plan.can_sign_now)
                self.assertIsNotNone(plan.signing_task_id)
                self.assertIsNotNone(plan.signing_packet_id)
        finally:
            shutil.rmtree(media_root, ignore_errors=True)

    def test_document_detail_includes_assistant_quick_sign_plan(self):
        company = self._create_company('quick-sign-detail')
        actor = User.objects.create_user(username='quick_actor_detail', password='secret')
        recipient = User.objects.create_user(username='quick_recipient_detail', password='secret')
        self._assign_company(actor, company)
        self._assign_company(recipient, company)

        media_root = Path(settings.BASE_DIR) / '.codex-tmp-pyc' / f'test-quick-sign-detail-{uuid.uuid4().hex}'
        media_root.mkdir(parents=True, exist_ok=True)
        try:
            with override_settings(MEDIA_ROOT=str(media_root)):
                document = Document.objects.create(
                    title='Quick sign detail',
                    owner=actor,
                    status=DOC_STATUS_FINAL,
                    share_status=SHARE_ACTIVE,
                    visibility='private',
                )
                document.output_file.save('quick_sign_detail.docx', ContentFile(b'docx-binary-placeholder'), save=True)
                preview_pdf_path = self._build_preview_pdf(media_root, 'quick-sign-detail.pdf')

                with patch('signing.services.build_document_preview_pdf', return_value=preview_pdf_path):
                    plan = prepare_quick_sign_plan(document, actor, recipient)

                self.client.force_login(actor)
                response = self.client.get(reverse('api:document_detail', args=[document.pk]))

                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json()['assistant_action']['plan_token'], str(plan.token))
                self.assertEqual(response.json()['assistant_action']['status'], 'quick_sign_plan_ready')
        finally:
            shutil.rmtree(media_root, ignore_errors=True)

    def test_quick_sign_plan_execute_rejects_wrong_password(self):
        company = self._create_company('quick-sign-password')
        actor = User.objects.create_user(username='quick_actor_pwd', password='secret')
        recipient = User.objects.create_user(username='quick_recipient_pwd', password='secret')
        self._assign_company(actor, company)
        self._assign_company(recipient, company)

        media_root = Path(settings.BASE_DIR) / '.codex-tmp-pyc' / f'test-quick-sign-pwd-{uuid.uuid4().hex}'
        media_root.mkdir(parents=True, exist_ok=True)
        try:
            with override_settings(MEDIA_ROOT=str(media_root)):
                document = Document.objects.create(
                    title='Quick sign password',
                    owner=actor,
                    status=DOC_STATUS_FINAL,
                    share_status=SHARE_ACTIVE,
                    visibility='private',
                )
                document.output_file.save('quick_sign_password.docx', ContentFile(b'docx-binary-placeholder'), save=True)
                preview_pdf_path = self._build_preview_pdf(media_root, 'quick-sign-password.pdf')

                with patch('signing.services.build_document_preview_pdf', return_value=preview_pdf_path), patch(
                    'signing.services._append_signature_stamp',
                    return_value=None,
                ):
                    plan = prepare_quick_sign_plan(document, actor, recipient)
                    with self.assertRaises(AssistantQuickSignError) as exc_info:
                        execute_quick_sign_and_forward(plan, actor, reauth_password='wrong')

                plan.refresh_from_db()
                self.assertEqual(exc_info.exception.code, 'wrong_password')
                self.assertEqual(plan.status, AssistantQuickSignPlan.Status.FAILED)
                payload = build_quick_sign_plan_payload(plan)
                self.assertEqual(payload['status'], 'operation_failed')
                self.assertEqual(payload['ui_hint']['state'], AssistantQuickSignPlan.Status.FAILED)
                self.assertEqual(payload['message'], 'Mat khau xac nhan khong dung.')
        finally:
            shutil.rmtree(media_root, ignore_errors=True)

    def test_quick_sign_plan_payload_hides_missing_recipient(self):
        company = self._create_company('quick-sign-missing-recipient')
        actor = User.objects.create_user(username='quick_actor_missing', password='secret')
        recipient = User.objects.create_user(username='quick_recipient_missing', password='secret')
        self._assign_company(actor, company)
        self._assign_company(recipient, company)

        media_root = Path(settings.BASE_DIR) / '.codex-tmp-pyc' / f'test-quick-sign-missing-{uuid.uuid4().hex}'
        media_root.mkdir(parents=True, exist_ok=True)
        try:
            with override_settings(MEDIA_ROOT=str(media_root)):
                document = Document.objects.create(
                    title='Quick sign missing recipient',
                    owner=actor,
                    status=DOC_STATUS_FINAL,
                    share_status=SHARE_ACTIVE,
                    visibility='private',
                )
                document.output_file.save(
                    'quick_sign_missing_recipient.docx',
                    ContentFile(b'docx-binary-placeholder'),
                    save=True,
                )
                preview_pdf_path = self._build_preview_pdf(
                    media_root,
                    'quick-sign-missing-recipient.pdf',
                )

                with patch('signing.services.build_document_preview_pdf', return_value=preview_pdf_path):
                    plan = prepare_quick_sign_plan(document, actor, recipient)

                recipient.is_active = False
                recipient.save(update_fields=['is_active'])

                plan = refresh_quick_sign_plan(plan, actor)
                payload = build_quick_sign_plan_payload(plan)

                self.assertEqual(plan.status, AssistantQuickSignPlan.Status.BLOCKED)
                self.assertEqual(payload['status'], 'operation_failed')
                self.assertIsNone(payload['recipient'])
                self.assertEqual(payload['recipient_resolution']['status'], 'not_found')
                self.assertIsNone(payload['recipient_resolution']['recipient'])
        finally:
            shutil.rmtree(media_root, ignore_errors=True)

    def test_quick_sign_plan_execute_marks_partial_then_retries_without_signing_again(self):
        company = self._create_company('quick-sign-partial')
        actor = User.objects.create_user(username='quick_actor_partial', password='secret')
        recipient = User.objects.create_user(username='quick_recipient_partial', password='secret')
        self._assign_company(actor, company)
        self._assign_company(recipient, company)

        media_root = Path(settings.BASE_DIR) / '.codex-tmp-pyc' / f'test-quick-sign-partial-{uuid.uuid4().hex}'
        media_root.mkdir(parents=True, exist_ok=True)
        try:
            with override_settings(MEDIA_ROOT=str(media_root)):
                document = Document.objects.create(
                    title='Quick sign partial',
                    owner=actor,
                    status=DOC_STATUS_FINAL,
                    share_status=SHARE_ACTIVE,
                    visibility='private',
                )
                document.output_file.save('quick_sign_partial.docx', ContentFile(b'docx-binary-placeholder'), save=True)
                preview_pdf_path = self._build_preview_pdf(media_root, 'quick-sign-partial.pdf')

                with patch('signing.services.build_document_preview_pdf', return_value=preview_pdf_path), patch(
                    'signing.services._append_signature_stamp',
                    return_value=None,
                ):
                    plan = prepare_quick_sign_plan(document, actor, recipient)
                    with patch(
                        'documents.mailbox_services.forward_document',
                        side_effect=MailboxFlowError('forward failed'),
                    ):
                        with self.assertRaises(AssistantQuickSignError) as exc_info:
                            execute_quick_sign_and_forward(plan, actor, reauth_password='secret')

                plan.refresh_from_db()
                self.assertEqual(exc_info.exception.code, 'forward_failed')
                self.assertEqual(plan.status, AssistantQuickSignPlan.Status.PARTIAL)
                self.assertIsNotNone(plan.signed_pdf_id)

                with patch('signing.assistant_quick_sign.sign_task') as sign_task_mock:
                    retried = execute_quick_sign_and_forward(plan, actor, reauth_password='')

                self.assertEqual(retried.status, AssistantQuickSignPlan.Status.COMPLETED)
                sign_task_mock.assert_not_called()
        finally:
            shutil.rmtree(media_root, ignore_errors=True)

    def test_quick_sign_plan_execute_blocks_reuse_after_completion(self):
        company = self._create_company('quick-sign-reuse')
        actor = User.objects.create_user(username='quick_actor_reuse', password='secret')
        recipient = User.objects.create_user(username='quick_recipient_reuse', password='secret')
        self._assign_company(actor, company)
        self._assign_company(recipient, company)

        media_root = Path(settings.BASE_DIR) / '.codex-tmp-pyc' / f'test-quick-sign-reuse-{uuid.uuid4().hex}'
        media_root.mkdir(parents=True, exist_ok=True)
        try:
            with override_settings(MEDIA_ROOT=str(media_root)):
                document = Document.objects.create(
                    title='Quick sign reuse',
                    owner=actor,
                    status=DOC_STATUS_FINAL,
                    share_status=SHARE_ACTIVE,
                    visibility='private',
                )
                document.output_file.save('quick_sign_reuse.docx', ContentFile(b'docx-binary-placeholder'), save=True)
                preview_pdf_path = self._build_preview_pdf(media_root, 'quick-sign-reuse.pdf')

                with patch('signing.services.build_document_preview_pdf', return_value=preview_pdf_path), patch(
                    'signing.services._append_signature_stamp',
                    return_value=None,
                ):
                    plan = prepare_quick_sign_plan(document, actor, recipient)
                    completed = execute_quick_sign_and_forward(plan, actor, reauth_password='secret')
                    with self.assertRaises(AssistantQuickSignError) as exc_info:
                        execute_quick_sign_and_forward(completed, actor, reauth_password='secret')

                self.assertEqual(exc_info.exception.code, 'plan_already_completed')
        finally:
            shutil.rmtree(media_root, ignore_errors=True)

    def test_pending_hr_proposals_are_company_scoped(self):
        company_a = self._create_company('review-a')
        company_b = self._create_company('review-b')
        reviewer_a = User.objects.create_user(username='reviewer_a', password='secret')
        reviewer_b = User.objects.create_user(username='reviewer_b', password='secret')
        proposer_a = User.objects.create_user(username='proposer_a', password='secret')
        proposer_b = User.objects.create_user(username='proposer_b', password='secret')
        signer_a = User.objects.create_user(username='signer_a', password='secret')
        signer_b = User.objects.create_user(username='signer_b', password='secret')
        self._assign_company(reviewer_a, company_a)
        self._assign_company(reviewer_b, company_b)
        self._assign_company(proposer_a, company_a)
        self._assign_company(proposer_b, company_b)
        self._assign_company(signer_a, company_a)
        self._assign_company(signer_b, company_b)
        Department.objects.create(company=company_a, name='Nhan su', code='HRA', manager=reviewer_a)
        Department.objects.create(company=company_b, name='Nhan su', code='HRB', manager=reviewer_b)

        media_root = Path(settings.BASE_DIR) / '.codex-tmp-pyc' / f'test-media-{uuid.uuid4().hex}'
        media_root.mkdir(parents=True, exist_ok=True)
        try:
            with override_settings(MEDIA_ROOT=str(media_root)):
                document_a = Document.objects.create(
                    title='Proposal A',
                    owner=proposer_a,
                    status=DOC_STATUS_FINAL,
                    share_status=SHARE_ACTIVE,
                    visibility='private',
                )
                document_a.output_file.save('proposal_a.docx', ContentFile(b'a'), save=True)
                proposal_a = create_signing_proposal(
                    document_a,
                    proposer_a,
                    [
                        {
                            'user': signer_a,
                            'display_role': 'Signer A',
                            'step_no': 1,
                            'required': True,
                            'group_context': '',
                        },
                    ],
                    proposal_note='A',
                )

                document_b = Document.objects.create(
                    title='Proposal B',
                    owner=proposer_b,
                    status=DOC_STATUS_FINAL,
                    share_status=SHARE_ACTIVE,
                    visibility='private',
                )
                document_b.output_file.save('proposal_b.docx', ContentFile(b'b'), save=True)
                create_signing_proposal(
                    document_b,
                    proposer_b,
                    [
                        {
                            'user': signer_b,
                            'display_role': 'Signer B',
                            'step_no': 1,
                            'required': True,
                            'group_context': '',
                        },
                    ],
                    proposal_note='B',
                )

                self.assertTrue(can_review_signing_proposals(reviewer_a))
                pending_ids = list(get_pending_hr_proposals(reviewer_a).values_list('id', flat=True))
                self.assertEqual(pending_ids, [proposal_a.id])
        finally:
            shutil.rmtree(media_root, ignore_errors=True)

    def test_signed_pdf_download_blocks_cross_company_storage_prefix(self):
        company_a = self._create_company('signed-a')
        company_b = self._create_company('signed-b')
        owner = User.objects.create_user(username='signed_owner', password='secret')
        reviewer = User.objects.create_user(username='signed_reviewer', password='secret')
        signer = User.objects.create_user(username='signed_signer', password='secret')
        self._assign_company(owner, company_a)
        self._assign_company(reviewer, company_a)
        self._assign_company(signer, company_a)
        Department.objects.create(company=company_a, name='Nhan su', code='HR-SIGNED', manager=reviewer)

        media_root = Path(settings.BASE_DIR) / '.codex-tmp-pyc' / f'test-media-{uuid.uuid4().hex}'
        media_root.mkdir(parents=True, exist_ok=True)
        try:
            with override_settings(MEDIA_ROOT=str(media_root)):
                document = Document.objects.create(
                    title='Tampered signed pdf',
                    owner=owner,
                    status=DOC_STATUS_FINAL,
                    share_status=SHARE_ACTIVE,
                    visibility='private',
                )
                document.output_file.save('signed_pdf_guard.docx', ContentFile(b'docx-binary-placeholder'), save=True)
                proposal = create_signing_proposal(
                    document,
                    owner,
                    [
                        {
                            'user': signer,
                            'display_role': 'Nguoi ky',
                            'step_no': 1,
                            'required': True,
                            'group_context': '',
                        },
                    ],
                    proposal_note='guard',
                )

                preview_pdf_path = media_root / 'preview.pdf'
                pdf = fitz.open()
                pdf.new_page()
                pdf.save(preview_pdf_path)
                pdf.close()

                with patch('signing.services.build_document_preview_pdf', return_value=preview_pdf_path):
                    packet = approve_signing_proposal(proposal, reviewer, 'ok')

                signed_doc = SignedPdfDocument.objects.create(
                    packet=packet,
                    title='Tampered signed pdf',
                    company=company_a,
                    owner=owner,
                    source_document=document,
                    source_version_number=document.version_number,
                    signed_pdf_file=(
                        f"companies/{company_storage_slug(company_b)}/signed_pdfs/"
                        f"document_{document.id}/tampered.pdf"
                    ),
                    signature_mode='internal_approval',
                    verification_status='internal_approval',
                )

                self.client.force_login(owner)
                response = self.client.get(reverse('api:signed_pdf_download', args=[signed_doc.pk]))
                self.assertEqual(response.status_code, 403)
                self.assertIn('cong ty khac', str(response.data.get('detail', '')).lower())
        finally:
            shutil.rmtree(media_root, ignore_errors=True)
