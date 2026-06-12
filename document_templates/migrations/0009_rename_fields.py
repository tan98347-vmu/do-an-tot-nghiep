from django.db import migrations


# class Migration là bước migration thay đổi cấu trúc CSDL (theo tên file: rename fields).
# vd: chạy "python manage.py migrate" để áp dụng thay đổi schema này.
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
