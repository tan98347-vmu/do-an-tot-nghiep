"""
Thuoc chuc nang nao: Bang dieu khien, Tai khoan - phong ban - nhom, Cau hinh AI, Sao luu du lieu, thong bao va ha tang route chung.
Vai tro backend: File `api/views/dashboard.py` giu hoac ho tro luong backend cho cau hinh du an, anh xa route, thong ke dashboard, quan tri du lieu nen va API chung toan he thong.
Vai tro cua no trong frontend: Cac man `/dashboard`, `/admin`, `/admin/ai-config`, `/admin/backup`, badge thong bao va shell dieu huong doc hoac chiu tac dong tu file nay.
Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `my_tennis_club.settings`, `my_tennis_club.urls`, `api/urls.py`, `api/views/admin_v.py`, `api/views/notifications.py`, `accounts.models`.
Tac dung: Giu cho cac man dieu phoi cap he thong co cung nguon cau hinh, cung route va cung so lieu nen khi frontend khoi chay.
"""

from datetime import timedelta

from django.utils import timezone
from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

# Là gì: `_scope_item` là helper nội bộ của module `dashboard.py`, phục vụ nhóm tổng hợp số liệu và trạng thái hoạt động của hệ thống.
# Chức năng backend: Hàm xử lý phần việc `scope item` theo dữ liệu và ngữ cảnh được truyền vào; đầu vào được kiểm tra hoặc chuẩn hóa trước khi tạo kết quả.
# Vai trò với UI: Flutter không gọi trực tiếp hàm này; các endpoint cùng module dùng kết quả của nó để phục vụ bảng điều khiển và các thẻ thống kê.
# Mối liên hệ: Hàm được các endpoint hoặc helper cùng module gọi khi cần cùng quy tắc xử lý.
# Bản chất và tác dụng: hàm hỗ trợ tái sử dụng trong module; chủ yếu đọc, kiểm tra hoặc biến đổi dữ liệu.
def _scope_item(key, label, description, count):
    """
    Thuoc chuc nang nao: Bang dieu khien, Tai khoan - phong ban - nhom, Cau hinh AI, Sao luu du lieu, thong bao va ha tang route chung.
    Vai tro backend: Ham `_scope_item` la helper noi bo cua lop API trong file `api/views/dashboard.py`, chiu trach nhiem dong goi mot muc pham vi thong ke truoc khi endpoint chinh phan hoi.
    Vai tro cua no trong frontend: Frontend Flutter khong goi truc tiep helper nay; endpoint cung file dung no khi giao dien can dong goi mot muc pham vi thong ke nhung khong nen tu xu ly o client.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `my_tennis_club.settings`, `my_tennis_club.urls`, `api/urls.py`, `api/views/admin_v.py`, `api/views/notifications.py`, `accounts.models`. Thuong duoc cac ham public nhu `dashboard_stats`, `dashboard_org_node_stats`, `pending_approvals_count` goi lai.
    Tac dung: Co lap rieng buoc dong goi mot muc pham vi thong ke de cac endpoint cung file tai su dung dung mot quy tac.
    """
    return {
        'key': key,
        'label': label,
        'description': description,
        'count': count,
    }

# Là gì: `_person_name` là helper nội bộ của module `dashboard.py`, phục vụ nhóm tổng hợp số liệu và trạng thái hoạt động của hệ thống.
# Chức năng backend: Hàm xử lý phần việc `person name` theo dữ liệu và ngữ cảnh được truyền vào; đầu vào được kiểm tra hoặc chuẩn hóa trước khi tạo kết quả.
# Vai trò với UI: Flutter không gọi trực tiếp hàm này; các endpoint cùng module dùng kết quả của nó để phục vụ bảng điều khiển và các thẻ thống kê.
# Mối liên hệ: Hàm phối hợp với `strip` và trả dữ liệu về cho lớp gọi kế tiếp trong cùng luồng.
# Bản chất và tác dụng: hàm hỗ trợ tái sử dụng trong module; chủ yếu đọc, kiểm tra hoặc biến đổi dữ liệu.
def _person_name(user):
    """
    Thuoc chuc nang nao: Bang dieu khien, Tai khoan - phong ban - nhom, Cau hinh AI, Sao luu du lieu, thong bao va ha tang route chung.
    Vai tro backend: Ham `_person_name` la helper noi bo cua lop API trong file `api/views/dashboard.py`, chiu trach nhiem chuan hoa ten hien thi cua nguoi dung truoc khi endpoint chinh phan hoi.
    Vai tro cua no trong frontend: Frontend Flutter khong goi truc tiep helper nay; endpoint cung file dung no khi giao dien can chuan hoa ten hien thi cua nguoi dung nhung khong nen tu xu ly o client.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `my_tennis_club.settings`, `my_tennis_club.urls`, `api/urls.py`, `api/views/admin_v.py`, `api/views/notifications.py`, `accounts.models`. Thuong duoc cac ham public nhu `dashboard_stats`, `dashboard_org_node_stats`, `pending_approvals_count` goi lai.
    Tac dung: Co lap rieng buoc chuan hoa ten hien thi cua nguoi dung de cac endpoint cung file tai su dung dung mot quy tac.
    """
    full_name = f'{user.first_name} {user.last_name}'.strip()
    return full_name or user.username

