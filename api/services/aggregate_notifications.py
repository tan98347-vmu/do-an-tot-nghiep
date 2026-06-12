from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from django.contrib.auth.models import User
from django.utils import timezone

from accounts.tenancy import filter_queryset_by_current_company
from ai_tasks.models import AITaskProgress, STATUS_QUEUED, STATUS_RUNNING
from document_templates.models import TemplateReviewNotification
from documents.models import (
    MAILBOX_STATUS_COMPLETED,
    MAILBOX_STATUS_REJECTED,
    MAILBOX_STATUS_VIEW,
    DocumentMailboxEntry,
)
from sharing import services as sharing_services
from signing.models import (
    PACKET_ACTIVE,
    PROPOSAL_REJECTED,
    TASK_AVAILABLE,
    TASK_REJECTED,
    SigningProposal,
)
from signing.permissions import get_accessible_signing_tasks, get_pending_hr_proposals


MAX_SOURCE_ITEMS = 100


# class AggregateNotificationItem là lớp gom logic/dữ liệu liên quan.
# vd: gom các thuộc tính/method liên quan vào một nơi.
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

    # def to_payload để to payload.
    # vd: nhận đầu vào -> trả kết quả đã xử lý.
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


# def _display_name để display name.
# vd: nhận đầu vào -> trả kết quả đã xử lý.
def _display_name(user: User | None) -> str:
    if user is None:
        return ''
    return user.get_full_name() or user.username


# def _parse_limit để phân tích limit.
# vd: nhận đầu vào -> trả kết quả đã xử lý.
def _parse_limit(value: Any, *, default: int = 20, minimum: int = 1, maximum: int = 100) -> int:
    try:
        parsed = int(value or default)
    except (TypeError, ValueError):
        parsed = default
    return max(min(parsed, maximum), minimum)

# def _sort_payloads để sort payloads.
# vd: nhận đầu vào -> trả kết quả đã xử lý.
def _sort_payloads(items: list[AggregateNotificationItem], limit: int) -> list[dict[str, Any]]:
    # def always_include để always include.
    # vd: nhận đầu vào -> trả kết quả đã xử lý.
    def always_include(item: AggregateNotificationItem) -> bool:
        return (
            item.is_actionable
            or item.category.startswith('signing')
            or item.category.startswith('mailbox')
            or item.category == 'approval'
        )

    sorted_items = sorted(
        items,
        key=lambda item: (
            0 if item.counts_as_unread else 1,
            0 if item.is_actionable else 1,
            -(item.updated_at.timestamp() if hasattr(item.updated_at, 'timestamp') else 0),
        ),
    )
    required_count = sum(1 for item in sorted_items if always_include(item))
    optional_budget = max(limit - required_count, 0)
    visible_items: list[AggregateNotificationItem] = []
    for item in sorted_items:
        if always_include(item):
            visible_items.append(item)
        elif optional_budget > 0:
            visible_items.append(item)
            optional_budget -= 1
    return [item.to_payload() for item in visible_items]


# def _template_review_items để template review items.
# vd: nhận đầu vào -> trả kết quả đã xử lý.
def _template_review_items(user: User) -> list[AggregateNotificationItem]:
    items: list[AggregateNotificationItem] = []
    queryset = TemplateReviewNotification.objects.filter(recipient=user).select_related(
        'template',
        'actor',
    )[:MAX_SOURCE_ITEMS]
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


