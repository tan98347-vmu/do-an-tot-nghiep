from __future__ import annotations

from datetime import date
from typing import Any

from django.db.models import Q
from rest_framework.exceptions import ValidationError

from accounts.models import UserGroupMembership
from accounts.permissions import get_accessible_prompts
from prompts.models import (
    PROMPT_STATUS_PENDING,
    PROMPT_STATUS_PENDING_LEADER,
    PROMPT_STATUS_CHOICES,
    Prompt,
    USAGE_SCOPES,
)


SORT_OPTIONS = {
    'updated_desc': ('-updated_at', '-id'),
    'updated_asc': ('updated_at', 'id'),
    'created_desc': ('-created_at', '-id'),
    'created_asc': ('created_at', 'id'),
    'title_asc': ('title', 'id'),
    'title_desc': ('-title', '-id'),
    'usage_desc': ('-usage_count', '-updated_at', '-id'),
}

PROMPT_STATUS_VALUES = {key for key, _ in PROMPT_STATUS_CHOICES}
PROMPT_VISIBILITY_VALUES = {Prompt.VISIBILITY_PRIVATE, Prompt.VISIBILITY_GROUP, Prompt.VISIBILITY_PUBLIC}
PROMPT_SOURCE_VALUES = {Prompt.SOURCE_CURATED, Prompt.SOURCE_USER_INLINE, Prompt.SOURCE_IMPORTED}


# def _as_list lấy giá trị filter dạng danh sách từ query params (hỗ trợ getlist hoặc tách theo dấu phẩy), bỏ phần tử rỗng.
# vd: ?scope=a,b&scope=c -> ['a','b','c'].
def _as_list(params: Any, key: str) -> list[str]:
    if hasattr(params, 'getlist'):
        values = params.getlist(key)
    else:
        raw = params.get(key, [])
        values = raw if isinstance(raw, list) else [raw]
    normalized: list[str] = []
    for value in values:
        for part in str(value or '').split(','):
            cleaned = part.strip()
            if cleaned:
                normalized.append(cleaned)
    return normalized


# def _parse_date_param đọc tham số ngày dạng YYYY-MM-DD từ query; rỗng -> None; sai định dạng -> ValidationError.
# vd: created_from='2026-06-01' -> date(2026,6,1).
def _parse_date_param(params: Any, key: str) -> date | None:
    raw = str(params.get(key, '') or '').strip()
    if not raw:
        return None
    try:
        return date.fromisoformat(raw)
    except ValueError as exc:
        raise ValidationError({key: 'Gia tri phai theo dinh dang YYYY-MM-DD.'}) from exc


# def _parse_flag đọc tham số cờ boolean từ query (nhận 1/true/yes/on là True).
# vd: review_mode='true' -> True.
def _parse_flag(params: Any, key: str) -> bool:
    return str(params.get(key, '') or '').strip().lower() in {'1', 'true', 'yes', 'on'}


# def _validated_scope_filters lấy và kiểm tra danh sách scope filter; scope lạ (không thuộc USAGE_SCOPES) -> ValidationError.
# vd: scope='template_fill' hợp lệ; scope='abc' -> báo lỗi 'Scope khong hop le'.
def _validated_scope_filters(params: Any) -> list[str]:
    scopes = _as_list(params, 'scope')
    invalid_scopes = [scope for scope in scopes if scope not in USAGE_SCOPES]
    if invalid_scopes:
        raise ValidationError(
            {
                'scope': (
                    f"Scope khong hop le: {', '.join(invalid_scopes)}. "
                    f"Cho phep: {', '.join(USAGE_SCOPES)}"
                )
            }
        )
    return scopes


# def _reviewable_prompt_queryset trả các prompt CẦN user này duyệt: admin -> mọi prompt pending/pending_leader; trưởng nhóm -> prompt pending_leader thuộc nhóm mình; người khác -> rỗng.
# vd: trưởng nhóm 'Phòng A' -> các prompt của nhóm A đang chờ duyệt.
def _reviewable_prompt_queryset(user) -> Prompt.objects.none().__class__:
    queryset = Prompt.objects.none()
    if user.is_superuser or user.is_staff:
        queryset = Prompt.objects.filter(
            Q(status=PROMPT_STATUS_PENDING) | Q(status=PROMPT_STATUS_PENDING_LEADER)
        )
    else:
        leader_groups = list(
            UserGroupMembership.objects.filter(user=user, role='leader').values_list('group_id', flat=True)
        )
        if leader_groups:
            queryset = Prompt.objects.filter(
                status=PROMPT_STATUS_PENDING_LEADER,
                group_id__in=leader_groups,
            )
    return queryset


