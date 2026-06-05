from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0005_userprofile_chuc_danh'),
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='cccd',
            field=models.CharField(blank=True, max_length=20, verbose_name='Số CCCD'),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='ngay_sinh',
            field=models.DateField(blank=True, null=True, verbose_name='Ngày sinh'),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='ma_nhan_vien',
            field=models.CharField(blank=True, max_length=50, verbose_name='Mã nhân viên'),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='so_yeu_ly_lich',
            field=models.TextField(blank=True, verbose_name='Sơ yếu lý lịch'),
        ),
    ]
