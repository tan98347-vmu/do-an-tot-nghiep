from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import signing.models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('accounts', '0010_globalaiconfig_ocr_model'),
        ('documents', '0009_alter_documentversion_id'),
    ]

    operations = [
        migrations.CreateModel(
            name='SigningSystemConfig',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('accounting_department', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='signing_accounting_configs', to='accounts.department', verbose_name='Phong Ke toan')),
                ('hr_department', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='signing_hr_configs', to='accounts.department', verbose_name='Phong Nhan su')),
                ('updated_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='updated_signing_configs', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Cau hinh ky so',
                'verbose_name_plural': 'Cau hinh ky so',
            },
        ),
        migrations.CreateModel(
            name='SigningProposal',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('source_version_number', models.IntegerField(default=1)),
                ('source_docx_sha256', models.CharField(blank=True, max_length=64)),
                ('proposal_note', models.TextField(blank=True)),
                ('status', models.CharField(choices=[('pending_hr_review', 'Cho Nhan su duyet'), ('approved', 'Da duyet'), ('rejected', 'Bi tu choi'), ('invalidated', 'Khong con hieu luc')], default='pending_hr_review', max_length=32)),
                ('review_note', models.TextField(blank=True)),
                ('hr_reviewed_at', models.DateTimeField(blank=True, null=True)),
                ('invalidated_reason', models.CharField(blank=True, max_length=255)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('document', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='signing_proposals', to='documents.document')),
                ('hr_reviewed_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='signing_proposals_reviewed', to=settings.AUTH_USER_MODEL)),
                ('proposed_by', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='signing_proposals_created', to=settings.AUTH_USER_MODEL)),
                ('source_version', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='signing_proposals', to='documents.documentversion')),
            ],
            options={
                'verbose_name': 'De xuat ky so',
                'verbose_name_plural': 'De xuat ky so',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='SigningPacket',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('source_version_number', models.IntegerField(default=1)),
                ('source_docx_sha256', models.CharField(blank=True, max_length=64)),
                ('pdf_snapshot', models.FileField(upload_to=signing.models._signing_snapshot_upload, verbose_name='PDF snapshot ban dau')),
                ('working_pdf', models.FileField(upload_to=signing.models._signing_working_upload, verbose_name='PDF dang duoc ky')),
                ('pdf_hash', models.CharField(blank=True, max_length=64)),
                ('status', models.CharField(choices=[('active', 'Dang cho ky'), ('rejected', 'Bi tu choi ky'), ('completed', 'Da hoan tat'), ('invalidated', 'Khong con hieu luc'), ('cancelled', 'Da huy')], default='active', max_length=32)),
                ('current_step', models.PositiveIntegerField(default=1)),
                ('rejection_reason', models.TextField(blank=True)),
                ('activated_at', models.DateTimeField(auto_now_add=True)),
                ('completed_at', models.DateTimeField(blank=True, null=True)),
                ('invalidated_at', models.DateTimeField(blank=True, null=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('document', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='signing_packets', to='documents.document')),
                ('proposal', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='packet', to='signing.signingproposal')),
                ('source_version', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='signing_packets', to='documents.documentversion')),
            ],
            options={
                'verbose_name': 'Phien ky PDF',
                'verbose_name_plural': 'Phien ky PDF',
                'ordering': ['-activated_at'],
            },
        ),
        migrations.CreateModel(
            name='SignedPdfDocument',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=255)),
                ('source_version_number', models.IntegerField(default=1)),
                ('signed_pdf_file', models.FileField(upload_to=signing.models._signed_pdf_upload)),
                ('file_hash', models.CharField(blank=True, max_length=64)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('owner', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='owned_signed_pdfs', to=settings.AUTH_USER_MODEL)),
                ('packet', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='signed_document', to='signing.signingpacket')),
                ('source_document', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='signed_pdf_records', to='documents.document')),
            ],
            options={
                'verbose_name': 'PDF da ky',
                'verbose_name_plural': 'PDF da ky',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='SigningProposalSigner',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('display_role', models.CharField(max_length=200)),
                ('group_context', models.CharField(blank=True, max_length=200)),
                ('step_no', models.PositiveIntegerField(default=1)),
                ('sort_order', models.PositiveIntegerField(default=0)),
                ('required', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('proposal', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='signers', to='signing.signingproposal')),
                ('signer_user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='signing_slots', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Nguoi ky de xuat',
                'verbose_name_plural': 'Nguoi ky de xuat',
                'ordering': ['step_no', 'sort_order', 'id'],
            },
        ),
        migrations.CreateModel(
            name='SigningTask',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('display_role', models.CharField(max_length=200)),
                ('group_context', models.CharField(blank=True, max_length=200)),
                ('step_no', models.PositiveIntegerField(default=1)),
                ('sort_order', models.PositiveIntegerField(default=0)),
                ('required', models.BooleanField(default=True)),
                ('status', models.CharField(choices=[('blocked', 'Chua mo buoc ky'), ('available', 'Can ky'), ('signed', 'Da ky'), ('rejected', 'Tu choi ky'), ('cancelled', 'Khong can xu ly nua')], default='blocked', max_length=32)),
                ('notified_at', models.DateTimeField(blank=True, null=True)),
                ('opened_at', models.DateTimeField(blank=True, null=True)),
                ('signed_at', models.DateTimeField(blank=True, null=True)),
                ('rejected_at', models.DateTimeField(blank=True, null=True)),
                ('rejection_reason', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('packet', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='tasks', to='signing.signingpacket')),
                ('proposal_signer', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='tasks', to='signing.signingproposalsigner')),
                ('signer_user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='signing_tasks', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Yeu cau ky',
                'verbose_name_plural': 'Yeu cau ky',
                'ordering': ['status', 'step_no', 'sort_order', 'id'],
            },
        ),
        migrations.CreateModel(
            name='DepartmentDelegation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('permission_type', models.CharField(choices=[('approve_signing_proposal', 'Duyet de xuat danh sach nguoi ky'), ('view_signed_pdf', 'Xem PDF da ky')], max_length=64)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='created_department_delegations', to=settings.AUTH_USER_MODEL)),
                ('delegate_user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='department_delegations', to=settings.AUTH_USER_MODEL)),
                ('department', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='delegations', to='accounts.department')),
            ],
            options={
                'verbose_name': 'Uy quyen phong ban cho ky so',
                'verbose_name_plural': 'Uy quyen phong ban cho ky so',
                'unique_together': {('department', 'delegate_user', 'permission_type')},
            },
        ),
    ]
