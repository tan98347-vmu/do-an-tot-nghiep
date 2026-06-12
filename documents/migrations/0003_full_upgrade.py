from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


# class Migration là bước migration thay đổi cấu trúc CSDL (theo tên file: full upgrade).
# vd: chạy "python manage.py migrate" để áp dụng thay đổi schema này.
class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0002_department'),
        ('document_templates', '0003_full_upgrade'),
        ('documents', '0002_document_output_file_alter_document_content'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # DocumentNumberConfig
        migrations.CreateModel(
            name='DocumentNumberConfig',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('prefix', models.CharField(max_length=20, verbose_name='Tiền tố')),
                ('year', models.IntegerField(verbose_name='Năm')),
                ('last_number', models.IntegerField(default=0, verbose_name='Số cuối')),
                ('format_str', models.CharField(
                    default='{prefix}-{number:04d}/{year}',
                    max_length=100,
                    verbose_name='Định dạng mã số'
                )),
                ('department', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='number_configs',
                    to='accounts.department',
                    verbose_name='Phòng ban'
                )),
                ('category', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    to='document_templates.templatecategory',
                    verbose_name='Danh mục'
                )),
            ],
            options={
                'verbose_name': 'Cấu hình mã số văn bản',
                'verbose_name_plural': 'Cấu hình mã số văn bản',
                'unique_together': {('department', 'prefix', 'year')},
            },
        ),

        # New fields on Document
        migrations.AddField(
            model_name='document',
            name='doc_number',
            field=models.CharField(blank=True, max_length=100, verbose_name='Mã số văn bản'),
        ),
        migrations.AddField(
            model_name='document',
            name='department',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='documents',
                to='accounts.department',
                verbose_name='Phòng ban'
            ),
        ),
        migrations.AddField(
            model_name='document',
            name='category',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='documents',
                to='document_templates.templatecategory',
                verbose_name='Danh mục'
            ),
        ),
        migrations.AddField(
            model_name='document',
            name='status',
            field=models.CharField(
                choices=[('draft', 'Nháp'), ('final', 'Chính thức'), ('archived', 'Lưu trữ')],
                default='draft', max_length=20, verbose_name='Trạng thái'
            ),
        ),
        migrations.AddField(
            model_name='document',
            name='tags',
            field=models.CharField(blank=True, max_length=255, verbose_name='Tags'),
        ),
        migrations.AddField(
            model_name='document',
            name='notes',
            field=models.TextField(blank=True, verbose_name='Ghi chú'),
        ),
        migrations.AddField(
            model_name='document',
            name='is_archived',
            field=models.BooleanField(default=False, verbose_name='Đã lưu trữ'),
        ),
        migrations.AddField(
            model_name='document',
            name='archived_at',
            field=models.DateTimeField(blank=True, null=True, verbose_name='Ngày lưu trữ'),
        ),
    ]
