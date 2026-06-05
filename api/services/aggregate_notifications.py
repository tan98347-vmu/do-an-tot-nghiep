from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any

from django.contrib.auth.models import User
from django.db.models import Q
from django.utils import timezone

from accounts.models import UserGroupMembership
from accounts.tenancy import filter_queryset_by_current_company
from ai_tasks.models import AITaskProgress, STATUS_QUEUED, STATUS_RUNNING
from document_templates.models import (
    STATUS_PENDING,
    STATUS_PENDING_LEADER,
    DocumentTemplate,
    TemplateReviewNotification,
)
from documents.models import (
    MAILBOX_STATUS_COMPLETED,
    MAILBOX_STATUS_REJECTED,
    MAILBOX_STATUS_VIEW,
    SHARE_PENDING_ADMIN,
    SHARE_PENDING_LEADER,
    Document,
    DocumentMailboxEntry,
)
from prompts.models import (
    PROMPT_STATUS_PENDING,
    PROMPT_STATUS_PENDING_LEADER,
    PROMPT_STATUS_REJECTED,
    Prompt,
)
from signing.models import (
    PACKET_ACTIVE,
    PROPOSAL_PENDING_HR_REVIEW,
    PROPOSAL_REJECTED,
    TASK_AVAILABLE,
    TASK_REJECTED,
    SigningProposal,
)
from signing.permissions import get_accessible_signing_tasks, get_pending_hr_proposals


@dataclass(frozen=True)
class AggregateNotificationItem:
    source_type: str
    source_id: str
    category: str
    title: str
    summary: str
    status: str
    is_read: bool
    supports_read: bool
    counts_as_unread: bool
    is_actionable: bool
    created_at: Any
    updated_at: Any
    deeplink: str
    action_label: str
    reason: str = ''
    actor_name: str = ''

    def to_payload(self) -> dict[str, Any]:
        return {
            'source_type': self.source_type,
            'source_id': self.source_id,
            'category': self.category,
            'title': self.title,
            'summary': self.summary,
            'status': self.status,
            'is_read': self.is_read,
            'supports_read': self.supports_read,
            'counts_as_unread': self.counts_as_unread,
            'is_actionable': self.is_actionable,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'deeplink': self.deeplink,
            'action_label': self.action_label,
            'reason': self.reason,
            'actor_name': self.actor_name,
        }


def _display_name(user: User | None) -> str:
    if user is None:
        return ''
    return user.get_full_name() or user.username


def _parse_flag(value: Any) -> bool:
    return str(value or '').strip().lower() in {'1', 'true', 'yes', 'on'}


def _parse_limit(value: Any, *, default: int = 20, minimum: int = 1, maximum: int = 100) -> int:
    try:
        parsed = int(value or default)
    except (TypeError, ValueError):
        parsed = default
    return max(min(parsed, maximum), minimum)


def _parse_date(value: str, field_name: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f'{field_name} phai co dinh dang YYYY-MM-DD.') from exc


def _sort_payloads(items: list[AggregateNotificationItem], limit: int) -> list[dict[str, Any]]:
    sorted_items = sorted(
        items,
        key=lambda item: (
            0 if item.counts_as_unread else 1,
            0 if item.is_actionable else 1,
            -(item.updated_at.timestamp() if hasattr(item.updated_at, 'timestamp') else 0),
        ),
    )
    return [item.to_payload() for item in sorted_items[:limit]]


def _template_review_items(user: User) -> list[AggregateNotificationItem]:
    items: list[AggregateNotificationItem] = []
    queryset = TemplateReviewNotification.objects.filter(recipient=user).select_related(
        'template',
        'actor',
    )[:20]
    for notification in queryset:
        actor_name = _display_name(notification.actor)
        verb = 'tu choi' if notification.action == 'reject' else 'da duyet'
        summary = f'{actor_name or "He thong"} {verb} mau van ban cua ban.'
        items.append(
            AggregateNotificationItem(
                source_type='template_review',
                source_id=str(notification.pk),
                category='template_review',
                title=notification.template.title,
                summary=summary,
                status=notification.action,
                is_read=notification.is_read,
                supports_read=True,
                counts_as_unread=not notification.is_read,
                is_actionable=False,
                created_at=notification.created_at,
                updated_at=notification.created_at,
                deeplink=f'/templates/{notification.template_id}',
                action_label='Mo mau',
                reason=notification.comment or '',
                actor_name=actor_name,
            )
        )
    return items


