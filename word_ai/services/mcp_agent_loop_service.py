import json
import re
import unicodedata
import uuid

from langchain_core.messages import HumanMessage, SystemMessage

from accounts.tenancy import resolve_ai_config
from ai_engine.rag_engine import get_llm
from word_ai.services.config_service import mcp_agent_max_steps
from word_ai.services.event_log_service import append_job_event
from word_ai.services.native_word_tool_catalog import (
    allowed_native_word_tools,
    is_mutation_tool,
    is_verify_tool,
    tool_prompt_specs,
    verify_pair_for_tool,
)


JSON_BLOCK_RE = re.compile(r'```(?:json)?\s*(\{.*?\})\s*```', re.DOTALL)
ALLOWED_TOOLS = set(allowed_native_word_tools())
REPLACEMENT_REQUEST_PATTERNS = (
    re.compile(
        r'(?:thay|doi|replace|change)?\s*["“”\'`](?P<target>.+?)["“”\'`]\s*(?:->|=>|thanh|bang|bằng|to|with)\s*["“”\'`](?P<replacement>.+?)["“”\'`]',
        re.IGNORECASE,
    ),
    re.compile(
        r'(?P<target>[^"\n]{1,120}?)\s*(?:->|=>)\s*(?P<replacement>[^"\n]{1,120})',
        re.IGNORECASE,
    ),
)


def _extract_json_block(text):
    text = str(text or '').strip()
    if not text:
        raise ValueError('Agent loop returned empty content.')
    match = JSON_BLOCK_RE.search(text)
    if match:
        return match.group(1)
    start = text.find('{')
    end = text.rfind('}')
    if start >= 0 and end > start:
        return text[start:end + 1]
    raise ValueError('Agent loop did not return JSON.')


def advance_mcp_agent(*, job, tool_transcript, latest_command, session_snapshot):
    terminal_decision = _terminal_decision_from_latest_command(
        latest_command=latest_command,
        tool_transcript=tool_transcript,
    )
    if terminal_decision is not None:
        append_job_event(
            job,
            step='tool_loop',
            status=terminal_decision.get('action', ''),
            message='Word tool loop selected the next step.',
            payload={
                'latest_tool_name': str((latest_command or {}).get('tool_name') or ''),
                'transcript_count': len(tool_transcript or []),
                'action': terminal_decision.get('action', ''),
                'queued_tool_names': [],
                'warning_codes': list(terminal_decision.get('warnings') or []),
            },
        )
        return terminal_decision

    if len(tool_transcript or []) >= mcp_agent_max_steps():
        return {
            'action': 'fail_session',
            'error_code': 'tool_loop_max_steps_exceeded',
            'error_detail': f'Word tool loop exceeded {mcp_agent_max_steps()} steps for job {job.id}.',
        }

    try:
        decision = _build_llm_agent_decision(
            job=job,
            tool_transcript=tool_transcript,
            latest_command=latest_command,
            session_snapshot=session_snapshot,
        )
    except Exception as exc:
        decision = _build_fallback_agent_decision(
            job=job,
            tool_transcript=tool_transcript,
            latest_command=latest_command,
            session_snapshot=session_snapshot,
            failure=str(exc),
        )
    decision = _guard_agent_decision(
        decision=decision,
        latest_command=latest_command,
        tool_transcript=tool_transcript,
        job=job,
    )

    append_job_event(
        job,
        step='tool_loop',
        status=decision.get('action', ''),
        message='Word tool loop selected the next step.',
        payload={
            'latest_tool_name': str((latest_command or {}).get('tool_name') or ''),
            'transcript_count': len(tool_transcript or []),
            'action': decision.get('action', ''),
            'queued_tool_names': [
                str(item.get('tool_name') or '')
                for item in decision.get('commands', [])
                if isinstance(item, dict)
            ],
            'warning_codes': list(decision.get('warnings') or []),
        },
    )
    return decision


def _build_llm_agent_decision(*, job, tool_transcript, latest_command, session_snapshot):
    config = resolve_ai_config(user=job.requested_by)
    llm = get_llm(
        user=job.requested_by,
        model_override=job.llm_model_name or config.ai_model,
        temperature_override=job.llm_temperature,
        allow_cloud_model=job.allow_cloud_model,
    )
    prompt = {
        'job': {
            'id': job.id,
            'instruction': job.instruction,
            'edit_mode': job.edit_mode,
            'track_changes': job.track_changes,
        },
        'session_snapshot': session_snapshot,
        'latest_command': latest_command,
        'tool_transcript': tool_transcript,
        'constraints': {
            'allowed_tools': sorted(ALLOWED_TOOLS),
            'tool_specs': tool_prompt_specs(),
            'must_verify_after_mutation': True,
            'must_export_last': True,
            'max_steps': mcp_agent_max_steps(),
            'default_behavior': {
                'text_replacement_is_exact': True,
                'preserve_formatting_when_text_only': True,
                'replace_text_defaults': {
                    'occurrence': 'all',
                    'match_case': True,
                    'match_whole_word': True,
                },
            },
        },
        'response_schema': {
            'action': 'queue_commands|fail_session|manual_review',
            'summary': 'short reason',
            'warnings': ['warning_code'],
            'commands': [
                {
                    'tool_name': 'inspect_document',
                    'input': {},
                }
            ],
            'error_code': 'only for fail_session',
            'error_detail': 'only for fail_session',
        },
    }
    system_prompt = (
        'You are the typed tool-loop controller for a live Microsoft Word editing host. '
        'Return JSON only. '
        'Choose the next tool command after seeing the current transcript and the latest tool result. '
        'Never invent raw VBA, raw code, OOXML, or HTML. '
        'After every mutation tool, the next command must be a verify tool before export_document. '
        'When the user asks to change text A to B, treat it as an exact replacement contract: remove A and insert exactly B in the same place. '
        'For replace_text_matches, default to occurrence=all, match_case=true, and match_whole_word=true unless the user explicitly asks for partial or case-insensitive matching. '
        'If the user only asked to change wording, preserve the existing formatting and layout; do not queue format or layout tools unless the user explicitly asked to change formatting or layout.'
    )
    response = llm.invoke(
        [
            SystemMessage(content=system_prompt),
            HumanMessage(content=json.dumps(prompt, ensure_ascii=True)),
        ]
    )
    return _sanitize_agent_decision(
        raw_decision=json.loads(_extract_json_block(getattr(response, 'content', ''))),
        job=job,
        tool_transcript=tool_transcript,
        latest_command=latest_command,
        session_snapshot=session_snapshot,
    )


