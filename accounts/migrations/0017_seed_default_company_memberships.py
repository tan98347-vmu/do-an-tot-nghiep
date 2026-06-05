from django.db import migrations


def seed_default_company_memberships(apps, schema_editor):
    Company = apps.get_model('accounts', 'Company')
    CompanyAIConfig = apps.get_model('accounts', 'CompanyAIConfig')
    CompanyUserMembership = apps.get_model('accounts', 'CompanyUserMembership')
    Department = apps.get_model('accounts', 'Department')
    GlobalAIConfig = apps.get_model('accounts', 'GlobalAIConfig')
    UserGroup = apps.get_model('accounts', 'UserGroup')
    UserProfile = apps.get_model('accounts', 'UserProfile')
    User = apps.get_model('auth', 'User')

    company, _ = Company.objects.get_or_create(
        code='default-company',
        defaults={
            'slug': 'default-company',
            'name': 'Default Company',
            'status': 'active',
        },
    )

    defaults = GlobalAIConfig.objects.filter(pk=1).first()
    if defaults is not None:
        CompanyAIConfig.objects.get_or_create(
            company=company,
            defaults={
                'ai_model': defaults.ai_model,
                'ocr_model': defaults.ocr_model,
                'ai_temperature': defaults.ai_temperature,
                'ai_max_results': defaults.ai_max_results,
                'embedding_model': defaults.embedding_model,
                'company_context': company.company_context or defaults.company_context,
                'ai_internet_results': defaults.ai_internet_results,
                'ai_search_engine': defaults.ai_search_engine,
                'updated_by_id': defaults.updated_by_id,
            },
        )

    Department.objects.filter(company__isnull=True).update(company=company, is_active=True)
    UserGroup.objects.filter(company__isnull=True).update(company=company)

    for user in User.objects.all().iterator():
        profile, _ = UserProfile.objects.get_or_create(user=user)
        if profile.company_id is None:
            profile.company = company
            profile.save(update_fields=['company'])
        CompanyUserMembership.objects.get_or_create(
            user=user,
            defaults={
                'company': company,
                'local_username': (user.username or f'user_{user.pk}')[:150],
                'role': 'company_admin' if (user.is_staff or user.is_superuser) else 'company_user',
                'is_active': user.is_active,
                'must_change_password': False,
            },
        )


class Migration(migrations.Migration):
    dependencies = [
        ('accounts', '0016_company_companyaiconfig_companyimportbatch_and_more'),
    ]

    operations = [
        migrations.RunPython(seed_default_company_memberships, migrations.RunPython.noop),
    ]
