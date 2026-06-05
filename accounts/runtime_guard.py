from __future__ import annotations

from pathlib import Path

from django.conf import settings
from rest_framework.exceptions import PermissionDenied

from .storage_paths import company_storage_slug
from .tenancy import get_target_company, get_user_company, is_platform_admin, targets_share_company


class CompanyRuntimeGuard:
    @staticmethod
    def company_media_prefix(company) -> str:
        return f'companies/{company_storage_slug(company)}/'

    @staticmethod
    def preview_cache_prefix(*, company, namespace: str) -> str:
        return f'preview_cache/{namespace}/{company_storage_slug(company)}/'

    @staticmethod
    def _normalize_storage_name(name) -> str:
        return str(name or '').replace('\\', '/').lstrip('/')

    @classmethod
    def assert_same_company(cls, *targets, detail='Tai nguyen runtime dang tro sang cong ty khac.'):
        scoped_targets = [target for target in targets if target is not None]
        if scoped_targets and not targets_share_company(*scoped_targets):
            raise PermissionDenied(detail)

    @classmethod
    def assert_user_target_access(
        cls,
        user,
        target,
        *,
        allow_platform_admin: bool = False,
        detail='Ban khong duoc truy cap tai nguyen runtime cua cong ty khac.',
    ):
        target_company = get_target_company(target)
        if target_company is None or user is None:
            return target_company

        user_company = get_user_company(user)
        if user_company is None:
            if allow_platform_admin and is_platform_admin(user):
                return target_company
            raise PermissionDenied(detail)

        if user_company.pk != target_company.pk:
            raise PermissionDenied(detail)
        return target_company

    @classmethod
    def assert_storage_name(
        cls,
        name,
        *,
        company=None,
        target=None,
        detail='File dang tro sang storage cua cong ty khac.',
    ) -> str:
        normalized = cls._normalize_storage_name(name)
        if not normalized:
            return normalized
        if not normalized.startswith('companies/'):
            return normalized

        target_company = company or get_target_company(target)
        if target_company is None:
            return normalized

        if not normalized.startswith(cls.company_media_prefix(target_company)):
            raise PermissionDenied(detail)
        return normalized

    @classmethod
    def assert_file_field(
        cls,
        file_field,
        *,
        company=None,
        target=None,
        detail='File dang tro sang storage cua cong ty khac.',
    ) -> str:
        if not file_field:
            return ''
        return cls.assert_storage_name(
            getattr(file_field, 'name', ''),
            company=company,
            target=target,
            detail=detail,
        )

    @classmethod
    def assert_preview_path(
        cls,
        preview_path,
        *,
        company=None,
        target=None,
        namespace='documents',
        detail='Ban xem truoc dang tro sang cache cua cong ty khac.',
    ):
        if preview_path is None:
            return preview_path

        target_company = company or get_target_company(target)
        if target_company is None:
            return preview_path

        try:
            media_root = Path(settings.MEDIA_ROOT).resolve(strict=False)
            resolved_path = Path(preview_path).resolve(strict=False)
        except (TypeError, ValueError, OSError):
            return preview_path

        try:
            relative_path = resolved_path.relative_to(media_root)
        except ValueError:
            return preview_path

        normalized = relative_path.as_posix().lstrip('/')
        if not normalized.startswith('preview_cache/'):
            return preview_path

        expected_prefix = cls.preview_cache_prefix(company=target_company, namespace=namespace)
        if not normalized.startswith(expected_prefix):
            raise PermissionDenied(detail)
        return preview_path
