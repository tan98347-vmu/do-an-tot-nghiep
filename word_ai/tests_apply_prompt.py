from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from documents.models import Document
from prompts.models import Prompt
from word_ai.models import WordEditJob


class WordAiApplyPromptTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='word-ai-prompt', password='secret')
        self.document = Document.objects.create(
            title='Word AI Prompt Document',
            owner=self.user,
            content='Original content',
        )
        self.prompt = Prompt.objects.create(
            title='Word AI Rewrite Prompt',
            owner=self.user,
            system_content='He thong chinh sua van ban.',
            rules_content='Giu nguyen y chinh va ten rieng.',
            usage_scope=['word_ai_edit'],
        )
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_create_job_applies_prompt_and_returns_summary(self):
        response = self.client.post(
            reverse('api:word_ai_job_list_create'),
            {
                'document_id': self.document.id,
                'prompt_id': self.prompt.id,
                'instruction': 'Lam ro phan mo dau.',
            },
            format='json',
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['applied_prompt']['id'], self.prompt.id)
        self.assertEqual(response.data['applied_prompt']['title'], self.prompt.title)

        job = WordEditJob.objects.get(pk=response.data['id'])
        self.assertEqual(job.applied_prompt_id, self.prompt.id)
        self.assertIn('He thong chinh sua van ban.', job.instruction)
        self.assertIn('Giu nguyen y chinh va ten rieng.', job.instruction)
        self.assertIn('Lam ro phan mo dau.', job.instruction)

    def test_create_job_rejects_prompt_with_wrong_scope(self):
        summary_prompt = Prompt.objects.create(
            title='Summary Prompt',
            owner=self.user,
            usage_scope=['summary'],
        )

        response = self.client.post(
            reverse('api:word_ai_job_list_create'),
            {
                'document_id': self.document.id,
                'prompt_id': summary_prompt.id,
                'instruction': 'Lam ro phan mo dau.',
            },
            format='json',
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn('prompt_id', response.data)