# def _terminal_ai_task_items để terminal ai task items.
# vd: nhận đầu vào -> trả kết quả đã xử lý.
def _terminal_ai_task_items(user: User) -> list[AggregateNotificationItem]:
    items: list[AggregateNotificationItem] = []
    queryset = (
        AITaskProgress.objects.filter(user=user)
        .exclude(status__in=[STATUS_QUEUED, STATUS_RUNNING])
        .order_by('-created_at')[:MAX_SOURCE_ITEMS]
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


# def _signing_task_items để signing task items.
# vd: nhận đầu vào -> trả kết quả đã xử lý.
def _signing_task_items(user: User) -> list[AggregateNotificationItem]:
    items: list[AggregateNotificationItem] = []
    queryset = (
        get_accessible_signing_tasks(user)
        .filter(status=TASK_AVAILABLE, packet__status=PACKET_ACTIVE)
        .select_related('packet__document')
        .order_by('step_no', 'sort_order', 'id')
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


# def _pending_signing_proposal_items để pending signing proposal items.
# vd: nhận đầu vào -> trả kết quả đã xử lý.
def _pending_signing_proposal_items(user: User) -> list[AggregateNotificationItem]:
    items: list[AggregateNotificationItem] = []
    queryset = get_pending_hr_proposals(user).order_by('-created_at')
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


# def _rejected_signing_feedback_items để rejected signing feedback items.
# vd: nhận đầu vào -> trả kết quả đã xử lý.
def _rejected_signing_feedback_items(user: User) -> list[AggregateNotificationItem]:
    items: list[AggregateNotificationItem] = []
    rejected_proposals = (
        SigningProposal.objects.filter(
            proposed_by=user,
            status=PROPOSAL_REJECTED,
        )
        .exclude(review_note='')
        .select_related('document', 'hr_reviewed_by')
        .order_by('-updated_at')
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
        .order_by('-rejected_at', '-id')
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
        .distinct()
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


# def _mailbox_items để mailbox items.
# vd: nhận đầu vào -> trả kết quả đã xử lý.
def _mailbox_items(user: User) -> list[AggregateNotificationItem]:
    items: list[AggregateNotificationItem] = []
    pending_entries = filter_queryset_by_current_company(
        DocumentMailboxEntry.objects.filter(
            forwarded_to=user,
            status=MAILBOX_STATUS_VIEW,
        ).select_related('thread__document', 'forwarded_by', 'forwarded_to'),
        user,
    ).order_by('-created_at')
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
    ).order_by('-actioned_at', '-id')
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


# def _share_approval_items để share approval items.
# vd: nhận đầu vào -> trả kết quả đã xử lý.
def _share_approval_items(user: User) -> list[AggregateNotificationItem]:
    entity_labels = {
        'templates': 'mau van ban',
        'documents': 'van ban',
        'prompts': 'prompt',
    }
    items: list[AggregateNotificationItem] = []
    for entity_type, resource, grant in sharing_services.get_reviewable_grant_rows(user):
        actor = grant.submitted_by or grant.created_by
        actor_name = _display_name(actor)
        entity_label = entity_labels.get(entity_type, 'noi dung')
        submitted_at = grant.submitted_at or grant.created_at
        items.append(
            AggregateNotificationItem(
                source_type='share_approval',
                source_id=str(grant.pk),
                category='approval',
                title=getattr(resource, 'title', '') or f'Yeu cau chia se {entity_label}',
                summary=(
                    f'{actor_name or "Nguoi dung"} gui {entity_label} '
                    f'cho duyet chia se {grant.get_scope_display().lower()}.'
                ),
                status=grant.approval_status,
                is_read=False,
                supports_read=False,
                counts_as_unread=True,
                is_actionable=True,
                created_at=submitted_at,
                updated_at=grant.updated_at,
                deeplink='/sharing/pending',
                action_label='Duyet chia se',
                actor_name=actor_name,
            )
        )
    return items


# def build_aggregate_notifications để dựng aggregate notifications.
# vd: nhận tham số đầu vào -> trả cấu trúc dữ liệu/chuỗi đã dựng.
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
    items.extend(_share_approval_items(user))
    if actionable_only:
        items = [item for item in items if item.is_actionable or item.counts_as_unread]
    return _sort_payloads(items, _parse_limit(limit))


# def get_aggregate_unread_count để lấy aggregate unread count.
# vd: nhận đầu vào -> trả kết quả đã xử lý.
def get_aggregate_unread_count(user: User, *, actionable_only: bool = False) -> int:
    count = TemplateReviewNotification.objects.filter(
        recipient=user,
        is_read=False,
    ).count()
    terminal_tasks = AITaskProgress.objects.filter(user=user).exclude(
        status__in=[STATUS_QUEUED, STATUS_RUNNING],
    )
    return count + sum(1 for task in terminal_tasks if not task.is_dismissed)


# def mark_aggregate_notification_read để đánh dấu aggregate notification read.
# vd: nhận đầu vào -> trả kết quả đã xử lý.
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


# def mark_all_aggregate_notifications_read để đánh dấu all aggregate notifications read.
# vd: nhận đầu vào -> trả kết quả đã xử lý.
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
