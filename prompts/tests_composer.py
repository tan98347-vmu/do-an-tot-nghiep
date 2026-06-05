from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from prompts.models import Prompt
from prompts.services.composer import compose_prompt


class ComposePromptTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='composer-user',
            email='composer@example.com',
            password='test-pass-123',
        )
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_compose_prompt_is_deterministic_and_orders_sections(self):
        base_prompt = SimpleNamespace(
            system_content='Bạn là trợ lý pháp lý nội bộ.',
            rules_content='Không tự suy diễn dữ liệu còn thiếu.',
        )
        payload = {
            'base_prompt_id': 15,
            'scope': 'summary',
            'options': {'language': 'vi', 'depth': 'brief'},
            'extra_user_text': '  Giữ nguyên số liệu quan trọng.  ',
            'user': self.user,
        }
        with patch('prompts.services.composer._load_base_prompt', return_value=base_prompt):
            first = compose_prompt(**payload)
            second = compose_prompt(**payload)

        self.assertEqual(first, second)
        self.assertEqual(
            [section['label'] for section in first['sections']],
            ['Hệ tư tưởng', 'Quy tắc', 'Tùy chọn — depth', 'Tùy chọn — language', 'Yêu cầu thêm'],
        )

    def test_compose_prompt_handles_empty_options_and_extra(self):
        result = compose_prompt(
            base_prompt_id=None,
            scope='chat',
            options={},
            extra_user_text='',
            user=self.user,
        )
        self.assertEqual(result['composed_text'], '')
        self.assertEqual(result['sections'], [])
        self.assertEqual(result['token_estimate'], 0)

    def test_compose_prompt_ignores_unknown_option_keys(self):
        result = compose_prompt(
            base_prompt_id=None,
            scope='summary',
            options={'unknown': 'value', 'language': 'vi'},
            extra_user_text='',
            user=self.user,
        )
        self.assertEqual(len(result['sections']), 1)
        self.assertEqual(result['sections'][0]['label'], 'Tùy chọn — language')

    def test_compose_prompt_ignores_invalid_option_values(self):
        result = compose_prompt(
            base_prompt_id=None,
            scope='word_ai_edit',
            options={'mode': 'not-valid'},
            extra_user_text='',
            user=self.user,
        )
        self.assertEqual(result['sections'], [])
        self.assertEqual(result['composed_text'], '')

    def test_compose_prompt_strips_extra_user_text(self):
        result = compose_prompt(
            base_prompt_id=None,
            scope='chat',
            options={},
            extra_user_text='   Chỉ trả lời bằng tiếng Việt.   ',
            user=self.user,
        )
        self.assertEqual(result['sections'], [{'label': 'Yêu cầu thêm', 'content': 'Chỉ trả lời bằng tiếng Việt.'}])

    def test_token_estimate_is_non_negative_integer(self):
        with patch(
            'prompts.services.composer._load_base_prompt',
            return_value=SimpleNamespace(system_content='A', rules_content='B'),
        ):
            result = compose_prompt(
                base_prompt_id=7,
                scope='template_fill',
                options={'tone': 'formal'},
                extra_user_text='Thêm phần mở đầu.',
                user=self.user,
            )
        self.assertIsInstance(result['token_estimate'], int)
        self.assertGreaterEqual(result['token_estimate'], 0)

    def test_preview_endpoint_requires_authentication(self):
        client = APIClient()
        response = client.post(
            '/api/prompts/compose-preview/',
            {'scope': 'summary', 'options': {}, 'extra_user_text': ''},
            format='json',
        )
        self.assertIn(response.status_code, {401, 403})

    def test_preview_endpoint_rejects_missing_base_prompt(self):
        with patch(
            'api.views.prompt_composer.compose_prompt',
            side_effect=Prompt.DoesNotExist(),
        ):
            response = self.client.post(
                '/api/prompts/compose-preview/',
                {
                    'base_prompt_id': 999999,
                    'scope': 'summary',
                    'options': {},
                    'extra_user_text': '',
                },
                format='json',
            )
        self.assertEqual(response.status_code, 400)

    def test_preview_endpoint_rejects_invalid_scope(self):
        response = self.client.post(
            '/api/prompts/compose-preview/',
            {'scope': 'invalid_scope', 'options': {}, 'extra_user_text': ''},
            format='json',
        )
        self.assertEqual(response.status_code, 400)

    def test_preview_endpoint_supports_expected_scopes(self):
        for scope in ('template_fill', 'summary', 'word_ai_edit', 'chat'):
            response = self.client.post(
                '/api/prompts/compose-preview/',
                {'scope': scope, 'options': {}, 'extra_user_text': ''},
                format='json',
            )
            self.assertEqual(response.status_code, 200, scope)
            self.assertIn('composed_text', response.data)
