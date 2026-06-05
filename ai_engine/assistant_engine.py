from __future__ import annotations

import json
import time
from copy import deepcopy
from dataclasses import dataclass

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool

from accounts.permissions import get_accessible_documents
from accounts.tenancy import get_user_company
from accounts.user_resolution import (
    get_company_recipient_by_id,
    resolve_choice_from_candidates,
    resolve_recipient_query,
    search_recipient_candidates,
)
from signing.assistant_quick_sign import (
    AssistantQuickSignError,
    build_quick_sign_plan_payload,
    prepare_quick_sign_plan as service_prepare_quick_sign_plan,
)

from .doc_creator import create_document_from_intent
from .rag_engine import _record_ai_usage, get_llm, rag_query

ASSISTANT_MODEL = 'kimi-k2.6:cloud'
ASSISTANT_ALLOW_CLOUD_MODEL = True
ASSISTANT_MAX_TOOL_STEPS = 5
ASSISTANT_DOCUMENT_RULES = (
    "- Dien day du tat ca variables cua mau da chon\n"
    "- Neu user chua cung cap du du lieu cho mot bien thi de chuoi rong ''\n"
    "- KHONG suy luan, KHONG bia, KHONG tu bu thong tin con thieu\n"
    "- Chon template phu hop nhat voi yeu cau, dua vao title + description + content_preview\n"
    "- Chi tra ve JSON thuan tuy, khong markdown, khong giai thich ben ngoai JSON"
)


@dataclass
class AssistantTurnResult:
    content: str
    citations: list
    payload: dict | None = None
    action: dict | None = None
    tool_name: str | None = None
    assistant_state: dict | None = None


def _assistant_debug(message: str) -> None:
    print(f'[assistant_tool_flow] {message}', flush=True)


def _assistant_debug_block(label: str, value, *, max_len: int = 8000) -> None:
    text = str(value or '')
    if len(text) > max_len:
        text = f'{text[:max_len]}...(truncated {len(text) - max_len} chars)'
    print(f'[assistant_tool_flow] {label} BEGIN', flush=True)
    print(text, flush=True)
    print(f'[assistant_tool_flow] {label} END | chars={len(str(value or ""))}', flush=True)


def _assistant_json(value) -> str:
    try:
        return json.dumps(value, ensure_ascii=False, indent=2, default=str)
    except Exception:
        return str(value)


def _empty_state(state) -> dict:
    if not isinstance(state, dict):
        state = {}
    cloned = deepcopy(state)
    cloned.setdefault('schema_version', 1)
    return cloned


def _user_company(session, user):
    return getattr(session, 'company', None) or get_user_company(user)


def _document_snapshot(document) -> dict:
    return {
        'id': getattr(document, 'pk', None),
        'title': getattr(document, 'title', '') or '',
        'route': f'/documents/{document.pk}' if getattr(document, 'pk', None) else '',
    }


def _state_summary(state: dict) -> dict:
    return {
        'schema_version': state.get('schema_version', 1),
        'current_document': state.get('current_document'),
        'pending_recipient_resolution': state.get('pending_recipient_resolution'),
        'resolved_recipient': state.get('resolved_recipient'),
        'quick_sign_plan': state.get('quick_sign_plan'),
    }


def _assistant_system_prompt(*, mode: str, state: dict) -> str:
    mode_hint = (
        'Voice mode is active. Keep clarification short, explicit, and speech-friendly.'
        if mode == 'voice'
        else 'Text mode is active. Keep answers concise unless the tool result requires detail.'
    )
    return (
        'You are the AI assistant for an internal document platform. '
        'Flutter Web is the only UI. Django owns workflow, auth, persistence, signing, and recipient resolution. '
        'Never claim that a document was signed or forwarded unless a backend tool explicitly says so. '
        'You may use these tools: generate_document_with_ai, ask_template_with_ai, ask_document_with_ai, '
        'find_recipient_candidates, resolve_recipient, prepare_quick_sign_plan. '
        'If the user asks to create, draft, fill, or generate a document, call generate_document_with_ai. '
        'If the user asks about a template or form, call ask_template_with_ai. '
        'If the user asks about an existing document record, call ask_document_with_ai. '
        'If the user asks to sign, send, forward, or "gui cho" someone, resolve the recipient first. '
        'If recipient resolution is ambiguous, stop and ask for clarification. '
        'If a current_document exists in state and the user says "van ban nay", "tai lieu nay", or a follow-up send/sign command, reuse that current_document. '
        'If pending_recipient_resolution exists in state, treat the current user reply as a clarification and call resolve_recipient. '
        'When a document and recipient are both known, call prepare_quick_sign_plan. '
        'Do not call any execution tool to sign or forward in the voice turn. The user must confirm from document detail. '
        'Call only the tools you need. Avoid inventing tool results. '
        f'{mode_hint}\n'
        f'Current assistant state summary:\n{_assistant_json(_state_summary(state))}'
    )


