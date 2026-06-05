import os
import secrets
from io import BytesIO

from django.core.files.base import ContentFile
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from accounts.permissions import can_edit_template
from accounts.runtime_guard import CompanyRuntimeGuard
from accounts.tenancy import get_user_company
from documents.manual_edit_provider import (
    get_manual_edit_provider_status,
    manual_edit_provider_name,
)
from documents.runtime_helpers import _ascii_safe_name, _extract_text_from_docx

from .manual_edit_models import (
    TemplateManualEditSession,
    TemplateManualEditSessionEvent,
)
from .models import DocumentTemplate, STATUS_APPROVED
from .status_rules import _auto_status
from .versioning import create_template_version_snapshot


def _manual_edit_session_ttl_seconds():
    from django.conf import settings

    return max(
        int(getattr(settings, 'MANUAL_EDIT_SESSION_TTL_SECONDS', 3600) or 3600),
        300,
    )


def _next_session_expiry():
    return timezone.now() + timezone.timedelta(
        seconds=_manual_edit_session_ttl_seconds()
    )


def _append_session_event(session, *, level='info', step='', message='', payload=None):
    return TemplateManualEditSessionEvent.objects.create(
        session=session,
        level=level,
        step=step,
        session_status=session.status,
        message=message,
        payload=payload or {},
    )


def _delete_field_file(instance, field_name):
    file_field = getattr(instance, field_name, None)
    if not file_field:
        return
    name = getattr(file_field, 'name', '')
    if not name:
        return
    try:
        storage = file_field.storage
        if storage.exists(name):
            storage.delete(name)
    except Exception:
        pass


def _save_field_bytes(instance, field_name, *, filename, file_bytes):
    file_field = getattr(instance, field_name)
    old_name = getattr(file_field, 'name', '')
    if old_name:
        _delete_field_file(instance, field_name)
    file_field.save(filename, ContentFile(file_bytes), save=False)


def _read_file_field_bytes(file_field, *, detail):
    try:
        with file_field.open('rb') as source_file:
            return source_file.read()
    except Exception as exc:
        raise ValidationError({'detail': detail}) from exc


def _working_copy_filename(template, session, source_name):
    extension = '.docx'
    raw_name = os.path.basename(str(source_name or '')).strip()
    if '.' in raw_name:
        extension = f".{raw_name.rsplit('.', 1)[-1].lower()}"
    return f'{_ascii_safe_name(template.title)}_manual_{session.id}{extension}'


def _bump_template_version(version):
    try:
        parts = str(version or '1.0').split('.')
        major = parts[0]
        minor = int(parts[1]) + 1 if len(parts) > 1 else 1
        return f'{major}.{minor}'
    except Exception:
        return str(version or '1.0')


def _apply_auto_approval_metadata(template, actor):
    if template.status != STATUS_APPROVED:
        template.approved_by = None
        template.approved_at = None
        template.approver_note = ''
        return
    template.approved_by = actor
    template.approved_at = timezone.now()
    template.approver_note = template.approver_note or ''


def _delete_session_working_copy(session):
    _delete_field_file(session, 'working_copy_file')
    if session.working_copy_file:
        session.working_copy_file = None
        session.save(update_fields=['working_copy_file', 'updated_at'])


def _require_manual_edit_provider():
    provider_status = get_manual_edit_provider_status()
    if not provider_status.is_ready:
        raise ValidationError({'detail': provider_status.detail})


