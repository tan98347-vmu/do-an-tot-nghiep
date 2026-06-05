from django.conf import settings
from django.db import migrations, models


def normalize_global_ai_config(apps, schema_editor):
    GlobalAIConfig = apps.get_model('accounts', 'GlobalAIConfig')
    default_model = getattr(settings, 'DEFAULT_AI_MODEL', 'llama3:8b')

    for config in GlobalAIConfig.objects.all():
        update_fields = []

        engine = str(config.ai_search_engine or '').strip().lower()
        if engine in {'', 'bing', 'duckduckgo', 'tvpl', 'thuvienphapluat'}:
            if config.ai_search_engine != 'thuvienphapluat':
                config.ai_search_engine = 'thuvienphapluat'
                update_fields.append('ai_search_engine')

        if int(config.ai_max_results or 0) == 3:
            config.ai_max_results = 6
            update_fields.append('ai_max_results')

        model = str(config.ai_model or '').strip()
        lowered = model.lower()
        if not model or lowered.endswith('-cloud') or ':cloud' in lowered:
            config.ai_model = default_model
            update_fields.append('ai_model')

        if update_fields:
            config.save(update_fields=sorted(set(update_fields)))


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0012_userprofile_dia_chi_userprofile_so_dien_thoai'),
    ]

    operations = [
        migrations.AlterField(
            model_name='globalaiconfig',
            name='ai_max_results',
            field=models.IntegerField(default=6, verbose_name='So ket qua toi da'),
        ),
        migrations.AlterField(
            model_name='globalaiconfig',
            name='ai_search_engine',
            field=models.CharField(default='thuvienphapluat', max_length=20, verbose_name='Search engine Internet'),
        ),
        migrations.RunPython(normalize_global_ai_config, migrations.RunPython.noop),
    ]
