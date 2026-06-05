from __future__ import annotations

import io
import secrets
import unicodedata
from dataclasses import dataclass
from typing import BinaryIO, Optional

from django.contrib.auth.models import User
from django.db import transaction
from django.utils.text import slugify

from .models import (
    Company,
    CompanyAIConfig,
    CompanyImportBatch,
    CompanyPosition,
    CompanyRole,
    CompanyStatus,
    CompanyUserMembership,
    Department,
    DepartmentMembership,
    UserGroup,
    UserGroupMembership,
    UserProfile,
)


@dataclass(frozen=True)
class BootstrapAdminResult:
    user: User
    membership: CompanyUserMembership
    raw_password: str


@dataclass(frozen=True)
class CompanyCredentialRow:
    full_name: str
    email: str
    username: str
    password: str
    role: str
    department: str = ''
    position: str = ''
    employee_code: str = ''


@dataclass(frozen=True)
class CompanyCreationResult:
    company: Company
    bootstrap_admin: BootstrapAdminResult
    created_department_count: int
    created_position_count: int
    created_employee_count: int
    credential_rows: tuple[CompanyCredentialRow, ...]
    # Nghiep vu moi: cong ty to chuc theo NHOM (khong dung phong ban/chuc vu).
    created_group_count: int = 0


def normalize_text(value) -> str:
    return ' '.join(str(value or '').strip().split())


def normalize_lookup(value) -> str:
    text = normalize_text(value).casefold()
    text = unicodedata.normalize('NFKD', text)
    return ''.join(ch for ch in text if not unicodedata.combining(ch))


def build_technical_username(company_code: str, local_username: str) -> str:
    base = slugify(f'cmp-{company_code}-{local_username}').replace('-', '_')
    technical_username = base[:140] or 'company_user'
    candidate = technical_username
    suffix = 1
    while User.objects.filter(username=candidate).exists():
        suffix_text = f'_{suffix}'
        candidate = f'{technical_username[: max(1, 140 - len(suffix_text))]}{suffix_text}'
        suffix += 1
    return candidate


def default_local_username(*, email: str = '', full_name: str = '') -> str:
    if email and '@' in email:
        base = email.split('@', 1)[0]
    else:
        base = slugify(full_name).replace('-', '_') or 'user'
    base = base.lower().replace('.', '_')
    return base[:150]


def _split_full_name(full_name: str):
    full_name = normalize_text(full_name)
    if not full_name:
        return '', ''
    parts = full_name.split()
    if len(parts) == 1:
        return parts[0], ''
    return parts[-1], ' '.join(parts[:-1])


def build_company_credential_row(
    *,
    user: User,
    membership: CompanyUserMembership,
    raw_password: str,
    department_name: str = '',
    position_name: str = '',
    employee_code: str = '',
) -> CompanyCredentialRow:
    full_name = normalize_text(user.get_full_name()) or membership.local_username
    return CompanyCredentialRow(
        full_name=full_name,
        email=normalize_text(user.email),
        username=membership.local_username,
        password=raw_password,
        role=membership.role,
        department=normalize_text(department_name),
        position=normalize_text(position_name),
        employee_code=normalize_text(employee_code),
    )


def serialize_company_credential_rows(credential_rows) -> list[dict]:
    return [
        {
            'full_name': row.full_name,
            'email': row.email,
            'username': row.username,
            'password': row.password,
            'role': row.role,
            'department': row.department,
            'position': row.position,
            'employee_code': row.employee_code,
        }
        for row in credential_rows
    ]


def _ensure_unique_local_username(company: Company, local_username: str) -> str:
    base = normalize_text(local_username).lower().replace(' ', '_')[:150] or 'user'
    candidate = base
    suffix = 1
    while CompanyUserMembership.objects.filter(company=company, local_username__iexact=candidate).exists():
        suffix_text = f'_{suffix}'
        candidate = f'{base[: max(1, 150 - len(suffix_text))]}{suffix_text}'
        suffix += 1
    return candidate


def _build_department_map(company: Company):
    result = {}
    for department in company.departments.all():
        result[normalize_lookup(department.code)] = department
        result[normalize_lookup(department.name)] = department
    return result


def _build_position_map(company: Company):
    result = {}
    for position in company.positions.all():
        result[normalize_lookup(position.code)] = position
        result[normalize_lookup(position.name)] = position
    return result


def _build_group_map(company: Company):
    result = {}
    for group in company.user_groups.all():
        result[normalize_lookup(group.name)] = group
    return result


def _normalize_role(value) -> str:
    """Chuan hoa vai tro -> 'leader' | 'member'."""
    text = normalize_lookup(value)
    if text in {'leader', 'truongnhom', 'truong nhom', 'tn', 'lead'}:
        return UserGroupMembership.ROLE_LEADER
    return UserGroupMembership.ROLE_MEMBER