# Là gì: `_person_title` là helper nội bộ của module `dashboard.py`, phục vụ nhóm tổng hợp số liệu và trạng thái hoạt động của hệ thống.
# Chức năng backend: Hàm xử lý phần việc `person title` theo dữ liệu và ngữ cảnh được truyền vào; đầu vào được kiểm tra hoặc chuẩn hóa trước khi tạo kết quả.
# Vai trò với UI: Flutter không gọi trực tiếp hàm này; các endpoint cùng module dùng kết quả của nó để phục vụ bảng điều khiển và các thẻ thống kê.
# Mối liên hệ: Hàm phối hợp với `strip` và trả dữ liệu về cho lớp gọi kế tiếp trong cùng luồng.
# Bản chất và tác dụng: hàm hỗ trợ tái sử dụng trong module; chủ yếu đọc, kiểm tra hoặc biến đổi dữ liệu.
def _person_title(user):
    """
    Thuoc chuc nang nao: Bang dieu khien, Tai khoan - phong ban - nhom, Cau hinh AI, Sao luu du lieu, thong bao va ha tang route chung.
    Vai tro backend: Ham `_person_title` la helper noi bo cua lop API trong file `api/views/dashboard.py`, chiu trach nhiem suy ra chuc danh hien thi cua nguoi dung truoc khi endpoint chinh phan hoi.
    Vai tro cua no trong frontend: Frontend Flutter khong goi truc tiep helper nay; endpoint cung file dung no khi giao dien can suy ra chuc danh hien thi cua nguoi dung nhung khong nen tu xu ly o client.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `my_tennis_club.settings`, `my_tennis_club.urls`, `api/urls.py`, `api/views/admin_v.py`, `api/views/notifications.py`, `accounts.models`. Thuong duoc cac ham public nhu `dashboard_stats`, `dashboard_org_node_stats`, `pending_approvals_count` goi lai.
    Tac dung: Co lap rieng buoc suy ra chuc danh hien thi cua nguoi dung de cac endpoint cung file tai su dung dung mot quy tac.
    """
    try:
        title = (user.profile.chuc_danh or '').strip()
        if title:
            return title
    except Exception:
        pass

    if user.is_superuser or user.is_staff:
        return 'Quản trị viên'
    return 'Nhân viên'