def _ensure_template_docx_source(template):
    docx_source_name = (
        getattr(template.docx_file, 'name', '') if getattr(template, 'docx_file', None) else ''
    )
    has_docx_source = bool(docx_source_name)
    if template.source_type == DocumentTemplate.SOURCE_DOCX and has_docx_source:
        return template.docx_file.name
    try:
        docx_buffer = template.render_as_docx({}, allow_content_fallback=True)
        docx_bytes = docx_buffer.read()
    except Exception as exc:
        raise ValidationError(
            {'detail': f'Khong the tao DOCX goc cho mau de mo trinh sua thu cong: {exc}'}
        ) from exc
    if not docx_bytes:
        raise ValidationError(
            {'detail': 'Mau chua co noi dung hop le de mo trinh sua thu cong.'}
        )
    filename = f'{_ascii_safe_name(template.title)}.docx'
    _save_field_bytes(
        template,
        'docx_file',
        filename=filename,
        file_bytes=docx_bytes,
    )
    template.source_type = DocumentTemplate.SOURCE_DOCX
    template.save(update_fields=['docx_file', 'source_type', 'updated_at'])
    return template.docx_file.name


def expire_stale_template_manual_edit_sessions(*, template=None):
    now = timezone.now()
    qs = TemplateManualEditSession.objects.filter(
        status__in=TemplateManualEditSession.active_statuses(),
        expires_at__lte=now,
    )
    if template is not None:
        qs = qs.filter(template=template)
    expired_ids = list(qs.values_list('id', flat=True))
    if not expired_ids:
        return 0
    qs.update(status=TemplateManualEditSession.Status.EXPIRED, lock_token='', updated_at=now)
    for session in TemplateManualEditSession.objects.filter(pk__in=expired_ids):
        _append_session_event(
            session,
            level='warning',
            step='expire',
            message='Template manual edit session expired.',
        )
        _delete_session_working_copy(session)
    return len(expired_ids)


def get_active_template_manual_edit_session(template, *, include_same_user=None):
    expire_stale_template_manual_edit_sessions(template=template)
    qs = (
        TemplateManualEditSession.objects.select_related('created_by')
        .filter(
            template=template,
            status__in=TemplateManualEditSession.active_statuses(),
            expires_at__gt=timezone.now(),
        )
        .order_by('-created_at')
    )
    if include_same_user is None:
        return qs.first()
    if include_same_user and include_same_user.is_authenticated:
        qs = qs.filter(created_by=include_same_user)
    return qs.first()


def touch_template_manual_edit_session(session):
    if not session.is_active:
        return session
    now = timezone.now()
    session.last_activity_at = now
    session.expires_at = _next_session_expiry()
    session.save(update_fields=['last_activity_at', 'expires_at', 'updated_at'])
    return session


def create_template_manual_edit_session(*, user, template):
    _require_manual_edit_provider()
    CompanyRuntimeGuard.assert_same_company(
        user,
        template,
        detail='Mau manual edit dang tro sang cong ty khac.',
    )
    active_session = get_active_template_manual_edit_session(template)
    if active_session is not None:
        if user.is_superuser or active_session.created_by_id == user.id:
            touch_template_manual_edit_session(active_session)
            return active_session, False
        raise ValidationError(
            {'detail': 'Mau van ban dang duoc nguoi dung khac chinh sua thu cong.'}
        )
    if not can_edit_template(user, template):
        raise PermissionDenied('You do not have permission to edit this template.')

    _ensure_template_docx_source(template)
    source_name = template.docx_file.name
    source_bytes = _read_file_field_bytes(
        template.docx_file,
        detail='Khong the mo file DOCX goc cua mau de chinh sua thu cong.',
    )
    now = timezone.now()
    with transaction.atomic():
        session = TemplateManualEditSession.objects.create(
            template=template,
            company=template.company,
            created_by=user,
            status=TemplateManualEditSession.Status.ACTIVE,
            provider=manual_edit_provider_name(),
            access_token=secrets.token_urlsafe(32),
            base_version_label=template.version,
            working_copy_updated_at=None,
            expires_at=_next_session_expiry(),
            last_activity_at=now,
        )
        _save_field_bytes(
            session,
            'working_copy_file',
            filename=_working_copy_filename(template, session, source_name),
            file_bytes=source_bytes,
        )
        session.save(update_fields=['working_copy_file', 'updated_at'])
    _append_session_event(
        session,
        step='create',
        message='Template manual edit session created.',
        payload={
            'template_version': template.version,
            'provider': session.provider,
        },
    )
    return session, True