def _normalize_employee_groups(item: dict) -> list[dict]:
    """Tra ve danh sach {'name', 'role'} cho cac nhom ma nhan vien thuoc ve.

    Ho tro nhieu dinh dang dau vao:
      - list[dict]: [{'group'|'name': 'Nhom A', 'role': 'leader'|'member'}, ...]
      - list[str] : ['Nhom A', 'Nhom B']
      - str (Excel): 'Nhom A:leader; Nhom B' (phan cach ';' , vai tro sau ':')
    """
    raw = item.get('groups')
    if raw is None:
        raw = item.get('nhom') or item.get('group')
    out: list[dict] = []
    if isinstance(raw, str):
        for chunk in raw.replace('\n', ';').split(';'):
            chunk = chunk.strip()
            if not chunk:
                continue
            if ':' in chunk:
                name, role = chunk.split(':', 1)
            else:
                name, role = chunk, ''
            name = normalize_text(name)
            if name:
                out.append({'name': name, 'role': _normalize_role(role)})
    elif isinstance(raw, (list, tuple)):
        for entry in raw:
            if isinstance(entry, dict):
                name = normalize_text(entry.get('group') or entry.get('name'))
                role = _normalize_role(entry.get('role'))
            else:
                name = normalize_text(entry)
                role = UserGroupMembership.ROLE_MEMBER
            if name:
                out.append({'name': name, 'role': role})
    return out


def _collect_manual_company_payload_errors(
    *,
    company_data: dict,
    groups: list[dict],
    employees: list[dict],
) -> list[str]:
    """Kiem tra payload tao cong ty theo NGHIEP VU NHOM (khong dung phong ban/chuc vu)."""
    errors: list[str] = []
    if not normalize_text(company_data.get('code')):
        errors.append('Cần nhập mã công ty.')
    if not normalize_text(company_data.get('name')):
        errors.append('Cần nhập tên công ty.')
    if not groups:
        errors.append('Cần tạo ít nhất 1 nhóm.')
    if not employees:
        errors.append('Cần tạo ít nhất 1 nhân sự.')

    group_keys: set[str] = set()
    for index, item in enumerate(groups, start=1):
        name = normalize_text(item.get('name'))
        if not name:
            errors.append(f'Nhóm #{index} cần có tên.')
            continue
        name_key = normalize_lookup(name)
        if name_key in group_keys:
            errors.append(f'Tên nhóm "{name}" bị trùng trong form tạo công ty.')
        group_keys.add(name_key)

    employee_code_keys: set[str] = set()
    local_username_keys: set[str] = set()
    for index, item in enumerate(employees, start=1):
        full_name = normalize_text(item.get('full_name') or item.get('name'))
        if not full_name:
            errors.append(f'Nhân sự #{index} cần có họ tên.')
        emp_groups = _normalize_employee_groups(item)
        if not emp_groups:
            errors.append(
                f'Nhân sự "{full_name or index}" cần được gán ít nhất 1 nhóm.'
            )
        for g in emp_groups:
            if normalize_lookup(g['name']) not in group_keys:
                errors.append(
                    f'Nhân sự "{full_name or index}" tham chiếu nhóm "{g["name"]}" không tồn tại.'
                )
        age_years = item.get('age_years')
        if age_years not in (None, ''):
            try:
                int(age_years)
            except (TypeError, ValueError):
                errors.append(f'Nhân sự "{full_name or index}" có tuổi không hợp lệ.')
        employee_code = normalize_text(item.get('employee_code') or item.get('ma_nhan_vien'))
        if employee_code:
            employee_code_key = normalize_lookup(employee_code)
            if employee_code_key in employee_code_keys:
                errors.append(f'Mã nhân viên "{employee_code}" bị trùng trong form tạo công ty.')
            employee_code_keys.add(employee_code_key)
        local_username = normalize_text(item.get('local_username')).lower()
        if local_username:
            local_username_key = normalize_lookup(local_username)
            if local_username_key in local_username_keys:
                errors.append(f'Username nội bộ "{local_username}" bị trùng trong form tạo công ty.')
            local_username_keys.add(local_username_key)

    return errors


