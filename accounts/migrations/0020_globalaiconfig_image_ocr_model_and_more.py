from django.db import migrations, models


OLD_DEFAULT_OCR_MODEL = 'qwen3-vl:4b'
DEFAULT_IMAGE_OCR_MODEL = 'qwen3-vl:235b-cloud'


def seed_image_ocr_models(apps, schema_editor):
    GlobalAIConfig = apps.get_model('accounts', 'GlobalAIConfig')
    CompanyAIConfig = apps.get_model('accounts', 'CompanyAIConfig')

    for config in GlobalAIConfig.objects.all():
        ocr_model = str(getattr(config, 'ocr_model', '') or '').strip()
        if ocr_model and ocr_model != OLD_DEFAULT_OCR_MODEL:
            config.image_ocr_model = ocr_model
        elif not str(getattr(config, 'image_ocr_model', '') or '').strip():
            config.image_ocr_model = DEFAULT_IMAGE_OCR_MODEL
        config.save(update_fields=['image_ocr_model'])

    for config in CompanyAIConfig.objects.all():
        ocr_model = str(getattr(config, 'ocr_model', '') or '').strip()
        if ocr_model and ocr_model != OLD_DEFAULT_OCR_MODEL:
            config.image_ocr_model = ocr_model
        elif not str(getattr(config, 'image_ocr_model', '') or '').strip():
            config.image_ocr_model = DEFAULT_IMAGE_OCR_MODEL
        config.save(update_fields=['image_ocr_model'])


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0019_userprofile_is_platform_admin_account'),
    ]

    operations = [
        migrations.AddField(
            model_name='companyaiconfig',
            name='image_ocr_model',
            field=models.CharField(default='qwen3-vl:235b-cloud', max_length=100),
        ),
        migrations.AddField(
            model_name='globalaiconfig',
            name='image_ocr_model',
            field=models.CharField(default='qwen3-vl:235b-cloud', max_length=100, verbose_name='Model OCR anh'),
        ),
        migrations.RunPython(seed_image_ocr_models, migrations.RunPython.noop),
    ]
