import re

from django.db.models import Q

from accounts.permissions import get_accessible_templates
from accounts.record_codes import TEMPLATE_RECORD_PREFIX, parse_record_code

_UNACCENT_FIELDS = (
    'title',
    'description',
    'notes',
    'content',
    'category__name',
    'department__name',
    'department__code',
    'group__name',
    'owner__username',
    'owner__first_name',
    'owner__last_name',
)
_PLAIN_LOOKUPS = (
    'tags__icontains',
)


# def _normalize_search_terms tách câu tìm kiếm mẫu thành các từ khóa (thay #,:; bằng khoảng trắng, bỏ token rỗng).
# vd: 'hop dong; thue' -> ['hop','dong','thue'].
def _normalize_search_terms(raw_query):
    normalized = re.sub(r'[#,:;]+', ' ', str(raw_query or '').strip())
    return [term for term in re.split(r'\s+', normalized) if term]


# def _build_search_query dựng Q tìm mẫu: khớp cả cụm (nhiều field không dấu) HOẶC khớp đủ mọi từ khóa; thêm khớp theo mã record nếu nhập đúng dạng mã.
# vd: nhập 'MAU-000005' -> khớp pk=5; 'hop dong' -> khớp mẫu chứa cụm hoặc đủ 2 từ.
def _build_search_query(raw_query):
    raw = str(raw_query or '').strip()
    if not raw:
        return Q()

    # def _value_query dựng Q khớp 1 giá trị trên toàn bộ field tìm kiếm (title/description/nội dung/category/department/owner...) cộng tags.
    # vd: 'thue' -> tìm trong title, mô tả, tên owner, phòng ban...
    def _value_query(value):
        query = Q()
        for field in _UNACCENT_FIELDS:
            query |= Q(**{f'{field}__unaccent__icontains': value})
        for lookup in _PLAIN_LOOKUPS:
            query |= Q(**{lookup: value})
        return query

    combined = _value_query(raw)
    record_id = parse_record_code(raw, TEMPLATE_RECORD_PREFIX)
    if record_id is not None:
        combined |= Q(pk=record_id)
    terms = _normalize_search_terms(raw)
    if len(terms) <= 1:
        return combined

    token_query = Q()
    for term in terms:
        term_query = _value_query(term)
        token_query = term_query if not token_query.children else token_query & term_query
    return combined | token_query


# def _strip_markup bỏ thẻ HTML và gộp khoảng trắng để lấy text thuần cho snippet.
# vd: '<p>Hợp đồng</p>' -> 'Hợp đồng'.
def _strip_markup(value):
    text = re.sub(r'<[^>]+>', ' ', str(value or ''))
    return ' '.join(text.split())


# def _join_tags nối danh sách tag thành chuỗi 'a, b, c' (bỏ tag rỗng).
# vd: ['a','',' b'] -> 'a, b'.
def _join_tags(tags):
    if not tags:
        return ''
    return ', '.join(str(tag).strip() for tag in tags if str(tag).strip())


# def _truncate_snippet rút gọn snippet về tối đa limit ký tự (sau khi bỏ HTML), thêm '...' nếu vượt.
# vd: nội dung dài 500 ký tự -> ~197 ký tự + '...'.
def _truncate_snippet(value, limit=200):
    text = _strip_markup(value)
    if len(text) <= limit:
        return text
    return f'{text[: limit - 3].rstrip()}...'


# def _template_snippet chọn đoạn xem trước cho 1 mẫu: ưu tiên description -> notes -> content -> tags (lấy cái đầu tiên có nội dung).
# vd: mẫu có description -> snippet lấy từ description.
def _template_snippet(template):
    candidates = (
        template.description,
        template.notes,
        template.content,
        _join_tags(template.tags),
    )
    for candidate in candidates:
        snippet = _truncate_snippet(candidate)
        if snippet:
            return snippet
    return ''


# def search_templates tìm mẫu theo từ khóa trong phạm vi user được phép xem (get_accessible_templates), trả tối đa limit kết quả gọn {id, record_code, title, snippet, deeplink, updated_at} cho ô tìm kiếm tổng; yêu cầu query >= 2 ký tự.
# vd: search_templates(user,'don xin nghi',5) -> tối đa 5 mẫu liên quan user được xem.
def search_templates(user, q: str, limit: int = 5) -> list[dict]:
    query = str(q or '').strip()
    if len(query) < 2:
        return []

    queryset = (
        get_accessible_templates(user)
        .filter(_build_search_query(query))
        .select_related('owner', 'category', 'department', 'group')
        .distinct()
        .order_by('-updated_at')[: max(1, limit)]
    )
    return [
        {
            'id': template.id,
            'record_code': template.record_code,
            'type': 'template',
            'title': template.title,
            'snippet': _template_snippet(template),
            'deeplink': f'/templates/{template.id}',
            'updated_at': template.updated_at,
        }
        for template in queryset
    ]