def create_company_user(
    *,
    company: Company,
    local_username: str,
    email: str = '',
    password: Optional[str] = None,
    role: str = CompanyRole.COMPANY_USER,
    first_name: str = '',
    last_name: str = '',
    full_name: str = '',
    profile_data: Optional[dict] = None,
    department: Optional[Department] = None,
    actor: Optional[User] = None,
    must_change_password: bool = False,
) -> BootstrapAdminResult:
    if full_name and not first_name and not last_name:
        first_name, last_name = _split_full_name(full_name)
    raw_password = password or secrets.token_urlsafe(10)
    local_username = _ensure_unique_local_username(company, local_username)
    technical_username = build_technical_username(company.code, local_username)
    user = User.objects.create_user(
        username=technical_username,
        email=normalize_text(email),
        password=raw_password,
        first_name=normalize_text(first_name),
        last_name=normalize_text(last_name),
        is_staff=role == CompanyRole.COMPANY_ADMIN,
        is_superuser=False,
    )
    membership = CompanyUserMembership.objects.create(
        company=company,
        user=user,
        local_username=local_username,
        role=role,
        must_change_password=must_change_password,
    )
    profile = user.profile
    profile.company = company
    profile_data = profile_data or {}
    profile.chuc_danh = normalize_text(profile_data.get('chuc_danh'))
    profile.cccd = normalize_text(profile_data.get('cccd'))
    profile.ma_nhan_vien = normalize_text(profile_data.get('ma_nhan_vien'))
    profile.so_yeu_ly_lich = str(profile_data.get('so_yeu_ly_lich') or '').strip()
    profile.so_dien_thoai = normalize_text(profile_data.get('so_dien_thoai'))
    profile.dia_chi = normalize_text(profile_data.get('dia_chi'))
    profile.bio = str(profile_data.get('bio') or '').strip()
    age_years = profile_data.get('age_years')
    if age_years not in (None, ''):
        try:
            profile.age_years = int(age_years)
        except (TypeError, ValueError):
            profile.age_years = None
    profile.save()
    if department is not None:
        DepartmentMembership.objects.get_or_create(
            department=department,
            user=user,
            defaults={'is_active': True},
        )
    CompanyAIConfig.seed_defaults(company, actor=actor)
    return BootstrapAdminResult(user=user, membership=membership, raw_password=raw_password)


def reset_company_bootstrap_admin(
    company: Company,
    *,
    actor: Optional[User] = None,
) -> BootstrapAdminResult:
    membership = (
        CompanyUserMembership.objects.select_related('user')
        .filter(company=company, role=CompanyRole.COMPANY_ADMIN)
        .order_by('pk')
        .first()
    )
    if membership is None:
        return create_company_user(
            company=company,
            local_username='admin',
            email=normalize_text(company.email),
            role=CompanyRole.COMPANY_ADMIN,
            full_name='Company Admin',
            actor=actor,
            must_change_password=True,
        )

    raw_password = secrets.token_urlsafe(10)
    membership.user.set_password(raw_password)
    membership.user.is_active = True
    membership.user.is_staff = True
    membership.user.is_superuser = False
    membership.user.save(update_fields=['password', 'is_active', 'is_staff', 'is_superuser'])
    membership.is_active = True
    membership.must_change_password = True
    membership.save(update_fields=['is_active', 'must_change_password'])
    return BootstrapAdminResult(user=membership.user, membership=membership, raw_password=raw_password)


def create_company_from_payload(payload: dict, *, actor: Optional[User] = None) -> CompanyCreationResult:
    company_data = payload.get('company') or payload
    groups = list(payload.get('groups') or [])
    employees = list(payload.get('employees') or [])
    company_status = company_data.get('status') or CompanyStatus.ACTIVE
    validation_errors = _collect_manual_company_payload_errors(
        company_data=company_data,
        groups=groups,
        employees=employees,
    )
    if validation_errors:
        raise ValueError(validation_errors)

    with transaction.atomic():
        credential_rows = []
        company = Company.objects.create(
            code=normalize_text(company_data.get('code')).lower() or slugify(company_data.get('name') or 'company'),
            slug=normalize_text(company_data.get('slug')),
            name=normalize_text(company_data.get('name')),
            status=company_status,
            description=str(company_data.get('description') or '').strip(),
            industry=normalize_text(company_data.get('industry')),
            address=normalize_text(company_data.get('address')),
            email=normalize_text(company_data.get('email')),
            phone=normalize_text(company_data.get('phone')),
            website=normalize_text(company_data.get('website')),
            company_context=str(company_data.get('company_context') or '').strip(),
            created_by=actor,
            updated_by=actor,
        )
        CompanyAIConfig.seed_defaults(company, actor=actor)

        for item in groups:
            name = normalize_text(item.get('name'))
            if not name:
                continue
            UserGroup.objects.create(
                company=company,
                name=name,
                description=str(item.get('description') or '').strip(),
                created_by=actor,
            )

        group_map = _build_group_map(company)

        bootstrap_admin = create_company_user(
            company=company,
            local_username='admin',
            email=normalize_text(company_data.get('admin_email')),
            password=company_data.get('admin_password') or None,
            role=CompanyRole.COMPANY_ADMIN,
            full_name=normalize_text(company_data.get('admin_full_name')) or 'Company Admin',
            actor=actor,
            must_change_password=True,
        )
        credential_rows.append(
            build_company_credential_row(
                user=bootstrap_admin.user,
                membership=bootstrap_admin.membership,
                raw_password=bootstrap_admin.raw_password,
                position_name='Company Admin',
            )
        )

        created_employee_count = 0
        for item in employees:
            local_username = item.get('local_username') or default_local_username(
                email=str(item.get('email') or ''),
                full_name=str(item.get('full_name') or item.get('name') or ''),
            )
            emp_groups = _normalize_employee_groups(item)
            chuc_danh = normalize_text(
                item.get('chuc_danh') or item.get('position') or item.get('chuc_vu')
            )
            profile_data = {
                'age_years': item.get('age_years'),
                'so_yeu_ly_lich': item.get('profile_text') or item.get('so_yeu_ly_lich'),
                'bio': item.get('profile_text') or item.get('bio'),
                'ma_nhan_vien': item.get('employee_code') or item.get('ma_nhan_vien'),
                'cccd': item.get('cccd'),
                'so_dien_thoai': item.get('phone') or item.get('so_dien_thoai'),
                'dia_chi': item.get('address') or item.get('dia_chi'),
                'chuc_danh': chuc_danh,
            }
            created = create_company_user(
                company=company,
                local_username=local_username,
                email=normalize_text(item.get('email')),
                password=item.get('password') or None,
                role=CompanyRole.COMPANY_USER,
                full_name=normalize_text(item.get('full_name') or item.get('name')),
                first_name=normalize_text(item.get('first_name')),
                last_name=normalize_text(item.get('last_name')),
                profile_data=profile_data,
                actor=actor,
            )
            # Gan nhan vien vao cac NHOM (vai tro theo tung nhom).
            assigned_group_names: list[str] = []
            for g in emp_groups:
                grp = group_map.get(normalize_lookup(g['name']))
                if grp is None:
                    continue
                UserGroupMembership.objects.get_or_create(
                    group=grp,
                    user=created.user,
                    defaults={'role': g['role']},
                )
                assigned_group_names.append(grp.name)
            credential_rows.append(
                build_company_credential_row(
                    user=created.user,
                    membership=created.membership,
                    raw_password=created.raw_password,
                    department_name=', '.join(assigned_group_names),
                    position_name=chuc_danh,
                    employee_code=profile_data.get('ma_nhan_vien') or '',
                )
            )
            created_employee_count += 1

    return CompanyCreationResult(
        company=company,
        bootstrap_admin=bootstrap_admin,
        created_department_count=0,
        created_position_count=0,
        created_group_count=len(groups),
        created_employee_count=created_employee_count,
        credential_rows=tuple(credential_rows),
    )


