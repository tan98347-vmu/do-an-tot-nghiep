# Chức năng web liên quan: Yêu cầu ký, PDF đã ký, Hòm thư và Ủy quyền ký số.
# Vai trò backend trong luồng: Tệp này gom nghiệp vụ nhiều bước, transaction và side effect khó của đề xuất ký, nhiệm vụ ký, PDF đã ký, xác minh chữ ký và ủy quyền ký số; nó đứng sau các nút thao tác quan trọng xuất hiện ở màn Yêu cầu ký, chi tiết ký, PDF đã ký, dialog đề xuất ký, dialog chọn người ký và màn Ủy quyền ký số.
# Đầu vào/đầu ra chính: Nhận dữ liệu đã qua bước kiểm tra, thực hiện transaction, cập nhật nhiều bản ghi, đụng tới file, storage, integrity hoặc gọi engine ngoài rồi trả kết quả trung gian cho endpoint.
# Người dùng sẽ thấy trên web: Các thao tác nhiều bước ở các chức năng Yêu cầu ký, PDF đã ký, Hòm thư và Ủy quyền ký số hoàn tất nhất quán; web không rơi vào trạng thái nửa chừng giữa DB, file, badge và timeline.

import hashlib
import shutil
import uuid
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch

import fitz
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding as asym_padding, utils as asym_utils
from django.conf import settings
from django.contrib.auth.models import User
from django.core.files.base import ContentFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from documents.models import DOC_STATUS_FINAL, SHARE_ACTIVE, Document
from signing.internal_pki import ensure_user_signing_credential, get_private_key_pem_for_credential
from signing.models import (
    CREDENTIAL_STATUS_ACTIVE,
    SIGNATURE_MODE_PDF_PKCS7,
    PdfSignatureRecord,
    UserSigningCredential,
)
from signing.pki import _sign_digest_locally, load_crypto_certificate
from signing.services import (
    SigningFlowError,
    approve_signing_proposal,
    create_signing_proposal,
    sign_task,
)

# [Web] `PkiSigningFlowTests` gom một cụm xử lý backend dùng chung cho nhóm màn Yêu cầu ký, PDF đã ký và Ủy quyền ký số.

