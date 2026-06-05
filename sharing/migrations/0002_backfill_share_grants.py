"""
Backfill ShareGrant tu du lieu chia se cu cho 3 resource.

3 nguon:
  1. visibility cu (private/group/public) tren Document/DocumentTemplate/Prompt
     -> scope tuong ung + approval_status theo `status`/`share_status`.
  2. *AudienceMember + peer_share_status -> scope=colleagues grants.
  3. TemplatePermission booleans -> scope=colleagues grants (template only).

Migration nay IDEMPOTENT - chay lai khong tao trung nho update_or_create.
"""

from django.db import migrations


SCOPE_PRIVATE = 'private'
SCOPE_GROUP = 'group'
SCOPE_COLLEAGUES = 'colleagues'
SCOPE_EVERYONE = 'everyone'

PERM_VIEW = 'view'
PERM_EDIT = 'edit'
PERM_DELETE = 'delete'

APPROVAL_ACTIVE = 'active'
APPROVAL_PENDING_LEADER = 'pending_leader'
APPROVAL_PENDING_ADMIN = 'pending_admin'
APPROVAL_REJECTED = 'rejected'


def _backfill_resource_visibility(apps, ContentType, ShareGrant, model_label, model_name, status_field, status_active_values, status_pending_leader, status_pending_admin, status_rejected):
    """Backfill grants tu truong `visibility` tren 1 model."""
    try:
        Model = apps.get_model(model_label, model_name)
    except LookupError:
        return
    ct = ContentType.objects.get_for_model(Model)

    for resource in Model.objects.all().iterator():
        visibility = getattr(resource, 'visibility', None)
        status = getattr(resource, status_field, None)

        # Bo qua private (khong can grant)
        if visibility == 'private' or visibility is None:
            continue

        # Map status sang approval_status
        if status in status_active_values:
            approval = APPROVAL_ACTIVE
        elif status == status_pending_leader:
            approval = APPROVAL_PENDING_LEADER
        elif status == status_pending_admin:
            approval = APPROVAL_PENDING_ADMIN
        elif status == status_rejected:
            approval = APPROVAL_REJECTED
        else:
            approval = APPROVAL_ACTIVE  # default fallback

        if visibility == 'group':
            group_id = getattr(resource, 'group_id', None)
            if group_id is None:
                continue
            ShareGrant.objects.update_or_create(
                content_type=ct,
                object_id=resource.pk,
                scope=SCOPE_GROUP,
                target_user=None,
                target_group_id=group_id,
                permission_level=PERM_VIEW,
                defaults={
                    'approval_status': approval,
                    'created_by_id': getattr(resource, 'owner_id', None) or getattr(resource, 'created_by_id', None),
                    'approved_by_id': getattr(resource, 'approved_by_id', None),
                    'approved_at': getattr(resource, 'approved_at', None),
                    'approver_note': getattr(resource, 'approver_note', '') or '',
                },
            )
        elif visibility == 'public':
            ShareGrant.objects.update_or_create(
                content_type=ct,
                object_id=resource.pk,
                scope=SCOPE_EVERYONE,
                target_user=None,
                target_group=None,
                permission_level=PERM_VIEW,
                defaults={
                    'approval_status': approval,
                    'created_by_id': getattr(resource, 'owner_id', None) or getattr(resource, 'created_by_id', None),
                    'approved_by_id': getattr(resource, 'approved_by_id', None),
                    'approved_at': getattr(resource, 'approved_at', None),
                    'approver_note': getattr(resource, 'approver_note', '') or '',
                },
            )


def _backfill_audience(apps, ContentType, ShareGrant, audience_model_label, audience_model_name, resource_fk_name, resource_model_label, resource_model_name):
    """Backfill grants tu *AudienceMember + peer_share_status tren resource."""
    try:
        AudienceModel = apps.get_model(audience_model_label, audience_model_name)
        ResourceModel = apps.get_model(resource_model_label, resource_model_name)
    except LookupError:
        return
    ct = ContentType.objects.get_for_model(ResourceModel)

    for member in AudienceModel.objects.all().iterator():
        resource = getattr(member, resource_fk_name, None)
        if resource is None:
            continue
        peer_status = getattr(resource, 'peer_share_status', 'none')

        if peer_status == 'active':
            approval = APPROVAL_ACTIVE
        elif peer_status == 'pending_leader':
            approval = APPROVAL_PENDING_LEADER
        elif peer_status == 'rejected':
            approval = APPROVAL_REJECTED
        else:
            # none -> bo qua (audience khong active)
            continue

        permission = getattr(member, 'permission_level', PERM_VIEW) or PERM_VIEW
        if permission not in (PERM_VIEW, PERM_EDIT, PERM_DELETE):
            permission = PERM_VIEW

        ShareGrant.objects.update_or_create(
            content_type=ct,
            object_id=resource.pk,
            scope=SCOPE_COLLEAGUES,
            target_user_id=member.user_id,
            target_group=None,
            permission_level=permission,
            defaults={
                'approval_status': approval,
                'created_by_id': getattr(resource, 'owner_id', None),
                'approved_by_id': getattr(resource, 'peer_share_approved_by_id', None),
                'approved_at': getattr(resource, 'peer_share_approved_at', None),
                'submitted_at': getattr(resource, 'peer_share_submitted_at', None),
                'approver_note': getattr(resource, 'peer_share_approver_note', '') or '',
            },
        )


