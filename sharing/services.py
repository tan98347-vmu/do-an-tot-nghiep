"""
Tang dich vu (service layer) cho co che chia se thong nhat.

Tat ca cac noi can kiem tra "user co duoc xem/sua/xoa resource hay khong" deu phai
goi qua module nay. Tang nay tach biet logic kiem tra quyen khoi schema cu the
cua tung resource (Document/Template/Prompt), giup viec dieu chinh sau nay don gian.

Quy tac quyen:
  - Owner (created_by/owner cua resource) luon co full quyen (delete) - bo qua grants.
  - Platform admin (superuser/is_platform_admin) luon co full quyen voi moi resource
    trong cong ty cua ho.
  - Cac user khac duoc quyen bang ShareGrant active. Ladder: delete > edit > view.
  - Permission cua user = MAX(permission_level) cua moi active grant ma user huong.

Quy tac approval:
  - scope=private  : auto-active.
  - scope=group    : pending_leader, nguoi duyet = leader cua target_group.
                     Neu owner cung la leader cua group do => auto-active.
  - scope=colleagues: pending_leader, nguoi duyet = leader cua bat ki nhom nao
                     ma owner thuoc ve.
  - scope=everyone : pending_admin, nguoi duyet = platform admin (superuser).
"""

from __future__ import annotations

from typing import Iterable, Optional

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.db.models import Q, QuerySet
from django.utils import timezone

from accounts.tenancy import (
    get_user_company,
    is_company_admin,
    is_platform_admin,
)

from .constants import (
    APPROVAL_ACTIVE,
    APPROVAL_DRAFT,
    APPROVAL_PENDING_ADMIN,
    APPROVAL_PENDING_LEADER,
    APPROVAL_REJECTED,
    PERMISSION_DELETE,
    PERMISSION_EDIT,
    PERMISSION_ORDER,
    PERMISSION_VIEW,
    SCOPE_COLLEAGUES,
    SCOPE_EVERYONE,
    SCOPE_GROUP,
    SCOPE_PRIVATE,
    normalize_permission,
    normalize_scope,
    required_approver_role,
)
from .models import ShareGrant


User = get_user_model()


# ============================================================================
# Helpers noi bo
# ============================================================================

def _owner_id(resource) -> Optional[int]:
    return getattr(resource, 'owner_id', None) or getattr(resource, 'created_by_id', None)


def _is_owner(user, resource) -> bool:
    if user is None or not getattr(user, 'is_authenticated', False):
        return False
    owner_id = _owner_id(resource)
    return owner_id is not None and owner_id == getattr(user, 'id', None)


def _is_superuser_or_platform_admin(user) -> bool:
    if user is None or not getattr(user, 'is_authenticated', False):
        return False
    if getattr(user, 'is_superuser', False):
        return True
    return is_platform_admin(user)


def _is_share_admin(user) -> bool:
    if _is_superuser_or_platform_admin(user):
        return True
    return is_company_admin(user)


def _user_group_ids(user) -> list[int]:
    """Lay danh sach group_id ma user thuoc ve (active membership)."""
    if user is None or not getattr(user, 'is_authenticated', False):
        return []
    from accounts.models import UserGroupMembership

    return list(
        UserGroupMembership.objects.filter(user=user).values_list('group_id', flat=True)
    )


def _is_leader_of_owner_groups(reviewer, owner) -> bool:
    """reviewer co la leader cua it nhat 1 nhom ma owner thuoc ve khong?"""
    if reviewer is None or owner is None:
        return False
    from accounts.models import UserGroupMembership

    owner_group_ids = list(
        UserGroupMembership.objects.filter(user=owner).values_list('group_id', flat=True)
    )
    if not owner_group_ids:
        return False
    return UserGroupMembership.objects.filter(
        user=reviewer,
        role=UserGroupMembership.ROLE_LEADER,
        group_id__in=owner_group_ids,
    ).exists()


def _is_leader_of_group(reviewer, group_id: int) -> bool:
    if reviewer is None or group_id is None:
        return False
    from accounts.models import UserGroupMembership

    return UserGroupMembership.objects.filter(
        user=reviewer,
        role=UserGroupMembership.ROLE_LEADER,
        group_id=group_id,
    ).exists()


