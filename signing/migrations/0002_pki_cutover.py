from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def backfill_legacy_signature_metadata(apps, schema_editor):
    SignedPdfDocument = apps.get_model('signing', 'SignedPdfDocument')
    SigningTask = apps.get_model('signing', 'SigningTask')

    for signed_doc in SignedPdfDocument.objects.select_related('packet').all():
        signed_count = SigningTask.objects.filter(packet_id=signed_doc.packet_id, status='signed').count()
        signed_doc.signature_mode = 'legacy_internal'
        signed_doc.verification_status = 'legacy_internal'
        signed_doc.signature_count = signed_count
        signed_doc.save(update_fields=['signature_mode', 'verification_status', 'signature_count'])


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('signing', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='signedpdfdocument',
            name='signature_count',
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='signedpdfdocument',
            name='signature_mode',
            field=models.CharField(
                choices=[('legacy_internal', 'Legacy internal confirmation'), ('pdf_pkcs7', 'Embedded PDF CMS/PKCS#7')],
                default='legacy_internal',
                max_length=32,
            ),
        ),
        migrations.AddField(
            model_name='signedpdfdocument',
            name='verification_checked_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='signedpdfdocument',
            name='verification_status',
            field=models.CharField(
                choices=[
                    ('unknown', 'Chua xac minh'),
                    ('safe', 'Hop le'),
                    ('invalid', 'Khong hop le'),
                    ('untrusted', 'Khong trust duoc CA'),
                    ('tampered', 'File da bi thay doi'),
                    ('legacy_internal', 'Legacy internal'),
                ],
                default='unknown',
                max_length=32,
            ),
        ),
        migrations.AddField(
            model_name='signingpacket',
            name='signature_mode',
            field=models.CharField(
                choices=[('legacy_internal', 'Legacy internal confirmation'), ('pdf_pkcs7', 'Embedded PDF CMS/PKCS#7')],
                default='legacy_internal',
                max_length=32,
            ),
        ),
        migrations.AddField(
            model_name='signingtask',
            name='signature_field_name',
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.CreateModel(
            name='UserSigningCredential',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('provider', models.CharField(max_length=64)),
                ('key_alias', models.CharField(blank=True, max_length=255)),
                ('key_id', models.CharField(blank=True, max_length=255)),
                ('certificate_pem', models.TextField()),
                ('subject_dn', models.CharField(max_length=1000)),
                ('serial_number', models.CharField(max_length=128)),
                ('issuer_dn', models.CharField(max_length=1000)),
                ('valid_from', models.DateTimeField()),
                ('valid_to', models.DateTimeField()),
                ('status', models.CharField(
                    choices=[('active', 'Dang hoat dong'), ('inactive', 'Tam ngung'), ('revoked', 'Da thu hoi'), ('expired', 'Het han')],
                    default='inactive',
                    max_length=32,
                )),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='signing_credentials', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Rang buoc chung thu ky cua user',
                'verbose_name_plural': 'Rang buoc chung thu ky cua user',
                'ordering': ['user_id', '-updated_at'],
            },
        ),
        migrations.CreateModel(
            name='PdfSignatureRecord',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('signature_field_name', models.CharField(blank=True, max_length=255)),
                ('certificate_fingerprint', models.CharField(max_length=128)),
                ('certificate_subject_dn', models.CharField(blank=True, max_length=1000)),
                ('certificate_serial_number', models.CharField(blank=True, max_length=128)),
                ('certificate_issuer_dn', models.CharField(blank=True, max_length=1000)),
                ('signature_algorithm', models.CharField(blank=True, max_length=128)),
                ('digest_algorithm', models.CharField(blank=True, max_length=64)),
                ('provider_transaction_id', models.CharField(blank=True, max_length=255)),
                ('signed_at', models.DateTimeField()),
                ('verification_status', models.CharField(
                    choices=[
                        ('unknown', 'Chua xac minh'),
                        ('safe', 'Hop le'),
                        ('invalid', 'Khong hop le'),
                        ('untrusted', 'Khong trust duoc CA'),
                        ('tampered', 'File da bi thay doi'),
                        ('legacy_internal', 'Legacy internal'),
                    ],
                    default='unknown',
                    max_length=32,
                )),
                ('verification_report', models.JSONField(blank=True, default=dict)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('packet', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='signature_records', to='signing.signingpacket')),
                ('signed_pdf', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='signature_records', to='signing.signedpdfdocument')),
                ('signer_user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='pdf_signature_records', to=settings.AUTH_USER_MODEL)),
                ('task', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='signature_record', to='signing.signingtask')),
            ],
            options={
                'verbose_name': 'Lan ky PDF thuc',
                'verbose_name_plural': 'Lan ky PDF thuc',
                'ordering': ['signed_at', 'id'],
            },
        ),
        migrations.AddConstraint(
            model_name='usersigningcredential',
            constraint=models.UniqueConstraint(
                condition=models.Q(status='active'),
                fields=('user',),
                name='uniq_active_signing_credential_per_user',
            ),
        ),
        migrations.RunPython(backfill_legacy_signature_metadata, migrations.RunPython.noop),
    ]
