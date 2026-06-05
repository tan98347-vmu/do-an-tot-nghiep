from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from django.contrib.auth.models import User
from django.db.utils import DatabaseError, OperationalError, ProgrammingError

from .models import (
    Company,
    CompanyAIConfig,
    CompanyRole,
    CompanyStatus,
    CompanyUserMembership,
    DepartmentMembership,
    GlobalAIConfig,
)


@dataclass(frozen=True)
class CompanyLoginMatch:
    user: User
    membership: CompanyUserMembership


def _legacy_platform_admin_fallback(user: User) -> bool:
    if not getattr(user, 'is_superuser', False):
        return False
    try:
        return not CompanyUserMembership.objects.filter(user=user).exists()
    except (ProgrammingError, OperationalError, DatabaseError):
        return bool(user.is_superuser)


def is_platform_admin(user: Optional[User]) -> bool:
    if not user or not user.is_authenticated:
        return False
    try:
        profile = getattr(user, 'profile', None)
    except (ProgrammingError, OperationalError, DatabaseError):
        return _legacy_platform_admin_fallback(user)
    if profile is None:
        return _legacy_platform_admin_fallback(user)
    marker = getattr(profile, 'is_platform_admin_account', None)
    if marker is None:
        return _legacy_platform_admin_fallback(user)
    return bool(marker)


def get_user_membership(user: Optional[User]) -> Optional[CompanyUserMembership]:
    if not user or not getattr(user, 'is_authenticated', False):
        return None
    membership = getattr(user, 'company_membership', None)
    if membership is None:
        return None
    if not membership.is_active:
        return None
    if membership.company.status != CompanyStatus.ACTIVE:
        return None
    return membership


def get_user_company(user: Optional[User]) -> Optional[Company]:
    membership = get_user_membership(user)
    return membership.company if membership else None


def get_target_company(target, _seen=None) -> Optional[Company]:
    if target is None:
        return None
    if _seen is None:
        _seen = set()
    target_key = (type(target), getattr(target, 'pk', None), id(target))
    if target_key in _seen:
        return None
    _seen.add(target_key)
    if isinstance(target, Company):
        return target
    if isinstance(target, User):
        return get_user_company(target)

    direct_company = getattr(target, 'company', None)
    if direct_company is not None:
        return direct_company

    for attr_name in ('document', 'source_document', 'thread', 'packet', 'proposal'):
        related = getattr(target, attr_name, None)
        if related is None:
            continue
        company = get_target_company(related, _seen=_seen)
        if company is not None:
            return company
    return None


def targets_share_company(*targets) -> bool:
    company_ids = []
    saw_missing_company = False

    for target in targets:
        if target is None:
            continue
        company = get_target_company(target)
        if company is None:
            saw_missing_company = True
            continue
        company_ids.append(company.pk)

    if not company_ids:
        return True
    if saw_missing_company:
        return False
    return len(set(company_ids)) == 1


def filter_queryset_by_current_company(queryset, user: Optional[User], *, company_field: str = 'company'):
    company = get_user_company(user)
    if company is None:
        return queryset
    return queryset.filter(**{company_field: company})


def is_company_admin(user: Optional[User]) -> bool:
    membership = get_user_membership(user)
    return bool(membership and membership.role == CompanyRole.COMPANY_ADMIN)


def is_tenant_admin(user: Optional[User]) -> bool:
    return is_platform_admin(user) or is_company_admin(user)


def resolve_company(company_id) -> Optional[Company]:
    if not company_id:
        return None
    try:
        return Company.objects.filter(pk=company_id).first()
    except (TypeError, ValueError):
        return None


