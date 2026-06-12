"""
API endpoints thong nhat cho co che chia se moi (4 pham vi x 3 quyen).

URL pattern (xem api/urls.py):
  GET    <entity>/<pk>/shares/                       -> list grants
  POST   <entity>/<pk>/shares/                       -> create grant
  PATCH  <entity>/<pk>/shares/<grant_id>/            -> update permission/scope
  DELETE <entity>/<pk>/shares/<grant_id>/            -> revoke grant
  POST   <entity>/<pk>/shares/<grant_id>/submit/     -> submit draft -> pending
  POST   <entity>/<pk>/shares/<grant_id>/approve/    -> leader/admin duyet
  POST   <entity>/<pk>/shares/<grant_id>/reject/     -> leader/admin tu choi

  GET    shares/pending/                             -> inbox duyet (ca 3 entity)
  GET    shares/shared-with-me/                      -> resource share cho user (ca 3 entity)

`<entity>` ∈ {templates, documents, prompts}.
"""

from __future__ import annotations

from django.apps import apps
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from accounts.tenancy import get_user_company, is_platform_admin
from api.serializers.sharing import (
    ShareGrantCreateSerializer,
    ShareGrantSerializer,
)
from sharing import services
from sharing.constants import (
    APPROVAL_DRAFT,
    APPROVAL_PENDING_ADMIN,
    APPROVAL_PENDING_LEADER,
    ENTITY_TYPE_TO_MODEL,
    MODEL_TO_ENTITY_TYPE,
)
from sharing.models import ShareGrant


# Là gì: `_resolve_model` là helper nội bộ của module `sharing.py`, phục vụ nhóm chia sẻ tài nguyên và quản lý phạm vi truy cập.
# Chức năng backend: Hàm xác định đối tượng hoặc cấu hình hiệu lực từ ngữ cảnh hiện tại; đầu vào được kiểm tra hoặc chuẩn hóa trước khi tạo kết quả.
# Vai trò với UI: Flutter không gọi trực tiếp hàm này; các endpoint cùng module dùng kết quả của nó để phục vụ các hộp thoại và màn hình chia sẻ.
# Mối liên hệ: Hàm phối hợp với `ENTITY_TYPE_TO_MODEL.get`, `apps.get_model` và trả dữ liệu về cho lớp gọi kế tiếp trong cùng luồng.
# Bản chất và tác dụng: hàm hỗ trợ tái sử dụng trong module; chủ yếu đọc, kiểm tra hoặc biến đổi dữ liệu.
def _resolve_model(entity_type: str):
    mapping = ENTITY_TYPE_TO_MODEL.get(entity_type)
    if not mapping:
        return None
    app_label, model_name = mapping
    try:
        return apps.get_model(app_label, model_name)
    except LookupError:
        return None


# Là gì: `_get_resource_or_404` là helper nội bộ của module `sharing.py`, phục vụ nhóm chia sẻ tài nguyên và quản lý phạm vi truy cập.
# Chức năng backend: Hàm đọc và trả về dữ liệu cần thiết; đầu vào được kiểm tra hoặc chuẩn hóa trước khi tạo kết quả.
# Vai trò với UI: Flutter không gọi trực tiếp hàm này; các endpoint cùng module dùng kết quả của nó để phục vụ các hộp thoại và màn hình chia sẻ.
# Mối liên hệ: Hàm phối hợp với `_resolve_model`, `get_object_or_404` và trả dữ liệu về cho lớp gọi kế tiếp trong cùng luồng.
# Bản chất và tác dụng: hàm hỗ trợ tái sử dụng trong module; chủ yếu đọc, kiểm tra hoặc biến đổi dữ liệu.
def _get_resource_or_404(entity_type: str, pk: int):
    model_cls = _resolve_model(entity_type)
    if model_cls is None:
        return None
    return get_object_or_404(model_cls, pk=pk)


