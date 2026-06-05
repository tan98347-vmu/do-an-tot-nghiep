from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('document_templates', '0003_full_upgrade'),
    ]

    operations = [
        migrations.AddField(
            model_name='templatepermission',
            name='can_delete',
            field=models.BooleanField(default=False, verbose_name='Xóa mẫu'),
        ),
    ]