def _sanitize_agent_decision(*, raw_decision, job, tool_transcript, latest_command, session_snapshot):
    action = str(raw_decision.get('action') or 'manual_review').strip().lower()
    if action not in {'queue_commands', 'fail_session', 'manual_review'}:
        action = 'manual_review'

    commands = []
    if action == 'queue_commands':
        for item in raw_decision.get('commands') or []:
            if not isinstance(item, dict):
                continue
            tool_name = str(item.get('tool_name') or '').strip()
            if tool_name not in ALLOWED_TOOLS:
                continue
            canonical_tool_name, normalized_input = _canonicalize_tool_request(
                tool_name=tool_name,
                command_input=dict(item.get('input') or {}),
                prior_commands=commands,
                latest_command=latest_command,
            )
            commands.append(
                {
                    'id': f'cmd-{uuid.uuid4().hex[:12]}',
                    'tool_name': canonical_tool_name,
                    'input': normalized_input,
                }
            )
        if not commands:
            return _build_fallback_agent_decision(
                job=job,
                tool_transcript=tool_transcript,
                latest_command=latest_command,
                session_snapshot=session_snapshot,
                failure='llm_returned_no_valid_commands',
            )
        if len(commands) > 1:
            commands = [commands[0]]

    decision = {
        'action': action,
        'summary': str(raw_decision.get('summary') or '').strip(),
        'warnings': [str(item) for item in (raw_decision.get('warnings') or []) if str(item).strip()],
        'commands': commands,
        'error_code': str(raw_decision.get('error_code') or '').strip(),
        'error_detail': str(raw_decision.get('error_detail') or '').strip(),
    }
    return decision


def _guard_agent_decision(*, decision, latest_command, tool_transcript, job):
    action = str(decision.get('action') or '').strip().lower()
    if action != 'queue_commands':
        return decision

    latest_tool = str((latest_command or {}).get('tool_name') or '').strip()
    latest_result = dict((latest_command or {}).get('result') or {})
    queued_commands = list(decision.get('commands') or [])

    if is_verify_tool(latest_tool) and not _verify_result_passed(latest_result):
        return {
            'action': 'fail_session',
            'summary': f'{latest_tool} failed.',
            'warnings': [f'{latest_tool}_failed'],
            'commands': [],
            'error_code': f'{latest_tool}_failed',
            'error_detail': json.dumps(latest_result, ensure_ascii=True)[:2000],
        }

    if _transcript_contains_failed_verify(tool_transcript):
        return {
            'action': 'fail_session',
            'summary': 'A required verify step failed before export.',
            'warnings': ['verify_failed_before_export'],
            'commands': [],
            'error_code': 'verify_failed_before_export',
            'error_detail': json.dumps(tool_transcript or [], ensure_ascii=True)[:2000],
        }

    replacement_dead_end = _detect_text_replacement_dead_end(
        decision=decision,
        latest_command=latest_command,
        tool_transcript=tool_transcript,
    )
    if replacement_dead_end is not None:
        return replacement_dead_end

    track_changes_alignment = _enforce_track_changes_alignment(
        queued_commands=queued_commands,
        latest_command=latest_command,
        tool_transcript=tool_transcript,
        desired_enabled=bool(getattr(job, 'track_changes', False)),
    )
    if track_changes_alignment is not None:
        return track_changes_alignment

    if is_mutation_tool(latest_tool) and _decision_queues_export(queued_commands):
        verify_tool_name = verify_pair_for_tool(latest_tool)
        verify_input = _build_follow_up_verify_input(latest_command)
        if verify_tool_name and verify_input is not None:
            return _queue_single(
                tool_name=verify_tool_name,
                command_input=verify_input,
                summary=f'Verify the result of {latest_tool} before export.',
                warnings=['post_mutation_verify_enforced'],
            )

    return decision


def _terminal_decision_from_latest_command(*, latest_command, tool_transcript):
    latest_tool = str((latest_command or {}).get('tool_name') or '').strip()
    latest_result = dict((latest_command or {}).get('result') or {})
    if is_verify_tool(latest_tool) and not _verify_result_passed(latest_result):
        return {
            'action': 'fail_session',
            'summary': f'{latest_tool} failed.',
            'warnings': [f'{latest_tool}_failed'],
            'commands': [],
            'error_code': f'{latest_tool}_failed',
            'error_detail': json.dumps(latest_result, ensure_ascii=True)[:2000],
        }
    if _transcript_contains_failed_verify(tool_transcript):
        return {
            'action': 'fail_session',
            'summary': 'A required verify step failed before export.',
            'warnings': ['verify_failed_before_export'],
            'commands': [],
            'error_code': 'verify_failed_before_export',
            'error_detail': json.dumps(tool_transcript or [], ensure_ascii=True)[:2000],
        }
    return None


def _detect_text_replacement_dead_end(*, decision, latest_command, tool_transcript):
    queued_commands = list(decision.get('commands') or [])
    if not queued_commands:
        return None
    queued_tool_name = str((queued_commands[0] or {}).get('tool_name') or '').strip()
    latest_tool_name = str((latest_command or {}).get('tool_name') or '').strip()
    latest_result = dict((latest_command or {}).get('result') or {})
    warning_codes = {str(item).strip().lower() for item in (decision.get('warnings') or []) if str(item).strip()}

    if queued_tool_name == 'replace_text_matches' and latest_tool_name == 'inspect_text_matches':
        if int(latest_result.get('target_count') or 0) <= 0:
            return {
                'action': 'fail_session',
                'summary': 'The requested text was not found in the document for replacement.',
                'warnings': ['text_replacement_target_not_found'],
                'commands': [],
                'error_code': 'text_replacement_target_not_found',
                'error_detail': json.dumps(latest_result, ensure_ascii=True)[:2000],
            }

    if queued_tool_name in {'inspect_document', 'inspect_text_matches', 'replace_text_matches'}:
        failed_replacements = _failed_replace_text_attempt_count(tool_transcript, latest_command)
        if failed_replacements >= 2 and warning_codes.intersection(
            {
                'encoding_mismatch',
                'text_encoding_mismatch',
                'text_encoding_issue_detected',
                'replacement_attempt_failed',
            }
        ):
            return {
                'action': 'fail_session',
                'summary': 'The document text appears to have an encoding mismatch; repeated replacement attempts found no exact target match.',
                'warnings': ['text_encoding_mismatch_requires_manual_review'],
                'commands': [],
                'error_code': 'text_encoding_mismatch_requires_manual_review',
                'error_detail': json.dumps(
                    {
                        'latest_command': latest_command or {},
                        'warning_codes': sorted(warning_codes),
                        'failed_replace_attempts': failed_replacements,
                    },
                    ensure_ascii=True,
                )[:2000],
            }
    return None


