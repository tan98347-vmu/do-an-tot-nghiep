from django.contrib.auth.models import User
from django.db import connection
from django.test import TestCase
from django.utils import timezone

from accounts.models import Company, CompanyStatus, CompanyUserMembership
from prompts.search_helpers import search_prompts


class PromptSearchHelpersTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(
            code='prompt-search',
            name='Prompt Search',
            status=CompanyStatus.ACTIVE,
        )
        self.user = User.objects.create_user(username='prompt-user', password='secret')
        self.other = User.objects.create_user(username='prompt-other', password='secret')
        CompanyUserMembership.objects.create(
            company=self.company,
            user=self.user,
            local_username='prompt-user',
            role='company_user',
            is_active=True,
        )
        CompanyUserMembership.objects.create(
            company=self.company,
            user=self.other,
            local_username='prompt-other',
            role='company_user',
            is_active=True,
        )

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
                    peer_share_approver_note,
                    usage_scope
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s, %s, %s, %s, %s, %s)
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
                    ['template_fill'],
                ],
            )
            return cursor.fetchone()[0]

    def test_search_prompts_matches_unaccent_and_hides_private_prompts(self):
        own_prompt_id = self._insert_prompt(
            owner_id=self.user.id,
            title='Prompt h\u1ee3p \u0111\u1ed3ng lao \u0111\u1ed9ng',
            rules_content='Luon kiem tra dieu khoan thu viec.',
        )
        self._insert_prompt(
            owner_id=self.other.id,
            title='Prompt h\u1ee3p \u0111\u1ed3ng bi m\u1eadt',
            rules_content='Khong chia se',
        )

        results = search_prompts(self.user, 'hop dong')

        self.assertEqual([item['id'] for item in results], [own_prompt_id])
        self.assertEqual(results[0]['deeplink'], f'/prompts/{own_prompt_id}/edit')

    def test_search_prompts_returns_empty_for_short_queries(self):
        self.assertEqual(search_prompts(self.user, 'x'), [])
