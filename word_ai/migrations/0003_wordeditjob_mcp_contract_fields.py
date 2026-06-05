from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('word_ai', '0002_wordeditjob_result_version'),
    ]

    operations = [
        migrations.AddField(
            model_name='wordeditjob',
            name='artifact_manifest',
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name='wordeditjob',
            name='document_checksums',
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name='wordeditjob',
            name='execution_payload',
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name='wordeditjob',
            name='mcp_session_id',
            field=models.CharField(blank=True, max_length=120),
        ),
        migrations.AddField(
            model_name='wordeditjob',
            name='tool_transcript',
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AddField(
            model_name='wordeditjob',
            name='verification_summary',
            field=models.JSONField(blank=True, default=dict),
        ),
    ]
