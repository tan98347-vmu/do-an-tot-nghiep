from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.models import Company, CompanyStatus, CompanyUserMembership
from prompts.models import Prompt, PromptCategory


class PromptScopeTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(
            code='scope-tests',
            name='Scope Tests Company',
            status=CompanyStatus.ACTIVE,
        )
        self.user = User.objects.create_user(username='scope-user', password='secret')
        CompanyUserMembership.objects.create(
            company=self.company,
            user=self.user,
            local_username='scope-user',
        )
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_prompt_list_filters_by_scope_and_wraps_results(self):
        Prompt.objects.create(
            title='Word AI Prompt',
            owner=self.user,
            usage_scope=['word_ai_edit'],
        )
        Prompt.objects.create(
            title='Summary Prompt',
            owner=self.user,
            usage_scope=['summary'],
        )

        response = self.client.get(reverse('api:prompt_list'), {'scope': ['word_ai_edit']})

        self.assertEqual(response.status_code, 200)
        self.assertIn('results', response.data)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['title'], 'Word AI Prompt')

    def test_prompt_scope_list_exposes_contract(self):
        response = self.client.get(reverse('api:prompt_scope_list'))

        self.assertEqual(response.status_code, 200)
        keys = [item['key'] for item in response.data['results']]
        self.assertIn('template_fill', keys)
        self.assertIn('summary', keys)
        self.assertIn('word_ai_edit', keys)
        self.assertIn('chat', keys)

    def test_backfill_prompt_scope_uses_summary_heuristic(self):
        category = PromptCategory.objects.create(name='Tom tat', description='')
        prompt = Prompt.objects.create(
            title='Prompt cu',
            owner=self.user,
            category=category,
            usage_scope=['template_fill'],
        )

        call_command('backfill_prompt_scope')

        prompt.refresh_from_db()
        self.assertEqual(prompt.usage_scope, ['summary'])

    def test_seed_default_prompts_is_idempotent(self):
        call_command('seed_default_prompts')
        first_count = Prompt.objects.filter(
            owner=self.user,
            source=Prompt.SOURCE_CURATED,
            tags__icontains='seed:r1-default',
        ).count()

        call_command('seed_default_prompts')
        second_count = Prompt.objects.filter(
            owner=self.user,
            source=Prompt.SOURCE_CURATED,
            tags__icontains='seed:r1-default',
        ).count()

        self.assertGreaterEqual(first_count, 8)
        self.assertEqual(first_count, second_count)
