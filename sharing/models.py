"""
Model ShareGrant - bang chia se thong nhat cho DocumentTemplate / Document / Prompt.

Moi grant la mot dong cap quyen rieng le:
    (resource, scope, target, permission_level, approval_status)

Owner co the tao NHIEU grant tren cung resource. Vi du, mot template co the dong thoi:
  - grant(scope=group, target_group=GroupA, permission=view, status=active)
  - grant(scope=colleagues, target_user=Bob, permission=edit, status=active)
  - grant(scope=everyone, permission=view, status=pending_admin)

Owner (created_by tren resource goc) va platform admin (superuser) tu dong co full quyen ma
khong can grant - check tai sharing.services.can().
"""

from __future__ import annotations

from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models

from .constants import (
    APPROVAL_ACTIVE,
    APPROVAL_CHOICES,
    APPROVAL_DRAFT,
    APPROVAL_PENDING_ADMIN,
    APPROVAL_PENDING_LEADER,
    APPROVAL_REJECTED,
    PERMISSION_CHOICES,
    PERMISSION_VIEW,
    SCOPE_CHOICES,
    SCOPE_COLLEAGUES,
    SCOPE_EVERYONE,
    SCOPE_GROUP,
    SCOPE_PRIVATE,
)


class ShareGrantQuerySet(models.QuerySet):
    def active(self):
        return self.filter(approval_status=APPROVAL_ACTIVE)

    def pending(self):
        return self.filter(approval_status__in=[APPROVAL_PENDING_LEADER, APPROVAL_PENDING_ADMIN])

    def for_resource(self, resource):
        ct = ContentType.objects.get_for_model(type(resource))
        return self.filter(content_type=ct, object_id=resource.pk)

    def for_user(self, user):
        """Grants ma user nay co the duoc huong (theo target_user hoac scope=everyone)."""
        if user is None or not user.is_authenticated:
            return self.none()
        return self.filter(
            models.Q(target_user=user)
            | models.Q(scope=SCOPE_EVERYONE)
            | models.Q(scope=SCOPE_GROUP, target_group__memberships__user=user)
        ).distinct()


class ShareGrant(models.Model):
    """
    Mot ban ghi grant chia se 1 resource cho 1 target voi 1 permission level.
    """

    # Resource duoc share (Template / Document / Prompt qua GenericFK)
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        related_name='share_grants',
    )
    object_id = models.PositiveBigIntegerField()
    resource = GenericForeignKey('content_type', 'object_id')

    # Pham vi chia se
    scope = models.CharField(
        max_length=16,
        choices=SCOPE_CHOICES,
        db_index=True,
        verbose_name='Pham vi',
    )

    # Quyen han duoc cap (ladder: delete > edit > view)
    permission_level = models.CharField(
        max_length=8,
        choices=PERMISSION_CHOICES,
        default=PERMISSION_VIEW,
        verbose_name='Quyen han',
    )

    # Target: tuy scope ma 1 trong 2 fk nay duoc set, hoac ca 2 null (private/everyone)
    target_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name='received_share_grants',
        verbose_name='Nguoi duoc chia se',
    )
    target_group = models.ForeignKey(
        'accounts.UserGroup',
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name='received_share_grants',
        verbose_name='Nhom duoc chia se',
    )

    # Trang thai duyet
    approval_status = models.CharField(
        max_length=20,
        choices=APPROVAL_CHOICES,
        default=APPROVAL_DRAFT,
        db_index=True,
        verbose_name='Trang thai duyet',
    )

    # Audit cua viec submit/approve
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_share_grants',
        verbose_name='Nguoi tao grant (owner cua resource)',
    )
    submitted_at = models.DateTimeField(null=True, blank=True)
    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='submitted_share_grants',
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_share_grants',
    )
    approver_note = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = ShareGrantQuerySet.as_manager()

    class Meta:
        verbose_name = 'Grant chia se'
        verbose_name_plural = 'Grants chia se'
        indexes = [
            models.Index(fields=['content_type', 'object_id', 'approval_status']),
            models.Index(fields=['target_user', 'approval_status']),
            models.Index(fields=['target_group', 'approval_status']),
            models.Index(fields=['scope', 'approval_status']),
        ]
        constraints = [
            # Khong cho phep 2 grant trung lap cho cung cap (resource, scope, target, permission)
            models.UniqueConstraint(
                fields=['content_type', 'object_id', 'scope', 'target_user', 'target_group', 'permission_level'],
                name='uniq_share_grant_resource_scope_target_perm',
            ),
            # scope=colleagues PHAI co target_user
            models.CheckConstraint(
                check=(
                    ~models.Q(scope=SCOPE_COLLEAGUES)
                    | models.Q(target_user__isnull=False)
                ),
                name='ck_share_grant_colleagues_requires_user',
            ),
            # scope=group PHAI co target_group
            models.CheckConstraint(
                check=(
                    ~models.Q(scope=SCOPE_GROUP)
                    | models.Q(target_group__isnull=False)
                ),
                name='ck_share_grant_group_requires_group',
            ),
            # scope=private/everyone KHONG duoc co target
            models.CheckConstraint(
                check=(
                    ~models.Q(scope__in=[SCOPE_PRIVATE, SCOPE_EVERYONE])
                    | (models.Q(target_user__isnull=True) & models.Q(target_group__isnull=True))
                ),
                name='ck_share_grant_private_everyone_no_target',
            ),
        ]

    def __str__(self):
        target = (
            f'user={self.target_user_id}' if self.target_user_id
            else f'group={self.target_group_id}' if self.target_group_id
            else 'all'
        )
        return f'Grant#{self.pk} {self.scope}/{self.permission_level}/{self.approval_status} -> {target}'

    @property
    def is_active(self) -> bool:
        return self.approval_status == APPROVAL_ACTIVE

    @property
    def is_pending(self) -> bool:
        return self.approval_status in (APPROVAL_PENDING_LEADER, APPROVAL_PENDING_ADMIN)

    @property
    def is_rejected(self) -> bool:
        return self.approval_status == APPROVAL_REJECTED