def _failed_replace_text_attempt_count(tool_transcript, latest_command):
    count = 0
    for item in list(tool_transcript or []) + [latest_command or {}]:
        if not isinstance(item, dict):
            continue
        if str(item.get('tool_name') or '').strip() != 'replace_text_matches':
            continue
        result = dict(item.get('result') or {})
        if int(result.get('replaced_count') or 0) <= 0:
            count += 1
    return count


def _enforce_track_changes_alignment(*, queued_commands, latest_command, tool_transcript, desired_enabled):
    if not queued_commands:
        return None
    first_tool_name = str((queued_commands[0] or {}).get('tool_name') or '').strip()
    if not first_tool_name or first_tool_name == 'toggle_track_changes':
        return None
    if not is_mutation_tool(first_tool_name):
        return None
    current_state = _latest_known_track_changes_state(
        latest_command=latest_command,
        tool_transcript=tool_transcript,
    )
    if current_state is None or current_state == bool(desired_enabled):
        return None
    return _queue_single(
        tool_name='toggle_track_changes',
        command_input={'enabled': bool(desired_enabled)},
        summary='Align Track Changes state before editing the document.',
        warnings=['track_changes_state_aligned_before_mutation'],
    )


def _latest_known_track_changes_state(*, latest_command, tool_transcript):
    candidate = _track_changes_state_from_command(latest_command)
    if candidate is not None:
        return candidate
    for item in reversed(tool_transcript or []):
        candidate = _track_changes_state_from_command(item)
        if candidate is not None:
            return candidate
    return None


def _track_changes_state_from_command(command):
    if not isinstance(command, dict):
        return None
    result = dict(command.get('result') or {})
    if 'track_revisions_state' in result:
        return bool(result.get('track_revisions_state'))
    if 'actual_enabled' in result:
        return bool(result.get('actual_enabled'))
    if str(command.get('tool_name') or '').strip() == 'toggle_track_changes':
        command_input = dict(command.get('input') or {})
        if 'enabled' in command_input:
            return bool(command_input.get('enabled'))
    return None


def _canonicalize_tool_request(*, tool_name, command_input, prior_commands, latest_command):
    normalized_tool_name = str(tool_name or '').strip()
    normalized_input = _normalize_command_input(
        tool_name=normalized_tool_name,
        command_input=command_input,
        prior_commands=prior_commands,
        latest_command=latest_command,
    )

    if normalized_tool_name in {'normalize_case_whole_document', 'normalize_case_selection'}:
        scope_name = str(normalized_input.get('scope') or '').strip().lower()
        target_text = _first_non_empty_value(
            normalized_input.get('text_to_normalize'),
            normalized_input.get('target_text'),
        )
        transformed_text = _transformed_case_text(
            source_text=str(target_text or ''),
            case_name=str(normalized_input.get('case') or ''),
        )
        if scope_name == 'specific_text' and target_text and transformed_text:
            return (
                'replace_text_matches',
                _replacement_command_input(
                    target_text=str(target_text),
                    replacement_text=transformed_text,
                ),
            )

    return normalized_tool_name, normalized_input