# Là gì: `_build_org_structure` là helper nội bộ của module `dashboard.py`, phục vụ nhóm tổng hợp số liệu và trạng thái hoạt động của hệ thống.
# Chức năng backend: Hàm tổng hợp dữ liệu đầu vào thành cấu trúc phục vụ bước tiếp theo; đầu vào được kiểm tra hoặc chuẩn hóa trước khi tạo kết quả.
# Vai trò với UI: Flutter không gọi trực tiếp hàm này; các endpoint cùng module dùng kết quả của nó để phục vụ bảng điều khiển và các thẻ thống kê.
# Mối liên hệ: Hàm phối hợp với `UserGroupMembership.objects.select_related.filter`, `UserGroupMembership.objects.select_related`, `User.objects.filter.select_related.prefetch_related` và trả dữ liệu về cho lớp gọi kế tiếp trong cùng luồng.
# Bản chất và tác dụng: hàm hỗ trợ tái sử dụng trong module; chủ yếu đọc, kiểm tra hoặc biến đổi dữ liệu.
def _build_org_structure(company=None):
    from collections import defaultdict
    from django.contrib.auth.models import User
    from accounts.models import (
        CompanyUserMembership, CompanyRole, UserGroupMembership,
    )

    membership_qs = (
        UserGroupMembership.objects
        .select_related('group', 'user', 'user__profile')
        .filter(user__is_active=True)
    )
    user_qs = (
        User.objects
        .filter(is_active=True)
        .select_related('profile')
        .prefetch_related('group_memberships__group')
    )
    company_admin_user_ids: set[int] = set()
    if company is not None:
        membership_qs = membership_qs.filter(group__company=company)
        user_qs = user_qs.filter(company_membership__company=company)
        company_admin_user_ids = set(
            CompanyUserMembership.objects
            .filter(company=company, role=CompanyRole.COMPANY_ADMIN)
            .values_list('user_id', flat=True)
        )

    memberships = list(
        membership_qs.order_by(
            'group__name', 'role',
            'user__first_name', 'user__last_name', 'user__username',
        )
    )
    users = list(user_qs.order_by('first_name', 'last_name', 'username'))

    user_groups = defaultdict(list)
    leader_groups = defaultdict(list)
    members_by_group = defaultdict(list)
    leaders_by_group = defaultdict(list)

    for membership in memberships:
        group_name = membership.group.name
        user_groups[membership.user_id].append(group_name)
        if membership.role == 'leader':
            leader_groups[membership.user_id].append(group_name)
            leaders_by_group[membership.group_id].append(membership.user_id)
        members_by_group[membership.group_id].append(membership.user_id)

    if company is None:
        admin_ids = {user.id for user in users if user.is_superuser or user.is_staff}
    else:
        admin_ids = {user.id for user in users if user.id in company_admin_user_ids}
    leader_ids = {
        user_id for user_id, groups in leader_groups.items()
        if groups and user_id not in admin_ids
    }

    

    # Là gì: `make_person` là hàm cục bộ bên trong `_build_org_structure`, chỉ phục vụ bước xử lý nội bộ của nhóm tổng hợp số liệu và trạng thái hoạt động của hệ thống.
    # Chức năng backend: Hàm xử lý phần việc `make person` theo dữ liệu và ngữ cảnh được truyền vào; đầu vào được kiểm tra hoặc chuẩn hóa trước khi tạo kết quả.
    # Vai trò với UI: Flutter không gọi trực tiếp hàm này; các endpoint cùng module dùng kết quả của nó để phục vụ bảng điều khiển và các thẻ thống kê.
    # Mối liên hệ: Hàm phối hợp với `_person_name`, `_person_title`, `user_groups.get` và trả dữ liệu về cho lớp gọi kế tiếp trong cùng luồng.
    # Bản chất và tác dụng: callback cục bộ chỉ có hiệu lực trong hàm bao ngoài; chủ yếu đọc, kiểm tra hoặc biến đổi dữ liệu.
    def make_person(user, role):
        """
        Thuoc chuc nang nao: Bang dieu khien, Tai khoan - phong ban - nhom, Cau hinh AI, Sao luu du lieu, thong bao va ha tang route chung.
        Vai tro backend: Ham `make_person` la endpoint hoac diem vao REST cua file `api/views/dashboard.py`, chiu trach nhiem thuc hien phan xu ly chuyen trach cua symbol hien tai theo request hien tai.
        Vai tro cua no trong frontend: Frontend goi truc tiep endpoint nay khi nguoi dung can thuc hien phan xu ly chuyen trach cua symbol hien tai tu man hinh tuong ung.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `my_tennis_club.settings`, `my_tennis_club.urls`, `api/urls.py`, `api/views/admin_v.py`, `api/views/notifications.py`, `accounts.models`. Dung cung cap voi cac ham `_scope_item`, `_person_name`, `_person_title` trong module nay.
        Tac dung: Bien request thanh JSON, file hoac ma trang thai dung cho thao tac thuc hien phan xu ly chuyen trach cua symbol hien tai tren giao dien.
        """
        return {
            'id': f'user_{user.id}',
            'user_id': user.id,
            'name': _person_name(user),
            'username': user.username,
            'title': _person_title(user),
            'role': role,
            'group_names': sorted(set(user_groups.get(user.id, []))),
        }

    admins = [make_person(user, 'admin') for user in users if user.id in admin_ids]
    leaders = [make_person(user, 'leader') for user in users if user.id in leader_ids]
    employees = [
        make_person(user, 'employee')
        for user in users
        if user.id not in admin_ids and user.id not in leader_ids
    ]

    reporting_edges = []
    team_edges = []

    for leader in leaders:
        for admin in admins:
            reporting_edges.append({
                'from': admin['id'],
                'to': leader['id'],
                'type': 'reporting',
                'label': 'Điều phối',
            })

    employees_by_id = {employee['user_id']: employee for employee in employees}
    leaders_by_id = {leader['user_id']: leader for leader in leaders}

    for group_id, member_ids in members_by_group.items():
        group_leaders = [
            leaders_by_id[user_id]
            for user_id in leaders_by_group.get(group_id, [])
            if user_id in leaders_by_id
        ]
        group_employees = [
            employees_by_id[user_id]
            for user_id in member_ids
            if user_id in employees_by_id
        ]

        if not group_leaders and admins and group_employees:
            for employee in group_employees:
                reporting_edges.append({
                    'from': admins[0]['id'],
                    'to': employee['id'],
                    'type': 'reporting',
                    'label': 'Quản trị trực tiếp',
                })

        for leader in group_leaders:
            for employee in group_employees:
                reporting_edges.append({
                    'from': leader['id'],
                    'to': employee['id'],
                    'type': 'reporting',
                    'label': 'Quản lý nhóm',
                })

        sorted_group_employees = sorted(group_employees, key=lambda item: item['name'].lower())
        for index in range(len(sorted_group_employees) - 1):
            current_employee = sorted_group_employees[index]
            next_employee = sorted_group_employees[index + 1]
            shared_groups = sorted(
                set(current_employee['group_names']).intersection(next_employee['group_names'])
            )
            team_edges.append({
                'from': current_employee['id'],
                'to': next_employee['id'],
                'type': 'team',
                'label': shared_groups[0] if shared_groups else 'Cùng nhóm',
            })

    

    # Là gì: `unique_edges` là hàm cục bộ bên trong `_build_org_structure`, chỉ phục vụ bước xử lý nội bộ của nhóm tổng hợp số liệu và trạng thái hoạt động của hệ thống.
    # Chức năng backend: Hàm xử lý phần việc `unique edges` theo dữ liệu và ngữ cảnh được truyền vào; đầu vào được kiểm tra hoặc chuẩn hóa trước khi tạo kết quả.
    # Vai trò với UI: Flutter không gọi trực tiếp hàm này; các endpoint cùng module dùng kết quả của nó để phục vụ bảng điều khiển và các thẻ thống kê.
    # Mối liên hệ: Hàm phối hợp với `seen.add`, `result.append` và trả dữ liệu về cho lớp gọi kế tiếp trong cùng luồng.
    # Bản chất và tác dụng: callback cục bộ chỉ có hiệu lực trong hàm bao ngoài; chủ yếu đọc, kiểm tra hoặc biến đổi dữ liệu.
    def unique_edges(edges):
        """
        Thuoc chuc nang nao: Bang dieu khien, Tai khoan - phong ban - nhom, Cau hinh AI, Sao luu du lieu, thong bao va ha tang route chung.
        Vai tro backend: Ham `unique_edges` la endpoint hoac diem vao REST cua file `api/views/dashboard.py`, chiu trach nhiem thuc hien phan xu ly chuyen trach cua symbol hien tai theo request hien tai.
        Vai tro cua no trong frontend: Frontend goi truc tiep endpoint nay khi nguoi dung can thuc hien phan xu ly chuyen trach cua symbol hien tai tu man hinh tuong ung.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `my_tennis_club.settings`, `my_tennis_club.urls`, `api/urls.py`, `api/views/admin_v.py`, `api/views/notifications.py`, `accounts.models`. Dung cung cap voi cac ham `_scope_item`, `_person_name`, `_person_title` trong module nay.
        Tac dung: Bien request thanh JSON, file hoac ma trang thai dung cho thao tac thuc hien phan xu ly chuyen trach cua symbol hien tai tren giao dien.
        """
        seen = set()
        result = []
        for edge in edges:
            key = (edge['from'], edge['to'], edge['type'], edge['label'])
            if key in seen:
                continue
            seen.add(key)
            result.append(edge)
        return result

    reporting_edges = unique_edges(reporting_edges)
    team_edges = unique_edges(team_edges)

    if admins and not leaders and not employees:
        summary = 'Hiện hệ thống mới chỉ có tài khoản quản trị viên.'
    else:
        summary = (
            f'Cấu trúc hiện có {len(admins)} quản trị viên, '
            f'{len(leaders)} trưởng nhóm và {len(employees)} nhân viên. '
            'Sơ đồ này lấy trực tiếp từ người dùng và nhóm hiện có nên sẽ tự cập nhật khi dữ liệu thay đổi.'
        )

    return {
        'summary': summary,
        'admins': admins,
        'leaders': leaders,
        'employees': employees,
        'reporting_edges': reporting_edges,
        'team_edges': team_edges,
    }

