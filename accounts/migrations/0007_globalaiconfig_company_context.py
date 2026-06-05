from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0006_userprofile_extra_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='globalaiconfig',
            name='company_context',
            field=models.TextField(blank=True, verbose_name='Ngữ cảnh công ty'),
        ),
    ]
