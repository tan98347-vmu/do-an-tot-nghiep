from django.db.models import Q
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from accounts.models import (
    CompanyUserMembership, Department, DepartmentMembership, UserGroupMembership,
)
from accounts.tenancy import get_user_company


# Là gì: `peer_search` là endpoint REST của nhóm tìm người dùng có thể tham gia hoặc nhận tài nguyên; nó là điểm nhận request từ client đã đi qua router và lớp permission.
# Chức năng backend: Hàm tìm kiếm và lọc các bản ghi phù hợp; đầu vào được kiểm tra hoặc chuẩn hóa trước khi tạo kết quả.
# Vai trò với UI: Kết quả được các ô tìm kiếm người dùng trên Flutter sử dụng trực tiếp để hiển thị dữ liệu, tải tệp hoặc cập nhật trạng thái thao tác.
# Mối liên hệ: Hàm phối hợp với `get_user_company`, `strip`, `request.GET.get` và trả dữ liệu về cho lớp gọi kế tiếp trong cùng luồng.
# Bản chất và tác dụng: view mỏng ở biên HTTP; chủ yếu đọc, kiểm tra hoặc biến đổi dữ liệu; chuyển kết quả thành HTTP response.
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def peer_search(request):
    """
    GET /api/users/peer-search/?q=&department=&position=
    Tra ve user trong cong ty hien tai (loai tru chinh user).
    """
    company = get_user_company(request.user)
    if company is None:
        return Response({'detail': 'Khong xac dinh duoc cong ty.'},
                        status=status.HTTP_403_FORBIDDEN)

    q = (request.GET.get('q') or '').strip()
    department_id = request.GET.get('department')
    position = (request.GET.get('position') or '').strip()

    memberships = (
        CompanyUserMembership.objects
        .filter(company=company)
        .select_related('user', 'user__profile')
        .exclude(user_id=request.user.pk)
    )
    if q:
        memberships = memberships.filter(
            Q(user__username__icontains=q)
            | Q(user__first_name__icontains=q)
            | Q(user__last_name__icontains=q)
            | Q(user__email__icontains=q)
            | Q(user__profile__chuc_danh__icontains=q)
        )
    if department_id:
        dept_user_ids = list(
            DepartmentMembership.objects
            .filter(department_id=department_id, department__company=company)
            .values_list('user_id', flat=True)
        )
        memberships = memberships.filter(user_id__in=dept_user_ids)
    if position:
        memberships = memberships.filter(
            user__profile__chuc_danh__iexact=position
        )

    memberships = memberships.order_by(
        'user__first_name', 'user__last_name', 'user__username',
    )[:50]

    user_ids = [m.user_id for m in memberships]

    dept_map = {}
    if user_ids:
        for row in (
            DepartmentMembership.objects
            .filter(user_id__in=user_ids, department__company=company)
            .select_related('department')
            .values('user_id', 'department__id', 'department__name')
        ):
            dept_map.setdefault(row['user_id'], []).append({
                'id': row['department__id'],
                'name': row['department__name'],
            })

    group_map = {}
    if user_ids:
        for row in (
            UserGroupMembership.objects
            .filter(user_id__in=user_ids, group__company=company)
            .values('user_id', 'group__name', 'role')
        ):
            group_map.setdefault(row['user_id'], []).append({
                'name': row['group__name'],
                'role': row['role'],
            })

    items = []
    for m in memberships:
        user = m.user
        profile = getattr(user, 'profile', None)
        full_name = f'{user.first_name} {user.last_name}'.strip() or user.username
        items.append({
            'id': user.pk,
            'username': user.username,
            'full_name': full_name,
            'email': user.email,
            'position': (profile.chuc_danh if profile else '') or '',
            'avatar_url': (profile.avatar.url if profile and profile.avatar else None),
            'departments': dept_map.get(user.pk, []),
            'groups': group_map.get(user.pk, []),
        })
    return Response({
        'count': len(items),
        'results': items,
    })


# Là gì: `peer_search_filters` là endpoint REST của nhóm tìm người dùng có thể tham gia hoặc nhận tài nguyên; nó là điểm nhận request từ client đã đi qua router và lớp permission.
# Chức năng backend: Hàm tìm kiếm và lọc các bản ghi phù hợp; đầu vào được kiểm tra hoặc chuẩn hóa trước khi tạo kết quả.
# Vai trò với UI: Kết quả được các ô tìm kiếm người dùng trên Flutter sử dụng trực tiếp để hiển thị dữ liệu, tải tệp hoặc cập nhật trạng thái thao tác.
# Mối liên hệ: Hàm phối hợp với `get_user_company`, `Department.objects.filter.order_by.values`, `Department.objects.filter.order_by` và trả dữ liệu về cho lớp gọi kế tiếp trong cùng luồng.
# Bản chất và tác dụng: view mỏng ở biên HTTP; chủ yếu đọc, kiểm tra hoặc biến đổi dữ liệu; chuyển kết quả thành HTTP response.
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def peer_search_filters(request):
    """
    GET /api/users/peer-search/filters/
    Tra ve danh sach phong ban + chuc danh trong cong ty de UI populate dropdown.
    """
    company = get_user_company(request.user)
    if company is None:
        return Response({'departments': [], 'positions': []})

    departments = list(
        Department.objects.filter(company=company)
        .order_by('name')
        .values('id', 'name')
    )
    positions = list(
        CompanyUserMembership.objects
        .filter(company=company)
        .exclude(user__profile__chuc_danh='')
        .exclude(user__profile__chuc_danh__isnull=True)
        .values_list('user__profile__chuc_danh', flat=True)
        .distinct()
        .order_by('user__profile__chuc_danh')
    )
    return Response({
        'departments': departments,
        'positions': [p for p in positions if p],
    })