def _terminal_ai_task_items(user: User) -> list[AggregateNotificationItem]:
    items: list[AggregateNotificationItem] = []
    queryset = (
        AITaskProgress.objects.filter(user=user)
        .exclude(status__in=[STATUS_QUEUED, STATUS_RUNNING])
        .order_by('-created_at')[:20]
    )
    for task in queryset:
        dismissed = task.is_dismissed
        title = task.title_summary or f'AI task {task.task_type}'
        if task.status == 'failed':
            summary = task.error_message or 'Tac vu AI da that bai.'
        else:
            summary = 'Tac vu AI da hoan tat.'
        items.append(
            AggregateNotificationItem(
                source_type='ai_task_terminal',
                source_id=str(task.task_id),
                category='ai_task',
                title=title,
                summary=summary,
                status=task.status,
                is_read=dismissed,
                supports_read=True,
                counts_as_unread=not dismissed,
                is_actionable=False,
                created_at=task.created_at,
                updated_at=task.updated_at,
                deeplink=task.deeplink or '/dashboard',
                action_label='Mo ket qua',
                reason=task.error_message or '',
            )
        )
    return items


def _signing_task_items(user: User) -> list[AggregateNotificationItem]:
    items: list[AggregateNotificationItem] = []
    queryset = (
        get_accessible_signing_tasks(user)
        .filter(status=TASK_AVAILABLE, packet__status=PACKET_ACTIVE)
        .select_related('packet__document')
        .order_by('step_no', 'sort_order', 'id')[:20]
    )
    for task in queryset:
        summary = f'Ban co yeu cau ky voi vai tro "{task.display_role}".'
        items.append(
            AggregateNotificationItem(
                source_type='signing_task',
                source_id=str(task.pk),
                category='signing',
                title=task.packet.document.title,
                summary=summary,
                status=task.status,
                is_read=False,
                supports_read=False,
                counts_as_unread=True,
                is_actionable=True,
                created_at=task.created_at,
                updated_at=task.notified_at or task.created_at,
                deeplink=f'/signing/tasks/{task.pk}',
                action_label='Ky ngay',
            )
        )
    return items


def _pending_signing_proposal_items(user: User) -> list[AggregateNotificationItem]:
    items: list[AggregateNotificationItem] = []
    queryset = get_pending_hr_proposals(user).order_by('-created_at')[:20]
    for proposal in queryset:
        items.append(
            AggregateNotificationItem(
                source_type='signing_proposal_pending',
                source_id=str(proposal.pk),
                category='signing_review',
                title=proposal.document.title,
                summary=f'De xuat ky cua {_display_name(proposal.proposed_by)} dang cho duyet.',
                status=proposal.status,
                is_read=False,
                supports_read=False,
                counts_as_unread=True,
                is_actionable=True,
                created_at=proposal.created_at,
                updated_at=proposal.updated_at,
                deeplink=f'/signing/proposals/review?proposal={proposal.pk}',
                action_label='Duyet de xuat',
                actor_name=_display_name(proposal.proposed_by),
            )
        )
    return items


