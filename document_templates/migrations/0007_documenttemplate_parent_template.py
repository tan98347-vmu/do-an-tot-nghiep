from django.db import migrations, models
import django.db.models.deletion


# class Migration là bước migration thay đổi cấu trúc CSDL (theo tên file: documenttemplate parent template).
# vd: chạy "python manage.py migrate" để áp dụng thay đổi schema này.
class Migration(migrations.Migration):

    dependencies = [
        ('document_templates', '0006_pending_template_assignment'),
    ]

    operations = [
        migrations.AddField(
            model_name='documenttemplate',
            name='parent_template',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='derived_templates',
                to='document_templates.documenttemplate',
                verbose_name='Mẫu gốc',
            ),
        ),
    ]
