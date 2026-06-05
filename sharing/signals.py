"""
Signals dong bo cache `visibility` tren resource goc khi ShareGrant doi.

Trong giai doan migration, cac model Document/Template/Prompt van giu truong `visibility`
cu de query nhanh va tuong thich nguoc. Khi ShareGrant tao moi / cap nhat / xoa,
ta cap nhat `visibility` thanh scope cao nhat dang duoc yeu cau hoac da kich hoat
(private < group < colleagues < everyone).
"""

from __future__ import annotations

from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .constants import (
    APPROVAL_ACTIVE,
    APPROVAL_PENDING_ADMIN,
    APPROVAL_PENDING_LEADER,
    SCOPE_COLLEAGUES,
    SCOPE_EVERYONE,
    SCOPE_GROUP,
    SCOPE_PRIVATE,
)
from .models import ShareGrant


_SCOPE_RANK = {
    SCOPE_PRIVATE: 0,
    SCOPE_GROUP: 1,
    SCOPE_COLLEAGUES: 2,
    SCOPE_EVERYONE: 3,
}

# Mapping scope moi -> visibility cu de update truong legacy
# Note: 'colleagues' khong co trong legacy => fallback 'group' de query cu khong vo.
_LEGACY_VISIBILITY_MAP = {
    SCOPE_PRIVATE: 'private',
    SCOPE_GROUP: 'group',
    SCOPE_COLLEAGUES: 'group',
    SCOPE_EVERYONE: 'public',
}

_VISIBILITY_CACHE_APPROVALS = (
    APPROVAL_ACTIVE,
    APPROVAL_PENDING_LEADER,
    APPROVAL_PENDING_ADMIN,
)


def _sync_visibility_cache(resource, *, excluded_grant_ids=()) -> None:
    if resource is None or not hasattr(resource, 'visibility'):
        return
    from django.contrib.contenttypes.models import ContentType

    ct = ContentType.objects.get_for_model(type(resource))
    visible_grants = ShareGrant.objects.filter(
        content_type=ct,
        object_id=resource.pk,
        approval_status__in=_VISIBILITY_CACHE_APPROVALS,
    )
    if excluded_grant_ids:
        visible_grants = visible_grants.exclude(pk__in=tuple(excluded_grant_ids))
    visible_scopes = (
        visible_grants
        .values_list('scope', flat=True)
        .distinct()
    )
    top_scope = SCOPE_PRIVATE
    top_rank = -1
    for sc in visible_scopes:
        rank = _SCOPE_RANK.get(sc, -1)
        if rank > top_rank:
            top_rank = rank
            top_scope = sc

    legacy_value = _LEGACY_VISIBILITY_MAP.get(top_scope, 'private')
    try:
        type(resource).objects.filter(pk=resource.pk).update(visibility=legacy_value)
        resource.visibility = legacy_value
    except Exception:
        pass


@receiver(post_save, sender=ShareGrant)
def _on_grant_saved(sender, instance: ShareGrant, **kwargs):
    _sync_visibility_cache(instance.resource)


@receiver(post_delete, sender=ShareGrant)
def _on_grant_deleted(sender, instance: ShareGrant, **kwargs):
    _sync_visibility_cache(instance.resource)


# ---------------------------------------------------------------------------
# Thong nhat ve ShareGrant: he thong peer-audience cu (PromptAudienceMember,
# TemplateAudienceMember, DocumentAudienceMember) duoc MIRROR sang ShareGrant
# (scope=colleagues) de phan giai quyen (chi doc ShareGrant) luon nhat quan.
# ---------------------------------------------------------------------------
from prompts.models import PromptAudienceMember  # noqa: E402
from document_templates.models import TemplateAudienceMember  # noqa: E402
from documents.models import DocumentAudienceMember  # noqa: E402

_AUDIENCE_FK = {
    PromptAudienceMember: 'prompt',
    TemplateAudienceMember: 'template',
    DocumentAudienceMember: 'document',
}


def _audience_resource(member):
    fk = _AUDIENCE_FK.get(type(member))
    return getattr(member, fk, None) if fk else None


def _colleagues_grant_qs(resource, user):
    from django.contrib.contenttypes.models import ContentType

    ct = ContentType.objects.get_for_model(type(resource))
    return ShareGrant.objects.filter(
        content_type=ct,
        object_id=resource.pk,
        scope=SCOPE_COLLEAGUES,
        target_user=user,
    )


def _mirror_audience_member(member) -> None:
    resource = _audience_resource(member)
    user = getattr(member, 'user', None)
    if resource is None or user is None:
        return
    from django.contrib.contenttypes.models import ContentType

    owner_id = getattr(resource, 'owner_id', None) or getattr(resource, 'created_by_id', None)
    # Xoa moi mirror cu cua (resource,user) (vi permission_level nam trong unique key)
    _colleagues_grant_qs(resource, user).delete()
    if owner_id == getattr(user, 'id', None):
        return  # chu so huu khong can grant
    ct = ContentType.objects.get_for_model(type(resource))
    ShareGrant.objects.create(
        content_type=ct,
        object_id=resource.pk,
        scope=SCOPE_COLLEAGUES,
        permission_level=member.permission_level,
        target_user=user,
        approval_status=APPROVAL_ACTIVE,
        created_by_id=owner_id or getattr(member, 'added_by_id', None),
    )


def _remove_audience_mirror(member) -> None:
    resource = _audience_resource(member)
    user = getattr(member, 'user', None)
    if resource is None or user is None:
        return
    _colleagues_grant_qs(resource, user).delete()


@receiver(post_save, sender=PromptAudienceMember)
@receiver(post_save, sender=TemplateAudienceMember)
@receiver(post_save, sender=DocumentAudienceMember)
def _on_audience_member_saved(sender, instance, **kwargs):
    _mirror_audience_member(instance)


@receiver(post_delete, sender=PromptAudienceMember)
@receiver(post_delete, sender=TemplateAudienceMember)
@receiver(post_delete, sender=DocumentAudienceMember)
def _on_audience_member_deleted(sender, instance, **kwargs):
    _remove_audience_mirror(instance)
