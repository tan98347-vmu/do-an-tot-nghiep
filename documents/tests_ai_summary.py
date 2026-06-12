from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.models import Company, CompanyStatus, CompanyUserMembership
from api.security.prompt_preflight_llm import PromptLlmAssessment
from documents.models import Document


class _FakeLlm:
    def __init__(self, content: str):
        self.content = content
        self.messages = None

    def invoke(self, messages):
        self.messages = messages
        return SimpleNamespace(content=self.content)


class DocumentAiSummaryTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.company = Company.objects.create(
            code='summary-a',
            name='Summary A',
            status=CompanyStatus.ACTIVE,
        )
        self.user = User.objects.create_user(username='summary-user', password='secret')
        CompanyUserMembership.objects.create(
            company=self.company,
            user=self.user,
            local_username='summary-user',
            role='company_user',
            is_active=True,
        )
        self.client.force_authenticate(self.user)
        patcher = patch(
            'api.security.prompt_guard.classify_prompt_with_llm',
            return_value=PromptLlmAssessment(
                verdict='pass',
                security='safe',
                quality='meaningful',
                relevance='relevant',
                model_name='test-preflight-model',
            ),
        )
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_document_summarize_returns_summary_for_html_content(self):
        document = Document.objects.create(
            company=self.company,
            owner=self.user,
            title='Thong bao nghi le',
            content='<p>Thong bao nghi le ngay 20/05.</p><p>Toan bo nhan vien nghi lam.</p>',
        )
        fake_llm = _FakeLlm(
            'Tóm tắt nhanh:\nThông báo nghỉ lễ ngày 20/05.\n\nÝ chính:\n- Toàn bộ nhân viên được nghỉ làm.\n\nLưu ý:\n- Theo dõi thông báo nội bộ.'
        )

        with patch('documents.ai_summary.get_llm', return_value=fake_llm):
            response = self.client.post(reverse('api:document_summarize', args=[document.pk]))

        self.assertEqual(response.status_code, 200, response.content)
        payload = response.json()
        self.assertIn('Tóm tắt nhanh', payload['summary'])
        self.assertEqual(payload['source_kind'], 'content')
        self.assertEqual(payload['chunk_count'], 1)
        self.assertIn('Thong bao nghi le ngay 20/05.', fake_llm.messages[-1].content)
        self.assertNotIn('<p>', fake_llm.messages[-1].content)

    def test_document_summarize_returns_conflict_when_document_has_no_text(self):
        document = Document.objects.create(
            company=self.company,
            owner=self.user,
            title='Van ban rong',
            content='',
            notes='',
        )

        response = self.client.post(reverse('api:document_summarize', args=[document.pk]))

        self.assertEqual(response.status_code, 409, response.content)
        self.assertIn('chua co noi dung', response.json()['detail'].lower())

    def test_async_summary_rejects_custom_prompt_without_check_token(self):
        document = Document.objects.create(
            company=self.company,
            owner=self.user,
            title='Bao cao rui ro',
            content='Noi dung bao cao can tom tat.',
        )

        response = self.client.post(
            reverse('api:document_summarize_async', args=[document.pk]),
            {
                'options': {'max_words': 300, 'language': 'vi', 'style': 'formal'},
                'user_extra_rules': 'Nhấn mạnh các rủi ro và thời hạn xử lý.',
            },
            format='json',
        )

        self.assertEqual(response.status_code, 400, response.content)
        self.assertIn('Check prompt', response.json()['detail'])

    def test_async_summary_accepts_matching_check_token_and_wraps_prompt(self):
        document = Document.objects.create(
            company=self.company,
            owner=self.user,
            title='Bao cao rui ro',
            content='Noi dung bao cao can tom tat.',
        )
        prompt_text = 'Nhấn mạnh các rủi ro và thời hạn xử lý.'
        check_response = self.client.post(
            reverse('api:prompt_check'),
            {
                'scope': 'summary',
                'context': 'document_summary',
                'prompt_role': 'extra_instruction',
                'prompt_text': prompt_text,
                'target_id': document.pk,
            },
            format='json',
        )
        self.assertEqual(check_response.status_code, 200, check_response.content)
        fake_task = SimpleNamespace(task_id=uuid4())

        with (
            patch(
                'ai_tasks.services.task_runner.create_task',
                return_value=fake_task,
            ),
            patch('ai_tasks.services.task_runner.run_in_thread') as run_in_thread,
        ):
            response = self.client.post(
                reverse('api:document_summarize_async', args=[document.pk]),
                {
                    'options': {
                        'max_words': 300,
                        'language': 'vi',
                        'style': 'formal',
                    },
                    'user_extra_rules': prompt_text,
                    'prompt_check_token': (
                        check_response.json()['prompt_check_token']
                    ),
                },
                format='json',
            )

        self.assertEqual(response.status_code, 202, response.content)
        safe_block = run_in_thread.call_args.args[-1]
        self.assertIn(prompt_text, safe_block)
        self.assertIn('trust="untrusted"', safe_block)

    def test_async_summary_rejects_token_after_prompt_is_edited(self):
        document = Document.objects.create(
            company=self.company,
            owner=self.user,
            title='Bao cao tien do',
            content='Noi dung bao cao can tom tat.',
        )
        checked_prompt = 'Nhấn mạnh các rủi ro và thời hạn xử lý.'
        check_response = self.client.post(
            reverse('api:prompt_check'),
            {
                'scope': 'summary',
                'context': 'document_summary',
                'prompt_role': 'extra_instruction',
                'prompt_text': checked_prompt,
                'target_id': document.pk,
            },
            format='json',
        )

        response = self.client.post(
            reverse('api:document_summarize_async', args=[document.pk]),
            {
                'options': {'max_words': 300, 'language': 'vi', 'style': 'formal'},
                'user_extra_rules': f'{checked_prompt} Bổ sung nội dung mới.',
                'prompt_check_token': check_response.json()['prompt_check_token'],
            },
            format='json',
        )

        self.assertEqual(response.status_code, 400, response.content)
        self.assertIn('mismatch:prompt_hash', response.json()['detail'])