def build_company_import_template_bytes(*, company: Optional[Company] = None, include_company_sheet: bool = True) -> bytes:
    import openpyxl

    workbook = openpyxl.Workbook()
    staff_sheet = workbook.active
    staff_sheet.title = 'Sheet1-NhanSu'
    staff_sheet.append([
        'Ten',
        'Tuoi',
        'HoSo',
        'Nhom',
        'ChucDanh',
        'Email',
        'SoDienThoai',
        'DiaChi',
        'MaNhanVien',
        'CCCD',
    ])
    # Cot "Nhom": cho phep gan NHIEU nhom, phan cach bang ";", vai tro sau dau ":"
    # (vd: "Hanh Chinh:leader; Ke Toan"). Khong ghi vai tro = thanh vien.
    staff_sheet.append([
        'Nguyen Van A',
        30,
        'Nhan vien chuyen theo doi van ban den va di.',
        'Hanh Chinh:leader; Ke Toan',
        'Chuyen Vien',
        'nguyenvana@example.com',
        '0912345678',
        '123 Duong ABC, Quan 1',
        'NV001',
        '012345678901',
    ])

    catalog_sheet = workbook.create_sheet('Sheet2-DanhMuc')
    catalog_sheet.append(['Loai', 'Ma', 'Ten', 'MoTa'])
    catalog_sheet.append(['group', '', 'Hanh Chinh', 'Nhom hanh chinh'])
    catalog_sheet.append(['group', '', 'Ke Toan', 'Nhom ke toan'])

    if include_company_sheet:
        company_sheet = workbook.create_sheet('Sheet3-CongTy')
        company_sheet.append([
            'TenCongTy',
            'MaCongTy',
            'MoTa',
            'LinhVuc',
            'DiaChi',
            'Email',
            'DienThoai',
            'Website',
            'NguCanhCongTy',
        ])
        company_sheet.append([
            company.name if company else 'Cong ty mau',
            company.code if company else 'cong-ty-mau',
            company.description if company else 'Mo ta cong ty',
            company.industry if company else 'Van phong',
            company.address if company else '123 Duong Mau',
            company.email if company else 'contact@example.com',
            company.phone if company else '0900000000',
            company.website if company else 'https://example.com',
            company.company_context if company else 'Ngu canh cong ty mau de AI suy dien cho user thuoc cong ty nay.',
        ])

    buffer = io.BytesIO()
    workbook.save(buffer)
    buffer.seek(0)
    return buffer.read()


