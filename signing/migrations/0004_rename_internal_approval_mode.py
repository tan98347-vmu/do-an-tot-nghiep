from django.db import migrations, models


def forwards(apps, schema_editor):
    PdfSignatureRecord = apps.get_model('signing', 'PdfSignatureRecord')
    SigningPacket = apps.get_model('signing', 'SigningPacket')
    SignedPdfDocument = apps.get_model('signing', 'SignedPdfDocument')

    SigningPacket.objects.filter(signature_mode='legacy_internal').update(
        signature_mode='internal_approval'
    )
    SignedPdfDocument.objects.filter(signature_mode='legacy_internal').update(
        signature_mode='internal_approval'
    )
    SignedPdfDocument.objects.filter(verification_status='legacy_internal').update(
        verification_status='internal_approval'
    )
    PdfSignatureRecord.objects.filter(verification_status='legacy_internal').update(
        verification_status='internal_approval'
    )


def backwards(apps, schema_editor):
    PdfSignatureRecord = apps.get_model('signing', 'PdfSignatureRecord')
    SigningPacket = apps.get_model('signing', 'SigningPacket')
    SignedPdfDocument = apps.get_model('signing', 'SignedPdfDocument')

    SigningPacket.objects.filter(signature_mode='internal_approval').update(
        signature_mode='legacy_internal'
    )
    SignedPdfDocument.objects.filter(signature_mode='internal_approval').update(
        signature_mode='legacy_internal'
    )
    SignedPdfDocument.objects.filter(verification_status='internal_approval').update(
        verification_status='legacy_internal'
    )
    PdfSignatureRecord.objects.filter(verification_status='internal_approval').update(
        verification_status='legacy_internal'
    )


class Migration(migrations.Migration):

    dependencies = [
        ('signing', '0003_internal_pki_secrets'),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
        migrations.AlterField(
            model_name='signingpacket',
            name='signature_mode',
            field=models.CharField(
                choices=[
                    ('internal_approval', 'Internal approval confirmation'),
                    ('pdf_pkcs7', 'Embedded PDF CMS/PKCS#7'),
                ],
                default='internal_approval',
                max_length=32,
            ),
        ),
        migrations.AlterField(
            model_name='signedpdfdocument',
            name='signature_mode',
            field=models.CharField(
                choices=[
                    ('internal_approval', 'Internal approval confirmation'),
                    ('pdf_pkcs7', 'Embedded PDF CMS/PKCS#7'),
                ],
                default='internal_approval',
                max_length=32,
            ),
        ),
        migrations.AlterField(
            model_name='signedpdfdocument',
            name='verification_status',
            field=models.CharField(
                choices=[
                    ('unknown', 'Chua xac minh'),
                    ('safe', 'Hop le'),
                    ('invalid', 'Khong hop le'),
                    ('untrusted', 'Khong trust duoc CA'),
                    ('tampered', 'File da bi thay doi'),
                    ('internal_approval', 'Internal approval'),
                ],
                default='unknown',
                max_length=32,
            ),
        ),
        migrations.AlterField(
            model_name='pdfsignaturerecord',
            name='verification_status',
            field=models.CharField(
                choices=[
                    ('unknown', 'Chua xac minh'),
                    ('safe', 'Hop le'),
                    ('invalid', 'Khong hop le'),
                    ('untrusted', 'Khong trust duoc CA'),
                    ('tampered', 'File da bi thay doi'),
                    ('internal_approval', 'Internal approval'),
                ],
                default='unknown',
                max_length=32,
            ),
        ),
    ]
