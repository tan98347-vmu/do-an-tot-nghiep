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
from api.security.prompt_guard import (
    prompt_check_expected_payload,
    verify_prompt_check_token,
)
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


# Là gì: `_normalized_scope_tokens` là helper nội bộ của module `compliance.py`, phục vụ nhóm kiểm tra tuân thủ và đánh giá nội dung văn bản.
# Chức năng backend: Hàm xử lý phần việc `normalized scope tokens` theo dữ liệu và ngữ cảnh được truyền vào; đầu vào được kiểm tra hoặc chuẩn hóa trước khi tạo kết quả.
# Vai trò với UI: Flutter không gọi trực tiếp hàm này; các endpoint cùng module dùng kết quả của nó để phục vụ màn hình kiểm tra tuân thủ.
# Mối liên hệ: Hàm phối hợp với `tokens.update`, `str.strip.lower`, `str.strip` và trả dữ liệu về cho lớp gọi kế tiếp trong cùng luồng.
# Bản chất và tác dụng: hàm hỗ trợ tái sử dụng trong module; có side effect ghi cơ sở dữ liệu.
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


# Là gì: `_prompt_supports_scope` là helper nội bộ của module `compliance.py`, phục vụ nhóm kiểm tra tuân thủ và đánh giá nội dung văn bản.
# Chức năng backend: Hàm xử lý phần việc `prompt supports scope` theo dữ liệu và ngữ cảnh được truyền vào; đầu vào được kiểm tra hoặc chuẩn hóa trước khi tạo kết quả.
# Vai trò với UI: Flutter không gọi trực tiếp hàm này; các endpoint cùng module dùng kết quả của nó để phục vụ màn hình kiểm tra tuân thủ.
# Mối liên hệ: Hàm phối hợp với `_normalized_scope_tokens` và trả dữ liệu về cho lớp gọi kế tiếp trong cùng luồng.
# Bản chất và tác dụng: hàm hỗ trợ tái sử dụng trong module; chủ yếu đọc, kiểm tra hoặc biến đổi dữ liệu.
def _prompt_supports_scope(prompt, scope: str) -> bool:
    tokens = _normalized_scope_tokens(prompt)
    if not tokens:
        return True
    return scope in tokens or f'scope:{scope}' in tokens


# Là gì: `_resolve_prompt` là helper nội bộ của module `compliance.py`, phục vụ nhóm kiểm tra tuân thủ và đánh giá nội dung văn bản.
# Chức năng backend: Hàm xác định đối tượng hoặc cấu hình hiệu lực từ ngữ cảnh hiện tại; đầu vào được kiểm tra hoặc chuẩn hóa trước khi tạo kết quả.
# Vai trò với UI: Flutter không gọi trực tiếp hàm này; các endpoint cùng module dùng kết quả của nó để phục vụ màn hình kiểm tra tuân thủ.
# Mối liên hệ: Hàm phối hợp với `get_accessible_prompts.filter.first`, `get_accessible_prompts.filter`, `get_accessible_prompts` và trả dữ liệu về cho lớp gọi kế tiếp trong cùng luồng.
# Bản chất và tác dụng: hàm hỗ trợ tái sử dụng trong module; chủ yếu đọc, kiểm tra hoặc biến đổi dữ liệu; chuyển kết quả thành HTTP response.
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


# Là gì: `_resolve_target` là helper nội bộ của module `compliance.py`, phục vụ nhóm kiểm tra tuân thủ và đánh giá nội dung văn bản.
# Chức năng backend: Hàm xác định đối tượng hoặc cấu hình hiệu lực từ ngữ cảnh hiện tại; đầu vào được kiểm tra hoặc chuẩn hóa trước khi tạo kết quả.
# Vai trò với UI: Flutter không gọi trực tiếp hàm này; các endpoint cùng module dùng kết quả của nó để phục vụ màn hình kiểm tra tuân thủ.
# Mối liên hệ: Hàm phối hợp với `get_user_company`, `getattr.filter`, `get_document_detail_queryset` và trả dữ liệu về cho lớp gọi kế tiếp trong cùng luồng.
# Bản chất và tác dụng: hàm hỗ trợ tái sử dụng trong module; chủ yếu đọc, kiểm tra hoặc biến đổi dữ liệu; chuyển kết quả thành HTTP response.
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


