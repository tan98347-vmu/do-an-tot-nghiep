import re

from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from accounts.permissions import (
    get_accessible_prompts,
    get_document_detail_queryset,
    get_template_detail_queryset,
)
from accounts.tenancy import get_user_company
from ai_engine.compliance_checker import (
    ComplianceChecker,
    ComplianceLLMError,
    ComplianceLLMTimeout,
)
from ai_engine.models import ComplianceCheckResult
from api.serializers.compliance import (
    ComplianceCheckResultSerializer,
    ComplianceCheckRunSerializer,
)
from document_templates.models import DocumentTemplate
from documents.ai_summary import DocumentSummaryUnavailable, _build_document_summary_source
from documents.models import Document
from documents.runtime_helpers import _extract_text_from_docx
from prompts.models import Prompt

_SCOPE_TAG_RE = re.compile(r'[\s,;|]+')


def _normalized_scope_tokens(prompt) -> set[str]:
    tokens: set[str] = set()

    usage_scope = getattr(prompt, 'usage_scope', None)
    if isinstance(usage_scope, (list, tuple, set)):
        tokens.update(str(item or '').strip().lower() for item in usage_scope if str(item or '').strip())
    elif isinstance(usage_scope, str):
        tokens.update(
            token
            for token in _SCOPE_TAG_RE.split(usage_scope.strip().lower())
            if token
        )

    raw_tags = str(getattr(prompt, 'tags', '') or '').strip()
    if raw_tags:
        for token in _SCOPE_TAG_RE.split(raw_tags.lower()):
            cleaned = token.strip()
            if cleaned:
                tokens.add(cleaned)
                if cleaned.startswith('scope:'):
                    tokens.add(cleaned.split(':', 1)[1])
    return tokens


def _prompt_supports_scope(prompt, scope: str) -> bool:
    tokens = _normalized_scope_tokens(prompt)
    if not tokens:
        return True
    return scope in tokens or f'scope:{scope}' in tokens


def _resolve_prompt(user, prompt_id: int, *, scope: str):
    prompt = get_accessible_prompts(user).filter(pk=prompt_id).first()
    if prompt is None:
        return None, Response({'detail': 'prompt_id không hợp lệ.'}, status=400)
    if not _prompt_supports_scope(prompt, scope):
        return None, Response(
            {'detail': f'prompt_id không hợp lệ cho scope {scope}.'},
            status=400,
        )
    return prompt, None


def _resolve_target(user, target_type: str, target_id: int):
    company = get_user_company(user)
    if target_type == ComplianceCheckResult.TARGET_DOCUMENT:
        model = Document
        all_qs = getattr(model, 'all_objects', model.objects).filter(pk=target_id)
        accessible_qs = get_document_detail_queryset(user)
    else:
        model = DocumentTemplate
        all_qs = getattr(model, 'all_objects', model.objects).filter(pk=target_id)
        accessible_qs = get_template_detail_queryset(user)

    if company is not None:
        all_qs = all_qs.filter(company=company)
        accessible_qs = accessible_qs.filter(company=company)

    existing = all_qs.first()
    if existing is None:
        return None, Response({'detail': 'Không tìm thấy đối tượng.'}, status=404)

    accessible = accessible_qs.filter(pk=target_id).first()
    if accessible is None:
        return None, Response({'detail': 'Bạn không có quyền xem đối tượng này.'}, status=403)
    return accessible, None


def _normalize_plain_text(value: str) -> str:
    text = re.sub(r'<[^>]+>', ' ', str(value or ''))
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    lines = [re.sub(r'\s+', ' ', line).strip() for line in text.split('\n')]
    return '\n'.join(line for line in lines if line).strip()


def _extract_template_text(template: DocumentTemplate) -> str:
    if _normalize_plain_text(template.content):
        return _normalize_plain_text(template.content)
    if template.docx_file:
        try:
            with template.docx_file.open('rb') as handle:
                extracted = _extract_text_from_docx(handle)
            if _normalize_plain_text(extracted):
                return _normalize_plain_text(extracted)
        except Exception:
            pass
    return _normalize_plain_text(template.notes or '')


def _extract_target_text(target, target_type: str) -> str:
    if target_type == ComplianceCheckResult.TARGET_DOCUMENT:
        try:
            text, _source_kind = _build_document_summary_source(target)
            return text
        except DocumentSummaryUnavailable:
            return ''
    return _extract_template_text(target)


def _serialize_result(result: ComplianceCheckResult) -> dict:
    return ComplianceCheckResultSerializer(result).data


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def compliance_check_run(request):
    serializer = ComplianceCheckRunSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    target_type = serializer.validated_data['target_type']
    target_id = serializer.validated_data['target_id']
    prompt_id = serializer.validated_data['prompt_id']
    force = serializer.validated_data.get('force', False)

    target, error_response = _resolve_target(request.user, target_type, target_id)
    if error_response is not None:
        return error_response

    prompt, prompt_error = _resolve_prompt(
        request.user,
        prompt_id,
        scope='compliance_check',
    )
    if prompt_error is not None:
        return prompt_error

    content = _extract_target_text(target, target_type)
    checker = ComplianceChecker(prompt, content, user=request.user)
    content_hash = checker.content_hash()

    if not force:
        cached = (
            ComplianceCheckResult.objects
            .select_related('prompt', 'created_by')
            .filter(
                target_type=target_type,
                target_id=target_id,
                prompt=prompt,
                content_hash=content_hash,
            )
            .order_by('-created_at')
            .first()
        )
        if cached is not None:
            return Response(_serialize_result(cached))

    try:
        result = checker.run()
    except ComplianceLLMTimeout as exc:
        return Response({'detail': str(exc)}, status=504)
    except ComplianceLLMError as exc:
        return Response({'detail': str(exc)}, status=502)

    record = ComplianceCheckResult.objects.create(
        target_type=target_type,
        target_id=target_id,
        prompt=prompt,
        passed=result['passed'],
        items_missing_json=result['items_missing'],
        content_hash=content_hash,
        created_by=request.user,
    )
    return Response(_serialize_result(record))


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def compliance_check_history(request):
    target_type = str(request.GET.get('target_type') or '').strip().lower()
    target_id_raw = str(request.GET.get('target_id') or '').strip()
    if target_type not in {
        ComplianceCheckResult.TARGET_DOCUMENT,
        ComplianceCheckResult.TARGET_TEMPLATE,
    }:
        return Response(
            {'detail': 'target_type phải là document hoặc template.'},
            status=400,
        )
    if not target_id_raw.isdigit():
        return Response({'detail': 'target_id không hợp lệ.'}, status=400)

    target, error_response = _resolve_target(
        request.user,
        target_type,
        int(target_id_raw),
    )
    if error_response is not None:
        return error_response

    results = (
        ComplianceCheckResult.objects
        .select_related('prompt', 'created_by')
        .filter(target_type=target_type, target_id=target.pk)
        .order_by('-created_at')[:10]
    )
    return Response(
        {'results': ComplianceCheckResultSerializer(results, many=True).data}
    )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def compliance_check_detail(request, pk):
    result = get_object_or_404(
        ComplianceCheckResult.objects.select_related('prompt', 'created_by'),
        pk=pk,
    )
    _target, error_response = _resolve_target(
        request.user,
        result.target_type,
        result.target_id,
    )
    if error_response is not None:
        return error_response
    return Response(_serialize_result(result))
