"""
Thuoc chuc nang nao: Tom tat van ban.
Vai tro backend: File nay cung cap discovery, live suggestions, preview prompt va generate tom tat cho route `/summaries` cua Flutter.
Vai tro cua no trong frontend: Cac man `/summaries` va `/summaries/:documentId` goi truc tiep cac endpoint trong file nay de tim van ban, xem preview prompt va tao ban tom tat.
Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/documents.py`, `api/security/prompt_guard.py`, `documents.ai_summary`, `accounts.permissions`.
Tac dung: Tach rieng nghiep vu tom tat van ban thanh mot contract on dinh, khong chen logic moi vao luong document list cu.
"""

import json
from collections import OrderedDict
from datetime import datetime
from types import SimpleNamespace

from django.db.models import F
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from accounts.permissions import (
    can_edit_document,
    get_accessible_documents,
    get_accessible_prompts,
)
from accounts.runtime_guard import CompanyRuntimeGuard
from accounts.tenancy import resolve_ai_config
from api.security.prompt_guard import (
    hash_rules,
    run_full_pipeline,
    sign_scoped_preview_token,
    verify_scoped_preview_token,
    prompt_check_expected_payload,
    verify_prompt_check_token,
    wrap_user_rules,
)
from api.serializers.document_summaries import (
    DocumentSummaryDownloadQuerySerializer,
    DocumentSummaryRequestSerializer,
)
from documents.ai_summary import (
    build_document_summary_preview,
    build_summary_options_hash,
    build_summary_revision_token,
    normalize_summary_options,
    summarize_document_content,
)
from documents.models import (
    DOC_STATUS_CHOICES,
    Document,
    DocumentFavorite,
    SHARE_ACTIVE,
    SHARE_PENDING_ADMIN,
    SHARE_PENDING_LEADER,
    SHARE_REJECTED,
    SOURCE_GENERATED,
    SOURCE_TYPE_CHOICES,
    SOURCE_UPLOADED,
    VIS_GROUP,
    VIS_PRIVATE,
    VIS_PUBLIC,
)
from documents.runtime_helpers import safe_attachment_filename
from documents.summary_exporters import export_summary_docx, export_summary_md
from prompts.models import Prompt

from ..serializers.documents import DocumentListSerializer
from .documents import _build_document_search_query

_SUMMARY_PREVIEW_SALT = 'document_summary.preview.v1'
_SUMMARY_EXPORT_KEY = 'summary_export'


# Là gì: `_coerce_tag_list` là helper nội bộ của module `document_summaries.py`, phục vụ nhóm tạo, xem và quản lý bản tóm tắt văn bản bằng AI.
# Chức năng backend: Hàm truy vấn và trả về danh sách dữ liệu phù hợp; đầu vào được kiểm tra hoặc chuẩn hóa trước khi tạo kết quả.
# Vai trò với UI: Flutter không gọi trực tiếp hàm này; các endpoint cùng module dùng kết quả của nó để phục vụ không gian làm việc tóm tắt văn bản.
# Mối liên hệ: Hàm phối hợp với `raw_value.strip`, `json.loads`, `item.strip` và trả dữ liệu về cho lớp gọi kế tiếp trong cùng luồng.
# Bản chất và tác dụng: hàm hỗ trợ tái sử dụng trong module; chủ yếu đọc, kiểm tra hoặc biến đổi dữ liệu.
def _coerce_tag_list(raw_value):
    if raw_value in (None, '', []):
        return []
    if isinstance(raw_value, str):
        raw_text = raw_value.strip()
        if not raw_text:
            return []
        try:
            return _coerce_tag_list(json.loads(raw_text))
        except Exception:
            return [item.strip() for item in raw_text.split(',') if item.strip()]
    if isinstance(raw_value, dict):
        ordered_items = sorted(raw_value.items(), key=lambda item: str(item[0]))
        flattened = []
        for _, item_value in ordered_items:
            flattened.extend(_coerce_tag_list(item_value))
        return flattened
    if isinstance(raw_value, (list, tuple, set)):
        flattened = []
        for item in raw_value:
            flattened.extend(_coerce_tag_list(item))
        return flattened
    return [str(raw_value)]


# Là gì: `_document_summary_queryset` là helper nội bộ của module `document_summaries.py`, phục vụ nhóm tạo, xem và quản lý bản tóm tắt văn bản bằng AI.
# Chức năng backend: Hàm tạo hoặc xử lý nội dung tóm tắt; đầu vào được kiểm tra hoặc chuẩn hóa trước khi tạo kết quả.
# Vai trò với UI: Flutter không gọi trực tiếp hàm này; các endpoint cùng module dùng kết quả của nó để phục vụ không gian làm việc tóm tắt văn bản.
# Mối liên hệ: Hàm phối hợp với `str.strip.lower`, `str.strip`, `get_accessible_documents.select_related.order_by` và trả dữ liệu về cho lớp gọi kế tiếp trong cùng luồng.
# Bản chất và tác dụng: hàm hỗ trợ tái sử dụng trong module; chủ yếu đọc, kiểm tra hoặc biến đổi dữ liệu.
def _document_summary_queryset(user, scope: str):
    scope_value = str(scope or 'all').strip().lower()
    # Chi lay van ban user CO QUYEN XEM (owner + ShareGrant active + mailbox/ky so).
    # KHONG bao gom van ban dang "cho duyet" (reviewable) vi do la quyen DUYET, chua
    # phai quyen xem — dung nghiep vu: picker tom tat chi hien thu user duoc xem.
    qs = get_accessible_documents(user).select_related(
        'owner',
        'template',
        'department',
        'category',
        'group',
    ).order_by('-updated_at')

    if scope_value in {'', 'all'}:
        return qs.filter(is_archived=False), 'all'
    if scope_value == 'private':
        return qs.filter(owner=user, is_archived=False), scope_value
    if scope_value == 'group':
        return qs.filter(visibility=VIS_GROUP, is_archived=False), scope_value
    if scope_value == 'public':
        return qs.filter(visibility=VIS_PUBLIC, is_archived=False), scope_value
    if scope_value == 'favorite':
        fav_ids = DocumentFavorite.objects.filter(user=user).values_list('document_id', flat=True)
        return qs.filter(id__in=fav_ids, is_archived=False), scope_value
    if scope_value == 'archived':
        return qs.filter(owner=user, is_archived=True), scope_value
    return qs.filter(is_archived=False), 'all'