def _normalize_command_input(*, tool_name, command_input, prior_commands, latest_command):
    normalized_tool_name = str(tool_name or '').strip()
    normalized_input = dict(command_input or {})

    if normalized_tool_name == 'replace_text_matches':
        normalized_input['target_text'] = str(normalized_input.get('target_text') or '').strip()
        normalized_input['replacement_text'] = str(normalized_input.get('replacement_text') or '')
        occurrence = str(normalized_input.get('occurrence') or 'all').strip().lower()
        normalized_input['occurrence'] = 'first' if occurrence == 'first' else 'all'
        normalized_input['match_case'] = _coerce_bool(normalized_input.get('match_case'), default=True)
        normalized_input['match_whole_word'] = _coerce_bool(normalized_input.get('match_whole_word'), default=True)
        normalized_input['preserve_formatting'] = _coerce_bool(
            normalized_input.get('preserve_formatting'),
            default=True,
        )
        return normalized_input

    if normalized_tool_name in {'normalize_case_whole_document', 'normalize_case_selection'}:
        case_name = _first_non_empty_value(
            normalized_input.get('case'),
            normalized_input.get('case_type'),
            normalized_input.get('target_case'),
            normalized_input.get('expected_case'),
        )
        if case_name:
            normalized_input['case'] = str(case_name).strip().lower()
        normalized_input.pop('case_type', None)
        normalized_input.pop('target_case', None)
        normalized_input.pop('expected_case', None)
        return normalized_input

    if normalized_tool_name in {
        'apply_format_whole_document',
        'apply_format_selection',
        'verify_document_format_coverage',
        'verify_selection_format',
    }:
        normalized_input = _normalize_format_like_payload(normalized_input)
        if normalized_tool_name in {'verify_document_format_coverage', 'verify_selection_format'}:
            fallback_input = _infer_expected_from_previous_command(
                verify_tool_name=normalized_tool_name,
                prior_commands=prior_commands,
                latest_command=latest_command,
            )
            if isinstance(fallback_input, dict):
                fallback_input = _normalize_format_like_payload(fallback_input)
                for field_name, field_value in fallback_input.items():
                    normalized_input.setdefault(field_name, field_value)
        return normalized_input

    if normalized_tool_name == 'verify_document_case':
        expected = _first_non_empty_value(
            normalized_input.get('expected'),
            normalized_input.get('case'),
            normalized_input.get('expected_case'),
            _infer_expected_from_previous_command(
                verify_tool_name=normalized_tool_name,
                prior_commands=prior_commands,
                latest_command=latest_command,
            ),
        )
        if expected:
            normalized_input['expected'] = str(expected).strip().lower()
        normalized_input.pop('case', None)
        normalized_input.pop('expected_case', None)
        return normalized_input

    if normalized_tool_name == 'verify_document_format_coverage':
        format_payload = normalized_input.pop('format', None)
        if isinstance(format_payload, dict):
            for field_name in ('bold', 'italic', 'font_color'):
                if field_name not in normalized_input and field_name in format_payload:
                    normalized_input[field_name] = format_payload.get(field_name)
        fallback_input = _infer_expected_from_previous_command(
            verify_tool_name=normalized_tool_name,
            prior_commands=prior_commands,
            latest_command=latest_command,
        )
        if isinstance(fallback_input, dict):
            for field_name in ('bold', 'italic', 'font_color'):
                if field_name not in normalized_input and field_name in fallback_input:
                    normalized_input[field_name] = fallback_input.get(field_name)
        return normalized_input

    if normalized_tool_name == 'verify_selection_case':
        expected = _first_non_empty_value(
            normalized_input.get('expected'),
            normalized_input.get('case'),
            normalized_input.get('expected_case'),
            _infer_expected_from_previous_command(
                verify_tool_name=normalized_tool_name,
                prior_commands=prior_commands,
                latest_command=latest_command,
            ),
        )
        if expected:
            normalized_input['expected'] = str(expected).strip().lower()
        normalized_input.pop('case', None)
        normalized_input.pop('expected_case', None)
        return normalized_input

    if normalized_tool_name == 'verify_text_replacement':
        inferred = _infer_expected_from_previous_command(
            verify_tool_name=normalized_tool_name,
            prior_commands=prior_commands,
            latest_command=latest_command,
        )
        if isinstance(inferred, dict):
            normalized_input.setdefault('target_text', inferred.get('target_text', ''))
            normalized_input.setdefault('replacement_text', inferred.get('replacement_text', ''))
            normalized_input.setdefault('expected_replaced_count', inferred.get('expected_replaced_count', 0))
            normalized_input.setdefault('match_case', inferred.get('match_case', True))
            normalized_input.setdefault('match_whole_word', inferred.get('match_whole_word', True))
        normalized_input['match_case'] = _coerce_bool(normalized_input.get('match_case'), default=True)
        normalized_input['match_whole_word'] = _coerce_bool(normalized_input.get('match_whole_word'), default=True)
        return normalized_input

    if normalized_tool_name == 'verify_selection_text':
        expected_text = _first_non_empty_value(
            normalized_input.get('expected_text'),
            normalized_input.get('replacement_text'),
            _infer_expected_from_previous_command(
                verify_tool_name=normalized_tool_name,
                prior_commands=prior_commands,
                latest_command=latest_command,
            ),
        )
        if expected_text is not None and expected_text != '':
            normalized_input['expected_text'] = str(expected_text)
        normalized_input.pop('replacement_text', None)
        return normalized_input

    if normalized_tool_name == 'verify_track_changes_state':
        if 'expected_enabled' not in normalized_input:
            inferred = _infer_expected_from_previous_command(
                verify_tool_name=normalized_tool_name,
                prior_commands=prior_commands,
                latest_command=latest_command,
            )
            if inferred is not None:
                normalized_input['expected_enabled'] = inferred
        return normalized_input

    if normalized_tool_name in {'verify_header_replacement', 'verify_footer_replacement', 'verify_table_replacement'}:
        if not normalized_input.get('target_text') or not normalized_input.get('replacement_text'):
            inferred = _infer_expected_from_previous_command(
                verify_tool_name=normalized_tool_name,
                prior_commands=prior_commands,
                latest_command=latest_command,
            )
            if isinstance(inferred, dict):
                normalized_input.setdefault('target_text', inferred.get('target_text', ''))
                normalized_input.setdefault('replacement_text', inferred.get('replacement_text', ''))
        return normalized_input

    if normalized_tool_name == 'verify_comment_selection':
        if 'comment_text' not in normalized_input:
            inferred = _infer_expected_from_previous_command(
                verify_tool_name=normalized_tool_name,
                prior_commands=prior_commands,
                latest_command=latest_command,
            )
            if inferred is not None:
                normalized_input['comment_text'] = inferred
        return normalized_input

    return normalized_input


def _normalize_format_like_payload(command_input):
    normalized_input = dict(command_input or {})
    format_payload = normalized_input.pop('format', None)
    if isinstance(format_payload, dict):
        for source_key, target_key in (
            ('bold', 'bold'),
            ('italic', 'italic'),
            ('underline', 'underline'),
            ('underlined', 'underline'),
            ('font_color', 'font_color'),
            ('fontColor', 'font_color'),
            ('color', 'font_color'),
            ('font_name', 'font_name'),
            ('fontName', 'font_name'),
            ('font_size', 'font_size'),
            ('fontSize', 'font_size'),
            ('alignment', 'alignment'),
            ('line_spacing', 'line_spacing'),
            ('lineSpacing', 'line_spacing'),
            ('spacing_before', 'spacing_before'),
            ('spacingBefore', 'spacing_before'),
            ('spacing_after', 'spacing_after'),
            ('spacingAfter', 'spacing_after'),
        ):
            if target_key not in normalized_input and source_key in format_payload:
                normalized_input[target_key] = format_payload.get(source_key)

    for source_key, target_key in (
        ('font_bold', 'bold'),
        ('fontBold', 'bold'),
        ('font_italic', 'italic'),
        ('fontItalic', 'italic'),
        ('fontColor', 'font_color'),
        ('color', 'font_color'),
        ('fontName', 'font_name'),
        ('fontSize', 'font_size'),
        ('lineSpacing', 'line_spacing'),
        ('spacingBefore', 'spacing_before'),
        ('spacingAfter', 'spacing_after'),
    ):
        if source_key in normalized_input and target_key not in normalized_input:
            normalized_input[target_key] = normalized_input.get(source_key)

    normalized_input.pop('fontColor', None)
    normalized_input.pop('color', None)
    normalized_input.pop('font_bold', None)
    normalized_input.pop('fontBold', None)
    normalized_input.pop('font_italic', None)
    normalized_input.pop('fontItalic', None)
    normalized_input.pop('fontName', None)
    normalized_input.pop('fontSize', None)
    normalized_input.pop('lineSpacing', None)
    normalized_input.pop('spacingBefore', None)
    normalized_input.pop('spacingAfter', None)
    normalized_input.pop('underlined', None)
    normalized_input.pop('underline', None)
    return normalized_input


