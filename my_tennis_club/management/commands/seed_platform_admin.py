import secrets

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Create or update a platform admin account used for company-level administration.'

    def add_arguments(self, parser):
        parser.add_argument('--username', default='platform_admin')
        parser.add_argument('--email', default='platform-admin@example.com')
        parser.add_argument('--password')

    def handle(self, *args, **options):
        username = str(options['username']).strip()
        email = str(options['email']).strip()
        raw_password = str(options.get('password') or '').strip() or secrets.token_urlsafe(12)

        user, created = User.objects.get_or_create(
            username=username,
            defaults={'email': email},
        )
        user.email = email or user.email
        user.is_active = True
        user.is_staff = True
        user.is_superuser = True
        user.set_password(raw_password)
        user.save()
        profile = user.profile
        profile.is_platform_admin_account = True
        profile.save(update_fields=['is_platform_admin_account'])

        status_label = 'created' if created else 'updated'
        self.stdout.write(
            self.style.SUCCESS(
                f'platform admin {status_label} | username={user.username} | email={user.email} | password={raw_password}'
            )
        )
