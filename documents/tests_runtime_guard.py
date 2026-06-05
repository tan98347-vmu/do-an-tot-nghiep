from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from rest_framework.exceptions import PermissionDenied
from rest_framework.test import APIClient

from accounts.models import Company, CompanyStatus, CompanyUserMembership
from accounts.storage_paths import company_storage_slug
from documents.models import Document
from documents.preview_builder import build_document_preview_pdf


class DocumentRuntimeGuardTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.company_a = Company.objects.create(code='guard-a', name='Guard A', status=CompanyStatus.ACTIVE)
        self.company_b = Company.objects.create(code='guard-b', name='Guard B', status=CompanyStatus.ACTIVE)
        self.user = User.objects.create_user(username='guard-owner', password='secret')
        CompanyUserMembership.objects.create(
            company=self.company_a,
            user=self.user,
            local_username='guard-owner',
            role='company_user',
            is_active=True,
        )
        self.client.force_authenticate(self.user)
        self.document = Document.objects.create(
            title='Runtime Guard Document',
            owner=self.user,
            content='Noi dung',
        )

    def test_document_download_blocks_cross_company_storage_prefix(self):
        self.document.output_file = (
            f"companies/{company_storage_slug(self.company_b)}/generated_docs/tampered.docx"
        )
        self.document.save(update_fields=['output_file'])

        response = self.client.get(reverse('api:document_download', args=[self.document.id]))

        self.assertEqual(response.status_code, 403)
        self.assertIn('cong ty khac', str(response.data.get('detail', '')).lower())

    def test_build_document_preview_blocks_cross_company_storage_prefix(self):
        self.document.output_file = (
            f"companies/{company_storage_slug(self.company_b)}/generated_docs/tampered.docx"
        )
        self.document.save(update_fields=['output_file'])

        with self.assertRaises(PermissionDenied):
            build_document_preview_pdf(self.document)
