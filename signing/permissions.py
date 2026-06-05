"""
Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
Vai tro backend: File `signing/permissions.py` giu hoac ho tro luong backend cho de xuat ky, packet ky, nhiem vu ky, xac minh PDF, PKI noi bo va quyen uy quyen.
Vai tro cua no trong frontend: Cac man `/signing/tasks`, `/signed-pdfs`, `/signing/access` va mot phan thao tac o `/mailbox` phu thuoc truc tiep hoac gian tiep vao file nay.
Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/signing.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`.
Tac dung: Giu cho quy trinh ky nhieu buoc, trang thai chu ky va kiem tra toan ven PDF nhat quan giua nguoi de xuat, nguoi ky va man tra cuu.
"""

import unicodedata

from django.contrib.auth.models import User
from django.db import models

from accounts.models import Department, DepartmentMembership, UserGroup, UserGroupMembership
from accounts.tenancy import filter_queryset_by_current_company, get_user_company
from documents.models import DocumentMailboxEntry, MAILBOX_STATUS_VIEW
from .models import (
    DELEGATION_APPROVE_PROPOSAL,
    DELEGATION_VIEW_SIGNED_PDF,
    PROPOSAL_PENDING_HR_REVIEW,
    DepartmentDelegation,
    SignedPdfDocument,
    SigningProposal,
    SigningSystemConfig,
    SigningTask,
)

def _normalize_key(value):
    """
    Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
    Vai tro backend: Ham `_normalize_key` chiu trach nhiem chuan hoa du lieu dau vao hoac du lieu trung gian trong file `signing/permissions.py`.
    Vai tro cua no trong frontend: Frontend dung ket qua cua ham nay theo cach gian tiep vi danh sach, nut thao tac va badge chi hien khi buoc chuan hoa du lieu dau vao hoac du lieu trung gian da duoc backend chot.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/signing.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`. Thuong duoc cac ham public nhu `get_signing_system_config`, `get_hr_department`, `get_accounting_department` goi lai.
    Tac dung: Tap trung rule chuan hoa du lieu dau vao hoac du lieu trung gian vao mot noi de moi API va service dung chung cung chuan.
    """
    normalized = unicodedata.normalize('NFKD', (value or '').strip().lower())
    normalized = ''.join(ch for ch in normalized if not unicodedata.combining(ch))
    normalized = normalized.replace('đ', 'd')
    return ' '.join(normalized.split())

    normalized = (value or '').strip().lower()
    replacements = {
        'á': 'a', 'à': 'a', 'ả': 'a', 'ã': 'a', 'ạ': 'a',
        'ă': 'a', 'ắ': 'a', 'ằ': 'a', 'ẳ': 'a', 'ẵ': 'a', 'ặ': 'a',
        'â': 'a', 'ấ': 'a', 'ầ': 'a', 'ẩ': 'a', 'ẫ': 'a', 'ậ': 'a',
        'é': 'e', 'è': 'e', 'ẻ': 'e', 'ẽ': 'e', 'ẹ': 'e',
        'ê': 'e', 'ế': 'e', 'ề': 'e', 'ể': 'e', 'ễ': 'e', 'ệ': 'e',
        'í': 'i', 'ì': 'i', 'ỉ': 'i', 'ĩ': 'i', 'ị': 'i',
        'ó': 'o', 'ò': 'o', 'ỏ': 'o', 'õ': 'o', 'ọ': 'o',
        'ô': 'o', 'ố': 'o', 'ồ': 'o', 'ổ': 'o', 'ỗ': 'o', 'ộ': 'o',
        'ơ': 'o', 'ớ': 'o', 'ờ': 'o', 'ở': 'o', 'ỡ': 'o', 'ợ': 'o',
        'ú': 'u', 'ù': 'u', 'ủ': 'u', 'ũ': 'u', 'ụ': 'u',
        'ư': 'u', 'ứ': 'u', 'ừ': 'u', 'ử': 'u', 'ữ': 'u', 'ự': 'u',
        'ý': 'y', 'ỳ': 'y', 'ỷ': 'y', 'ỹ': 'y', 'ỵ': 'y',
        'đ': 'd',
    }
    for src, dst in replacements.items():
        normalized = normalized.replace(src, dst)
    return normalized

def _or_queries(*parts):
    """
    Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
    Vai tro backend: Ham `_or_queries` chiu trach nhiem thuc hien phan xu ly chuyen trach cua symbol hien tai trong file `signing/permissions.py`.
    Vai tro cua no trong frontend: Frontend dung ket qua cua ham nay theo cach gian tiep vi danh sach, nut thao tac va badge chi hien khi buoc thuc hien phan xu ly chuyen trach cua symbol hien tai da duoc backend chot.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/signing.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`. Thuong duoc cac ham public nhu `get_signing_system_config`, `get_hr_department`, `get_accounting_department` goi lai.
    Tac dung: Tap trung rule thuc hien phan xu ly chuyen trach cua symbol hien tai vao mot noi de moi API va service dung chung cung chuan.
    """
    query = None
    for part in parts:
        if part is None:
            continue
        query = part if query is None else (query | part)
    return query

