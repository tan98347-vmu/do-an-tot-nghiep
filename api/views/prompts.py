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


def _prompt_serializer_context(request):
    return {'request': request}


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


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def prompt_scope_list(request):
    return Response({
        'results': [
            {'key': key, 'label': label}
            for key, label in USAGE_SCOPES.items()
        ]
    })


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
