"""Di tru du lieu peer-audience cu (PromptAudienceMember / TemplateAudienceMember /
DocumentAudienceMember) sang ShareGrant (scope=colleagues) de thong nhat ve ShareGrant.
"""

from django.db import migrations


# (app_label model, FK toi resource, app_label cua resource, ten model resource o ContentType)
_SPECS = [
    ('prompts', 'PromptAudienceMember', 'prompt_id', 'prompts', 'prompt'),
    ('document_templates', 'TemplateAudienceMember', 'template_id', 'document_templates', 'documenttemplate'),
    ('documents', 'DocumentAudienceMember', 'document_id', 'documents', 'document'),
]


def _resource_owner_id(resource):
    return getattr(resource, 'owner_id', None) or getattr(resource, 'created_by_id', None)


def backfill(apps, schema_editor):
    ContentType = apps.get_model('contenttypes', 'ContentType')
    ShareGrant = apps.get_model('sharing', 'ShareGrant')

    for app_label, model_name, fk_id, res_app, res_model in _SPECS:
        try:
            Member = apps.get_model(app_label, model_name)
        except LookupError:
            continue
        try:
            ct = ContentType.objects.get(app_label=res_app, model=res_model)
        except ContentType.DoesNotExist:
            continue

        for member in Member.objects.all():
            object_id = getattr(member, fk_id, None)
            if object_id is None:
                continue
            resource = getattr(member, fk_id.replace('_id', ''), None)
            owner_id = _resource_owner_id(resource) if resource is not None else None
            if owner_id == member.user_id:
                continue  # chu so huu khong can grant
            already = ShareGrant.objects.filter(
                content_type=ct,
                object_id=object_id,
                scope='colleagues',
                target_user_id=member.user_id,
            ).exists()
            if already:
                continue
            ShareGrant.objects.create(
                content_type=ct,
                object_id=object_id,
                scope='colleagues',
                permission_level=member.permission_level,
                target_user_id=member.user_id,
                approval_status='active',
                created_by_id=owner_id or getattr(member, 'added_by_id', None),
            )


def noop_reverse(apps, schema_editor):
    # Khong xoa grant khi rollback (an toan du lieu).
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('sharing', '0003_rename_sharing_sha_content_d63b5e_idx_sharing_sha_content_2479db_idx_and_more'),
        ('prompts', '0009_prompt_usage_scope_and_more'),
        ('documents', '0021_documentaudiencemember_permission_level'),
        ('document_templates', '0021_templateaudiencemember_permission_level'),
        ('contenttypes', '0002_remove_content_type_name'),
    ]

    operations = [
        migrations.RunPython(backfill, noop_reverse),
    ]