# Là gì: `_apply_discovery_filters` là helper nội bộ của module `document_summaries.py`, phục vụ nhóm tạo, xem và quản lý bản tóm tắt văn bản bằng AI.
# Chức năng backend: Hàm xử lý phần việc `apply discovery filters` theo dữ liệu và ngữ cảnh được truyền vào; đầu vào được kiểm tra hoặc chuẩn hóa trước khi tạo kết quả.
# Vai trò với UI: Flutter không gọi trực tiếp hàm này; các endpoint cùng module dùng kết quả của nó để phục vụ không gian làm việc tóm tắt văn bản.
# Mối liên hệ: Hàm phối hợp với `str.strip`, `request.GET.get`, `str.strip.lower` và trả dữ liệu về cho lớp gọi kế tiếp trong cùng luồng.
# Bản chất và tác dụng: hàm hỗ trợ tái sử dụng trong module; chủ yếu đọc, kiểm tra hoặc biến đổi dữ liệu.
def _apply_discovery_filters(qs, request):
    base_qs = qs
    q = str(request.GET.get('q', '') or '').strip()
    status_filter = str(request.GET.get('status', '') or '').strip()
    visibility_filter = str(request.GET.get('visibility', '') or '').strip()
    share_status_filter = str(request.GET.get('share_status', '') or '').strip()
    source_type_filter = str(request.GET.get('source_type', '') or '').strip()
    tag_filter = str(request.GET.get('tag', '') or '').strip()
    doc_number_filter = str(request.GET.get('doc_number', '') or '').strip()
    category_id = str(request.GET.get('category_id', '') or '').strip()
    group_id = str(request.GET.get('group_id', '') or '').strip()
    signing_status = str(request.GET.get('signing_status', '') or '').strip()
    editable_only = str(request.GET.get('editable_only', '') or '').strip().lower() in {'1', 'true', 'yes'}

    if q:
        qs = qs.filter(_build_document_search_query(q))
        tag_match_ids = [
            document.pk
            for document in base_qs
            if any(q.casefold() in tag.casefold() for tag in _coerce_tag_list(document.tags))
        ]
        if tag_match_ids:
            qs = (qs | base_qs.filter(pk__in=tag_match_ids)).distinct()
    if status_filter:
        qs = qs.filter(status=status_filter)
    if visibility_filter:
        qs = qs.filter(visibility=visibility_filter)
    if share_status_filter:
        qs = qs.filter(share_status=share_status_filter)
    if source_type_filter:
        qs = qs.filter(source_type=source_type_filter)
    if tag_filter:
        tag_match_ids = [
            document.pk
            for document in qs
            if any(tag_filter.casefold() in tag.casefold() for tag in _coerce_tag_list(document.tags))
        ]
        qs = qs.filter(pk__in=tag_match_ids)
    if doc_number_filter:
        qs = qs.filter(doc_number__icontains=doc_number_filter)
    if category_id.isdigit():
        qs = qs.filter(category_id=int(category_id))
    if group_id.isdigit():
        qs = qs.filter(group_id=int(group_id))
    if signing_status == 'signed':
        qs = qs.filter(
            signed_pdf_records__source_version_number=F('version_number'),
            signed_pdf_records__verification_status='safe',
        ).distinct()
    elif signing_status == 'unsigned':
        qs = qs.exclude(
            signed_pdf_records__source_version_number=F('version_number'),
            signed_pdf_records__verification_status='safe',
        ).distinct()
    if editable_only:
        candidate_ids = [
            document.pk
            for document in qs
            if can_edit_document(request.user, document)
        ]
        qs = qs.filter(pk__in=candidate_ids)
    return qs


# Là gì: `_matched_field` là helper nội bộ của module `document_summaries.py`, phục vụ nhóm tạo, xem và quản lý bản tóm tắt văn bản bằng AI.
# Chức năng backend: Hàm xử lý phần việc `matched field` theo dữ liệu và ngữ cảnh được truyền vào; đầu vào được kiểm tra hoặc chuẩn hóa trước khi tạo kết quả.
# Vai trò với UI: Flutter không gọi trực tiếp hàm này; các endpoint cùng module dùng kết quả của nó để phục vụ không gian làm việc tóm tắt văn bản.
# Mối liên hệ: Hàm phối hợp với `query.casefold`, `join`, `document.owner.get_full_name` và trả dữ liệu về cho lớp gọi kế tiếp trong cùng luồng.
# Bản chất và tác dụng: hàm hỗ trợ tái sử dụng trong module; chủ yếu đọc, kiểm tra hoặc biến đổi dữ liệu.
def _matched_field(document, query: str) -> str:
    needle = query.casefold()
    field_checks = (
        ('title', document.title or ''),
        ('doc_number', document.doc_number or ''),
        ('owner', document.owner.get_full_name() or document.owner.username or ''),
        ('category', document.category.name if document.category else ''),
        ('group', document.group.name if document.group else ''),
        ('department', document.department.name if document.department else ''),
        ('template', document.template.title if document.template else ''),
        ('tag', ' '.join(_coerce_tag_list(document.tags))),
    )
    for name, value in field_checks:
        if needle in str(value).casefold():
            return name
    return 'title'


