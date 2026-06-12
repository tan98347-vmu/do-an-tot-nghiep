import re

from django.db.models import Q

from accounts.permissions import get_accessible_prompts

_UNACCENT_FIELDS = (
    'title',
    'system_content',
    'rules_content',
    'original_raw_text',
    'category__name',
    'group__name',
    'owner__username',
    'owner__first_name',
    'owner__last_name',
)
_PLAIN_LOOKUPS = (
    'tags__icontains',
)


# def _normalize_search_terms tách câu tìm kiếm thành các từ khóa: thay các ký tự #,:; bằng khoảng trắng rồi split theo khoảng trắng, bỏ token rỗng.
# vd: 'pháp lý; hợp đồng' -> ['pháp','lý','hợp','đồng'].
def _normalize_search_terms(raw_query):
    normalized = re.sub(r'[#,:;]+', ' ', str(raw_query or '').strip())
    return [term for term in re.split(r'\s+', normalized) if term]


# def _build_search_query dựng điều kiện Q để tìm prompt: khớp cả cụm nguyên câu trên nhiều field (không dấu, icontains) HOẶC khớp khi MỌI từ khóa đều xuất hiện (AND từng từ) — vừa ưu tiên cụm vừa cho phép khớp rời.
# vd: 'hop dong thue' -> khớp prompt chứa nguyên cụm, hoặc chứa đủ cả 'hop','dong','thue'.
def _build_search_query(raw_query):
    raw = str(raw_query or '').strip()
    if not raw:
        return Q()

    # def _value_query dựng Q khớp 1 giá trị trên toàn bộ field tìm kiếm (title/nội dung/category/group/owner... dạng unaccent icontains) cộng field tags.
    # vd: 'thue' -> Q tìm 'thue' trong title, nội dung, tên owner...
    def _value_query(value):
        query = Q()
        for field in _UNACCENT_FIELDS:
            query |= Q(**{f'{field}__unaccent__icontains': value})
        for lookup in _PLAIN_LOOKUPS:
            query |= Q(**{lookup: value})
        return query

    combined = _value_query(raw)
    terms = _normalize_search_terms(raw)
    if len(terms) <= 1:
        return combined

    token_query = Q()
    for term in terms:
        term_query = _value_query(term)
        token_query = term_query if not token_query.children else token_query & term_query
    return combined | token_query


# def _truncate_snippet rút gọn đoạn xem trước về tối đa limit ký tự (gộp khoảng trắng thừa), thêm '...' nếu vượt.
# vd: đoạn 500 ký tự, limit=200 -> ~197 ký tự + '...'.
def _truncate_snippet(value, limit=200):
    text = ' '.join(str(value or '').split())
    if len(text) <= limit:
        return text
    return f'{text[: limit - 3].rstrip()}...'


# def _prompt_snippet chọn đoạn xem trước cho 1 prompt: ưu tiên văn bản gốc -> rules_content -> system_content -> tags (lấy cái đầu tiên có nội dung).
# vd: prompt có rules_content -> snippet lấy từ rules_content.
def _prompt_snippet(prompt):
    candidates = (
        prompt.original_raw_text,
        prompt.rules_content,
        prompt.system_content,
        prompt.tags,
    )
    for candidate in candidates:
        snippet = _truncate_snippet(candidate)
        if snippet:
            return snippet
    return ''


# def search_prompts tìm prompt theo từ khóa trong phạm vi user được phép xem (get_accessible_prompts), trả tối đa limit kết quả gọn {id,title,snippet,deeplink,updated_at} cho ô tìm kiếm tổng; yêu cầu query >= 2 ký tự.
# vd: search_prompts(user,'hop dong',5) -> tối đa 5 prompt liên quan mà user được xem.
def search_prompts(user, q: str, limit: int = 5) -> list[dict]:
    query = str(q or '').strip()
    if len(query) < 2:
        return []

    queryset = (
        get_accessible_prompts(user)
        .filter(_build_search_query(query))
        .defer('usage_scope')
        .select_related('owner', 'category', 'group')
        .distinct()
        .order_by('-updated_at')[: max(1, limit)]
    )
    return [
        {
            'id': prompt.id,
            'type': 'prompt',
            'title': prompt.title,
            'snippet': _prompt_snippet(prompt),
            'deeplink': f'/prompts/{prompt.id}/edit',
            'updated_at': prompt.updated_at,
        }
        for prompt in queryset
    ]
