from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def provision_internal_pki_credentials(apps, schema_editor):
    from signing.internal_pki import ensure_all_active_users_have_signing_credentials

    ensure_all_active_users_have_signing_credentials()


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('signing', '0002_pki_cutover'),
    ]

    operations = [
        migrations.CreateModel(
            name='InternalPkiConfig',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('ca_certificate_pem', models.TextField(blank=True)),
                ('encrypted_private_key_pem', models.TextField(blank=True)),
                ('valid_from', models.DateTimeField(blank=True, null=True)),
                ('valid_to', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Cau hinh CA PKI noi bo',
                'verbose_name_plural': 'Cau hinh CA PKI noi bo',
            },
        ),
        migrations.CreateModel(
            name='UserSigningKeySecret',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('encrypted_private_key_pem', models.TextField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('credential', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='key_secret', to='signing.usersigningcredential')),
            ],
            options={
                'verbose_name': 'Bi mat khoa rieng cua user',
                'verbose_name_plural': 'Bi mat khoa rieng cua user',
            },
        ),
        migrations.RunPython(provision_internal_pki_credentials, migrations.RunPython.noop),
    ]