# Là gì: `_managed_user_ids` là helper nội bộ của module `dashboard.py`, phục vụ nhóm tổng hợp số liệu và trạng thái hoạt động của hệ thống.
# Chức năng backend: Hàm xử lý phần việc `managed user ids` theo dữ liệu và ngữ cảnh được truyền vào; đầu vào được kiểm tra hoặc chuẩn hóa trước khi tạo kết quả.
# Vai trò với UI: Flutter không gọi trực tiếp hàm này; các endpoint cùng module dùng kết quả của nó để phục vụ bảng điều khiển và các thẻ thống kê.
# Mối liên hệ: Hàm phối hợp với `UserGroupMembership.objects.filter.values_list`, `UserGroupMembership.objects.filter`, `managed_ids.discard` và trả dữ liệu về cho lớp gọi kế tiếp trong cùng luồng.
# Bản chất và tác dụng: hàm hỗ trợ tái sử dụng trong module; chủ yếu đọc, kiểm tra hoặc biến đổi dữ liệu.
def _managed_user_ids(viewer):
    """
    Thuoc chuc nang nao: Bang dieu khien, Tai khoan - phong ban - nhom, Cau hinh AI, Sao luu du lieu, thong bao va ha tang route chung.
    Vai tro backend: Ham `_managed_user_ids` la helper noi bo cua lop API trong file `api/views/dashboard.py`, chiu trach nhiem tinh tap nguoi dung ma tai khoan hien tai duoc quyen theo doi truoc khi endpoint chinh phan hoi.
    Vai tro cua no trong frontend: Frontend Flutter khong goi truc tiep helper nay; endpoint cung file dung no khi giao dien can tinh tap nguoi dung ma tai khoan hien tai duoc quyen theo doi nhung khong nen tu xu ly o client.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `my_tennis_club.settings`, `my_tennis_club.urls`, `api/urls.py`, `api/views/admin_v.py`, `api/views/notifications.py`, `accounts.models`. Thuong duoc cac ham public nhu `dashboard_stats`, `dashboard_org_node_stats`, `pending_approvals_count` goi lai.
    Tac dung: Co lap rieng buoc tinh tap nguoi dung ma tai khoan hien tai duoc quyen theo doi de cac endpoint cung file tai su dung dung mot quy tac.
    """
    from accounts.models import UserGroupMembership

    leader_group_ids = list(
        UserGroupMembership.objects.filter(
            user=viewer,
            role=UserGroupMembership.ROLE_LEADER,
        ).values_list('group_id', flat=True)
    )
    if not leader_group_ids:
        return set()

    managed_ids = set(
        UserGroupMembership.objects.filter(
            group_id__in=leader_group_ids,
            role=UserGroupMembership.ROLE_MEMBER,
            user__is_active=True,
        ).values_list('user_id', flat=True)
    )
    managed_ids.discard(viewer.id)
    return managed_ids

# Là gì: `_can_view_org_node_stats` là helper nội bộ của module `dashboard.py`, phục vụ nhóm tổng hợp số liệu và trạng thái hoạt động của hệ thống.
# Chức năng backend: Hàm tổng hợp số liệu thống kê cho phạm vi hiện tại, đồng thời đánh giá quyền hoặc điều kiện cho phép thao tác; đầu vào được kiểm tra hoặc chuẩn hóa trước khi tạo kết quả.
# Vai trò với UI: Flutter không gọi trực tiếp hàm này; các endpoint cùng module dùng kết quả của nó để phục vụ bảng điều khiển và các thẻ thống kê.
# Mối liên hệ: Hàm phối hợp với `_managed_user_ids` và trả dữ liệu về cho lớp gọi kế tiếp trong cùng luồng.
# Bản chất và tác dụng: hàm hỗ trợ tái sử dụng trong module; chủ yếu đọc, kiểm tra hoặc biến đổi dữ liệu.
def _can_view_org_node_stats(viewer, target_user):
    """
    Thuoc chuc nang nao: Bang dieu khien, Tai khoan - phong ban - nhom, Cau hinh AI, Sao luu du lieu, thong bao va ha tang route chung.
    Vai tro backend: Ham `_can_view_org_node_stats` la helper noi bo cua lop API trong file `api/views/dashboard.py`, chiu trach nhiem kiem tra quyen xem thong ke cua mot nut to chuc truoc khi endpoint chinh phan hoi.
    Vai tro cua no trong frontend: Frontend Flutter khong goi truc tiep helper nay; endpoint cung file dung no khi giao dien can kiem tra quyen xem thong ke cua mot nut to chuc nhung khong nen tu xu ly o client.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `my_tennis_club.settings`, `my_tennis_club.urls`, `api/urls.py`, `api/views/admin_v.py`, `api/views/notifications.py`, `accounts.models`. Thuong duoc cac ham public nhu `dashboard_stats`, `dashboard_org_node_stats`, `pending_approvals_count` goi lai.
    Tac dung: Co lap rieng buoc kiem tra quyen xem thong ke cua mot nut to chuc de cac endpoint cung file tai su dung dung mot quy tac.
    """
    if viewer.is_superuser or viewer.is_staff:
        return True
    return target_user.id in _managed_user_ids(viewer)