# def build_prompt_list_queryset dựng queryset danh sách prompt theo nhiều bộ lọc từ query params: review_mode (hàng chờ duyệt) hoặc phạm vi user được xem; lọc theo scope / q (tìm nhiều field) / status / visibility / owner(mine|shared) / shared_with_me / source / category / group / khoảng ngày, rồi sắp xếp theo sort. Mỗi tham số sai -> ValidationError.
# vd: ?owner=mine&status=approved&sort=usage_desc -> prompt của tôi đã duyệt, sắp theo lượt dùng giảm dần.
def build_prompt_list_queryset(user, params: Any):
    review_mode = _parse_flag(params, 'review_mode')
    queryset = _reviewable_prompt_queryset(user) if review_mode else get_accessible_prompts(user)

    scopes = _validated_scope_filters(params)
    if scopes:
        queryset = queryset.filter(usage_scope__overlap=scopes)

    query = str(params.get('q', '') or '').strip()
    if query:
        queryset = queryset.filter(
            Q(title__icontains=query)
            | Q(system_content__icontains=query)
            | Q(rules_content__icontains=query)
            | Q(tags__icontains=query)
            | Q(source__icontains=query)
            | Q(owner__username__icontains=query)
            | Q(owner__first_name__icontains=query)
            | Q(owner__last_name__icontains=query)
            | Q(category__name__icontains=query)
            | Q(group__name__icontains=query)
        )

    status_filter = str(params.get('status', '') or '').strip()
    if status_filter:
        statuses = _as_list(params, 'status')
        invalid_statuses = [status for status in statuses if status not in PROMPT_STATUS_VALUES]
        if invalid_statuses:
            raise ValidationError({'status': f'Status khong hop le: {", ".join(invalid_statuses)}'})
        queryset = queryset.filter(status__in=statuses)

    visibility = str(params.get('visibility', '') or '').strip()
    if visibility:
        if visibility not in PROMPT_VISIBILITY_VALUES:
            raise ValidationError({'visibility': 'visibility khong hop le.'})
        queryset = queryset.filter(visibility=visibility)

    owner_filter = str(params.get('owner', '') or '').strip()
    if owner_filter and owner_filter not in {'all', 'mine', 'shared'}:
        raise ValidationError({'owner': 'owner chi chap nhan "mine", "shared" hoac "all".'})
    if owner_filter == 'mine':
        queryset = queryset.filter(owner=user)
    elif owner_filter == 'shared':
        queryset = queryset.exclude(owner=user)

    if _parse_flag(params, 'shared_with_me'):
        queryset = queryset.exclude(owner=user).filter(audience_members__user=user)

    source = str(params.get('source', '') or '').strip()
    if source:
        if source not in PROMPT_SOURCE_VALUES:
            raise ValidationError({'source': 'source khong hop le.'})
        queryset = queryset.filter(source=source)

    category_filter = str(params.get('category', '') or '').strip()
    if category_filter:
        if category_filter.isdigit():
            queryset = queryset.filter(category_id=int(category_filter))
        else:
            queryset = queryset.filter(category__name__icontains=category_filter)

    group_filter = str(params.get('group_filter', '') or params.get('group_name', '') or '').strip()
    if group_filter:
        if group_filter.isdigit():
            queryset = queryset.filter(group_id=int(group_filter))
        else:
            queryset = queryset.filter(group__name__icontains=group_filter)

    created_from = _parse_date_param(params, 'created_from')
    created_to = _parse_date_param(params, 'created_to')
    updated_from = _parse_date_param(params, 'updated_from')
    updated_to = _parse_date_param(params, 'updated_to')
    if created_from:
        queryset = queryset.filter(created_at__date__gte=created_from)
    if created_to:
        queryset = queryset.filter(created_at__date__lte=created_to)
    if updated_from:
        queryset = queryset.filter(updated_at__date__gte=updated_from)
    if updated_to:
        queryset = queryset.filter(updated_at__date__lte=updated_to)

    sort_key = str(params.get('sort', 'updated_desc') or 'updated_desc').strip()
    if sort_key not in SORT_OPTIONS:
        raise ValidationError({'sort': 'sort khong hop le.'})

    return queryset.select_related('owner', 'category', 'group').distinct().order_by(*SORT_OPTIONS[sort_key])