def _infer_expected_from_previous_command(*, verify_tool_name, prior_commands, latest_command):
    candidate_commands = []
    if prior_commands:
        candidate_commands.extend(reversed(prior_commands))
    if latest_command:
        candidate_commands.append(latest_command)

    for candidate in candidate_commands:
        if not isinstance(candidate, dict):
            continue
        candidate_tool_name = str(candidate.get('tool_name') or '').strip()
        candidate_input = dict(candidate.get('input') or {})
        if verify_tool_name == 'verify_document_case' and candidate_tool_name == 'normalize_case_whole_document':
            return candidate_input.get('case')
        if verify_tool_name == 'verify_selection_case' and candidate_tool_name == 'normalize_case_selection':
            return candidate_input.get('case')
        if verify_tool_name == 'verify_document_format_coverage' and candidate_tool_name == 'apply_format_whole_document':
            return {
                'bold': candidate_input.get('bold', ''),
                'italic': candidate_input.get('italic', ''),
                'font_color': candidate_input.get('font_color', ''),
            }
        if verify_tool_name == 'verify_selection_format' and candidate_tool_name in {
            'apply_format_selection',
            'clear_format_selection',
            'set_paragraph_alignment',
            'set_line_spacing',
            'set_paragraph_spacing',
        }:
            return candidate_input
        if verify_tool_name == 'verify_text_replacement' and candidate_tool_name == 'replace_text_matches':
            candidate_result = dict(candidate.get('result') or {})
            return {
                'target_text': candidate_input.get('target_text', ''),
                'replacement_text': candidate_input.get('replacement_text', ''),
                'expected_replaced_count': int(candidate_result.get('replaced_count') or 0),
                'match_case': bool(candidate_input.get('match_case', False)),
                'match_whole_word': bool(candidate_input.get('match_whole_word', False)),
            }
        if verify_tool_name == 'verify_selection_text' and candidate_tool_name == 'replace_selection_text':
            return candidate_input.get('replacement_text')
        if verify_tool_name == 'verify_track_changes_state' and candidate_tool_name == 'toggle_track_changes':
            return candidate_input.get('enabled', False)
        if verify_tool_name == 'verify_header_replacement' and candidate_tool_name == 'replace_in_headers':
            return {
                'target_text': candidate_input.get('target_text', ''),
                'replacement_text': candidate_input.get('replacement_text', ''),
            }
        if verify_tool_name == 'verify_footer_replacement' and candidate_tool_name == 'replace_in_footers':
            return {
                'target_text': candidate_input.get('target_text', ''),
                'replacement_text': candidate_input.get('replacement_text', ''),
            }
        if verify_tool_name == 'verify_table_replacement' and candidate_tool_name == 'replace_in_tables':
            return {
                'target_text': candidate_input.get('target_text', ''),
                'replacement_text': candidate_input.get('replacement_text', ''),
            }
        if verify_tool_name == 'verify_comment_selection' and candidate_tool_name == 'insert_comment_selection':
            return candidate_input.get('comment_text', '')
    return None


def _first_non_empty_value(*values):
    for value in values:
        if value is None:
            continue
        if isinstance(value, str):
            if value.strip():
                return value
            continue
        return value
    return None


def _coerce_bool(value, *, default):
    if value is None:
        return bool(default)
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in {'1', 'true', 'yes', 'y', 'on'}:
        return True
    if text in {'0', 'false', 'no', 'n', 'off'}:
        return False
    return bool(default)


def _requested_text_replacement(job):
    plan = job.plan_payload or {}
    target = str(plan.get('target_anchor') or '').strip()
    replacement = str(plan.get('replacement_text') or '')
    if target and replacement and str(plan.get('mode') or '').strip().lower() in {'anchored_edit', 'tool_loop'}:
        return {
            'target_text': target,
            'replacement_text': replacement,
        }
    return _extract_text_replacement_request(job.instruction)


def _extract_text_replacement_request(instruction):
    raw_instruction = str(instruction or '').strip()
    if not raw_instruction:
        return None
    for pattern in REPLACEMENT_REQUEST_PATTERNS:
        match = pattern.search(raw_instruction)
        if not match:
            continue
        target_text = str(match.group('target') or '').strip(' "\'`“”')
        replacement_text = str(match.group('replacement') or '').strip(' "\'`“”')
        if not target_text or not replacement_text or target_text == replacement_text:
            continue
        if len(target_text) > 300 or len(replacement_text) > 300:
            continue
        return {
            'target_text': target_text,
            'replacement_text': replacement_text,
        }
    return None


def _replacement_command_input(*, target_text, replacement_text, occurrence='all'):
    return {
        'target_text': str(target_text or '').strip(),
        'replacement_text': str(replacement_text or ''),
        'occurrence': 'first' if str(occurrence or '').strip().lower() == 'first' else 'all',
        'match_case': True,
        'match_whole_word': True,
        'preserve_formatting': True,
    }


def _transformed_case_text(*, source_text, case_name):
    normalized_case_name = str(case_name or '').strip().lower()
    if not source_text:
        return ''
    if normalized_case_name == 'uppercase':
        return source_text.upper()
    if normalized_case_name == 'lowercase':
        return source_text.lower()
    return ''


