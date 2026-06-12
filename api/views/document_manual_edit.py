from django.http import FileResponse, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from accounts.permissions import get_document_detail_queryset
from documents.edit_lock_state import get_document_edit_lock_state
from documents.manual_edit_models import DocumentManualEditSession
from documents.manual_edit_provider import (
    browser_origin_from_request,
    get_manual_edit_provider_status,
    manual_edit_postmessage_origin,
)
from documents.manual_edit_services import (
    cancel_manual_edit_session,
    create_manual_edit_session,
    finish_manual_edit_session,
    get_manual_edit_session_for_user,
    get_manual_edit_session_for_wopi,
    touch_manual_edit_session,
    update_manual_edit_working_copy,
)

from ..serializers.document_manual_edit import (
    DocumentManualEditFinishSerializer,
    DocumentManualEditSessionSerializer,
)
from ..serializers.documents import DocumentDetailSerializer


# Là gì: `_resolve_wopi_access_token` là helper nội bộ của module `document_manual_edit.py`, phục vụ nhóm chỉnh sửa thủ công nội dung và phiên bản văn bản.
# Chức năng backend: Hàm xác định đối tượng hoặc cấu hình hiệu lực từ ngữ cảnh hiện tại; đầu vào được kiểm tra hoặc chuẩn hóa trước khi tạo kết quả.
# Vai trò với UI: Flutter không gọi trực tiếp hàm này; các endpoint cùng module dùng kết quả của nó để phục vụ trình chỉnh sửa văn bản trên Flutter.
# Mối liên hệ: Hàm phối hợp với `request.GET.get`, `request.POST.get`, `request.headers.get` và trả dữ liệu về cho lớp gọi kế tiếp trong cùng luồng.
# Bản chất và tác dụng: hàm hỗ trợ tái sử dụng trong module; chủ yếu đọc, kiểm tra hoặc biến đổi dữ liệu.
def _resolve_wopi_access_token(request):
    return (
        request.GET.get('access_token')
        or request.POST.get('access_token')
        or request.headers.get('X-Access-Token', '')
    )


# Là gì: `_wopi_override` là helper nội bộ của module `document_manual_edit.py`, phục vụ nhóm chỉnh sửa thủ công nội dung và phiên bản văn bản.
# Chức năng backend: Hàm xử lý phần việc `wopi override` theo dữ liệu và ngữ cảnh được truyền vào; đầu vào được kiểm tra hoặc chuẩn hóa trước khi tạo kết quả.
# Vai trò với UI: Flutter không gọi trực tiếp hàm này; các endpoint cùng module dùng kết quả của nó để phục vụ trình chỉnh sửa văn bản trên Flutter.
# Mối liên hệ: Hàm phối hợp với `strip.upper`, `strip`, `request.headers.get` và trả dữ liệu về cho lớp gọi kế tiếp trong cùng luồng.
# Bản chất và tác dụng: hàm hỗ trợ tái sử dụng trong module; chủ yếu đọc, kiểm tra hoặc biến đổi dữ liệu.
def _wopi_override(request):
    return (request.headers.get('X-WOPI-Override', '') or '').strip().upper()


# Là gì: `_allow_inactive_wopi_cleanup` là helper nội bộ của module `document_manual_edit.py`, phục vụ nhóm chỉnh sửa thủ công nội dung và phiên bản văn bản.
# Chức năng backend: Hàm dọn tài nguyên tạm hoặc dữ liệu không còn hiệu lực; đầu vào được kiểm tra hoặc chuẩn hóa trước khi tạo kết quả.
# Vai trò với UI: Flutter không gọi trực tiếp hàm này; các endpoint cùng module dùng kết quả của nó để phục vụ trình chỉnh sửa văn bản trên Flutter.
# Mối liên hệ: Hàm phối hợp với `_wopi_override` và trả dữ liệu về cho lớp gọi kế tiếp trong cùng luồng.
# Bản chất và tác dụng: hàm hỗ trợ tái sử dụng trong module; chủ yếu đọc, kiểm tra hoặc biến đổi dữ liệu.
def _allow_inactive_wopi_cleanup(request):
    return _wopi_override(request) in {'GET_LOCK', 'UNLOCK', 'UNLOCK_AND_RELOCK'}


