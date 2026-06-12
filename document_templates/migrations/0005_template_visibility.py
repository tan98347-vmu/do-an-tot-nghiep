from django.db import migrations, models
import django.db.models.deletion


# class Migration là bước migration thay đổi cấu trúc CSDL (theo tên file: template visibility).
# vd: chạy "python manage.py migrate" để áp dụng thay đổi schema này.
class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0004_usergroup'),
        ('document_templates', '0004_templatepermission_can_delete'),
    ]

    operations = [
        migrations.AddField(
            model_name='documenttemplate',
            name='visibility',
            field=models.CharField(
                choices=[('private', 'Riêng tư'), ('group', 'Nhóm'), ('public', 'Công khai')],
                default='private',
                max_length=10,
                verbose_name='Phạm vi hiển thị',
            ),
        ),
        migrations.AddField(
            model_name='documenttemplate',
            name='group',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='templates',
                to='accounts.usergroup',
                verbose_name='Nhóm',
            ),
        ),
    ]