def _resolve_department_by_keywords(*keywords, company=None):
    """
    Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
    Vai tro backend: Ham `_resolve_department_by_keywords` chiu trach nhiem thuc hien phan xu ly chuyen trach cua symbol hien tai trong file `signing/permissions.py`.
    Vai tro cua no trong frontend: Frontend dung ket qua cua ham nay theo cach gian tiep vi danh sach, nut thao tac va badge chi hien khi buoc thuc hien phan xu ly chuyen trach cua symbol hien tai da duoc backend chot.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/signing.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`. Thuong duoc cac ham public nhu `get_signing_system_config`, `get_hr_department`, `get_accounting_department` goi lai.
    Tac dung: Tap trung rule thuc hien phan xu ly chuyen trach cua symbol hien tai vao mot noi de moi API va service dung chung cung chuan.
    """
    departments = Department.objects.select_related('manager').all()
    if company is not None:
        departments = departments.filter(company=company)
    normalized_keywords = [_normalize_key(keyword) for keyword in keywords if keyword]
    for department in departments:
        haystack = ' '.join([
            _normalize_key(department.name),
            _normalize_key(department.code),
            _normalize_key(department.description),
        ])
        if any(keyword in haystack for keyword in normalized_keywords):
            return department
    return None

def _resolve_group_by_keywords(*keywords, company=None):
    """
    Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
    Vai tro backend: Ham `_resolve_group_by_keywords` chiu trach nhiem thuc hien phan xu ly chuyen trach cua symbol hien tai trong file `signing/permissions.py`.
    Vai tro cua no trong frontend: Frontend dung ket qua cua ham nay theo cach gian tiep vi danh sach, nut thao tac va badge chi hien khi buoc thuc hien phan xu ly chuyen trach cua symbol hien tai da duoc backend chot.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/signing.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`. Thuong duoc cac ham public nhu `get_signing_system_config`, `get_hr_department`, `get_accounting_department` goi lai.
    Tac dung: Tap trung rule thuc hien phan xu ly chuyen trach cua symbol hien tai vao mot noi de moi API va service dung chung cung chuan.
    """
    groups = UserGroup.objects.all()
    if company is not None:
        groups = groups.filter(company=company)
    normalized_keywords = [_normalize_key(keyword) for keyword in keywords if keyword]
    for group in groups:
        haystack = ' '.join([
            _normalize_key(group.name),
            _normalize_key(group.description),
        ])
        if any(keyword in haystack for keyword in normalized_keywords):
            return group
    return None

def get_signing_system_config(user=None, company=None):
    """
    Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
    Vai tro backend: Ham `get_signing_system_config` chiu trach nhiem thuc hien phan xu ly chuyen trach cua symbol hien tai trong file `signing/permissions.py`.
    Vai tro cua no trong frontend: Frontend dung ket qua cua ham nay theo cach gian tiep vi danh sach, nut thao tac va badge chi hien khi buoc thuc hien phan xu ly chuyen trach cua symbol hien tai da duoc backend chot.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/signing.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`. Dung cung cap voi cac ham `_normalize_key`, `_or_queries`, `_resolve_department_by_keywords` trong module nay.
    Tac dung: Tap trung rule thuc hien phan xu ly chuyen trach cua symbol hien tai vao mot noi de moi API va service dung chung cung chuan.
    """
    company = company or get_user_company(user)
    return SigningSystemConfig.get_config(company=company)

def get_hr_department(user=None, company=None):
    """
    Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
    Vai tro backend: Ham `get_hr_department` chiu trach nhiem thuc hien phan xu ly chuyen trach cua symbol hien tai trong file `signing/permissions.py`.
    Vai tro cua no trong frontend: Frontend dung ket qua cua ham nay theo cach gian tiep vi danh sach, nut thao tac va badge chi hien khi buoc thuc hien phan xu ly chuyen trach cua symbol hien tai da duoc backend chot.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/signing.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`. Dung cung cap voi cac ham `_normalize_key`, `_or_queries`, `_resolve_department_by_keywords` trong module nay.
    Tac dung: Tap trung rule thuc hien phan xu ly chuyen trach cua symbol hien tai vao mot noi de moi API va service dung chung cung chuan.
    """
    company = company or get_user_company(user)
    config = get_signing_system_config(user=user, company=company)
    if getattr(config, 'hr_department_id', None):
        return config.hr_department
    return _resolve_department_by_keywords('nhan su', 'human resources', 'human resource', 'hr', company=company)