def _sync_system_prompt(messages: list, *, mode: str, state: dict) -> None:
    messages[0] = SystemMessage(content=_assistant_system_prompt(mode=mode, state=state))


def _history_to_messages(history):
    messages = []
    for turn in (history or [])[-8:]:
        role = str(turn.get('role') or '').strip().lower()
        content = str(turn.get('content') or '').strip()
        if not content:
            continue
        if role == 'user':
            messages.append(HumanMessage(content=content))
        else:
            messages.append(AIMessage(content=content))
    return messages


def _coerce_text_content(value) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        parts = []
        for item in value:
            if isinstance(item, dict):
                text = item.get('text')
                if text:
                    parts.append(str(text))
            elif item:
                parts.append(str(item))
        return '\n'.join(parts).strip()
    if value is None:
        return ''
    return str(value)


def _assistant_action(
    *,
    status: str,
    document=None,
    route: str = '',
    plan_token: str = '',
    recipient_resolution: dict | None = None,
    blocking_reason: str = '',
    speak_text: str = '',
    ui_hint: dict | None = None,
) -> dict:
    document_id = None
    if isinstance(document, dict):
        document_id = document.get('id')
        route = route or str(document.get('route') or '')
    elif document is not None:
        document_id = getattr(document, 'pk', None)
        route = route or (f'/documents/{document.pk}' if getattr(document, 'pk', None) else '')
    return {
        'type': 'assistant_action',
        'status': status,
        'route': route,
        'document_id': document_id,
        'plan_token': plan_token,
        'recipient_resolution': recipient_resolution,
        'blocking_reason': blocking_reason,
        'speak_text': speak_text,
        'ui_hint': ui_hint or {},
    }


def _clarification_payload(result: dict) -> dict:
    candidates = result.get('candidates') or []
    return {
        'kind': 'recipient_resolution',
        'status': 'clarification_required',
        'message': result.get('message') or '',
        'clarification_prompt': result.get('clarification_prompt') or '',
        'recipient_resolution': {
            'status': result.get('status') or 'ambiguous',
            'recipient': result.get('recipient'),
            'candidates': candidates,
        },
    }


def _result_with_state(
    *,
    content: str,
    citations: list | None,
    state: dict,
    payload: dict | None = None,
    action: dict | None = None,
    tool_name: str | None = None,
) -> AssistantTurnResult:
    return AssistantTurnResult(
        content=content,
        citations=citations or [],
        payload=payload,
        action=action,
        tool_name=tool_name,
        assistant_state=state,
    )


def _document_created_result(content: str, state: dict) -> AssistantTurnResult:
    document = state.get('current_document') or {}
    route = str(document.get('route') or '')
    payload = {
        'kind': 'document_result',
        'status': 'document_created',
        'document_id': document.get('id'),
        'title': document.get('title', ''),
        'route': route,
    }
    action = _assistant_action(
        status='document_created',
        document=document,
        route=route,
        speak_text='Toi da tao van ban. Ban co the mo de xem chi tiet.',
        ui_hint={'state': 'document_created'},
    )
    return _result_with_state(
        content=content or 'Toi da tao van ban cho ban.',
        citations=[],
        state=state,
        payload=payload,
        action=action,
        tool_name='generate_document_with_ai',
    )


