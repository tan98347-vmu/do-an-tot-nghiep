from django.db import migrations, models


# class Migration là bước migration thay đổi cấu trúc CSDL (theo tên file: document tags).
# vd: chạy "python manage.py migrate" để áp dụng thay đổi schema này.
class Migration(migrations.Migration):

    dependencies = [
        ('documents', '0018_document_applied_prompt_snapshot_document_prompt'),
    ]

    operations = [
        migrations.AddField(
            model_name='document',
            name='tags',
            field=models.JSONField(blank=True, default=list, verbose_name='Tags'),
        ),
    ]
