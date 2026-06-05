from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0004_usergroup'),
        ('documents', '0004_document_source_type'),
    ]

    operations = [
        migrations.AddField(
            model_name='document',
            name='visibility',
            field=models.CharField(
                choices=[('private', 'Riêng tư'), ('group', 'Nhóm'), ('public', 'Công khai')],
                default='private',
                max_length=10,
                verbose_name='Phạm vi hiển thị',
            ),
        ),
        migrations.AddField(
            model_name='document',
            name='group',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='documents',
                to='accounts.usergroup',
                verbose_name='Nhóm',
            ),
        ),
        migrations.AddField(
            model_name='document',
            name='share_status',
            field=models.CharField(
                choices=[
                    ('active', 'Đang hoạt động'),
                    ('pending_leader', 'Chờ trưởng nhóm duyệt'),
                    ('pending_admin', 'Chờ admin duyệt'),
                    ('rejected', 'Bị từ chối'),
                ],
                default='active',
                max_length=20,
                verbose_name='Trạng thái chia sẻ',
            ),
        ),
    ]
