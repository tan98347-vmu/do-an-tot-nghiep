from django.db import migrations, models


# class Migration là bước migration thay đổi cấu trúc CSDL (theo tên file: alter prompt is shared).
# vd: chạy "python manage.py migrate" để áp dụng thay đổi schema này.
class Migration(migrations.Migration):

    dependencies = [
        ('prompts', '0004_prompt_visibility'),
    ]

    operations = [
        migrations.AlterField(
            model_name='prompt',
            name='is_shared',
            field=models.BooleanField(default=False, verbose_name='Chia sẻ nội bộ'),
        ),
    ]