# Là gì: `_document_caption` là helper nội bộ của module `document_summaries.py`, phục vụ nhóm tạo, xem và quản lý bản tóm tắt văn bản bằng AI.
# Chức năng backend: Hàm xử lý phần việc `document caption` theo dữ liệu và ngữ cảnh được truyền vào; đầu vào được kiểm tra hoặc chuẩn hóa trước khi tạo kết quả.
# Vai trò với UI: Flutter không gọi trực tiếp hàm này; các endpoint cùng module dùng kết quả của nó để phục vụ không gian làm việc tóm tắt văn bản.
# Mối liên hệ: Hàm phối hợp với `parts.append`, `_coerce_tag_list`, `join` và trả dữ liệu về cho lớp gọi kế tiếp trong cùng luồng.
# Bản chất và tác dụng: hàm hỗ trợ tái sử dụng trong module; chủ yếu đọc, kiểm tra hoặc biến đổi dữ liệu.
def _document_caption(document) -> str:
    parts = []
    if document.doc_number:
        parts.append(document.doc_number)
    if document.category:
        parts.append(document.category.name)
    if document.group:
        parts.append(document.group.name)
    tag_list = _coerce_tag_list(document.tags)
    if tag_list:
        parts.append(', '.join(tag_list[:3]))
    return ' • '.join(part for part in parts if part)


# Là gì: `_collect_tag_suggestions` là helper nội bộ của module `document_summaries.py`, phục vụ nhóm tạo, xem và quản lý bản tóm tắt văn bản bằng AI.
# Chức năng backend: Hàm xử lý phần việc `collect tag suggestions` theo dữ liệu và ngữ cảnh được truyền vào; đầu vào được kiểm tra hoặc chuẩn hóa trước khi tạo kết quả.
# Vai trò với UI: Flutter không gọi trực tiếp hàm này; các endpoint cùng module dùng kết quả của nó để phục vụ không gian làm việc tóm tắt văn bản.
# Mối liên hệ: Hàm phối hợp với `query.casefold`, `_coerce_tag_list`, `tag.casefold` và trả dữ liệu về cho lớp gọi kế tiếp trong cùng luồng.
# Bản chất và tác dụng: hàm hỗ trợ tái sử dụng trong module; chủ yếu đọc, kiểm tra hoặc biến đổi dữ liệu.
def _collect_tag_suggestions(documents, query: str):
    needle = query.casefold()
    suggestions = []
    seen = set()
    for document in documents:
        for tag in _coerce_tag_list(document.tags):
            normalized = tag.casefold()
            if needle not in normalized or normalized in seen:
                continue
            seen.add(normalized)
            suggestions.append(
                {
                    'type': 'tag',
                    'value': tag,
                    'label': f'#{tag}',
                    'caption': 'Tag',
                    'matched_field': 'tag',
                }
            )
            if len(suggestions) >= 6:
                return suggestions
    return suggestions


# Là gì: `_build_discovery_facets` là helper nội bộ của module `document_summaries.py`, phục vụ nhóm tạo, xem và quản lý bản tóm tắt văn bản bằng AI.
# Chức năng backend: Hàm tổng hợp dữ liệu đầu vào thành cấu trúc phục vụ bước tiếp theo; đầu vào được kiểm tra hoặc chuẩn hóa trước khi tạo kết quả.
# Vai trò với UI: Flutter không gọi trực tiếp hàm này; các endpoint cùng module dùng kết quả của nó để phục vụ không gian làm việc tóm tắt văn bản.
# Mối liên hệ: Hàm phối hợp với `qs.exclude.values.distinct.order_by`, `qs.exclude.values.distinct`, `qs.exclude.values` và trả dữ liệu về cho lớp gọi kế tiếp trong cùng luồng.
# Bản chất và tác dụng: hàm hỗ trợ tái sử dụng trong module; chủ yếu đọc, kiểm tra hoặc biến đổi dữ liệu.
def _build_discovery_facets(qs):
    category_rows = qs.exclude(category__isnull=True).values(
        'category_id',
        'category__name',
    ).distinct().order_by('category__name')[:100]
    group_rows = qs.exclude(group__isnull=True).values(
        'group_id',
        'group__name',
    ).distinct().order_by('group__name')[:100]

    tag_values = OrderedDict()
    for raw_tags in qs.values_list('tags', flat=True)[:250]:
        for tag in _coerce_tag_list(raw_tags):
            key = tag.casefold()
            if key not in tag_values:
                tag_values[key] = tag
            if len(tag_values) >= 30:
                break
        if len(tag_values) >= 30:
            break

    return {
        'scopes': [
            {'value': 'all', 'label': 'Tat ca co the truy cap'},
            {'value': 'private', 'label': 'Van ban cua toi'},
            {'value': 'group', 'label': 'Chia se trong nhom'},
            {'value': 'public', 'label': 'Chia se cong khai'},
            {'value': 'favorite', 'label': 'Yeu thich'},
            {'value': 'archived', 'label': 'Da luu tru'},
        ],
        'statuses': [
            {'value': code, 'label': label}
            for code, label in DOC_STATUS_CHOICES
        ],
        'visibilities': [
            {'value': VIS_PRIVATE, 'label': 'Rieng tu'},
            {'value': VIS_GROUP, 'label': 'Nhom'},
            {'value': VIS_PUBLIC, 'label': 'Cong khai'},
        ],
        'share_statuses': [
            {'value': SHARE_ACTIVE, 'label': 'Dang hoat dong'},
            {'value': SHARE_PENDING_LEADER, 'label': 'Cho truong nhom duyet'},
            {'value': SHARE_PENDING_ADMIN, 'label': 'Cho admin duyet'},
            {'value': SHARE_REJECTED, 'label': 'Bi tu choi'},
        ],
        'source_types': [
            {'value': code, 'label': label}
            for code, label in SOURCE_TYPE_CHOICES
        ],
        'signing_statuses': [
            {'value': 'signed', 'label': 'Da ky'},
            {'value': 'unsigned', 'label': 'Chua ky'},
        ],
        'categories': [
            {'id': row['category_id'], 'label': row['category__name']}
            for row in category_rows
        ],
        'groups': [
            {'id': row['group_id'], 'label': row['group__name']}
            for row in group_rows
        ],
        'tags': list(tag_values.values()),
    }