def _rejected_signing_feedback_items(user: User) -> list[AggregateNotificationItem]:
    items: list[AggregateNotificationItem] = []
    rejected_proposals = (
        SigningProposal.objects.filter(
            proposed_by=user,
            status=PROPOSAL_REJECTED,
        )
        .exclude(review_note='')
        .select_related('document', 'hr_reviewed_by')
        .order_by('-updated_at')[:10]
    )
    for proposal in rejected_proposals:
        actor_name = _display_name(proposal.hr_reviewed_by)
        items.append(
            AggregateNotificationItem(
                source_type='signing_proposal_rejected',
                source_id=str(proposal.pk),
                category='signing_feedback',
                title=proposal.document.title,
                summary=f'De xuat ky bi tu choi boi {actor_name or "bo phan duyet"}.',
                status=proposal.status,
                is_read=False,
                supports_read=False,
                counts_as_unread=False,
                is_actionable=False,
                created_at=proposal.created_at,
                updated_at=proposal.hr_reviewed_at or proposal.updated_at,
                deeplink=f'/documents/{proposal.document_id}',
                action_label='Mo van ban',
                reason=proposal.review_note,
                actor_name=actor_name,
            )
        )

    rejected_tasks = (
        get_accessible_signing_tasks(user)
        .filter(status=TASK_REJECTED)
        .exclude(rejection_reason='')
        .select_related('packet__document', 'signer_user')
        .order_by('-rejected_at', '-id')[:10]
    )
    for task in rejected_tasks:
        actor_name = _display_name(task.signer_user)
        items.append(
            AggregateNotificationItem(
                source_type='signing_task_rejected',
                source_id=str(task.pk),
                category='signing_feedback',
                title=task.packet.document.title,
                summary=f'Yeu cau ky bi tu choi boi {actor_name or "nguoi ky"}.',
                status=task.status,
                is_read=False,
                supports_read=False,
                counts_as_unread=False,
                is_actionable=False,
                created_at=task.created_at,
                updated_at=task.rejected_at or task.created_at,
                deeplink=f'/signing/tasks/{task.pk}',
                action_label='Xem yeu cau ky',
                reason=task.rejection_reason,
                actor_name=actor_name,
            )
        )

    proposer_task_feedback = (
        SigningProposal.objects.filter(proposed_by=user)
        .exclude(packet__tasks__rejection_reason='')
        .filter(packet__tasks__status=TASK_REJECTED)
        .select_related('document')
        .prefetch_related('packet__tasks__signer_user')
        .order_by('-updated_at')
        .distinct()[:10]
    )
    existing_ids = {
        (item.source_type, item.source_id)
        for item in items
    }
    for proposal in proposer_task_feedback:
        for task in proposal.packet.tasks.filter(status=TASK_REJECTED).exclude(rejection_reason=''):
            key = ('signing_task_feedback_to_sender', str(task.pk))
            if key in existing_ids:
                continue
            actor_name = _display_name(task.signer_user)
            items.append(
                AggregateNotificationItem(
                    source_type='signing_task_feedback_to_sender',
                    source_id=str(task.pk),
                    category='signing_feedback',
                    title=proposal.document.title,
                    summary=f'Nguoi ky {actor_name or "khong ro"} da tu choi yeu cau ky.',
                    status=task.status,
                    is_read=False,
                    supports_read=False,
                    counts_as_unread=False,
                    is_actionable=False,
                    created_at=task.created_at,
                    updated_at=task.rejected_at or task.created_at,
                    deeplink=f'/documents/{proposal.document_id}',
                    action_label='Mo van ban',
                    reason=task.rejection_reason,
                    actor_name=actor_name,
                )
            )
            existing_ids.add(key)
    return items


def _mailbox_items(user: User) -> list[AggregateNotificationItem]:
    items: list[AggregateNotificationItem] = []
    pending_entries = filter_queryset_by_current_company(
        DocumentMailboxEntry.objects.filter(
            forwarded_to=user,
            status=MAILBOX_STATUS_VIEW,
        ).select_related('thread__document', 'forwarded_by', 'forwarded_to'),
        user,
    ).order_by('-created_at')[:20]
    for entry in pending_entries:
        items.append(
            AggregateNotificationItem(
                source_type='mailbox_pending',
                source_id=str(entry.pk),
                category='mailbox',
                title=entry.thread.document.title,
                summary=f'Ban vua duoc forward van ban tu {_display_name(entry.forwarded_by)}.',
                status=entry.status,
                is_read=False,
                supports_read=False,
                counts_as_unread=True,
                is_actionable=True,
                created_at=entry.created_at,
                updated_at=entry.updated_at,
                deeplink=f'/mailbox/{entry.thread_id}',
                action_label='Mo hom thu',
                reason=entry.note or '',
                actor_name=_display_name(entry.forwarded_by),
            )
        )

    sender_feedback = filter_queryset_by_current_company(
        DocumentMailboxEntry.objects.filter(
            forwarded_by=user,
            status__in=[MAILBOX_STATUS_REJECTED, MAILBOX_STATUS_COMPLETED],
            actioned_at__isnull=False,
        ).select_related('thread__document', 'actioned_by'),
        user,
    ).order_by('-actioned_at', '-id')[:20]
    for entry in sender_feedback:
        actor_name = _display_name(entry.actioned_by)
        status_label = 'tu choi' if entry.status == MAILBOX_STATUS_REJECTED else 'hoan thanh'
        items.append(
            AggregateNotificationItem(
                source_type='mailbox_feedback',
                source_id=str(entry.pk),
                category='mailbox_feedback',
                title=entry.thread.document.title,
                summary=f'Nguoi nhan da {status_label} xu ly van ban.',
                status=entry.status,
                is_read=False,
                supports_read=False,
                counts_as_unread=False,
                is_actionable=False,
                created_at=entry.created_at,
                updated_at=entry.actioned_at or entry.updated_at,
                deeplink=f'/mailbox/{entry.thread_id}',
                action_label='Mo hom thu',
                reason=entry.action_reason,
                actor_name=actor_name,
            )
        )
    return items


