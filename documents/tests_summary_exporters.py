from io import BytesIO
from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from docx import Document as DocxDocument
from rest_framework.test import APIClient

from accounts.models import Company, CompanyStatus, CompanyUserMembership
from documents.models import Document
from documents.summary_exporters import export_summary_docx, export_summary_md


class SummaryExporterTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.company = Company.objects.create(
            code='summary-export',
            name='Summary Export',
            status=CompanyStatus.ACTIVE,
        )
        self.user = User.objects.create_user(
            username='summary-export-user',
            password='secret',
            first_name='Summary',
            last_name='Owner',
        )
        CompanyUserMembership.objects.create(
            company=self.company,
            user=self.user,
            local_username='summary-export-user',
            role='company_user',
            is_active=True,
        )
        self.client.force_authenticate(self.user)
        self.document = Document.objects.create(
            company=self.company,
            owner=self.user,
            title='Thong bao he thong',
            content='Noi dung van ban de tom tat.',
        )

    def _summary_object(self):
        return SimpleNamespace(
            document=self.document,
            created_at=self.document.created_at,
            created_by=self.user,
            model_name='kimi-k2.6:cloud',
            content_md='# Muc 1\n- Y dau dong\n**Dam** noi dung',
        )

    def test_export_summary_docx_renders_heading_and_bullets(self):
        payload = export_summary_docx(self._summary_object())
        parsed = DocxDocument(BytesIO(payload))
        paragraphs = [paragraph.text for paragraph in parsed.paragraphs if paragraph.text.strip()]
        self.assertTrue(paragraphs[0].startswith('Tóm tắt: Thong bao he thong'))
        self.assertIn('Muc 1', paragraphs)
        self.assertIn('Y dau dong', paragraphs)

    def test_export_summary_md_contains_frontmatter(self):
        payload = export_summary_md(self._summary_object())
        self.assertIn('title: "Tóm tắt: Thong bao he thong"', payload)
        self.assertIn('model: "kimi-k2.6:cloud"', payload)
        self.assertIn('# Muc 1', payload)

    def test_download_summary_returns_docx_attachment(self):
        with patch('documents.ai_summary.get_llm') as mocked_get_llm:
            mocked_get_llm.return_value.invoke.return_value = SimpleNamespace(
                content='Tom tat nhanh\n\n- Muc 1'
            )
            generate_response = self.client.post(
                reverse('api:document_summary_generate', args=[self.document.pk]),
                data={
                    'options': {
                        'length': 'brief',
                        'language': 'vi',
                        'style': 'bullet',
                    },
                },
                format='json',
            )

        self.assertEqual(generate_response.status_code, 200, generate_response.content)

        response = self.client.get(
            reverse('api:document_summary_download', args=[self.document.pk]),
            {'format': 'DOCX'},
        )

        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(
            response['Content-Type'],
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        )
        self.assertIn('filename=', response['Content-Disposition'])
        self.assertIn("filename*=UTF-8''", response['Content-Disposition'])