@override_settings(
    SIGNING_DEFAULT_SIGNATURE_MODE='pdf_pkcs7',
    SIGNING_REMOTE_HSM={'base_url': 'https://hsm.internal'},
)
class PkiSigningFlowTests(TestCase):
    CERT_META = {
        'subject_dn': 'CN=Signer One,OU=Internal PKI,O=MyWorld',
        'issuer_dn': 'CN=MyWorld Root CA,O=MyWorld',
        'serial_number': 'A1B2C3D4',
        'fingerprint_sha256': 'f0' * 32,
    }

    # [Web] `_make_media_root` là bước nội bộ của class để hỗ trợ dữ liệu hoặc trạng thái mà nhóm màn Yêu cầu ký, PDF đã ký và Ủy quyền ký số đang cần.

    def _make_media_root(self):
        media_root = Path(settings.BASE_DIR) / '.codex-tmp-pyc' / f'test-media-{uuid.uuid4().hex}'
        media_root.mkdir(parents=True, exist_ok=True)
        return media_root

    # [Web] `_build_preview_pdf` là bước nội bộ của class để hỗ trợ dữ liệu hoặc trạng thái mà nhóm màn Yêu cầu ký, PDF đã ký và Ủy quyền ký số đang cần.

    def _build_preview_pdf(self, output_path):
        pdf = fitz.open()
        pdf.new_page()
        pdf.save(output_path)
        pdf.close()

    # [Web] `_copy_prepared_pdf` là bước nội bộ của class để hỗ trợ dữ liệu hoặc trạng thái mà nhóm màn Yêu cầu ký, PDF đã ký và Ủy quyền ký số đang cần.

    def _copy_prepared_pdf(self, source_path, output_path, signature_fields):
        del signature_fields
        shutil.copy2(source_path, output_path)

    # [Web] `_create_document` là bước nội bộ của class để hỗ trợ dữ liệu hoặc trạng thái mà nhóm màn Yêu cầu ký, PDF đã ký và Ủy quyền ký số đang cần.

    def _create_document(self, owner, title):
        document = Document.objects.create(
            title=title,
            owner=owner,
            status=DOC_STATUS_FINAL,
            share_status=SHARE_ACTIVE,
            visibility='private',
        )
        document.output_file.save(
            f'{title.lower().replace(" ", "_")}.docx',
            ContentFile(b'docx-binary-placeholder'),
            save=True,
        )
        return document

    # [Web] `_create_active_credential` là bước nội bộ của class để hỗ trợ dữ liệu hoặc trạng thái mà nhóm màn Yêu cầu ký, PDF đã ký và Ủy quyền ký số đang cần.

    def _create_active_credential(self, user):
        now = timezone.now()
        return UserSigningCredential.objects.create(
            user=user,
            provider='remote_hsm',
            key_alias='alias-signer-one',
            key_id='key-signer-one',
            certificate_pem='-----BEGIN CERTIFICATE-----\nDUMMY\n-----END CERTIFICATE-----',
            subject_dn=self.CERT_META['subject_dn'],
            serial_number=self.CERT_META['serial_number'],
            issuer_dn=self.CERT_META['issuer_dn'],
            valid_from=now - timedelta(days=1),
            valid_to=now + timedelta(days=30),
            status=CREDENTIAL_STATUS_ACTIVE,
        )

    # [Web] `_approve_single_signer_packet` là bước nội bộ của class để hỗ trợ dữ liệu hoặc trạng thái mà nhóm màn Yêu cầu ký, PDF đã ký và Ủy quyền ký số đang cần.

    def _approve_single_signer_packet(self, media_root, document, proposer, reviewer, signer):
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
        self._build_preview_pdf(preview_pdf_path)

        with patch('signing.services.build_document_preview_pdf', return_value=preview_pdf_path), patch(
            'signing.services.prepare_pdf_signature_fields',
            side_effect=self._copy_prepared_pdf,
        ):
            packet = approve_signing_proposal(proposal, reviewer, 'ok')

        task = packet.tasks.get(signer_user=signer)
        return packet, task

    # [Web] `_fake_validate_report` là bước nội bộ của class để hỗ trợ dữ liệu hoặc trạng thái mà nhóm màn Yêu cầu ký, PDF đã ký và Ủy quyền ký số đang cần.

    def _fake_validate_report(self, task, fingerprint):
        return {
            'status': 'safe',
            'is_safe': True,
            'is_access_allowed': True,
            'summary': 'Embedded PDF signatures are valid.',
            'checked_at': timezone.now().isoformat(),
            'signature_mode': 'pdf_pkcs7',
            'signature_count': 1,
            'signer_reports': [
                {
                    'field_name': task.signature_field_name,
                    'task_id': task.id,
                    'signer_user_id': task.signer_user_id,
                    'signer_name': task.signer_user.get_full_name() or task.signer_user.username,
                    'display_role': task.display_role,
                    'step_no': task.step_no,
                    'status': 'safe',
                    'is_valid': True,
                    'detail': 'Embedded PDF signature is valid and trusted.',
                    'signed_at': timezone.now().isoformat(),
                    'subject_dn': self.CERT_META['subject_dn'],
                    'issuer_dn': self.CERT_META['issuer_dn'],
                    'serial_number': self.CERT_META['serial_number'],
                    'certificate_fingerprint': fingerprint,
                    'digest_algorithm': 'sha256',
                    'signature_algorithm': 'sha256_rsa',
                    'integrity': {
                        'intact': True,
                        'valid': True,
                        'trusted': True,
                        'bottom_line': True,
                        'coverage': 'ENTIRE_FILE',
                        'modification_level': 'NONE',
                    },
                    'chain': [
                        {
                            'subject_dn': self.CERT_META['issuer_dn'],
                            'issuer_dn': self.CERT_META['issuer_dn'],
                            'serial_number': 'ROOT-CA',
                            'fingerprint_sha256': 'ab' * 32,
                        },
                    ],
                },
            ],
            'steps': [
                {
                    'code': 'signature_presence',
                    'label': 'Embedded signature present',
                    'status': 'passed',
                    'detail': 'Found one embedded CMS signature.',
                },
            ],
        }

    # [Web] `test_signature_context_reports_auto_provisioned_and_explicit_credential` là bước nội bộ của class để hỗ trợ dữ liệu hoặc trạng thái mà nhóm màn Yêu cầu ký, PDF đã ký và Ủy quyền ký số đang cần.

    def test_signature_context_reports_auto_provisioned_and_explicit_credential(self):
        proposer = User.objects.create_user(username='proposer', password='secret')
        reviewer = User.objects.create_user(username='reviewer', password='secret')
        signer = User.objects.create_user(username='signer', password='secret')

        media_root = self._make_media_root()
        try:
            with override_settings(MEDIA_ROOT=str(media_root)):
                document = self._create_document(proposer, 'PKI context demo')
                packet, task = self._approve_single_signer_packet(media_root, document, proposer, reviewer, signer)

                self.assertEqual(packet.signature_mode, SIGNATURE_MODE_PDF_PKCS7)
                self.assertTrue(task.signature_field_name)

                self.client.force_login(signer)
                response = self.client.get(reverse('api:signing_task_signature_context', args=[task.pk]))
                self.assertEqual(response.status_code, 200)
                payload = response.json()
                self.assertTrue(payload['can_sign'])
                self.assertTrue(payload['credential_required'])
                self.assertTrue(payload['credential_bound'])
                self.assertTrue(payload['provider_ready'])
                self.assertEqual(payload['certificate']['provider'], 'internal_pki')

                self._create_active_credential(signer)
                with patch('signing.services.certificate_metadata_from_pem', return_value=self.CERT_META), patch(
                    'signing.services.RemoteHsmSigner.get_provider_readiness',
                    return_value=(True, 'Remote HSM ready'),
                ):
                    response = self.client.get(reverse('api:signing_task_signature_context', args=[task.pk]))

                self.assertEqual(response.status_code, 200)
                payload = response.json()
                self.assertTrue(payload['can_sign'])
                self.assertTrue(payload['provider_ready'])
                self.assertTrue(payload['credential_bound'])
                self.assertEqual(payload['certificate']['provider'], 'remote_hsm')
                self.assertEqual(payload['certificate']['subject_dn'], self.CERT_META['subject_dn'])
                self.assertEqual(payload['certificate']['serial_number'], self.CERT_META['serial_number'])
        finally:
            shutil.rmtree(media_root, ignore_errors=True)

    # [Web] `test_pdf_pkcs7_sign_creates_signature_record_and_safe_verify` là bước nội bộ của class để hỗ trợ dữ liệu hoặc trạng thái mà nhóm màn Yêu cầu ký, PDF đã ký và Ủy quyền ký số đang cần.

    def test_pdf_pkcs7_sign_creates_signature_record_and_safe_verify(self):
        proposer = User.objects.create_user(username='proposer', password='secret')
        reviewer = User.objects.create_user(username='reviewer', password='secret')
        signer = User.objects.create_user(username='signer', password='secret')

        media_root = self._make_media_root()
        try:
            with override_settings(MEDIA_ROOT=str(media_root)):
                document = self._create_document(proposer, 'PKI sign demo')
                packet, task = self._approve_single_signer_packet(media_root, document, proposer, reviewer, signer)
                self._create_active_credential(signer)

                # [Web] `fake_sign_pdf_incremental` là bước con bên trong `test_pdf_pkcs7_sign_creates_signature_record_and_safe_verify` để tách một phép xử lý nhỏ cho dễ đọc và khó sai hơn.

                def fake_sign_pdf_incremental(source_path, output_path, field_name, credential, signer_display_name, reason_text):
                    del field_name, credential, signer_display_name, reason_text
                    shutil.copy2(source_path, output_path)
                    return {
                        'provider_transaction_id': 'tx-001',
                        'digest_algorithm': 'sha256',
                        'signature_algorithm': 'sha256_rsa',
                        'certificate_fingerprint': self.CERT_META['fingerprint_sha256'],
                        'certificate_subject_dn': self.CERT_META['subject_dn'],
                        'certificate_serial_number': self.CERT_META['serial_number'],
                        'certificate_issuer_dn': self.CERT_META['issuer_dn'],
                    }

                # [Web] `fake_validate_pdf_signatures` là bước con bên trong `test_pdf_pkcs7_sign_creates_signature_record_and_safe_verify` để tách một phép xử lý nhỏ cho dễ đọc và khó sai hơn.

                def fake_validate_pdf_signatures(pdf_path, task_by_field_name=None):
                    del pdf_path
                    matched_task = next(iter((task_by_field_name or {}).values()))
                    return self._fake_validate_report(matched_task, self.CERT_META['fingerprint_sha256'])

                with patch('signing.services.certificate_metadata_from_pem', return_value=self.CERT_META), patch(
                    'signing.services.RemoteHsmSigner.get_provider_readiness',
                    return_value=(True, 'Remote HSM ready'),
                ), patch(
                    'signing.services.sign_pdf_incremental',
                    side_effect=fake_sign_pdf_incremental,
                ), patch(
                    'signing.services.validate_pdf_signatures',
                    side_effect=fake_validate_pdf_signatures,
                ):
                    result = sign_task(task, signer, 'secret')

                    self.assertIsNotNone(result['signed_pdf'])
                    self.assertEqual(result['verification_report']['status'], 'safe')
                    self.assertIsNotNone(result['signature_record'])

                    signed_doc = result['signed_pdf']
                    signed_doc.refresh_from_db()
                    self.assertEqual(signed_doc.signature_mode, SIGNATURE_MODE_PDF_PKCS7)
                    self.assertEqual(signed_doc.verification_status, 'safe')
                    self.assertEqual(signed_doc.signature_count, 1)

                    signature_record = PdfSignatureRecord.objects.get(task=task)
                    self.assertEqual(signature_record.provider_transaction_id, 'tx-001')
                    self.assertEqual(signature_record.verification_status, 'safe')
                    self.assertEqual(signature_record.certificate_subject_dn, self.CERT_META['subject_dn'])

                    self.client.force_login(proposer)
                    verify_response = self.client.get(reverse('api:signed_pdf_verify', args=[signed_doc.pk]))
                    detail_response = self.client.get(reverse('api:signed_pdf_detail', args=[signed_doc.pk]))

                self.assertEqual(verify_response.status_code, 200)
                self.assertEqual(verify_response.json()['status'], 'safe')
                self.assertEqual(detail_response.status_code, 200)
                self.assertEqual(detail_response.json()['signature_mode'], 'pdf_pkcs7')
                self.assertEqual(detail_response.json()['verification_status'], 'safe')
                self.assertEqual(len(detail_response.json()['signing_events']), 1)
                self.assertEqual(
                    detail_response.json()['signing_events'][0]['certificate_subject_dn'],
                    self.CERT_META['subject_dn'],
                )
        finally:
            shutil.rmtree(media_root, ignore_errors=True)

    # [Web] `test_pdf_pkcs7_rejects_credential_binding_mismatch` là bước nội bộ của class để hỗ trợ dữ liệu hoặc trạng thái mà nhóm màn Yêu cầu ký, PDF đã ký và Ủy quyền ký số đang cần.

    def test_pdf_pkcs7_rejects_credential_binding_mismatch(self):
        proposer = User.objects.create_user(username='proposer', password='secret')
        reviewer = User.objects.create_user(username='reviewer', password='secret')
        signer = User.objects.create_user(username='signer', password='secret')

        media_root = self._make_media_root()
        try:
            with override_settings(MEDIA_ROOT=str(media_root)):
                document = self._create_document(proposer, 'PKI mismatch demo')
                packet, task = self._approve_single_signer_packet(media_root, document, proposer, reviewer, signer)
                self._create_active_credential(signer)
                self.assertEqual(packet.signature_mode, SIGNATURE_MODE_PDF_PKCS7)

                # [Web] `fake_sign_pdf_incremental` là bước con bên trong `test_pdf_pkcs7_rejects_credential_binding_mismatch` để tách một phép xử lý nhỏ cho dễ đọc và khó sai hơn.

                def fake_sign_pdf_incremental(source_path, output_path, field_name, credential, signer_display_name, reason_text):
                    del field_name, credential, signer_display_name, reason_text
                    shutil.copy2(source_path, output_path)
                    return {
                        'provider_transaction_id': 'tx-mismatch',
                        'digest_algorithm': 'sha256',
                        'signature_algorithm': 'sha256_rsa',
                        'certificate_fingerprint': self.CERT_META['fingerprint_sha256'],
                        'certificate_subject_dn': self.CERT_META['subject_dn'],
                        'certificate_serial_number': self.CERT_META['serial_number'],
                        'certificate_issuer_dn': self.CERT_META['issuer_dn'],
                    }

                # [Web] `fake_validate_pdf_signatures` là bước con bên trong `test_pdf_pkcs7_rejects_credential_binding_mismatch` để tách một phép xử lý nhỏ cho dễ đọc và khó sai hơn.

                def fake_validate_pdf_signatures(pdf_path, task_by_field_name=None):
                    del pdf_path
                    matched_task = next(iter((task_by_field_name or {}).values()))
                    return self._fake_validate_report(matched_task, '00' * 32)

                with patch('signing.services.certificate_metadata_from_pem', return_value=self.CERT_META), patch(
                    'signing.services.RemoteHsmSigner.get_provider_readiness',
                    return_value=(True, 'Remote HSM ready'),
                ), patch(
                    'signing.services.sign_pdf_incremental',
                    side_effect=fake_sign_pdf_incremental,
                ), patch(
                    'signing.services.validate_pdf_signatures',
                    side_effect=fake_validate_pdf_signatures,
                ):
                    with self.assertRaises(SigningFlowError):
                        sign_task(task, signer, 'secret')

                task.refresh_from_db()
                self.assertEqual(task.status, 'available')
                self.assertFalse(PdfSignatureRecord.objects.filter(task=task).exists())
        finally:
            shutil.rmtree(media_root, ignore_errors=True)

    # [Web] `test_sign_digest_locally_signs_rsa_digest_for_internal_pki_credential` là bước nội bộ của class để hỗ trợ dữ liệu hoặc trạng thái mà nhóm màn Yêu cầu ký, PDF đã ký và Ủy quyền ký số đang cần.

    def test_sign_digest_locally_signs_rsa_digest_for_internal_pki_credential(self):
        signer = User.objects.create_user(username='local-signer', password='secret')
        credential = ensure_user_signing_credential(signer)
        private_key_pem = get_private_key_pem_for_credential(credential)

        digest_bytes = hashlib.sha256(b'pkcs7-local-signature-regression').digest()
        signature = _sign_digest_locally(
            private_key_pem,
            credential.certificate_pem,
            digest_bytes,
            'sha256',
        )

        certificate = load_crypto_certificate(credential.certificate_pem)
        certificate.public_key().verify(
            signature,
            digest_bytes,
            asym_padding.PKCS1v15(),
            asym_utils.Prehashed(hashes.SHA256()),
        )
        self.assertTrue(signature)
