import re

from django.db.models import Q

from accounts.permissions import get_accessible_templates

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


def _normalize_search_terms(raw_query):
    normalized = re.sub(r'[#,:;]+', ' ', str(raw_query or '').strip())
    return [term for term in re.split(r'\s+', normalized) if term]


def _build_search_query(raw_query):
    raw = str(raw_query or '').strip()
    if not raw:
        return Q()

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


def _strip_markup(value):
    text = re.sub(r'<[^>]+>', ' ', str(value or ''))
    return ' '.join(text.split())


def _join_tags(tags):
    if not tags:
        return ''
    return ', '.join(str(tag).strip() for tag in tags if str(tag).strip())


def _truncate_snippet(value, limit=200):
    text = _strip_markup(value)
    if len(text) <= limit:
        return text
    return f'{text[: limit - 3].rstrip()}...'


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
            'type': 'template',
            'title': template.title,
            'snippet': _template_snippet(template),
            'deeplink': f'/templates/{template.id}',
            'updated_at': template.updated_at,
        }
        for template in queryset
    ]
