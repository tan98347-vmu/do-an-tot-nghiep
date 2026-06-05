from __future__ import annotations

import logging
import shutil
from dataclasses import dataclass
from pathlib import Path

from django.conf import settings
from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import Q

from ai_engine.rag_index import _delete_collection_embeddings
from .models import Company, CompanyRole, CompanyStatus, CompanyUserMembership
from .storage_paths import company_storage_slug
from .tenancy import is_platform_admin


LOGGER = logging.getLogger(__name__)


class CompanyHardDeleteError(ValueError):
    pass


@dataclass(frozen=True)
class CompanyTrashSummary:
    company: Company
    bootstrap_admin_username: str
    bootstrap_admin_email: str


@dataclass(frozen=True)
class CompanyHardDeleteResult:
    company_id: int
    company_code: str
    company_name: str
    deleted_user_count: int
    deleted_membership_count: int


def get_company_bootstrap_admin_membership(company: Company) -> CompanyUserMembership | None:
    memberships = company.memberships.select_related('user').filter(
        role=CompanyRole.COMPANY_ADMIN,
        is_active=True,
    )
    membership = memberships.filter(local_username__iexact='admin').order_by('pk').first()
    if membership is not None:
        return membership
    return memberships.order_by('pk').first()


def list_deleted_companies(*, query: str = '') -> list[CompanyTrashSummary]:
    companies = Company.objects.filter(status=CompanyStatus.DELETED).order_by('name', 'code')
    if query:
        companies = companies.filter(Q(name__icontains=query) | Q(code__icontains=query))
    items: list[CompanyTrashSummary] = []
    for company in companies:
        bootstrap = get_company_bootstrap_admin_membership(company)
        items.append(
            CompanyTrashSummary(
                company=company,
                bootstrap_admin_username=bootstrap.local_username if bootstrap else '',
                bootstrap_admin_email=bootstrap.user.email if bootstrap else '',
            )
        )
    return items


def soft_delete_company(company: Company, *, actor: User | None = None) -> Company:
    if company.status == CompanyStatus.DELETED:
        return company
    company.status = CompanyStatus.DELETED
    company.updated_by = actor
    company.save(update_fields=['status', 'updated_by', 'updated_at'])
    return company


def restore_company_from_trash(
    company: Company,
    *,
    actor: User | None = None,
    target_status: str = CompanyStatus.ACTIVE,
) -> Company:
    if company.status != CompanyStatus.DELETED:
        raise CompanyHardDeleteError('Chi cong ty trong thung rac moi co the khoi phuc.')
    company.status = target_status
    company.updated_by = actor
    company.save(update_fields=['status', 'updated_by', 'updated_at'])
    return company


def _company_media_cleanup_paths(company: Company) -> list[Path]:
    slug = company_storage_slug(company)
    media_root = Path(settings.MEDIA_ROOT)
    return [
        media_root / 'companies' / slug,
        media_root / 'preview_cache' / 'documents' / slug,
        media_root / 'preview_cache' / 'templates' / slug,
    ]


def _purge_path(path: Path) -> None:
    if not path.exists():
        return
    if path.is_file():
        path.unlink()
        return
    shutil.rmtree(path)


def _purge_company_media(paths: list[Path]) -> None:
    for path in paths:
        try:
            _purge_path(path)
        except OSError as exc:
            LOGGER.warning('company hard delete media cleanup skipped | path=%s | error=%s', path, exc)


def _company_rag_collection_names(*, company_id: int, user_ids: list[int]) -> list[str]:
    names = [
        f'company_{company_id}_template_rag_kb',
        f'company_{company_id}_document_rag_kb',
        f'company_{company_id}_shared_kb',
    ]
    names.extend(f'company_{company_id}_user_{user_id}_kb' for user_id in user_ids)
    return names


def _purge_company_rag_indexes(*, company_id: int, user_ids: list[int]) -> None:
    for collection_name in _company_rag_collection_names(company_id=company_id, user_ids=user_ids):
        try:
            _delete_collection_embeddings(collection_name)
        except Exception as exc:  # pragma: no cover - defensive cleanup only
            LOGGER.warning(
                'company hard delete rag cleanup skipped | company_id=%s | collection=%s | error=%s',
                company_id,
                collection_name,
                exc,
            )


def hard_delete_company(
    company: Company,
    *,
    platform_admin_user: User,
    platform_admin_password: str,
    company_admin_password: str = '',
) -> CompanyHardDeleteResult:
    # Chi can xac thuc mat khau cua admin quan tri nen tang. Khong con yeu cau
    # mat khau cua admin cong ty (tham so company_admin_password giu lai cho
    # tuong thich nguoc nhung khong duoc su dung).
    if company.status != CompanyStatus.DELETED:
        raise CompanyHardDeleteError('Chi cong ty da xoa mem moi duoc xoa cung.')
    if not is_platform_admin(platform_admin_user):
        raise CompanyHardDeleteError('Chi platform admin moi duoc xoa cung cong ty.')
    if not platform_admin_user.check_password(platform_admin_password or ''):
        raise CompanyHardDeleteError('Mat khau admin quan tri nen tang khong dung.')

    user_ids = list(
        CompanyUserMembership.objects.filter(company=company).values_list('user_id', flat=True)
    )
    deleted_membership_count = len(user_ids)
    media_paths = _company_media_cleanup_paths(company)
    company_id = company.pk
    company_code = company.code
    company_name = company.name

    with transaction.atomic():
        User.objects.filter(pk__in=user_ids).delete()
        company.delete()
        transaction.on_commit(lambda: _purge_company_media(media_paths))
        transaction.on_commit(
            lambda: _purge_company_rag_indexes(company_id=company_id, user_ids=user_ids)
        )

    return CompanyHardDeleteResult(
        company_id=company_id,
        company_code=company_code,
        company_name=company_name,
        deleted_user_count=len(user_ids),
        deleted_membership_count=deleted_membership_count,
    )