# Là gì: `_wopi_lock_conflict` là helper nội bộ của module `document_manual_edit.py`, phục vụ nhóm chỉnh sửa thủ công nội dung và phiên bản văn bản.
# Chức năng backend: Hàm xử lý phần việc `wopi lock conflict` theo dữ liệu và ngữ cảnh được truyền vào; đầu vào được kiểm tra hoặc chuẩn hóa trước khi tạo kết quả.
# Vai trò với UI: Flutter không gọi trực tiếp hàm này; các endpoint cùng module dùng kết quả của nó để phục vụ trình chỉnh sửa văn bản trên Flutter.
# Mối liên hệ: Hàm phối hợp với `HttpResponse` và trả dữ liệu về cho lớp gọi kế tiếp trong cùng luồng.
# Bản chất và tác dụng: hàm hỗ trợ tái sử dụng trong module; chủ yếu đọc, kiểm tra hoặc biến đổi dữ liệu; chuyển kết quả thành HTTP response.
def _wopi_lock_conflict(lock_value):
    response = HttpResponse(status=409)
    if lock_value:
        response['X-WOPI-Lock'] = lock_value
    return response


# Là gì: `_handle_wopi_lock_override` là helper nội bộ của module `document_manual_edit.py`, phục vụ nhóm chỉnh sửa thủ công nội dung và phiên bản văn bản.
# Chức năng backend: Hàm xử lý phần việc `handle wopi lock override` theo dữ liệu và ngữ cảnh được truyền vào; đầu vào được kiểm tra hoặc chuẩn hóa trước khi tạo kết quả.
# Vai trò với UI: Flutter không gọi trực tiếp hàm này; các endpoint cùng module dùng kết quả của nó để phục vụ trình chỉnh sửa văn bản trên Flutter.
# Mối liên hệ: Hàm phối hợp với `_wopi_override`, `strip`, `request.headers.get` và trả dữ liệu về cho lớp gọi kế tiếp trong cùng luồng.
# Bản chất và tác dụng: hàm hỗ trợ tái sử dụng trong module; có side effect ghi cơ sở dữ liệu; chuyển kết quả thành HTTP response.
def _handle_wopi_lock_override(session, request):
    override = _wopi_override(request)
    requested_lock = (request.headers.get('X-WOPI-Lock', '') or '').strip()
    old_lock = (request.headers.get('X-WOPI-OldLock', '') or '').strip()
    if not override or override == 'PUT':
        return None
    if override == 'GET_LOCK':
        response = HttpResponse(status=200)
        if session.lock_token:
            response['X-WOPI-Lock'] = session.lock_token
        return response
    if override == 'LOCK':
        if session.lock_token and session.lock_token != requested_lock:
            return _wopi_lock_conflict(session.lock_token)
        session.lock_token = requested_lock
        session.lock_token_refreshed_at = session.last_activity_at
        session.save(update_fields=['lock_token', 'lock_token_refreshed_at', 'updated_at'])
        return HttpResponse(status=200)
    if override == 'REFRESH_LOCK':
        if session.lock_token != requested_lock:
            return _wopi_lock_conflict(session.lock_token)
        session.lock_token_refreshed_at = session.last_activity_at
        session.save(update_fields=['lock_token_refreshed_at', 'updated_at'])
        return HttpResponse(status=200)
    if override == 'UNLOCK':
        if not session.is_active or not session.lock_token:
            session.lock_token = ''
            session.lock_token_refreshed_at = None
            session.save(update_fields=['lock_token', 'lock_token_refreshed_at', 'updated_at'])
            return HttpResponse(status=200)
        if session.lock_token != requested_lock:
            return _wopi_lock_conflict(session.lock_token)
        session.lock_token = ''
        session.lock_token_refreshed_at = None
        session.save(update_fields=['lock_token', 'lock_token_refreshed_at', 'updated_at'])
        return HttpResponse(status=200)
    if override == 'UNLOCK_AND_RELOCK':
        if not session.is_active or not session.lock_token:
            session.lock_token = requested_lock
            session.lock_token_refreshed_at = session.last_activity_at
            session.save(update_fields=['lock_token', 'lock_token_refreshed_at', 'updated_at'])
            return HttpResponse(status=200)
        if session.lock_token != old_lock:
            return _wopi_lock_conflict(session.lock_token)
        session.lock_token = requested_lock
        session.lock_token_refreshed_at = session.last_activity_at
        session.save(update_fields=['lock_token', 'lock_token_refreshed_at', 'updated_at'])
        return HttpResponse(status=200)
    if override == 'PUT_RELATIVE':
        return HttpResponse(status=501)
    return HttpResponse(status=400)


