from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.models import Company, CompanyStatus, CompanyUserMembership
from accounts.storage_paths import company_storage_slug
from ai_engine.assistant_engine import AssistantTurnResult
from ai_engine.models import ChatAudioAttachment, ChatSession


class AssistantAudioRuntimeGuardTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.company_a = Company.objects.create(code='audio-a', name='Audio A', status=CompanyStatus.ACTIVE)
        self.company_b = Company.objects.create(code='audio-b', name='Audio B', status=CompanyStatus.ACTIVE)
        self.user = User.objects.create_user(username='audio-owner', password='secret')
        CompanyUserMembership.objects.create(
            company=self.company_a,
            user=self.user,
            local_username='audio-owner',
            role='company_user',
            is_active=True,
        )
        self.client.force_authenticate(self.user)

    def test_audio_download_blocks_cross_company_storage_prefix(self):
        session = ChatSession.objects.create(
            user=self.user,
            company=self.company_a,
            title='Voice Session',
            session_type=ChatSession.SESSION_VOICE,
        )
        item = ChatAudioAttachment.objects.create(
            session=session,
            created_by=self.user,
            title='Voice Clip',
            mime_type='audio/webm',
            audio_file=f"companies/{company_storage_slug(self.company_b)}/chat_audio/clip.webm",
        )

        response = self.client.get(reverse('api:assistant_audio_download', args=[item.id]))

        self.assertEqual(response.status_code, 403)
        self.assertIn('cong ty khac', str(response.data.get('detail', '')).lower())

    def test_assistant_turn_persists_assistant_state(self):
        from unittest.mock import patch

        with patch(
            'api.views.assistant.run_assistant_turn',
            return_value=AssistantTurnResult(
                content='Da ghi nho.',
                citations=[],
                payload={'kind': 'plain_reply'},
                action={'type': 'assistant_action', 'status': 'assistant_message'},
                assistant_state={
                    'schema_version': 1,
                    'current_document': {'id': 321, 'route': '/documents/321'},
                },
            ),
        ):
            response = self.client.post(
                reverse('api:assistant_turn'),
                data={'input': 'ghi nho van ban nay', 'mode': 'voice'},
            )

        self.assertEqual(response.status_code, 200, response.content)
        session = ChatSession.objects.get(pk=response.json()['session']['id'])
        self.assertEqual(session.assistant_state['current_document']['id'], 321)