def _common_group_ids(owner, target_user) -> list[int]:
    """Danh sach group ma CA owner LAN target_user cung thuoc ve (active membership)."""
    if owner is None or target_user is None:
        return []
    from accounts.models import UserGroupMembership

    owner_gids = set(
        UserGroupMembership.objects.filter(user=owner).values_list('group_id', flat=True)
    )
    if not owner_gids:
        return []
    return list(
        UserGroupMembership.objects.filter(
            user=target_user, group_id__in=owner_gids
        ).values_list('group_id', flat=True)
    )


def _is_leader_of_common_group(reviewer, owner, target_user) -> bool:
    """reviewer co lam leader cua mot nhom CHUNG giua owner va target_user khong?"""
    common = _common_group_ids(owner, target_user)
    if not common:
        return False
    from accounts.models import UserGroupMembership

    return UserGroupMembership.objects.filter(
        user=reviewer,
        role=UserGroupMembership.ROLE_LEADER,
        group_id__in=common,
    ).exists()


def _resolve_resource_owner(resource):
    owner_id = _owner_id(resource)
    if not owner_id:
        return None
    try:
        return User.objects.get(pk=owner_id)
    except User.DoesNotExist:
        return None


def _is_member_of_group(user, group_id) -> bool:
    if user is None or group_id is None:
        return False
    from accounts.models import UserGroupMembership

    return UserGroupMembership.objects.filter(user=user, group_id=group_id).exists()


def _sync_legacy_visibility_cache(resource, *, excluded_grant_ids=()) -> None:
    from .signals import _sync_visibility_cache

    _sync_visibility_cache(resource, excluded_grant_ids=excluded_grant_ids)


def _apply_company_scope(queryset, *, user, model_cls, company):
    if company is None or _is_superuser_or_platform_admin(user):
        return queryset
    if hasattr(model_cls, 'company'):
        return queryset.filter(company=company)

    owner_lookup = None
    if hasattr(model_cls, 'owner'):
        owner_lookup = 'owner__company_membership__company'
    elif hasattr(model_cls, 'created_by'):
        owner_lookup = 'created_by__company_membership__company'

    if owner_lookup is None:
        return queryset
    return queryset.filter(**{owner_lookup: company})


# ============================================================================
# API chinh
# ============================================================================

def get_effective_grants(user, resource) -> list[ShareGrant]:
    """Tra ve danh sach active grants ma user co the huong tu resource nay."""
    if user is None or not getattr(user, 'is_authenticated', False):
        return []
    ct = ContentType.objects.get_for_model(type(resource))
    user_group_ids = _user_group_ids(user)
    qs = ShareGrant.objects.filter(
        content_type=ct,
        object_id=resource.pk,
        approval_status=APPROVAL_ACTIVE,
    ).filter(
        Q(scope=SCOPE_EVERYONE)
        | Q(scope=SCOPE_COLLEAGUES, target_user=user)
        | Q(scope=SCOPE_GROUP, target_group_id__in=user_group_ids)
    )
    return list(qs.distinct())


def user_permission_for(user, resource) -> Optional[str]:
    """Tra ve permission cao nhat (view/edit/delete) hoac None neu user khong co quyen.

    Owner va admin tu dong duoc 'delete' (full quyen).
    """
    if _is_owner(user, resource):
        return PERMISSION_DELETE
    if _is_superuser_or_platform_admin(user):
        return PERMISSION_DELETE

    grants = get_effective_grants(user, resource)
    if not grants:
        return None

    best = None
    best_rank = -1
    for g in grants:
        rank = PERMISSION_ORDER.get(g.permission_level, -1)
        if rank > best_rank:
            best = g.permission_level
            best_rank = rank
    return best


def can(user, resource, action: str) -> bool:
    """Kiem tra user co quyen thuc hien action ('view'|'edit'|'delete') tren resource."""
    required = normalize_permission(action)
    if required is None:
        return False
    current = user_permission_for(user, resource)
    if current is None:
        return False
    return PERMISSION_ORDER[current] >= PERMISSION_ORDER[required]


