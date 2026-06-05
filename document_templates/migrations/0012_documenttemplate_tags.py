from django.db import migrations, models


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
