from django.contrib.auth.models import User
from django.test import TestCase

from accounts.models import Company, CompanyStatus, CompanyUserMembership
from documents.models import Document
from documents.search_helpers import search_documents


class DocumentSearchHelpersTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(
            code='docs-search',
            name='Docs Search',
            status=CompanyStatus.ACTIVE,
        )
        self.user = User.objects.create_user(username='doc-user', password='secret')
        self.other = User.objects.create_user(username='doc-other', password='secret')
        CompanyUserMembership.objects.create(
            company=self.company,
            user=self.user,
            local_username='doc-user',
            role='company_user',
            is_active=True,
        )
        CompanyUserMembership.objects.create(
            company=self.company,
            user=self.other,
            local_username='doc-other',
            role='company_user',
            is_active=True,
        )

    def test_search_documents_matches_unaccent_and_hides_private_docs(self):
        own_document = Document.objects.create(
            company=self.company,
            owner=self.user,
            title='Hợp đồng lao động',
            notes='Bản hợp đồng nội bộ',
        )
        Document.objects.create(
            company=self.company,
            owner=self.other,
            title='Hợp đồng bí mật',
            notes='Không chia sẻ',
        )

        results = search_documents(self.user, 'hop dong')

        self.assertEqual([item['id'] for item in results], [own_document.id])
        self.assertEqual(results[0]['deeplink'], f'/documents/{own_document.id}')

    def test_search_documents_returns_empty_for_short_queries(self):
        self.assertEqual(search_documents(self.user, 'a'), [])

    def test_search_documents_matches_record_code(self):
        document = Document.objects.create(
            company=self.company,
            owner=self.user,
            title='Van ban trung ten',
        )

        results = search_documents(self.user, document.record_code)

        self.assertEqual([item['id'] for item in results], [document.id])
        self.assertEqual(results[0]['record_code'], document.record_code)
