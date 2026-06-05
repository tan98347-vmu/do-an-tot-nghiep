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


def _truncate_snippet(value, limit=200):
    text = ' '.join(str(value or '').split())
    if len(text) <= limit:
        return text
    return f'{text[: limit - 3].rstrip()}...'


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