# Là gì: `_dashboard_stats_legacy` là endpoint REST của nhóm tổng hợp số liệu và trạng thái hoạt động của hệ thống; nó là điểm nhận request từ client đã đi qua router và lớp permission.
# Chức năng backend: Hàm tổng hợp số liệu thống kê cho phạm vi hiện tại; đầu vào được kiểm tra hoặc chuẩn hóa trước khi tạo kết quả.
# Vai trò với UI: Kết quả được bảng điều khiển và các thẻ thống kê sử dụng trực tiếp để hiển thị dữ liệu, tải tệp hoặc cập nhật trạng thái thao tác.
# Mối liên hệ: Hàm phối hợp với `timezone.now`, `now.date`, `today.replace` và trả dữ liệu về cho lớp gọi kế tiếp trong cùng luồng.
# Bản chất và tác dụng: view mỏng ở biên HTTP; chủ yếu đọc, kiểm tra hoặc biến đổi dữ liệu; chuyển kết quả thành HTTP response.
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def _dashboard_stats_legacy(request):
    """
    Thuoc chuc nang nao: Bang dieu khien, Tai khoan - phong ban - nhom, Cau hinh AI, Sao luu du lieu, thong bao va ha tang route chung.
    Vai tro backend: Ham `_dashboard_stats_legacy` la helper noi bo cua lop API trong file `api/views/dashboard.py`, chiu trach nhiem giu nhanh tong hop so lieu cu de tuong thich du lieu dashboard truoc khi endpoint chinh phan hoi.
    Vai tro cua no trong frontend: Frontend Flutter khong goi truc tiep helper nay; endpoint cung file dung no khi giao dien can giu nhanh tong hop so lieu cu de tuong thich du lieu dashboard nhung khong nen tu xu ly o client.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `my_tennis_club.settings`, `my_tennis_club.urls`, `api/urls.py`, `api/views/admin_v.py`, `api/views/notifications.py`, `accounts.models`. Thuong duoc cac ham public nhu `dashboard_stats`, `dashboard_org_node_stats`, `pending_approvals_count` goi lai.
    Tac dung: Co lap rieng buoc giu nhanh tong hop so lieu cu de tuong thich du lieu dashboard de cac endpoint cung file tai su dung dung mot quy tac.
    """
    user = request.user
    now = timezone.now()
    today = now.date()
    month_start = today.replace(day=1)
    week_ago = today - timedelta(days=6)

    from document_templates.models import DocumentTemplate
    from documents.models import Document
    from ai_engine.models import ChatSession, ChatMessage, AIUsageLog
    from accounts.models import GlobalAIConfig
    from accounts.permissions import get_accessible_templates

    
    accessible_qs = get_accessible_templates(user)
    my_templates = DocumentTemplate.objects.filter(owner=user)

    total_templates = my_templates.count()
    templates_this_month = my_templates.filter(created_at__date__gte=month_start).count()

    
    my_docs = Document.objects.filter(owner=user)
    total_documents = my_docs.count()
    documents_this_month = my_docs.filter(created_at__date__gte=month_start).count()

    
    current_llm_model = GlobalAIConfig.get_config().ai_model
    ai_sessions = ChatSession.objects.filter(user=user).count()
    ai_messages = ChatMessage.objects.filter(session__user=user).count()
    ai_api_calls = AIUsageLog.objects.filter(user=user).count()

    
    docs_last_7 = []
    for i in range(6, -1, -1):
        d = today - timedelta(days=i)
        cnt = my_docs.filter(created_at__date=d).count()
        docs_last_7.append({'date': d.isoformat(), 'count': cnt})

    
    templates_by_visibility = []
    for vis, label in [('private', 'Riêng tư'), ('group', 'Nhóm'), ('public', 'Công khai')]:
        cnt = my_templates.filter(visibility=vis).count()
        templates_by_visibility.append({'visibility': vis, 'label': label, 'count': cnt})

    
    documents_by_status = []
    for st, label in [('draft', 'Nháp'), ('final', 'Hoàn tất'), ('archived', 'Lưu trữ')]:
        cnt = my_docs.filter(status=st).count()
        documents_by_status.append({'status': st, 'label': label, 'count': cnt})

    
    recent_templates = list(my_templates.order_by('-created_at')[:5].values(
        'id', 'title', 'status', 'visibility', 'created_at'
    ))
    recent_documents = list(my_docs.order_by('-created_at')[:5].values(
        'id', 'title', 'status', 'created_at'
    ))

    return Response({
        'total_templates': total_templates,
        'total_documents': total_documents,
        'templates_this_month': templates_this_month,
        'documents_this_month': documents_this_month,
        'current_llm_model': current_llm_model,
        'ai_api_calls': ai_api_calls,
        'ai_sessions': ai_sessions,
        'ai_messages': ai_messages,
        'docs_last_7_days': docs_last_7,
        'templates_by_visibility': templates_by_visibility,
        'documents_by_status': documents_by_status,
        'recent_templates': recent_templates,
        'recent_documents': recent_documents,
    })

