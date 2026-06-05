import json
import re

from langchain_core.messages import HumanMessage, SystemMessage

from accounts.tenancy import resolve_ai_config
from ai_engine.rag_engine import get_llm
from word_ai.services.config_service import allowed_format_ops, allowed_macro_capabilities
from word_ai.services.event_log_service import append_job_event


JSON_BLOCK_RE = re.compile(r'```(?:json)?\s*(\{.*?\})\s*```', re.DOTALL)


def _extract_json_block(text):
    text = str(text or '').strip()
    if not text:
        raise ValueError('Planner returned empty content.')
    match = JSON_BLOCK_RE.search(text)
    if match:
        return match.group(1)
    start = text.find('{')
    end = text.rfind('}')
    if start >= 0 and end > start:
        return text[start:end + 1]
    raise ValueError('Planner did not return JSON.')


def _latest_variables(document):
    latest_version = document.versions.order_by('-version_number').first()
    if latest_version and isinstance(latest_version.variables_used, dict):
        return latest_version.variables_used
    return {}


def _sanitize_plan_with_debug(job, raw_plan):
    mode = str(raw_plan.get('mode') or 'anchored_edit').strip().lower()
    if mode not in {'anchored_edit', 'selection_edit', 'manual_review', 'requires_template_rebuild'}:
        mode = 'manual_review'

    allowed_ops = allowed_format_ops()
    allowed_ops_set = set(allowed_ops)
    raw_ops = raw_plan.get('format_ops') or []
    format_ops = []
    requested_format_ops = []
    dropped_format_ops = []
    if isinstance(raw_ops, list):
        for index, op in enumerate(raw_ops):
            if not isinstance(op, dict):
                dropped_format_ops.append(
                    {
                        'index': index,
                        'reason': 'invalid_format_op_type',
                        'received_type': type(op).__name__,
                    }
                )
                continue
            action = str(op.get('action') or '').strip()
            requested_format_ops.append(
                {
                    'index': index,
                    'action': action,
                    'value': op.get('value'),
                }
            )
            if not action:
                dropped_format_ops.append(
                    {
                        'index': index,
                        'reason': 'missing_action',
                        'value': op.get('value'),
                    }
                )
                continue
            if action not in allowed_ops_set:
                dropped_format_ops.append(
                    {
                        'index': index,
                        'reason': 'unsupported_action',
                        'action': action,
                        'value': op.get('value'),
                    }
                )
                continue
            format_ops.append(
                {
                    'action': action,
                    'value': op.get('value'),
                }
            )

    warnings = raw_plan.get('warnings') or []
    if not isinstance(warnings, list):
        warnings = [str(warnings)]

    allowed_macro_caps = allowed_macro_capabilities()
    allowed_macro_caps_set = set(allowed_macro_caps)
    requested_macro_caps = []
    dropped_macro_caps = []
    raw_macro_caps = raw_plan.get('macro_capabilities') or raw_plan.get('macro_capability_hints') or []
    if not isinstance(raw_macro_caps, list):
        raw_macro_caps = [raw_macro_caps]
    macro_capabilities = []
    for index, item in enumerate(raw_macro_caps):
        capability = str(item or '').strip()
        if not capability:
            dropped_macro_caps.append({'index': index, 'reason': 'missing_macro_capability'})
            continue
        requested_macro_caps.append(capability)
        if capability not in allowed_macro_caps_set:
            dropped_macro_caps.append(
                {
                    'index': index,
                    'reason': 'unsupported_macro_capability',
                    'capability': capability,
                }
            )
            continue
        macro_capabilities.append(capability)

    inferred_macro_caps = _infer_macro_capabilities(job.instruction, macro_capabilities)
    for capability in inferred_macro_caps:
        if capability not in macro_capabilities and capability in allowed_macro_caps_set:
            macro_capabilities.append(capability)

    if not _instruction_requests_format_change(job.instruction):
        if format_ops:
            dropped_format_ops.extend(
                {
                    'index': index,
                    'reason': 'format_change_not_explicitly_requested',
                    'action': op.get('action'),
                    'value': op.get('value'),
                }
                for index, op in enumerate(format_ops)
            )
        format_ops = []

    return {
        'mode': mode,
        'target_anchor': str(raw_plan.get('target_anchor') or '').strip(),
        'replacement_text': str(raw_plan.get('replacement_text') or '').strip(),
        'format_ops': format_ops,
        'macro_capabilities': macro_capabilities,
        'track_changes': bool(raw_plan.get('track_changes', job.track_changes)),
        'summary': str(raw_plan.get('summary') or '').strip(),
        'warnings': [str(item) for item in warnings if str(item).strip()],
        'debug': {
            'allowed_format_ops': allowed_ops,
            'requested_format_ops': requested_format_ops,
            'dropped_format_ops': dropped_format_ops,
            'allowed_macro_capabilities': allowed_macro_caps,
            'requested_macro_capabilities': requested_macro_caps,
            'dropped_macro_capabilities': dropped_macro_caps,
            'inferred_macro_capabilities': inferred_macro_caps,
        },
    }, {
        'allowed_format_ops': allowed_ops,
        'requested_format_ops': requested_format_ops,
        'dropped_format_ops': dropped_format_ops,
        'allowed_macro_capabilities': allowed_macro_caps,
        'requested_macro_capabilities': requested_macro_caps,
        'dropped_macro_capabilities': dropped_macro_caps,
        'inferred_macro_capabilities': inferred_macro_caps,
    }


