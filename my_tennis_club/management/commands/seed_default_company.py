from django.core.management.base import BaseCommand

from accounts.models import CompanyAIConfig, CompanyStatus, Company


class Command(BaseCommand):
    help = 'Seed the default company used to hold legacy single-company data.'

    def handle(self, *args, **options):
        company = Company.get_default()
        if company.status != CompanyStatus.ACTIVE:
            company.status = CompanyStatus.ACTIVE
            company.save(update_fields=['status'])
        CompanyAIConfig.seed_defaults(company)
        self.stdout.write(
            self.style.SUCCESS(
                f'default company ready | id={company.pk} | code={company.code} | slug={company.slug}'
            )
        )