def resolve_company_login(identifier: str, password: str, company: Company) -> Optional[CompanyLoginMatch]:
    if not identifier or not password:
        return None
    memberships = CompanyUserMembership.objects.select_related('user', 'company').filter(
        company=company,
        is_active=True,
    )

    direct = memberships.filter(local_username__iexact=identifier).first()
    if direct and direct.user.check_password(password) and direct.user.is_active:
        return CompanyLoginMatch(user=direct.user, membership=direct)

    username_matches = memberships.filter(user__username__iexact=identifier)
    if username_matches.count() == 1:
        membership = username_matches.first()
        if membership and membership.user.check_password(password) and membership.user.is_active:
            return CompanyLoginMatch(user=membership.user, membership=membership)

    email_matches = memberships.filter(user__email__iexact=identifier)
    if email_matches.count() == 1:
        membership = email_matches.first()
        if membership and membership.user.check_password(password) and membership.user.is_active:
            return CompanyLoginMatch(user=membership.user, membership=membership)

    employee_matches = memberships.filter(user__profile__ma_nhan_vien__iexact=identifier).distinct()
    if employee_matches.count() == 1:
        membership = employee_matches.first()
        if membership and membership.user.check_password(password) and membership.user.is_active:
            return CompanyLoginMatch(user=membership.user, membership=membership)
    return None


def resolve_ai_config(*, user: Optional[User] = None, company: Optional[Company] = None):
    company = company or get_user_company(user)
    if not company:
        return GlobalAIConfig.get_config()
    return CompanyAIConfig.seed_defaults(company)


def resolve_chat_ai_model(*, user: Optional[User] = None, company: Optional[Company] = None) -> str:
    """Model rieng cho Tro ly Chat AI. Fall back ve ai_model neu de trong."""
    cfg = resolve_ai_config(user=user, company=company)
    return (getattr(cfg, 'chat_ai_model', '') or getattr(cfg, 'ai_model', '') or 'kimi-k2.6:cloud').strip()


def build_effective_company_context(*, user: Optional[User] = None, company: Optional[Company] = None) -> str:
    config = resolve_ai_config(user=user, company=company)
    return config.company_context or ''


def build_employee_profile_context(user: Optional[User]) -> str:
    if not user or not getattr(user, 'is_authenticated', False):
        return ''
    profile = getattr(user, 'profile', None)
    if profile is None:
        return ''

    membership = get_user_membership(user)
    department_membership = (
        DepartmentMembership.objects.select_related('department')
        .filter(user=user, is_active=True, department__is_active=True)
        .order_by('department__name', 'pk')
        .first()
    )

    lines = []
    full_name = (user.get_full_name() or '').strip()
    if full_name:
        lines.append(f'Ho va ten: {full_name}')
    lines.append(f'Ten dang nhap: {membership.local_username if membership else user.username}')
    if user.email:
        lines.append(f'Email: {user.email}')
    if getattr(profile, 'age_years', None) is not None:
        lines.append(f'Tuoi: {profile.age_years}')
    if getattr(profile, 'chuc_danh', ''):
        lines.append(f'Chuc danh: {profile.chuc_danh}')
    if getattr(profile, 'ma_nhan_vien', ''):
        lines.append(f'Ma nhan vien: {profile.ma_nhan_vien}')
    department = department_membership.department if department_membership else None
    if department is not None and getattr(department, 'name', ''):
        lines.append(f'Phong ban: {department.name}')
    if getattr(profile, 'so_yeu_ly_lich', ''):
        lines.append(f'Ho so nhan su: {profile.so_yeu_ly_lich.strip()}')
    return '\n'.join(line for line in lines if line).strip()


def build_effective_ai_context(
    *,
    user: Optional[User] = None,
    company: Optional[Company] = None,
    include_profile: bool = True,
    include_company: bool = True,
) -> str:
    """Ghep ngu canh AI tu hai nguon: cong ty + ho so nhan vien.

    Co the tat tung nguon doc lap qua flag `include_company`, `include_profile`.
    Khi user tat ca hai flag o frontend (toggle prefill VoiceAI/ChatAI) thi
    ham nay tra ve chuoi rong, downstream prefill se khong goi LLM.
    """
    parts = []
    if include_company:
        company_context = build_effective_company_context(user=user, company=company).strip()
        if company_context:
            parts.append(f'NGU CANH CONG TY:\n{company_context}')
    if include_profile:
        employee_context = build_employee_profile_context(user).strip()
        if employee_context:
            parts.append(f'HO SO NHAN VIEN:\n{employee_context}')
    return '\n\n'.join(parts).strip()
