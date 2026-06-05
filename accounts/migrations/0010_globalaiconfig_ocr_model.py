from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0009_globalaiconfig_ai_search_engine'),
    ]

    operations = [
        migrations.AddField(
            model_name='globalaiconfig',
            name='ocr_model',
            field=models.CharField(default='qwen3-vl:4b', max_length=100, verbose_name='Model OCR'),
        ),
    ]
