from django.db import migrations


# class Migration là bước migration thay đổi cấu trúc CSDL (theo tên file: remove document tags).
# vd: chạy "python manage.py migrate" để áp dụng thay đổi schema này.
class Migration(migrations.Migration):

    dependencies = [
        ('documents', '0005_document_visibility'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='document',
            name='tags',
        ),
    ]
