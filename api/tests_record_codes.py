from django.contrib.auth.models import User
from rest_framework.test import APITestCase

from accounts.models import Company, CompanyStatus, CompanyUserMembership
from accounts.record_codes import (
    DOCUMENT_RECORD_PREFIX,
    TEMPLATE_RECORD_PREFIX,
    format_record_code,
    parse_record_code,
)
from document_templates.models import DocumentTemplate
from documents.models import Document


class RecordCodeApiTests(APITestCase):
    def setUp(self):
        self.company = Company.objects.create(
            code='record-code-tests',
            name='Record Code Tests',
            status=CompanyStatus.ACTIVE,
        )
        self.user = User.objects.create_user(
            username='record-code-user',
            password='secret',
        )
        CompanyUserMembership.objects.create(
            company=self.company,
            user=self.user,
            local_username='record-code-user',
            role='company_user',
            is_active=True,
        )
        self.template = DocumentTemplate.objects.create(
            company=self.company,
            owner=self.user,
            title='Mau trung ten',
            content='Noi dung mau',
        )
        self.document = Document.objects.create(
            company=self.company,
            owner=self.user,
            title='Van ban trung ten',
            content='Noi dung van ban',
        )
        self.client.force_authenticate(self.user)

    def test_record_code_format_and_parse(self):
        self.assertEqual(
            self.document.record_code,
            format_record_code(DOCUMENT_RECORD_PREFIX, self.document.pk),
        )
        self.assertEqual(
            self.template.record_code,
            format_record_code(TEMPLATE_RECORD_PREFIX, self.template.pk),
        )
        self.assertEqual(
            parse_record_code(self.document.record_code, DOCUMENT_RECORD_PREFIX),
            self.document.pk,
        )
        self.assertEqual(
            parse_record_code(self.template.record_code.lower(), TEMPLATE_RECORD_PREFIX),
            self.template.pk,
        )

    def test_document_list_detail_and_search_expose_record_code(self):
        list_response = self.client.get(
            '/api/documents/',
            {'group': 'private', 'q': self.document.record_code},
        )
        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(
            [item['record_code'] for item in list_response.data],
            [self.document.record_code],
        )

        detail_response = self.client.get(f'/api/documents/{self.document.pk}/')
        self.assertEqual(detail_response.status_code, 200)
        self.assertEqual(detail_response.data['record_code'], self.document.record_code)

    def test_template_list_detail_and_search_expose_record_code(self):
        list_response = self.client.get(
            '/api/templates/',
            {'group': 'private', 'q': self.template.record_code},
        )
        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(
            [item['record_code'] for item in list_response.data],
            [self.template.record_code],
        )

        detail_response = self.client.get(f'/api/templates/{self.template.pk}/')
        self.assertEqual(detail_response.status_code, 200)
        self.assertEqual(detail_response.data['record_code'], self.template.record_code)