def get_accessible_qs(user, model_cls) -> QuerySet:
    """Queryset cac instance cua model_cls ma user co the xem.

    Bao gom:
      - Cac instance owner cua user.
      - Cac instance co ShareGrant active phu hop voi user (everyone, group user thuoc ve,
        colleagues target user).
      - Platform admin: tat ca trong company cua ho.
    """
    base_qs = model_cls.objects.all()
    if user is None or not getattr(user, 'is_authenticated', False):
        return base_qs.none()

    company = get_user_company(user)

    # Platform admin: thay tat ca
    if _is_superuser_or_platform_admin(user) and company is None:
        return base_qs

    ct = ContentType.objects.get_for_model(model_cls)
    user_group_ids = _user_group_ids(user)

    accessible_object_ids = ShareGrant.objects.filter(
        content_type=ct,
        approval_status=APPROVAL_ACTIVE,
    ).filter(
        Q(scope=SCOPE_EVERYONE)
        | Q(scope=SCOPE_COLLEAGUES, target_user=user)
        | Q(scope=SCOPE_GROUP, target_group_id__in=user_group_ids)
    ).values_list('object_id', flat=True)

    owner_field = 'owner' if hasattr(model_cls, 'owner') else 'created_by'
    queryset = base_qs.filter(
        Q(**{owner_field: user}) | Q(pk__in=accessible_object_ids)
    ).distinct()

    return _apply_company_scope(
        queryset,
        user=user,
        model_cls=model_cls,
        company=company,
    )


def get_reviewable_qs(user, model_cls) -> QuerySet:
    """Queryset cac instance dang co grant pending can user nay duyet.

    - Leader: thay grants pending_leader cho resource owner cung nhom voi user.
    - Platform admin: thay grants pending_admin.
    """
    base_qs = model_cls.objects.all()
    if user is None or not getattr(user, 'is_authenticated', False):
        return base_qs.none()

    ct = ContentType.objects.get_for_model(model_cls)
    company = get_user_company(user)
    from accounts.models import UserGroupMembership

    pending_object_ids: set[int] = set()

    if _is_share_admin(user):
        pending_object_ids.update(
            ShareGrant.objects.filter(
                content_type=ct, approval_status=APPROVAL_PENDING_ADMIN
            ).values_list('object_id', flat=True)
        )

    leader_group_ids = list(
        UserGroupMembership.objects.filter(
            user=user, role=UserGroupMembership.ROLE_LEADER
        ).values_list('group_id', flat=True)
    )
    if leader_group_ids:
        # Grants pending_leader voi scope=group va target_group thuoc nhom user lead
        pending_object_ids.update(
            ShareGrant.objects.filter(
                content_type=ct,
                approval_status=APPROVAL_PENDING_LEADER,
                scope=SCOPE_GROUP,
                target_group_id__in=leader_group_ids,
            ).values_list('object_id', flat=True)
        )
        # Grants pending_leader scope=colleagues: chi hien cho leader cua NHOM CHUNG
        # giua owner va target_user (dung nguoi se duyet theo nghiep vu).
        colleague_grants = ShareGrant.objects.filter(
            content_type=ct,
            approval_status=APPROVAL_PENDING_LEADER,
            scope=SCOPE_COLLEAGUES,
        ).select_related('target_user')
        for g in colleague_grants:
            owner = _resolve_resource_owner(g.resource)
            if owner is None and g.created_by_id:
                try:
                    owner = User.objects.get(pk=g.created_by_id)
                except User.DoesNotExist:
                    owner = None
            if _is_leader_of_common_group(user, owner, g.target_user):
                pending_object_ids.add(g.object_id)

    if not pending_object_ids:
        return base_qs.none()

    queryset = base_qs.filter(pk__in=pending_object_ids).distinct()
    return _apply_company_scope(
        queryset,
        user=user,
        model_cls=model_cls,
        company=company,
    )


# ============================================================================
# Mutation API
# ============================================================================