def get_accounting_department(user=None, company=None):
    """
    Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
    Vai tro backend: Ham `get_accounting_department` chiu trach nhiem thuc hien phan xu ly chuyen trach cua symbol hien tai trong file `signing/permissions.py`.
    Vai tro cua no trong frontend: Frontend dung ket qua cua ham nay theo cach gian tiep vi danh sach, nut thao tac va badge chi hien khi buoc thuc hien phan xu ly chuyen trach cua symbol hien tai da duoc backend chot.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/signing.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`. Dung cung cap voi cac ham `_normalize_key`, `_or_queries`, `_resolve_department_by_keywords` trong module nay.
    Tac dung: Tap trung rule thuc hien phan xu ly chuyen trach cua symbol hien tai vao mot noi de moi API va service dung chung cung chuan.
    """
    company = company or get_user_company(user)
    config = get_signing_system_config(user=user, company=company)
    if getattr(config, 'accounting_department_id', None):
        return config.accounting_department
    return _resolve_department_by_keywords('ke toan', 'accounting', 'finance', 'tai chinh', 'kt', company=company)

def get_hr_group(user=None, company=None):
    """
    Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
    Vai tro backend: Ham `get_hr_group` chiu trach nhiem thuc hien phan xu ly chuyen trach cua symbol hien tai trong file `signing/permissions.py`.
    Vai tro cua no trong frontend: Frontend dung ket qua cua ham nay theo cach gian tiep vi danh sach, nut thao tac va badge chi hien khi buoc thuc hien phan xu ly chuyen trach cua symbol hien tai da duoc backend chot.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/signing.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`. Dung cung cap voi cac ham `_normalize_key`, `_or_queries`, `_resolve_department_by_keywords` trong module nay.
    Tac dung: Tap trung rule thuc hien phan xu ly chuyen trach cua symbol hien tai vao mot noi de moi API va service dung chung cung chuan.
    """
    company = company or get_user_company(user)
    return _resolve_group_by_keywords('nhan su', 'human resources', 'human resource', 'hr', company=company)

def get_accounting_group(user=None, company=None):
    """
    Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
    Vai tro backend: Ham `get_accounting_group` chiu trach nhiem thuc hien phan xu ly chuyen trach cua symbol hien tai trong file `signing/permissions.py`.
    Vai tro cua no trong frontend: Frontend dung ket qua cua ham nay theo cach gian tiep vi danh sach, nut thao tac va badge chi hien khi buoc thuc hien phan xu ly chuyen trach cua symbol hien tai da duoc backend chot.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/signing.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`. Dung cung cap voi cac ham `_normalize_key`, `_or_queries`, `_resolve_department_by_keywords` trong module nay.
    Tac dung: Tap trung rule thuc hien phan xu ly chuyen trach cua symbol hien tai vao mot noi de moi API va service dung chung cung chuan.
    """
    company = company or get_user_company(user)
    return _resolve_group_by_keywords('ke toan', 'accounting', 'finance', 'tai chinh', 'kt', company=company)

def is_department_manager(user, department):
    """
    Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
    Vai tro backend: Ham `is_department_manager` chiu trach nhiem thuc hien phan xu ly chuyen trach cua symbol hien tai trong file `signing/permissions.py`.
    Vai tro cua no trong frontend: Frontend dung ket qua cua ham nay theo cach gian tiep vi danh sach, nut thao tac va badge chi hien khi buoc thuc hien phan xu ly chuyen trach cua symbol hien tai da duoc backend chot.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/signing.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`. Dung cung cap voi cac ham `_normalize_key`, `_or_queries`, `_resolve_department_by_keywords` trong module nay.
    Tac dung: Tap trung rule thuc hien phan xu ly chuyen trach cua symbol hien tai vao mot noi de moi API va service dung chung cung chuan.
    """
    if not user or not user.is_authenticated or department is None:
        return False
    return department.manager_id == user.id

def is_group_leader(user, group):
    """
    Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
    Vai tro backend: Ham `is_group_leader` chiu trach nhiem thuc hien phan xu ly chuyen trach cua symbol hien tai trong file `signing/permissions.py`.
    Vai tro cua no trong frontend: Frontend dung ket qua cua ham nay theo cach gian tiep vi danh sach, nut thao tac va badge chi hien khi buoc thuc hien phan xu ly chuyen trach cua symbol hien tai da duoc backend chot.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/signing.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`. Dung cung cap voi cac ham `_normalize_key`, `_or_queries`, `_resolve_department_by_keywords` trong module nay.
    Tac dung: Tap trung rule thuc hien phan xu ly chuyen trach cua symbol hien tai vao mot noi de moi API va service dung chung cung chuan.
    """
    if not user or not user.is_authenticated or group is None:
        return False
    return UserGroupMembership.objects.filter(
        user=user,
        group=group,
        role=UserGroupMembership.ROLE_LEADER,
    ).exists()

