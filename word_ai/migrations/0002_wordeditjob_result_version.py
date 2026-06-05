from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('documents', '0012_alter_document_options_and_more'),
        ('word_ai', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='wordeditjob',
            name='result_version',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=models.deletion.SET_NULL,
                related_name='word_ai_jobs',
                to='documents.documentversion',
            ),
        ),
    ]
