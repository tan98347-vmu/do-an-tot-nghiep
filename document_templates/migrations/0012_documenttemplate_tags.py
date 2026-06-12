from django.db import migrations, models


# class Migration là bước migration thay đổi cấu trúc CSDL (theo tên file: documenttemplate tags).
# vd: chạy "python manage.py migrate" để áp dụng thay đổi schema này.
class Migration(migrations.Migration):

    dependencies = [
        ('document_templates', '0011_merge_20260315_0605'),
    ]

    operations = [
        migrations.AddField(
            model_name='documenttemplate',
            name='tags',
            field=models.JSONField(blank=True, default=list, verbose_name='Tags'),
        ),
    ]
