from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0020_globalaiconfig_image_ocr_model_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='UserAlias',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('alias', models.CharField(max_length=150)),
                ('normalized_alias', models.CharField(editable=False, max_length=150)),
                ('is_primary_hint', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('company', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='user_aliases', to='accounts.company')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='aliases', to='auth.user')),
            ],
            options={
                'ordering': ['-is_primary_hint', 'alias', 'id'],
            },
        ),
        migrations.AddConstraint(
            model_name='useralias',
            constraint=models.UniqueConstraint(fields=('company', 'user', 'normalized_alias'), name='uniq_user_alias_company_user_value'),
        ),
    ]