# Là gì: `_get_wopi_working_copy_size` là helper nội bộ của module `document_manual_edit.py`, phục vụ nhóm chỉnh sửa thủ công nội dung và phiên bản văn bản.
# Chức năng backend: Hàm đọc và trả về dữ liệu cần thiết; đầu vào được kiểm tra hoặc chuẩn hóa trước khi tạo kết quả.
# Vai trò với UI: Flutter không gọi trực tiếp hàm này; các endpoint cùng module dùng kết quả của nó để phục vụ trình chỉnh sửa văn bản trên Flutter.
# Mối liên hệ: Hàm phối hợp với `file_field.open`, `handle.read` và trả dữ liệu về cho lớp gọi kế tiếp trong cùng luồng.
# Bản chất và tác dụng: hàm hỗ trợ tái sử dụng trong module; có side effect lên tệp hoặc storage.
def _get_wopi_working_copy_size(file_field):
    if not file_field:
        return 0
    try:
        return file_field.size
    except Exception:
        try:
            with file_field.open('rb') as handle:
                return len(handle.read())
        except Exception:
            return 0


# Là gì: `document_manual_edit_session_create` là endpoint REST của nhóm chỉnh sửa thủ công nội dung và phiên bản văn bản; nó là điểm nhận request từ client đã đi qua router và lớp permission.
# Chức năng backend: Hàm kiểm tra đầu vào và tạo dữ liệu mới; đầu vào được kiểm tra hoặc chuẩn hóa trước khi tạo kết quả.
# Vai trò với UI: Kết quả được trình chỉnh sửa văn bản trên Flutter sử dụng trực tiếp để hiển thị dữ liệu, tải tệp hoặc cập nhật trạng thái thao tác.
# Mối liên hệ: Hàm phối hợp với `get_object_or_404`, `get_document_detail_queryset`, `create_manual_edit_session` và trả dữ liệu về cho lớp gọi kế tiếp trong cùng luồng.
# Bản chất và tác dụng: view mỏng ở biên HTTP; có side effect ghi cơ sở dữ liệu; chuyển kết quả thành HTTP response.
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def document_manual_edit_session_create(request, pk):
    document = get_object_or_404(get_document_detail_queryset(request.user), pk=pk)
    session, created = create_manual_edit_session(user=request.user, document=document)
    # Ghi lai origin THAT cua trinh duyet (request nay den tu browser) de CheckFileInfo
    # tra dung PostMessageOrigin -> Collabora postMessage ve duoc frame cha.
    browser_origin = browser_origin_from_request(request)
    if browser_origin and session.post_message_origin != browser_origin:
        session.post_message_origin = browser_origin
        session.save(update_fields=['post_message_origin', 'updated_at'])
    serializer = DocumentManualEditSessionSerializer(session, context={'request': request})
    return Response(
        {
            'created_new': created,
            'session': serializer.data,
        },
        status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
    )


