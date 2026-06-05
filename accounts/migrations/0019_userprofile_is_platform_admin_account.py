from django.db import migrations, models


def backfill_platform_admin_marker(apps, schema_editor):
    User = apps.get_model('auth', 'User')
    UserProfile = apps.get_model('accounts', 'UserProfile')
    CompanyUserMembership = apps.get_model('accounts', 'CompanyUserMembership')

    membership_user_ids = set(
        CompanyUserMembership.objects.values_list('user_id', flat=True)
    )

    profiles_by_user_id = {
        profile.user_id: profile
        for profile in UserProfile.objects.all()
    }

    users = User.objects.filter(is_superuser=True)
    for user in users.iterator():
        profile = profiles_by_user_id.get(user.pk)
        if profile is None:
            profile = UserProfile.objects.create(user_id=user.pk)
            profiles_by_user_id[user.pk] = profile
        should_be_platform_admin = user.pk not in membership_user_ids
        if profile.is_platform_admin_account != should_be_platform_admin:
            profile.is_platform_admin_account = should_be_platform_admin
            profile.save(update_fields=['is_platform_admin_account'])


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0018_alter_userprofile_avatar'),
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='is_platform_admin_account',
            field=models.BooleanField(default=False),
        ),
        migrations.RunPython(backfill_platform_admin_marker, migrations.RunPython.noop),
    ]