def is_department_member(user, department):
    """
    Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
    Vai tro backend: Ham `is_department_member` chiu trach nhiem thuc hien phan xu ly chuyen trach cua symbol hien tai trong file `signing/permissions.py`.
    Vai tro cua no trong frontend: Frontend dung ket qua cua ham nay theo cach gian tiep vi danh sach, nut thao tac va badge chi hien khi buoc thuc hien phan xu ly chuyen trach cua symbol hien tai da duoc backend chot.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/signing.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`. Dung cung cap voi cac ham `_normalize_key`, `_or_queries`, `_resolve_department_by_keywords` trong module nay.
    Tac dung: Tap trung rule thuc hien phan xu ly chuyen trach cua symbol hien tai vao mot noi de moi API va service dung chung cung chuan.
    """
    if not user or not user.is_authenticated or department is None:
        return False
    if is_department_manager(user, department):
        return True
    return DepartmentMembership.objects.filter(
        department=department,
        user=user,
        is_active=True,
    ).exists()

def is_group_member(user, group):
    """
    Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
    Vai tro backend: Ham `is_group_member` chiu trach nhiem thuc hien phan xu ly chuyen trach cua symbol hien tai trong file `signing/permissions.py`.
    Vai tro cua no trong frontend: Frontend dung ket qua cua ham nay theo cach gian tiep vi danh sach, nut thao tac va badge chi hien khi buoc thuc hien phan xu ly chuyen trach cua symbol hien tai da duoc backend chot.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/signing.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`. Dung cung cap voi cac ham `_normalize_key`, `_or_queries`, `_resolve_department_by_keywords` trong module nay.
    Tac dung: Tap trung rule thuc hien phan xu ly chuyen trach cua symbol hien tai vao mot noi de moi API va service dung chung cung chuan.
    """
    if not user or not user.is_authenticated or group is None:
        return False
    return UserGroupMembership.objects.filter(
        user=user,
        group=group,
    ).exists()

def get_department_members_qs(department):
    """
    Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
    Vai tro backend: Ham `get_department_members_qs` chiu trach nhiem thuc hien phan xu ly chuyen trach cua symbol hien tai trong file `signing/permissions.py`.
    Vai tro cua no trong frontend: Frontend dung ket qua cua ham nay theo cach gian tiep vi danh sach, nut thao tac va badge chi hien khi buoc thuc hien phan xu ly chuyen trach cua symbol hien tai da duoc backend chot.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/signing.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`. Dung cung cap voi cac ham `_normalize_key`, `_or_queries`, `_resolve_department_by_keywords` trong module nay.
    Tac dung: Tap trung rule thuc hien phan xu ly chuyen trach cua symbol hien tai vao mot noi de moi API va service dung chung cung chuan.
    """
    if department is None:
        return User.objects.none()
    return User.objects.filter(
        models.Q(managed_departments=department)
        | models.Q(department_memberships__department=department, department_memberships__is_active=True)
    ).filter(is_active=True).distinct()

def get_group_members_qs(group):
    """
    Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
    Vai tro backend: Ham `get_group_members_qs` chiu trach nhiem thuc hien phan xu ly chuyen trach cua symbol hien tai trong file `signing/permissions.py`.
    Vai tro cua no trong frontend: Frontend dung ket qua cua ham nay theo cach gian tiep vi danh sach, nut thao tac va badge chi hien khi buoc thuc hien phan xu ly chuyen trach cua symbol hien tai da duoc backend chot.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/signing.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`. Dung cung cap voi cac ham `_normalize_key`, `_or_queries`, `_resolve_department_by_keywords` trong module nay.
    Tac dung: Tap trung rule thuc hien phan xu ly chuyen trach cua symbol hien tai vao mot noi de moi API va service dung chung cung chuan.
    """
    if group is None:
        return User.objects.none()
    return User.objects.filter(
        group_memberships__group=group,
        is_active=True,
    ).distinct()

