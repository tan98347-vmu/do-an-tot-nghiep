from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('documents', '0006_remove_document_tags'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='document',
            name='version_number',
            field=models.IntegerField(default=1, verbose_name='Phiên bản'),
        ),
        migrations.CreateModel(
            name='DocumentVersion',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('version_number', models.IntegerField(default=1, verbose_name='Số phiên bản')),
                ('content', models.TextField(blank=True, verbose_name='Nội dung')),
                ('output_file', models.FileField(blank=True, null=True, upload_to='doc_versions/', verbose_name='File DOCX')),
                ('change_note', models.CharField(blank=True, max_length=500, verbose_name='Ghi chú thay đổi')),
                ('variables_used', models.JSONField(blank=True, default=dict, verbose_name='Biến đã dùng')),
                ('is_hidden', models.BooleanField(default=False, verbose_name='Ẩn')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('created_by', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='doc_versions',
                    to=settings.AUTH_USER_MODEL,
                    verbose_name='Người tạo',
                )),
                ('document', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='versions',
                    to='documents.document',
                    verbose_name='Văn bản',
                )),
            ],
            options={'verbose_name': 'Phiên bản văn bản', 'verbose_name_plural': 'Phiên bản văn bản', 'ordering': ['-version_number']},
        ),
    ]
