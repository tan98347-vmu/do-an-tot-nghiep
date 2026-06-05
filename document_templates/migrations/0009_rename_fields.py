from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('document_templates', '0008_templatefavorite'),
    ]

    operations = [
        migrations.RenameField(
            model_name='documenttemplate',
            old_name='tags',
            new_name='notes',
        ),
        migrations.RenameField(
            model_name='documenttemplate',
            old_name='review_date',
            new_name='end_date',
        ),
    ]