def _backfill_template_permission(apps, ContentType, ShareGrant):
    """Backfill grants tu TemplatePermission booleans (can_view/can_edit/can_delete)."""
    try:
        TemplatePermission = apps.get_model('document_templates', 'TemplatePermission')
        DocumentTemplate = apps.get_model('document_templates', 'DocumentTemplate')
    except LookupError:
        return
    ct = ContentType.objects.get_for_model(DocumentTemplate)

    for perm in TemplatePermission.objects.all().iterator():
        # Suy ra permission cao nhat
        if getattr(perm, 'can_delete', False):
            level = PERM_DELETE
        elif getattr(perm, 'can_edit', False):
            level = PERM_EDIT
        elif getattr(perm, 'can_view', True):
            level = PERM_VIEW
        else:
            continue

        ShareGrant.objects.update_or_create(
            content_type=ct,
            object_id=perm.template_id,
            scope=SCOPE_COLLEAGUES,
            target_user_id=perm.user_id,
            target_group=None,
            permission_level=level,
            defaults={
                'approval_status': APPROVAL_ACTIVE,
                'created_by_id': getattr(perm.template, 'owner_id', None) if hasattr(perm, 'template') else None,
            },
        )


def forwards(apps, schema_editor):
    ContentType = apps.get_model('contenttypes', 'ContentType')
    ShareGrant = apps.get_model('sharing', 'ShareGrant')

    # 1. Document visibility
    _backfill_resource_visibility(
        apps, ContentType, ShareGrant,
        'documents', 'Document',
        status_field='share_status',
        status_active_values=('active',),
        status_pending_leader='pending_leader',
        status_pending_admin='pending_admin',
        status_rejected='rejected',
    )

    # 2. DocumentTemplate visibility
    _backfill_resource_visibility(
        apps, ContentType, ShareGrant,
        'document_templates', 'DocumentTemplate',
        status_field='status',
        status_active_values=('approved',),
        status_pending_leader='pending_leader',
        status_pending_admin='pending',
        status_rejected='rejected',
    )

    # 3. Prompt visibility
    _backfill_resource_visibility(
        apps, ContentType, ShareGrant,
        'prompts', 'Prompt',
        status_field='status',
        status_active_values=('approved',),
        status_pending_leader='pending_leader',
        status_pending_admin='pending',
        status_rejected='rejected',
    )

    # 4. Audience members -> colleagues grants
    _backfill_audience(
        apps, ContentType, ShareGrant,
        'documents', 'DocumentAudienceMember', 'document',
        'documents', 'Document',
    )
    _backfill_audience(
        apps, ContentType, ShareGrant,
        'document_templates', 'TemplateAudienceMember', 'template',
        'document_templates', 'DocumentTemplate',
    )
    _backfill_audience(
        apps, ContentType, ShareGrant,
        'prompts', 'PromptAudienceMember', 'prompt',
        'prompts', 'Prompt',
    )

    # 5. TemplatePermission -> colleagues grants
    _backfill_template_permission(apps, ContentType, ShareGrant)


def backwards(apps, schema_editor):
    # Khong khoi phuc du lieu cu, chi xoa toan bo grant.
    # Du lieu cu (visibility/peer_share/TemplatePermission) van con nguyen ven.
    ShareGrant = apps.get_model('sharing', 'ShareGrant')
    ShareGrant.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('sharing', '0001_initial'),
        ('documents', '0021_documentaudiencemember_permission_level'),
        ('document_templates', '0021_templateaudiencemember_permission_level'),
        ('prompts', '0009_prompt_usage_scope_and_more'),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
