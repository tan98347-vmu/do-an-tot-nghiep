from django.db import migrations, models


# class Migration là bước migration thay đổi cấu trúc CSDL (theo tên file: rename content split).
# vd: chạy "python manage.py migrate" để áp dụng thay đổi schema này.
class Migration(migrations.Migration):

    dependencies = [
        ('prompts', '0002_promptcategory_prompt_category_prompt_tags'),
    ]

    operations = [
        migrations.RenameField(
            model_name='prompt',
            old_name='content',
            new_name='system_content',
        ),
        migrations.AlterField(
            model_name='prompt',
            name='system_content',
            field=models.TextField(
                blank=True,
                verbose_name='Hệ tư tưởng (System Ideology)',
                help_text='Thay thế toàn bộ danh tính gốc của AI.',
            ),
        ),
        migrations.AddField(
            model_name='prompt',
            name='rules_content',
            field=models.TextField(
                blank=True,
                verbose_name='Suy luận (In-Context Rules)',
                help_text='Ghi đè phần QUY TẮC trong tạo văn bản.',
            ),
        ),
    ]
