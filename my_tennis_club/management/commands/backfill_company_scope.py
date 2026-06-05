from django.apps import apps
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from accounts.models import (
    Company,
    CompanyAIConfig,
    CompanyRole,
    CompanyStatus,
    CompanyUserMembership,
    Department,
    UserGroup,
    UserProfile,
)


def _model_has_company_field(model):
    try:
        return any(field.name == 'company' for field in model._meta.fields)
    except Exception:
        return False


class Command(BaseCommand):
    help = 'Backfill legacy records into the default company scope.'

    def add_arguments(self, parser):
        parser.add_argument('--include-superusers', action='store_true', default=True)

    def handle(self, *args, **options):
        default_company = Company.get_default()
        if default_company.status != CompanyStatus.ACTIVE:
            default_company.status = CompanyStatus.ACTIVE
            default_company.save(update_fields=['status'])
        CompanyAIConfig.seed_defaults(default_company)

        membership_count = 0
        for user in User.objects.select_related('profile').all().order_by('pk'):
            membership = getattr(user, 'company_membership', None)
            if membership is not None:
                if not membership.company_id:
                    membership.company = default_company
                    membership.save(update_fields=['company'])
                continue
            local_username = (user.email.split('@', 1)[0] if user.email and '@' in user.email else user.username).strip().lower() or f'user_{user.pk}'
            seed = local_username
            counter = 1
            while CompanyUserMembership.objects.filter(company=default_company, local_username__iexact=local_username).exists():
                local_username = f'{seed}_{counter}'
                counter += 1
            CompanyUserMembership.objects.create(
                company=default_company,
                user=user,
                local_username=local_username,
                role=CompanyRole.COMPANY_ADMIN if user.is_staff else CompanyRole.COMPANY_USER,
                is_active=user.is_active,
                must_change_password=False,
            )
            membership_count += 1

        UserProfile.objects.filter(company__isnull=True).update(company=default_company)
        Department.objects.filter(company__isnull=True).update(company=default_company)
        UserGroup.objects.filter(company__isnull=True).update(company=default_company)

        generic_updates = {}
        for model in apps.get_models():
            if model in {Company, CompanyAIConfig, CompanyUserMembership, Department, UserGroup, UserProfile}:
                continue
            if not _model_has_company_field(model):
                continue
            try:
                updated = model._default_manager.filter(company__isnull=True).update(company=default_company)
            except Exception:
                continue
            if updated:
                generic_updates[model._meta.label] = updated

        self.stdout.write(
            self.style.SUCCESS(
                f'backfill done | default_company={default_company.code} | seeded_memberships={membership_count} | updated_models={len(generic_updates)}'
            )
        )
        for label, count in sorted(generic_updates.items()):
            self.stdout.write(f' - {label}: {count}')
