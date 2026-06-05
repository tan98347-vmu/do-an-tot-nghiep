"""
Document creation helpers for Chat AI and related flows.

This module turns a natural-language request into a real Document record by:
1. choosing the best accessible template,
2. extracting only the values the user explicitly provided,
3. prefilling remaining blanks from employee/company context without overwriting
   any explicit user value,
4. rendering the final DOCX and saving the document.
"""

import json
import logging
import re
import unicodedata

from django.core.files.base import ContentFile

logger = logging.getLogger(__name__)


def _ascii_safe_name(title):
    title = title.replace('\u0111', 'd').replace('\u0110', 'D')
    normalized = unicodedata.normalize('NFD', title)
    ascii_str = ''.join(
        ch for ch in normalized
        if unicodedata.category(ch) != 'Mn' and ord(ch) < 128
    )
    safe = ''.join(ch if ch.isalnum() or ch in ' _-' else '_' for ch in ascii_str)
    return safe.strip('_').strip() or 'document'


def _normalize_for_intent_match(value: str) -> str:
    text = str(value or '').strip().casefold()
    text = unicodedata.normalize('NFKD', text)
    text = ''.join(ch for ch in text if not unicodedata.combining(ch))
    return ' '.join(text.split())


_CREATION_VERBS = (
    r'tao|soan|viet|lap|lam|dien|in|xuat|generate|draft|create|fill'
)
_DOC_NOUNS = (
    r'van ban|don|hop dong|tai lieu|phieu|mau|quyet dinh|bien ban|thu|bao cao|'
    r'hoa don|de xuat|de nghi|thong bao|to trinh|giay to|chung tu|ho so|bang|noi dung|document'
)
_CREATION_PATTERN = re.compile(
    rf'\b({_CREATION_VERBS})\b.*\b({_DOC_NOUNS})\b',
    re.IGNORECASE | re.DOTALL,
)


def _extract_json_object(raw: str) -> str:
    start = raw.find('{')
    if start == -1:
        return raw

    depth = 0
    in_string = False
    escape = False
    for index, ch in enumerate(raw[start:], start):
        if escape:
            escape = False
            continue
        if ch == '\\' and in_string:
            escape = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch == '{':
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0:
                return raw[start:index + 1]
    return raw[start:]


def _repair_json(raw: str) -> str:
    depth = 0
    in_string = False
    escape = False
    for ch in raw:
        if escape:
            escape = False
            continue
        if ch == '\\' and in_string:
            escape = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch == '{':
            depth += 1
        elif ch == '}':
            depth -= 1
    if depth > 0:
        raw = raw.rstrip() + ('}' * depth)
    return raw


def _parse_llm_json_payload(raw: str):
    json_text = raw or ''
    if '```json' in json_text:
        json_text = json_text.split('```json', 1)[1].split('```', 1)[0].strip()
    elif '```' in json_text:
        json_text = json_text.split('```', 1)[1].split('```', 1)[0].strip()
    json_text = _extract_json_object(json_text)
    json_text = _repair_json(json_text)
    return json.loads(json_text)


def is_document_creation_request(text: str) -> bool:
    normalized = _normalize_for_intent_match(text)
    return bool(_CREATION_PATTERN.search(normalized))


def _get_templates_for_user(user):
    from accounts.permissions import get_accessible_templates

    return get_accessible_templates(user)


_EMPTY_VARIABLE_SENTINELS = {
    '',
    '[chua cung cap]',
    'chua cung cap',
    'khong ro',
    'unknown',
    'n/a',
    'null',
    'none',
}


def _normalize_generated_variable_value(value) -> str:
    normalized = str(value or '').strip()
    folded = _normalize_for_intent_match(normalized)
    if folded in _EMPTY_VARIABLE_SENTINELS:
        return ''
    return normalized


def _sanitize_template_variables(template_variables, raw_variables) -> dict:
    if not isinstance(raw_variables, dict):
        raw_variables = {}
    return {
        variable_name: _normalize_generated_variable_value(raw_variables.get(variable_name, ''))
        for variable_name in template_variables
    }