def get_special_department_members_qs(department, group):
    """
    Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
    Vai tro backend: Ham `get_special_department_members_qs` chiu trach nhiem thuc hien phan xu ly chuyen trach cua symbol hien tai trong file `signing/permissions.py`.
    Vai tro cua no trong frontend: Frontend dung ket qua cua ham nay theo cach gian tiep vi danh sach, nut thao tac va badge chi hien khi buoc thuc hien phan xu ly chuyen trach cua symbol hien tai da duoc backend chot.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/signing.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`. Dung cung cap voi cac ham `_normalize_key`, `_or_queries`, `_resolve_department_by_keywords` trong module nay.
    Tac dung: Tap trung rule thuc hien phan xu ly chuyen trach cua symbol hien tai vao mot noi de moi API va service dung chung cung chuan.
    """
    filters = _or_queries(
        models.Q(managed_departments=department) if department is not None else None,
        models.Q(department_memberships__department=department, department_memberships__is_active=True)
        if department is not None else None,
        models.Q(group_memberships__group=group) if group is not None else None,
    )
    if filters is None:
        return User.objects.none()
    return User.objects.filter(filters, is_active=True).distinct()

def is_special_department_member(user, department, group):
    """
    Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
    Vai tro backend: Ham `is_special_department_member` chiu trach nhiem thuc hien phan xu ly chuyen trach cua symbol hien tai trong file `signing/permissions.py`.
    Vai tro cua no trong frontend: Frontend dung ket qua cua ham nay theo cach gian tiep vi danh sach, nut thao tac va badge chi hien khi buoc thuc hien phan xu ly chuyen trach cua symbol hien tai da duoc backend chot.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/signing.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`. Dung cung cap voi cac ham `_normalize_key`, `_or_queries`, `_resolve_department_by_keywords` trong module nay.
    Tac dung: Tap trung rule thuc hien phan xu ly chuyen trach cua symbol hien tai vao mot noi de moi API va service dung chung cung chuan.
    """
    return is_department_member(user, department) or is_group_member(user, group)

def has_department_permission(user, department, permission_type):
    """
    Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
    Vai tro backend: Ham `has_department_permission` chiu trach nhiem danh gia pham vi quyen truy cap trong file `signing/permissions.py`.
    Vai tro cua no trong frontend: Frontend dung ket qua cua ham nay theo cach gian tiep vi danh sach, nut thao tac va badge chi hien khi buoc danh gia pham vi quyen truy cap da duoc backend chot.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/signing.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`. Dung cung cap voi cac ham `_normalize_key`, `_or_queries`, `_resolve_department_by_keywords` trong module nay.
    Tac dung: Tap trung rule danh gia pham vi quyen truy cap vao mot noi de moi API va service dung chung cung chuan.
    """
    if not user or not user.is_authenticated or department is None:
        return False
    if is_department_manager(user, department):
        return True
    return DepartmentDelegation.objects.filter(
        department=department,
        delegate_user=user,
        permission_type=permission_type,
        is_active=True,
    ).exists()

def get_hr_reviewer_users_qs(user=None, company=None):
    """
    Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
    Vai tro backend: Ham `get_hr_reviewer_users_qs` chiu trach nhiem thuc hien phan xu ly chuyen trach cua symbol hien tai trong file `signing/permissions.py`.
    Vai tro cua no trong frontend: Frontend dung ket qua cua ham nay theo cach gian tiep vi danh sach, nut thao tac va badge chi hien khi buoc thuc hien phan xu ly chuyen trach cua symbol hien tai da duoc backend chot.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/signing.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`. Dung cung cap voi cac ham `_normalize_key`, `_or_queries`, `_resolve_department_by_keywords` trong module nay.
    Tac dung: Tap trung rule thuc hien phan xu ly chuyen trach cua symbol hien tai vao mot noi de moi API va service dung chung cung chuan.
    """
    company = company or get_user_company(user)
    hr_department = get_hr_department(user=user, company=company)
    hr_group = get_hr_group(user=user, company=company)
    reviewer_ids = set()

    if hr_department is not None:
        if hr_department.manager_id:
            reviewer_ids.add(hr_department.manager_id)
        reviewer_ids.update(
            DepartmentDelegation.objects.filter(
                department=hr_department,
                delegate_user__is_active=True,
                permission_type=DELEGATION_APPROVE_PROPOSAL,
                is_active=True,
            ).values_list('delegate_user_id', flat=True)
        )

    if hr_group is not None:
        reviewer_ids.update(
            UserGroupMembership.objects.filter(
                group=hr_group,
                role=UserGroupMembership.ROLE_LEADER,
                user__is_active=True,
            ).values_list('user_id', flat=True)
        )

    if not reviewer_ids:
        return User.objects.none()
    return User.objects.filter(id__in=reviewer_ids, is_active=True).distinct()