def _leader_group_ids(user: User) -> list[int]:
    return list(
        UserGroupMembership.objects.filter(user=user, role='leader').values_list('group_id', flat=True)
    )


def _approval_queue_item(user: User) -> AggregateNotificationItem | None:
    leader_gids = _leader_group_ids(user)

    template_qs = DocumentTemplate.objects.none()
    if user.is_superuser:
        template_qs = DocumentTemplate.objects.filter(
            status__in=[STATUS_PENDING, STATUS_PENDING_LEADER],
        )
    if leader_gids:
        leader_template_qs = DocumentTemplate.objects.filter(
            status=STATUS_PENDING_LEADER,
            group_id__in=leader_gids,
        )
        template_qs = template_qs | leader_template_qs if user.is_superuser else leader_template_qs

    document_qs = Document.objects.none()
    if user.is_superuser:
        document_qs = Document.objects.filter(share_status=SHARE_PENDING_ADMIN)
    if leader_gids:
        leader_document_qs = Document.objects.filter(
            share_status=SHARE_PENDING_LEADER,
            group_id__in=leader_gids,
        )
        document_qs = document_qs | leader_document_qs if user.is_superuser else leader_document_qs

    prompt_qs = Prompt.objects.none()
    if user.is_superuser:
        prompt_qs = Prompt.objects.filter(
            status__in=[PROMPT_STATUS_PENDING, PROMPT_STATUS_PENDING_LEADER],
        )
    if leader_gids:
        leader_prompt_qs = Prompt.objects.filter(
            status=PROMPT_STATUS_PENDING_LEADER,
            group_id__in=leader_gids,
        )
        prompt_qs = prompt_qs | leader_prompt_qs if user.is_superuser else leader_prompt_qs

    owner_ids_under_leader = list(
        UserGroupMembership.objects.filter(group_id__in=leader_gids)
        .values_list('user_id', flat=True)
        .distinct()
    )
    template_peer_qs = DocumentTemplate.objects.none()
    document_peer_qs = Document.objects.none()
    prompt_peer_qs = Prompt.objects.none()
    if user.is_superuser:
        template_peer_qs = DocumentTemplate.objects.filter(
            peer_share_status=DocumentTemplate.PEER_SHARE_PENDING_LEADER,
        )
        document_peer_qs = Document.objects.filter(
            peer_share_status=Document.PEER_SHARE_PENDING_LEADER,
        )
        prompt_peer_qs = Prompt.objects.filter(
            peer_share_status=Prompt.PEER_SHARE_PENDING_LEADER,
        )
    if owner_ids_under_leader:
        leader_template_peer_qs = DocumentTemplate.objects.filter(
            peer_share_status=DocumentTemplate.PEER_SHARE_PENDING_LEADER,
            owner_id__in=owner_ids_under_leader,
        )
        leader_document_peer_qs = Document.objects.filter(
            peer_share_status=Document.PEER_SHARE_PENDING_LEADER,
            owner_id__in=owner_ids_under_leader,
        )
        leader_prompt_peer_qs = Prompt.objects.filter(
            peer_share_status=Prompt.PEER_SHARE_PENDING_LEADER,
            owner_id__in=owner_ids_under_leader,
        )
        if user.is_superuser:
            template_peer_qs = template_peer_qs | leader_template_peer_qs
            document_peer_qs = document_peer_qs | leader_document_peer_qs
            prompt_peer_qs = prompt_peer_qs | leader_prompt_peer_qs
        else:
            template_peer_qs = leader_template_peer_qs
            document_peer_qs = leader_document_peer_qs
            prompt_peer_qs = leader_prompt_peer_qs

    template_count = template_qs.distinct().count()
    document_count = document_qs.distinct().count()
    prompt_count = prompt_qs.distinct().count()
    peer_count = (
        template_peer_qs.distinct().count()
        + document_peer_qs.distinct().count()
        + prompt_peer_qs.distinct().count()
    )
    total = template_count + document_count + prompt_count + peer_count
    if total == 0:
        return None

    latest_candidates = [
        template_qs.order_by('-updated_at').values_list('updated_at', flat=True).first(),
        document_qs.order_by('-updated_at').values_list('updated_at', flat=True).first(),
        prompt_qs.order_by('-updated_at').values_list('updated_at', flat=True).first(),
        template_peer_qs.order_by('-updated_at').values_list('updated_at', flat=True).first(),
        document_peer_qs.order_by('-updated_at').values_list('updated_at', flat=True).first(),
        prompt_peer_qs.order_by('-updated_at').values_list('updated_at', flat=True).first(),
    ]
    updated_at = max((item for item in latest_candidates if item is not None), default=timezone.now())
    summary_bits = [
        f'{template_count} mau',
        f'{document_count} van ban',
        f'{prompt_count} prompt',
    ]
    if peer_count:
        summary_bits.append(f'{peer_count} chia se dong nghiep')
    return AggregateNotificationItem(
        source_type='approval_queue',
        source_id='pending-approvals',
        category='approval',
        title=f'Co {total} yeu cau phe duyet',
        summary=', '.join(summary_bits) + ' dang cho xu ly.',
        status='pending',
        is_read=False,
        supports_read=False,
        counts_as_unread=True,
        is_actionable=True,
        created_at=updated_at,
        updated_at=updated_at,
        deeplink='/pending-approvals',
        action_label='Mo yeu cau duyet',
    )


