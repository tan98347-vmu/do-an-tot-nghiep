from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('document_templates', '0013_alter_documenttemplate_status'),
    ]

    operations = [
        migrations.CreateModel(
            name='TemplateAudienceMember',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                (
                    'template',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='audience_members',
                        to='document_templates.documenttemplate',
                        verbose_name='Mau van ban',
                    ),
                ),
                (
                    'user',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='template_audience_memberships',
                        to=settings.AUTH_USER_MODEL,
                        verbose_name='Nguoi duoc dung mau',
                    ),
                ),
            ],
            options={
                'verbose_name': 'Nguoi duoc dung mau theo nhom',
                'verbose_name_plural': 'Nguoi duoc dung mau theo nhom',
                'unique_together': {('template', 'user')},
            },
        ),
    ]