def get_accounting_special_users_qs(user=None, company=None):
    """
    Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
    Vai tro backend: Ham `get_accounting_special_users_qs` chiu trach nhiem thuc hien phan xu ly chuyen trach cua symbol hien tai trong file `signing/permissions.py`.
    Vai tro cua no trong frontend: Frontend dung ket qua cua ham nay theo cach gian tiep vi danh sach, nut thao tac va badge chi hien khi buoc thuc hien phan xu ly chuyen trach cua symbol hien tai da duoc backend chot.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/signing.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`. Dung cung cap voi cac ham `_normalize_key`, `_or_queries`, `_resolve_department_by_keywords` trong module nay.
    Tac dung: Tap trung rule thuc hien phan xu ly chuyen trach cua symbol hien tai vao mot noi de moi API va service dung chung cung chuan.
    """
    company = company or get_user_company(user)
    accounting_department = get_accounting_department(user=user, company=company)
    accounting_group = get_accounting_group(user=user, company=company)
    user_ids = set()

    if accounting_department is not None:
        if accounting_department.manager_id:
            user_ids.add(accounting_department.manager_id)
        user_ids.update(
            DepartmentDelegation.objects.filter(
                department=accounting_department,
                delegate_user__is_active=True,
                permission_type=DELEGATION_VIEW_SIGNED_PDF,
                is_active=True,
            ).values_list('delegate_user_id', flat=True)
        )

    if accounting_group is not None:
        user_ids.update(
            UserGroupMembership.objects.filter(
                group=accounting_group,
                role=UserGroupMembership.ROLE_LEADER,
                user__is_active=True,
            ).values_list('user_id', flat=True)
        )

    if not user_ids:
        return User.objects.none()
    return User.objects.filter(id__in=user_ids, is_active=True).distinct()

def can_review_signing_proposals(user):
    """
    Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
    Vai tro backend: Ham `can_review_signing_proposals` chiu trach nhiem thuc hien phan xu ly chuyen trach cua symbol hien tai trong file `signing/permissions.py`.
    Vai tro cua no trong frontend: Frontend dung ket qua cua ham nay theo cach gian tiep vi danh sach, nut thao tac va badge chi hien khi buoc thuc hien phan xu ly chuyen trach cua symbol hien tai da duoc backend chot.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/signing.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`. Dung cung cap voi cac ham `_normalize_key`, `_or_queries`, `_resolve_department_by_keywords` trong module nay.
    Tac dung: Tap trung rule thuc hien phan xu ly chuyen trach cua symbol hien tai vao mot noi de moi API va service dung chung cung chuan.
    """
    if not user or not user.is_authenticated:
        return False
    company = get_user_company(user)
    if company is None:
        return False
    return get_hr_reviewer_users_qs(user=user, company=company).filter(pk=user.pk).exists()

def can_manage_hr_delegations(user):
    """
    Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
    Vai tro backend: Ham `can_manage_hr_delegations` chiu trach nhiem thuc hien phan xu ly chuyen trach cua symbol hien tai trong file `signing/permissions.py`.
    Vai tro cua no trong frontend: Frontend dung ket qua cua ham nay theo cach gian tiep vi danh sach, nut thao tac va badge chi hien khi buoc thuc hien phan xu ly chuyen trach cua symbol hien tai da duoc backend chot.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/signing.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`. Dung cung cap voi cac ham `_normalize_key`, `_or_queries`, `_resolve_department_by_keywords` trong module nay.
    Tac dung: Tap trung rule thuc hien phan xu ly chuyen trach cua symbol hien tai vao mot noi de moi API va service dung chung cung chuan.
    """
    hr_department = get_hr_department(user)
    if is_department_manager(user, hr_department):
        return True
    return hr_department is not None and is_group_leader(user, get_hr_group(user))

def can_manage_accounting_delegations(user):
    """
    Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
    Vai tro backend: Ham `can_manage_accounting_delegations` chiu trach nhiem thuc hien phan xu ly chuyen trach cua symbol hien tai trong file `signing/permissions.py`.
    Vai tro cua no trong frontend: Frontend dung ket qua cua ham nay theo cach gian tiep vi danh sach, nut thao tac va badge chi hien khi buoc thuc hien phan xu ly chuyen trach cua symbol hien tai da duoc backend chot.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/signing.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`. Dung cung cap voi cac ham `_normalize_key`, `_or_queries`, `_resolve_department_by_keywords` trong module nay.
    Tac dung: Tap trung rule thuc hien phan xu ly chuyen trach cua symbol hien tai vao mot noi de moi API va service dung chung cung chuan.
    """
    accounting_department = get_accounting_department(user)
    if is_department_manager(user, accounting_department):
        return True
    return accounting_department is not None and is_group_leader(user, get_accounting_group(user))