# Là gì: `document_manual_edit_provider_status` là endpoint REST của nhóm chỉnh sửa thủ công nội dung và phiên bản văn bản; nó là điểm nhận request từ client đã đi qua router và lớp permission.
# Chức năng backend: Hàm xử lý phần việc `document manual edit provider status` theo dữ liệu và ngữ cảnh được truyền vào; đầu vào được kiểm tra hoặc chuẩn hóa trước khi tạo kết quả.
# Vai trò với UI: Kết quả được trình chỉnh sửa văn bản trên Flutter sử dụng trực tiếp để hiển thị dữ liệu, tải tệp hoặc cập nhật trạng thái thao tác.
# Mối liên hệ: Hàm phối hợp với `get_manual_edit_provider_status` và trả dữ liệu về cho lớp gọi kế tiếp trong cùng luồng.
# Bản chất và tác dụng: view mỏng ở biên HTTP; chủ yếu đọc, kiểm tra hoặc biến đổi dữ liệu; chuyển kết quả thành HTTP response.
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def document_manual_edit_provider_status(request):
    provider_status = get_manual_edit_provider_status()
    return Response(
        {
            'provider': provider_status.provider,
            'is_ready': provider_status.is_ready,
            'code': provider_status.code,
            'detail': provider_status.detail,
        }
    )


# Là gì: `document_manual_edit_session_detail` là endpoint REST của nhóm chỉnh sửa thủ công nội dung và phiên bản văn bản; nó là điểm nhận request từ client đã đi qua router và lớp permission.
# Chức năng backend: Hàm đọc hoặc xử lý một bản ghi cụ thể; đầu vào được kiểm tra hoặc chuẩn hóa trước khi tạo kết quả.
# Vai trò với UI: Kết quả được trình chỉnh sửa văn bản trên Flutter sử dụng trực tiếp để hiển thị dữ liệu, tải tệp hoặc cập nhật trạng thái thao tác.
# Mối liên hệ: Hàm phối hợp với `get_manual_edit_session_for_user`, `DocumentManualEditSessionSerializer` và trả dữ liệu về cho lớp gọi kế tiếp trong cùng luồng.
# Bản chất và tác dụng: view mỏng ở biên HTTP; chủ yếu đọc, kiểm tra hoặc biến đổi dữ liệu; chuyển kết quả thành HTTP response.
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def document_manual_edit_session_detail(request, session_id):
    session = get_manual_edit_session_for_user(session_id=session_id, user=request.user)
    serializer = DocumentManualEditSessionSerializer(session, context={'request': request})
    return Response(serializer.data)


# Là gì: `document_manual_edit_session_heartbeat` là endpoint REST của nhóm chỉnh sửa thủ công nội dung và phiên bản văn bản; nó là điểm nhận request từ client đã đi qua router và lớp permission.
# Chức năng backend: Hàm xử lý phần việc `document manual edit session heartbeat` theo dữ liệu và ngữ cảnh được truyền vào; đầu vào được kiểm tra hoặc chuẩn hóa trước khi tạo kết quả.
# Vai trò với UI: Kết quả được trình chỉnh sửa văn bản trên Flutter sử dụng trực tiếp để hiển thị dữ liệu, tải tệp hoặc cập nhật trạng thái thao tác.
# Mối liên hệ: Hàm phối hợp với `get_manual_edit_session_for_user`, `touch_manual_edit_session`, `session.refresh_from_db` và trả dữ liệu về cho lớp gọi kế tiếp trong cùng luồng.
# Bản chất và tác dụng: view mỏng ở biên HTTP; chủ yếu đọc, kiểm tra hoặc biến đổi dữ liệu; chuyển kết quả thành HTTP response.
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def document_manual_edit_session_heartbeat(request, session_id):
    session = get_manual_edit_session_for_user(session_id=session_id, user=request.user)
    touch_manual_edit_session(session)
    session.refresh_from_db()
    serializer = DocumentManualEditSessionSerializer(session, context={'request': request})
    return Response(serializer.data)


