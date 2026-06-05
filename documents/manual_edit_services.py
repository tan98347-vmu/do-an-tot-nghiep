import os
import secrets
from io import BytesIO

from django.conf import settings
from django.core.files.base import ContentFile
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from accounts.permissions import can_edit_document
from accounts.runtime_guard import CompanyRuntimeGuard
from accounts.tenancy import get_user_company
from documents.pdf_preview import schedule_document_preview_regeneration
from documents.runtime_helpers import _ascii_safe_name, _extract_text_from_docx

from .manual_edit_models import DocumentManualEditSession, DocumentManualEditSessionEvent
from .manual_edit_provider import (
    get_manual_edit_provider_status,
    manual_edit_provider_name,
)
from .models import SHARE_ACTIVE, SHARE_PENDING_ADMIN, SHARE_PENDING_LEADER, DocumentVersion


def _manual_edit_session_ttl_seconds():
    return max(int(getattr(settings, 'MANUAL_EDIT_SESSION_TTL_SECONDS', 3600) or 3600), 300)


def _next_session_expiry():
    return timezone.now() + timezone.timedelta(seconds=_manual_edit_session_ttl_seconds())


def _append_session_event(session, *, level='info', step='', message='', payload=None):
    return DocumentManualEditSessionEvent.objects.create(
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


def _working_copy_filename(document, session, source_name):
    extension = '.docx'
    raw_name = os.path.basename(str(source_name or '')).strip()
    if '.' in raw_name:
        extension = f".{raw_name.rsplit('.', 1)[-1].lower()}"
    return f'{_ascii_safe_name(document.title)}_manual_{session.id}{extension}'


def expire_stale_manual_edit_sessions(*, document=None):
    now = timezone.now()
    qs = DocumentManualEditSession.objects.filter(
        status__in=DocumentManualEditSession.active_statuses(),
        expires_at__lte=now,
    )
    if document is not None:
        qs = qs.filter(document=document)
    expired_ids = list(qs.values_list('id', flat=True))
    if not expired_ids:
        return 0
    qs.update(status=DocumentManualEditSession.Status.EXPIRED, lock_token='', updated_at=now)
    for session in DocumentManualEditSession.objects.filter(pk__in=expired_ids):
        _append_session_event(
            session,
            level='warning',
            step='expire',
            message='Manual edit session expired.',
        )
        _delete_session_working_copy(session)
    return len(expired_ids)


def get_active_manual_edit_session(document, *, include_same_user=None):
    expire_stale_manual_edit_sessions(document=document)
    qs = (
        DocumentManualEditSession.objects.select_related('created_by')
        .filter(
            document=document,
            status__in=DocumentManualEditSession.active_statuses(),
            expires_at__gt=timezone.now(),
        )
        .order_by('-created_at')
    )
    if include_same_user is None:
        return qs.first()
    if include_same_user and include_same_user.is_authenticated:
        qs = qs.filter(created_by=include_same_user)
    return qs.first()


def touch_manual_edit_session(session):
    if not session.is_active:
        return session
    now = timezone.now()
    session.last_activity_at = now
    session.expires_at = _next_session_expiry()
    session.save(update_fields=['last_activity_at', 'expires_at', 'updated_at'])
    return session


def _delete_session_working_copy(session):
    _delete_field_file(session, 'working_copy_file')
    if session.working_copy_file:
        session.working_copy_file = None
        session.save(update_fields=['working_copy_file', 'updated_at'])


def _require_manual_edit_provider():
    provider_status = get_manual_edit_provider_status()
    if not provider_status.is_ready:
        raise ValidationError({'detail': provider_status.detail})


def create_manual_edit_session(*, user, document):
    _require_manual_edit_provider()
    CompanyRuntimeGuard.assert_same_company(
        user,
        document,
        detail='Van ban manual edit dang tro sang cong ty khac.',
    )
    active_session = get_active_manual_edit_session(document)
    if active_session is not None:
        if user.is_superuser or active_session.created_by_id == user.id:
            touch_manual_edit_session(active_session)
            return active_session, False
        raise ValidationError({'detail': 'Van ban dang duoc nguoi dung khac chinh sua thu cong.'})
    if not can_edit_document(user, document):
        raise PermissionDenied('You do not have permission to edit this document.')
    if not document.output_file:
        raise ValidationError({'detail': 'Document does not have a DOCX file to edit.'})

    source_name = document.output_file.name
    source_bytes = _read_file_field_bytes(
        document.output_file,
        detail='Unable to open the current DOCX file for manual editing.',
    )

    now = timezone.now()
    with transaction.atomic():
        session = DocumentManualEditSession.objects.create(
            document=document,
            company=document.company,
            created_by=user,
            status=DocumentManualEditSession.Status.ACTIVE,
            provider=manual_edit_provider_name(),
            access_token=secrets.token_urlsafe(32),
            base_version_number=document.version_number,
            working_copy_updated_at=None,
            expires_at=_next_session_expiry(),
            last_activity_at=now,
        )
        _save_field_bytes(
            session,
            'working_copy_file',
            filename=_working_copy_filename(document, session, source_name),
            file_bytes=source_bytes,
        )
        session.save(update_fields=['working_copy_file', 'updated_at'])
    _append_session_event(
        session,
        step='create',
        message='Manual edit session created.',
        payload={
            'document_version_number': document.version_number,
            'provider': session.provider,
        },
    )
    return session, True


def get_manual_edit_session_for_user(*, session_id, user):
    queryset = DocumentManualEditSession.objects.select_related('document', 'created_by', 'committed_version')
    company = get_user_company(user)
    if company is not None:
        queryset = queryset.filter(company=company)
    session = queryset.filter(pk=session_id).first()
    if session is None:
        raise ValidationError({'detail': 'Manual edit session does not exist.'})
    CompanyRuntimeGuard.assert_same_company(
        session,
        session.document,
        detail='Manual edit session dang tro sang cong ty khac.',
    )
    CompanyRuntimeGuard.assert_file_field(
        session.working_copy_file,
        target=session,
        detail='Working copy manual edit dang tro sang cong ty khac.',
    )
    if not user.is_superuser and session.created_by_id != user.id and session.document.owner_id != user.id:
        raise PermissionDenied('You do not have permission to access this manual edit session.')
    if session.is_active and session.expires_at <= timezone.now():
        expire_stale_manual_edit_sessions(document=session.document)
        session.refresh_from_db()
    return session


def get_manual_edit_session_for_wopi(*, wopi_file_id, access_token, allow_inactive=False, touch_activity=True):
    if not access_token:
        raise ValidationError({'detail': 'Missing access token.'})
    session = (
        DocumentManualEditSession.objects.select_related('document', 'created_by')
        .filter(wopi_file_id=wopi_file_id, access_token=access_token)
        .first()
    )
    if session is None:
        raise ValidationError({'detail': 'Invalid manual edit access token.'})
    CompanyRuntimeGuard.assert_same_company(
        session,
        session.document,
        detail='Manual edit WOPI session dang tro sang cong ty khac.',
    )
    CompanyRuntimeGuard.assert_file_field(
        session.working_copy_file,
        target=session,
        detail='Working copy WOPI dang tro sang cong ty khac.',
    )
    if session.expires_at <= timezone.now() or not session.is_active:
        expire_stale_manual_edit_sessions(document=session.document)
        session.refresh_from_db()
        if not allow_inactive:
            raise ValidationError({'detail': 'Manual edit session is no longer active.'})
        return session
    if touch_activity:
        touch_manual_edit_session(session)
        session.refresh_from_db()
    return session


def update_manual_edit_working_copy(*, session, file_bytes, filename=''):
    if not session.is_active:
        raise ValidationError({'detail': 'Manual edit session is not active.'})
    safe_name = _working_copy_filename(session.document, session, filename or session.working_copy_file.name)
    _save_field_bytes(
        session,
        'working_copy_file',
        filename=safe_name,
        file_bytes=file_bytes,
    )
    working_copy_updated_at = timezone.now()
    touch_manual_edit_session(session)
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
        message='Working copy updated from web editor.',
        payload={'size_bytes': len(file_bytes)},
    )
    return session


