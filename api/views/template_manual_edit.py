from django.http import FileResponse, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from accounts.permissions import get_template_detail_queryset
from document_templates.manual_edit_models import TemplateManualEditSession
from document_templates.manual_edit_services import (
    cancel_template_manual_edit_session,
    create_template_manual_edit_session,
    finish_template_manual_edit_session,
    get_template_manual_edit_session_for_user,
    get_template_manual_edit_session_for_wopi,
    touch_template_manual_edit_session,
    update_template_manual_edit_working_copy,
)
from documents.manual_edit_provider import get_manual_edit_provider_status

from ..serializers.template_manual_edit import (
    TemplateManualEditFinishSerializer,
    TemplateManualEditSessionSerializer,
)
from ..serializers.templates import TemplateDetailSerializer


def _resolve_wopi_access_token(request):
    return (
        request.GET.get('access_token')
        or request.POST.get('access_token')
        or request.headers.get('X-Access-Token', '')
    )


def _wopi_override(request):
    return (request.headers.get('X-WOPI-Override', '') or '').strip().upper()


def _allow_inactive_wopi_cleanup(request):
    return _wopi_override(request) in {'GET_LOCK', 'UNLOCK', 'UNLOCK_AND_RELOCK'}


def _wopi_lock_conflict(lock_value):
    response = HttpResponse(status=409)
    if lock_value:
        response['X-WOPI-Lock'] = lock_value
    return response


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


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def template_manual_edit_session_create(request, pk):
    template = get_object_or_404(get_template_detail_queryset(request.user), pk=pk)
    session, created = create_template_manual_edit_session(
        user=request.user,
        template=template,
    )
    serializer = TemplateManualEditSessionSerializer(session, context={'request': request})
    return Response(
        {
            'created_new': created,
            'session': serializer.data,
        },
        status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
    )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def template_manual_edit_provider_status(request):
    provider_status = get_manual_edit_provider_status()
    return Response(
        {
            'provider': provider_status.provider,
            'is_ready': provider_status.is_ready,
            'code': provider_status.code,
            'detail': provider_status.detail,
        }
    )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def template_manual_edit_session_detail(request, session_id):
    session = get_template_manual_edit_session_for_user(
        session_id=session_id,
        user=request.user,
    )
    serializer = TemplateManualEditSessionSerializer(session, context={'request': request})
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def template_manual_edit_session_heartbeat(request, session_id):
    session = get_template_manual_edit_session_for_user(
        session_id=session_id,
        user=request.user,
    )
    touch_template_manual_edit_session(session)
    session.refresh_from_db()
    serializer = TemplateManualEditSessionSerializer(session, context={'request': request})
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def template_manual_edit_session_finish(request, session_id):
    session = get_template_manual_edit_session_for_user(
        session_id=session_id,
        user=request.user,
    )
    serializer = TemplateManualEditFinishSerializer(data=request.data or {})
    serializer.is_valid(raise_exception=True)
    template = finish_template_manual_edit_session(
        session=session,
        user=request.user,
        change_note=serializer.validated_data.get('change_note', ''),
    )
    session.refresh_from_db()
    response_payload = {
        'session': TemplateManualEditSessionSerializer(
            session,
            context={'request': request},
        ).data,
        'template': TemplateDetailSerializer(
            template,
            context={'request': request},
        ).data,
    }
    return Response(response_payload)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def template_manual_edit_session_cancel(request, session_id):
    session = get_template_manual_edit_session_for_user(
        session_id=session_id,
        user=request.user,
    )
    cancel_template_manual_edit_session(session=session, user=request.user)
    session.refresh_from_db()
    return Response(
        TemplateManualEditSessionSerializer(
            session,
            context={'request': request},
        ).data
    )


@csrf_exempt
def template_manual_edit_wopi_file(request, file_id):
    access_token = _resolve_wopi_access_token(request)
    try:
        session = get_template_manual_edit_session_for_wopi(
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
        working_copy_name = (
            session.working_copy_file.name.rsplit('/', 1)[-1]
            if session.working_copy_file
            else 'template.docx'
        )
        size_bytes = _get_wopi_working_copy_size(session.working_copy_file)
        payload = {
            'BaseFileName': working_copy_name,
            'OwnerId': str(session.template.owner_id or ''),
            'Size': size_bytes,
            'UserId': str(session.created_by_id or ''),
            'UserFriendlyName': session.created_by.get_full_name()
            or session.created_by.username,
            'Version': f'{session.template.version}:{session.updated_at.isoformat()}',
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


@csrf_exempt
def template_manual_edit_wopi_contents(request, file_id):
    access_token = _resolve_wopi_access_token(request)
    try:
        session = get_template_manual_edit_session_for_wopi(
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
        if session.lock_token and session.lock_token != (
            request.headers.get('X-WOPI-Lock', '') or ''
        ).strip():
            return _wopi_lock_conflict(session.lock_token)
        update_template_manual_edit_working_copy(
            session=session,
            file_bytes=request.body,
            filename=session.working_copy_file.name if session.working_copy_file else '',
        )
        return HttpResponse(status=200)

    return HttpResponse(status=400)
