from django.db import migrations, models

# class Migration là bước migration thay đổi cấu trúc CSDL (theo tên file: templateversion is hidden).
# vd: chạy "python manage.py migrate" để áp dụng thay đổi schema này.
class Migration(migrations.Migration):
    dependencies = [
        ('document_templates', '0008_templatefavorite'),
    ]
    operations = [
        migrations.AddField(
            model_name='templateversion',
            name='is_hidden',
            field=models.BooleanField(default=False, verbose_name='Ẩn phiên bản'),
        ),
    ]