def build_aggregate_notifications(
    user: User,
    *,
    limit: int = 20,
    actionable_only: bool = False,
) -> list[dict[str, Any]]:
    items: list[AggregateNotificationItem] = []
    items.extend(_template_review_items(user))
    items.extend(_terminal_ai_task_items(user))
    items.extend(_signing_task_items(user))
    items.extend(_pending_signing_proposal_items(user))
    items.extend(_rejected_signing_feedback_items(user))
    items.extend(_mailbox_items(user))
    approval_item = _approval_queue_item(user)
    if approval_item is not None:
        items.append(approval_item)
    if actionable_only:
        items = [item for item in items if item.is_actionable or item.counts_as_unread]
    return _sort_payloads(items, _parse_limit(limit))


def get_aggregate_unread_count(user: User, *, actionable_only: bool = False) -> int:
    # Badge tren chuong chi dem cac thong bao CHUA DOC va CO THE danh dau da doc
    # (template_review, ai_task_terminal). Cac muc "viec can lam" dang cho nhu
    # phe duyet/ky/mailbox co counts_as_unread=True nhung supports_read=False:
    # chung khong the danh dau da doc nen khong tinh vao badge, neu khong nut
    # "Da xem tat ca" se khong bao gio dua badge ve 0. Cac muc do van hien trong
    # danh sach thong bao va co chi bao rieng (pending approvals / signing).
    items = build_aggregate_notifications(user, limit=100, actionable_only=actionable_only)
    return sum(
        1
        for item in items
        if item.get('counts_as_unread') and item.get('supports_read')
    )


def mark_aggregate_notification_read(user: User, source_type: str, source_id: str) -> bool:
    if source_type == 'template_review':
        notification = TemplateReviewNotification.objects.filter(
            recipient=user,
            pk=source_id,
        ).first()
        if notification is None:
            return False
        if not notification.is_read:
            notification.is_read = True
            notification.read_at = timezone.now()
            notification.save(update_fields=['is_read', 'read_at'])
        return True

    if source_type == 'ai_task_terminal':
        task = AITaskProgress.objects.filter(user=user, task_id=source_id).first()
        if task is None:
            return False
        result = task.result if isinstance(task.result, dict) else {}
        if not result.get('dismissed'):
            task.result = {**result, 'dismissed': True}
            task.save(update_fields=['result', 'updated_at'])
        return True

    return False


def mark_all_aggregate_notifications_read(user: User) -> int:
    """Danh dau da doc tat ca thong bao ho tro mark-read cua nguoi dung.

    Bao gom: thong bao duyet mau (TemplateReviewNotification) va cac tac vu AI
    da ket thuc (AITaskProgress). Tra ve so muc da cap nhat.
    """
    updated = TemplateReviewNotification.objects.filter(
        recipient=user,
        is_read=False,
    ).update(is_read=True, read_at=timezone.now())

    terminal_tasks = AITaskProgress.objects.filter(user=user).exclude(
        status__in=[STATUS_QUEUED, STATUS_RUNNING],
    )
    for task in terminal_tasks:
        result = task.result if isinstance(task.result, dict) else {}
        if not result.get('dismissed'):
            task.result = {**result, 'dismissed': True}
            task.save(update_fields=['result', 'updated_at'])
            updated += 1
    return updated