# Là gì: `_entity_type_for_grant` là helper nội bộ của module `sharing.py`, phục vụ nhóm chia sẻ tài nguyên và quản lý phạm vi truy cập.
# Chức năng backend: Hàm xử lý phần việc `entity type for grant` theo dữ liệu và ngữ cảnh được truyền vào; đầu vào được kiểm tra hoặc chuẩn hóa trước khi tạo kết quả.
# Vai trò với UI: Flutter không gọi trực tiếp hàm này; các endpoint cùng module dùng kết quả của nó để phục vụ các hộp thoại và màn hình chia sẻ.
# Mối liên hệ: Hàm phối hợp với `MODEL_TO_ENTITY_TYPE.get`, `ct.model.lower`, `join` và trả dữ liệu về cho lớp gọi kế tiếp trong cùng luồng.
# Bản chất và tác dụng: hàm hỗ trợ tái sử dụng trong module; chủ yếu đọc, kiểm tra hoặc biến đổi dữ liệu.
def _entity_type_for_grant(grant: ShareGrant) -> str | None:
    ct = grant.content_type
    return MODEL_TO_ENTITY_TYPE.get((ct.app_label, ct.model.lower())) or MODEL_TO_ENTITY_TYPE.get(
        (ct.app_label, ''.join(p.capitalize() for p in ct.model.split('_')))
    )


# Là gì: `_is_owner_or_admin` là helper nội bộ của module `sharing.py`, phục vụ nhóm chia sẻ tài nguyên và quản lý phạm vi truy cập.
# Chức năng backend: Hàm đánh giá một điều kiện và trả về kết quả boolean; đầu vào được kiểm tra hoặc chuẩn hóa trước khi tạo kết quả.
# Vai trò với UI: Flutter không gọi trực tiếp hàm này; các endpoint cùng module dùng kết quả của nó để phục vụ các hộp thoại và màn hình chia sẻ.
# Mối liên hệ: Hàm phối hợp với `is_platform_admin`, `services.can` và trả dữ liệu về cho lớp gọi kế tiếp trong cùng luồng.
# Bản chất và tác dụng: hàm hỗ trợ tái sử dụng trong module; chủ yếu đọc, kiểm tra hoặc biến đổi dữ liệu.
def _is_owner_or_admin(user, resource) -> bool:
    owner_id = getattr(resource, 'owner_id', None) or getattr(resource, 'created_by_id', None)
    if owner_id is not None and owner_id == user.pk:
        return True
    if user.is_superuser or is_platform_admin(user):
        return True
    # Nguoi duoc chia se voi quyen TOAN QUYEN (delete) duoc quan ly va chia se tiep
    # nhu chu so huu. Nguoi chi duoc 'view' hoac 'edit' thi can(...,'delete')=False
    # nen KHONG the chia se tiep cho nhom/dong nghiep khac.
    try:
        if services.can(user, resource, 'delete'):
            return True
    except Exception:
        pass
    return False


# Là gì: `shareable_group_list` là endpoint REST của nhóm chia sẻ tài nguyên và quản lý phạm vi truy cập; nó là điểm nhận request từ client đã đi qua router và lớp permission.
# Chức năng backend: Hàm truy vấn và trả về danh sách dữ liệu phù hợp; đầu vào được kiểm tra hoặc chuẩn hóa trước khi tạo kết quả.
# Vai trò với UI: Kết quả được các hộp thoại và màn hình chia sẻ sử dụng trực tiếp để hiển thị dữ liệu, tải tệp hoặc cập nhật trạng thái thao tác.
# Mối liên hệ: Hàm phối hợp với `get_user_company`, `UserGroup.objects.filter`, `groups.filter` và trả dữ liệu về cho lớp gọi kế tiếp trong cùng luồng.
# Bản chất và tác dụng: view mỏng ở biên HTTP; chủ yếu đọc, kiểm tra hoặc biến đổi dữ liệu; chuyển kết quả thành HTTP response.
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def shareable_group_list(request):
    from accounts.models import UserGroup, UserGroupMembership

    company = get_user_company(request.user)
    # Nghiep vu: chi chia se toi NHOM MA NGUOI DUNG LA THANH VIEN.
    groups = UserGroup.objects.filter(memberships__user=request.user)
    if company is not None:
        groups = groups.filter(company=company)
    groups = groups.order_by('name').distinct()

    role_by_group_id = dict(
        UserGroupMembership.objects.filter(
            user=request.user,
            group_id__in=groups.values_list('pk', flat=True),
        ).values_list('group_id', 'role')
    )
    return Response(
        {
            'groups': [
                {
                    'id': group.pk,
                    'name': group.name,
                    'description': group.description,
                    'my_role': role_by_group_id.get(group.pk, ''),
                }
                for group in groups
            ]
        }
    )