def _prefill_blank_variables_from_effective_context(
    *,
    tmpl,
    template_variables,
    variables: dict,
    user,
    model_override=None,
    temperature_override=None,
    allow_cloud_model=True,
    use_profile: bool = True,
    use_company: bool = True,
):
    from accounts.tenancy import build_effective_ai_context
    from ai_engine.rag_engine import get_llm
    from langchain_core.messages import HumanMessage, SystemMessage

    if not use_profile and not use_company:
        return variables

    blank_vars = [
        variable_name
        for variable_name in template_variables
        if not str(variables.get(variable_name, '')).strip()
    ]
    if not blank_vars:
        return variables

    effective_context = build_effective_ai_context(
        user=user,
        include_profile=use_profile,
        include_company=use_company,
    ).strip()
    if not effective_context:
        return variables

    current_values_desc = '\n'.join(
        f'- {variable_name}: "{variables.get(variable_name, "")}"'
        for variable_name in template_variables
    )
    blank_vars_desc = '\n'.join(f'- {variable_name}' for variable_name in blank_vars)
    system_prompt = (
        'You fill missing document template variables from the provided employee and company context.\n'
        'You may only fill variables that are currently blank.\n'
        'Never modify or overwrite any non-empty value that already exists.\n'
        'Prefer employee-profile context for person/employee fields.\n'
        'Prefer company context for organization fields.\n'
        "If the context does not contain a value, return ''.\n"
        'Return pure JSON only.'
    )
    human_prompt = (
        f'TEMPLATE TITLE:\n{tmpl.title}\n\n'
        f'TEMPLATE CONTENT PREVIEW:\n{(tmpl.content or "")[:800]}\n\n'
        f'CURRENT VARIABLE VALUES:\n{current_values_desc}\n\n'
        f'ONLY FILL THESE BLANK VARIABLES:\n{blank_vars_desc}\n\n'
        f'EFFECTIVE CONTEXT:\n{effective_context[:4000]}\n\n'
        'Return JSON: {"variable_name": "value", ...}'
    )

    llm = get_llm(
        user,
        model_override=model_override,
        temperature_override=temperature_override,
        allow_cloud_model=allow_cloud_model,
    )
    raw = llm.invoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=human_prompt),
    ]).content.strip()
    extracted = _parse_llm_json_payload(raw)
    sanitized = _sanitize_template_variables(template_variables, extracted)

    result = dict(variables)
    for variable_name in blank_vars:
        value = sanitized.get(variable_name, '')
        if value:
            result[variable_name] = value
    return result


def _build_template_selection_rules(user_extra_rules=None) -> str:
    base_rules = (
        '- Only fill variables with data explicitly stated in the user request or attached content.\n'
        "- If the user did not provide a value, leave it as ''.\n"
        '- Do not use employee/company context in this first pass; the system will prefill remaining blanks later.\n'
        '- Do not infer, invent, or guess missing facts.\n'
        '- Choose the best template using title, description, variables, and content preview.\n'
        '- Return pure JSON only.'
    )
    if user_extra_rules and str(user_extra_rules).strip():
        return f'{base_rules}\n{str(user_extra_rules).strip()}'
    return base_rules