def run_assistant_turn(
    question,
    user,
    *,
    mode='text',
    history=None,
    state=None,
    session=None,
    streaming_callback=None,
    use_profile: bool = True,
    use_company: bool = True,
    attachment_context: str = '',
):
    started_at = time.perf_counter()
    question = (question or '').strip()
    runtime_state = _empty_state(state)
    runtime = {
        'created_document_this_turn': False,
        'stop': None,
    }
    _assistant_debug(
        f'run_assistant_turn start | mode={mode} | user_id={getattr(user, "id", None)} '
        f'| history_turns={len(history or [])} | question_len={len(question)}'
    )
    _assistant_debug_block('assistant_state_in', _assistant_json(_state_summary(runtime_state)), max_len=6000)
    _assistant_debug_block('question', question, max_len=3000)
    if not question:
        return _result_with_state(
            content='Vui long nhap noi dung can xu ly.',
            citations=[],
            state=runtime_state,
        )

    @tool('generate_document_with_ai')
    def generate_document_with_ai(request_text: str) -> str:
        """Create a document from the user's intent and store it in assistant state."""
        answer, document, _, _ = create_document_from_intent(
            request_text,
            user,
            model_override=ASSISTANT_MODEL,
            temperature_override=0.0,
            user_extra_rules=ASSISTANT_DOCUMENT_RULES,
            allow_cloud_model=ASSISTANT_ALLOW_CLOUD_MODEL,
            use_profile=use_profile,
            use_company=use_company,
            extra_context=attachment_context or '',
        )
        runtime_state['current_document'] = _document_snapshot(document)
        runtime_state.pop('pending_recipient_resolution', None)
        runtime_state.pop('resolved_recipient', None)
        runtime_state.pop('quick_sign_plan', None)
        runtime['created_document_this_turn'] = True
        return answer

    @tool('ask_template_with_ai')
    def ask_template_with_ai(request_text: str) -> str:
        """Answer a template question through RAG and stop the turn with citations."""
        answer, citations = rag_query(
            request_text,
            user,
            mode='template',
            history=history,
            model_override=ASSISTANT_MODEL,
            temperature_override=0.0,
            allow_cloud_model=ASSISTANT_ALLOW_CLOUD_MODEL,
        )
        payload = {
            'kind': 'rag_result',
            'tool_name': 'ask_template_with_ai',
            'source_mode': 'template',
            'citations_present': bool(citations),
        }
        action = {
            'type': 'open_rag_result',
            'source_mode': 'template',
        }
        runtime['stop'] = _result_with_state(
            content=answer,
            citations=citations or [],
            state=runtime_state,
            payload=payload,
            action=action,
            tool_name='ask_template_with_ai',
        )
        return answer

    @tool('ask_document_with_ai')
    def ask_document_with_ai(request_text: str) -> str:
        """Answer a document question through RAG and stop the turn with citations."""
        answer, citations = rag_query(
            request_text,
            user,
            mode='document',
            history=history,
            model_override=ASSISTANT_MODEL,
            temperature_override=0.0,
            allow_cloud_model=ASSISTANT_ALLOW_CLOUD_MODEL,
        )
        payload = {
            'kind': 'rag_result',
            'tool_name': 'ask_document_with_ai',
            'source_mode': 'document',
            'citations_present': bool(citations),
        }
        action = {
            'type': 'open_rag_result',
            'source_mode': 'document',
        }
        runtime['stop'] = _result_with_state(
            content=answer,
            citations=citations or [],
            state=runtime_state,
            payload=payload,
            action=action,
            tool_name='ask_document_with_ai',
        )
        return answer

    @tool('find_recipient_candidates')
    def find_recipient_candidates(
        query: str,
        limit: int = 5,
        department_hint: str = '',
        title_hint: str = '',
    ) -> str:
        """Search recipient candidates by name, username, employee code, or alias."""
        candidates = search_recipient_candidates(
            query,
            company=_user_company(session, user),
            actor=user,
            limit=max(1, min(int(limit or 5), 10)),
            department_hint=department_hint,
            title_hint=title_hint,
        )
        return _assistant_json(candidates)

    @tool('resolve_recipient')
    def resolve_recipient(
        query: str = '',
        choice_text: str = '',
        limit: int = 5,
        department_hint: str = '',
        title_hint: str = '',
    ) -> str:
        """Resolve one recipient or request clarification when multiple candidates match."""
        pending = runtime_state.get('pending_recipient_resolution') or {}
        resolution_text = str(choice_text or query or '').strip()
        if pending.get('candidates') and resolution_text:
            result = resolve_choice_from_candidates(
                resolution_text,
                pending.get('candidates') or [],
            )
        else:
            result = resolve_recipient_query(
                resolution_text,
                company=_user_company(session, user),
                actor=user,
                limit=max(1, min(int(limit or 5), 10)),
                department_hint=department_hint,
                title_hint=title_hint,
            )
        if result['status'] == 'resolved':
            runtime_state['resolved_recipient'] = result['recipient']
            runtime_state.pop('pending_recipient_resolution', None)
            return _assistant_json(result)

        runtime_state.pop('resolved_recipient', None)
        runtime_state['pending_recipient_resolution'] = {
            'query': resolution_text,
            'status': result['status'],
            'candidates': result.get('candidates') or [],
            'message': result.get('message') or '',
            'clarification_prompt': result.get('clarification_prompt') or '',
        }
        payload = _clarification_payload(result)
        status_code = (
            'clarification_required'
            if result['status'] == 'ambiguous'
            else 'operation_failed'
        )
        runtime['stop'] = _result_with_state(
            content=result.get('clarification_prompt') or result.get('message') or 'Can lam ro nguoi nhan.',
            citations=[],
            state=runtime_state,
            payload=payload,
            action=_assistant_action(
                status=status_code,
                document=runtime_state.get('current_document'),
                recipient_resolution=payload['recipient_resolution'],
                blocking_reason='' if status_code == 'clarification_required' else payload['message'],
                speak_text=result.get('clarification_prompt') or result.get('message') or '',
                ui_hint={'state': result['status']},
            ),
            tool_name='resolve_recipient',
        )
        return _assistant_json(result)

    @tool('prepare_quick_sign_plan')
    def prepare_quick_sign_plan(
        recipient_user_id: int = 0,
        forward_note: str = '',
    ) -> str:
        """Prepare a backend quick-sign plan for the current document and resolved recipient."""
        current_document = runtime_state.get('current_document') or {}
        document_id = int(current_document.get('id') or 0)
        if not document_id:
            message = 'Toi chua co van ban hien tai de chuan bi quick-sign.'
            runtime['stop'] = _result_with_state(
                content=message,
                citations=[],
                state=runtime_state,
                payload={'kind': 'assistant_quick_sign_plan', 'status': 'operation_failed'},
                action=_assistant_action(
                    status='operation_failed',
                    blocking_reason=message,
                    speak_text=message,
                    ui_hint={'state': 'missing_document'},
                ),
                tool_name='prepare_quick_sign_plan',
            )
            return message

        document = get_accessible_documents(user).filter(pk=document_id).first()
        if document is None:
            message = 'Van ban hien tai khong con kha dung cho quick-sign.'
            runtime['stop'] = _result_with_state(
                content=message,
                citations=[],
                state=runtime_state,
                payload={'kind': 'assistant_quick_sign_plan', 'status': 'operation_failed'},
                action=_assistant_action(
                    status='operation_failed',
                    document=current_document,
                    blocking_reason=message,
                    speak_text=message,
                    ui_hint={'state': 'missing_document'},
                ),
                tool_name='prepare_quick_sign_plan',
            )
            return message

        resolved_recipient = runtime_state.get('resolved_recipient') or {}
        resolved_recipient_id = int(resolved_recipient.get('user_id') or 0)
        recipient_id = int(recipient_user_id or resolved_recipient_id or 0)
        recipient = get_company_recipient_by_id(_user_company(session, user), recipient_id)
        if recipient is None:
            message = 'Toi chua xac dinh duoc nguoi nhan de chuan bi quick-sign.'
            runtime['stop'] = _result_with_state(
                content=message,
                citations=[],
                state=runtime_state,
                payload={'kind': 'assistant_quick_sign_plan', 'status': 'operation_failed'},
                action=_assistant_action(
                    status='operation_failed',
                    document=current_document,
                    blocking_reason=message,
                    speak_text=message,
                    ui_hint={'state': 'missing_recipient'},
                ),
                tool_name='prepare_quick_sign_plan',
            )
            return message

        try:
            plan = service_prepare_quick_sign_plan(
                document,
                user,
                recipient,
                session=session,
                forward_note=forward_note,
            )
        except AssistantQuickSignError as exc:
            runtime['stop'] = _result_with_state(
                content=exc.message,
                citations=[],
                state=runtime_state,
                payload={
                    'kind': 'assistant_quick_sign_plan',
                    'status': 'operation_failed',
                    'blocking_reason': exc.message,
                },
                action=_assistant_action(
                    status='operation_failed',
                    document=current_document,
                    blocking_reason=exc.message,
                    speak_text=exc.message,
                    ui_hint={'state': exc.code},
                ),
                tool_name='prepare_quick_sign_plan',
            )
            return exc.message
        payload = build_quick_sign_plan_payload(plan) or {}
        runtime_state['current_document'] = _document_snapshot(document)
        runtime_state['resolved_recipient'] = payload.get('recipient') or runtime_state.get('resolved_recipient')
        runtime_state['quick_sign_plan'] = {
            'plan_token': payload.get('plan_token'),
            'status': payload.get('status'),
            'document_id': payload.get('document_id'),
            'route': payload.get('route'),
        }
        action_status = (
            'quick_sign_plan_ready'
            if plan.status in {
                plan.Status.READY,
                plan.Status.PARTIAL,
            }
            else 'operation_failed'
        )
        runtime['stop'] = _result_with_state(
            content=payload.get('message') or 'Toi da chuan bi quick-sign plan.',
            citations=[],
            state=runtime_state,
            payload=payload,
            action=_assistant_action(
                status=action_status,
                document=current_document,
                route=payload.get('route', ''),
                plan_token=payload.get('plan_token', ''),
                recipient_resolution=payload.get('recipient_resolution'),
                blocking_reason=payload.get('blocking_reason', ''),
                speak_text=payload.get('message', ''),
                ui_hint=payload.get('ui_hint') or {},
            ),
            tool_name='prepare_quick_sign_plan',
        )
        return payload.get('message') or 'Quick-sign plan da san sang.'

    tools = [
        generate_document_with_ai,
        ask_template_with_ai,
        ask_document_with_ai,
        find_recipient_candidates,
        resolve_recipient,
        prepare_quick_sign_plan,
    ]
    tool_map = {item.name: item for item in tools}
    try:
        from accounts.tenancy import resolve_chat_ai_model
        effective_model = resolve_chat_ai_model(user=user) or ASSISTANT_MODEL
    except Exception:
        effective_model = ASSISTANT_MODEL
    llm = get_llm(
        user,
        model_override=effective_model,
        temperature_override=0.0,
        allow_cloud_model=ASSISTANT_ALLOW_CLOUD_MODEL,
        streaming_callback=streaming_callback,
    )
    runnable = llm.bind_tools(tools, tool_choice='auto')
    messages = [
        SystemMessage(content=_assistant_system_prompt(mode=mode, state=runtime_state)),
        *_history_to_messages(history),
        HumanMessage(content=question),
    ]

    for step in range(ASSISTANT_MAX_TOOL_STEPS):
        _sync_system_prompt(messages, mode=mode, state=runtime_state)
        try:
            response = runnable.invoke(messages)
            _record_ai_usage(user, effective_model, status='success')
        except Exception:
            _record_ai_usage(user, effective_model, status='error')
            _assistant_debug(
                f'llm_invoke error | step={step} | elapsed_ms={(time.perf_counter() - started_at) * 1000:.0f}'
            )
            raise

        plain_content = _coerce_text_content(getattr(response, 'content', ''))
        tool_calls = getattr(response, 'tool_calls', None) or []
        _assistant_debug(
            f'llm_invoke done | step={step} | tool_calls={len(tool_calls)} '
            f'| elapsed_ms={(time.perf_counter() - started_at) * 1000:.0f}'
        )
        _assistant_debug_block('llm_raw_content', plain_content, max_len=8000)
        _assistant_debug_block('llm_tool_calls', _assistant_json(tool_calls), max_len=8000)

        if not tool_calls:
            if runtime['created_document_this_turn'] and not runtime_state.get('quick_sign_plan'):
                return _document_created_result(plain_content, runtime_state)
            return _result_with_state(
                content=plain_content or 'Toi da ghi nhan yeu cau cua ban.',
                citations=[],
                state=runtime_state,
                payload={'kind': 'plain_reply'},
            )

        messages.append(AIMessage(content=plain_content, tool_calls=tool_calls))
        for index, tool_call in enumerate(tool_calls, start=1):
            tool_name = tool_call.get('name')
            tool_args = tool_call.get('args') or {}
            if tool_name not in tool_map:
                return _result_with_state(
                    content='Khong the xu ly yeu cau nay vi tool khong ton tai trong phien hien tai.',
                    citations=[],
                    state=runtime_state,
                )
            _assistant_debug(
                f'tool_selected | step={step} | index={index} | tool={tool_name} | args_keys={list(tool_args.keys())}'
            )
            _assistant_debug_block(
                f'tool_args[{tool_name}]',
                _assistant_json(tool_args),
                max_len=6000,
            )
            tool_result = tool_map[tool_name].invoke(tool_args)
            messages.append(
                ToolMessage(
                    content=_coerce_text_content(tool_result),
                    tool_call_id=tool_call.get('id') or f'{tool_name}_{step}_{index}',
                )
            )
            if runtime['stop'] is not None:
                _assistant_debug_block(
                    'assistant_turn final_payload',
                    _assistant_json(
                        {
                            'content': runtime['stop'].content,
                            'payload': runtime['stop'].payload,
                            'action': runtime['stop'].action,
                            'assistant_state': _state_summary(runtime_state),
                        }
                    ),
                    max_len=10000,
                )
                return runtime['stop']

    if runtime['created_document_this_turn'] and not runtime_state.get('quick_sign_plan'):
        return _document_created_result('', runtime_state)
    return _result_with_state(
        content='Toi can them mot luot de hoan thanh yeu cau nay. Ban hay noi ro hon mot chut.',
        citations=[],
        state=runtime_state,
        payload={'kind': 'plain_reply'},
    )