# Là gì: `_parse_summary_options_payload` là helper nội bộ của module `document_summaries.py`, phục vụ nhóm tạo, xem và quản lý bản tóm tắt văn bản bằng AI.
# Chức năng backend: Hàm tạo hoặc xử lý nội dung tóm tắt, đồng thời phân tích dữ liệu thô thành cấu trúc có thể sử dụng; đầu vào được kiểm tra hoặc chuẩn hóa trước khi tạo kết quả.
# Vai trò với UI: Flutter không gọi trực tiếp hàm này; các endpoint cùng module dùng kết quả của nó để phục vụ không gian làm việc tóm tắt văn bản.
# Mối liên hệ: Hàm phối hợp với `data.get`, `normalize_summary_options` và trả dữ liệu về cho lớp gọi kế tiếp trong cùng luồng.
# Bản chất và tác dụng: hàm hỗ trợ tái sử dụng trong module; chủ yếu đọc, kiểm tra hoặc biến đổi dữ liệu.
def _parse_summary_options_payload(data):
    raw_options = data.get('options')
    if not isinstance(raw_options, dict):
        raw_options = {
            'length': data.get('length'),
            'language': data.get('language'),
            'style': data.get('style'),
        }
    return normalize_summary_options(raw_options)


# Là gì: `_parse_summary_request` là helper nội bộ của module `document_summaries.py`, phục vụ nhóm tạo, xem và quản lý bản tóm tắt văn bản bằng AI.
# Chức năng backend: Hàm tạo hoặc xử lý nội dung tóm tắt, đồng thời phân tích dữ liệu thô thành cấu trúc có thể sử dụng; đầu vào được kiểm tra hoặc chuẩn hóa trước khi tạo kết quả.
# Vai trò với UI: Flutter không gọi trực tiếp hàm này; các endpoint cùng module dùng kết quả của nó để phục vụ không gian làm việc tóm tắt văn bản.
# Mối liên hệ: Hàm phối hợp với `DocumentSummaryRequestSerializer`, `serializer.is_valid`, `_parse_summary_options_payload` và trả dữ liệu về cho lớp gọi kế tiếp trong cùng luồng.
# Bản chất và tác dụng: hàm hỗ trợ tái sử dụng trong module; chủ yếu đọc, kiểm tra hoặc biến đổi dữ liệu.
def _parse_summary_request(data):
    serializer = DocumentSummaryRequestSerializer(data=data)
    serializer.is_valid(raise_exception=True)
    validated = serializer.validated_data
    return {
        'options': _parse_summary_options_payload(data),
        'user_extra_rules': str(validated.get('user_extra_rules', '') or '').strip(),
        'preview_token': str(validated.get('preview_token', '') or '').strip(),
        'prompt_check_token': str(validated.get('prompt_check_token', '') or '').strip(),
        'prompt_id': validated.get('prompt_id'),
    }


# Là gì: `_prompt_scope_tokens` là helper nội bộ của module `document_summaries.py`, phục vụ nhóm tạo, xem và quản lý bản tóm tắt văn bản bằng AI.
# Chức năng backend: Hàm xử lý phần việc `prompt scope tokens` theo dữ liệu và ngữ cảnh được truyền vào; đầu vào được kiểm tra hoặc chuẩn hóa trước khi tạo kết quả.
# Vai trò với UI: Flutter không gọi trực tiếp hàm này; các endpoint cùng module dùng kết quả của nó để phục vụ không gian làm việc tóm tắt văn bản.
# Mối liên hệ: Hàm phối hợp với `tokens.update`, `str.strip.lower`, `str.strip` và trả dữ liệu về cho lớp gọi kế tiếp trong cùng luồng.
# Bản chất và tác dụng: hàm hỗ trợ tái sử dụng trong module; có side effect ghi cơ sở dữ liệu.
def _prompt_scope_tokens(prompt: Prompt) -> set[str]:
    tokens = set()
    usage_scope = getattr(prompt, 'usage_scope', None)
    if isinstance(usage_scope, (list, tuple, set)):
        tokens.update(
            str(item or '').strip().lower()
            for item in usage_scope
            if str(item or '').strip()
        )
    elif isinstance(usage_scope, str):
        tokens.update(
            token.strip()
            for token in usage_scope.replace(';', ',').split(',')
            if token.strip()
        )

    raw_tags = str(getattr(prompt, 'tags', '') or '').strip().lower()
    for token in raw_tags.replace(';', ',').split(','):
        cleaned = token.strip()
        if not cleaned:
            continue
        tokens.add(cleaned)
        if cleaned.startswith('scope:'):
            tokens.add(cleaned.split(':', 1)[1])
    return tokens


# Là gì: `_prompt_supports_scope` là helper nội bộ của module `document_summaries.py`, phục vụ nhóm tạo, xem và quản lý bản tóm tắt văn bản bằng AI.
# Chức năng backend: Hàm xử lý phần việc `prompt supports scope` theo dữ liệu và ngữ cảnh được truyền vào; đầu vào được kiểm tra hoặc chuẩn hóa trước khi tạo kết quả.
# Vai trò với UI: Flutter không gọi trực tiếp hàm này; các endpoint cùng module dùng kết quả của nó để phục vụ không gian làm việc tóm tắt văn bản.
# Mối liên hệ: Hàm phối hợp với `_prompt_scope_tokens` và trả dữ liệu về cho lớp gọi kế tiếp trong cùng luồng.
# Bản chất và tác dụng: hàm hỗ trợ tái sử dụng trong module; chủ yếu đọc, kiểm tra hoặc biến đổi dữ liệu.
def _prompt_supports_scope(prompt: Prompt, scope: str) -> bool:
    tokens = _prompt_scope_tokens(prompt)
    if not tokens:
        return True
    return scope in tokens or f'scope:{scope}' in tokens


