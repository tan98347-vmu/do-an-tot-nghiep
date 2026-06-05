from django.core.management.base import BaseCommand, CommandError

from accounts.company_services import reset_company_bootstrap_admin
from accounts.models import Company


class Command(BaseCommand):
    help = 'Reset or create the bootstrap admin account for a company.'

    def add_arguments(self, parser):
        parser.add_argument('--company-id', type=int)
        parser.add_argument('--company-code')

    def handle(self, *args, **options):
        company_id = options.get('company_id')
        company_code = str(options.get('company_code') or '').strip().lower()
        if bool(company_id) == bool(company_code):
            raise CommandError('Can chi ro dung mot trong hai tham so --company-id hoac --company-code.')

        queryset = Company.objects.all()
        company = queryset.filter(pk=company_id).first() if company_id else queryset.filter(code__iexact=company_code).first()
        if company is None:
            raise CommandError('Khong tim thay cong ty.')

        bootstrap = reset_company_bootstrap_admin(company)
        self.stdout.write(
            self.style.SUCCESS(
                'bootstrap admin ready | company={code} | username={username} | email={email} | password={password}'.format(
                    code=company.code,
                    username=bootstrap.membership.local_username,
                    email=bootstrap.user.email,
                    password=bootstrap.raw_password,
                )
            )
        )
