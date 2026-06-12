from __future__ import annotations
'''
assistant_quick_sign.py không có thuật toán ký riêng. Nó tái sử dụng chính services.py → pki.py → internal_pki.py, vì vậy chữ ký tạo bằng Quick Sign vẫn là chữ ký PKCS#7 giống luồng ký thông thường.
'''
import logging
from dataclasses import dataclass

from django.db import transaction
from django.utils import timezone

from accounts.tenancy import get_user_company, targets_share_company
from accounts.user_resolution import (
    build_recipient_candidate_snapshot,
    get_company_recipient_by_id,
)
from documents.models import DOC_STATUS_DRAFT, DOC_STATUS_FINAL
from signing.models import (
    AssistantQuickSignPlan,
    PACKET_ACTIVE,
    SIGNATURE_MODE_PDF_PKCS7,
    TASK_AVAILABLE,
    TASK_BLOCKED,
    TASK_SIGNED,
)
from signing.services import (
    SigningFlowError,
    ensure_signing_task_for_user,
    get_signature_context_for_task,
    sign_task,
)

logger = logging.getLogger('assistant_quick_sign')


@dataclass
class AssistantQuickSignError(Exception):
    code: str
    message: str
    http_status: int = 400

    def __str__(self) -> str:
        return self.message


def _recipient_snapshot(user) -> dict:
    return build_recipient_candidate_snapshot(
        user,
        match_reason='selected',
        score=100,
    )


def _active_plan_statuses() -> list[str]:
    return [
        AssistantQuickSignPlan.Status.READY,
        AssistantQuickSignPlan.Status.BLOCKED,
        AssistantQuickSignPlan.Status.IN_PROGRESS,
        AssistantQuickSignPlan.Status.PARTIAL,
        AssistantQuickSignPlan.Status.FAILED,
    ]


def _promote_draft_document_for_quick_sign(document, actor) -> None:
    if document.status != DOC_STATUS_DRAFT:
        return
    if document.owner_id != actor.id:
        return
    if document.is_archived or document.is_deleted:
        return
    document.status = DOC_STATUS_FINAL
    document.save(update_fields=['status', 'updated_at'])


def _ensure_plan_owner(plan: AssistantQuickSignPlan, actor) -> None:
    actor_company = get_user_company(actor)
    if plan.created_by_id != actor.id:
        raise AssistantQuickSignError(
            'plan_forbidden',
            'Ban khong duoc phep thao tac quick-sign plan nay.',
            http_status=403,
        )
    if actor_company is not None and plan.company_id not in (None, actor_company.id):
        raise AssistantQuickSignError(
            'plan_forbidden',
            'Quick-sign plan nay thuoc cong ty khac.',
            http_status=403,
        )


def _ensure_plan_current_document(plan: AssistantQuickSignPlan) -> None:
    if plan.document.version_number != plan.document_version_number:
        plan.status = AssistantQuickSignPlan.Status.FAILED
        plan.blocking_code = 'plan_expired'
        plan.blocking_reason = 'Van ban da thay doi sau khi tro ly tao quick-sign plan.'
        plan.last_error_code = 'plan_expired'
        plan.last_error_message = plan.blocking_reason
        plan.can_sign_now = False
        plan.save(
            update_fields=[
                'status',
                'blocking_code',
                'blocking_reason',
                'last_error_code',
                'last_error_message',
                'can_sign_now',
                'updated_at',
            ]
        )
        raise AssistantQuickSignError('plan_expired', plan.blocking_reason, http_status=409)


def _validate_recipient(document, actor, recipient) -> None:
    if recipient is None or not recipient.is_active:
        raise AssistantQuickSignError(
            'recipient_not_found',
            'Nguoi nhan khong con ton tai hoac da bi khoa.',
        )
    if recipient.id == actor.id:
        raise AssistantQuickSignError(
            'recipient_invalid',
            'Khong the gui nhanh cho chinh minh.',
        )
    if not targets_share_company(document, actor, recipient):
        raise AssistantQuickSignError(
            'recipient_cross_company',
            'Chi co the gui nhanh cho nguoi thuoc cung cong ty.',
            http_status=403,
        )


def _load_recipient_from_plan(plan: AssistantQuickSignPlan, actor):
    return get_company_recipient_by_id(get_user_company(actor), plan.recipient_user_id)


def _packet_has_other_pending_signers(task) -> bool:
    return task.packet.tasks.exclude(pk=task.pk).filter(
        status__in=[TASK_AVAILABLE, TASK_BLOCKED],
    ).exists()


