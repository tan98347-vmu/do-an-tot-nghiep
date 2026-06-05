from django.db import migrations, models


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