# Là gì: `_resolve_summary_prompt` là helper nội bộ của module `document_summaries.py`, phục vụ nhóm tạo, xem và quản lý bản tóm tắt văn bản bằng AI.
# Chức năng backend: Hàm xác định đối tượng hoặc cấu hình hiệu lực từ ngữ cảnh hiện tại, đồng thời tạo hoặc xử lý nội dung tóm tắt; đầu vào được kiểm tra hoặc chuẩn hóa trước khi tạo kết quả.
# Vai trò với UI: Flutter không gọi trực tiếp hàm này; các endpoint cùng module dùng kết quả của nó để phục vụ không gian làm việc tóm tắt văn bản.
# Mối liên hệ: Hàm phối hợp với `get_accessible_prompts.filter.first`, `get_accessible_prompts.filter`, `get_accessible_prompts` và trả dữ liệu về cho lớp gọi kế tiếp trong cùng luồng.
# Bản chất và tác dụng: hàm hỗ trợ tái sử dụng trong module; chủ yếu đọc, kiểm tra hoặc biến đổi dữ liệu; chuyển kết quả thành HTTP response.
def _resolve_summary_prompt(user, prompt_id):
    if not prompt_id:
        return None, None
    prompt = get_accessible_prompts(user).filter(pk=prompt_id).first()
    if prompt is None:
        return None, Response({'detail': 'prompt_id khong hop le.'}, status=400)
    if not _prompt_supports_scope(prompt, 'summary'):
        return None, Response(
            {'detail': 'prompt_id khong hop le cho scope summary.'},
            status=400,
        )
    return prompt, None


# Là gì: `_compose_summary_rules` là helper nội bộ của module `document_summaries.py`, phục vụ nhóm tạo, xem và quản lý bản tóm tắt văn bản bằng AI.
# Chức năng backend: Hàm tạo hoặc xử lý nội dung tóm tắt; đầu vào được kiểm tra hoặc chuẩn hóa trước khi tạo kết quả.
# Vai trò với UI: Flutter không gọi trực tiếp hàm này; các endpoint cùng module dùng kết quả của nó để phục vụ không gian làm việc tóm tắt văn bản.
# Mối liên hệ: Hàm phối hợp với `str.strip`, `join.strip`, `prompt_parts.append` và trả dữ liệu về cho lớp gọi kế tiếp trong cùng luồng.
# Bản chất và tác dụng: hàm hỗ trợ tái sử dụng trong module; chủ yếu đọc, kiểm tra hoặc biến đổi dữ liệu.
def _compose_summary_rules(prompt, user_extra_rules_raw: str) -> str:
    parts = []
    if prompt is not None:
        prompt_parts = []
        if str(prompt.system_content or '').strip():
            prompt_parts.append(str(prompt.system_content).strip())
        if str(prompt.rules_content or '').strip():
            prompt_parts.append(str(prompt.rules_content).strip())
        prompt_text = '\n\n'.join(prompt_parts).strip()
        if prompt_text:
            parts.append(
                f'Prompt tom tat da chon: {prompt.title}\n'
                f'{prompt_text}'
            )
    if user_extra_rules_raw:
        parts.append(user_extra_rules_raw.strip())
    return '\n\n'.join(part for part in parts if part).strip()


# Là gì: `_selected_prompt_payload` là helper nội bộ của module `document_summaries.py`, phục vụ nhóm tạo, xem và quản lý bản tóm tắt văn bản bằng AI.
# Chức năng backend: Hàm xử lý phần việc `selected prompt payload` theo dữ liệu và ngữ cảnh được truyền vào; đầu vào được kiểm tra hoặc chuẩn hóa trước khi tạo kết quả.
# Vai trò với UI: Flutter không gọi trực tiếp hàm này; các endpoint cùng module dùng kết quả của nó để phục vụ không gian làm việc tóm tắt văn bản.
# Mối liên hệ: Hàm được các endpoint hoặc helper cùng module gọi khi cần cùng quy tắc xử lý.
# Bản chất và tác dụng: hàm hỗ trợ tái sử dụng trong module; chủ yếu đọc, kiểm tra hoặc biến đổi dữ liệu.
def _selected_prompt_payload(prompt):
    if prompt is None:
        return None
    return {
        'id': prompt.pk,
        'title': prompt.title,
    }


# Là gì: `_store_latest_summary_export` là helper nội bộ của module `document_summaries.py`, phục vụ nhóm tạo, xem và quản lý bản tóm tắt văn bản bằng AI.
# Chức năng backend: Hàm kết xuất dữ liệu thành tệp hoặc định dạng trao đổi, đồng thời tạo hoặc xử lý nội dung tóm tắt; đầu vào được kiểm tra hoặc chuẩn hóa trước khi tạo kết quả.
# Vai trò với UI: Flutter không gọi trực tiếp hàm này; các endpoint cùng module dùng kết quả của nó để phục vụ không gian làm việc tóm tắt văn bản.
# Mối liên hệ: Hàm phối hợp với `str.strip`, `timezone.now.isoformat`, `payload.get` và trả dữ liệu về cho lớp gọi kế tiếp trong cùng luồng.
# Bản chất và tác dụng: hàm hỗ trợ tái sử dụng trong module; có side effect ghi cơ sở dữ liệu.
def _store_latest_summary_export(document, payload, *, user, prompt, user_extra_rules):
    snapshot = dict(document.applied_prompt_snapshot or {})
    summary_snapshot = {
        'status': 'done',
        'summary': str(payload.get('summary', '') or '').strip(),
        'content_md': str(payload.get('summary', '') or '').strip(),
        'summary_revision': str(payload.get('summary_revision', '') or '').strip(),
        'source_kind': str(payload.get('source_kind', '') or '').strip(),
        'source_length': int(payload.get('source_length') or 0),
        'chunk_count': int(payload.get('chunk_count') or 0),
        'applied_options': payload.get('applied_options') or {},
        'model_name': resolve_ai_config(user=user).ai_model,
        'created_at': timezone.now().isoformat(),
        'created_by_id': user.pk,
        'created_by_name': user.get_full_name().strip() or user.username,
        'prompt_id': getattr(prompt, 'pk', None),
        'prompt_title': getattr(prompt, 'title', None),
        'user_extra_rules': user_extra_rules,
    }
    snapshot[_SUMMARY_EXPORT_KEY] = summary_snapshot
    Document.all_objects.filter(pk=document.pk).update(
        applied_prompt_snapshot=snapshot,
    )
    document.applied_prompt_snapshot = snapshot