def _set_blocked(plan: AssistantQuickSignPlan, code: str, reason: str) -> AssistantQuickSignPlan:
    plan.status = AssistantQuickSignPlan.Status.BLOCKED
    plan.blocking_code = code
    plan.blocking_reason = reason
    plan.can_sign_now = False
    plan.save(
        update_fields=[
            'status',
            'blocking_code',
            'blocking_reason',
            'can_sign_now',
            'updated_at',
        ]
    )
    return plan


def _map_signing_error(exc: Exception) -> tuple[str, str, int]:
    detail = str(exc)
    lowered = detail.lower()
    if 'mat khau xac nhan khong dung' in lowered:
        return 'wrong_password', 'Mat khau xac nhan khong dung.', 400
    if 'chung thu' in lowered or 'credential' in lowered:
        return 'signing_credential_missing', detail, 409
    return 'signing_failed', detail or 'Khong the ky nhanh van ban nay.', 400


def _sync_plan_runtime(
    plan: AssistantQuickSignPlan,
    actor,
    recipient,
) -> AssistantQuickSignPlan:
    _validate_recipient(plan.document, actor, recipient)
    if plan.signed_pdf_id and plan.status in {
        AssistantQuickSignPlan.Status.PARTIAL,
        AssistantQuickSignPlan.Status.COMPLETED,
    }:
        plan.document_version_number = plan.document.version_number
        plan.recipient_user = recipient
        plan.recipient_snapshot = _recipient_snapshot(recipient)
        plan.already_signed = True
        plan.requires_reauth_password = False
        plan.credential_required = plan.signature_mode == SIGNATURE_MODE_PDF_PKCS7
        plan.blocking_code = ''
        plan.blocking_reason = ''
        plan.can_sign_now = plan.status != AssistantQuickSignPlan.Status.COMPLETED
        plan.save()
        return plan
    bundle = ensure_signing_task_for_user(
        plan.document,
        actor,
        display_role='Nguoi ky nhanh',
        group_context='assistant_quick_sign',
        proposal_note='Quick-sign duoc khoi tao boi tro ly AI.',
    )
    plan.document_version_number = plan.document.version_number
    plan.recipient_user = recipient
    plan.recipient_snapshot = _recipient_snapshot(recipient)
    plan.signing_task = bundle['task']
    plan.signing_packet = bundle['packet']
    plan.signature_mode = bundle['packet'].signature_mode
    plan.already_signed = bool(bundle['already_signed'])
    plan.signed_pdf = bundle['signed_pdf']
    plan.last_error_code = ''
    plan.last_error_message = ''
    plan.requires_reauth_password = not plan.already_signed
    plan.credential_required = plan.signature_mode == SIGNATURE_MODE_PDF_PKCS7

    if plan.already_signed and plan.signed_pdf_id is not None:
        if plan.status not in {
            AssistantQuickSignPlan.Status.PARTIAL,
            AssistantQuickSignPlan.Status.COMPLETED,
        }:
            plan.status = AssistantQuickSignPlan.Status.READY
        plan.blocking_code = ''
        plan.blocking_reason = ''
        plan.can_sign_now = plan.status != AssistantQuickSignPlan.Status.COMPLETED
        plan.save()
        return plan

    task = bundle['task']
    if task.packet.status != PACKET_ACTIVE or task.status != TASK_AVAILABLE:
        reason = 'Quick-sign chua the tiep tuc vi tac vu ky hien tai chua san sang.'
        _set_blocked(plan, 'signing_task_unavailable', reason)
        plan.credential_required = task.packet.signature_mode == SIGNATURE_MODE_PDF_PKCS7
        plan.requires_reauth_password = True
        plan.save(update_fields=['credential_required', 'requires_reauth_password', 'updated_at'])
        return plan

    if _packet_has_other_pending_signers(task):
        reason = 'Van ban dang nam trong mot quy trinh ky nhieu buoc, nen khong the ky nhanh de gui ngay.'
        _set_blocked(plan, 'signing_flow_conflict', reason)
        plan.save(update_fields=['updated_at'])
        return plan

    signature_context = get_signature_context_for_task(task, actor)
    plan.credential_required = bool(signature_context.get('credential_required'))
    if signature_context.get('can_sign'):
        plan.status = AssistantQuickSignPlan.Status.READY
        plan.blocking_code = ''
        plan.blocking_reason = ''
        plan.can_sign_now = True
    else:
        reason = str(signature_context.get('reason') or '').strip()
        if plan.credential_required and not signature_context.get('credential_bound'):
            code = 'signing_credential_missing'
        elif plan.credential_required and not signature_context.get('provider_ready'):
            code = 'signing_provider_unavailable'
        else:
            code = 'signing_task_unavailable'
        plan.status = AssistantQuickSignPlan.Status.BLOCKED
        plan.blocking_code = code
        plan.blocking_reason = reason or 'Quick-sign chua san sang.'
        plan.can_sign_now = False
    plan.save()
    return plan