# Là gì: `dashboard_stats` là endpoint REST của nhóm tổng hợp số liệu và trạng thái hoạt động của hệ thống; nó là điểm nhận request từ client đã đi qua router và lớp permission.
# Chức năng backend: Hàm tổng hợp số liệu thống kê cho phạm vi hiện tại; đầu vào được kiểm tra hoặc chuẩn hóa trước khi tạo kết quả.
# Vai trò với UI: Kết quả được bảng điều khiển và các thẻ thống kê sử dụng trực tiếp để hiển thị dữ liệu, tải tệp hoặc cập nhật trạng thái thao tác.
# Mối liên hệ: Hàm phối hợp với `timezone.localdate`, `today.replace`, `get_user_company` và trả dữ liệu về cho lớp gọi kế tiếp trong cùng luồng.
# Bản chất và tác dụng: view mỏng ở biên HTTP; chủ yếu đọc, kiểm tra hoặc biến đổi dữ liệu; chuyển kết quả thành HTTP response.
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_stats(request):
    """
    Thuoc chuc nang nao: Bang dieu khien, Tai khoan - phong ban - nhom, Cau hinh AI, Sao luu du lieu, thong bao va ha tang route chung.
    Vai tro backend: Ham `dashboard_stats` la endpoint hoac diem vao REST cua file `api/views/dashboard.py`, chiu trach nhiem tong hop bo so lieu chinh cho dashboard theo request hien tai.
    Vai tro cua no trong frontend: Frontend goi truc tiep endpoint nay khi nguoi dung can tong hop bo so lieu chinh cho dashboard tu man hinh tuong ung.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `my_tennis_club.settings`, `my_tennis_club.urls`, `api/urls.py`, `api/views/admin_v.py`, `api/views/notifications.py`, `accounts.models`. Dung cung cap voi cac ham `_scope_item`, `_person_name`, `_person_title` trong module nay.
    Tac dung: Bien request thanh JSON, file hoac ma trang thai dung cho thao tac tong hop bo so lieu chinh cho dashboard tren giao dien.
    """
    user = request.user
    today = timezone.localdate()
    month_start = today.replace(day=1)

    from accounts.models import CompanyUserMembership, GlobalAIConfig
    from accounts.permissions import get_accessible_documents, get_accessible_templates
    from accounts.tenancy import get_user_company
    from ai_engine.models import AIUsageLog, ChatMessage, ChatSession
    from document_templates.models import DocumentTemplate
    from documents.models import Document

    current_company = get_user_company(user)
    company_user_ids: list[int] = []
    if current_company is not None:
        company_user_ids = list(
            CompanyUserMembership.objects
            .filter(company=current_company)
            .values_list('user_id', flat=True)
        )

    memberships_qs = user.group_memberships.select_related('group')
    if current_company is not None:
        memberships_qs = memberships_qs.filter(group__company=current_company)
    memberships = list(memberships_qs)
    group_names = [membership.group.name for membership in memberships]
    group_count = len(group_names)
    leader_group_count = sum(1 for membership in memberships if membership.role == 'leader')

    accessible_templates = get_accessible_templates(user).distinct()
    accessible_documents = get_accessible_documents(user).distinct()
    my_templates = accessible_templates.filter(owner=user).distinct()
    my_documents = accessible_documents.filter(owner=user).distinct()

    template_structure = [
        _scope_item(
            'personal',
            'Cá nhân sở hữu',
            'Mẫu do bạn tạo, chỉnh sửa hoặc đang phụ trách.',
            my_templates.count(),
        ),
        _scope_item(
            'private_scope',
            'Riêng tư / cấp phát',
            'Mẫu private được cấp riêng cho bạn hoặc nằm ngoài phạm vi sở hữu của bạn.',
            accessible_templates.filter(visibility='private').exclude(owner=user).distinct().count(),
        ),
        _scope_item(
            'team',
            'Không gian nhóm',
            'Mẫu chia sẻ theo nhóm, phòng ban mà bạn đang tham gia.',
            accessible_templates.filter(visibility='group').exclude(owner=user).distinct().count(),
        ),
        _scope_item(
            'organization',
            'Toàn tổ chức',
            'Mẫu công khai, đã được duyệt và sẵn sàng cho tổ chức sử dụng.',
            accessible_templates.filter(visibility='public').exclude(owner=user).distinct().count(),
        ),
    ]

    document_structure = [
        _scope_item(
            'personal',
            'Cá nhân sở hữu',
            'Văn bản do bạn tạo hoặc đang quản lý trực tiếp.',
            my_documents.count(),
        ),
        _scope_item(
            'private_scope',
            'Riêng tư / cấp phát',
            'Văn bản private ngoài sở hữu của bạn chỉ hiển thị nếu tài khoản có quyền quản trị.',
            accessible_documents.filter(visibility='private').exclude(owner=user).distinct().count(),
        ),
        _scope_item(
            'team',
            'Không gian nhóm',
            'Văn bản chia sẻ trong nhóm, đơn vị và đã được kích hoạt.',
            accessible_documents.filter(visibility='group').exclude(owner=user).distinct().count(),
        ),
        _scope_item(
            'organization',
            'Toàn tổ chức',
            'Văn bản công khai mà tài khoản hiện có thể tra cứu.',
            accessible_documents.filter(visibility='public').exclude(owner=user).distinct().count(),
        ),
    ]

    monthly_document_structure = [
        _scope_item(
            'personal',
            'Cá nhân trong tháng',
            'Văn bản bạn tạo từ ngày đầu tháng đến hiện tại.',
            my_documents.filter(created_at__date__gte=month_start).count(),
        ),
        _scope_item(
            'private_scope',
            'Private trong tháng',
            'Văn bản private phát sinh trong tháng, chỉ có ý nghĩa với góc nhìn quản trị.',
            accessible_documents.filter(
                created_at__date__gte=month_start,
                visibility='private',
            ).exclude(owner=user).distinct().count(),
        ),
        _scope_item(
            'team',
            'Nhóm trong tháng',
            'Văn bản nhóm/phòng ban có phát sinh trong tháng và bạn có thể truy cập.',
            accessible_documents.filter(
                created_at__date__gte=month_start,
                visibility='group',
            ).exclude(owner=user).distinct().count(),
        ),
        _scope_item(
            'organization',
            'Tổ chức trong tháng',
            'Văn bản công khai của tổ chức được tạo trong tháng hiện tại.',
            accessible_documents.filter(
                created_at__date__gte=month_start,
                visibility='public',
            ).exclude(owner=user).distinct().count(),
        ),
    ]

    total_templates = sum(item['count'] for item in template_structure)
    total_documents = sum(item['count'] for item in document_structure)
    documents_this_month = sum(item['count'] for item in monthly_document_structure)
    templates_this_month = my_templates.filter(created_at__date__gte=month_start).count()

    current_llm_model = GlobalAIConfig.get_config().ai_model
    chat_session_qs = ChatSession.objects.filter(user=user)
    chat_message_qs = ChatMessage.objects.filter(session__user=user)
    ai_usage_qs = AIUsageLog.objects.filter(user=user)
    if current_company is not None:
        chat_session_qs = chat_session_qs.filter(company=current_company)
        chat_message_qs = chat_message_qs.filter(session__company=current_company)
    ai_sessions = chat_session_qs.count()
    ai_messages = chat_message_qs.count()
    ai_api_calls = ai_usage_qs.count()

    docs_last_7 = []
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        docs_last_7.append({
            'date': day.isoformat(),
            'count': accessible_documents.filter(created_at__date=day).count(),
        })

    templates_by_visibility = [
        {'visibility': item['key'], 'label': item['label'], 'count': item['count']}
        for item in template_structure
    ]
    documents_by_status = []
    for st, label in [('draft', 'Nháp'), ('final', 'Hoàn tất'), ('archived', 'Lưu trữ')]:
        documents_by_status.append({
            'status': st,
            'label': label,
            'count': accessible_documents.filter(status=st).count(),
        })

    recent_templates = list(accessible_templates.order_by('-updated_at')[:5].values(
        'id', 'title', 'status', 'visibility', 'created_at'
    ))
    recent_documents = list(accessible_documents.order_by('-updated_at')[:5].values(
        'id', 'title', 'status', 'created_at'
    ))

    if user.is_superuser:
        role_label = 'Quản trị viên'
        org_summary = (
            'Góc nhìn quản trị: dashboard tách rõ tài nguyên cá nhân, private, nhóm và toàn tổ chức.'
        )
    elif any(membership.role == 'leader' for membership in memberships):
        role_label = 'Trưởng nhóm'
        org_summary = (
            'Góc nhìn trưởng nhóm: bạn thấy tài nguyên cá nhân, không gian nhóm phụ trách và tài nguyên toàn tổ chức.'
        )
    elif group_names:
        role_label = 'Thành viên nhóm'
        org_summary = (
            'Góc nhìn đơn vị: bạn theo dõi tài nguyên của bạn, tài nguyên nhóm tham gia và các thành phần công khai của tổ chức.'
        )
    else:
        role_label = 'Người dùng'
        org_summary = (
            'Góc nhìn cá nhân: dashboard nhấn mạnh tài nguyên của bạn và những gì tổ chức chia sẻ cho bạn.'
        )

    org_structure = _build_org_structure(company=current_company)

    return Response({
        'total_templates': total_templates,
        'total_documents': total_documents,
        'templates_this_month': templates_this_month,
        'documents_this_month': documents_this_month,
        'current_llm_model': current_llm_model,
        'ai_api_calls': ai_api_calls,
        'ai_sessions': ai_sessions,
        'ai_messages': ai_messages,
        'docs_last_7_days': docs_last_7,
        'templates_by_visibility': templates_by_visibility,
        'documents_by_status': documents_by_status,
        'recent_templates': recent_templates,
        'recent_documents': recent_documents,
        'org_context': {
            'role_label': role_label,
            'group_names': group_names,
            'group_count': group_count,
            'leader_group_count': leader_group_count,
            'summary': org_summary,
            'can_approve_pending': bool(
                user.is_superuser or any(membership.role == 'leader' for membership in memberships)
            ),
        },
        'template_structure': {
            'total': total_templates,
            'summary': 'Tổng số mẫu văn bản bạn có thể khai thác theo cấu trúc của tổ chức.',
            'items': template_structure,
        },
        'document_structure': {
            'total': total_documents,
            'summary': 'Tổng số văn bản bạn đang nhìn thấy theo từng tầng tài nguyên trong hệ thống.',
            'items': document_structure,
        },
        'monthly_document_structure': {
            'total': documents_this_month,
            'summary': 'Văn bản phát sinh trong tháng hiện tại, tách theo các tầng của tổ chức.',
            'items': monthly_document_structure,
        },
        'ai_overview': {
            'current_model': current_llm_model,
            'sessions': ai_sessions,
            'messages': ai_messages,
            'api_calls': ai_api_calls,
            'summary': (
                'Phiên AI là dữ liệu cá nhân của tài khoản hiện tại, nhưng đang sử dụng cấu hình mô hình chung của tổ chức.'
            ),
        },
        'org_structure': org_structure,
    })

