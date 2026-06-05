from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Department',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, unique=True, verbose_name='Tên phòng ban')),
                ('code', models.CharField(max_length=20, unique=True, verbose_name='Mã phòng ban')),
                ('description', models.TextField(blank=True, verbose_name='Mô tả')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('manager', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='managed_departments',
                    to=settings.AUTH_USER_MODEL,
                    verbose_name='Trưởng phòng'
                )),
            ],
            options={
                'verbose_name': 'Phòng ban',
                'verbose_name_plural': 'Phòng ban',
                'ordering': ['name'],
            },
        ),
    ]
