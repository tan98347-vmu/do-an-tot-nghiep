from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ('accounts', '0022_companyaiconfig_chat_ai_model_and_more'),
    ]

    operations = [
        migrations.RunSQL(
            sql='CREATE EXTENSION IF NOT EXISTS unaccent;',
            reverse_sql='DROP EXTENSION IF EXISTS unaccent;',
        ),
    ]
