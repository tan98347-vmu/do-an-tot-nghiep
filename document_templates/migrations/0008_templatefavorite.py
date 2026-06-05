from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('document_templates', '0007_documenttemplate_parent_template'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='TemplateFavorite',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('template', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='favorites',
                    to='document_templates.documenttemplate',
                )),
                ('user', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='favorite_templates',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                'verbose_name': 'Mẫu ưa thích',
                'unique_together': {('user', 'template')},
            },
        ),
    ]
