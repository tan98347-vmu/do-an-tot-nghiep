from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


# class Migration là bước migration thay đổi cấu trúc CSDL (theo tên file: full upgrade).
# vd: chạy "python manage.py migrate" để áp dụng thay đổi schema này.
class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0002_department'),
        ('document_templates', '0002_documenttemplate_docx_file_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # TemplateCategory
        migrations.CreateModel(
            name='TemplateCategory',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, unique=True, verbose_name='Tên danh mục')),
                ('description', models.TextField(blank=True, verbose_name='Mô tả')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'verbose_name': 'Danh mục mẫu',
                'verbose_name_plural': 'Danh mục mẫu',
                'ordering': ['name'],
            },
        ),

        # Add new fields to DocumentTemplate
        migrations.AddField(
            model_name='documenttemplate',
            name='category',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='templates',
                to='document_templates.templatecategory',
                verbose_name='Danh mục'
            ),
        ),
        migrations.AddField(
            model_name='documenttemplate',
            name='department',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='templates',
                to='accounts.department',
                verbose_name='Phòng ban'
            ),
        ),
        migrations.AddField(
            model_name='documenttemplate',
            name='status',
            field=models.CharField(
                choices=[('draft', 'Nháp'), ('pending', 'Chờ duyệt'), ('approved', 'Đã duyệt'), ('rejected', 'Bị từ chối')],
                default='draft', max_length=20, verbose_name='Trạng thái'
            ),
        ),
        migrations.AddField(
            model_name='documenttemplate',
            name='tags',
            field=models.CharField(blank=True, max_length=255, verbose_name='Tags'),
        ),
        migrations.AddField(
            model_name='documenttemplate',
            name='effective_date',
            field=models.DateField(blank=True, null=True, verbose_name='Ngày hiệu lực'),
        ),
        migrations.AddField(
            model_name='documenttemplate',
            name='review_date',
            field=models.DateField(blank=True, null=True, verbose_name='Ngày xem xét lại'),
        ),
        migrations.AddField(
            model_name='documenttemplate',
            name='version',
            field=models.CharField(default='1.0', max_length=20, verbose_name='Phiên bản'),
        ),
        migrations.AddField(
            model_name='documenttemplate',
            name='approved_by',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='approved_templates',
                to=settings.AUTH_USER_MODEL,
                verbose_name='Người duyệt'
            ),
        ),
        migrations.AddField(
            model_name='documenttemplate',
            name='approved_at',
            field=models.DateTimeField(blank=True, null=True, verbose_name='Ngày duyệt'),
        ),
        migrations.AddField(
            model_name='documenttemplate',
            name='approver_note',
            field=models.TextField(blank=True, verbose_name='Ghi chú người duyệt'),
        ),

        # TemplateVersion
        migrations.CreateModel(
            name='TemplateVersion',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('version_number', models.CharField(max_length=20, verbose_name='Số phiên bản')),
                ('content', models.TextField(verbose_name='Nội dung snapshot')),
                ('docx_file', models.FileField(blank=True, null=True, upload_to='template_versions/', verbose_name='File DOCX phiên bản')),
                ('change_note', models.TextField(blank=True, verbose_name='Ghi chú thay đổi')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('template', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='versions',
                    to='document_templates.documenttemplate'
                )),
                ('created_by', models.ForeignKey(
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='template_versions',
                    to=settings.AUTH_USER_MODEL
                )),
            ],
            options={
                'verbose_name': 'Phiên bản mẫu',
                'verbose_name_plural': 'Phiên bản mẫu',
                'ordering': ['-created_at'],
            },
        ),

        # TemplatePermission
        migrations.CreateModel(
            name='TemplatePermission',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('can_view', models.BooleanField(default=True, verbose_name='Xem')),
                ('can_edit', models.BooleanField(default=False, verbose_name='Sửa')),
                ('can_use', models.BooleanField(default=True, verbose_name='Dùng tạo văn bản')),
                ('can_approve', models.BooleanField(default=False, verbose_name='Duyệt')),
                ('template', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='permissions',
                    to='document_templates.documenttemplate'
                )),
                ('user', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='template_permissions',
                    to=settings.AUTH_USER_MODEL
                )),
            ],
            options={
                'verbose_name': 'Phân quyền mẫu',
                'verbose_name_plural': 'Phân quyền mẫu',
                'unique_together': {('template', 'user')},
            },
        ),

        # TemplateApprovalLog
        migrations.CreateModel(
            name='TemplateApprovalLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('action', models.CharField(
                    choices=[('submit', 'Gửi duyệt'), ('approve', 'Duyệt'), ('reject', 'Từ chối')],
                    max_length=20
                )),
                ('comment', models.TextField(blank=True, verbose_name='Ghi chú')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('template', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='approval_logs',
                    to='document_templates.documenttemplate'
                )),
                ('actor', models.ForeignKey(
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    to=settings.AUTH_USER_MODEL
                )),
            ],
            options={
                'verbose_name': 'Lịch sử phê duyệt',
                'verbose_name_plural': 'Lịch sử phê duyệt',
                'ordering': ['-created_at'],
            },
        ),
    ]
