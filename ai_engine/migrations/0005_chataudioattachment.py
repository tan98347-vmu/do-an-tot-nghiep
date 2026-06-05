from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('ai_engine', '0004_chatsession_updated_at_chatmessage_payload_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='ChatAudioAttachment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(blank=True, max_length=255)),
                ('transcript', models.TextField(blank=True)),
                ('mime_type', models.CharField(blank=True, max_length=120)),
                ('duration_seconds', models.FloatField(default=0)),
                ('audio_file', models.FileField(upload_to='chat_audio/%Y/%m/')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('created_by', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='chat_audio_attachments', to=settings.AUTH_USER_MODEL)),
                ('message', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='audio_attachments', to='ai_engine.chatmessage')),
                ('session', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='audio_attachments', to='ai_engine.chatsession')),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
    ]
