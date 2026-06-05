from django.contrib.auth.models import User
from django.db import connection
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import Company, CompanyStatus, CompanyUserMembership
from document_templates.models import DocumentTemplate
from documents.models import Document


class GlobalSearchApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.company = Company.objects.create(
            code='global-search',
            name='Global Search',
            status=CompanyStatus.ACTIVE,
        )
        self.user = User.objects.create_user(username='search-user', password='secret')
        self.other = User.objects.create_user(username='search-other', password='secret')
        CompanyUserMembership.objects.create(
            company=self.company,
            user=self.user,
            local_username='search-user',
            role='company_user',
            is_active=True,
        )
        CompanyUserMembership.objects.create(
            company=self.company,
            user=self.other,
            local_username='search-other',
            role='company_user',
            is_active=True,
        )
        self.client.force_authenticate(self.user)

    def _insert_prompt(self, *, owner_id, title, rules_content, visibility='private'):
        now = timezone.now()
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO prompts_prompt (
                    title,
                    system_content,
                    rules_content,
                    owner_id,
                    is_shared,
                    visibility,
                    status,
                    approver_note,
                    tags,
                    created_at,
                    updated_at,
                    source,
                    safety_flags,
                    original_raw_text,
                    original_raw_text_hash,
                    usage_count,
                    peer_share_status,
                    peer_share_approver_note
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                [
                    title,
                    '',
                    rules_content,
                    owner_id,
                    False,
                    visibility,
                    'approved',
                    '',
                    '',
                    now,
                    now,
                    'curated',
                    '[]',
                    '',
                    '',
                    0,
                    'none',
                    '',
                ],
            )
            return cursor.fetchone()[0]

    def test_global_search_returns_documents_templates_and_prompts(self):
        document = Document.objects.create(
            company=self.company,
            owner=self.user,
            title='H\u1ee3p \u0111\u1ed3ng th\u1eed vi\u1ec7c 2026',
            notes='Dieu khoan nhan su',
        )
        template = DocumentTemplate.objects.create(
            company=self.company,
            owner=self.user,
            title='M\u1eabu h\u1ee3p \u0111\u1ed3ng th\u1eed vi\u1ec7c',
            content='Noi dung mau hop dong',
        )
        prompt_id = self._insert_prompt(
            owner_id=self.user.id,
            title='Prompt h\u1ee3p \u0111\u1ed3ng th\u1eed vi\u1ec7c',
            rules_content='Nhac kiem tra dieu khoan chinh.',
        )
        Document.objects.create(
            company=self.company,
            owner=self.other,
            title='H\u1ee3p \u0111\u1ed3ng khong duoc thay',
            notes='Rieng tu',
        )

        response = self.client.get(
            reverse('api:global_search'),
            {'q': 'hop dong'},
        )

        self.assertEqual(response.status_code, 200, response.content)
        payload = response.json()
        self.assertIsInstance(payload['took_ms'], int)
        self.assertEqual(payload['results']['document'][0]['id'], document.id)
        self.assertEqual(payload['results']['template'][0]['id'], template.id)
        self.assertEqual(payload['results']['prompt'][0]['id'], prompt_id)
        self.assertEqual(payload['results']['summary'], [])
        self.assertEqual(payload['results']['conversation'], [])

    def test_global_search_types_filter_limits_response_sections(self):
        DocumentTemplate.objects.create(
            company=self.company,
            owner=self.user,
            title='M\u1eabu h\u1ee3p \u0111\u1ed3ng tuyen dung',
            content='Noi dung mau',
        )
        self._insert_prompt(
            owner_id=self.user.id,
            title='Prompt h\u1ee3p \u0111\u1ed3ng tuyen dung',
            rules_content='Soan hop dong tuyen dung',
        )

        response = self.client.get(
            reverse('api:global_search'),
            {'q': 'hop dong', 'types': 'template,prompt'},
        )

        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(set(response.json()['results'].keys()), {'template', 'prompt'})

    def test_global_search_rejects_empty_short_and_invalid_type_queries(self):
        empty_response = self.client.get(reverse('api:global_search'), {'q': ''})
        short_response = self.client.get(reverse('api:global_search'), {'q': 'a'})
        invalid_type_response = self.client.get(
            reverse('api:global_search'),
            {'q': 'hop dong', 'types': 'template,unknown'},
        )

        self.assertEqual(empty_response.status_code, 400)
        self.assertEqual(short_response.status_code, 400)
        self.assertEqual(invalid_type_response.status_code, 400)

    def test_global_search_handles_special_characters_without_crashing(self):
        response = self.client.get(
            reverse('api:global_search'),
            {'q': r"%_'\\"},
        )

        self.assertEqual(response.status_code, 200, response.content)
