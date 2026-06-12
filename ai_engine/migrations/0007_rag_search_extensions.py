from django.contrib.postgres.operations import TrigramExtension, UnaccentExtension
from django.db import migrations


# class Migration là bước migration thay đổi cấu trúc CSDL (theo tên file: rag search extensions).
# vd: chạy "python manage.py migrate" để áp dụng thay đổi schema này vào database.
class Migration(migrations.Migration):

    dependencies = [
        ('ai_engine', '0006_chatsession_soft_delete'),
    ]

    operations = [
        UnaccentExtension(),
        TrigramExtension(),
    ]