# ============================================================================
# Per-resource endpoints
# ============================================================================

# vd: POST body hợp lệ -> tạo bản ghi, trả 201.
# Là gì: `shares_list_create` là endpoint REST của nhóm chia sẻ tài nguyên và quản lý phạm vi truy cập; nó là điểm nhận request từ client đã đi qua router và lớp permission.
# Chức năng backend: Hàm truy vấn và trả về danh sách dữ liệu phù hợp, đồng thời kiểm tra đầu vào và tạo dữ liệu mới; đầu vào được kiểm tra hoặc chuẩn hóa trước khi tạo kết quả.
# Vai trò với UI: Kết quả được các hộp thoại và màn hình chia sẻ sử dụng trực tiếp để hiển thị dữ liệu, tải tệp hoặc cập nhật trạng thái thao tác.
# Mối liên hệ: Hàm phối hợp với `_get_resource_or_404`, `_is_owner_or_admin`, `services.grants_listed_for_owner` và trả dữ liệu về cho lớp gọi kế tiếp trong cùng luồng.
# Bản chất và tác dụng: view mỏng ở biên HTTP; chủ yếu đọc, kiểm tra hoặc biến đổi dữ liệu; chuyển kết quả thành HTTP response.
@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def shares_list_create(request, entity_type: str, pk: int):
    """GET: list grants; POST: create grant."""
    resource = _get_resource_or_404(entity_type, pk)
    if resource is None:
        return Response({'detail': 'Entity type khong hop le'}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        # Owner thay tat ca; user khac thay grants ma ho duoc huong
        if _is_owner_or_admin(request.user, resource):
            grants = services.grants_listed_for_owner(resource)
        else:
            grants = ShareGrant.objects.for_resource(resource).for_user(request.user)
        data = ShareGrantSerializer(grants, many=True).data
        return Response({'grants': data})

    # POST: create
    if not _is_owner_or_admin(request.user, resource):
        return Response({'detail': 'Chi owner hoac admin duoc tao grant.'}, status=status.HTTP_403_FORBIDDEN)

    serializer = ShareGrantCreateSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data

    target_user = None
    target_group = None
    if data.get('target_user'):
        from django.contrib.auth import get_user_model
        from accounts.models import CompanyUserMembership

        User = get_user_model()
        target_user = get_object_or_404(User, pk=data['target_user'])
        # Validate target_user cung company voi owner
        owner_company = get_user_company(request.user)
        if owner_company is not None:
            in_company = CompanyUserMembership.objects.filter(
                company=owner_company, user=target_user
            ).exists()
            if not in_company:
                return Response(
                    {'detail': 'Target user khong thuoc cong ty.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
    if data.get('target_group'):
        from accounts.models import UserGroup

        target_group = get_object_or_404(UserGroup, pk=data['target_group'])
        owner_company = get_user_company(request.user)
        if owner_company is not None and getattr(target_group, 'company_id', None) != owner_company.id:
            return Response(
                {'detail': 'Target group khong thuoc cong ty hien tai.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

    try:
        grant = services.create_grant(
            resource=resource,
            scope=data['scope'],
            permission_level=data['permission_level'],
            target_user=target_user,
            target_group=target_group,
            actor=request.user,
            auto_submit=data.get('auto_submit', True),
        )
    except (PermissionError, ValueError) as e:
        return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    return Response(ShareGrantSerializer(grant).data, status=status.HTTP_201_CREATED)


# Là gì: `shares_detail` là endpoint REST của nhóm chia sẻ tài nguyên và quản lý phạm vi truy cập; nó là điểm nhận request từ client đã đi qua router và lớp permission.
# Chức năng backend: Hàm đọc hoặc xử lý một bản ghi cụ thể; đầu vào được kiểm tra hoặc chuẩn hóa trước khi tạo kết quả.
# Vai trò với UI: Kết quả được các hộp thoại và màn hình chia sẻ sử dụng trực tiếp để hiển thị dữ liệu, tải tệp hoặc cập nhật trạng thái thao tác.
# Mối liên hệ: Hàm phối hợp với `_get_resource_or_404`, `get_object_or_404`, `_is_owner_or_admin` và trả dữ liệu về cho lớp gọi kế tiếp trong cùng luồng.
# Bản chất và tác dụng: view mỏng ở biên HTTP; có side effect ghi cơ sở dữ liệu; chuyển kết quả thành HTTP response.
@api_view(['PATCH', 'DELETE'])
@permission_classes([IsAuthenticated])
def shares_detail(request, entity_type: str, pk: int, grant_id: int):
    """PATCH: update grant (permission_level only); DELETE: revoke grant."""
    resource = _get_resource_or_404(entity_type, pk)
    if resource is None:
        return Response({'detail': 'Entity type khong hop le'}, status=status.HTTP_404_NOT_FOUND)
    grant = get_object_or_404(ShareGrant, pk=grant_id, object_id=resource.pk)

    if not _is_owner_or_admin(request.user, resource):
        return Response({'detail': 'Khong co quyen.'}, status=status.HTTP_403_FORBIDDEN)

    if request.method == 'DELETE':
        try:
            services.revoke_grant(grant, actor=request.user)
        except PermissionError as e:
            return Response({'detail': str(e)}, status=status.HTTP_403_FORBIDDEN)
        return Response(status=status.HTTP_204_NO_CONTENT)

    # PATCH
    new_permission = request.data.get('permission_level')
    if new_permission:
        grant.permission_level = new_permission
        # Doi quyen -> giu nguyen approval_status (vi cung trong cung target)
        grant.save(update_fields=['permission_level', 'updated_at'])
    return Response(ShareGrantSerializer(grant).data)


# Là gì: `shares_submit` là endpoint REST của nhóm chia sẻ tài nguyên và quản lý phạm vi truy cập; nó là điểm nhận request từ client đã đi qua router và lớp permission.
# Chức năng backend: Hàm gửi dữ liệu vào bước xử lý hoặc phê duyệt tiếp theo; đầu vào được kiểm tra hoặc chuẩn hóa trước khi tạo kết quả.
# Vai trò với UI: Kết quả được các hộp thoại và màn hình chia sẻ sử dụng trực tiếp để hiển thị dữ liệu, tải tệp hoặc cập nhật trạng thái thao tác.
# Mối liên hệ: Hàm phối hợp với `_get_resource_or_404`, `get_object_or_404`, `_is_owner_or_admin` và trả dữ liệu về cho lớp gọi kế tiếp trong cùng luồng.
# Bản chất và tác dụng: view mỏng ở biên HTTP; chủ yếu đọc, kiểm tra hoặc biến đổi dữ liệu; chuyển kết quả thành HTTP response.
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def shares_submit(request, entity_type: str, pk: int, grant_id: int):
    """Owner submit grant tu draft -> pending."""
    resource = _get_resource_or_404(entity_type, pk)
    if resource is None:
        return Response({'detail': 'Entity type khong hop le'}, status=status.HTTP_404_NOT_FOUND)
    grant = get_object_or_404(ShareGrant, pk=grant_id, object_id=resource.pk)
    if not _is_owner_or_admin(request.user, resource):
        return Response({'detail': 'Chi owner moi submit duoc.'}, status=status.HTTP_403_FORBIDDEN)
    grant = services.submit_grant(grant, actor=request.user)
    return Response(ShareGrantSerializer(grant).data)


# Là gì: `shares_approve` là endpoint REST của nhóm chia sẻ tài nguyên và quản lý phạm vi truy cập; nó là điểm nhận request từ client đã đi qua router và lớp permission.
# Chức năng backend: Hàm chấp thuận yêu cầu và chuyển trạng thái nghiệp vụ; đầu vào được kiểm tra hoặc chuẩn hóa trước khi tạo kết quả.
# Vai trò với UI: Kết quả được các hộp thoại và màn hình chia sẻ sử dụng trực tiếp để hiển thị dữ liệu, tải tệp hoặc cập nhật trạng thái thao tác.
# Mối liên hệ: Hàm phối hợp với `_get_resource_or_404`, `get_object_or_404`, `get` và trả dữ liệu về cho lớp gọi kế tiếp trong cùng luồng.
# Bản chất và tác dụng: view mỏng ở biên HTTP; chủ yếu đọc, kiểm tra hoặc biến đổi dữ liệu; chuyển kết quả thành HTTP response.
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def shares_approve(request, entity_type: str, pk: int, grant_id: int):
    """Leader/admin duyet grant pending."""
    resource = _get_resource_or_404(entity_type, pk)
    if resource is None:
        return Response({'detail': 'Entity type khong hop le'}, status=status.HTTP_404_NOT_FOUND)
    grant = get_object_or_404(ShareGrant, pk=grant_id, object_id=resource.pk)
    note = (request.data or {}).get('note', '') or ''
    try:
        grant = services.approve_grant(grant, approver=request.user, note=note)
    except PermissionError as e:
        return Response({'detail': str(e)}, status=status.HTTP_403_FORBIDDEN)
    return Response(ShareGrantSerializer(grant).data)


# Là gì: `shares_reject` là endpoint REST của nhóm chia sẻ tài nguyên và quản lý phạm vi truy cập; nó là điểm nhận request từ client đã đi qua router và lớp permission.
# Chức năng backend: Hàm từ chối yêu cầu và ghi nhận lý do; đầu vào được kiểm tra hoặc chuẩn hóa trước khi tạo kết quả.
# Vai trò với UI: Kết quả được các hộp thoại và màn hình chia sẻ sử dụng trực tiếp để hiển thị dữ liệu, tải tệp hoặc cập nhật trạng thái thao tác.
# Mối liên hệ: Hàm phối hợp với `_get_resource_or_404`, `get_object_or_404`, `get` và trả dữ liệu về cho lớp gọi kế tiếp trong cùng luồng.
# Bản chất và tác dụng: view mỏng ở biên HTTP; chủ yếu đọc, kiểm tra hoặc biến đổi dữ liệu; chuyển kết quả thành HTTP response.
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def shares_reject(request, entity_type: str, pk: int, grant_id: int):
    """Leader/admin tu choi grant pending."""
    resource = _get_resource_or_404(entity_type, pk)
    if resource is None:
        return Response({'detail': 'Entity type khong hop le'}, status=status.HTTP_404_NOT_FOUND)
    grant = get_object_or_404(ShareGrant, pk=grant_id, object_id=resource.pk)
    note = (request.data or {}).get('note', '') or ''
    try:
        grant = services.reject_grant(grant, approver=request.user, note=note)
    except PermissionError as e:
        return Response({'detail': str(e)}, status=status.HTTP_403_FORBIDDEN)
    return Response(ShareGrantSerializer(grant).data)


# ============================================================================
# Inbox / shared-with-me cross-entity
# ============================================================================

# vd: client gọi endpoint này -> nhận JSON kết quả tương ứng.
# Là gì: `shares_pending_inbox` là endpoint REST của nhóm chia sẻ tài nguyên và quản lý phạm vi truy cập; nó là điểm nhận request từ client đã đi qua router và lớp permission.
# Chức năng backend: Hàm xử lý phần việc `shares pending inbox` theo dữ liệu và ngữ cảnh được truyền vào; đầu vào được kiểm tra hoặc chuẩn hóa trước khi tạo kết quả.
# Vai trò với UI: Kết quả được các hộp thoại và màn hình chia sẻ sử dụng trực tiếp để hiển thị dữ liệu, tải tệp hoặc cập nhật trạng thái thao tác.
# Mối liên hệ: Hàm phối hợp với `strip.lower`, `strip`, `request.GET.get` và trả dữ liệu về cho lớp gọi kế tiếp trong cùng luồng.
# Bản chất và tác dụng: view mỏng ở biên HTTP; chủ yếu đọc, kiểm tra hoặc biến đổi dữ liệu; chuyển kết quả thành HTTP response.
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def shares_pending_inbox(request):
    """Tat ca grant pending ma user nay co the duyet (cross-entity).

    Ho tro:
      - q          : tim theo ten resource / ten chu so huu.
      - entity_type: loc theo loai (templates|documents|prompts).
      - scope      : loc theo pham vi (group|colleagues|everyone).
      - sort       : 'newest' (mac dinh) | 'oldest' theo thoi gian gui duyet.
    """
    q = (request.GET.get('q') or '').strip().lower()
    entity_filter = (request.GET.get('entity_type') or '').strip().lower()
    scope_filter = (request.GET.get('scope') or '').strip().lower()
    sort = (request.GET.get('sort') or 'newest').strip().lower()

    rows = []  # (timestamp, payload)
    for entity_type, resource, grant in services.get_reviewable_grant_rows(request.user):
        if entity_filter and entity_filter != entity_type:
            continue
        if scope_filter and grant.scope != scope_filter:
            continue
        title = getattr(resource, 'title', '') or ''
        owner = getattr(resource, 'owner', None) or getattr(resource, 'created_by', None)
        owner_name = ''
        if owner is not None:
            owner_name = owner.get_full_name() or owner.get_username() or ''
        if q and q not in title.lower() and q not in owner_name.lower():
            continue
        submitted_at = grant.submitted_at or grant.created_at
        rows.append((
            submitted_at,
            {
                'entity_type': entity_type,
                'entity_id': resource.pk,
                'entity_title': title,
                'owner_name': owner_name,
                'submitted_at': submitted_at.isoformat() if submitted_at else None,
                'grant': ShareGrantSerializer(grant).data,
            },
        ))

    import datetime as _dt

    _min_dt = _dt.datetime.min.replace(tzinfo=_dt.timezone.utc)
    rows.sort(key=lambda r: r[0] or _min_dt, reverse=(sort != 'oldest'))
    return Response({'pending': [payload for _, payload in rows], 'count': len(rows)})


# Là gì: `shares_shared_with_me` là endpoint REST của nhóm chia sẻ tài nguyên và quản lý phạm vi truy cập; nó là điểm nhận request từ client đã đi qua router và lớp permission.
# Chức năng backend: Hàm xử lý phần việc `shares shared with me` theo dữ liệu và ngữ cảnh được truyền vào; đầu vào được kiểm tra hoặc chuẩn hóa trước khi tạo kết quả.
# Vai trò với UI: Kết quả được các hộp thoại và màn hình chia sẻ sử dụng trực tiếp để hiển thị dữ liệu, tải tệp hoặc cập nhật trạng thái thao tác.
# Mối liên hệ: Hàm phối hợp với `ENTITY_TYPE_TO_MODEL.items`, `services.get_accessible_qs`, `accessible_qs.exclude` và trả dữ liệu về cho lớp gọi kế tiếp trong cùng luồng.
# Bản chất và tác dụng: view mỏng ở biên HTTP; chủ yếu đọc, kiểm tra hoặc biến đổi dữ liệu; chuyển kết quả thành HTTP response.
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def shares_shared_with_me(request):
    """Resource duoc share cho user hien tai (cross-entity, da kich hoat)."""
    result = []
    for entity_type, (app_label, model_name) in ENTITY_TYPE_TO_MODEL.items():
        try:
            model_cls = apps.get_model(app_label, model_name)
        except LookupError:
            continue
        accessible_qs = services.get_accessible_qs(request.user, model_cls)
        owner_field = 'owner_id' if hasattr(model_cls, 'owner') else 'created_by_id'
        not_owned = accessible_qs.exclude(**{owner_field: request.user.pk})
        for resource in not_owned[:200]:
            permission = services.user_permission_for(request.user, resource)
            if permission is None:
                continue
            result.append({
                'entity_type': entity_type,
                'entity_id': resource.pk,
                'entity_title': getattr(resource, 'title', '') or '',
                'my_permission': permission,
            })
    return Response({'items': result, 'count': len(result)})
