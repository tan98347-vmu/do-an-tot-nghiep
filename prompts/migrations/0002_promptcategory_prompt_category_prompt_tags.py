from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('prompts', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='PromptCategory',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, unique=True, verbose_name='Tên danh mục')),
                ('description', models.TextField(blank=True, verbose_name='Mô tả')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'verbose_name': 'Danh mục prompt',
                'verbose_name_plural': 'Danh mục prompt',
                'ordering': ['name'],
            },
        ),
        migrations.AddField(
            model_name='prompt',
            name='tags',
            field=models.CharField(blank=True, max_length=255, verbose_name='Tags'),
        ),
        migrations.AddField(
            model_name='prompt',
            name='category',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='prompts',
                to='prompts.promptcategory',
                verbose_name='Danh mục'
            ),
        ),
    ]
