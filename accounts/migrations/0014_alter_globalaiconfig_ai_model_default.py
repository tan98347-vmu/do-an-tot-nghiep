from django.db import migrations, models


def set_existing_ai_model_to_kimi(apps, schema_editor):
    GlobalAIConfig = apps.get_model('accounts', 'GlobalAIConfig')
    GlobalAIConfig.objects.all().update(ai_model='kimi-k2.6:cloud')


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0013_globalaiconfig_rag_defaults'),
    ]

    operations = [
        migrations.AlterField(
            model_name='globalaiconfig',
            name='ai_model',
            field=models.CharField(default='kimi-k2.6:cloud', max_length=100, verbose_name='Model AI'),
        ),
        migrations.RunPython(set_existing_ai_model_to_kimi, migrations.RunPython.noop),
    ]
