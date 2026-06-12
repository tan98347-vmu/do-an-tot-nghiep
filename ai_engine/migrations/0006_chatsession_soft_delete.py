from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


# class Migration là bước migration thay đổi cấu trúc CSDL (theo tên file: chatsession soft delete).
# vd: chạy "python manage.py migrate" để áp dụng thay đổi schema này vào database.
class Migration(migrations.Migration):

    dependencies = [
        ('ai_engine', '0005_chataudioattachment'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='chatsession',
            name='deleted_at',
            field=models.DateTimeField(blank=True, db_index=True, null=True),
        ),
        migrations.AddField(
            model_name='chatsession',
            name='deleted_by',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='deleted_chat_sessions',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name='chatsession',
            name='is_deleted',
            field=models.BooleanField(db_index=True, default=False),
        ),
    ]