# Là gì: `document_manual_edit_session_finish` là endpoint REST của nhóm chỉnh sửa thủ công nội dung và phiên bản văn bản; nó là điểm nhận request từ client đã đi qua router và lớp permission.
# Chức năng backend: Hàm xử lý phần việc `document manual edit session finish` theo dữ liệu và ngữ cảnh được truyền vào; đầu vào được kiểm tra hoặc chuẩn hóa trước khi tạo kết quả.
# Vai trò với UI: Kết quả được trình chỉnh sửa văn bản trên Flutter sử dụng trực tiếp để hiển thị dữ liệu, tải tệp hoặc cập nhật trạng thái thao tác.
# Mối liên hệ: Hàm phối hợp với `get_manual_edit_session_for_user`, `DocumentManualEditFinishSerializer`, `serializer.is_valid` và trả dữ liệu về cho lớp gọi kế tiếp trong cùng luồng.
# Bản chất và tác dụng: view mỏng ở biên HTTP; chủ yếu đọc, kiểm tra hoặc biến đổi dữ liệu; chuyển kết quả thành HTTP response.
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def document_manual_edit_session_finish(request, session_id):
    session = get_manual_edit_session_for_user(session_id=session_id, user=request.user)
    serializer = DocumentManualEditFinishSerializer(data=request.data or {})
    serializer.is_valid(raise_exception=True)
    finish_manual_edit_session(
        session=session,
        user=request.user,
        change_note=serializer.validated_data.get('change_note', ''),
    )
    session.refresh_from_db()
    document = get_object_or_404(get_document_detail_queryset(request.user), pk=session.document_id)
    response_payload = {
        'session': DocumentManualEditSessionSerializer(session, context={'request': request}).data,
        'document': DocumentDetailSerializer(document, context={'request': request}).data,
    }
    return Response(response_payload)


# Là gì: `document_manual_edit_session_cancel` là endpoint REST của nhóm chỉnh sửa thủ công nội dung và phiên bản văn bản; nó là điểm nhận request từ client đã đi qua router và lớp permission.
# Chức năng backend: Hàm yêu cầu dừng một tiến trình đang chờ hoặc đang chạy; đầu vào được kiểm tra hoặc chuẩn hóa trước khi tạo kết quả.
# Vai trò với UI: Kết quả được trình chỉnh sửa văn bản trên Flutter sử dụng trực tiếp để hiển thị dữ liệu, tải tệp hoặc cập nhật trạng thái thao tác.
# Mối liên hệ: Hàm phối hợp với `get_manual_edit_session_for_user`, `cancel_manual_edit_session`, `session.refresh_from_db` và trả dữ liệu về cho lớp gọi kế tiếp trong cùng luồng.
# Bản chất và tác dụng: view mỏng ở biên HTTP; chủ yếu đọc, kiểm tra hoặc biến đổi dữ liệu; chuyển kết quả thành HTTP response.
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def document_manual_edit_session_cancel(request, session_id):
    session = get_manual_edit_session_for_user(session_id=session_id, user=request.user)
    cancel_manual_edit_session(session=session, user=request.user)
    session.refresh_from_db()
    return Response(DocumentManualEditSessionSerializer(session, context={'request': request}).data)