def _next_document_share_status(document, user):
    if document.visibility == 'group':
        return SHARE_PENDING_LEADER
    if document.visibility == 'public':
        return SHARE_ACTIVE if user.is_superuser else SHARE_PENDING_ADMIN
    return document.share_status


def finish_manual_edit_session(*, session, user, change_note=''):
    if not user.is_superuser and session.created_by_id != user.id:
        raise PermissionDenied('You do not have permission to finish this manual edit session.')
    if session.status not in [DocumentManualEditSession.Status.ACTIVE, DocumentManualEditSession.Status.SAVING]:
        raise ValidationError({'detail': 'Manual edit session is not active.'})
    if not session.working_copy_file:
        raise ValidationError({'detail': 'Manual edit working copy is missing.'})
    if session.expires_at <= timezone.now():
        expire_stale_manual_edit_sessions(document=session.document)
        raise ValidationError({'detail': 'Manual edit session has expired.'})

    now = timezone.now()
    previous_status = session.status
    session.status = DocumentManualEditSession.Status.SAVING
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

    current_document_bytes = _read_file_field_bytes(
        session.document.output_file,
        detail='Unable to read the current DOCX document before committing the manual edit session.',
    )
    if file_bytes == current_document_bytes:
        session.status = previous_status
        session.save(update_fields=['status', 'updated_at'])
        _append_session_event(
            session,
            level='warning',
            step='finish_blocked',
            message='Manual edit finish was blocked because no saved working-copy changes were detected.',
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
    doc = session.document
    new_version_number = doc.version_number + 1
    effective_change_note = change_note.strip() or 'Manual web editor revision'

    try:
        with transaction.atomic():
            new_version = DocumentVersion(
                document=doc,
                version_number=new_version_number,
                content=extracted_text,
                change_note=effective_change_note,
                created_by=user,
            )
            new_version.output_file.save(
                f'{_ascii_safe_name(doc.title)}_v{new_version_number}.docx',
                ContentFile(file_bytes),
                save=False,
            )
            new_version.save()

            doc.version_number = new_version_number
            doc.content = extracted_text
            doc.output_file = new_version.output_file
            next_share_status = _next_document_share_status(doc, user)
            update_fields = ['version_number', 'content', 'output_file', 'updated_at']
            if next_share_status != doc.share_status:
                doc.share_status = next_share_status
                update_fields.append('share_status')
            doc.save(update_fields=update_fields)

            session.status = DocumentManualEditSession.Status.FINISHED
            session.committed_version = new_version
            session.finished_at = timezone.now()
            session.lock_token = ''
            session.lock_token_refreshed_at = None
            session.save(
                update_fields=[
                    'status',
                    'committed_version',
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

    try:
        from documents.preview_builder import invalidate_document_preview_cache
        invalidate_document_preview_cache(doc)
    except Exception:
        pass
    schedule_document_preview_regeneration(doc)
    _append_session_event(
        session,
        step='finish',
        message='Manual edit session committed as a new document version.',
        payload={
            'document_version_number': new_version.version_number,
            'change_note': effective_change_note,
        },
    )
    _delete_session_working_copy(session)
    return new_version


def cancel_manual_edit_session(*, session, user):
    if not user.is_superuser and session.created_by_id != user.id:
        raise PermissionDenied('You do not have permission to cancel this manual edit session.')
    if session.status not in DocumentManualEditSession.active_statuses():
        return session
    session.status = DocumentManualEditSession.Status.CANCELLED
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
        message='Manual edit session cancelled.',
    )
    _delete_session_working_copy(session)
    return session
