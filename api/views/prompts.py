from __future__ import annotations

from django.db.models import Max, Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from accounts.permissions import (
    can_delete_prompt,
    can_edit_prompt,
    get_accessible_prompts,
)
from api.security.prompt_guard import (
    VERDICT_BLOCK,
    prompt_check_expected_payload,
    prompt_quality_suggestions,
    run_prompt_preflight,
    sign_prompt_check_token,
)
from api.security.prompt_preflight_llm import LLM_PREFLIGHT_LAYER
from prompts.models import (
    PROMPT_STATUS_APPROVED,
    PROMPT_STATUS_PENDING,
    PROMPT_STATUS_PENDING_LEADER,
    PROMPT_STATUS_REJECTED,
    Prompt,
    USAGE_SCOPES,
)
from prompts.services.listing import build_prompt_list_queryset
from prompts.status_rules import can_approve_prompt, resolve_prompt_status_on_create

from ..serializers.prompts import (
    PromptDetailSerializer,
    PromptListSerializer,
    PromptWriteSerializer,
)


# Là gì: `_prompt_serializer_context` là helper nội bộ của module `prompts.py`, phục vụ nhóm tạo, sửa, chia sẻ và sử dụng prompt.
# Chức năng backend: Hàm xử lý phần việc `prompt serializer context` theo dữ liệu và ngữ cảnh được truyền vào; đầu vào được kiểm tra hoặc chuẩn hóa trước khi tạo kết quả.
# Vai trò với UI: Flutter không gọi trực tiếp hàm này; các endpoint cùng module dùng kết quả của nó để phục vụ thư viện prompt và các bộ chọn prompt.
# Mối liên hệ: Hàm được các endpoint hoặc helper cùng module gọi khi cần cùng quy tắc xử lý.
# Bản chất và tác dụng: hàm hỗ trợ tái sử dụng trong module; chủ yếu đọc, kiểm tra hoặc biến đổi dữ liệu.
def _prompt_serializer_context(request):
    return {'request': request}


# Là gì: `_validated_scope_filters` là helper nội bộ của module `prompts.py`, phục vụ nhóm tạo, sửa, chia sẻ và sử dụng prompt.
# Chức năng backend: Hàm xử lý phần việc `validated scope filters` theo dữ liệu và ngữ cảnh được truyền vào; đầu vào được kiểm tra hoặc chuẩn hóa trước khi tạo kết quả.
# Vai trò với UI: Flutter không gọi trực tiếp hàm này; các endpoint cùng module dùng kết quả của nó để phục vụ thư viện prompt và các bộ chọn prompt.
# Mối liên hệ: Hàm phối hợp với `str.strip`, `request.query_params.getlist`, `ValidationError` và trả dữ liệu về cho lớp gọi kế tiếp trong cùng luồng.
# Bản chất và tác dụng: hàm hỗ trợ tái sử dụng trong module; chủ yếu đọc, kiểm tra hoặc biến đổi dữ liệu.
def _validated_scope_filters(request):
    scopes = [
        str(scope or '').strip()
        for scope in request.query_params.getlist('scope')
        if str(scope or '').strip()
    ]
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


# Là gì: `prompt_scope_list` là endpoint REST của nhóm tạo, sửa, chia sẻ và sử dụng prompt; nó là điểm nhận request từ client đã đi qua router và lớp permission.
# Chức năng backend: Hàm truy vấn và trả về danh sách dữ liệu phù hợp; đầu vào được kiểm tra hoặc chuẩn hóa trước khi tạo kết quả.
# Vai trò với UI: Kết quả được thư viện prompt và các bộ chọn prompt sử dụng trực tiếp để hiển thị dữ liệu, tải tệp hoặc cập nhật trạng thái thao tác.
# Mối liên hệ: Hàm phối hợp với `USAGE_SCOPES.items` và trả dữ liệu về cho lớp gọi kế tiếp trong cùng luồng.
# Bản chất và tác dụng: view mỏng ở biên HTTP; chủ yếu đọc, kiểm tra hoặc biến đổi dữ liệu; chuyển kết quả thành HTTP response.
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def prompt_scope_list(request):
    return Response({
        'results': [
            {'key': key, 'label': label}
            for key, label in USAGE_SCOPES.items()
        ]
    })


