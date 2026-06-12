from django.contrib.auth.models import User
from django.test import TestCase

from accounts.models import Company, CompanyStatus, CompanyUserMembership
from document_templates.models import DocumentTemplate
from document_templates.search_helpers import search_templates


class TemplateSearchHelpersTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(
            code='tmpl-search',
            name='Template Search',
            status=CompanyStatus.ACTIVE,
        )
        self.user = User.objects.create_user(username='template-user', password='secret')
        self.other = User.objects.create_user(username='template-other', password='secret')
        CompanyUserMembership.objects.create(
            company=self.company,
            user=self.user,
            local_username='template-user',
            role='company_user',
            is_active=True,
        )
        CompanyUserMembership.objects.create(
            company=self.company,
            user=self.other,
            local_username='template-other',
            role='company_user',
            is_active=True,
        )

    def test_search_templates_matches_unaccent_and_hides_private_templates(self):
        own_template = DocumentTemplate.objects.create(
            company=self.company,
            owner=self.user,
            title='Mẫu hợp đồng thử việc',
            content='Nội dung mẫu thử việc',
        )
        DocumentTemplate.objects.create(
            company=self.company,
            owner=self.other,
            title='Mẫu hợp đồng bí mật',
            content='Không chia sẻ',
        )

        results = search_templates(self.user, 'hop dong')

        self.assertEqual([item['id'] for item in results], [own_template.id])
        self.assertEqual(results[0]['deeplink'], f'/templates/{own_template.id}')

    def test_search_templates_returns_empty_for_short_queries(self):
        self.assertEqual(search_templates(self.user, 'q'), [])

    def test_search_templates_matches_record_code(self):
        template = DocumentTemplate.objects.create(
            company=self.company,
            owner=self.user,
            title='Mau trung ten',
            content='Noi dung',
        )

        results = search_templates(self.user, template.record_code)

        self.assertEqual([item['id'] for item in results], [template.id])
        self.assertEqual(results[0]['record_code'], template.record_code)