# Là gì: `_normalize_plain_text` là helper nội bộ của module `compliance.py`, phục vụ nhóm kiểm tra tuân thủ và đánh giá nội dung văn bản.
# Chức năng backend: Hàm chuẩn hóa dữ liệu về định dạng thống nhất; đầu vào được kiểm tra hoặc chuẩn hóa trước khi tạo kết quả.
# Vai trò với UI: Flutter không gọi trực tiếp hàm này; các endpoint cùng module dùng kết quả của nó để phục vụ màn hình kiểm tra tuân thủ.
# Mối liên hệ: Hàm phối hợp với `re.sub`, `text.replace.replace`, `text.replace` và trả dữ liệu về cho lớp gọi kế tiếp trong cùng luồng.
# Bản chất và tác dụng: hàm hỗ trợ tái sử dụng trong module; chủ yếu đọc, kiểm tra hoặc biến đổi dữ liệu.
def _normalize_plain_text(value: str) -> str:
    text = re.sub(r'<[^>]+>', ' ', str(value or ''))
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    lines = [re.sub(r'\s+', ' ', line).strip() for line in text.split('\n')]
    return '\n'.join(line for line in lines if line).strip()


# Là gì: `_extract_template_text` là helper nội bộ của module `compliance.py`, phục vụ nhóm kiểm tra tuân thủ và đánh giá nội dung văn bản.
# Chức năng backend: Hàm trích xuất nội dung hoặc giá trị cần thiết từ dữ liệu nguồn; đầu vào được kiểm tra hoặc chuẩn hóa trước khi tạo kết quả.
# Vai trò với UI: Flutter không gọi trực tiếp hàm này; các endpoint cùng module dùng kết quả của nó để phục vụ màn hình kiểm tra tuân thủ.
# Mối liên hệ: Hàm phối hợp với `_normalize_plain_text`, `template.docx_file.open`, `_extract_text_from_docx` và trả dữ liệu về cho lớp gọi kế tiếp trong cùng luồng.
# Bản chất và tác dụng: hàm hỗ trợ tái sử dụng trong module; có side effect lên tệp hoặc storage.
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


# Là gì: `_extract_target_text` là helper nội bộ của module `compliance.py`, phục vụ nhóm kiểm tra tuân thủ và đánh giá nội dung văn bản.
# Chức năng backend: Hàm trích xuất nội dung hoặc giá trị cần thiết từ dữ liệu nguồn; đầu vào được kiểm tra hoặc chuẩn hóa trước khi tạo kết quả.
# Vai trò với UI: Flutter không gọi trực tiếp hàm này; các endpoint cùng module dùng kết quả của nó để phục vụ màn hình kiểm tra tuân thủ.
# Mối liên hệ: Hàm phối hợp với `_build_document_summary_source`, `_extract_template_text` và trả dữ liệu về cho lớp gọi kế tiếp trong cùng luồng.
# Bản chất và tác dụng: hàm hỗ trợ tái sử dụng trong module; chủ yếu đọc, kiểm tra hoặc biến đổi dữ liệu.
def _extract_target_text(target, target_type: str) -> str:
    if target_type == ComplianceCheckResult.TARGET_DOCUMENT:
        try:
            text, _source_kind = _build_document_summary_source(target)
            return text
        except DocumentSummaryUnavailable:
            return ''
    return _extract_template_text(target)


# Là gì: `_serialize_result` là helper nội bộ của module `compliance.py`, phục vụ nhóm kiểm tra tuân thủ và đánh giá nội dung văn bản.
# Chức năng backend: Hàm chuyển đối tượng nội bộ thành dữ liệu có thể trả cho client; đầu vào được kiểm tra hoặc chuẩn hóa trước khi tạo kết quả.
# Vai trò với UI: Flutter không gọi trực tiếp hàm này; các endpoint cùng module dùng kết quả của nó để phục vụ màn hình kiểm tra tuân thủ.
# Mối liên hệ: Hàm phối hợp với `ComplianceCheckResultSerializer` và trả dữ liệu về cho lớp gọi kế tiếp trong cùng luồng.
# Bản chất và tác dụng: hàm hỗ trợ tái sử dụng trong module; chủ yếu đọc, kiểm tra hoặc biến đổi dữ liệu.
def _serialize_result(result: ComplianceCheckResult) -> dict:
    return ComplianceCheckResultSerializer(result).data


