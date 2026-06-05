import json
import shutil
from pathlib import Path

from django.apps import apps
from django.conf import settings
from django.contrib.auth.models import User
from django.core import serializers
from django.core.management.base import BaseCommand, CommandError
from django.db.models import FileField

from accounts.models import Company, CompanyUserMembership, DepartmentMembership, UserGroupMembership, UserProfile


def _resolve_company(*, company_id=None, company_code=''):
    queryset = Company.objects.all()
    if company_id:
        return queryset.filter(pk=company_id).first()
    return queryset.filter(code__iexact=company_code).first()


def _serialize_queryset(queryset):
    return json.loads(serializers.serialize('json', queryset))


def _collect_file_paths(queryset):
    paths = set()
    model = queryset.model
    file_fields = [field for field in model._meta.fields if isinstance(field, FileField)]
    if not file_fields:
        return paths
    for obj in queryset:
        for field in file_fields:
            file_value = getattr(obj, field.name, None)
            if file_value and getattr(file_value, 'name', ''):
                paths.add(file_value.name)
    return paths


class Command(BaseCommand):
    help = 'Export one company bundle as JSON records plus media subtree.'

    def add_arguments(self, parser):
        parser.add_argument('--company-id', type=int)
        parser.add_argument('--company-code')
        parser.add_argument('--output-dir', default='.codex-runtime/company-exports')

    def handle(self, *args, **options):
        company_id = options.get('company_id')
        company_code = str(options.get('company_code') or '').strip().lower()
        if bool(company_id) == bool(company_code):
            raise CommandError('Can chi ro dung mot trong hai tham so --company-id hoac --company-code.')

        company = _resolve_company(company_id=company_id, company_code=company_code)
        if company is None:
            raise CommandError('Khong tim thay cong ty.')

        base_dir = Path(str(options['output_dir'])).resolve()
        bundle_dir = base_dir / f'company_{company.code}'
        data_dir = bundle_dir / 'data'
        media_dir = bundle_dir / 'media'
        data_dir.mkdir(parents=True, exist_ok=True)
        media_dir.mkdir(parents=True, exist_ok=True)

        payload = {}
        file_paths = set()

        payload['accounts.Company'] = _serialize_queryset(Company.objects.filter(pk=company.pk))
        memberships = CompanyUserMembership.objects.filter(company=company).select_related('user')
        user_ids = list(memberships.values_list('user_id', flat=True))
        payload['accounts.CompanyUserMembership'] = _serialize_queryset(memberships)
        payload['auth.User'] = _serialize_queryset(User.objects.filter(pk__in=user_ids))
        profiles = UserProfile.objects.filter(user_id__in=user_ids)
        payload['accounts.UserProfile'] = _serialize_queryset(profiles)
        payload['accounts.DepartmentMembership'] = _serialize_queryset(DepartmentMembership.objects.filter(user_id__in=user_ids, department__company=company))
        payload['accounts.UserGroupMembership'] = _serialize_queryset(UserGroupMembership.objects.filter(user_id__in=user_ids, group__company=company))
        file_paths |= _collect_file_paths(profiles)

        for model in apps.get_models():
            if model in {Company, CompanyUserMembership, UserProfile, DepartmentMembership, UserGroupMembership, User}:
                continue
            if not any(field.name == 'company' for field in model._meta.fields):
                continue
            try:
                queryset = model._default_manager.filter(company=company)
            except Exception:
                continue
            if not queryset.exists():
                continue
            payload[model._meta.label] = _serialize_queryset(queryset)
            file_paths |= _collect_file_paths(queryset)

        (bundle_dir / 'manifest.json').write_text(
            json.dumps(
                {
                    'company': {
                        'id': company.pk,
                        'code': company.code,
                        'name': company.name,
                        'status': company.status,
                    },
                    'record_groups': {label: len(items) for label, items in payload.items()},
                    'file_count': len(file_paths),
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding='utf-8',
        )
        for label, items in payload.items():
            safe_name = label.replace('.', '__')
            (data_dir / f'{safe_name}.json').write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding='utf-8')

        media_root = Path(getattr(settings, 'MEDIA_ROOT', '') or '')
        copied_files = 0
        if media_root.exists():
            for relative_path in sorted(file_paths):
                source_path = media_root / relative_path
                if not source_path.exists() or not source_path.is_file():
                    continue
                destination = media_dir / relative_path
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source_path, destination)
                copied_files += 1

        self.stdout.write(
            self.style.SUCCESS(
                f'company export ready | company={company.code} | bundle={bundle_dir} | copied_files={copied_files}'
            )
        )