# Là gì: `_latest_summary_export` là helper nội bộ của module `document_summaries.py`, phục vụ nhóm tạo, xem và quản lý bản tóm tắt văn bản bằng AI.
# Chức năng backend: Hàm kết xuất dữ liệu thành tệp hoặc định dạng trao đổi, đồng thời tạo hoặc xử lý nội dung tóm tắt; đầu vào được kiểm tra hoặc chuẩn hóa trước khi tạo kết quả.
# Vai trò với UI: Flutter không gọi trực tiếp hàm này; các endpoint cùng module dùng kết quả của nó để phục vụ không gian làm việc tóm tắt văn bản.
# Mối liên hệ: Hàm phối hợp với `snapshot.get`, `str.strip`, `summary_snapshot.get` và trả dữ liệu về cho lớp gọi kế tiếp trong cùng luồng.
# Bản chất và tác dụng: hàm hỗ trợ tái sử dụng trong module; chủ yếu đọc, kiểm tra hoặc biến đổi dữ liệu.
def _latest_summary_export(document):
    snapshot = document.applied_prompt_snapshot or {}
    if not isinstance(snapshot, dict):
        return None
    summary_snapshot = snapshot.get(_SUMMARY_EXPORT_KEY)
    if not isinstance(summary_snapshot, dict):
        return None
    summary_text = str(summary_snapshot.get('summary', '') or '').strip()
    if not summary_text:
        return None
    created_at_raw = str(summary_snapshot.get('created_at', '') or '').strip()
    created_at = None
    if created_at_raw:
        try:
            created_at = datetime.fromisoformat(
                created_at_raw.replace('Z', '+00:00')
            )
        except ValueError:
            created_at = None
    return SimpleNamespace(
        document=document,
        status=str(summary_snapshot.get('status', 'done') or 'done'),
        summary=summary_text,
        content_md=str(summary_snapshot.get('content_md', '') or '').strip(),
        created_at=created_at or timezone.now(),
        created_by_name=str(
            summary_snapshot.get('created_by_name', '')
            or document.owner.get_full_name().strip()
            or document.owner.username
        ).strip(),
        model_name=str(summary_snapshot.get('model_name', '') or '').strip(),
        prompt_id=summary_snapshot.get('prompt_id'),
        prompt_title=summary_snapshot.get('prompt_title'),
    )


# Là gì: `document_summary_discovery` là endpoint REST của nhóm tạo, xem và quản lý bản tóm tắt văn bản bằng AI; nó là điểm nhận request từ client đã đi qua router và lớp permission.
# Chức năng backend: Hàm tạo hoặc xử lý nội dung tóm tắt; đầu vào được kiểm tra hoặc chuẩn hóa trước khi tạo kết quả.
# Vai trò với UI: Kết quả được không gian làm việc tóm tắt văn bản sử dụng trực tiếp để hiển thị dữ liệu, tải tệp hoặc cập nhật trạng thái thao tác.
# Mối liên hệ: Hàm phối hợp với `_document_summary_queryset`, `request.GET.get`, `_apply_discovery_filters` và trả dữ liệu về cho lớp gọi kế tiếp trong cùng luồng.
# Bản chất và tác dụng: view mỏng ở biên HTTP; chủ yếu đọc, kiểm tra hoặc biến đổi dữ liệu; chuyển kết quả thành HTTP response.
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def document_summary_discovery(request):
    scope_qs, resolved_scope = _document_summary_queryset(
        request.user,
        request.GET.get('scope', 'all'),
    )
    filtered_qs = _apply_discovery_filters(scope_qs, request)

    limit = min(max(int(request.GET.get('limit', 24) or 24), 1), 100)
    offset = max(int(request.GET.get('offset', 0) or 0), 0)
    total_count = filtered_qs.count()
    items = filtered_qs[offset:offset + limit]

    return Response(
        {
            'items': DocumentListSerializer(
                items,
                many=True,
                context={'request': request},
            ).data,
            'total_count': total_count,
            'limit': limit,
            'offset': offset,
            'has_more': offset + limit < total_count,
            'scope': resolved_scope,
            'facets': _build_discovery_facets(scope_qs),
        }
    )


# Là gì: `document_summary_suggest` là endpoint REST của nhóm tạo, xem và quản lý bản tóm tắt văn bản bằng AI; nó là điểm nhận request từ client đã đi qua router và lớp permission.
# Chức năng backend: Hàm tạo hoặc xử lý nội dung tóm tắt; đầu vào được kiểm tra hoặc chuẩn hóa trước khi tạo kết quả.
# Vai trò với UI: Kết quả được không gian làm việc tóm tắt văn bản sử dụng trực tiếp để hiển thị dữ liệu, tải tệp hoặc cập nhật trạng thái thao tác.
# Mối liên hệ: Hàm phối hợp với `str.strip`, `request.GET.get`, `_document_summary_queryset` và trả dữ liệu về cho lớp gọi kế tiếp trong cùng luồng.
# Bản chất và tác dụng: view mỏng ở biên HTTP; chủ yếu đọc, kiểm tra hoặc biến đổi dữ liệu; chuyển kết quả thành HTTP response.
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def document_summary_suggest(request):
    query = str(request.GET.get('q', '') or '').strip()
    if len(query) < 2:
        return Response({'items': []})

    scope_qs, _resolved_scope = _document_summary_queryset(
        request.user,
        request.GET.get('scope', 'all'),
    )
    filtered_qs = _apply_discovery_filters(scope_qs, request)
    matched_docs = list(filtered_qs.filter(_build_document_search_query(query))[:8])

    suggestions = []
    seen = set()
    for document in matched_docs:
        key = ('document', document.pk)
        if key in seen:
            continue
        seen.add(key)
        suggestions.append(
            {
                'type': 'document',
                'document_id': document.pk,
                'value': document.title,
                'label': document.title,
                'caption': _document_caption(document),
                'matched_field': _matched_field(document, query),
            }
        )

    suggestions.extend(_collect_tag_suggestions(matched_docs, query))
    for document in matched_docs:
        if document.doc_number and query.casefold() in document.doc_number.casefold():
            key = ('doc_number', document.doc_number.casefold())
            if key in seen:
                continue
            seen.add(key)
            suggestions.append(
                {
                    'type': 'doc_number',
                    'value': document.doc_number,
                    'label': document.doc_number,
                    'caption': document.title,
                    'matched_field': 'doc_number',
                }
            )

    return Response({'items': suggestions[:12]})


