from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0003_globalaiconfig_remove_ai_fields'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='UserGroup',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, unique=True, verbose_name='Tên nhóm')),
                ('description', models.TextField(blank=True, verbose_name='Mô tả')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('created_by', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='created_groups',
                    to=settings.AUTH_USER_MODEL,
                    verbose_name='Người tạo',
                )),
            ],
            options={
                'verbose_name': 'Nhóm người dùng',
                'verbose_name_plural': 'Nhóm người dùng',
                'ordering': ['name'],
            },
        ),
        migrations.CreateModel(
            name='UserGroupMembership',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('role', models.CharField(
                    choices=[('member', 'Thành viên'), ('leader', 'Trưởng nhóm')],
                    default='member',
                    max_length=10,
                )),
                ('joined_at', models.DateTimeField(auto_now_add=True)),
                ('group', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='memberships',
                    to='accounts.usergroup',
                )),
                ('user', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='group_memberships',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                'verbose_name': 'Thành viên nhóm',
                'verbose_name_plural': 'Thành viên nhóm',
                'unique_together': {('group', 'user')},
            },
        ),
    ]
