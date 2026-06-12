import re

from django.db.models import Q

from accounts.permissions import get_accessible_documents
from accounts.record_codes import DOCUMENT_RECORD_PREFIX, parse_record_code

_UNACCENT_FIELDS = (
    'title',
    'doc_number',
    'notes',
    'template__title',
    'department__name',
    'department__code',
    'category__name',
    'group__name',
    'owner__username',
    'owner__first_name',
    'owner__last_name',
)
_PLAIN_LOOKUPS = (
    'tags__icontains',
)


# def _normalize_search_terms tách câu tìm kiếm văn bản thành các từ khóa (thay #,:; bằng khoảng trắng, bỏ token rỗng).
# vd: 'hop dong; thue' -> ['hop','dong','thue'].
def _normalize_search_terms(raw_query):
    normalized = re.sub(r'[#,:;]+', ' ', str(raw_query or '').strip())
    return [term for term in re.split(r'\s+', normalized) if term]


# def _build_search_query dựng Q tìm văn bản: khớp cả cụm (nhiều field không dấu) HOẶC khớp đủ mọi từ khóa.
# vd: 'hop dong' -> văn bản chứa nguyên cụm hoặc đủ cả 'hop','dong'.
def _build_search_query(raw_query):
    raw = str(raw_query or '').strip()
    if not raw:
        return Q()

    # def _value_query dựng Q khớp 1 giá trị trên các field tìm kiếm của văn bản (title/nội dung/owner/phòng ban...) cộng tags.
    # vd: 'thue' -> tìm trong title, nội dung, tên owner...
    def _value_query(value):
        query = Q()
        for field in _UNACCENT_FIELDS:
            query |= Q(**{f'{field}__unaccent__icontains': value})
        for lookup in _PLAIN_LOOKUPS:
            query |= Q(**{lookup: value})
        return query

    combined = _value_query(raw)
    record_id = parse_record_code(raw, DOCUMENT_RECORD_PREFIX)
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
# vd: nội dung 500 ký tự -> ~197 ký tự + '...'.
def _truncate_snippet(value, limit=200):
    text = _strip_markup(value)
    if len(text) <= limit:
        return text
    return f'{text[: limit - 3].rstrip()}...'


# def _document_snippet chọn đoạn xem trước cho 1 văn bản (ưu tiên nội dung / ghi chú / tags).
# vd: văn bản có content -> snippet lấy từ content.
def _document_snippet(document):
    candidates = (
        document.notes,
        document.content,
        document.doc_number,
        getattr(getattr(document, 'template', None), 'title', ''),
        _join_tags(document.tags),
    )
    for candidate in candidates:
        snippet = _truncate_snippet(candidate)
        if snippet:
            return snippet
    return ''


# def search_documents tìm văn bản theo từ khóa trong phạm vi user được phép xem (get_accessible_documents), trả tối đa limit kết quả gọn {id, record_code, title, snippet, deeplink, updated_at} cho ô tìm kiếm tổng; yêu cầu query >= 2 ký tự.
# vd: search_documents(user,'hop dong',5) -> tối đa 5 văn bản liên quan user được xem.
def search_documents(user, q: str, limit: int = 5) -> list[dict]:
    query = str(q or '').strip()
    if len(query) < 2:
        return []

    queryset = (
        get_accessible_documents(user)
        .filter(is_archived=False)
        .filter(_build_search_query(query))
        .select_related('owner', 'template', 'department', 'category', 'group')
        .distinct()
        .order_by('-updated_at')[: max(1, limit)]
    )
    return [
        {
            'id': document.id,
            'record_code': document.record_code,
            'type': 'document',
            'title': document.title,
            'snippet': _document_snippet(document),
            'deeplink': f'/documents/{document.id}',
            'updated_at': document.updated_at,
        }
        for document in queryset
    ]
