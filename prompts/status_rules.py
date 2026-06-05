"""
Logic auto-set status cua Prompt theo visibility + role nguoi tao/sua.
- Private -> approved ngay (chi minh dung)
- Group -> pending_leader (cho truong nhom duyet)
- Public -> pending (cho admin duyet)
- Superuser luon auto-approved.
"""

from prompts.models import (
    PROMPT_STATUS_APPROVED,
    PROMPT_STATUS_PENDING,
    PROMPT_STATUS_PENDING_LEADER,
)


def _is_admin(user) -> bool:
    return bool(user and (user.is_superuser or user.is_staff))


def _is_leader_of_group(user, group) -> bool:
    if not user or not group:
        return False
    try:
        from accounts.models import UserGroupMembership
        return UserGroupMembership.objects.filter(
            user=user, group=group, role='leader',
        ).exists()
    except Exception:
        return False


def resolve_prompt_status_on_create(user, visibility: str, group=None) -> str:
    if _is_admin(user):
        return PROMPT_STATUS_APPROVED
    if visibility == 'public':
        return PROMPT_STATUS_PENDING
    if visibility == 'group':
        if _is_leader_of_group(user, group):
            return PROMPT_STATUS_APPROVED
        return PROMPT_STATUS_PENDING_LEADER
    return PROMPT_STATUS_APPROVED


def resolve_prompt_status_on_update(user, new_visibility: str, instance) -> str:
    return resolve_prompt_status_on_create(user, new_visibility, group=instance.group)


def can_approve_prompt(user, prompt) -> tuple[bool, str]:
    if not user or not user.is_authenticated:
        return False, 'unauthenticated'
    if prompt.visibility == 'public':
        if _is_admin(user):
            return True, ''
        return False, 'Chi admin moi duoc duyet prompt public.'
    if prompt.visibility == 'group':
        if _is_admin(user) or _is_leader_of_group(user, prompt.group):
            return True, ''
        return False, 'Chi truong nhom moi duoc duyet prompt cua nhom.'
    return False, 'Prompt private khong can duyet.'
