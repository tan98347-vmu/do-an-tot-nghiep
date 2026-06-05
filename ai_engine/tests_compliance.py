from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.models import Company, CompanyStatus, CompanyUserMembership
from ai_engine.compliance_checker import (
    ComplianceChecker,
    ComplianceLLMError,
)
from ai_engine.models import ComplianceCheckResult
from document_templates.models import DocumentTemplate
from documents.models import Document
from prompts.models import PROMPT_STATUS_APPROVED, Prompt


class _FakeLlm:
    def __init__(self, responses):
        self._responses = list(responses)
        self.calls = 0

    def invoke(self, _messages):
        index = min(self.calls, len(self._responses) - 1)
        self.calls += 1
        return SimpleNamespace(content=self._responses[index])


class ComplianceCheckerTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(
            code='compliance-checker',
            name='Compliance Checker',
            status=CompanyStatus.ACTIVE,
        )
        self.user = User.objects.create_user(
            username='compliance-user',
            password='secret',
        )
        CompanyUserMembership.objects.create(
            company=self.company,
            user=self.user,
            local_username='compliance-user',
            role='company_user',
            is_active=True,
        )
        self.prompt = Prompt.objects.create(
            owner=self.user,
            title='Compliance Prompt',
            system_content='Kiem tra dung schema',
            rules_content='Bat buoc cac muc tuan thu.',
            tags='scope:compliance_check',
            visibility=Prompt.VISIBILITY_PRIVATE,
            status=PROMPT_STATUS_APPROVED,
        )

    def test_checker_returns_pass_payload(self):
        fake_llm = _FakeLlm(['{"passed": true, "items_missing": []}'])
        with patch('ai_engine.compliance_checker.get_llm', return_value=fake_llm):
            checker = ComplianceChecker(self.prompt, 'Noi dung hop le.', user=self.user)
            result = checker.run()

        self.assertEqual(result, {'passed': True, 'items_missing': []})

    def test_checker_retries_when_first_response_is_invalid_json(self):
        fake_llm = _FakeLlm([
            'not-json',
            '{"passed": false, "items_missing": [{"requirement": "Muc 1", "explanation": "Thieu noi dung"}]}',
        ])
        with patch('ai_engine.compliance_checker.get_llm', return_value=fake_llm):
            checker = ComplianceChecker(self.prompt, 'Noi dung can kiem tra.', user=self.user)
            result = checker.run()

        self.assertFalse(result['passed'])
        self.assertEqual(fake_llm.calls, 2)
        self.assertEqual(result['items_missing'][0]['requirement'], 'Muc 1')

    def test_checker_raises_after_second_invalid_json(self):
        fake_llm = _FakeLlm(['bad', 'still-bad'])
        with patch('ai_engine.compliance_checker.get_llm', return_value=fake_llm):
            checker = ComplianceChecker(self.prompt, 'Noi dung can kiem tra.', user=self.user)
            with self.assertRaises(ComplianceLLMError):
                checker.run()


class ComplianceEndpointTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.company = Company.objects.create(
            code='compliance-endpoint',
            name='Compliance Endpoint',
            status=CompanyStatus.ACTIVE,
        )
        self.other_company = Company.objects.create(
            code='compliance-other',
            name='Compliance Other',
            status=CompanyStatus.ACTIVE,
        )
        self.user = User.objects.create_user(username='endpoint-user', password='secret')
        self.other_user = User.objects.create_user(username='endpoint-other', password='secret')
        CompanyUserMembership.objects.create(
            company=self.company,
            user=self.user,
            local_username='endpoint-user',
            role='company_user',
            is_active=True,
        )
        CompanyUserMembership.objects.create(
            company=self.other_company,
            user=self.other_user,
            local_username='endpoint-other',
            role='company_user',
            is_active=True,
        )
        self.prompt = Prompt.objects.create(
            owner=self.user,
            title='Compliance Endpoint Prompt',
            system_content='Kiem tra dung schema',
            rules_content='Chi ro muc thieu.',
            tags='scope:compliance_check',
            visibility=Prompt.VISIBILITY_PRIVATE,
            status=PROMPT_STATUS_APPROVED,
        )
        self.document = Document.objects.create(
            company=self.company,
            owner=self.user,
            title='Quy che noi bo',
            content='Noi dung day du.',
        )
        self.template = DocumentTemplate.objects.create(
            company=self.company,
            owner=self.user,
            title='Mau thong bao',
            content='Noi dung mau.',
        )
        self.other_document = Document.objects.create(
            company=self.other_company,
            owner=self.other_user,
            title='Van ban khac cong ty',
            content='Noi dung khac.',
        )
        self.client.force_authenticate(self.user)

    def test_run_endpoint_returns_exact_pass_message(self):
        fake_llm = _FakeLlm(['{"passed": true, "items_missing": []}'])
        with patch('ai_engine.compliance_checker.get_llm', return_value=fake_llm):
            response = self.client.post(
                reverse('api:compliance_check_run'),
                data={
                    'target_type': 'document',
                    'target_id': self.document.pk,
                    'prompt_id': self.prompt.pk,
                },
                format='json',
            )

        self.assertEqual(response.status_code, 200, response.content)
        payload = response.json()
        self.assertTrue(payload['passed'])
        self.assertEqual(
            payload['message'],
            'Văn bản/mẫu văn bản đã đáp ứng được những yêu cầu mà bạn đưa ra',
        )

    def test_run_endpoint_uses_cache_for_same_hash(self):
        fake_llm = _FakeLlm([
            '{"passed": false, "items_missing": [{"requirement": "Muc A", "explanation": "Con thieu"}]}',
        ])
        with patch('ai_engine.compliance_checker.get_llm', return_value=fake_llm):
            first = self.client.post(
                reverse('api:compliance_check_run'),
                data={
                    'target_type': 'template',
                    'target_id': self.template.pk,
                    'prompt_id': self.prompt.pk,
                },
                format='json',
            )
            second = self.client.post(
                reverse('api:compliance_check_run'),
                data={
                    'target_type': 'template',
                    'target_id': self.template.pk,
                    'prompt_id': self.prompt.pk,
                },
                format='json',
            )

        self.assertEqual(first.status_code, 200, first.content)
        self.assertEqual(second.status_code, 200, second.content)
        self.assertEqual(fake_llm.calls, 1)
        self.assertEqual(ComplianceCheckResult.objects.count(), 1)

    def test_run_endpoint_returns_404_for_cross_company_target(self):
        response = self.client.post(
            reverse('api:compliance_check_run'),
            data={
                'target_type': 'document',
                'target_id': self.other_document.pk,
                'prompt_id': self.prompt.pk,
            },
            format='json',
        )

        self.assertEqual(response.status_code, 404, response.content)

    def test_history_returns_latest_results(self):
        fake_llm = _FakeLlm([
            '{"passed": false, "items_missing": [{"requirement": "Muc 1", "explanation": "Thieu 1"}]}',
            '{"passed": false, "items_missing": [{"requirement": "Muc 2", "explanation": "Thieu 2"}]}',
        ])
        with patch('ai_engine.compliance_checker.get_llm', return_value=fake_llm):
            self.client.post(
                reverse('api:compliance_check_run'),
                data={
                    'target_type': 'document',
                    'target_id': self.document.pk,
                    'prompt_id': self.prompt.pk,
                },
                format='json',
            )
            self.document.content = 'Noi dung moi de thay doi hash.'
            self.document.save(update_fields=['content'])
            self.client.post(
                reverse('api:compliance_check_run'),
                data={
                    'target_type': 'document',
                    'target_id': self.document.pk,
                    'prompt_id': self.prompt.pk,
                },
                format='json',
            )

        history_response = self.client.get(
            reverse('api:compliance_check_history'),
            {
                'target_type': 'document',
                'target_id': self.document.pk,
            },
        )

        self.assertEqual(history_response.status_code, 200, history_response.content)
        self.assertEqual(len(history_response.json()['results']), 2)
