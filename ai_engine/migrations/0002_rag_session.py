from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ai_engine', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='chatsession',
            name='session_type',
            field=models.CharField(
                choices=[('chat', 'Chat AI'), ('rag', 'Hỏi đáp RAG')],
                default='chat', max_length=10,
            ),
        ),
        migrations.AddField(
            model_name='chatsession',
            name='rag_mode',
            field=models.CharField(blank=True, default='', max_length=20),
        ),
        migrations.AddField(
            model_name='chatmessage',
            name='citations',
            field=models.JSONField(blank=True, null=True),
        ),
    ]
