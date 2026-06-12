from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


# class Migration là bước migration thay đổi cấu trúc CSDL (theo tên file: aiusagelog).
# vd: chạy "python manage.py migrate" để áp dụng thay đổi schema này vào database.
class Migration(migrations.Migration):

    dependencies = [
        ('ai_engine', '0002_rag_session'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='AIUsageLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('model_name', models.CharField(blank=True, default='', max_length=120)),
                ('status', models.CharField(choices=[('success', 'Success'), ('error', 'Error')], default='success', max_length=20)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='ai_usage_logs', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
    ]