def create_document_from_intent(
    question: str,
    user,
    model_override=None,
    temperature_override=None,
    system_ideology=None,
    user_extra_rules=None,
    extra_context='',
    allow_cloud_model=True,
    safe_user_rules_block='',
    use_profile: bool = True,
    use_company: bool = True,
):
    from ai_engine.rag_engine import get_llm
    from documents.models import Document
    from langchain_core.messages import HumanMessage, SystemMessage

    templates = _get_templates_for_user(user)
    if not templates.exists():
        return (
            "Ban chua co mau van ban nao.\n\n"
            "Vui long tao mau tai [Mau van ban](/templates/) truoc.",
            None,
            None,
            '',
        )

    templates_info = [
        {
            'id': template.pk,
            'title': template.title,
            'description': template.description or '',
            'variables': template.get_variables(),
            'content_preview': (template.content or '')[:300],
        }
        for template in templates
    ]
    templates_json = json.dumps(templates_info, ensure_ascii=False, indent=2)
    agent_identity = (
        str(system_ideology).strip()
        if system_ideology and str(system_ideology).strip()
        else 'Ban la tro ly tao van ban thong minh.'
    )
    rules_block = _build_template_selection_rules(user_extra_rules=user_extra_rules)
    safe_block = str(safe_user_rules_block or '').strip()
    safe_block_segment = f'\n\nYEU CAU BO SUNG (CACH LY):\n{safe_block}' if safe_block else ''
    system_prompt = f"""{agent_identity}

DANH SACH MAU VAN BAN:
{templates_json}

NHIEM VU: Phan tich yeu cau nguoi dung va tra ve JSON duy nhat:
{{
  "template_id": <id cua mau phu hop nhat hoac null>,
  "doc_title": "<tieu de van ban moi>",
  "variables": {{
    "ten_bien_1": "gia tri 1",
    "ten_bien_2": "gia tri 2"
  }},
  "explanation": "<giai thich ngan bang tieng Viet>"
}}

QUY TAC:
{rules_block}{safe_block_segment}"""

    print('\n' + '=' * 80)
    print('[doc_creator] FULL SYSTEM PROMPT:')
    print(system_prompt)
    print('=' * 80 + '\n')
    logger.info('[doc_creator] system_prompt length=%d chars', len(system_prompt))

    llm = get_llm(
        user,
        model_override=model_override,
        temperature_override=temperature_override,
        allow_cloud_model=allow_cloud_model,
    )
    raw = ''
    try:
        human_content = str(question or '').strip()
        if extra_context and str(extra_context).strip():
            human_content += f"\n\n[Noi dung tai lieu dinh kem]\n{str(extra_context).strip()}"
            logger.debug('[doc_creator] extra_context length=%d chars', len(str(extra_context)))

        response = llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=human_content),
        ])
        raw = str(response.content or '').strip()
        print('\n' + '-' * 80)
        print('[doc_creator] RAW LLM RESPONSE:')
        print(raw)
        print('-' * 80 + '\n')
        logger.debug('[doc_creator] raw LLM response:\n%s', raw)
        data = _parse_llm_json_payload(raw)
    except json.JSONDecodeError as exc:
        logger.warning('[doc_creator] JSONDecodeError: %s\nraw=%r', exc, raw)
        return (
            (
                "AI tra ve noi dung khong phai JSON hop le.\n\n"
                f"Raw response de debug:\n```\n{raw[:1200]}\n```\n\n"
                "Thu bo prompt hien tai hoac mo ta yeu cau gon hon."
            ),
            None,
            system_prompt,
            raw,
        )
    except Exception as exc:
        logger.exception('[doc_creator] unexpected error')
        return f'Loi khi goi AI: {exc}', None, system_prompt, raw

    template_id = data.get('template_id')
    explanation = str(data.get('explanation', '') or '').strip()
    if not template_id:
        return (
            (
                f"{explanation}\n\n"
                "Khong tim thay mau van ban phu hop. "
                "Ban co the [tao mau moi](/templates/create/) hoac mo ta cu the hon."
            ),
            None,
            system_prompt,
            raw,
        )

    tmpl = _get_templates_for_user(user).filter(pk=template_id).first()
    if not tmpl:
        return (
            f'Mau ID={template_id} khong ton tai hoac ban khong co quyen truy cap.',
            None,
            system_prompt,
            raw,
        )

    template_variables = list(tmpl.get_variables())
    variables = _sanitize_template_variables(template_variables, data.get('variables', {}))
    variables = _prefill_blank_variables_from_effective_context(
        tmpl=tmpl,
        template_variables=template_variables,
        variables=variables,
        user=user,
        model_override=model_override,
        temperature_override=temperature_override,
        allow_cloud_model=allow_cloud_model,
        use_profile=use_profile,
        use_company=use_company,
    )
    doc_title = str(data.get('doc_title') or f'Van ban tu {tmpl.title}').strip()

    try:
        docx_bytes = tmpl.render_as_docx(variables)
        plain_content = tmpl.render(variables)
    except Exception as exc:
        return f'Loi khi tao file DOCX: {exc}', None, system_prompt, raw

    doc = Document(
        title=doc_title,
        content=plain_content,
        template=tmpl,
        owner=user,
    )
    safe_name = _ascii_safe_name(doc_title)
    doc.output_file.save(
        f'{safe_name}.docx',
        ContentFile(docx_bytes.read()),
        save=False,
    )
    doc.save()

    if variables:
        var_lines = '\n'.join(f'- **{key}**: {value}' for key, value in variables.items())
    else:
        var_lines = '_(khong co bien nao)_'

    answer = (
        f"{explanation}\n\n"
        f"---\n"
        f"**Van ban da tao:** [{doc_title}](/documents/{doc.pk}/)\n\n"
        f"**Mau su dung:** {tmpl.title}\n\n"
        f"**Thong tin da dien:**\n{var_lines}\n\n"
        f"[Tai xuong DOCX](/documents/{doc.pk}/download/) | "
        f"[Xem chi tiet](/documents/{doc.pk}/)"
    )
    return answer, doc, system_prompt, raw