def can_view_signed_pdf_via_special_access(user):
    """
    Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
    Vai tro backend: Ham `can_view_signed_pdf_via_special_access` chiu trach nhiem thuc hien phan xu ly chuyen trach cua symbol hien tai trong file `signing/permissions.py`.
    Vai tro cua no trong frontend: Frontend dung ket qua cua ham nay theo cach gian tiep vi danh sach, nut thao tac va badge chi hien khi buoc thuc hien phan xu ly chuyen trach cua symbol hien tai da duoc backend chot.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/signing.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`. Dung cung cap voi cac ham `_normalize_key`, `_or_queries`, `_resolve_department_by_keywords` trong module nay.
    Tac dung: Tap trung rule thuc hien phan xu ly chuyen trach cua symbol hien tai vao mot noi de moi API va service dung chung cung chuan.
    """
    if not user or not user.is_authenticated:
        return False
    return (
        get_hr_reviewer_users_qs(user).filter(pk=user.pk).exists()
        or get_accounting_special_users_qs(user).filter(pk=user.pk).exists()
    )

def get_pending_hr_proposals(user):
    """
    Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
    Vai tro backend: Ham `get_pending_hr_proposals` chiu trach nhiem thuc hien phan xu ly chuyen trach cua symbol hien tai trong file `signing/permissions.py`.
    Vai tro cua no trong frontend: Frontend dung ket qua cua ham nay theo cach gian tiep vi danh sach, nut thao tac va badge chi hien khi buoc thuc hien phan xu ly chuyen trach cua symbol hien tai da duoc backend chot.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/signing.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`. Dung cung cap voi cac ham `_normalize_key`, `_or_queries`, `_resolve_department_by_keywords` trong module nay.
    Tac dung: Tap trung rule thuc hien phan xu ly chuyen trach cua symbol hien tai vao mot noi de moi API va service dung chung cung chuan.
    """
    if not can_review_signing_proposals(user):
        return SigningProposal.objects.none()
    queryset = SigningProposal.objects.filter(
        status=PROPOSAL_PENDING_HR_REVIEW,
    ).select_related(
        'company',
        'document',
        'document__owner',
        'proposed_by',
        'hr_reviewed_by',
    ).prefetch_related('signers__signer_user')
    return filter_queryset_by_current_company(queryset, user)

def get_accessible_signing_tasks(user):
    """
    Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
    Vai tro backend: Ham `get_accessible_signing_tasks` chiu trach nhiem danh gia pham vi quyen truy cap trong file `signing/permissions.py`.
    Vai tro cua no trong frontend: Frontend dung ket qua cua ham nay theo cach gian tiep vi danh sach, nut thao tac va badge chi hien khi buoc danh gia pham vi quyen truy cap da duoc backend chot.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/signing.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`. Dung cung cap voi cac ham `_normalize_key`, `_or_queries`, `_resolve_department_by_keywords` trong module nay.
    Tac dung: Tap trung rule danh gia pham vi quyen truy cap vao mot noi de moi API va service dung chung cung chuan.
    """
    if not user or not user.is_authenticated:
        return SigningTask.objects.none()
    queryset = SigningTask.objects.filter(
        signer_user=user,
    ).select_related(
        'company',
        'packet',
        'packet__document',
        'packet__proposal',
        'signer_user',
    )
    return filter_queryset_by_current_company(queryset, user)

def get_accessible_signed_pdfs(user):
    """
    Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
    Vai tro backend: Ham `get_accessible_signed_pdfs` chiu trach nhiem danh gia pham vi quyen truy cap trong file `signing/permissions.py`.
    Vai tro cua no trong frontend: Frontend dung ket qua cua ham nay theo cach gian tiep vi danh sach, nut thao tac va badge chi hien khi buoc danh gia pham vi quyen truy cap da duoc backend chot.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/signing.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`. Dung cung cap voi cac ham `_normalize_key`, `_or_queries`, `_resolve_department_by_keywords` trong module nay.
    Tac dung: Tap trung rule danh gia pham vi quyen truy cap vao mot noi de moi API va service dung chung cung chuan.
    """
    if not user or not user.is_authenticated:
        return SignedPdfDocument.objects.none()
    base_qs = SignedPdfDocument.objects.select_related(
        'owner',
        'company',
        'source_document',
        'packet',
        'packet__proposal',
    ).prefetch_related('packet__tasks__signer_user', 'signature_records__signer_user', 'signature_records__task')
    company = get_user_company(user)
    if company is not None:
        base_qs = base_qs.filter(company=company)
    if can_view_signed_pdf_via_special_access(user):
        return base_qs
    return base_qs.filter(
        models.Q(packet__tasks__signer_user=user)
        | models.Q(packet__proposal__proposed_by=user)
    ).distinct()

