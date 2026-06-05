from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('documents', '0007_document_versioning'),
    ]

    operations = [
        migrations.CreateModel(
            name='DocumentFavorite',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('document', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='favorites', to='documents.document')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='favorite_documents', to='auth.user')),
            ],
            options={
                'verbose_name': 'Van ban ua thich',
                'unique_together': {('user', 'document')},
            },
        ),
    ]
