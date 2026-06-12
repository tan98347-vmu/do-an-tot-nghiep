from django.conf import settings
from django.db import migrations, models


# class Migration là bước migration thay đổi cấu trúc CSDL (theo tên file: compliancecheckresult).
# vd: chạy "python manage.py migrate" để áp dụng thay đổi schema này vào database.
class Migration(migrations.Migration):

    dependencies = [
        ('prompts', '0008_prompt_peer_share_approved_at_and_more'),
        ('ai_engine', '0011_alter_chataudioattachment_audio_file'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='ComplianceCheckResult',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('target_type', models.CharField(choices=[('document', 'Document'), ('template', 'Template')], db_index=True, max_length=16)),
                ('target_id', models.IntegerField(db_index=True)),
                ('passed', models.BooleanField()),
                ('items_missing_json', models.JSONField(blank=True, default=list)),
                ('content_hash', models.CharField(db_index=True, max_length=64)),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=models.SET_NULL, related_name='created_compliance_checks', to=settings.AUTH_USER_MODEL)),
                ('prompt', models.ForeignKey(blank=True, null=True, on_delete=models.SET_NULL, related_name='compliance_checks', to='prompts.prompt')),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='compliancecheckresult',
            index=models.Index(fields=['target_type', 'target_id', 'prompt', 'content_hash'], name='ai_engine_co_target__d779ca_idx'),
        ),
    ]
