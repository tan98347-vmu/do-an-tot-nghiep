from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


# class Migration là bước migration thay đổi cấu trúc CSDL (theo tên file: document mailbox).
# vd: chạy "python manage.py migrate" để áp dụng thay đổi schema này.
class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('signing', '0002_pki_cutover'),
        ('documents', '0009_alter_documentversion_id'),
    ]

    operations = [
        migrations.CreateModel(
            name='DocumentMailboxThread',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('source_version_number', models.IntegerField(default=1)),
                ('source_docx_sha256', models.CharField(blank=True, max_length=64)),
                ('status', models.CharField(choices=[('view', 'Xem'), ('forward', 'Dang duoc forward'), ('completed', 'Da hoan thanh'), ('rejected', 'Da bi tu choi')], default='view', max_length=32)),
                ('last_action_at', models.DateTimeField(blank=True, null=True)),
                ('last_action_summary', models.CharField(blank=True, max_length=500)),
                ('last_action_reason', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('created_by', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='created_mailbox_threads', to=settings.AUTH_USER_MODEL)),
                ('document', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='mailbox_threads', to='documents.document')),
                ('last_action_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='mailbox_thread_actions', to=settings.AUTH_USER_MODEL)),
                ('source_signed_pdf', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='mailbox_threads', to='signing.signedpdfdocument')),
            ],
            options={
                'verbose_name': 'Luong hom thu van ban',
                'verbose_name_plural': 'Luong hom thu van ban',
                'ordering': ['-updated_at', '-created_at'],
            },
        ),
        migrations.CreateModel(
            name='DocumentMailboxEntry',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.CharField(choices=[('view', 'Xem'), ('forward', 'Dang duoc forward'), ('completed', 'Da hoan thanh'), ('rejected', 'Da bi tu choi')], default='view', max_length=32)),
                ('note', models.TextField(blank=True)),
                ('action_reason', models.TextField(blank=True)),
                ('actioned_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('actioned_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='mailbox_entry_actions', to=settings.AUTH_USER_MODEL)),
                ('forwarded_by', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='mailbox_entries_sent', to=settings.AUTH_USER_MODEL)),
                ('forwarded_to', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='mailbox_entries_received', to=settings.AUTH_USER_MODEL)),
                ('parent_entry', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='children', to='documents.documentmailboxentry')),
                ('signed_pdf', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='mailbox_entries', to='signing.signedpdfdocument')),
                ('thread', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='entries', to='documents.documentmailboxthread')),
            ],
            options={
                'verbose_name': 'Entry hom thu van ban',
                'verbose_name_plural': 'Entry hom thu van ban',
                'ordering': ['-created_at'],
            },
        ),
    ]
