from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('documents', '0005_document_visibility'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='document',
            name='tags',
        ),
    ]
