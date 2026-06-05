from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import Company, CompanyStatus, CompanyUserMembership
from prompts.models import Prompt, PromptCategory


class PromptListingTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(
            code='prompt-listing',
            name='Prompt Listing',
            status=CompanyStatus.ACTIVE,
        )
        self.user = User.objects.create_user(username='prompt-user', password='secret')
        CompanyUserMembership.objects.create(
            company=self.company,
            user=self.user,
            local_username='prompt-user',
            is_active=True,
        )
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_prompt_list_filters_by_source_query_and_created_date(self):
        category = PromptCategory.objects.create(name='Phap che', description='')
        older_prompt = Prompt.objects.create(
            title='Prompt cu',
            owner=self.user,
            category=category,
            source=Prompt.SOURCE_CURATED,
            tags='hop-dong',
            usage_scope=['template_fill'],
        )
        newer_prompt = Prompt.objects.create(
            title='Prompt moi',
            owner=self.user,
            category=category,
            source=Prompt.SOURCE_IMPORTED,
            tags='bien-ban',
            usage_scope=['summary'],
        )

        old_day = timezone.now() - timedelta(days=20)
        recent_day = timezone.now() - timedelta(days=2)
        Prompt.objects.filter(pk=older_prompt.pk).update(created_at=old_day, updated_at=old_day)
        Prompt.objects.filter(pk=newer_prompt.pk).update(created_at=recent_day, updated_at=recent_day)

        response = self.client.get(
            reverse('api:prompt_list'),
            {
                'source': Prompt.SOURCE_IMPORTED,
                'q': 'Phap che',
                'created_from': (timezone.now() - timedelta(days=5)).date().isoformat(),
                'scope': ['summary'],
            },
        )

        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['title'], 'Prompt moi')