def _initial_approval_status(scope: str, owner, target_user=None) -> str:
    """Tra ve status mac dinh khi tao grant moi tuy theo scope (theo nghiep vu phan quyen).

    - private  : auto-active.
    - group    : cho truong nhom duyet.
    - colleagues: neu target_user CHUNG NHOM voi owner -> cho truong nhom chung duyet;
                  neu KHAC NHOM -> cho ADMIN duyet.
    - everyone : cho admin duyet.
    """
    s = normalize_scope(scope)
    if s == SCOPE_PRIVATE:
        return APPROVAL_ACTIVE  # private khong can duyet
    if s == SCOPE_GROUP:
        return APPROVAL_PENDING_LEADER
    if s == SCOPE_COLLEAGUES:
        if _common_group_ids(owner, target_user):
            return APPROVAL_PENDING_LEADER
        return APPROVAL_PENDING_ADMIN
    if s == SCOPE_EVERYONE:
        return APPROVAL_PENDING_ADMIN
    return APPROVAL_DRAFT


@transaction.atomic
def create_grant(
    *,
    resource,
    scope: str,
    permission_level: str,
    target_user=None,
    target_group=None,
    actor,
    auto_submit: bool = True,
) -> ShareGrant:
    """Tao mot grant moi tren resource.

    actor phai la owner, admin, HOAC nguoi duoc chia se voi quyen TOAN QUYEN (delete).
    Nguoi chi co 'view'/'edit' khong duoc chia se tiep.
    """
    if not (
        _is_owner(actor, resource)
        or _is_superuser_or_platform_admin(actor)
        or can(actor, resource, 'delete')
    ):
        raise PermissionError('Chi owner hoac nguoi co toan quyen moi co the tao grant.')

    scope_norm = normalize_scope(scope)
    perm_norm = normalize_permission(permission_level) or PERMISSION_VIEW

    if scope_norm is None:
        raise ValueError(f'Scope khong hop le: {scope}')

    # Validate target theo scope
    if scope_norm == SCOPE_GROUP and target_group is None:
        raise ValueError('Scope group can target_group.')
    if scope_norm == SCOPE_COLLEAGUES and target_user is None:
        raise ValueError('Scope colleagues can target_user.')
    if scope_norm in (SCOPE_PRIVATE, SCOPE_EVERYONE):
        target_user = None
        target_group = None

    # Nghiep vu: chi chia se toi NHOM MA NGUOI CHIA SE LA THANH VIEN (admin mien tru).
    if scope_norm == SCOPE_GROUP and target_group is not None:
        gid = getattr(target_group, 'pk', target_group)
        if not (_is_superuser_or_platform_admin(actor) or _is_member_of_group(actor, gid)):
            raise ValueError('Chi co the chia se toi nhom ma ban la thanh vien.')

    resource_owner = _resolve_resource_owner(resource)
    initial_status = (
        APPROVAL_DRAFT
        if not auto_submit
        else _initial_approval_status(scope_norm, resource_owner, target_user)
    )

    # Tu dong active neu owner la leader cua chinh target_group
    if scope_norm == SCOPE_GROUP and target_group is not None:
        if _is_leader_of_group(actor, getattr(target_group, 'pk', target_group)):
            initial_status = APPROVAL_ACTIVE
    if scope_norm == SCOPE_EVERYONE and _is_share_admin(actor):
        initial_status = APPROVAL_ACTIVE

    ct = ContentType.objects.get_for_model(type(resource))
    grant, _created = ShareGrant.objects.update_or_create(
        content_type=ct,
        object_id=resource.pk,
        scope=scope_norm,
        target_user=target_user,
        target_group=target_group,
        permission_level=perm_norm,
        defaults={
            'approval_status': initial_status,
            'created_by_id': _owner_id(resource),
            'submitted_at': timezone.now() if initial_status in (APPROVAL_PENDING_LEADER, APPROVAL_PENDING_ADMIN) else None,
            'submitted_by': actor if initial_status != APPROVAL_DRAFT else None,
            'approved_at': timezone.now() if initial_status == APPROVAL_ACTIVE else None,
            'approved_by': actor if initial_status == APPROVAL_ACTIVE else None,
        },
    )
    _sync_legacy_visibility_cache(resource)
    return grant