# Là gì: `_summary_target_document` là helper nội bộ của module `document_summaries.py`, phục vụ nhóm tạo, xem và quản lý bản tóm tắt văn bản bằng AI.
# Chức năng backend: Hàm tạo hoặc xử lý nội dung tóm tắt; đầu vào được kiểm tra hoặc chuẩn hóa trước khi tạo kết quả.
# Vai trò với UI: Flutter không gọi trực tiếp hàm này; các endpoint cùng module dùng kết quả của nó để phục vụ không gian làm việc tóm tắt văn bản.
# Mối liên hệ: Hàm phối hợp với `get_accessible_documents`, `get_object_or_404`, `CompanyRuntimeGuard.assert_file_field` và trả dữ liệu về cho lớp gọi kế tiếp trong cùng luồng.
# Bản chất và tác dụng: hàm hỗ trợ tái sử dụng trong module; chủ yếu đọc, kiểm tra hoặc biến đổi dữ liệu.
def _summary_target_document(request, pk):
    # Chi cho tom tat van ban user CO QUYEN XEM (khong gom van ban cho duyet).
    qs = get_accessible_documents(request.user)
    document = get_object_or_404(qs, pk=pk)
    if document.output_file:
        CompanyRuntimeGuard.assert_file_field(
            document.output_file,
            target=document,
            detail='File van ban dang tro sang cong ty khac.',
        )
    return document


