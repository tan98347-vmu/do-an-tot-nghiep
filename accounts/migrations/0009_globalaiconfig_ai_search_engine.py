from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0008_globalaiconfig_ai_internet_results'),
    ]

    operations = [
        migrations.AddField(
            model_name='globalaiconfig',
            name='ai_search_engine',
            field=models.CharField(default='bing', max_length=20, verbose_name='Search engine Internet'),
        ),
    ]