def get_template_manual_edit_session_for_user(*, session_id, user):
    queryset = TemplateManualEditSession.objects.select_related('template', 'created_by')
    company = get_user_company(user)
    if company is not None:
        queryset = queryset.filter(company=company)
    session = queryset.filter(pk=session_id).first()
    if session is None:
        raise ValidationError({'detail': 'Template manual edit session does not exist.'})
    CompanyRuntimeGuard.assert_same_company(
        session,
        session.template,
        detail='Template manual edit session dang tro sang cong ty khac.',
    )
    CompanyRuntimeGuard.assert_file_field(
        session.working_copy_file,
        target=session,
        detail='Working copy template manual edit dang tro sang cong ty khac.',
    )
    if (
        not user.is_superuser
        and session.created_by_id != user.id
        and session.template.owner_id != user.id
    ):
        raise PermissionDenied(
            'You do not have permission to access this template manual edit session.'
        )
    if session.is_active and session.expires_at <= timezone.now():
        expire_stale_template_manual_edit_sessions(template=session.template)
        session.refresh_from_db()
    return session


def get_template_manual_edit_session_for_wopi(
    *,
    wopi_file_id,
    access_token,
    allow_inactive=False,
    touch_activity=True,
):
    if not access_token:
        raise ValidationError({'detail': 'Missing access token.'})
    session = (
        TemplateManualEditSession.objects.select_related('template', 'created_by')
        .filter(wopi_file_id=wopi_file_id, access_token=access_token)
        .first()
    )
    if session is None:
        raise ValidationError({'detail': 'Invalid template manual edit access token.'})
    CompanyRuntimeGuard.assert_same_company(
        session,
        session.template,
        detail='Template manual edit WOPI session dang tro sang cong ty khac.',
    )
    CompanyRuntimeGuard.assert_file_field(
        session.working_copy_file,
        target=session,
        detail='Working copy template WOPI dang tro sang cong ty khac.',
    )
    if session.expires_at <= timezone.now() or not session.is_active:
        expire_stale_template_manual_edit_sessions(template=session.template)
        session.refresh_from_db()
        if not allow_inactive:
            raise ValidationError(
                {'detail': 'Template manual edit session is no longer active.'}
            )
        return session
    if touch_activity:
        touch_template_manual_edit_session(session)
        session.refresh_from_db()
    return session


def update_template_manual_edit_working_copy(*, session, file_bytes, filename=''):
    if not session.is_active:
        raise ValidationError({'detail': 'Template manual edit session is not active.'})
    safe_name = _working_copy_filename(
        session.template,
        session,
        filename or session.working_copy_file.name,
    )
    _save_field_bytes(
        session,
        'working_copy_file',
        filename=safe_name,
        file_bytes=file_bytes,
    )
    working_copy_updated_at = timezone.now()
    touch_template_manual_edit_session(session)
    session.working_copy_updated_at = working_copy_updated_at
    session.save(
        update_fields=[
            'working_copy_file',
            'working_copy_updated_at',
            'last_activity_at',
            'expires_at',
            'updated_at',
        ]
    )
    _append_session_event(
        session,
        step='wopi_put_file',
        message='Template working copy updated from web editor.',
        payload={'size_bytes': len(file_bytes)},
    )
    return session