def _build_fallback_agent_decision(*, job, tool_transcript, latest_command, session_snapshot, failure):
    transcript = list(tool_transcript or [])
    latest_tool = str((latest_command or {}).get('tool_name') or '').strip()
    latest_result = dict((latest_command or {}).get('result') or {})
    executed_tools = {
        str(item.get('tool_name') or '').strip()
        for item in transcript
        if isinstance(item, dict) and str(item.get('status') or '').strip().lower() == 'completed'
    }
    instruction_flags = _instruction_flags(job.instruction)

    if _latest_command_failed(latest_command):
        return {
            'action': 'fail_session',
            'summary': 'Latest Word tool failed.',
            'warnings': ['latest_command_failed'],
            'commands': [],
            'error_code': 'word_tool_failed',
            'error_detail': str((latest_command or {}).get('error') or 'The Word host reported a failed tool.'),
        }

    if not transcript:
        return _queue_single(
            tool_name='inspect_document',
            command_input={
                'scope': 'whole_document',
                'include_text_excerpt': True,
                'include_track_revisions_state': True,
            },
            summary='Bootstrap the Word tool loop.',
            warnings=['tool_loop_bootstrap', failure],
        )

    if latest_tool == 'inspect_document':
        pending_capabilities = _pending_capabilities(
            job=job,
            instruction_flags=instruction_flags,
            tool_transcript=transcript,
        )
        if pending_capabilities:
            return _queue_single(
                tool_name=pending_capabilities[0]['tool_name'],
                command_input=pending_capabilities[0]['input'],
                summary='Invoke a native Word capability for a non-body transform.',
                warnings=['llm_fallback', failure],
            )
        replacement_request = _requested_text_replacement(job)
        if replacement_request and 'inspect_text_matches' not in executed_tools:
            return _queue_single(
                tool_name='inspect_text_matches',
                command_input=_replacement_command_input(
                    target_text=replacement_request['target_text'],
                    replacement_text=replacement_request['replacement_text'],
                ),
                summary='Inspect exact text matches before replacing the requested text.',
                warnings=['llm_fallback', failure],
            )
        if instruction_flags['wants_uppercase'] and 'normalize_case_whole_document' not in executed_tools:
            return _queue_single(
                tool_name='normalize_case_whole_document',
                command_input={'case': 'uppercase'},
                summary='Normalize the whole document to uppercase.',
                warnings=['llm_fallback', failure],
            )
        if instruction_flags['wants_bold'] and 'apply_format_whole_document' not in executed_tools:
            return _queue_single(
                tool_name='apply_format_whole_document',
                command_input={'bold': True},
                summary='Apply whole-document bold formatting.',
                warnings=['llm_fallback', failure],
            )
        if instruction_flags['supports_deterministic_export']:
            return _queue_single(
                tool_name='export_document',
                command_input={'include_content_text': True},
                summary='Export the verified document.',
                warnings=['llm_fallback', failure],
            )
        return {
            'action': 'manual_review',
            'summary': 'The fallback tool loop could not derive a safe deterministic command sequence.',
            'warnings': ['no_safe_fallback_path', failure],
            'commands': [],
            'error_code': '',
            'error_detail': '',
        }

    if latest_tool == 'inspect_text_matches':
        replacement_request = _requested_text_replacement(job)
        if replacement_request:
            return _queue_single(
                tool_name='replace_text_matches',
                command_input=_replacement_command_input(
                    target_text=replacement_request['target_text'],
                    replacement_text=replacement_request['replacement_text'],
                ),
                summary='Replace the exact requested text while preserving existing formatting.',
                warnings=['llm_fallback', failure],
            )

    if latest_tool == 'normalize_case_whole_document':
        expected_case = str((latest_command or {}).get('input', {}).get('case') or 'uppercase').strip().lower() or 'uppercase'
        return _queue_single(
            tool_name='verify_document_case',
            command_input={'expected': expected_case},
            summary=f'Verify the whole document is {expected_case}.',
            warnings=['post_mutation_verify'],
        )

    if latest_tool == 'verify_document_case':
        if not _verify_result_passed(latest_result):
            return {
                'action': 'fail_session',
                'summary': 'Whole-document case verification failed.',
                'warnings': ['verify_document_case_failed'],
                'commands': [],
                'error_code': 'verify_document_case_failed',
                'error_detail': json.dumps(latest_result, ensure_ascii=True)[:2000],
            }
        if instruction_flags['wants_bold'] and 'apply_format_whole_document' not in executed_tools:
            return _queue_single(
                tool_name='apply_format_whole_document',
                command_input={'bold': True},
                summary='Apply whole-document bold formatting.',
                warnings=['llm_fallback', failure],
            )
        pending_capabilities = _pending_capabilities(
            job=job,
            instruction_flags=instruction_flags,
            tool_transcript=transcript,
        )
        if pending_capabilities:
            return _queue_single(
                tool_name=pending_capabilities[0]['tool_name'],
                command_input=pending_capabilities[0]['input'],
                summary='Invoke the next native Word capability.',
                warnings=['llm_fallback', failure],
            )
        return _queue_single(
            tool_name='export_document',
            command_input={'include_content_text': True},
            summary='Export the verified document.',
            warnings=['llm_fallback', failure],
        )

    if latest_tool == 'apply_format_whole_document':
        verify_input = _build_follow_up_verify_input(latest_command) or {}
        return _queue_single(
            tool_name='verify_document_format_coverage',
            command_input=verify_input,
            summary='Verify the whole document formatting coverage.',
            warnings=['post_mutation_verify'],
        )

    if latest_tool == 'verify_document_format_coverage':
        if not _verify_result_passed(latest_result):
            return {
                'action': 'fail_session',
                'summary': 'Whole-document format verification failed.',
                'warnings': ['verify_document_format_failed'],
                'commands': [],
                'error_code': 'verify_document_format_failed',
                'error_detail': json.dumps(latest_result, ensure_ascii=True)[:2000],
            }
        pending_capabilities = _pending_capabilities(
            job=job,
            instruction_flags=instruction_flags,
            tool_transcript=transcript,
        )
        if pending_capabilities:
            return _queue_single(
                tool_name=pending_capabilities[0]['tool_name'],
                command_input=pending_capabilities[0]['input'],
                summary='Invoke the next native Word capability.',
                warnings=['llm_fallback', failure],
            )
        return _queue_single(
            tool_name='export_document',
            command_input={'include_content_text': True},
            summary='Export the verified document.',
            warnings=['llm_fallback', failure],
        )

    if latest_tool == 'replace_text_matches':
        return _queue_single(
            tool_name='verify_text_replacement',
            command_input=_build_follow_up_verify_input(latest_command) or {
                'target_text': str((latest_command or {}).get('input', {}).get('target_text') or ''),
                'replacement_text': str((latest_command or {}).get('input', {}).get('replacement_text') or ''),
            },
            summary='Verify the text replacement result.',
            warnings=['post_mutation_verify'],
        )

    generic_verify_tool = verify_pair_for_tool(latest_tool)
    generic_verify_input = _build_follow_up_verify_input(latest_command)
    if generic_verify_tool and generic_verify_input is not None and latest_tool not in {
        'normalize_case_whole_document',
        'replace_text_matches',
        'apply_format_whole_document',
    }:
        return _queue_single(
            tool_name=generic_verify_tool,
            command_input=generic_verify_input,
            summary=f'Verify the result of {latest_tool}.',
            warnings=['post_mutation_verify'],
        )

    if latest_tool == 'verify_text_replacement':
        if not bool(latest_result.get('matches_expected_replacement')):
            return {
                'action': 'fail_session',
                'summary': 'Text replacement verification failed.',
                'warnings': ['verify_text_replacement_failed'],
                'commands': [],
                'error_code': 'verify_text_replacement_failed',
                'error_detail': json.dumps(latest_result, ensure_ascii=True)[:2000],
            }
        if instruction_flags['wants_bold'] and 'apply_format_whole_document' not in executed_tools:
            return _queue_single(
                tool_name='apply_format_whole_document',
                command_input={'bold': True},
                summary='Apply follow-up formatting after replacement.',
                warnings=['llm_fallback', failure],
            )
        pending_capabilities = _pending_capabilities(
            job=job,
            instruction_flags=instruction_flags,
            tool_transcript=transcript,
        )
        if pending_capabilities:
            return _queue_single(
                tool_name=pending_capabilities[0]['tool_name'],
                command_input=pending_capabilities[0]['input'],
                summary='Invoke the next native Word capability.',
                warnings=['llm_fallback', failure],
            )
        return _queue_single(
            tool_name='export_document',
            command_input={'include_content_text': True},
            summary='Export the verified document.',
            warnings=['llm_fallback', failure],
        )

    if latest_tool in {
        'verify_selection_text',
        'verify_selection_case',
        'verify_selection_format',
        'verify_track_changes_state',
        'verify_header_replacement',
        'verify_footer_replacement',
        'verify_table_replacement',
        'verify_comment_selection',
    }:
        if not _verify_result_passed(latest_result):
            return {
                'action': 'fail_session',
                'summary': f'{latest_tool} failed.',
                'warnings': [f'{latest_tool}_failed'],
                'commands': [],
                'error_code': f'{latest_tool}_failed',
                'error_detail': json.dumps(latest_result, ensure_ascii=True)[:2000],
            }
        pending_capabilities = _pending_capabilities(
            job=job,
            instruction_flags=instruction_flags,
            tool_transcript=transcript,
        )
        if pending_capabilities:
            return _queue_single(
                tool_name=pending_capabilities[0]['tool_name'],
                command_input=pending_capabilities[0]['input'],
                summary='Invoke the next native Word capability.',
                warnings=['llm_fallback', failure],
            )
        return _queue_single(
            tool_name='export_document',
            command_input={'include_content_text': True},
            summary='Export the verified document.',
            warnings=['llm_fallback', failure],
        )

    if latest_tool == 'export_document':
        return {
            'action': 'queue_commands',
            'summary': 'Export already executed; wait for completion upload.',
            'warnings': ['export_already_executed'],
            'commands': [],
            'error_code': '',
            'error_detail': '',
        }

    return {
        'action': 'manual_review',
        'summary': 'The tool loop reached an unsupported state transition.',
        'warnings': ['unsupported_state_transition', failure],
        'commands': [],
        'error_code': '',
        'error_detail': '',
    }