# Là gì: `dashboard_org_node_stats` là endpoint REST của nhóm tổng hợp số liệu và trạng thái hoạt động của hệ thống; nó là điểm nhận request từ client đã đi qua router và lớp permission.
# Chức năng backend: Hàm tổng hợp số liệu thống kê cho phạm vi hiện tại; đầu vào được kiểm tra hoặc chuẩn hóa trước khi tạo kết quả.
# Vai trò với UI: Kết quả được bảng điều khiển và các thẻ thống kê sử dụng trực tiếp để hiển thị dữ liệu, tải tệp hoặc cập nhật trạng thái thao tác.
# Mối liên hệ: Hàm phối hợp với `get_user_company`, `User.objects.select_related.filter`, `User.objects.select_related` và trả dữ liệu về cho lớp gọi kế tiếp trong cùng luồng.
# Bản chất và tác dụng: view mỏng ở biên HTTP; chủ yếu đọc, kiểm tra hoặc biến đổi dữ liệu; chuyển kết quả thành HTTP response.
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_org_node_stats(request, user_id):
    """
    Thuoc chuc nang nao: Bang dieu khien, Tai khoan - phong ban - nhom, Cau hinh AI, Sao luu du lieu, thong bao va ha tang route chung.
    Vai tro backend: Ham `dashboard_org_node_stats` la endpoint hoac diem vao REST cua file `api/views/dashboard.py`, chiu trach nhiem tra thong ke chi tiet cho mot nut tren so do to chuc theo request hien tai.
    Vai tro cua no trong frontend: Frontend goi truc tiep endpoint nay khi nguoi dung can tra thong ke chi tiet cho mot nut tren so do to chuc tu man hinh tuong ung.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `my_tennis_club.settings`, `my_tennis_club.urls`, `api/urls.py`, `api/views/admin_v.py`, `api/views/notifications.py`, `accounts.models`. Dung cung cap voi cac ham `_scope_item`, `_person_name`, `_person_title` trong module nay.
    Tac dung: Bien request thanh JSON, file hoac ma trang thai dung cho thao tac tra thong ke chi tiet cho mot nut tren so do to chuc tren giao dien.
    """
    from django.contrib.auth.models import User
    from ai_engine.models import ChatMessage
    from accounts.tenancy import get_user_company
    from document_templates.models import DocumentTemplate
    from documents.models import Document

    viewer_company = get_user_company(request.user)

    target_qs = User.objects.select_related('profile').filter(pk=user_id, is_active=True)
    if viewer_company is not None and not request.user.is_superuser:
        target_qs = target_qs.filter(company_membership__company=viewer_company)
    target_user = get_object_or_404(target_qs)

    if not _can_view_org_node_stats(request.user, target_user):
        return Response(
            {'detail': 'Ban khong co quyen xem thong tin cua nguoi dung nay.'},
            status=403,
        )

    today = timezone.localdate()
    month_start = today.replace(day=1)
    user_templates = DocumentTemplate.objects.filter(owner=target_user)
    user_documents = Document.objects.filter(owner=target_user)
    user_messages = ChatMessage.objects.filter(
        session__user=target_user,
        role=ChatMessage.ROLE_USER,
    )
    if viewer_company is not None:
        user_templates = user_templates.filter(company=viewer_company)
        user_documents = user_documents.filter(company=viewer_company)
        user_messages = user_messages.filter(session__company=viewer_company)

    activity_last_7_days = []
    for offset in range(6, -1, -1):
        day = today - timedelta(days=offset)
        day_total = (
            user_templates.filter(created_at__date=day).count()
            + user_documents.filter(created_at__date=day).count()
            + user_messages.filter(created_at__date=day).count()
        )
        activity_last_7_days.append({
            'date': day.isoformat(),
            'count': day_total,
        })

    full_name = f'{target_user.first_name} {target_user.last_name}'.strip() or target_user.username
    try:
        title = (target_user.profile.chuc_danh or '').strip()
    except Exception:
        title = ''

    return Response({
        'user_id': target_user.id,
        'name': full_name,
        'username': target_user.username,
        'title': title,
        'template_count': user_templates.count(),
        'document_count': user_documents.count(),
        'documents_this_month': user_documents.filter(created_at__date__gte=month_start).count(),
        'activity_last_7_days': activity_last_7_days,
        'activity_total': sum(item['count'] for item in activity_last_7_days),
    })

