from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ('document_templates', '0008_templatefavorite'),
    ]
    operations = [
        migrations.AddField(
            model_name='templateversion',
            name='is_hidden',
            field=models.BooleanField(default=False, verbose_name='Ẩn phiên bản'),
        ),
    ]
