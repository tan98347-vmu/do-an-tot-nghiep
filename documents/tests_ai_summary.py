from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.models import Company, CompanyStatus, CompanyUserMembership
from documents.models import Document


class _FakeLlm:
    def __init__(self, content: str):
        self.content = content
        self.messages = None

    def invoke(self, messages):
        self.messages = messages
        return SimpleNamespace(content=self.content)


class DocumentAiSummaryTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.company = Company.objects.create(
            code='summary-a',
            name='Summary A',
            status=CompanyStatus.ACTIVE,
        )
        self.user = User.objects.create_user(username='summary-user', password='secret')
        CompanyUserMembership.objects.create(
            company=self.company,
            user=self.user,
            local_username='summary-user',
            role='company_user',
            is_active=True,
        )
        self.client.force_authenticate(self.user)

    def test_document_summarize_returns_summary_for_html_content(self):
        document = Document.objects.create(
            company=self.company,
            owner=self.user,
            title='Thong bao nghi le',
            content='<p>Thong bao nghi le ngay 20/05.</p><p>Toan bo nhan vien nghi lam.</p>',
        )
        fake_llm = _FakeLlm(
            'Tóm tắt nhanh:\nThông báo nghỉ lễ ngày 20/05.\n\nÝ chính:\n- Toàn bộ nhân viên được nghỉ làm.\n\nLưu ý:\n- Theo dõi thông báo nội bộ.'
        )

        with patch('documents.ai_summary.get_llm', return_value=fake_llm):
            response = self.client.post(reverse('api:document_summarize', args=[document.pk]))

        self.assertEqual(response.status_code, 200, response.content)
        payload = response.json()
        self.assertIn('Tóm tắt nhanh', payload['summary'])
        self.assertEqual(payload['source_kind'], 'content')
        self.assertEqual(payload['chunk_count'], 1)
        self.assertIn('Thong bao nghi le ngay 20/05.', fake_llm.messages[-1].content)
        self.assertNotIn('<p>', fake_llm.messages[-1].content)

    def test_document_summarize_returns_conflict_when_document_has_no_text(self):
        document = Document.objects.create(
            company=self.company,
            owner=self.user,
            title='Van ban rong',
            content='',
            notes='',
        )

        response = self.client.post(reverse('api:document_summarize', args=[document.pk]))

        self.assertEqual(response.status_code, 409, response.content)
        self.assertIn('chua co noi dung', response.json()['detail'].lower())
