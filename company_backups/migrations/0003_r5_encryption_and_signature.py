from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('company_backups', '0002_companybackup_progress_detail_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='companybackup',
            name='encryption_meta',
            field=models.JSONField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='companybackup',
            name='signature_path',
            field=models.CharField(blank=True, default='', max_length=500),
        ),
        migrations.AddField(
            model_name='companybackup',
            name='signature_status',
            field=models.CharField(
                choices=[
                    ('unsigned', 'Chua ky'),
                    ('signed', 'Da ky'),
                    ('invalid', 'Chu ky khong hop le'),
                ],
                db_index=True,
                default='unsigned',
                max_length=16,
            ),
        ),
    ]
