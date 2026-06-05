from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('documents', '0012_alter_document_options_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='WordWorker',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('worker_key', models.CharField(max_length=100, unique=True)),
                ('slot_label', models.CharField(max_length=32)),
                ('host_name', models.CharField(blank=True, max_length=120)),
                ('status', models.CharField(choices=[('idle', 'Idle'), ('busy', 'Busy'), ('paused', 'Paused'), ('offline', 'Offline')], default='idle', max_length=16)),
                ('metadata', models.JSONField(blank=True, default=dict)),
                ('last_seen_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={'ordering': ['worker_key']},
        ),
        migrations.CreateModel(
            name='WordEditJob',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('instruction', models.TextField()),
                ('edit_mode', models.CharField(default='direct_edit', max_length=32)),
                ('plan_mode', models.CharField(blank=True, max_length=32)),
                ('preferred_slot', models.CharField(blank=True, max_length=32)),
                ('current_slot_label', models.CharField(blank=True, max_length=32)),
                ('track_changes', models.BooleanField(default=False)),
                ('status', models.CharField(choices=[('queued', 'Queued'), ('claimed', 'Claimed'), ('editing', 'Editing'), ('uploading', 'Uploading'), ('completed', 'Completed'), ('failed', 'Failed'), ('cancelled', 'Cancelled'), ('needs_review', 'Needs review')], db_index=True, default='queued', max_length=24)),
                ('llm_model_name', models.CharField(blank=True, max_length=120)),
                ('llm_temperature', models.FloatField(default=0)),
                ('ollama_base_url', models.CharField(blank=True, max_length=255)),
                ('prompt_version', models.CharField(blank=True, max_length=64)),
                ('allow_cloud_model', models.BooleanField(default=True)),
                ('plan_payload', models.JSONField(blank=True, default=dict)),
                ('heartbeat_payload', models.JSONField(blank=True, default=dict)),
                ('result_summary', models.TextField(blank=True)),
                ('change_note', models.CharField(blank=True, max_length=500)),
                ('error_code', models.CharField(blank=True, max_length=120)),
                ('error_detail', models.TextField(blank=True)),
                ('artifact_file', models.FileField(blank=True, null=True, upload_to='word_ai/jobs/')),
                ('claimed_at', models.DateTimeField(blank=True, null=True)),
                ('completed_at', models.DateTimeField(blank=True, null=True)),
                ('failed_at', models.DateTimeField(blank=True, null=True)),
                ('cancelled_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('current_worker', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='claimed_jobs', to='word_ai.wordworker')),
                ('document', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='word_ai_jobs', to='documents.document')),
                ('requested_by', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='requested_word_ai_jobs', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-created_at'],
                'indexes': [
                    models.Index(fields=['status', 'created_at'], name='word_ai_job_status_created_idx'),
                    models.Index(fields=['document', 'status'], name='word_ai_job_doc_status_idx'),
                ],
            },
        ),
        migrations.CreateModel(
            name='WordEditJobEvent',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('level', models.CharField(default='info', max_length=16)),
                ('step', models.CharField(blank=True, max_length=64)),
                ('status', models.CharField(blank=True, max_length=32)),
                ('message', models.TextField(blank=True)),
                ('payload', models.JSONField(blank=True, default=dict)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('job', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='events', to='word_ai.wordeditjob')),
                ('worker', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='events', to='word_ai.wordworker')),
            ],
            options={'ordering': ['created_at', 'id']},
        ),
    ]