def _queue_single(*, tool_name, command_input, summary, warnings):
    return {
        'action': 'queue_commands',
        'summary': summary,
        'warnings': [str(item) for item in warnings if str(item).strip()],
        'commands': [
            {
                'id': f'cmd-{uuid.uuid4().hex[:12]}',
                'tool_name': tool_name,
                'input': command_input,
            }
        ],
        'error_code': '',
        'error_detail': '',
    }


def _latest_command_failed(latest_command):
    if not isinstance(latest_command, dict):
        return False
    return str(latest_command.get('status') or '').strip().lower() == 'failed'


def _normalized_instruction(instruction):
    normalized = unicodedata.normalize('NFKD', str(instruction or '').strip().lower())
    return ''.join(character for character in normalized if not unicodedata.combining(character))


def _instruction_flags(instruction):
    normalized = _normalized_instruction(instruction)
    wants_uppercase = any(token in normalized for token in ('uppercase', 'viet hoa', 'chu hoa'))
    wants_bold = any(token in normalized for token in ('bold', 'boi den', 'in dam'))
    wants_headers = 'header' in normalized or 'dau trang' in normalized
    wants_footers = 'footer' in normalized or 'chan trang' in normalized
    wants_tables = 'table' in normalized or 'bang' in normalized
    wants_track_changes = any(token in normalized for token in ('track changes', 'tracked changes', 'revision', 'theo doi sua doi'))
    wants_comment = any(token in normalized for token in ('comment', 'ghi chu', 'nhan xet'))
    wants_alignment = any(token in normalized for token in ('align', 'canh le', 'center', 'left', 'right', 'justify'))
    wants_spacing = any(token in normalized for token in ('line spacing', 'paragraph spacing', 'gian dong', 'khoang cach doan'))
    return {
        'wants_uppercase': wants_uppercase,
        'wants_bold': wants_bold,
        'wants_headers': wants_headers,
        'wants_footers': wants_footers,
        'wants_tables': wants_tables,
        'wants_track_changes': wants_track_changes,
        'wants_comment': wants_comment,
        'wants_alignment': wants_alignment,
        'wants_spacing': wants_spacing,
        'supports_deterministic_export': wants_uppercase or wants_bold or wants_headers or wants_footers or wants_tables or wants_track_changes or wants_comment or wants_alignment or wants_spacing,
    }


