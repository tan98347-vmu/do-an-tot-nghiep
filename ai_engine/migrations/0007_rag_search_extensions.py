from django.contrib.postgres.operations import TrigramExtension, UnaccentExtension
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('ai_engine', '0006_chatsession_soft_delete'),
    ]

    operations = [
        UnaccentExtension(),
        TrigramExtension(),
    ]
