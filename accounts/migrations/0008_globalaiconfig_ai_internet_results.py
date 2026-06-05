from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0007_globalaiconfig_company_context'),
    ]

    operations = [
        migrations.AddField(
            model_name='globalaiconfig',
            name='ai_internet_results',
            field=models.IntegerField(default=3, verbose_name='So ket qua Internet'),
        ),
    ]
