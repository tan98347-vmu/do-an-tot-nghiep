from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('contenttypes', '0002_remove_content_type_name'),
        ('accounts', '0023_unaccent'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='ShareGrant',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('object_id', models.PositiveBigIntegerField()),
                ('scope', models.CharField(
                    choices=[
                        ('private', 'Rieng tu'),
                        ('group', 'Nhom'),
                        ('colleagues', 'Dong nghiep'),
                        ('everyone', 'Moi nguoi'),
                    ],
                    db_index=True,
                    max_length=16,
                    verbose_name='Pham vi',
                )),
                ('permission_level', models.CharField(
                    choices=[
                        ('view', 'Chi xem'),
                        ('edit', 'Xem & sua'),
                        ('delete', 'Toan quyen (xem, sua, xoa)'),
                    ],
                    default='view',
                    max_length=8,
                    verbose_name='Quyen han',
                )),
                ('approval_status', models.CharField(
                    choices=[
                        ('draft', 'Nhap'),
                        ('pending_leader', 'Cho truong nhom duyet'),
                        ('pending_admin', 'Cho admin duyet'),
                        ('active', 'Da kich hoat'),
                        ('rejected', 'Bi tu choi'),
                    ],
                    db_index=True,
                    default='draft',
                    max_length=20,
                    verbose_name='Trang thai duyet',
                )),
                ('submitted_at', models.DateTimeField(blank=True, null=True)),
                ('approved_at', models.DateTimeField(blank=True, null=True)),
                ('approver_note', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('approved_by', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='approved_share_grants',
                    to=settings.AUTH_USER_MODEL,
                )),
                ('content_type', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='share_grants',
                    to='contenttypes.contenttype',
                )),
                ('created_by', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='created_share_grants',
                    to=settings.AUTH_USER_MODEL,
                    verbose_name='Nguoi tao grant (owner cua resource)',
                )),
                ('submitted_by', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='submitted_share_grants',
                    to=settings.AUTH_USER_MODEL,
                )),
                ('target_group', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='received_share_grants',
                    to='accounts.usergroup',
                    verbose_name='Nhom duoc chia se',
                )),
                ('target_user', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='received_share_grants',
                    to=settings.AUTH_USER_MODEL,
                    verbose_name='Nguoi duoc chia se',
                )),
            ],
            options={
                'verbose_name': 'Grant chia se',
                'verbose_name_plural': 'Grants chia se',
            },
        ),
        migrations.AddIndex(
            model_name='sharegrant',
            index=models.Index(
                fields=['content_type', 'object_id', 'approval_status'],
                name='sharing_sha_content_d63b5e_idx',
            ),
        ),
        migrations.AddIndex(
            model_name='sharegrant',
            index=models.Index(
                fields=['target_user', 'approval_status'],
                name='sharing_sha_target__22a4d8_idx',
            ),
        ),
        migrations.AddIndex(
            model_name='sharegrant',
            index=models.Index(
                fields=['target_group', 'approval_status'],
                name='sharing_sha_target__f3e74c_idx',
            ),
        ),
        migrations.AddIndex(
            model_name='sharegrant',
            index=models.Index(
                fields=['scope', 'approval_status'],
                name='sharing_sha_scope_b16291_idx',
            ),
        ),
        migrations.AddConstraint(
            model_name='sharegrant',
            constraint=models.UniqueConstraint(
                fields=('content_type', 'object_id', 'scope', 'target_user', 'target_group', 'permission_level'),
                name='uniq_share_grant_resource_scope_target_perm',
            ),
        ),
        migrations.AddConstraint(
            model_name='sharegrant',
            constraint=models.CheckConstraint(
                check=~models.Q(scope='colleagues') | models.Q(target_user__isnull=False),
                name='ck_share_grant_colleagues_requires_user',
            ),
        ),
        migrations.AddConstraint(
            model_name='sharegrant',
            constraint=models.CheckConstraint(
                check=~models.Q(scope='group') | models.Q(target_group__isnull=False),
                name='ck_share_grant_group_requires_group',
            ),
        ),
        migrations.AddConstraint(
            model_name='sharegrant',
            constraint=models.CheckConstraint(
                check=(
                    ~models.Q(scope__in=['private', 'everyone'])
                    | (models.Q(target_user__isnull=True) & models.Q(target_group__isnull=True))
                ),
                name='ck_share_grant_private_everyone_no_target',
            ),
        ),
    ]
