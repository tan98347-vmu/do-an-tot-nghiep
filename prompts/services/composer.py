from __future__ import annotations

from collections.abc import Iterable

from prompts.models import Prompt


DEFAULT_USAGE_SCOPES = (
    'template_fill',
    'summary',
    'word_ai_edit',
    'chat',
    'compliance_check',
)

OPTION_TEMPLATES: dict[str, dict[str, dict[str, str]]] = {
    'template_fill': {
        'tone': {
            'formal': 'Sử dụng văn phong trang trọng và nhất quán.',
            'friendly': 'Giữ văn phong thân thiện, dễ đọc.',
            'neutral': 'Dùng văn phong trung tính, chuyên nghiệp.',
        },
        'length': {
            'short': 'Ưu tiên câu chữ ngắn gọn, đi thẳng vào nội dung chính.',
            'medium': 'Trình bày đủ ý trong độ dài trung bình.',
            'long': 'Triển khai chi tiết, có mở đầu và kết thúc rõ ràng.',
        },
        'format': {
            'plain': 'Trả về nội dung văn bản thuần, không dùng bullet.',
            'bullet': 'Cho phép dùng bullet khi giúp nội dung rõ ràng hơn.',
        },
    },
    'summary': {
        'depth': {
            'brief': 'Tóm tắt ngắn trong 5-7 câu.',
            'detailed': 'Tóm tắt chi tiết thành nhiều đoạn mạch lạc.',
            'bullet': 'Tóm tắt theo dạng bullet list có ý chính rõ ràng.',
        },
        'language': {
            'vi': 'Trả lời bằng tiếng Việt.',
            'en': 'Reply in English.',
        },
        'focus': {
            'key_points': 'Ưu tiên nêu các ý chính và kết luận quan trọng.',
            'risks': 'Nhấn mạnh rủi ro, vấn đề còn mở, và điểm cần lưu ý.',
        },
    },
    'word_ai_edit': {
        'mode': {
            'rewrite': 'Viết lại toàn bộ nội dung theo hướng rõ ràng hơn.',
            'polish': 'Chỉ trau chuốt văn phong, không đổi ý chính.',
            'expand': 'Mở rộng nội dung bằng cách thêm diễn giải cần thiết.',
            'shorten': 'Rút gọn nội dung nhưng giữ nguyên ý nghĩa cốt lõi.',
        },
        'tone': {
            'formal': 'Giữ giọng văn trang trọng, phù hợp văn bản công việc.',
            'plain': 'Dùng câu chữ đơn giản, trực tiếp, dễ hiểu.',
        },
    },
    'chat': {
        'persona': {
            'assistant': 'Đóng vai trợ lý văn phòng chuyên nghiệp.',
            'lawyer': 'Đóng vai luật sư tư vấn pháp lý thận trọng.',
            'analyst': 'Đóng vai chuyên viên phân tích tài liệu, trả lời súc tích.',
        },
        'response_style': {
            'direct': 'Trả lời trực tiếp, đi vào trọng tâm trước.',
            'guided': 'Trả lời theo từng bước để người dùng dễ làm theo.',
        },
    },
    'compliance_check': {
        'severity': {
            'strict': 'Kiểm tra nghiêm ngặt từng yêu cầu một.',
            'lenient': 'Cho phép chấp nhận các đáp ứng tương đương hợp lý.',
        },
        'output': {
            'table': 'Trả kết quả theo cấu trúc bảng hoặc mục rõ ràng.',
            'narrative': 'Trả kết quả theo diễn giải có kết luận ngắn.',
        },
    },
}


def _load_usage_scopes() -> tuple[str, ...]:
    try:
        from prompts.models import USAGE_SCOPES  # type: ignore
    except Exception:
        return DEFAULT_USAGE_SCOPES
    if isinstance(USAGE_SCOPES, dict):
        return tuple(USAGE_SCOPES.keys())
    if isinstance(USAGE_SCOPES, Iterable):
        return tuple(str(item) for item in USAGE_SCOPES)
    return DEFAULT_USAGE_SCOPES


def _peer_can(user, obj, level: str) -> bool:
    try:
        from accounts.peer_permissions import peer_can  # type: ignore
    except Exception:
        return True
    return bool(peer_can(user, obj, level))


def _load_base_prompt(*, base_prompt_id: int | None, user=None) -> Prompt | None:
    if not base_prompt_id:
        return None
    prompt = Prompt.objects.filter(pk=base_prompt_id).first()
    if prompt is None:
        raise Prompt.DoesNotExist(f'Prompt {base_prompt_id} not found')
    if user is None:
        return prompt
    owner_id = getattr(prompt, 'owner_id', None)
    if owner_id == getattr(user, 'id', None) or getattr(user, 'is_superuser', False):
        return prompt
    if _peer_can(user, prompt, 'view'):
        return prompt
    raise PermissionError('Bạn không có quyền dùng prompt này.')


def compose_prompt(
    *,
    base_prompt_id: int | None,
    scope: str,
    options: dict,
    extra_user_text: str,
    user=None,
) -> dict:
    sections: list[tuple[str, str]] = []
    prompt = _load_base_prompt(base_prompt_id=base_prompt_id, user=user)
    if prompt is not None:
        if getattr(prompt, 'system_content', ''):
            sections.append(('Hệ tư tưởng', prompt.system_content))
        if getattr(prompt, 'rules_content', ''):
            sections.append(('Quy tắc', prompt.rules_content))

    scope_templates = OPTION_TEMPLATES.get(scope, {})
    options = options if isinstance(options, dict) else {}
    for option_key in scope_templates:
        selected_value = options.get(option_key)
        selected_text = scope_templates.get(option_key, {}).get(str(selected_value or ''))
        if selected_text:
            sections.append((f'Tùy chọn — {option_key}', selected_text))

    extra_text = str(extra_user_text or '').strip()
    if extra_text:
        sections.append(('Yêu cầu thêm', extra_text))

    composed_text = '\n\n'.join(f'### {label}\n{content}' for label, content in sections)
    return {
        'composed_text': composed_text,
        'token_estimate': max(0, len(composed_text) // 4),
        'sections': [
            {'label': label, 'content': content}
            for label, content in sections
        ],
    }


ALLOWED_COMPOSE_SCOPES = _load_usage_scopes()
