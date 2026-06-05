from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('accounts', '0010_globalaiconfig_ocr_model'),
    ]

    operations = [
        migrations.CreateModel(
            name='DepartmentMembership',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('is_active', models.BooleanField(default=True, verbose_name='Dang hoat dong')),
                ('joined_at', models.DateTimeField(auto_now_add=True)),
                ('department', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='memberships', to='accounts.department', verbose_name='Phong ban')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='department_memberships', to=settings.AUTH_USER_MODEL, verbose_name='Nhan vien')),
            ],
            options={
                'verbose_name': 'Thanh vien phong ban',
                'verbose_name_plural': 'Thanh vien phong ban',
                'ordering': ['department__name', 'user__username'],
                'unique_together': {('department', 'user')},
            },
        ),
    ]
