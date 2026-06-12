"""Kiem tra dinh dang bien bang LLM (advisory) cho luong sinh van ban tu mau.

Bao phu:
- assess_variable_values_with_llm: parse ket qua, fail-open khi LLM loi.
- endpoint ai/doc/check-variables/: bo qua bien trong, tra issues, khong chan, 404 khi khong co quyen.
- keep_raw_on_invalid: giu gia tri tho khi nguoi dung "Bo qua & tiep tuc".
"""
import json
from types import SimpleNamespace
from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.company_services import create_company_user
from accounts.models import Company, CompanyRole, CompanyStatus
from api.security.prompt_preflight_llm import (
    VariableValueAssessment,
    assess_variable_values_with_llm,
)
from api.views.ai_doc import _normalize_variable_value, _sanitize_variable_payload
from document_templates.models import DocumentTemplate


class _FakeResp:
    def __init__(self, content):
        self.content = content


class _FakeLLM:
    def __init__(self, content):
        self._content = content

    def invoke(self, messages):
        return _FakeResp(self._content)


class AssessVariableValuesTests(TestCase):
    def test_flags_value_not_fitting_variable_kind(self):
        llm_json = json.dumps({'results': [
            {'name': 'gioi_tinh', 'fits': False, 'reason': 'Gia tri khong phai nam/nu.'},
            {'name': 'ho_ten', 'fits': True},
        ]})
        with patch('api.security.prompt_preflight_llm.ChatOllama',
                   return_value=_FakeLLM(llm_json)), \
             patch('api.security.prompt_preflight_llm._validate_isolated_classifier_config'):
            result = assess_variable_values_with_llm(
                [{'name': 'gioi_tinh', 'value': 'abc'}, {'name': 'ho_ten', 'value': 'Nguyen Van A'}],
                template_title='Don xin',
            )
        self.assertTrue(result.available)
        by_name = {r['name']: r for r in result.results}
        self.assertFalse(by_name['gioi_tinh']['fits'])
        self.assertIn('nam/nu', by_name['gioi_tinh']['reason'])
        self.assertTrue(by_name['ho_ten']['fits'])

    def test_skips_empty_values(self):
        result = assess_variable_values_with_llm([{'name': 'x', 'value': '   '}])
        self.assertTrue(result.available)
        self.assertEqual(result.results, [])

    def test_missing_variable_in_llm_response_defaults_to_fits(self):
        # LLM chi nhac toi 1 bien -> bien con lai mac dinh fits=True (lenient).
        llm_json = json.dumps({'results': [{'name': 'gioi_tinh', 'fits': False, 'reason': 'sai'}]})
        with patch('api.security.prompt_preflight_llm.ChatOllama',
                   return_value=_FakeLLM(llm_json)), \
             patch('api.security.prompt_preflight_llm._validate_isolated_classifier_config'):
            result = assess_variable_values_with_llm(
                [{'name': 'gioi_tinh', 'value': 'abc'}, {'name': 'que_quan', 'value': 'Ha Noi'}],
            )
        by_name = {r['name']: r for r in result.results}
        self.assertFalse(by_name['gioi_tinh']['fits'])
        self.assertTrue(by_name['que_quan']['fits'])

    def test_fail_open_when_llm_errors(self):
        with patch('api.security.prompt_preflight_llm.ChatOllama',
                   side_effect=RuntimeError('ollama down')), \
             patch('api.security.prompt_preflight_llm._validate_isolated_classifier_config'):
            result = assess_variable_values_with_llm([{'name': 'gioi_tinh', 'value': 'abc'}])
        self.assertFalse(result.available)
        self.assertEqual(result.results, [])


class SanitizeKeepRawTests(TestCase):
    def _tmpl(self, variables):
        return SimpleNamespace(get_variables=lambda: variables)

    def test_default_blanks_invalid_email(self):
        out = _sanitize_variable_payload(self._tmpl(['email']), {'email': 'not-an-email'})
        self.assertEqual(out['email'], '')

    def test_keep_raw_preserves_user_value(self):
        out = _sanitize_variable_payload(
            self._tmpl(['email']), {'email': 'not-an-email'}, keep_raw_on_invalid=True,
        )
        self.assertEqual(out['email'], 'not-an-email')

    def test_keep_raw_still_normalizes_valid_value(self):
        out = _normalize_variable_value('ngay_sinh', '1990-02-03', keep_raw_on_invalid=True)
        self.assertEqual(out, '03/02/1990')


class CheckVariablesEndpointTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(
            code='var-check-co', name='Var Check Co', status=CompanyStatus.ACTIVE,
        )
        boot = create_company_user(
            company=self.company, local_username='var_user', password='secret123',
            email='v@example.com', role=CompanyRole.COMPANY_USER, full_name='Var User',
        )
        self.user = boot.user
        self.template = DocumentTemplate.objects.create(
            owner=self.user, title='Don co bien',
            content='<p>{{gioi_tinh}}</p><p>{{ho_ten}}</p>',
            source_type=DocumentTemplate.SOURCE_MANUAL,
            status='approved', visibility='private', company=self.company,
        )
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def _post(self, **data):
        return self.client.post(reverse('api:ai_doc_check_variables'), data, format='json')

    def test_returns_issues_and_skips_empty(self):
        assessment = VariableValueAssessment(
            available=True,
            results=[
                {'name': 'gioi_tinh', 'value': 'abc', 'fits': False, 'reason': 'Khong phai nam/nu.'},
            ],
        )
        with patch('api.security.prompt_preflight_llm.assess_variable_values_with_llm',
                   return_value=assessment) as mocked:
            resp = self._post(template_id=self.template.pk,
                              variables={'gioi_tinh': 'abc', 'ho_ten': ''})
        self.assertEqual(resp.status_code, 200, resp.content)
        body = resp.json()
        self.assertTrue(body['available'])
        self.assertEqual(len(body['issues']), 1)
        self.assertEqual(body['issues'][0]['name'], 'gioi_tinh')
        # Chi bien da dien (non-empty) duoc gui di kiem tra
        items = mocked.call_args.args[0]
        self.assertEqual([i['name'] for i in items], ['gioi_tinh'])

    def test_fail_open_available_false(self):
        assessment = VariableValueAssessment(available=False, results=[])
        with patch('api.security.prompt_preflight_llm.assess_variable_values_with_llm',
                   return_value=assessment):
            resp = self._post(template_id=self.template.pk, variables={'gioi_tinh': 'abc'})
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertFalse(resp.json()['available'])
        self.assertEqual(resp.json()['issues'], [])

    def test_404_when_template_not_accessible(self):
        resp = self._post(template_id=999999, variables={'gioi_tinh': 'abc'})
        self.assertEqual(resp.status_code, 404)
