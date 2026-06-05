import uuid
from unittest.mock import patch

from django.test import TestCase

from accounts.company_services import create_company_user
from accounts.models import Company, CompanyRole, CompanyStatus, Department, DepartmentMembership
from accounts.user_resolution import build_recipient_candidate_snapshot
from ai_engine.assistant_engine import run_assistant_turn
from ai_engine.models import ChatSession
from documents.models import Document
from signing.models import AssistantQuickSignPlan


class _FakeResponse:
    def __init__(self, *, content='', tool_calls=None):
        self.content = content
        self.tool_calls = tool_calls or []


class _FakeLlm:
    def __init__(self, responses):
        self._responses = list(responses)
        self._index = 0

    def bind_tools(self, _tools, tool_choice='auto'):
        return self

    def invoke(self, _messages):
        response = self._responses[self._index]
        self._index += 1
        return response


class _StateAwareQuickSignLlm:
    def __init__(self, *, document_id, recipient_id, request_text, recipient_query):
        self.document_id = document_id
        self.recipient_id = recipient_id
        self.request_text = request_text
        self.recipient_query = recipient_query
        self._step = 0

    def bind_tools(self, _tools, tool_choice='auto'):
        return self

    def invoke(self, messages):
        self._step += 1
        if self._step == 1:
            return _FakeResponse(
                tool_calls=[
                    {
                        'id': 'state-call-1',
                        'name': 'generate_document_with_ai',
                        'args': {'request_text': self.request_text},
                    }
                ]
            )

        system_prompt = str(messages[0].content)
        if self._step == 2:
            if f'"id": {self.document_id}' not in system_prompt:
                return _FakeResponse(content='Da tao van ban.')
            return _FakeResponse(
                tool_calls=[
                    {
                        'id': 'state-call-2',
                        'name': 'resolve_recipient',
                        'args': {'query': self.recipient_query},
                    }
                ]
            )

        if self._step == 3:
            if f'"user_id": {self.recipient_id}' not in system_prompt:
                return _FakeResponse(content='Da tao van ban.')
            return _FakeResponse(
                tool_calls=[
                    {
                        'id': 'state-call-3',
                        'name': 'prepare_quick_sign_plan',
                        'args': {},
                    }
                ]
            )

        return _FakeResponse(content='Quick-sign da san sang.')


class AssistantEngineTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(
            code='assistant-engine',
            name='Assistant Engine',
            status=CompanyStatus.ACTIVE,
        )
        self.user = create_company_user(
            company=self.company,
            local_username='creator',
            password='secret123',
            email='creator@example.com',
            role=CompanyRole.COMPANY_USER,
            full_name='Creator User',
        ).user
        self.recipient = create_company_user(
            company=self.company,
            local_username='lan.office',
            password='secret123',
            email='lan@example.com',
            role=CompanyRole.COMPANY_USER,
            full_name='Tran Thi Lan',
        ).user
        self.session = ChatSession.objects.create(
            user=self.user,
            company=self.company,
            title='Voice Session',
            session_type=ChatSession.SESSION_VOICE,
        )

    def _quick_sign_plan(self, document, recipient, *, status=AssistantQuickSignPlan.Status.READY):
        plan = AssistantQuickSignPlan(
            document=document,
            created_by=self.user,
            recipient_user=recipient,
            document_version_number=document.version_number,
            status=status,
            can_sign_now=True,
            requires_reauth_password=True,
            credential_required=False,
        )
        plan.token = uuid.uuid4()
        plan.recipient_snapshot = build_recipient_candidate_snapshot(
            recipient,
            match_reason='selected',
            score=100,
        )
        return plan

    @patch('ai_engine.assistant_engine.service_prepare_quick_sign_plan')
    @patch('ai_engine.assistant_engine.create_document_from_intent')
    @patch('ai_engine.assistant_engine.get_llm')
    def test_run_assistant_turn_creates_document_then_prepares_quick_sign_plan(
        self,
        get_llm_mock,
        create_document_mock,
        prepare_plan_mock,
    ):
        document = Document.objects.create(
            title='To trinh nghi phep',
            owner=self.user,
        )
        create_document_mock.return_value = ('Da tao xong', document, None, None)
        prepare_plan_mock.return_value = self._quick_sign_plan(document, self.recipient)
        get_llm_mock.return_value = _FakeLlm(
            [
                _FakeResponse(
                    tool_calls=[
                        {
                            'id': 'call-1',
                            'name': 'generate_document_with_ai',
                            'args': {'request_text': 'Tao to trinh nghi phep'},
                        }
                    ]
                ),
                _FakeResponse(
                    tool_calls=[
                        {
                            'id': 'call-2',
                            'name': 'resolve_recipient',
                            'args': {'query': 'Tran Thi Lan'},
                        }
                    ]
                ),
                _FakeResponse(
                    tool_calls=[
                        {
                            'id': 'call-3',
                            'name': 'prepare_quick_sign_plan',
                            'args': {},
                        }
                    ]
                ),
            ]
        )

        result = run_assistant_turn(
            'Tao to trinh nghi phep, ky va gui cho Tran Thi Lan',
            self.user,
            mode='voice',
            history=[],
            state={},
            session=self.session,
        )

        self.assertEqual(result.action['status'], 'quick_sign_plan_ready')
        self.assertEqual(result.payload['document_id'], document.id)
        self.assertEqual(result.assistant_state['current_document']['id'], document.id)
        self.assertEqual(result.assistant_state['resolved_recipient']['user_id'], self.recipient.id)
        self.assertEqual(
            result.assistant_state['quick_sign_plan']['plan_token'],
            result.payload['plan_token'],
        )

    @patch('ai_engine.assistant_engine.service_prepare_quick_sign_plan')
    @patch('ai_engine.assistant_engine.create_document_from_intent')
    @patch('ai_engine.assistant_engine.get_llm')
    def test_run_assistant_turn_refreshes_state_between_tool_steps_for_quick_sign_flow(
        self,
        get_llm_mock,
        create_document_mock,
        prepare_plan_mock,
    ):
        document = Document.objects.create(
            title='To trinh cong tac',
            owner=self.user,
        )
        create_document_mock.return_value = ('Da tao xong', document, None, None)
        prepare_plan_mock.return_value = self._quick_sign_plan(document, self.recipient)
        get_llm_mock.return_value = _StateAwareQuickSignLlm(
            document_id=document.id,
            recipient_id=self.recipient.id,
            request_text='Tao to trinh cong tac',
            recipient_query='Tran Thi Lan',
        )

        result = run_assistant_turn(
            'Tao to trinh cong tac, ky va gui cho Tran Thi Lan',
            self.user,
            mode='voice',
            history=[],
            state={},
            session=self.session,
        )

        self.assertEqual(result.action['status'], 'quick_sign_plan_ready')
        self.assertEqual(result.payload['document_id'], document.id)
        self.assertEqual(result.assistant_state['current_document']['id'], document.id)
        self.assertEqual(result.assistant_state['resolved_recipient']['user_id'], self.recipient.id)

    @patch('ai_engine.assistant_engine.service_prepare_quick_sign_plan')
    @patch('ai_engine.assistant_engine.get_llm')
    def test_run_assistant_turn_carries_pending_recipient_state_across_turns(
        self,
        get_llm_mock,
        prepare_plan_mock,
    ):
        document = Document.objects.create(
            title='Cong van nhac viec',
            owner=self.user,
        )
        dept_hr = Department.objects.create(company=self.company, name='Nhan su', code='HR')
        dept_ops = Department.objects.create(company=self.company, name='Van thu', code='OPS')
        minh_hr = create_company_user(
            company=self.company,
            local_username='minh.hr',
            password='secret123',
            email='minh.hr@example.com',
            role=CompanyRole.COMPANY_USER,
            full_name='Le Van Minh',
        ).user
        minh_ops = create_company_user(
            company=self.company,
            local_username='minh.ops',
            password='secret123',
            email='minh.ops@example.com',
            role=CompanyRole.COMPANY_USER,
            full_name='Le Van Minh',
        ).user
        DepartmentMembership.objects.create(department=dept_hr, user=minh_hr, is_active=True)
        DepartmentMembership.objects.create(department=dept_ops, user=minh_ops, is_active=True)
        prepare_plan_mock.return_value = self._quick_sign_plan(document, minh_hr)

        get_llm_mock.return_value = _FakeLlm(
            [
                _FakeResponse(
                    tool_calls=[
                        {
                            'id': 'call-a',
                            'name': 'resolve_recipient',
                            'args': {'query': 'Le Van Minh'},
                        }
                    ]
                ),
            ]
        )
        first = run_assistant_turn(
            'Gui van ban nay cho Le Van Minh',
            self.user,
            mode='voice',
            history=[],
            state={
                'schema_version': 1,
                'current_document': {
                    'id': document.id,
                    'title': document.title,
                    'route': f'/documents/{document.id}',
                },
            },
            session=self.session,
        )

        self.assertEqual(first.action['status'], 'clarification_required')
        self.assertEqual(first.assistant_state['pending_recipient_resolution']['status'], 'ambiguous')
        self.assertEqual(len(first.assistant_state['pending_recipient_resolution']['candidates']), 2)

        get_llm_mock.return_value = _FakeLlm(
            [
                _FakeResponse(
                    tool_calls=[
                        {
                            'id': 'call-b',
                            'name': 'resolve_recipient',
                            'args': {'choice_text': 'Nhan su'},
                        }
                    ]
                ),
                _FakeResponse(
                    tool_calls=[
                        {
                            'id': 'call-c',
                            'name': 'prepare_quick_sign_plan',
                            'args': {},
                        }
                    ]
                ),
            ]
        )
        second = run_assistant_turn(
            'Nguoi phong nhan su',
            self.user,
            mode='voice',
            history=[],
            state=first.assistant_state,
            session=self.session,
        )

        self.assertEqual(second.action['status'], 'quick_sign_plan_ready')
        self.assertEqual(second.assistant_state['resolved_recipient']['user_id'], minh_hr.id)
        self.assertEqual(second.payload['recipient']['department'], 'Nhan su')
