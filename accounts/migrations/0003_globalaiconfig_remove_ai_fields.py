from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0002_department'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # Remove AI fields from UserProfile
        migrations.RemoveField(model_name='userprofile', name='ai_config_level'),
        migrations.RemoveField(model_name='userprofile', name='ai_model'),
        migrations.RemoveField(model_name='userprofile', name='ai_temperature'),
        migrations.RemoveField(model_name='userprofile', name='ai_max_results'),
        migrations.RemoveField(model_name='userprofile', name='embedding_model'),
        # Create GlobalAIConfig singleton table
        migrations.CreateModel(
            name='GlobalAIConfig',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('ai_model', models.CharField(default='llama3:8b', max_length=100, verbose_name='Model AI')),
                ('ai_temperature', models.FloatField(default=0.0, verbose_name='Temperature')),
                ('ai_max_results', models.IntegerField(default=3, verbose_name='Số kết quả tối đa')),
                ('embedding_model', models.CharField(default='mxbai-embed-large', max_length=100, verbose_name='Embedding Model')),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('updated_by', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    to=settings.AUTH_USER_MODEL,
                    verbose_name='Cập nhật bởi'
                )),
            ],
            options={'verbose_name': 'Cấu hình AI toàn cục'},
        ),
    ]