# Là gì: `document_summary_preview` là endpoint REST của nhóm tạo, xem và quản lý bản tóm tắt văn bản bằng AI; nó là điểm nhận request từ client đã đi qua router và lớp permission.
# Chức năng backend: Hàm tạo dữ liệu xem trước mà chưa ghi nhận thay đổi cuối cùng, đồng thời tạo hoặc xử lý nội dung tóm tắt; đầu vào được kiểm tra hoặc chuẩn hóa trước khi tạo kết quả.
# Vai trò với UI: Kết quả được không gian làm việc tóm tắt văn bản sử dụng trực tiếp để hiển thị dữ liệu, tải tệp hoặc cập nhật trạng thái thao tác.
# Mối liên hệ: Hàm phối hợp với `_summary_target_document`, `_parse_summary_request`, `_resolve_summary_prompt` và trả dữ liệu về cho lớp gọi kế tiếp trong cùng luồng.
# Bản chất và tác dụng: view mỏng ở biên HTTP; chủ yếu đọc, kiểm tra hoặc biến đổi dữ liệu; chuyển kết quả thành HTTP response.
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def document_summary_preview(request, pk):
    document = _summary_target_document(request, pk)
    summary_request = _parse_summary_request(request.data)
    options = summary_request['options']
    prompt, prompt_error = _resolve_summary_prompt(
        request.user,
        summary_request['prompt_id'],
    )
    if prompt_error is not None:
        return prompt_error

    user_extra_rules_raw = summary_request['user_extra_rules']
    combined_rules_raw = _compose_summary_rules(prompt, user_extra_rules_raw)

    safe_block = ''
    sanitize_report = {
        'score': 0.0,
        'flags': [],
        'modifications': [],
    }
    if combined_rules_raw:
        final, _audit = run_full_pipeline(combined_rules_raw, request.user, include_llm=False)
        if final.verdict == 'block':
            return Response(
                {
                    'detail': final.reason or 'Yeu cau bo sung bi tu choi.',
                    'incident_id': final.incident_id,
                    'flags': final.flags,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        safe_block, _nonce = wrap_user_rules(final.sanitized_text)
        sanitize_report = {
            'score': final.score,
            'flags': final.flags,
            'modifications': final.modifications,
        }

    preview_payload = build_document_summary_preview(
        document,
        options=options,
        safe_user_rules_block=safe_block,
    )
    preview_payload['preview']['sanitize_report'] = sanitize_report
    preview_payload['preview_token'] = sign_scoped_preview_token(
        {
            'user_id': request.user.pk,
            'document_id': document.pk,
            'rules_hash': hash_rules(combined_rules_raw),
            'options_hash': build_summary_options_hash(options),
            'summary_revision': build_summary_revision_token(document),
            'prompt_id': prompt.pk if prompt is not None else None,
        },
        salt=_SUMMARY_PREVIEW_SALT,
    )
    preview_payload['selected_prompt'] = _selected_prompt_payload(prompt)
    return Response(preview_payload)


# Là gì: `document_summary_generate` là endpoint REST của nhóm tạo, xem và quản lý bản tóm tắt văn bản bằng AI; nó là điểm nhận request từ client đã đi qua router và lớp permission.
# Chức năng backend: Hàm sinh nội dung hoặc tệp mới từ dữ liệu đầu vào, đồng thời tạo hoặc xử lý nội dung tóm tắt; đầu vào được kiểm tra hoặc chuẩn hóa trước khi tạo kết quả.
# Vai trò với UI: Kết quả được không gian làm việc tóm tắt văn bản sử dụng trực tiếp để hiển thị dữ liệu, tải tệp hoặc cập nhật trạng thái thao tác.
# Mối liên hệ: Hàm phối hợp với `_summary_target_document`, `_parse_summary_request`, `_resolve_summary_prompt` và trả dữ liệu về cho lớp gọi kế tiếp trong cùng luồng.
# Bản chất và tác dụng: view mỏng ở biên HTTP; chủ yếu đọc, kiểm tra hoặc biến đổi dữ liệu; chuyển kết quả thành HTTP response.
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def document_summary_generate(request, pk):
    document = _summary_target_document(request, pk)
    summary_request = _parse_summary_request(request.data)
    options = summary_request['options']
    prompt, prompt_error = _resolve_summary_prompt(
        request.user,
        summary_request['prompt_id'],
    )
    if prompt_error is not None:
        return prompt_error

    user_extra_rules_raw = summary_request['user_extra_rules']
    preview_token = summary_request['preview_token']
    prompt_check_token = summary_request['prompt_check_token']
    combined_rules_raw = _compose_summary_rules(prompt, user_extra_rules_raw)

    safe_block = ''
    guard_report = None
    if combined_rules_raw:
        if user_extra_rules_raw:
            expected_check = prompt_check_expected_payload(
                user_id=request.user.pk,
                scope='summary',
                context='document_summary',
                prompt_role='extra_instruction',
                prompt_text=user_extra_rules_raw,
                target_id=document.pk,
            )
            check_ok, check_why = verify_prompt_check_token(
                prompt_check_token,
                expected_check,
            )
            if not check_ok:
                return Response(
                    {'detail': f'Can check prompt lai truoc khi tom tat ({check_why}).'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        if not preview_token:
            return Response(
                {'detail': 'Phai xem truoc prompt (preview_token bat buoc).'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        expected = {
            'user_id': request.user.pk,
            'document_id': document.pk,
            'rules_hash': hash_rules(combined_rules_raw),
            'options_hash': build_summary_options_hash(options),
            'summary_revision': build_summary_revision_token(document),
            'prompt_id': prompt.pk if prompt is not None else None,
        }
        ok, why = verify_scoped_preview_token(
            preview_token,
            expected,
            salt=_SUMMARY_PREVIEW_SALT,
            required_keys=(
                'user_id',
                'document_id',
                'rules_hash',
                'options_hash',
                'summary_revision',
                'prompt_id',
            ),
        )
        if not ok:
            return Response(
                {'detail': f'preview_token khong hop le ({why}). Vui long xem preview lai.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        final, _audit = run_full_pipeline(combined_rules_raw, request.user, include_llm=True)
        if final.verdict == 'block':
            return Response(
                {
                    'detail': final.reason or 'Yeu cau bo sung bi tu choi.',
                    'incident_id': final.incident_id,
                    'flags': final.flags,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        safe_block, _nonce = wrap_user_rules(final.sanitized_text)
        guard_report = {
            'score': final.score,
            'flags': final.flags,
            'modifications': final.modifications,
        }

    try:
        payload = summarize_document_content(
            document,
            user=request.user,
            options=options,
            safe_user_rules_block=safe_block,
        )
    except Exception as exc:
        if hasattr(exc, 'detail') and hasattr(exc, 'status_code'):
            return Response({'detail': exc.detail}, status=exc.status_code)
        return Response(
            {'detail': 'Khong the tom tat van ban luc nay. Vui long thu lai sau.'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    if guard_report is not None:
        payload['guard_report'] = guard_report
    payload['selected_prompt'] = _selected_prompt_payload(prompt)
    _store_latest_summary_export(
        document,
        payload,
        user=request.user,
        prompt=prompt,
        user_extra_rules=user_extra_rules_raw,
    )
    return Response(payload)


# Là gì: `document_summary_download` là hàm điều phối nghiệp vụ của module `document_summaries.py`, thuộc nhóm tạo, xem và quản lý bản tóm tắt văn bản bằng AI.
# Chức năng backend: Hàm chuẩn bị và trả tệp cho phía client tải xuống, đồng thời tạo hoặc xử lý nội dung tóm tắt; đầu vào được kiểm tra hoặc chuẩn hóa trước khi tạo kết quả.
# Vai trò với UI: Flutter không gọi trực tiếp hàm này; các endpoint cùng module dùng kết quả của nó để phục vụ không gian làm việc tóm tắt văn bản.
# Mối liên hệ: Hàm phối hợp với `Request`, `JWTAuthentication`, `SessionAuthentication` và trả dữ liệu về cho lớp gọi kế tiếp trong cùng luồng.
# Bản chất và tác dụng: hàm hỗ trợ tái sử dụng trong module; chủ yếu đọc, kiểm tra hoặc biến đổi dữ liệu; chuyển kết quả thành HTTP response.
def document_summary_download(request, pk):
    """Plain Django view (KHONG dung @api_view) — debug Python 3.14 + DRF compat issue.

    Tu xu ly authentication qua JWT + Session, va su dung helper hien co.
    """
    from django.http import JsonResponse
    # Resolve user manually
    from rest_framework.request import Request
    from rest_framework.authentication import SessionAuthentication
    from rest_framework_simplejwt.authentication import JWTAuthentication
    drf_request = Request(request, authenticators=[JWTAuthentication(), SessionAuthentication()])
    try:
        user = drf_request.user
    except Exception:
        user = request.user if request.user.is_authenticated else None
    if user is None or not getattr(user, 'is_authenticated', False):
        return JsonResponse({'detail': 'Khong xac thuc.'}, status=401)

    # Reuse helper bang cach gan user vao request fake
    fake_req = SimpleNamespace(user=user, query_params=request.GET)
    try:
        document = _summary_target_document(fake_req, pk)
    except Exception as exc:
        # Http404 -> 404
        from django.http import Http404
        if isinstance(exc, Http404):
            return JsonResponse({'detail': 'Khong tim thay van ban.'}, status=404)
        raise

    fmt_raw = (request.GET.get('format') or '').strip().lower()
    if not fmt_raw:
        return JsonResponse({'detail': 'format is required'}, status=400)
    if fmt_raw not in {'docx', 'md'}:
        return JsonResponse({'detail': "format must be 'docx' or 'md'."}, status=400)

    summary = _latest_summary_export(document)
    if summary is None:
        return JsonResponse({'detail': 'Chua co ban tom tat de tai xuong.'}, status=409)
    if summary.status != 'done':
        return JsonResponse({'detail': 'Ban tom tat chua hoan tat.'}, status=409)

    if fmt_raw == 'docx':
        payload = export_summary_docx(summary)
        response = HttpResponse(
            payload,
            content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        )
    else:
        payload = export_summary_md(summary).encode('utf-8')
        response = HttpResponse(payload, content_type='text/markdown; charset=utf-8')

    date_token = summary.created_at.strftime('%Y%m%d')
    filename = f'{document.title}_tomtat_{date_token}.{fmt_raw}'
    response['Content-Disposition'] = (
        'attachment; ' + safe_attachment_filename(filename)
    )
    return response