# Là gì: `prompt_check` là endpoint REST của nhóm tạo, sửa, chia sẻ và sử dụng prompt; nó là điểm nhận request từ client đã đi qua router và lớp permission.
# Chức năng backend: Hàm kiểm tra điều kiện và trả kết quả để bước sau quyết định; đầu vào được kiểm tra hoặc chuẩn hóa trước khi tạo kết quả.
# Vai trò với UI: Kết quả được thư viện prompt và các bộ chọn prompt sử dụng trực tiếp để hiển thị dữ liệu, tải tệp hoặc cập nhật trạng thái thao tác.
# Mối liên hệ: Hàm phối hợp với `str.strip`, `request.data.get`, `USAGE_SCOPES.keys` và trả dữ liệu về cho lớp gọi kế tiếp trong cùng luồng.
# Bản chất và tác dụng: view mỏng ở biên HTTP; chủ yếu đọc, kiểm tra hoặc biến đổi dữ liệu; chuyển kết quả thành HTTP response.
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def prompt_check(request):
    scope = str(request.data.get('scope') or '').strip()
    context = str(request.data.get('context') or '').strip()
    prompt_role = str(request.data.get('prompt_role') or '').strip()
    prompt_text = str(request.data.get('prompt_text') or '').strip()
    target_id = request.data.get('target_id')

    allowed_scopes = {*USAGE_SCOPES.keys(), 'saved_prompt'}
    if scope not in allowed_scopes:
        return Response(
            {
                'verdict': 'block',
                'reason': f'scope phai thuoc {sorted(allowed_scopes)}',
                'flags': ['invalid_scope'],
                'suggestions': prompt_quality_suggestions(
                    scope=scope,
                    context=context,
                    prompt_role=prompt_role,
                ),
            },
            status=status.HTTP_400_BAD_REQUEST,
        )
    if not context:
        return Response(
            {
                'verdict': 'block',
                'reason': 'context la bat buoc.',
                'flags': ['missing_context'],
                'suggestions': prompt_quality_suggestions(
                    scope=scope,
                    context=context,
                    prompt_role=prompt_role,
                ),
            },
            status=status.HTTP_400_BAD_REQUEST,
        )
    if not prompt_role:
        return Response(
            {
                'verdict': 'block',
                'reason': 'prompt_role la bat buoc.',
                'flags': ['missing_prompt_role'],
                'suggestions': prompt_quality_suggestions(
                    scope=scope,
                    context=context,
                    prompt_role=prompt_role,
                ),
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    final, audit = run_prompt_preflight(
        prompt_text,
        request.user,
        scope=scope,
        context=context,
        prompt_role=prompt_role,
        include_llm=True,
    )
    fallback_suggestions = prompt_quality_suggestions(
        scope=scope,
        context=context,
        prompt_role=prompt_role,
    )
    suggestions = final.suggestions or fallback_suggestions
    llm_result = next(
        (
            result
            for result in audit
            if result.layer == LLM_PREFLIGHT_LAYER
        ),
        None,
    )
    llm_review = llm_result.metadata if llm_result is not None else {}
    rules_passed = not any(
        result.verdict == VERDICT_BLOCK
        for result in audit
        if result.layer != LLM_PREFLIGHT_LAYER
    )
    checks = {
        'rules': 'pass' if rules_passed else 'block',
        'llm': (
            'pass'
            if llm_result is not None and llm_result.verdict != VERDICT_BLOCK
            else 'block' if llm_result is not None else 'not_run'
        ),
    }
    if final.verdict == VERDICT_BLOCK:
        return Response(
            {
                'verdict': 'block',
                'reason': final.reason or 'Prompt không đạt yêu cầu.',
                'flags': final.flags,
                'suggestions': suggestions,
                'incident_id': final.incident_id,
                'checks': checks,
                'llm_review': llm_review,
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    payload = prompt_check_expected_payload(
        user_id=request.user.pk,
        scope=scope,
        context=context,
        prompt_role=prompt_role,
        prompt_text=prompt_text,
        target_id=target_id,
    )
    return Response(
        {
            'verdict': 'pass',
            'prompt_check_token': sign_prompt_check_token(payload),
            'message': 'Prompt có thể sử dụng.',
            'flags': final.flags,
            'suggestions': [],
            'checks': checks,
            'llm_review': llm_review,
        }
    )


# Là gì: `prompt_list_create` là endpoint REST của nhóm tạo, sửa, chia sẻ và sử dụng prompt; nó là điểm nhận request từ client đã đi qua router và lớp permission.
# Chức năng backend: Hàm truy vấn và trả về danh sách dữ liệu phù hợp, đồng thời kiểm tra đầu vào và tạo dữ liệu mới; đầu vào được kiểm tra hoặc chuẩn hóa trước khi tạo kết quả.
# Vai trò với UI: Kết quả được thư viện prompt và các bộ chọn prompt sử dụng trực tiếp để hiển thị dữ liệu, tải tệp hoặc cập nhật trạng thái thao tác.
# Mối liên hệ: Hàm phối hợp với `build_prompt_list_queryset`, `PromptListSerializer`, `_prompt_serializer_context` và trả dữ liệu về cho lớp gọi kế tiếp trong cùng luồng.
# Bản chất và tác dụng: view mỏng ở biên HTTP; có side effect ghi cơ sở dữ liệu; chuyển kết quả thành HTTP response.
@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def prompt_list_create(request):
    if request.method == 'GET':
        qs = build_prompt_list_queryset(request.user, request.query_params)
        serializer = PromptListSerializer(
            qs,
            many=True,
            context=_prompt_serializer_context(request),
        )
        return Response({'results': serializer.data})

    serializer = PromptWriteSerializer(data=request.data, context=_prompt_serializer_context(request))
    serializer.is_valid(raise_exception=True)
    prompt = serializer.save()
    detail = PromptDetailSerializer(prompt, context=_prompt_serializer_context(request))
    return Response(detail.data, status=status.HTTP_201_CREATED)


# Là gì: `prompt_detail` là endpoint REST của nhóm tạo, sửa, chia sẻ và sử dụng prompt; nó là điểm nhận request từ client đã đi qua router và lớp permission.
# Chức năng backend: Hàm đọc hoặc xử lý một bản ghi cụ thể; đầu vào được kiểm tra hoặc chuẩn hóa trước khi tạo kết quả.
# Vai trò với UI: Kết quả được thư viện prompt và các bộ chọn prompt sử dụng trực tiếp để hiển thị dữ liệu, tải tệp hoặc cập nhật trạng thái thao tác.
# Mối liên hệ: Hàm phối hợp với `get_object_or_404`, `get_accessible_prompts`, `PromptDetailSerializer` và trả dữ liệu về cho lớp gọi kế tiếp trong cùng luồng.
# Bản chất và tác dụng: view mỏng ở biên HTTP; có side effect ghi cơ sở dữ liệu; chuyển kết quả thành HTTP response.
@api_view(['GET', 'PUT', 'PATCH', 'DELETE'])
@permission_classes([IsAuthenticated])
def prompt_detail(request, pk):
    prompt = get_object_or_404(get_accessible_prompts(request.user), pk=pk)

    if request.method == 'GET':
        serializer = PromptDetailSerializer(prompt, context=_prompt_serializer_context(request))
        return Response(serializer.data)

    if request.method == 'DELETE':
        if not can_delete_prompt(request.user, prompt):
            return Response({'detail': 'Khong co quyen.'}, status=status.HTTP_403_FORBIDDEN)
        prompt.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    if not can_edit_prompt(request.user, prompt):
        return Response({'detail': 'Khong co quyen.'}, status=status.HTTP_403_FORBIDDEN)

    partial = request.method == 'PATCH'
    serializer = PromptWriteSerializer(
        prompt,
        data=request.data,
        partial=partial,
        context=_prompt_serializer_context(request),
    )
    serializer.is_valid(raise_exception=True)
    serializer.save()
    detail = PromptDetailSerializer(prompt, context=_prompt_serializer_context(request))
    return Response(detail.data)


# Là gì: `prompt_submit` là endpoint REST của nhóm tạo, sửa, chia sẻ và sử dụng prompt; nó là điểm nhận request từ client đã đi qua router và lớp permission.
# Chức năng backend: Hàm gửi dữ liệu vào bước xử lý hoặc phê duyệt tiếp theo; đầu vào được kiểm tra hoặc chuẩn hóa trước khi tạo kết quả.
# Vai trò với UI: Kết quả được thư viện prompt và các bộ chọn prompt sử dụng trực tiếp để hiển thị dữ liệu, tải tệp hoặc cập nhật trạng thái thao tác.
# Mối liên hệ: Hàm phối hợp với `get_object_or_404`, `can_edit_prompt`, `resolve_prompt_status_on_create` và trả dữ liệu về cho lớp gọi kế tiếp trong cùng luồng.
# Bản chất và tác dụng: view mỏng ở biên HTTP; có side effect ghi cơ sở dữ liệu; chuyển kết quả thành HTTP response.
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def prompt_submit(request, pk):
    prompt = get_object_or_404(Prompt, pk=pk)
    if not can_edit_prompt(request.user, prompt):
        return Response({'detail': 'Khong co quyen.'}, status=status.HTTP_403_FORBIDDEN)
    new_status = resolve_prompt_status_on_create(
        request.user,
        prompt.visibility,
        group=prompt.group,
    )
    prompt.status = new_status
    prompt.approved_by = None
    prompt.approved_at = None
    prompt.approver_note = ''
    prompt.save(update_fields=['status', 'approved_by', 'approved_at', 'approver_note', 'updated_at'])
    serializer = PromptDetailSerializer(prompt, context=_prompt_serializer_context(request))
    return Response(serializer.data)


# Là gì: `prompt_approve` là endpoint REST của nhóm tạo, sửa, chia sẻ và sử dụng prompt; nó là điểm nhận request từ client đã đi qua router và lớp permission.
# Chức năng backend: Hàm chấp thuận yêu cầu và chuyển trạng thái nghiệp vụ; đầu vào được kiểm tra hoặc chuẩn hóa trước khi tạo kết quả.
# Vai trò với UI: Kết quả được thư viện prompt và các bộ chọn prompt sử dụng trực tiếp để hiển thị dữ liệu, tải tệp hoặc cập nhật trạng thái thao tác.
# Mối liên hệ: Hàm phối hợp với `get_object_or_404`, `can_approve_prompt`, `timezone.now` và trả dữ liệu về cho lớp gọi kế tiếp trong cùng luồng.
# Bản chất và tác dụng: view mỏng ở biên HTTP; có side effect ghi cơ sở dữ liệu; chuyển kết quả thành HTTP response.
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def prompt_approve(request, pk):
    prompt = get_object_or_404(Prompt, pk=pk)
    ok, reason = can_approve_prompt(request.user, prompt)
    if not ok:
        return Response({'detail': reason}, status=status.HTTP_403_FORBIDDEN)
    prompt.status = PROMPT_STATUS_APPROVED
    prompt.approved_by = request.user
    prompt.approved_at = timezone.now()
    prompt.approver_note = str(request.data.get('note', '') or '').strip()
    prompt.save(update_fields=['status', 'approved_by', 'approved_at', 'approver_note', 'updated_at'])
    serializer = PromptDetailSerializer(prompt, context=_prompt_serializer_context(request))
    return Response(serializer.data)


# Là gì: `prompt_reject` là endpoint REST của nhóm tạo, sửa, chia sẻ và sử dụng prompt; nó là điểm nhận request từ client đã đi qua router và lớp permission.
# Chức năng backend: Hàm từ chối yêu cầu và ghi nhận lý do; đầu vào được kiểm tra hoặc chuẩn hóa trước khi tạo kết quả.
# Vai trò với UI: Kết quả được thư viện prompt và các bộ chọn prompt sử dụng trực tiếp để hiển thị dữ liệu, tải tệp hoặc cập nhật trạng thái thao tác.
# Mối liên hệ: Hàm phối hợp với `get_object_or_404`, `can_approve_prompt`, `str.strip` và trả dữ liệu về cho lớp gọi kế tiếp trong cùng luồng.
# Bản chất và tác dụng: view mỏng ở biên HTTP; có side effect ghi cơ sở dữ liệu; chuyển kết quả thành HTTP response.
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def prompt_reject(request, pk):
    prompt = get_object_or_404(Prompt, pk=pk)
    ok, reason = can_approve_prompt(request.user, prompt)
    if not ok:
        return Response({'detail': reason}, status=status.HTTP_403_FORBIDDEN)
    note = str(request.data.get('note', '') or '').strip()
    if not note:
        return Response({'detail': 'Phai co ghi chu khi tu choi.'}, status=status.HTTP_400_BAD_REQUEST)
    prompt.status = PROMPT_STATUS_REJECTED
    prompt.approved_by = request.user
    prompt.approved_at = timezone.now()
    prompt.approver_note = note
    prompt.save(update_fields=['status', 'approved_by', 'approved_at', 'approver_note', 'updated_at'])
    serializer = PromptDetailSerializer(prompt, context=_prompt_serializer_context(request))
    return Response(serializer.data)


# Là gì: `prompts_pending_review` là endpoint REST của nhóm tạo, sửa, chia sẻ và sử dụng prompt; nó là điểm nhận request từ client đã đi qua router và lớp permission.
# Chức năng backend: Hàm xử lý phần việc `prompts pending review` theo dữ liệu và ngữ cảnh được truyền vào; đầu vào được kiểm tra hoặc chuẩn hóa trước khi tạo kết quả.
# Vai trò với UI: Kết quả được thư viện prompt và các bộ chọn prompt sử dụng trực tiếp để hiển thị dữ liệu, tải tệp hoặc cập nhật trạng thái thao tác.
# Mối liên hệ: Hàm phối hợp với `Prompt.objects.none`, `Prompt.objects.filter`, `UserGroupMembership.objects.filter.values_list` và trả dữ liệu về cho lớp gọi kế tiếp trong cùng luồng.
# Bản chất và tác dụng: view mỏng ở biên HTTP; chủ yếu đọc, kiểm tra hoặc biến đổi dữ liệu; chuyển kết quả thành HTTP response.
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def prompts_pending_review(request):
    user = request.user

    qs = Prompt.objects.none()
    if user.is_superuser or user.is_staff:
        qs = Prompt.objects.filter(
            Q(status=PROMPT_STATUS_PENDING) | Q(status=PROMPT_STATUS_PENDING_LEADER)
        )
    else:
        from accounts.models import UserGroupMembership

        leader_groups = UserGroupMembership.objects.filter(
            user=user,
            role='leader',
        ).values_list('group_id', flat=True)
        if leader_groups:
            qs = Prompt.objects.filter(
                status=PROMPT_STATUS_PENDING_LEADER,
                group_id__in=list(leader_groups),
            )

    serializer = PromptListSerializer(
        qs.order_by('-updated_at')[:100],
        many=True,
        context=_prompt_serializer_context(request),
    )
    return Response(serializer.data)


# Là gì: `prompts_recent_used` là endpoint REST của nhóm tạo, sửa, chia sẻ và sử dụng prompt; nó là điểm nhận request từ client đã đi qua router và lớp permission.
# Chức năng backend: Hàm xử lý phần việc `prompts recent used` theo dữ liệu và ngữ cảnh được truyền vào; đầu vào được kiểm tra hoặc chuẩn hóa trước khi tạo kết quả.
# Vai trò với UI: Kết quả được thư viện prompt và các bộ chọn prompt sử dụng trực tiếp để hiển thị dữ liệu, tải tệp hoặc cập nhật trạng thái thao tác.
# Mối liên hệ: Hàm phối hợp với `strip`, `request.GET.get`, `get_accessible_prompts.filter.annotate.filter` và trả dữ liệu về cho lớp gọi kế tiếp trong cùng luồng.
# Bản chất và tác dụng: view mỏng ở biên HTTP; chủ yếu đọc, kiểm tra hoặc biến đổi dữ liệu; chuyển kết quả thành HTTP response.
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def prompts_recent_used(request):
    from documents.models import Document

    query = (request.GET.get('q') or '').strip()

    qs = (
        get_accessible_prompts(request.user)
        .filter(status=PROMPT_STATUS_APPROVED)
        .annotate(last_used=Max('documents_using__created_at'))
        .filter(last_used__isnull=False)
    )
    if query:
        qs = qs.filter(
            Q(title__icontains=query)
            | Q(original_raw_text__icontains=query)
            | Q(owner__username__icontains=query)
            | Q(owner__first_name__icontains=query)
            | Q(owner__last_name__icontains=query)
            | Q(documents_using__title__icontains=query)
        ).distinct()
    qs = qs.order_by('-usage_count', '-last_used')[:50]

    prompt_ids = [prompt.pk for prompt in qs]
    last_doc_by_prompt = {}
    if prompt_ids:
        doc_qs = (
            Document.all_objects
            .filter(prompt_id__in=prompt_ids)
            .order_by('prompt_id', '-created_at')
            .values(
                'prompt_id',
                'id',
                'title',
                'owner__username',
                'owner__first_name',
                'owner__last_name',
                'created_at',
            )
        )
        for row in doc_qs:
            prompt_id = row['prompt_id']
            if prompt_id in last_doc_by_prompt:
                continue
            owner_name = (
                f"{(row.get('owner__first_name') or '').strip()} {(row.get('owner__last_name') or '').strip()}"
            ).strip() or row.get('owner__username') or ''
            last_doc_by_prompt[prompt_id] = {
                'doc_id': row['id'],
                'doc_title': row['title'],
                'owner_name': owner_name,
                'created_at': row['created_at'].isoformat() if row['created_at'] else None,
            }

    items = []
    for prompt in qs:
        last = last_doc_by_prompt.get(prompt.pk, {})
        owner_full = (
            f'{prompt.owner.first_name} {prompt.owner.last_name}'.strip()
            if prompt.owner else ''
        ) or (prompt.owner.username if prompt.owner else '')
        items.append(
            {
                'id': prompt.pk,
                'title': prompt.title,
                'rules_content_preview': (prompt.original_raw_text or prompt.rules_content or '')[:200],
                'rules_content': prompt.original_raw_text or '',
                'tags': prompt.tags or '',
                'category_name': prompt.category.name if prompt.category else None,
                'last_used': prompt.last_used.isoformat() if prompt.last_used else None,
                'created_at': prompt.created_at.isoformat() if prompt.created_at else None,
                'usage_count': prompt.usage_count,
                'safety_score': prompt.safety_score,
                'visibility': prompt.visibility,
                'owner_name': owner_full,
                'owner_id': prompt.owner_id,
                'is_mine': prompt.owner_id == request.user.pk,
                'last_used_doc_id': last.get('doc_id'),
                'last_used_doc_title': last.get('doc_title'),
                'last_used_by_name': last.get('owner_name'),
            }
        )
    return Response(items)
