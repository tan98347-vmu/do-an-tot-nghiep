from django.db import migrations, models


# class Migration là bước migration thay đổi cấu trúc CSDL (theo tên file: templatepermission can delete).
# vd: chạy "python manage.py migrate" để áp dụng thay đổi schema này.
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