# Là gì: `compliance_check_run` là endpoint REST của nhóm kiểm tra tuân thủ và đánh giá nội dung văn bản; nó là điểm nhận request từ client đã đi qua router và lớp permission.
# Chức năng backend: Hàm kiểm tra điều kiện và trả kết quả để bước sau quyết định, đồng thời điều phối và thực thi chuỗi bước nghiệp vụ; đầu vào được kiểm tra hoặc chuẩn hóa trước khi tạo kết quả.
# Vai trò với UI: Kết quả được màn hình kiểm tra tuân thủ sử dụng trực tiếp để hiển thị dữ liệu, tải tệp hoặc cập nhật trạng thái thao tác.
# Mối liên hệ: Hàm phối hợp với `ComplianceCheckRunSerializer`, `serializer.is_valid`, `serializer.validated_data.get` và trả dữ liệu về cho lớp gọi kế tiếp trong cùng luồng.
# Bản chất và tác dụng: view mỏng ở biên HTTP; có side effect ghi cơ sở dữ liệu; chuyển kết quả thành HTTP response.
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def compliance_check_run(request):
    serializer = ComplianceCheckRunSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    target_type = serializer.validated_data['target_type']
    target_id = serializer.validated_data['target_id']
    prompt_id = serializer.validated_data['prompt_id']
    prompt_check_token = serializer.validated_data['prompt_check_token']
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

    prompt_text = '\n\n'.join(
        part.strip()
        for part in (
            str(prompt.system_content or ''),
            str(prompt.rules_content or ''),
        )
        if part.strip()
    )
    expected_check = prompt_check_expected_payload(
        user_id=request.user.pk,
        scope='compliance_check',
        context=f'compliance_{target_type}',
        prompt_role='criteria',
        prompt_text=prompt_text,
        target_id=target_id,
    )
    check_ok, check_why = verify_prompt_check_token(
        prompt_check_token,
        expected_check,
    )
    if not check_ok:
        return Response(
            {'detail': f'Cần kiểm tra lại prompt trước khi chạy kiểm tra ({check_why}).'},
            status=400,
        )

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


# Là gì: `compliance_check_history` là endpoint REST của nhóm kiểm tra tuân thủ và đánh giá nội dung văn bản; nó là điểm nhận request từ client đã đi qua router và lớp permission.
# Chức năng backend: Hàm kiểm tra điều kiện và trả kết quả để bước sau quyết định; đầu vào được kiểm tra hoặc chuẩn hóa trước khi tạo kết quả.
# Vai trò với UI: Kết quả được màn hình kiểm tra tuân thủ sử dụng trực tiếp để hiển thị dữ liệu, tải tệp hoặc cập nhật trạng thái thao tác.
# Mối liên hệ: Hàm phối hợp với `str.strip.lower`, `str.strip`, `request.GET.get` và trả dữ liệu về cho lớp gọi kế tiếp trong cùng luồng.
# Bản chất và tác dụng: view mỏng ở biên HTTP; chủ yếu đọc, kiểm tra hoặc biến đổi dữ liệu; chuyển kết quả thành HTTP response.
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


# Là gì: `compliance_check_detail` là endpoint REST của nhóm kiểm tra tuân thủ và đánh giá nội dung văn bản; nó là điểm nhận request từ client đã đi qua router và lớp permission.
# Chức năng backend: Hàm đọc hoặc xử lý một bản ghi cụ thể, đồng thời kiểm tra điều kiện và trả kết quả để bước sau quyết định; đầu vào được kiểm tra hoặc chuẩn hóa trước khi tạo kết quả.
# Vai trò với UI: Kết quả được màn hình kiểm tra tuân thủ sử dụng trực tiếp để hiển thị dữ liệu, tải tệp hoặc cập nhật trạng thái thao tác.
# Mối liên hệ: Hàm phối hợp với `get_object_or_404`, `ComplianceCheckResult.objects.select_related`, `_resolve_target` và trả dữ liệu về cho lớp gọi kế tiếp trong cùng luồng.
# Bản chất và tác dụng: view mỏng ở biên HTTP; chủ yếu đọc, kiểm tra hoặc biến đổi dữ liệu; chuyển kết quả thành HTTP response.
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