def can_view_signing_packet(user, packet):
    """
    Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
    Vai tro backend: Ham `can_view_signing_packet` chiu trach nhiem thuc hien phan xu ly chuyen trach cua symbol hien tai trong file `signing/permissions.py`.
    Vai tro cua no trong frontend: Frontend dung ket qua cua ham nay theo cach gian tiep vi danh sach, nut thao tac va badge chi hien khi buoc thuc hien phan xu ly chuyen trach cua symbol hien tai da duoc backend chot.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/signing.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`. Dung cung cap voi cac ham `_normalize_key`, `_or_queries`, `_resolve_department_by_keywords` trong module nay.
    Tac dung: Tap trung rule thuc hien phan xu ly chuyen trach cua symbol hien tai vao mot noi de moi API va service dung chung cung chuan.
    """
    if not user or not user.is_authenticated:
        return False
    company = get_user_company(user)
    if company is not None and getattr(packet, 'company_id', None) not in (None, company.id):
        return False
    if packet.document.owner_id == user.id:
        return True
    if packet.tasks.filter(signer_user=user).exists():
        return True
    return can_review_signing_proposals(user)

def can_view_signed_pdf(user, signed_pdf):
    """
    Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
    Vai tro backend: Ham `can_view_signed_pdf` chiu trach nhiem thuc hien phan xu ly chuyen trach cua symbol hien tai trong file `signing/permissions.py`.
    Vai tro cua no trong frontend: Frontend dung ket qua cua ham nay theo cach gian tiep vi danh sach, nut thao tac va badge chi hien khi buoc thuc hien phan xu ly chuyen trach cua symbol hien tai da duoc backend chot.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/signing.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`. Dung cung cap voi cac ham `_normalize_key`, `_or_queries`, `_resolve_department_by_keywords` trong module nay.
    Tac dung: Tap trung rule thuc hien phan xu ly chuyen trach cua symbol hien tai vao mot noi de moi API va service dung chung cung chuan.
    """
    if not user or not user.is_authenticated:
        return False
    company = get_user_company(user)
    if company is not None and getattr(signed_pdf, 'company_id', None) not in (None, company.id):
        return False
    if can_view_signed_pdf_via_special_access(user):
        return True
    if signed_pdf.packet.proposal.proposed_by_id == user.id:
        return True
    return signed_pdf.packet.tasks.filter(signer_user=user).exists()

def get_signing_summary(user):
    """
    Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
    Vai tro backend: Ham `get_signing_summary` chiu trach nhiem tong hop so lieu tom tat trong file `signing/permissions.py`.
    Vai tro cua no trong frontend: Frontend dung ket qua cua ham nay theo cach gian tiep vi danh sach, nut thao tac va badge chi hien khi buoc tong hop so lieu tom tat da duoc backend chot.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/signing.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`. Dung cung cap voi cac ham `_normalize_key`, `_or_queries`, `_resolve_department_by_keywords` trong module nay.
    Tac dung: Tap trung rule tong hop so lieu tom tat vao mot noi de moi API va service dung chung cung chuan.
    """
    tasks = get_accessible_signing_tasks(user)
    actionable = tasks.filter(status='available', packet__status='active').count()
    blocked = tasks.filter(status='blocked', packet__status='active').count()
    signed = tasks.filter(status='signed').count()
    hr_pending = 0
    mailbox_pending_entries = 0
    mailbox_pending_threads = 0
    if user and user.is_authenticated:
        mailbox_pending_qs = DocumentMailboxEntry.objects.filter(
            forwarded_to=user,
            status=MAILBOX_STATUS_VIEW,
        )
        mailbox_pending_qs = filter_queryset_by_current_company(mailbox_pending_qs, user)
        mailbox_pending_entries = mailbox_pending_qs.count()
        mailbox_pending_threads = mailbox_pending_qs.values('thread_id').distinct().count()
        hr_pending = get_pending_hr_proposals(user).count()
    return {
        'tasks_available': actionable,
        'tasks_blocked': blocked,
        'tasks_signed': signed,
        'tasks_total': tasks.count(),
        'hr_pending_proposals': hr_pending,
        'actionable_total': actionable + hr_pending,
        'can_review_proposals': can_review_signing_proposals(user),
        'can_manage_hr_delegations': can_manage_hr_delegations(user),
        'can_manage_accounting_delegations': can_manage_accounting_delegations(user),
        'can_view_signed_pdfs_special': can_view_signed_pdf_via_special_access(user),
        'mailbox_pending_entries': mailbox_pending_entries,
        'mailbox_pending_threads': mailbox_pending_threads,
        'hr_department_name': getattr(get_hr_department(user), 'name', None),
        'accounting_department_name': getattr(get_accounting_department(user), 'name', None),
        'hr_group_name': getattr(get_hr_group(user), 'name', None),
        'accounting_group_name': getattr(get_accounting_group(user), 'name', None),
    }