def build_company_credentials_workbook_bytes(
    *,
    company_name: str,
    company_code: str,
    credential_rows,
) -> bytes:
    import openpyxl

    rows = list(credential_rows or [])
    workbook = openpyxl.Workbook()
    credentials_sheet = workbook.active
    credentials_sheet.title = 'TaiKhoanNhanSu'
    credentials_sheet.append(
        [
            'HoTen',
            'Email',
            'Username',
            'Password',
            'VaiTro',
            'PhongBan',
            'ChucVu',
            'MaNhanVien',
        ]
    )
    for row in rows:
        if isinstance(row, dict):
            item = row
        else:
            item = {
                'full_name': row.full_name,
                'email': row.email,
                'username': row.username,
                'password': row.password,
                'role': row.role,
                'department': row.department,
                'position': row.position,
                'employee_code': row.employee_code,
            }
        credentials_sheet.append(
            [
                normalize_text(item.get('full_name')),
                normalize_text(item.get('email')),
                normalize_text(item.get('username')),
                str(item.get('password') or '').strip(),
                normalize_text(item.get('role')),
                normalize_text(item.get('department')),
                normalize_text(item.get('position')),
                normalize_text(item.get('employee_code')),
            ]
        )

    company_sheet = workbook.create_sheet('ThongTinCongTy')
    company_sheet.append(['TenCongTy', normalize_text(company_name)])
    company_sheet.append(['MaCongTy', normalize_text(company_code)])
    company_sheet.append(['TongTaiKhoan', len(rows)])

    for sheet in workbook.worksheets:
        for column in sheet.columns:
            max_len = 0
            letter = column[0].column_letter
            for cell in column:
                value = '' if cell.value is None else str(cell.value)
                max_len = max(max_len, len(value))
            sheet.column_dimensions[letter].width = min(max(max_len + 2, 12), 40)

    buffer = io.BytesIO()
    workbook.save(buffer)
    buffer.seek(0)
    return buffer.read()


def _sheet_headers(sheet):
    return [normalize_text(value) for value in next(sheet.iter_rows(min_row=1, max_row=1, values_only=True))]


def _find_header(headers, *candidates):
    normalized_headers = [normalize_lookup(header) for header in headers]
    for candidate in candidates:
        wanted = normalize_lookup(candidate)
        for index, header in enumerate(normalized_headers):
            if header == wanted or wanted in header:
                return index
    return None


