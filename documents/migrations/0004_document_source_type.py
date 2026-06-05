from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('documents', '0003_full_upgrade'),
    ]

    operations = [
        migrations.AddField(
            model_name='document',
            name='source_type',
            field=models.CharField(
                choices=[('generated', 'Tạo từ server'), ('uploaded', 'Upload')],
                default='generated',
                max_length=20,
                verbose_name='Nguồn tạo',
            ),
        ),
    ]