def finish_template_manual_edit_session(*, session, user, change_note=''):
    if not user.is_superuser and session.created_by_id != user.id:
        raise PermissionDenied(
            'You do not have permission to finish this template manual edit session.'
        )
    if session.status not in [
        TemplateManualEditSession.Status.ACTIVE,
        TemplateManualEditSession.Status.SAVING,
    ]:
        raise ValidationError({'detail': 'Template manual edit session is not active.'})
    if not session.working_copy_file:
        raise ValidationError({'detail': 'Template manual edit working copy is missing.'})
    if session.expires_at <= timezone.now():
        expire_stale_template_manual_edit_sessions(template=session.template)
        raise ValidationError({'detail': 'Template manual edit session has expired.'})

    now = timezone.now()
    previous_status = session.status
    session.status = TemplateManualEditSession.Status.SAVING
    session.last_activity_at = now
    session.expires_at = _next_session_expiry()
    session.save(update_fields=['status', 'last_activity_at', 'expires_at', 'updated_at'])

    try:
        file_bytes = _read_file_field_bytes(
            session.working_copy_file,
            detail='Unable to read the edited DOCX working copy.',
        )
    except ValidationError:
        session.status = previous_status
        session.save(update_fields=['status', 'updated_at'])
        raise

    current_template_bytes = _read_file_field_bytes(
        session.template.docx_file,
        detail='Unable to read the current DOCX template before committing the manual edit session.',
    )
    if file_bytes == current_template_bytes:
        session.status = previous_status
        session.save(update_fields=['status', 'updated_at'])
        _append_session_event(
            session,
            level='warning',
            step='finish_blocked',
            message='Template manual edit finish was blocked because no saved working-copy changes were detected.',
        )
        raise ValidationError(
            {
                'detail': (
                    'Khong co thay doi moi nao da duoc luu tu trinh sua web. '
                    'Hay doi editor dong bo xong hoac bam luu trong editor roi thu lai.'
                )
            }
        )

    extracted_text = _extract_text_from_docx(BytesIO(file_bytes))
    template = session.template
    effective_change_note = change_note.strip() or 'Manual web editor revision'

    try:
        with transaction.atomic():
            create_template_version_snapshot(
                template,
                created_by=user,
                change_note=effective_change_note,
            )
            template.version = _bump_template_version(template.version)
            template.content = extracted_text
            _save_field_bytes(
                template,
                'docx_file',
                filename=f'{_ascii_safe_name(template.title)}.docx',
                file_bytes=file_bytes,
            )
            template.source_type = DocumentTemplate.SOURCE_DOCX
            template.status = _auto_status(
                template.source_type,
                template.visibility,
                user,
                template.group,
            )
            _apply_auto_approval_metadata(template, user)
            template.save(
                update_fields=[
                    'version',
                    'content',
                    'docx_file',
                    'source_type',
                    'status',
                    'approved_by',
                    'approved_at',
                    'approver_note',
                    'updated_at',
                ]
            )

            session.status = TemplateManualEditSession.Status.FINISHED
            session.finished_at = timezone.now()
            session.lock_token = ''
            session.lock_token_refreshed_at = None
            session.save(
                update_fields=[
                    'status',
                    'finished_at',
                    'lock_token',
                    'lock_token_refreshed_at',
                    'updated_at',
                ],
            )
    except Exception:
        session.status = previous_status
        session.save(update_fields=['status', 'updated_at'])
        raise

    _append_session_event(
        session,
        step='finish',
        message='Template manual edit session committed as a new template revision.',
        payload={
            'template_version': template.version,
            'change_note': effective_change_note,
        },
    )
    _delete_session_working_copy(session)
    return template


def cancel_template_manual_edit_session(*, session, user):
    if not user.is_superuser and session.created_by_id != user.id:
        raise PermissionDenied(
            'You do not have permission to cancel this template manual edit session.'
        )
    if session.status not in TemplateManualEditSession.active_statuses():
        return session
    session.status = TemplateManualEditSession.Status.CANCELLED
    session.cancelled_at = timezone.now()
    session.lock_token = ''
    session.lock_token_refreshed_at = None
    session.save(
        update_fields=[
            'status',
            'cancelled_at',
            'lock_token',
            'lock_token_refreshed_at',
            'updated_at',
        ],
    )
    _append_session_event(
        session,
        level='warning',
        step='cancel',
        message='Template manual edit session cancelled.',
    )
    _delete_session_working_copy(session)
    return session