def _payload_status(plan: AssistantQuickSignPlan) -> str:
    if plan.status in {
        AssistantQuickSignPlan.Status.BLOCKED,
        AssistantQuickSignPlan.Status.FAILED,
    }:
        return 'operation_failed'
    if plan.status == AssistantQuickSignPlan.Status.READY:
        return 'quick_sign_plan_ready'
    if plan.status == AssistantQuickSignPlan.Status.PARTIAL:
        return 'quick_sign_plan_ready'
    if plan.status == AssistantQuickSignPlan.Status.COMPLETED:
        return 'assistant_message'
    return 'assistant_message'


def _payload_message(plan: AssistantQuickSignPlan) -> str:
    recipient_name = str(plan.recipient_snapshot.get('display_name', '') or '').strip()
    if plan.status == AssistantQuickSignPlan.Status.BLOCKED:
        return plan.blocking_reason or 'Quick-sign chua san sang.'
    if plan.status == AssistantQuickSignPlan.Status.FAILED:
        return (
            plan.last_error_message
            or plan.blocking_reason
            or 'Quick-sign khong thanh cong. Hay chuan bi lai quick-sign plan.'
        )
    if plan.status == AssistantQuickSignPlan.Status.PARTIAL:
        return (
            f'Da ky xong van ban cho {recipient_name}, nhung buoc gui di chua thanh cong. '
            'Ban co the thu lai.'
        )
    if plan.status == AssistantQuickSignPlan.Status.COMPLETED:
        return f'Da ky nhanh va gui van ban cho {recipient_name}.'
    return f'Toi da chuan bi quick-sign cho {recipient_name}. Ban co the mo van ban va bam "Ky nhanh ngay".'


def build_quick_sign_plan_payload(plan: AssistantQuickSignPlan | None) -> dict | None:
    if plan is None:
        return None
    route = f'/documents/{plan.document_id}' if plan.document_id else ''
    recipient_missing = (
        plan.recipient_user_id is None
        or plan.blocking_code == 'recipient_not_found'
        or plan.last_error_code == 'recipient_not_found'
    )
    recipient_payload = None if recipient_missing else (plan.recipient_snapshot or None)
    return {
        'kind': 'assistant_quick_sign_plan',
        'type': 'assistant_quick_sign',
        'status': _payload_status(plan),
        'route': route,
        'document_id': plan.document_id,
        'document_version_number': plan.document_version_number,
        'plan_token': str(plan.token),
        'recipient_resolution': {
            'status': 'resolved' if recipient_payload is not None else 'not_found',
            'recipient': recipient_payload,
            'candidates': [],
        },
        'recipient': recipient_payload,
        'signature_mode': plan.signature_mode,
        'requires_reauth_password': bool(plan.requires_reauth_password),
        'credential_required': bool(plan.credential_required),
        'can_sign_now': bool(plan.can_sign_now),
        'already_signed': bool(plan.already_signed),
        'blocking_code': plan.blocking_code,
        'blocking_reason': plan.blocking_reason,
        'last_error_code': plan.last_error_code,
        'last_error_message': plan.last_error_message,
        'signed_pdf_id': plan.signed_pdf_id,
        'mailbox_thread_id': plan.mailbox_thread_id,
        'forward_note': plan.forward_note,
        'message': _payload_message(plan),
        'ui_hint': {
            'cta': 'retry_forward' if plan.status == AssistantQuickSignPlan.Status.PARTIAL else 'quick_sign',
            'state': plan.status,
        },
    }


def get_latest_quick_sign_plan(document, actor) -> AssistantQuickSignPlan | None:
    return (
        AssistantQuickSignPlan.objects.select_related(
            'document',
            'created_by',
            'recipient_user',
            'signing_task',
            'signing_packet',
            'signed_pdf',
            'mailbox_thread',
        )
        .filter(
            document=document,
            created_by=actor,
            document_version_number=document.version_number,
        )
        .exclude(status=AssistantQuickSignPlan.Status.CANCELLED)
        .order_by('-updated_at', '-created_at')
        .first()
    )


