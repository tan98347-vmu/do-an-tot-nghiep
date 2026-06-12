from django.db import migrations, models


# class Migration là bước migration thay đổi cấu trúc CSDL (theo tên file: document source type).
# vd: chạy "python manage.py migrate" để áp dụng thay đổi schema này.
class Migration(migrations.Migration):

    dependencies = [
        ('documents', '0003_full_upgrade'),
    ]

    operations = [
        migrations.AddField(
            model_name='document',
            name='source_type',
            field=models.CharField(
                choices=[('generated', 'Tạo từ server'), ('uploaded', 'Upload')],
                default='generated',
                max_length=20,
                verbose_name='Nguồn tạo',
            ),
        ),
    ]