def preview_company_import(excel_file: BinaryIO, *, actor: Optional[User] = None) -> CompanyImportBatch:
    import openpyxl

    workbook = openpyxl.load_workbook(excel_file)
    errors = []

    if 'Sheet1-NhanSu' not in workbook.sheetnames:
        errors.append({'sheet': 'Sheet1-NhanSu', 'row': 0, 'message': 'Thieu sheet nhan su.'})
    if 'Sheet2-DanhMuc' not in workbook.sheetnames:
        errors.append({'sheet': 'Sheet2-DanhMuc', 'row': 0, 'message': 'Thieu sheet danh muc.'})
    if 'Sheet3-CongTy' not in workbook.sheetnames:
        errors.append({'sheet': 'Sheet3-CongTy', 'row': 0, 'message': 'Thieu sheet cong ty.'})

    preview_payload = {
        'company': {},
        'groups': [],
        'employees': [],
    }

    if 'Sheet3-CongTy' in workbook.sheetnames:
        sheet = workbook['Sheet3-CongTy']
        rows = list(sheet.iter_rows(values_only=True))
        if rows:
            if len(rows) >= 2 and sum(1 for item in rows[0] if item not in (None, '')) > 1:
                headers = [normalize_text(value) for value in rows[0]]
                values = rows[1] if len(rows) > 1 else []
                lookup = {normalize_lookup(headers[idx]): values[idx] for idx in range(min(len(headers), len(values)))}
            else:
                lookup = {}
                for row in rows:
                    if len(row) >= 2 and row[0]:
                        lookup[normalize_lookup(row[0])] = row[1]
            preview_payload['company'] = {
                'name': normalize_text(lookup.get('tencongty') or lookup.get('ten cong ty')),
                'code': normalize_text(lookup.get('macongty') or lookup.get('ma cong ty')).lower(),
                'description': str(lookup.get('mota') or lookup.get('mo ta') or '').strip(),
                'industry': normalize_text(lookup.get('linhvuc') or lookup.get('nganhnghe') or lookup.get('linh vuc')),
                'address': normalize_text(lookup.get('diachi') or lookup.get('dia chi')),
                'email': normalize_text(lookup.get('email')),
                'phone': normalize_text(lookup.get('dienthoai') or lookup.get('dien thoai')),
                'website': normalize_text(lookup.get('website')),
                'company_context': str(
                    lookup.get('ngucanhcongty')
                    or lookup.get('ngu canh cong ty')
                    or lookup.get('companycontext')
                    or ''
                ).strip(),
                'status': CompanyStatus.ACTIVE,
            }
            if not preview_payload['company']['name']:
                errors.append({'sheet': 'Sheet3-CongTy', 'row': 1, 'message': 'Thieu TenCongTy.'})
            if not preview_payload['company']['code']:
                errors.append({'sheet': 'Sheet3-CongTy', 'row': 1, 'message': 'Thieu MaCongTy.'})

    catalog_group_keys = set()
    if 'Sheet2-DanhMuc' in workbook.sheetnames:
        sheet = workbook['Sheet2-DanhMuc']
        headers = _sheet_headers(sheet)
        # Moi dong la 1 NHOM (cot Ten). Bo qua cot Loai/Ma cu neu co.
        name_idx = _find_header(headers, 'Ten', 'TenNhom', 'Nhom')
        description_idx = _find_header(headers, 'MoTa', 'Mo ta')
        for row_number, row in enumerate(sheet.iter_rows(min_row=2, values_only=True), start=2):
            name = normalize_text(row[name_idx] if name_idx is not None and name_idx < len(row) else '')
            description = str(row[description_idx] if description_idx is not None and description_idx < len(row) else '').strip()
            if not name:
                continue
            key = normalize_lookup(name)
            if key in catalog_group_keys:
                continue
            preview_payload['groups'].append({'name': name, 'description': description})
            catalog_group_keys.add(key)

    if 'Sheet1-NhanSu' in workbook.sheetnames:
        sheet = workbook['Sheet1-NhanSu']
        headers = _sheet_headers(sheet)
        name_idx = _find_header(headers, 'Ten', 'HoTen', 'Ho ten')
        age_idx = _find_header(headers, 'Tuoi')
        profile_idx = _find_header(headers, 'HoSo', 'Ho so', 'SoYeuLyLich')
        group_idx = _find_header(headers, 'Nhom', 'Nhom/VaiTro', 'PhongBan', 'Phong ban')
        chuc_danh_idx = _find_header(headers, 'ChucDanh', 'Chuc danh', 'ChucVu', 'Chuc vu')
        email_idx = _find_header(headers, 'Email')
        phone_idx = _find_header(headers, 'SoDienThoai', 'So dien thoai')
        address_idx = _find_header(headers, 'DiaChi', 'Dia chi')
        employee_code_idx = _find_header(headers, 'MaNhanVien', 'Ma nhan vien')
        cccd_idx = _find_header(headers, 'CCCD')

        for row_number, row in enumerate(sheet.iter_rows(min_row=2, values_only=True), start=2):
            full_name = normalize_text(row[name_idx] if name_idx is not None and name_idx < len(row) else '')
            if not full_name and not any(value not in (None, '') for value in row):
                continue
            age_value = row[age_idx] if age_idx is not None and age_idx < len(row) else None
            group_raw = normalize_text(row[group_idx] if group_idx is not None and group_idx < len(row) else '')
            chuc_danh = normalize_text(row[chuc_danh_idx] if chuc_danh_idx is not None and chuc_danh_idx < len(row) else '')
            emp_groups = _normalize_employee_groups({'groups': group_raw})
            if not full_name:
                errors.append({'sheet': 'Sheet1-NhanSu', 'row': row_number, 'message': 'Thieu Ten.'})
            if age_value not in (None, ''):
                try:
                    int(age_value)
                except (TypeError, ValueError):
                    errors.append({'sheet': 'Sheet1-NhanSu', 'row': row_number, 'message': 'Tuoi khong hop le.'})
            if not emp_groups:
                errors.append({'sheet': 'Sheet1-NhanSu', 'row': row_number, 'message': 'Thieu Nhom cho nhan su.'})
            for g in emp_groups:
                if normalize_lookup(g['name']) not in catalog_group_keys:
                    errors.append({'sheet': 'Sheet1-NhanSu', 'row': row_number, 'message': f'Nhom "{g["name"]}" khong co trong Sheet2.'})
            preview_payload['employees'].append(
                {
                    'full_name': full_name,
                    'age_years': age_value,
                    'profile_text': str(row[profile_idx] if profile_idx is not None and profile_idx < len(row) else '').strip(),
                    'groups': emp_groups,
                    'chuc_danh': chuc_danh,
                    'email': normalize_text(row[email_idx] if email_idx is not None and email_idx < len(row) else ''),
                    'phone': normalize_text(row[phone_idx] if phone_idx is not None and phone_idx < len(row) else ''),
                    'address': normalize_text(row[address_idx] if address_idx is not None and address_idx < len(row) else ''),
                    'employee_code': normalize_text(row[employee_code_idx] if employee_code_idx is not None and employee_code_idx < len(row) else ''),
                    'cccd': normalize_text(row[cccd_idx] if cccd_idx is not None and cccd_idx < len(row) else ''),
                }
            )

    batch = CompanyImportBatch.objects.create(
        source_type=CompanyImportBatch.SOURCE_EXCEL,
        status=CompanyImportBatch.STATUS_PREVIEWED if not errors else CompanyImportBatch.STATUS_FAILED,
        uploaded_by=actor,
        preview_payload=preview_payload,
        validation_errors=errors,
        commit_summary={
            'group_count': len(preview_payload['groups']),
            'employee_count': len(preview_payload['employees']),
        },
    )
    return batch