@transaction.atomic
def submit_grant(grant: ShareGrant, *, actor) -> ShareGrant:
    """Chuyen grant tu draft sang pending phu hop voi scope."""
    if grant.approval_status != APPROVAL_DRAFT:
        return grant
    target_status = _initial_approval_status(
        grant.scope, _resolve_resource_owner(grant.resource), grant.target_user
    )
    grant.approval_status = target_status
    grant.submitted_at = timezone.now()
    grant.submitted_by = actor
    grant.save(update_fields=['approval_status', 'submitted_at', 'submitted_by', 'updated_at'])
    _sync_legacy_visibility_cache(grant.resource)
    return grant


def can_approve_grant(reviewer, grant: ShareGrant) -> bool:
    """Reviewer co quyen approve/reject grant nay khong?"""
    if reviewer is None or not getattr(reviewer, 'is_authenticated', False):
        return False
    # Colleagues: nghiep vu dac biet — neu CHUNG NHOM voi owner thi truong nhom chung
    # duyet; neu KHONG chung nhom thi ADMIN duyet. (Admin/superuser luon duyet duoc.)
    if grant.scope == SCOPE_COLLEAGUES:
        owner = _resolve_resource_owner(grant.resource)
        if grant.created_by_id and owner is None:
            try:
                owner = User.objects.get(pk=grant.created_by_id)
            except User.DoesNotExist:
                owner = None
        if not _common_group_ids(owner, grant.target_user):
            return _is_share_admin(reviewer)  # khac nhom -> admin
        if _is_superuser_or_platform_admin(reviewer):
            return True
        return _is_leader_of_common_group(reviewer, owner, grant.target_user)

    role = required_approver_role(grant.scope)
    if role == 'admin':
        return _is_share_admin(reviewer)
    if role == 'leader':
        if _is_superuser_or_platform_admin(reviewer):
            return True
        if grant.scope == SCOPE_GROUP and grant.target_group_id:
            return _is_leader_of_group(reviewer, grant.target_group_id)
    return False


@transaction.atomic
def approve_grant(grant: ShareGrant, *, approver, note: str = '') -> ShareGrant:
    if not can_approve_grant(approver, grant):
        raise PermissionError('Khong co quyen duyet grant nay.')
    if grant.approval_status not in (APPROVAL_PENDING_LEADER, APPROVAL_PENDING_ADMIN, APPROVAL_DRAFT):
        return grant
    grant.approval_status = APPROVAL_ACTIVE
    grant.approved_at = timezone.now()
    grant.approved_by = approver
    grant.approver_note = note or ''
    grant.save(update_fields=['approval_status', 'approved_at', 'approved_by', 'approver_note', 'updated_at'])
    _sync_legacy_visibility_cache(grant.resource)
    return grant


@transaction.atomic
def reject_grant(grant: ShareGrant, *, approver, note: str = '') -> ShareGrant:
    if not can_approve_grant(approver, grant):
        raise PermissionError('Khong co quyen tu choi grant nay.')
    grant.approval_status = APPROVAL_REJECTED
    grant.approved_at = timezone.now()
    grant.approved_by = approver
    grant.approver_note = note or ''
    grant.save(update_fields=['approval_status', 'approved_at', 'approved_by', 'approver_note', 'updated_at'])
    _sync_legacy_visibility_cache(grant.resource)
    return grant


@transaction.atomic
def revoke_grant(grant: ShareGrant, *, actor) -> None:
    """Owner hoac admin thu hoi grant (xoa hoan toan)."""
    resource = grant.resource
    if not (_is_owner(actor, resource) or _is_superuser_or_platform_admin(actor)):
        raise PermissionError('Chi owner hoac admin moi co the thu hoi grant.')
    grant.delete()
    _sync_legacy_visibility_cache(resource)


# ============================================================================
# Convenience checks dung lai trong helpers cu
# ============================================================================

def can_view(user, resource) -> bool:
    return can(user, resource, PERMISSION_VIEW)


def can_edit(user, resource) -> bool:
    return can(user, resource, PERMISSION_EDIT)


def can_delete(user, resource) -> bool:
    return can(user, resource, PERMISSION_DELETE)


def grants_listed_for_owner(resource) -> QuerySet:
    """Tat ca grants cua mot resource (owner view)."""
    ct = ContentType.objects.get_for_model(type(resource))
    return ShareGrant.objects.filter(content_type=ct, object_id=resource.pk).order_by(
        'scope', 'permission_level', 'pk'
    )