# Là gì: `pending_approvals_count` là endpoint REST của nhóm tổng hợp số liệu và trạng thái hoạt động của hệ thống; nó là điểm nhận request từ client đã đi qua router và lớp permission.
# Chức năng backend: Hàm đếm số bản ghi thỏa điều kiện; đầu vào được kiểm tra hoặc chuẩn hóa trước khi tạo kết quả.
# Vai trò với UI: Kết quả được bảng điều khiển và các thẻ thống kê sử dụng trực tiếp để hiển thị dữ liệu, tải tệp hoặc cập nhật trạng thái thao tác.
# Mối liên hệ: Hàm phối hợp với `UserGroupMembership.objects.filter.values_list`, `UserGroupMembership.objects.filter`, `DocumentTemplate.objects.none` và trả dữ liệu về cho lớp gọi kế tiếp trong cùng luồng.
# Bản chất và tác dụng: view mỏng ở biên HTTP; chủ yếu đọc, kiểm tra hoặc biến đổi dữ liệu; chuyển kết quả thành HTTP response.
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def pending_approvals_count(request):
    """
    Thuoc chuc nang nao: Bang dieu khien, Tai khoan - phong ban - nhom, Cau hinh AI, Sao luu du lieu, thong bao va ha tang route chung.
    Vai tro backend: Ham `pending_approvals_count` la endpoint hoac diem vao REST cua file `api/views/dashboard.py`, chiu trach nhiem tong hop badge cho duyet cho shell va dashboard theo request hien tai.
    Vai tro cua no trong frontend: Frontend goi truc tiep endpoint nay khi nguoi dung can tong hop badge cho duyet cho shell va dashboard tu man hinh tuong ung.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `my_tennis_club.settings`, `my_tennis_club.urls`, `api/urls.py`, `api/views/admin_v.py`, `api/views/notifications.py`, `accounts.models`. Dung cung cap voi cac ham `_scope_item`, `_person_name`, `_person_title` trong module nay.
    Tac dung: Bien request thanh JSON, file hoac ma trang thai dung cho thao tac tong hop badge cho duyet cho shell va dashboard tren giao dien.
    """
    from accounts.models import UserGroupMembership
    from document_templates.models import (
        DocumentTemplate,
        STATUS_PENDING,
        STATUS_PENDING_LEADER,
    )
    from documents.models import (
        Document,
        SHARE_PENDING_ADMIN,
        SHARE_PENDING_LEADER,
    )
    from prompts.models import (
        Prompt,
        PROMPT_STATUS_PENDING,
        PROMPT_STATUS_PENDING_LEADER,
    )

    leader_gids = list(
        UserGroupMembership.objects.filter(user=request.user, role='leader')
        .values_list('group_id', flat=True)
    )

    template_qs = DocumentTemplate.objects.none()
    if request.user.is_superuser:
        template_qs = DocumentTemplate.objects.filter(
            status__in=[STATUS_PENDING, STATUS_PENDING_LEADER]
        )
    if leader_gids:
        leader_template_qs = DocumentTemplate.objects.filter(
            status=STATUS_PENDING_LEADER,
            group_id__in=leader_gids,
        )
        template_qs = (
            (template_qs | leader_template_qs)
            if request.user.is_superuser
            else leader_template_qs
        )

    document_qs = Document.objects.none()
    if request.user.is_superuser:
        document_qs = Document.objects.filter(share_status=SHARE_PENDING_ADMIN)
    if leader_gids:
        leader_document_qs = Document.objects.filter(
            share_status=SHARE_PENDING_LEADER,
            group_id__in=leader_gids,
        )
        document_qs = (
            (document_qs | leader_document_qs)
            if request.user.is_superuser
            else leader_document_qs
        )

    prompt_qs = Prompt.objects.none()
    if request.user.is_superuser:
        prompt_qs = Prompt.objects.filter(
            status__in=[PROMPT_STATUS_PENDING, PROMPT_STATUS_PENDING_LEADER]
        )
    if leader_gids:
        leader_prompt_qs = Prompt.objects.filter(
            status=PROMPT_STATUS_PENDING_LEADER,
            group_id__in=leader_gids,
        )
        prompt_qs = (
            (prompt_qs | leader_prompt_qs)
            if request.user.is_superuser
            else leader_prompt_qs
        )

    # Peer share pending — viewer la leader cua owner (qua group cua owner).
    template_peer_qs = DocumentTemplate.objects.none()
    document_peer_qs = Document.objects.none()
    prompt_peer_qs = Prompt.objects.none()
    if leader_gids or request.user.is_superuser:
        owner_ids_under_leader = list(
            UserGroupMembership.objects.filter(group_id__in=leader_gids)
            .values_list('user_id', flat=True).distinct()
        )
        if request.user.is_superuser:
            template_peer_qs = DocumentTemplate.objects.filter(
                peer_share_status=DocumentTemplate.PEER_SHARE_PENDING_LEADER,
            )
            document_peer_qs = Document.objects.filter(
                peer_share_status=Document.PEER_SHARE_PENDING_LEADER,
            )
            prompt_peer_qs = Prompt.objects.filter(
                peer_share_status=Prompt.PEER_SHARE_PENDING_LEADER,
            )
        if owner_ids_under_leader:
            tpl_leader_peer = DocumentTemplate.objects.filter(
                peer_share_status=DocumentTemplate.PEER_SHARE_PENDING_LEADER,
                owner_id__in=owner_ids_under_leader,
            )
            doc_leader_peer = Document.objects.filter(
                peer_share_status=Document.PEER_SHARE_PENDING_LEADER,
                owner_id__in=owner_ids_under_leader,
            )
            prm_leader_peer = Prompt.objects.filter(
                peer_share_status=Prompt.PEER_SHARE_PENDING_LEADER,
                owner_id__in=owner_ids_under_leader,
            )
            if request.user.is_superuser:
                template_peer_qs = template_peer_qs | tpl_leader_peer
                document_peer_qs = document_peer_qs | doc_leader_peer
                prompt_peer_qs = prompt_peer_qs | prm_leader_peer
            else:
                template_peer_qs = tpl_leader_peer
                document_peer_qs = doc_leader_peer
                prompt_peer_qs = prm_leader_peer

    templates = template_qs.distinct().count()
    documents = document_qs.distinct().count()
    prompts_count = prompt_qs.distinct().count()
    template_peer = template_peer_qs.distinct().count()
    document_peer = document_peer_qs.distinct().count()
    prompt_peer = prompt_peer_qs.distinct().count()

    total = templates + documents + prompts_count + template_peer + document_peer + prompt_peer

    return Response({
        'templates': templates,
        'documents': documents,
        'prompts': prompts_count,
        'template_peer': template_peer,
        'document_peer': document_peer,
        'prompt_peer': prompt_peer,
        'total': total,
    })