def _pending_capabilities(*, job, instruction_flags, tool_transcript):
    pending = []
    used_tools = {
        str(item.get('tool_name') or '').strip()
        for item in (tool_transcript or [])
        if isinstance(item, dict)
    }
    if instruction_flags['wants_headers'] and 'replace_in_headers' not in used_tools:
        pending.append(
            {
                'tool_name': 'replace_in_headers',
                'input': _native_capability_arguments(job=job),
            }
        )
    if instruction_flags['wants_footers'] and 'replace_in_footers' not in used_tools:
        pending.append(
            {
                'tool_name': 'replace_in_footers',
                'input': _native_capability_arguments(job=job),
            }
        )
    if instruction_flags['wants_tables'] and 'replace_in_tables' not in used_tools:
        pending.append(
            {
                'tool_name': 'replace_in_tables',
                'input': _native_capability_arguments(job=job),
            }
        )
    if instruction_flags['wants_track_changes'] and 'toggle_track_changes' not in used_tools:
        pending.append(
            {
                'tool_name': 'toggle_track_changes',
                'input': {'enabled': bool(job.track_changes)},
            }
        )
    if instruction_flags['wants_comment'] and 'insert_comment_selection' not in used_tools:
        pending.append(
            {
                'tool_name': 'insert_comment_selection',
                'input': {'comment_text': str(job.instruction or '')[:500]},
            }
        )
    if instruction_flags['wants_alignment'] and 'set_paragraph_alignment' not in used_tools:
        pending.append(
            {
                'tool_name': 'set_paragraph_alignment',
                'input': {'alignment': _infer_alignment(job.instruction)},
            }
        )
    if instruction_flags['wants_spacing'] and 'set_line_spacing' not in used_tools:
        pending.append(
            {
                'tool_name': 'set_line_spacing',
                'input': {'line_spacing': _infer_line_spacing(job.instruction)},
            }
        )
    return pending


def _build_follow_up_verify_input(latest_command):
    latest_tool = str((latest_command or {}).get('tool_name') or '').strip()
    latest_input = dict((latest_command or {}).get('input') or {})
    latest_result = dict((latest_command or {}).get('result') or {})

    if latest_tool == 'replace_text_matches':
        return {
            'target_text': str(latest_input.get('target_text') or ''),
            'replacement_text': str(latest_input.get('replacement_text') or ''),
            'expected_replaced_count': int(latest_result.get('replaced_count') or 0),
            'match_case': bool(latest_input.get('match_case', False)),
            'match_whole_word': bool(latest_input.get('match_whole_word', False)),
        }
    if latest_tool == 'replace_selection_text':
        return {'expected_text': str(latest_input.get('replacement_text') or '')}
    if latest_tool == 'normalize_case_selection':
        return {'expected': str(latest_input.get('case') or '')}
    if latest_tool == 'apply_format_selection':
        return {
            'bold': latest_input.get('bold', ''),
            'italic': latest_input.get('italic', ''),
            'font_color': latest_input.get('font_color', ''),
            'alignment': latest_input.get('alignment', ''),
            'font_name': latest_input.get('font_name', ''),
            'font_size': latest_input.get('font_size', ''),
            'line_spacing': latest_input.get('line_spacing', ''),
            'spacing_before': latest_input.get('spacing_before', ''),
            'spacing_after': latest_input.get('spacing_after', ''),
        }
    if latest_tool == 'apply_format_whole_document':
        return {
            'bold': latest_input.get('bold', ''),
            'italic': latest_input.get('italic', ''),
            'font_color': latest_input.get('font_color', ''),
        }
    if latest_tool == 'clear_format_selection':
        return {}
    if latest_tool == 'set_paragraph_alignment':
        return {'alignment': latest_input.get('alignment', '')}
    if latest_tool == 'set_line_spacing':
        return {
            'line_spacing': latest_input.get('line_spacing', ''),
        }
    if latest_tool == 'set_paragraph_spacing':
        return {
            'spacing_before': latest_input.get('spacing_before', ''),
            'spacing_after': latest_input.get('spacing_after', ''),
        }
    if latest_tool == 'toggle_track_changes':
        return {'expected_enabled': latest_input.get('enabled', False)}
    if latest_tool in {'replace_in_headers', 'replace_in_footers', 'replace_in_tables'}:
        return {
            'target_text': str(latest_input.get('target_text') or ''),
            'replacement_text': str(latest_input.get('replacement_text') or ''),
        }
    if latest_tool == 'insert_comment_selection':
        return {'comment_text': str(latest_input.get('comment_text') or '')}
    return None


def _verify_result_passed(result):
    payload = dict(result or {})
    if 'verified' in payload:
        return bool(payload.get('verified'))
    if 'matches_expected_case' in payload:
        return bool(payload.get('matches_expected_case'))
    if 'matches_expected_format' in payload:
        return bool(payload.get('matches_expected_format'))
    if 'matches_expected_replacement' in payload:
        return bool(payload.get('matches_expected_replacement'))
    if 'is_all_lowercase' in payload:
        return bool(payload.get('is_all_lowercase'))
    if 'is_all_uppercase' in payload:
        return bool(payload.get('is_all_uppercase'))
    return False


def _transcript_contains_failed_verify(tool_transcript):
    for item in tool_transcript or []:
        if not isinstance(item, dict):
            continue
        tool_name = str(item.get('tool_name') or '').strip()
        if not is_verify_tool(tool_name):
            continue
        if not _verify_result_passed(item.get('result') or {}):
            return True
    return False


def _decision_queues_export(commands):
    return any(str((item or {}).get('tool_name') or '').strip() == 'export_document' for item in (commands or []))


def _native_capability_arguments(*, job):
    plan = job.plan_payload or {}
    return {
        'instruction': job.instruction,
        'target_text': str(plan.get('target_anchor') or ''),
        'replacement_text': str(plan.get('replacement_text') or ''),
    }


def _infer_alignment(instruction):
    normalized = _normalized_instruction(instruction)
    if 'center' in normalized or 'canh giua' in normalized:
        return 'center'
    if 'right' in normalized or 'canh phai' in normalized:
        return 'right'
    if 'justify' in normalized or 'deu' in normalized:
        return 'justify'
    return 'left'


def _infer_line_spacing(instruction):
    normalized = _normalized_instruction(instruction)
    if '1.5' in normalized:
        return '1.5'
    if 'double' in normalized or '2.0' in normalized:
        return '2.0'
    return 'single'