def _sanitize_plan(job, raw_plan):
    sanitized, _debug_payload = _sanitize_plan_with_debug(job, raw_plan)
    return sanitized


def build_edit_plan(job):
    document = job.document
    config = resolve_ai_config(user=job.requested_by)
    allowed_ops = allowed_format_ops()
    allowed_macro_caps = allowed_macro_capabilities()
    llm = get_llm(
        user=job.requested_by,
        model_override=job.llm_model_name or config.ai_model,
        temperature_override=job.llm_temperature,
        allow_cloud_model=job.allow_cloud_model,
    )

    system_prompt = (
        'You are the planning layer for a Microsoft Word editing worker. '
        'Return JSON only. '
        'Never return OOXML, HTML, CSS, or markdown. '
        'Choose one mode from anchored_edit, selection_edit, manual_review, requires_template_rebuild. '
        f'Use format_ops only from these allowed action names: {", ".join(allowed_ops)}. '
        f'Use macro_capabilities only from these allowed names: {", ".join(allowed_macro_caps)}. '
        'If the user asks to change text color, use set_font_color with a named color like black or a #RRGGBB hex value. '
        'If the user asks to capitalize or normalize text, use replacement_text for the exact replacement and keep formatting instructions in format_ops. '
        'When the request is A -> B, treat it as an exact text replacement: remove A and insert exactly B in the same place. '
        'If the user did not explicitly ask to change formatting or layout, keep the original formatting and return an empty format_ops list. '
        'If the user asks about headers, footers, sections, page layout, tables, or tracked changes, include the most relevant macro_capabilities hint.'
    )
    human_prompt = json.dumps(
        {
            'document': {
                'id': document.id,
                'title': document.title,
                'source_type': document.source_type,
                'version_number': document.version_number,
                'has_file': bool(document.output_file),
                'content_excerpt': (document.content or '')[:4000],
                'variables_used': _latest_variables(document),
            },
            'job': {
                'id': job.id,
                'instruction': job.instruction,
                'track_changes': job.track_changes,
                'edit_mode': job.edit_mode,
            },
            'allowed_format_ops': allowed_ops,
            'allowed_macro_capabilities': allowed_macro_caps,
            'response_schema': {
                'mode': 'anchored_edit|selection_edit|manual_review|requires_template_rebuild',
                'target_anchor': 'short string or empty',
                'replacement_text': 'string',
                'format_ops': [
                    {'action': 'set_font_color', 'value': 'black'},
                    {'action': 'set_alignment', 'value': 'center'},
                ],
                'macro_capabilities': ['replace_in_headers'],
                'track_changes': True,
                'summary': 'short summary',
                'warnings': ['list of warning codes'],
            },
        },
        ensure_ascii=True,
    )
    response = llm.invoke([SystemMessage(content=system_prompt), HumanMessage(content=human_prompt)])
    response_text = getattr(response, 'content', '')
    raw_plan_json = _extract_json_block(response_text)
    plan = json.loads(raw_plan_json)
    sanitized, debug_payload = _sanitize_plan_with_debug(job, plan)
    append_job_event(
        job,
        step='planning',
        status='planned',
        message='Word AI plan built.',
        payload={
            'plan_mode': sanitized['mode'],
            'warning_count': len(sanitized['warnings']),
            'ops_count': len(sanitized['format_ops']),
            'allowed_format_ops': debug_payload['allowed_format_ops'],
            'requested_format_ops': debug_payload['requested_format_ops'],
            'applied_format_ops': sanitized['format_ops'],
            'dropped_format_ops': debug_payload['dropped_format_ops'],
            'allowed_macro_capabilities': debug_payload['allowed_macro_capabilities'],
            'requested_macro_capabilities': debug_payload['requested_macro_capabilities'],
            'applied_macro_capabilities': sanitized['macro_capabilities'],
            'dropped_macro_capabilities': debug_payload['dropped_macro_capabilities'],
            'target_anchor': sanitized['target_anchor'],
            'replacement_present': bool(sanitized['replacement_text']),
            'replacement_text_preview': sanitized['replacement_text'][:160],
            'raw_plan_json': raw_plan_json[:4000],
        },
    )
    return sanitized


def _infer_macro_capabilities(instruction, existing_capabilities):
    normalized = _normalize_instruction(instruction)
    inferred = list(existing_capabilities or [])
    if any(token in normalized for token in ('header', 'dau trang')):
        inferred.append('replace_in_headers')
    if any(token in normalized for token in ('footer', 'chan trang')):
        inferred.append('replace_in_footers')
    if any(token in normalized for token in ('track changes', 'tracked changes', 'theo doi sua doi', 'revision')):
        inferred.append('set_track_revisions')
    if 'table' in normalized or 'bang' in normalized:
        inferred.append('replace_in_tables')
    deduped = []
    for item in inferred:
        if item and item not in deduped:
            deduped.append(item)
    return deduped


def _normalize_instruction(instruction):
    return str(instruction or '').strip().lower()


def _instruction_requests_format_change(instruction):
    normalized = _normalize_instruction(instruction)
    format_tokens = (
        'bold',
        'italic',
        'underline',
        'font',
        'font color',
        'color',
        'mau',
        'màu',
        'canh le',
        'căn lề',
        'align',
        'center',
        'left',
        'right',
        'justify',
        'line spacing',
        'paragraph spacing',
        'gian dong',
        'giãn dòng',
        'khoang cach doan',
        'khoảng cách đoạn',
        'in dam',
        'in nghieng',
        'gach chan',
    )
    return any(token in normalized for token in format_tokens)