def commit_company_import(batch: CompanyImportBatch, *, actor: Optional[User] = None) -> CompanyCreationResult:
    if batch.status == CompanyImportBatch.STATUS_COMMITTED:
        raise ValueError('Batch da duoc commit.')
    if batch.validation_errors:
        raise ValueError('Batch preview con loi, khong the commit.')
    result = create_company_from_payload(batch.preview_payload, actor=actor)
    batch.target_company = result.company
    batch.status = CompanyImportBatch.STATUS_COMMITTED
    batch.commit_summary = {
        'company_id': result.company.id,
        'company_code': result.company.code,
        'bootstrap_admin_username': result.bootstrap_admin.membership.local_username,
        'group_count': result.created_group_count,
        'employee_count': result.created_employee_count,
    }
    batch.save(update_fields=['target_company', 'status', 'commit_summary', 'updated_at'])
    return result


def _find_existing_company_user(
    *,
    company: Company,
    local_username: str,
    email: str,
    employee_code: str,
) -> Optional[CompanyUserMembership]:
    memberships = CompanyUserMembership.objects.select_related('user', 'user__profile').filter(company=company)
    if employee_code:
        membership = memberships.filter(user__profile__ma_nhan_vien__iexact=employee_code).first()
        if membership is not None:
            return membership
    if email:
        membership = memberships.filter(user__email__iexact=email).first()
        if membership is not None:
            return membership
    if local_username:
        return memberships.filter(local_username__iexact=local_username).first()
    return None


