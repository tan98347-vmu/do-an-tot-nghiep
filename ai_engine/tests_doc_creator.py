import shutil
import uuid
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from django.conf import settings
from django.test import TestCase, override_settings

from accounts.company_services import create_company_user
from accounts.models import Company, CompanyRole, CompanyStatus
from accounts.storage_paths import company_storage_slug
from ai_engine.doc_creator import create_document_from_intent
from document_templates.models import DocumentTemplate


class _FakeLlm:
    def __init__(self, responses):
        self._responses = list(responses)
        self.calls = []

    def invoke(self, messages):
        self.calls.append(messages)
        return SimpleNamespace(content=self._responses.pop(0))


class DocCreatorContextPrefillTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(
            code='doc-creator',
            name='Doc Creator Company',
            status=CompanyStatus.ACTIVE,
            company_context='Ten cong ty la CTY PREFILL. Dia chi cong ty o 123 Duong ABC.',
        )
        bootstrap = create_company_user(
            company=self.company,
            local_username='employee',
            password='secret123',
            email='employee@example.com',
            role=CompanyRole.COMPANY_USER,
            full_name='Nguyen Van A',
            profile_data={
                'so_yeu_ly_lich': 'Nhan vien phong hanh chinh.',
                'chuc_danh': 'Chuyen vien',
            },
        )
        self.user = bootstrap.user
        self.template = DocumentTemplate.objects.create(
            owner=self.user,
            title='Don de nghi',
            description='Mau don de nghi co bien co ban.',
            content='{{ho_ten}} | {{ten_cong_ty}} | {{ly_do}}',
            visibility='private',
            status='approved',
        )

    def _make_media_root(self):
        media_root = Path(settings.BASE_DIR) / '.codex-tmp-pyc' / f'test-doc-creator-{uuid.uuid4().hex}'
        media_root.mkdir(parents=True, exist_ok=True)
        return media_root

    def test_prefills_blank_variables_from_effective_context_after_user_values(self):
        media_root = self._make_media_root()
        fake_llm = _FakeLlm([
            (
                '{"template_id": %d, "doc_title": "Don cong tac", '
                '"variables": {"ho_ten": "", "ten_cong_ty": "", "ly_do": "Cong tac ngan han"}, '
                '"explanation": "Da chon mau phu hop."}'
            ) % self.template.pk,
            '{"ho_ten": "Nguyen Van A", "ten_cong_ty": "CTY PREFILL", "ly_do": ""}',
        ])
        try:
            with override_settings(MEDIA_ROOT=str(media_root)):
                with patch('ai_engine.rag_engine.get_llm', return_value=fake_llm):
                    answer, document, _, _ = create_document_from_intent(
                        'Tao don de nghi cong tac ngan han.',
                        self.user,
                    )

            self.assertIsNotNone(document)
            self.assertIn('Nguyen Van A', document.content)
            self.assertIn('CTY PREFILL', document.content)
            self.assertIn('Cong tac ngan han', document.content)
            self.assertIn('Don cong tac', answer)
            self.assertTrue(
                document.output_file.name.startswith(
                    f'companies/{company_storage_slug(self.company)}/generated_docs/'
                )
            )
            self.assertNotIn('NGU CANH HE THONG', fake_llm.calls[0][1].content)
            self.assertIn('EFFECTIVE CONTEXT', fake_llm.calls[1][1].content)
        finally:
            shutil.rmtree(media_root, ignore_errors=True)

    def test_context_prefill_never_overwrites_user_supplied_values(self):
        media_root = self._make_media_root()
        fake_llm = _FakeLlm([
            (
                '{"template_id": %d, "doc_title": "Don nghi phep", '
                '"variables": {"ho_ten": "Tran Thi B", "ten_cong_ty": "Cong ty Khach Hang", "ly_do": ""}, '
                '"explanation": "Da chon mau don nghi phep."}'
            ) % self.template.pk,
            '{"ho_ten": "Nguyen Van A", "ten_cong_ty": "CTY PREFILL", "ly_do": "Nghi phep ca nhan"}',
        ])
        try:
            with override_settings(MEDIA_ROOT=str(media_root)):
                with patch('ai_engine.rag_engine.get_llm', return_value=fake_llm):
                    _, document, _, _ = create_document_from_intent(
                        'Tao don nghi phep cho Tran Thi B tai Cong ty Khach Hang.',
                        self.user,
                    )

            self.assertIsNotNone(document)
            self.assertIn('Tran Thi B', document.content)
            self.assertIn('Cong ty Khach Hang', document.content)
            self.assertIn('Nghi phep ca nhan', document.content)
            self.assertNotIn('Nguyen Van A | CTY PREFILL', document.content)
        finally:
            shutil.rmtree(media_root, ignore_errors=True)