def refresh_quick_sign_plan(plan: AssistantQuickSignPlan, actor) -> AssistantQuickSignPlan:
    _ensure_plan_owner(plan, actor)
    _ensure_plan_current_document(plan)
    if plan.status == AssistantQuickSignPlan.Status.COMPLETED:
        return plan
    recipient = _load_recipient_from_plan(plan, actor)
    if recipient is None:
        return _set_blocked(
            plan,
            'recipient_not_found',
            'Nguoi nhan trong quick-sign plan khong con hop le.',
        )
    return _sync_plan_runtime(plan, actor, recipient)


def prepare_quick_sign_plan(
    document,
    actor,
    recipient,
    *,
    session=None,
    forward_note='',
) -> AssistantQuickSignPlan:
    _promote_draft_document_for_quick_sign(document, actor)
    _validate_recipient(document, actor, recipient)
    active_plan = (
        AssistantQuickSignPlan.objects.select_related('document', 'created_by')
        .filter(
            document=document,
            created_by=actor,
            status__in=_active_plan_statuses(),
        )
        .order_by('-updated_at', '-created_at')
        .first()
    )
    if active_plan is None:
        plan = AssistantQuickSignPlan(
            document=document,
            created_by=actor,
        )
    else:
        plan = active_plan
    plan.session = session
    plan.forward_note = str(forward_note or '').strip()
    plan.status = AssistantQuickSignPlan.Status.READY
    plan.cancelled_at = None
    plan.completed_at = None
    plan.save()
    other_plan_ids = list(
        AssistantQuickSignPlan.objects.filter(
            document=document,
            created_by=actor,
            status__in=_active_plan_statuses(),
        )
        .exclude(pk=plan.pk)
        .values_list('pk', flat=True)
    )
    if other_plan_ids:
        AssistantQuickSignPlan.objects.filter(pk__in=other_plan_ids).update(
            status=AssistantQuickSignPlan.Status.CANCELLED,
            cancelled_at=timezone.now(),
        )
    return _sync_plan_runtime(plan, actor, recipient)


def update_quick_sign_plan_recipient(
    plan: AssistantQuickSignPlan,
    actor,
    recipient,
) -> AssistantQuickSignPlan:
    _ensure_plan_owner(plan, actor)
    _ensure_plan_current_document(plan)
    return _sync_plan_runtime(plan, actor, recipient)


def cancel_quick_sign_plan(plan: AssistantQuickSignPlan, actor) -> AssistantQuickSignPlan:
    _ensure_plan_owner(plan, actor)
    plan.status = AssistantQuickSignPlan.Status.CANCELLED
    plan.cancelled_at = timezone.now()
    plan.save(update_fields=['status', 'cancelled_at', 'updated_at'])
    return plan