def import_company_people_from_excel(
    excel_file: BinaryIO,
    *,
    company: Company,
    actor: Optional[User] = None,
) -> dict:
    import openpyxl

    workbook = openpyxl.load_workbook(excel_file)
    errors = []
    if 'Sheet1-NhanSu' not in workbook.sheetnames:
        errors.append({'sheet': 'Sheet1-NhanSu', 'row': 0, 'message': 'Thieu sheet nhan su.'})
    if 'Sheet2-DanhMuc' not in workbook.sheetnames:
        errors.append({'sheet': 'Sheet2-DanhMuc', 'row': 0, 'message': 'Thieu sheet danh muc.'})
    if errors:
        raise ValueError(errors)

    group_items = []
    employee_items = []

    # Sheet2-DanhMuc: moi dong la 1 NHOM (cot Ten). (Nghiep vu nhom, bo phong ban/chuc vu.)
    catalog_sheet = workbook['Sheet2-DanhMuc']
    catalog_headers = _sheet_headers(catalog_sheet)
    catalog_name_idx = _find_header(catalog_headers, 'Ten', 'TenNhom', 'Nhom')
    catalog_description_idx = _find_header(catalog_headers, 'MoTa', 'Mo ta')
    group_keys = set()
    for row_number, row in enumerate(catalog_sheet.iter_rows(min_row=2, values_only=True), start=2):
        name = normalize_text(row[catalog_name_idx] if catalog_name_idx is not None and catalog_name_idx < len(row) else '')
        description = str(row[catalog_description_idx] if catalog_description_idx is not None and catalog_description_idx < len(row) else '').strip()
        if not name:
            continue
        key = normalize_lookup(name)
        if key in group_keys:
            continue
        group_items.append({'name': name, 'description': description})
        group_keys.add(key)

    staff_sheet = workbook['Sheet1-NhanSu']
    staff_headers = _sheet_headers(staff_sheet)
    name_idx = _find_header(staff_headers, 'Ten', 'HoTen', 'Ho ten')
    age_idx = _find_header(staff_headers, 'Tuoi')
    profile_idx = _find_header(staff_headers, 'HoSo', 'Ho so', 'SoYeuLyLich')
    group_idx = _find_header(staff_headers, 'Nhom', 'Nhom/VaiTro', 'PhongBan', 'Phong ban')
    chuc_danh_idx = _find_header(staff_headers, 'ChucDanh', 'Chuc danh', 'ChucVu', 'Chuc vu')
    email_idx = _find_header(staff_headers, 'Email')
    phone_idx = _find_header(staff_headers, 'SoDienThoai', 'So dien thoai')
    address_idx = _find_header(staff_headers, 'DiaChi', 'Dia chi')
    employee_code_idx = _find_header(staff_headers, 'MaNhanVien', 'Ma nhan vien')
    cccd_idx = _find_header(staff_headers, 'CCCD')
    seen_employee_codes = set()

    for row_number, row in enumerate(staff_sheet.iter_rows(min_row=2, values_only=True), start=2):
        full_name = normalize_text(row[name_idx] if name_idx is not None and name_idx < len(row) else '')
        if not full_name and not any(value not in (None, '') for value in row):
            continue
        age_value = row[age_idx] if age_idx is not None and age_idx < len(row) else None
        group_raw = normalize_text(row[group_idx] if group_idx is not None and group_idx < len(row) else '')
        chuc_danh = normalize_text(row[chuc_danh_idx] if chuc_danh_idx is not None and chuc_danh_idx < len(row) else '')
        emp_groups = _normalize_employee_groups({'groups': group_raw})
        employee_code = normalize_text(row[employee_code_idx] if employee_code_idx is not None and employee_code_idx < len(row) else '')
        if not full_name:
            errors.append({'sheet': 'Sheet1-NhanSu', 'row': row_number, 'message': 'Thieu Ten.'})
        if age_value not in (None, ''):
            try:
                int(age_value)
            except (TypeError, ValueError):
                errors.append({'sheet': 'Sheet1-NhanSu', 'row': row_number, 'message': 'Tuoi khong hop le.'})
        if not emp_groups:
            errors.append({'sheet': 'Sheet1-NhanSu', 'row': row_number, 'message': 'Thieu Nhom cho nhan su.'})
        for g in emp_groups:
            if normalize_lookup(g['name']) not in group_keys:
                errors.append({'sheet': 'Sheet1-NhanSu', 'row': row_number, 'message': f'Nhom "{g["name"]}" khong co trong Sheet2.'})
        if employee_code:
            lookup_code = normalize_lookup(employee_code)
            if lookup_code in seen_employee_codes:
                errors.append({'sheet': 'Sheet1-NhanSu', 'row': row_number, 'message': f'Ma nhan vien "{employee_code}" bi trung trong file.'})
            seen_employee_codes.add(lookup_code)
        employee_items.append(
            {
                'full_name': full_name,
                'age_years': age_value,
                'profile_text': str(row[profile_idx] if profile_idx is not None and profile_idx < len(row) else '').strip(),
                'groups': emp_groups,
                'chuc_danh': chuc_danh,
                'email': normalize_text(row[email_idx] if email_idx is not None and email_idx < len(row) else ''),
                'phone': normalize_text(row[phone_idx] if phone_idx is not None and phone_idx < len(row) else ''),
                'address': normalize_text(row[address_idx] if address_idx is not None and address_idx < len(row) else ''),
                'employee_code': employee_code,
                'cccd': normalize_text(row[cccd_idx] if cccd_idx is not None and cccd_idx < len(row) else ''),
            }
        )

    if errors:
        raise ValueError(errors)

    results = []
    created_groups = 0
    created_users = 0
    updated_users = 0

    with transaction.atomic():
        for item in group_items:
            group, created = UserGroup.objects.get_or_create(
                company=company,
                name=item['name'],
                defaults={'description': item['description'], 'created_by': actor},
            )
            if not created and item['description'] and group.description != item['description']:
                group.description = item['description']
                group.save(update_fields=['description'])
            created_groups += int(created)

        group_map = _build_group_map(company)

        def _assign_groups(user, emp_groups):
            for g in emp_groups:
                grp = group_map.get(normalize_lookup(g['name']))
                if grp is None:
                    continue
                UserGroupMembership.objects.update_or_create(
                    group=grp,
                    user=user,
                    defaults={'role': g['role']},
                )

        for item in employee_items:
            local_username = default_local_username(
                email=item['email'],
                full_name=item['full_name'],
            )
            membership = _find_existing_company_user(
                company=company,
                local_username=local_username,
                email=item['email'],
                employee_code=item['employee_code'],
            )
            profile_data = {
                'age_years': item.get('age_years'),
                'so_yeu_ly_lich': item.get('profile_text'),
                'bio': item.get('profile_text'),
                'ma_nhan_vien': item.get('employee_code'),
                'cccd': item.get('cccd'),
                'so_dien_thoai': item.get('phone'),
                'dia_chi': item.get('address'),
                'chuc_danh': item.get('chuc_danh'),
            }
            if membership is None:
                created = create_company_user(
                    company=company,
                    local_username=local_username,
                    email=item['email'],
                    role=CompanyRole.COMPANY_USER,
                    full_name=item['full_name'],
                    profile_data=profile_data,
                    actor=actor,
                )
                _assign_groups(created.user, item['groups'])
                created_users += 1
                results.append({
                    'email': created.user.email,
                    'username': created.membership.local_username,
                    'status': 'created',
                })
                continue

            user = membership.user
            first_name, last_name = _split_full_name(item['full_name'])
            if item['email']:
                user.email = item['email']
            if first_name:
                user.first_name = first_name
            if last_name:
                user.last_name = last_name
            user.is_active = True
            user.save(update_fields=['email', 'first_name', 'last_name', 'is_active'])

            profile = user.profile
            profile.company = company
            profile.chuc_danh = profile_data['chuc_danh']
            profile.cccd = profile_data['cccd']
            profile.ma_nhan_vien = profile_data['ma_nhan_vien']
            profile.so_yeu_ly_lich = profile_data['so_yeu_ly_lich']
            profile.so_dien_thoai = profile_data['so_dien_thoai']
            profile.dia_chi = profile_data['dia_chi']
            profile.bio = profile_data['bio']
            try:
                profile.age_years = int(profile_data['age_years']) if profile_data['age_years'] not in (None, '') else None
            except (TypeError, ValueError):
                profile.age_years = None
            profile.save()

            membership.is_active = True
            membership.save(update_fields=['is_active'])
            _assign_groups(user, item['groups'])
            updated_users += 1
            results.append({
                'email': user.email,
                'username': membership.local_username,
                'status': 'updated',
            })

    return {
        'created_groups': created_groups,
        'created_users': created_users,
        'updated_users': updated_users,
        'total': len(employee_items),
        'results': results,
    }