# Là gì: `document_manual_edit_wopi_file` là hàm điều phối nghiệp vụ của module `document_manual_edit.py`, thuộc nhóm chỉnh sửa thủ công nội dung và phiên bản văn bản.
# Chức năng backend: Hàm xử lý phần việc `document manual edit wopi file` theo dữ liệu và ngữ cảnh được truyền vào; đầu vào được kiểm tra hoặc chuẩn hóa trước khi tạo kết quả.
# Vai trò với UI: Flutter không gọi trực tiếp hàm này; các endpoint cùng module dùng kết quả của nó để phục vụ trình chỉnh sửa văn bản trên Flutter.
# Mối liên hệ: Hàm phối hợp với `_resolve_wopi_access_token`, `get_manual_edit_session_for_wopi`, `JsonResponse` và trả dữ liệu về cho lớp gọi kế tiếp trong cùng luồng.
# Bản chất và tác dụng: hàm hỗ trợ tái sử dụng trong module; chủ yếu đọc, kiểm tra hoặc biến đổi dữ liệu; chuyển kết quả thành HTTP response.
@csrf_exempt
def document_manual_edit_wopi_file(request, file_id):
    access_token = _resolve_wopi_access_token(request)
    try:
        session = get_manual_edit_session_for_wopi(
            wopi_file_id=file_id,
            access_token=access_token,
            allow_inactive=_allow_inactive_wopi_cleanup(request),
            touch_activity=request.method == 'GET',
        )
    except ValidationError as exc:
        return JsonResponse(exc.detail, status=401)
    except PermissionDenied as exc:
        return JsonResponse({'detail': str(exc)}, status=403)

    if request.method == 'GET':
        working_copy_name = session.working_copy_file.name.rsplit('/', 1)[-1] if session.working_copy_file else 'document.docx'
        size_bytes = _get_wopi_working_copy_size(session.working_copy_file)
        payload = {
            'BaseFileName': working_copy_name,
            'OwnerId': str(session.document.owner_id or ''),
            'Size': size_bytes,
            'UserId': str(session.created_by_id or ''),
            'UserFriendlyName': session.created_by.get_full_name() or session.created_by.username,
            'Version': f'{session.document.version_number}:{session.updated_at.isoformat()}',
            'PostMessageOrigin': session.post_message_origin or manual_edit_postmessage_origin(request),
            'UserCanWrite': True,
            'ReadOnly': False,
            'SupportsUpdate': True,
            'SupportsLocks': True,
            'SupportsGetLock': True,
            'SupportsRename': False,
            'SupportsDeleteFile': False,
            'SupportsUserInfo': True,
        }
        return JsonResponse(payload)

    response = _handle_wopi_lock_override(session, request)
    if response is not None:
        return response
    return HttpResponse(status=400)


# Là gì: `document_manual_edit_wopi_contents` là hàm điều phối nghiệp vụ của module `document_manual_edit.py`, thuộc nhóm chỉnh sửa thủ công nội dung và phiên bản văn bản.
# Chức năng backend: Hàm xử lý phần việc `document manual edit wopi contents` theo dữ liệu và ngữ cảnh được truyền vào; đầu vào được kiểm tra hoặc chuẩn hóa trước khi tạo kết quả.
# Vai trò với UI: Flutter không gọi trực tiếp hàm này; các endpoint cùng module dùng kết quả của nó để phục vụ trình chỉnh sửa văn bản trên Flutter.
# Mối liên hệ: Hàm phối hợp với `_resolve_wopi_access_token`, `get_manual_edit_session_for_wopi`, `JsonResponse` và trả dữ liệu về cho lớp gọi kế tiếp trong cùng luồng.
# Bản chất và tác dụng: hàm hỗ trợ tái sử dụng trong module; có side effect lên tệp hoặc storage; chuyển kết quả thành HTTP response.
@csrf_exempt
def document_manual_edit_wopi_contents(request, file_id):
    access_token = _resolve_wopi_access_token(request)
    try:
        session = get_manual_edit_session_for_wopi(
            wopi_file_id=file_id,
            access_token=access_token,
            allow_inactive=_allow_inactive_wopi_cleanup(request),
            touch_activity=request.method == 'GET',
        )
    except ValidationError as exc:
        return JsonResponse(exc.detail, status=401)
    except PermissionDenied as exc:
        return JsonResponse({'detail': str(exc)}, status=403)

    if request.method == 'GET':
        if not session.working_copy_file:
            return HttpResponse(status=404)
        return FileResponse(session.working_copy_file.open('rb'), as_attachment=False)

    response = _handle_wopi_lock_override(session, request)
    if response is not None:
        return response

    if (request.headers.get('X-WOPI-Override', '') or '').strip().upper() == 'PUT':
        if session.lock_token and session.lock_token != (request.headers.get('X-WOPI-Lock', '') or '').strip():
            return _wopi_lock_conflict(session.lock_token)
        update_manual_edit_working_copy(
            session=session,
            file_bytes=request.body,
            filename=session.working_copy_file.name if session.working_copy_file else '',
        )
        return HttpResponse(status=200)

    return HttpResponse(status=400)