def execute_quick_sign_and_forward(
    plan: AssistantQuickSignPlan,
    actor,
    *,
    reauth_password='',
) -> AssistantQuickSignPlan:
    _ensure_plan_owner(plan, actor)
    _ensure_plan_current_document(plan)
    raised_error: AssistantQuickSignError | None = None

    with transaction.atomic():
        plan = AssistantQuickSignPlan.objects.select_for_update().get(pk=plan.pk)
        _ensure_plan_owner(plan, actor)
        if plan.status == AssistantQuickSignPlan.Status.COMPLETED:
            raised_error = AssistantQuickSignError(
                'plan_already_completed',
                'Quick-sign plan nay da hoan thanh.',
                http_status=409,
            )
        elif plan.status == AssistantQuickSignPlan.Status.CANCELLED:
            raised_error = AssistantQuickSignError(
                'plan_cancelled',
                'Quick-sign plan nay da bi huy.',
                http_status=409,
            )
        elif plan.status == AssistantQuickSignPlan.Status.IN_PROGRESS:
            raised_error = AssistantQuickSignError(
                'plan_in_progress',
                'Quick-sign plan nay dang duoc xu ly.',
                http_status=409,
            )
        else:
            recipient = _load_recipient_from_plan(plan, actor)
            if recipient is None:
                plan.status = AssistantQuickSignPlan.Status.FAILED
                plan.last_error_code = 'recipient_not_found'
                plan.last_error_message = 'Nguoi nhan trong quick-sign plan khong con hop le.'
                plan.save(
                    update_fields=[
                        'status',
                        'last_error_code',
                        'last_error_message',
                        'updated_at',
                    ]
                )
                raised_error = AssistantQuickSignError(
                    'recipient_not_found',
                    'Nguoi nhan trong quick-sign plan khong con hop le.',
                )
            else:
                plan = _sync_plan_runtime(plan, actor, recipient)
                if plan.status == AssistantQuickSignPlan.Status.BLOCKED:
                    raised_error = AssistantQuickSignError(
                        plan.blocking_code or 'quick_sign_blocked',
                        plan.blocking_reason or 'Quick-sign chua san sang.',
                        http_status=409,
                    )
                else:
                    if plan.status != AssistantQuickSignPlan.Status.PARTIAL:
                        plan.status = AssistantQuickSignPlan.Status.IN_PROGRESS
                        plan.last_error_code = ''
                        plan.last_error_message = ''
                        plan.save(
                            update_fields=[
                                'status',
                                'last_error_code',
                                'last_error_message',
                                'updated_at',
                            ]
                        )
                    if plan.signed_pdf_id is None:
                        if plan.signing_task_id is None:
                            raised_error = AssistantQuickSignError(
                                'signing_task_missing',
                                'Khong tim thay tac vu ky de thuc hien quick-sign.',
                                http_status=409,
                            )
                        else:
                            try:
                                sign_result = sign_task(plan.signing_task, actor, reauth_password)
                            except SigningFlowError as exc:
                                code, message, http_status = _map_signing_error(exc)
                                plan.status = AssistantQuickSignPlan.Status.FAILED
                                plan.last_error_code = code
                                plan.last_error_message = message
                                plan.can_sign_now = False
                                plan.save(
                                    update_fields=[
                                        'status',
                                        'last_error_code',
                                        'last_error_message',
                                        'can_sign_now',
                                        'updated_at',
                                    ]
                                )
                                raised_error = AssistantQuickSignError(
                                    code,
                                    message,
                                    http_status=http_status,
                                )
                            else:
                                signed_pdf = sign_result.get('signed_pdf')
                                if signed_pdf is None:
                                    raised_error = AssistantQuickSignError(
                                        'signing_failed',
                                        'Khong tim thay PDF da ky sau khi thuc hien quick-sign.',
                                    )
                                else:
                                    plan.signed_pdf = signed_pdf
                                    plan.already_signed = True
                                    plan.requires_reauth_password = False
                                    plan.can_sign_now = True
                                    plan.save(
                                        update_fields=[
                                            'signed_pdf',
                                            'already_signed',
                                            'requires_reauth_password',
                                            'can_sign_now',
                                            'updated_at',
                                        ]
                                    )

                    if raised_error is None:
                        try:
                            from documents.mailbox_services import MailboxFlowError, forward_document

                            thread = forward_document(
                                plan.document,
                                actor,
                                [recipient],
                                note=plan.forward_note,
                                signed_pdf_override=plan.signed_pdf,
                            )
                        except MailboxFlowError as exc:
                            plan.status = AssistantQuickSignPlan.Status.PARTIAL
                            plan.last_error_code = 'forward_failed'
                            plan.last_error_message = str(exc)
                            plan.save(
                                update_fields=[
                                    'status',
                                    'last_error_code',
                                    'last_error_message',
                                    'updated_at',
                                ]
                            )
                            raised_error = AssistantQuickSignError(
                                'forward_failed',
                                'Da ky xong van ban nhung chua gui duoc den nguoi nhan.',
                                http_status=409,
                            )
                        else:
                            plan.mailbox_thread = thread
                            plan.status = AssistantQuickSignPlan.Status.COMPLETED
                            plan.completed_at = timezone.now()
                            plan.can_sign_now = False
                            plan.blocking_code = ''
                            plan.blocking_reason = ''
                            plan.save(
                                update_fields=[
                                    'mailbox_thread',
                                    'status',
                                    'completed_at',
                                    'can_sign_now',
                                    'blocking_code',
                                    'blocking_reason',
                                    'updated_at',
                                ]
                            )

    if raised_error is not None:
        raise raised_error
    logger.info(
        'assistant quick sign completed | plan_token=%s | document_id=%s | recipient_user_id=%s | thread_id=%s',
        plan.token,
        plan.document_id,
        plan.recipient_user_id,
        plan.mailbox_thread_id,
    )
    return plan
