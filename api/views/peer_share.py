"""
Helpers chia se cho dung cho 3 entity (Template/Document/Prompt).
- Validate company scope cho user_ids
- Replace audience an toan
- Check quyen approve/reject (leader cua owner)
"""

from typing import Iterable

from django.contrib.auth.models import User
from django.db import transaction
from django.utils import timezone

from accounts.models import CompanyUserMembership, UserGroupMembership
from accounts.tenancy import get_user_company


PEER_NONE = 'none'
PEER_PENDING_LEADER = 'pending_leader'
PEER_ACTIVE = 'active'
PEER_REJECTED = 'rejected'


def get_owner_groups_ids(owner) -> list[int]:
    return list(
        UserGroupMembership.objects.filter(user=owner)
        .values_list('group_id', flat=True)
    )


def can_approve_peer_share(viewer, owner) -> tuple[bool, str]:
    """Viewer la leader cua it nhat 1 nhom cua owner, hoac la superuser."""
    if not viewer or not viewer.is_authenticated:
        return False, 'Chua dang nhap.'
    if viewer.is_superuser:
        return True, ''
    owner_company = get_user_company(owner)
    viewer_company = get_user_company(viewer)
    if owner_company is None or viewer_company is None:
        return False, 'Khong xac dinh duoc cong ty.'
    if owner_company.pk != viewer_company.pk:
        return False, 'Khac cong ty.'

    owner_group_ids = get_owner_groups_ids(owner)
    if not owner_group_ids:
        return False, 'Owner khong thuoc nhom nao de duyet.'
    is_leader = UserGroupMembership.objects.filter(
        user=viewer, role='leader', group_id__in=owner_group_ids,
    ).exists()
    if not is_leader:
        return False, 'Khong phai truong nhom cua owner.'
    return True, ''


def validate_user_ids_in_company(user_ids: Iterable[int], company) -> tuple[list[int], list[int]]:
    """Tach user_ids thanh (valid_in_company, invalid)."""
    ids = [int(uid) for uid in user_ids if uid is not None]
    if not ids:
        return [], []
    valid_ids = list(
        CompanyUserMembership.objects
        .filter(company=company, user_id__in=ids)
        .values_list('user_id', flat=True)
    )
    invalid = [uid for uid in ids if uid not in valid_ids]
    return valid_ids, invalid


def replace_audience(entity, audience_model, user_ids: Iterable[int], added_by, fk_name: str):
    """
    Replace toan bo audience cua entity.
    audience_model: TemplateAudienceMember / DocumentAudienceMember / PromptAudienceMember
    fk_name: 'template' | 'document' | 'prompt'
    """
    ids = list({int(uid) for uid in user_ids if uid is not None})
    if added_by and added_by.pk in ids:
        ids.remove(added_by.pk)

    with transaction.atomic():
        existing = audience_model.objects.filter(**{fk_name: entity})
        existing_ids = set(existing.values_list('user_id', flat=True))
        target_ids = set(ids)
        to_remove = existing_ids - target_ids
        to_add = target_ids - existing_ids
        if to_remove:
            audience_model.objects.filter(
                **{fk_name: entity},
                user_id__in=to_remove,
            ).delete()
        for uid in to_add:
            audience_model.objects.create(
                **{fk_name: entity},
                user_id=uid,
                added_by=added_by,
            )


def set_peer_status(entity, status: str, approver=None, note: str = ''):
    entity.peer_share_status = status
    if status == PEER_ACTIVE:
        entity.peer_share_approved_by = approver
        entity.peer_share_approved_at = timezone.now()
        entity.peer_share_approver_note = note
    elif status == PEER_REJECTED:
        entity.peer_share_approved_by = approver
        entity.peer_share_approved_at = timezone.now()
        entity.peer_share_approver_note = note
    elif status == PEER_PENDING_LEADER:
        entity.peer_share_submitted_at = timezone.now()
        entity.peer_share_approved_by = None
        entity.peer_share_approved_at = None
        entity.peer_share_approver_note = ''
    elif status == PEER_NONE:
        entity.peer_share_approved_by = None
        entity.peer_share_approved_at = None
        entity.peer_share_approver_note = ''
        entity.peer_share_submitted_at = None
    entity.save(update_fields=[
        'peer_share_status', 'peer_share_approved_by', 'peer_share_approved_at',
        'peer_share_approver_note', 'peer_share_submitted_at', 'updated_at',
    ])
