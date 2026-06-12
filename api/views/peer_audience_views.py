"""
Endpoints peer-audience cho Template / Document / Prompt.
Pattern factory de tao 6 view cho moi entity.
"""

from __future__ import annotations

from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from accounts.models import UserGroupMembership
from accounts.peer_permissions import (
    PeerPermissionLevel,
    log_peer_permission_change,
    normalize_peer_permission_level,
    peer_can,
)
from accounts.tenancy import get_user_company

from api.views.peer_share import (
    PEER_NONE,
    PEER_PENDING_LEADER,
    PEER_REJECTED,
    can_approve_peer_share,
    set_peer_status,
    validate_user_ids_in_company,
)


# Là gì: `_serialize_user` là helper nội bộ của module `peer_audience_views.py`, phục vụ nhóm xây dựng các view chia sẻ tài nguyên theo đối tượng người nhận.
# Chức năng backend: Hàm chuyển đối tượng nội bộ thành dữ liệu có thể trả cho client; đầu vào được kiểm tra hoặc chuẩn hóa trước khi tạo kết quả.
# Vai trò với UI: Flutter không gọi trực tiếp hàm này; các endpoint cùng module dùng kết quả của nó để phục vụ các màn hình tài nguyên được chia sẻ trong công ty.
# Mối liên hệ: Hàm phối hợp với `strip` và trả dữ liệu về cho lớp gọi kế tiếp trong cùng luồng.
# Bản chất và tác dụng: hàm hỗ trợ tái sử dụng trong module; chủ yếu đọc, kiểm tra hoặc biến đổi dữ liệu.
def _serialize_user(user):
    profile = getattr(user, 'profile', None)
    full_name = f'{user.first_name} {user.last_name}'.strip() or user.username
    return {
        'id': user.pk,
        'username': user.username,
        'full_name': full_name,
        'email': user.email,
        'position': (profile.chuc_danh if profile else '') or '',
    }


# Là gì: `_serialize_audience_member` là helper nội bộ của module `peer_audience_views.py`, phục vụ nhóm xây dựng các view chia sẻ tài nguyên theo đối tượng người nhận.
# Chức năng backend: Hàm chuyển đối tượng nội bộ thành dữ liệu có thể trả cho client; đầu vào được kiểm tra hoặc chuẩn hóa trước khi tạo kết quả.
# Vai trò với UI: Flutter không gọi trực tiếp hàm này; các endpoint cùng module dùng kết quả của nó để phục vụ các màn hình tài nguyên được chia sẻ trong công ty.
# Mối liên hệ: Hàm phối hợp với `_serialize_user`, `audience_member.created_at.isoformat` và trả dữ liệu về cho lớp gọi kế tiếp trong cùng luồng.
# Bản chất và tác dụng: hàm hỗ trợ tái sử dụng trong module; chủ yếu đọc, kiểm tra hoặc biến đổi dữ liệu.
def _serialize_audience_member(audience_member):
    return {
        'user_id': audience_member.user_id,
        'permission_level': getattr(audience_member, 'permission_level', PeerPermissionLevel.VIEW),
        'user': _serialize_user(audience_member.user),
        'added_by_id': audience_member.added_by_id,
        'created_at': audience_member.created_at.isoformat() if audience_member.created_at else None,
    }


# Là gì: `_peer_card_payload` là helper nội bộ của module `peer_audience_views.py`, phục vụ nhóm xây dựng các view chia sẻ tài nguyên theo đối tượng người nhận.
# Chức năng backend: Hàm xử lý phần việc `peer card payload` theo dữ liệu và ngữ cảnh được truyền vào; đầu vào được kiểm tra hoặc chuẩn hóa trước khi tạo kết quả.
# Vai trò với UI: Flutter không gọi trực tiếp hàm này; các endpoint cùng module dùng kết quả của nó để phục vụ các màn hình tài nguyên được chia sẻ trong công ty.
# Mối liên hệ: Hàm phối hợp với `audience_model.objects.filter.select_related`, `audience_model.objects.filter`, `audience_qs.count` và trả dữ liệu về cho lớp gọi kế tiếp trong cùng luồng.
# Bản chất và tác dụng: hàm hỗ trợ tái sử dụng trong module; chủ yếu đọc, kiểm tra hoặc biến đổi dữ liệu.
def _peer_card_payload(entity, fk_name: str, audience_model):
    audience_qs = audience_model.objects.filter(**{fk_name: entity}).select_related('user', 'user__profile')
    return {
        'id': entity.pk,
        'title': getattr(entity, 'title', '') or '',
        'owner_id': entity.owner_id,
        'owner_name': (
            (entity.owner.get_full_name() or entity.owner.username)
            if entity.owner_id else ''
        ),
        'peer_share_status': entity.peer_share_status,
        'peer_share_approver_note': entity.peer_share_approver_note or '',
        'peer_share_submitted_at': (
            entity.peer_share_submitted_at.isoformat()
            if entity.peer_share_submitted_at else None
        ),
        'peer_audience_count': audience_qs.count(),
        'audience_preview': [_serialize_audience_member(am) for am in audience_qs[:5]],
    }


# Là gì: `_parse_audience_payload` là helper nội bộ của module `peer_audience_views.py`, phục vụ nhóm xây dựng các view chia sẻ tài nguyên theo đối tượng người nhận.
# Chức năng backend: Hàm phân tích dữ liệu thô thành cấu trúc có thể sử dụng; đầu vào được kiểm tra hoặc chuẩn hóa trước khi tạo kết quả.
# Vai trò với UI: Flutter không gọi trực tiếp hàm này; các endpoint cùng module dùng kết quả của nó để phục vụ các màn hình tài nguyên được chia sẻ trong công ty.
# Mối liên hệ: Hàm phối hợp với `data.get`, `item.get`, `normalize_peer_permission_level` và trả dữ liệu về cho lớp gọi kế tiếp trong cùng luồng.
# Bản chất và tác dụng: hàm hỗ trợ tái sử dụng trong module; chủ yếu đọc, kiểm tra hoặc biến đổi dữ liệu.
def _parse_audience_payload(data):
    raw_audiences = data.get('audiences')
    if raw_audiences is not None:
        if not isinstance(raw_audiences, list):
            return None, {'detail': 'audiences phai la mang.'}
        parsed = {}
        for item in raw_audiences:
            if not isinstance(item, dict):
                return None, {'detail': 'Moi audience phai la object.'}
            user_id = item.get('user_id')
            if user_id is None:
                return None, {'detail': 'Moi audience phai co user_id.'}
            try:
                normalized_user_id = int(user_id)
            except (TypeError, ValueError):
                return None, {'detail': 'user_id khong hop le.'}
            permission_level = normalize_peer_permission_level(item.get('permission_level'))
            if permission_level is None:
                return None, {
                    'detail': 'permission_level khong hop le.',
                    'allowed_values': list(PeerPermissionLevel.values),
                }
            parsed[normalized_user_id] = permission_level
        return parsed, None

    user_ids_raw = data.get('user_ids') or []
    if not isinstance(user_ids_raw, list):
        return None, {'detail': 'user_ids phai la mang.'}
    parsed = {}
    for user_id in user_ids_raw:
        try:
            parsed[int(user_id)] = PeerPermissionLevel.VIEW
        except (TypeError, ValueError):
            return None, {'detail': 'user_ids phai chua so nguyen.'}
    return parsed, None


# Là gì: `build_peer_views` là hàm điều phối nghiệp vụ của module `peer_audience_views.py`, thuộc nhóm xây dựng các view chia sẻ tài nguyên theo đối tượng người nhận.
# Chức năng backend: Hàm tổng hợp dữ liệu đầu vào thành cấu trúc phục vụ bước tiếp theo; đầu vào được kiểm tra hoặc chuẩn hóa trước khi tạo kết quả.
# Vai trò với UI: Flutter không gọi trực tiếp hàm này; các endpoint cùng module dùng kết quả của nó để phục vụ các màn hình tài nguyên được chia sẻ trong công ty.
# Mối liên hệ: Hàm phối hợp với `get_user_company`, `model.objects.all`, `get_object_or_404` và trả dữ liệu về cho lớp gọi kế tiếp trong cùng luồng.
# Bản chất và tác dụng: hàm hỗ trợ tái sử dụng trong module; có side effect ghi cơ sở dữ liệu; chuyển kết quả thành HTTP response.
def build_peer_views(*, model, audience_model, fk_name: str, entity_label: str):
    """
    Returns dict cua 6 view functions.
    fk_name: 'template' | 'document' | 'prompt'
    """

    # Là gì: `_get_entity` là hàm cục bộ bên trong `build_peer_views`, chỉ phục vụ bước xử lý nội bộ của nhóm xây dựng các view chia sẻ tài nguyên theo đối tượng người nhận.
    # Chức năng backend: Hàm đọc và trả về dữ liệu cần thiết; đầu vào được kiểm tra hoặc chuẩn hóa trước khi tạo kết quả.
    # Vai trò với UI: Flutter không gọi trực tiếp hàm này; các endpoint cùng module dùng kết quả của nó để phục vụ các màn hình tài nguyên được chia sẻ trong công ty.
    # Mối liên hệ: Hàm phối hợp với `get_user_company`, `model.objects.all`, `any` và trả dữ liệu về cho lớp gọi kế tiếp trong cùng luồng.
    # Bản chất và tác dụng: callback cục bộ chỉ có hiệu lực trong hàm bao ngoài; chủ yếu đọc, kiểm tra hoặc biến đổi dữ liệu.
    def _get_entity(request, pk):
        company = get_user_company(request.user)
        qs = model.objects.all()
        if company is not None and not request.user.is_superuser:
            if any(field.name == 'company' for field in model._meta.fields):
                qs = qs.filter(company=company)
            else:
                qs = qs.filter(owner__company_membership__company=company)
        return get_object_or_404(qs, pk=pk)

    # Là gì: `_can_manage_audience` là hàm cục bộ bên trong `build_peer_views`, chỉ phục vụ bước xử lý nội bộ của nhóm xây dựng các view chia sẻ tài nguyên theo đối tượng người nhận.
    # Chức năng backend: Hàm đánh giá quyền hoặc điều kiện cho phép thao tác; đầu vào được kiểm tra hoặc chuẩn hóa trước khi tạo kết quả.
    # Vai trò với UI: Flutter không gọi trực tiếp hàm này; các endpoint cùng module dùng kết quả của nó để phục vụ các màn hình tài nguyên được chia sẻ trong công ty.
    # Mối liên hệ: Hàm phối hợp với `peer_can` và trả dữ liệu về cho lớp gọi kế tiếp trong cùng luồng.
    # Bản chất và tác dụng: callback cục bộ chỉ có hiệu lực trong hàm bao ngoài; chủ yếu đọc, kiểm tra hoặc biến đổi dữ liệu.
    def _can_manage_audience(request, entity):
        if request.user.is_superuser or entity.owner_id == request.user.pk:
            return True
        return peer_can(request.user, entity, PeerPermissionLevel.DELETE)

    # Là gì: `_can_view_audience` là hàm cục bộ bên trong `build_peer_views`, chỉ phục vụ bước xử lý nội bộ của nhóm xây dựng các view chia sẻ tài nguyên theo đối tượng người nhận.
    # Chức năng backend: Hàm đánh giá quyền hoặc điều kiện cho phép thao tác; đầu vào được kiểm tra hoặc chuẩn hóa trước khi tạo kết quả.
    # Vai trò với UI: Flutter không gọi trực tiếp hàm này; các endpoint cùng module dùng kết quả của nó để phục vụ các màn hình tài nguyên được chia sẻ trong công ty.
    # Mối liên hệ: Hàm phối hợp với `peer_can` và trả dữ liệu về cho lớp gọi kế tiếp trong cùng luồng.
    # Bản chất và tác dụng: callback cục bộ chỉ có hiệu lực trong hàm bao ngoài; chủ yếu đọc, kiểm tra hoặc biến đổi dữ liệu.
    def _can_view_audience(request, entity):
        if request.user.is_superuser or entity.owner_id == request.user.pk:
            return True
        return peer_can(request.user, entity, PeerPermissionLevel.VIEW)

    # Là gì: `_render_state` là hàm cục bộ bên trong `build_peer_views`, chỉ phục vụ bước xử lý nội bộ của nhóm xây dựng các view chia sẻ tài nguyên theo đối tượng người nhận.
    # Chức năng backend: Hàm kết xuất nội dung theo mẫu hoặc định dạng đích; đầu vào được kiểm tra hoặc chuẩn hóa trước khi tạo kết quả.
    # Vai trò với UI: Flutter không gọi trực tiếp hàm này; các endpoint cùng module dùng kết quả của nó để phục vụ các màn hình tài nguyên được chia sẻ trong công ty.
    # Mối liên hệ: Hàm phối hợp với `audience_model.objects.filter.select_related.order_by`, `audience_model.objects.filter.select_related`, `audience_model.objects.filter` và trả dữ liệu về cho lớp gọi kế tiếp trong cùng luồng.
    # Bản chất và tác dụng: callback cục bộ chỉ có hiệu lực trong hàm bao ngoài; chủ yếu đọc, kiểm tra hoặc biến đổi dữ liệu; chuyển kết quả thành HTTP response.
    def _render_state(entity):
        members = list(
            audience_model.objects.filter(**{fk_name: entity})
            .select_related('user', 'user__profile')
            .order_by('user__first_name', 'user__last_name', 'user__username')
        )
        audiences = [_serialize_audience_member(member) for member in members]
        return Response({
            'peer_share_status': entity.peer_share_status,
            'peer_share_approver_note': entity.peer_share_approver_note or '',
            'peer_share_submitted_at': entity.peer_share_submitted_at.isoformat() if entity.peer_share_submitted_at else None,
            'peer_share_approved_at': entity.peer_share_approved_at.isoformat() if entity.peer_share_approved_at else None,
            'audiences': audiences,
            # Backward-compat for older Flutter code.
            'members': [
                {
                    **audience['user'],
                    'added_by_id': audience['added_by_id'],
                    'created_at': audience['created_at'],
                    'permission_level': audience['permission_level'],
                }
                for audience in audiences
            ],
        })

    # Là gì: `_handle_list_audience` là hàm cục bộ bên trong `build_peer_views`, chỉ phục vụ bước xử lý nội bộ của nhóm xây dựng các view chia sẻ tài nguyên theo đối tượng người nhận.
    # Chức năng backend: Hàm truy vấn và trả về danh sách dữ liệu phù hợp; đầu vào được kiểm tra hoặc chuẩn hóa trước khi tạo kết quả.
    # Vai trò với UI: Flutter không gọi trực tiếp hàm này; các endpoint cùng module dùng kết quả của nó để phục vụ các màn hình tài nguyên được chia sẻ trong công ty.
    # Mối liên hệ: Hàm phối hợp với `_get_entity`, `_can_view_audience`, `_render_state` và trả dữ liệu về cho lớp gọi kế tiếp trong cùng luồng.
    # Bản chất và tác dụng: callback cục bộ chỉ có hiệu lực trong hàm bao ngoài; chủ yếu đọc, kiểm tra hoặc biến đổi dữ liệu; chuyển kết quả thành HTTP response.
    def _handle_list_audience(request, pk):
        entity = _get_entity(request, pk)
        if not _can_view_audience(request, entity):
            return Response(
                {'detail': 'Khong co quyen xem audience.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        return _render_state(entity)

    # Là gì: `_handle_update_audience` là hàm cục bộ bên trong `build_peer_views`, chỉ phục vụ bước xử lý nội bộ của nhóm xây dựng các view chia sẻ tài nguyên theo đối tượng người nhận.
    # Chức năng backend: Hàm cập nhật trạng thái hoặc nội dung hiện có; đầu vào được kiểm tra hoặc chuẩn hóa trước khi tạo kết quả.
    # Vai trò với UI: Flutter không gọi trực tiếp hàm này; các endpoint cùng module dùng kết quả của nó để phục vụ các màn hình tài nguyên được chia sẻ trong công ty.
    # Mối liên hệ: Hàm phối hợp với `_get_entity`, `_can_manage_audience`, `_parse_audience_payload` và trả dữ liệu về cho lớp gọi kế tiếp trong cùng luồng.
    # Bản chất và tác dụng: callback cục bộ chỉ có hiệu lực trong hàm bao ngoài; có side effect ghi cơ sở dữ liệu; chuyển kết quả thành HTTP response.
    def _handle_update_audience(request, pk):
        entity = _get_entity(request, pk)
        if not _can_manage_audience(request, entity):
            return Response(
                {'detail': 'Khong co quyen sua audience.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        target_levels, error = _parse_audience_payload(request.data)
        if error is not None:
            return Response(error, status=status.HTTP_400_BAD_REQUEST)

        target_levels.pop(entity.owner_id, None)
        owner_company = get_user_company(entity.owner)
        valid_ids, invalid_ids = validate_user_ids_in_company(target_levels.keys(), owner_company)
        if invalid_ids:
            return Response(
                {
                    'detail': 'Mot so user khong thuoc cong ty cua chu so huu.',
                    'invalid_user_ids': invalid_ids,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        cleaned_levels = {
            user_id: target_levels[user_id]
            for user_id in valid_ids
        }

        with transaction.atomic():
            existing_qs = audience_model.objects.select_for_update().filter(**{fk_name: entity})
            existing_by_user_id = {entry.user_id: entry for entry in existing_qs}
            existing_ids = set(existing_by_user_id)
            target_ids = set(cleaned_levels)

            for user_id in sorted(existing_ids - target_ids):
                existing_by_user_id[user_id].delete()
                log_peer_permission_change(
                    entity_name=entity_label,
                    entity_id=entity.pk,
                    actor_id=request.user.pk,
                    target_user_id=user_id,
                    old_level=existing_by_user_id[user_id].permission_level,
                    new_level=None,
                )

            for user_id in sorted(target_ids):
                desired_level = cleaned_levels[user_id]
                existing_entry = existing_by_user_id.get(user_id)
                if existing_entry is None:
                    audience_model.objects.create(
                        **{fk_name: entity},
                        user_id=user_id,
                        added_by=request.user,
                        permission_level=desired_level,
                    )
                    log_peer_permission_change(
                        entity_name=entity_label,
                        entity_id=entity.pk,
                        actor_id=request.user.pk,
                        target_user_id=user_id,
                        old_level=None,
                        new_level=desired_level,
                    )
                    continue
                if existing_entry.permission_level == desired_level:
                    continue
                old_level = existing_entry.permission_level
                existing_entry.permission_level = desired_level
                existing_entry.save(update_fields=['permission_level'])
                log_peer_permission_change(
                    entity_name=entity_label,
                    entity_id=entity.pk,
                    actor_id=request.user.pk,
                    target_user_id=user_id,
                    old_level=old_level,
                    new_level=desired_level,
                )

        if not cleaned_levels:
            set_peer_status(entity, PEER_NONE)
        return _render_state(entity)

    # Là gì: `list_audience` là endpoint REST của nhóm xây dựng các view chia sẻ tài nguyên theo đối tượng người nhận; nó là điểm nhận request từ client đã đi qua router và lớp permission.
    # Chức năng backend: Hàm truy vấn và trả về danh sách dữ liệu phù hợp; đầu vào được kiểm tra hoặc chuẩn hóa trước khi tạo kết quả.
    # Vai trò với UI: Kết quả được các màn hình tài nguyên được chia sẻ trong công ty sử dụng trực tiếp để hiển thị dữ liệu, tải tệp hoặc cập nhật trạng thái thao tác.
    # Mối liên hệ: Hàm phối hợp với `_handle_list_audience` và trả dữ liệu về cho lớp gọi kế tiếp trong cùng luồng.
    # Bản chất và tác dụng: view mỏng ở biên HTTP; chủ yếu đọc, kiểm tra hoặc biến đổi dữ liệu.
    @api_view(['GET'])
    @permission_classes([IsAuthenticated])
    def list_audience(request, pk):
        return _handle_list_audience(request, pk)

    # Là gì: `update_audience` là endpoint REST của nhóm xây dựng các view chia sẻ tài nguyên theo đối tượng người nhận; nó là điểm nhận request từ client đã đi qua router và lớp permission.
    # Chức năng backend: Hàm cập nhật trạng thái hoặc nội dung hiện có; đầu vào được kiểm tra hoặc chuẩn hóa trước khi tạo kết quả.
    # Vai trò với UI: Kết quả được các màn hình tài nguyên được chia sẻ trong công ty sử dụng trực tiếp để hiển thị dữ liệu, tải tệp hoặc cập nhật trạng thái thao tác.
    # Mối liên hệ: Hàm phối hợp với `_handle_update_audience` và trả dữ liệu về cho lớp gọi kế tiếp trong cùng luồng.
    # Bản chất và tác dụng: view mỏng ở biên HTTP; chủ yếu đọc, kiểm tra hoặc biến đổi dữ liệu.
    @api_view(['PUT'])
    @permission_classes([IsAuthenticated])
    def update_audience(request, pk):
        return _handle_update_audience(request, pk)

    # Là gì: `audience` là endpoint REST của nhóm xây dựng các view chia sẻ tài nguyên theo đối tượng người nhận; nó là điểm nhận request từ client đã đi qua router và lớp permission.
    # Chức năng backend: Hàm xử lý phần việc `audience` theo dữ liệu và ngữ cảnh được truyền vào; đầu vào được kiểm tra hoặc chuẩn hóa trước khi tạo kết quả.
    # Vai trò với UI: Kết quả được các màn hình tài nguyên được chia sẻ trong công ty sử dụng trực tiếp để hiển thị dữ liệu, tải tệp hoặc cập nhật trạng thái thao tác.
    # Mối liên hệ: Hàm phối hợp với `_handle_list_audience`, `_handle_update_audience` và trả dữ liệu về cho lớp gọi kế tiếp trong cùng luồng.
    # Bản chất và tác dụng: view mỏng ở biên HTTP; chủ yếu đọc, kiểm tra hoặc biến đổi dữ liệu.
    @api_view(['GET', 'PUT'])
    @permission_classes([IsAuthenticated])
    def audience(request, pk):
        if request.method == 'GET':
            return _handle_list_audience(request, pk)
        return _handle_update_audience(request, pk)

    # Là gì: `submit` là endpoint REST của nhóm xây dựng các view chia sẻ tài nguyên theo đối tượng người nhận; nó là điểm nhận request từ client đã đi qua router và lớp permission.
    # Chức năng backend: Hàm gửi dữ liệu vào bước xử lý hoặc phê duyệt tiếp theo; đầu vào được kiểm tra hoặc chuẩn hóa trước khi tạo kết quả.
    # Vai trò với UI: Kết quả được các màn hình tài nguyên được chia sẻ trong công ty sử dụng trực tiếp để hiển thị dữ liệu, tải tệp hoặc cập nhật trạng thái thao tác.
    # Mối liên hệ: Hàm phối hợp với `_get_entity`, `_can_manage_audience`, `audience_model.objects.filter.exists` và trả dữ liệu về cho lớp gọi kế tiếp trong cùng luồng.
    # Bản chất và tác dụng: view mỏng ở biên HTTP; chủ yếu đọc, kiểm tra hoặc biến đổi dữ liệu; chuyển kết quả thành HTTP response.
    @api_view(['POST'])
    @permission_classes([IsAuthenticated])
    def submit(request, pk):
        entity = _get_entity(request, pk)
        if not _can_manage_audience(request, entity):
            return Response(
                {'detail': 'Khong co quyen gui duyet audience.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        if not audience_model.objects.filter(**{fk_name: entity}).exists():
            return Response(
                {'detail': 'Chua co dong nghiep nao trong danh sach.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        owner_group_count = UserGroupMembership.objects.filter(user=entity.owner).count()
        if owner_group_count == 0:
            return Response(
                {'detail': 'Ban phai thuoc it nhat 1 nhom de duoc duyet peer share.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        set_peer_status(entity, PEER_PENDING_LEADER)
        return _render_state(entity)

    # Là gì: `approve` là endpoint REST của nhóm xây dựng các view chia sẻ tài nguyên theo đối tượng người nhận; nó là điểm nhận request từ client đã đi qua router và lớp permission.
    # Chức năng backend: Hàm chấp thuận yêu cầu và chuyển trạng thái nghiệp vụ; đầu vào được kiểm tra hoặc chuẩn hóa trước khi tạo kết quả.
    # Vai trò với UI: Kết quả được các màn hình tài nguyên được chia sẻ trong công ty sử dụng trực tiếp để hiển thị dữ liệu, tải tệp hoặc cập nhật trạng thái thao tác.
    # Mối liên hệ: Hàm phối hợp với `_get_entity`, `can_approve_peer_share`, `str.strip` và trả dữ liệu về cho lớp gọi kế tiếp trong cùng luồng.
    # Bản chất và tác dụng: view mỏng ở biên HTTP; chủ yếu đọc, kiểm tra hoặc biến đổi dữ liệu; chuyển kết quả thành HTTP response.
    @api_view(['POST'])
    @permission_classes([IsAuthenticated])
    def approve(request, pk):
        entity = _get_entity(request, pk)
        ok, reason = can_approve_peer_share(request.user, entity.owner)
        if not ok:
            return Response({'detail': reason}, status=status.HTTP_403_FORBIDDEN)
        if entity.peer_share_status != PEER_PENDING_LEADER:
            return Response(
                {'detail': 'Khong o trang thai cho duyet.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        note = str(request.data.get('note', '') or '').strip()
        set_peer_status(entity, 'active', approver=request.user, note=note)
        return _render_state(entity)

    # Là gì: `reject` là endpoint REST của nhóm xây dựng các view chia sẻ tài nguyên theo đối tượng người nhận; nó là điểm nhận request từ client đã đi qua router và lớp permission.
    # Chức năng backend: Hàm từ chối yêu cầu và ghi nhận lý do; đầu vào được kiểm tra hoặc chuẩn hóa trước khi tạo kết quả.
    # Vai trò với UI: Kết quả được các màn hình tài nguyên được chia sẻ trong công ty sử dụng trực tiếp để hiển thị dữ liệu, tải tệp hoặc cập nhật trạng thái thao tác.
    # Mối liên hệ: Hàm phối hợp với `_get_entity`, `can_approve_peer_share`, `str.strip` và trả dữ liệu về cho lớp gọi kế tiếp trong cùng luồng.
    # Bản chất và tác dụng: view mỏng ở biên HTTP; chủ yếu đọc, kiểm tra hoặc biến đổi dữ liệu; chuyển kết quả thành HTTP response.
    @api_view(['POST'])
    @permission_classes([IsAuthenticated])
    def reject(request, pk):
        entity = _get_entity(request, pk)
        ok, reason = can_approve_peer_share(request.user, entity.owner)
        if not ok:
            return Response({'detail': reason}, status=status.HTTP_403_FORBIDDEN)
        note = str(request.data.get('note', '') or '').strip()
        if not note:
            return Response(
                {'detail': 'Phai co ly do tu choi.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if entity.peer_share_status != PEER_PENDING_LEADER:
            return Response(
                {'detail': 'Khong o trang thai cho duyet.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        set_peer_status(entity, PEER_REJECTED, approver=request.user, note=note)
        return _render_state(entity)

    has_company_fk = any(field.name == 'company' for field in model._meta.fields)

    # Là gì: `_scope_to_company` là hàm cục bộ bên trong `build_peer_views`, chỉ phục vụ bước xử lý nội bộ của nhóm xây dựng các view chia sẻ tài nguyên theo đối tượng người nhận.
    # Chức năng backend: Hàm xử lý phần việc `scope to company` theo dữ liệu và ngữ cảnh được truyền vào; đầu vào được kiểm tra hoặc chuẩn hóa trước khi tạo kết quả.
    # Vai trò với UI: Flutter không gọi trực tiếp hàm này; các endpoint cùng module dùng kết quả của nó để phục vụ các màn hình tài nguyên được chia sẻ trong công ty.
    # Mối liên hệ: Hàm phối hợp với `qs.filter` và trả dữ liệu về cho lớp gọi kế tiếp trong cùng luồng.
    # Bản chất và tác dụng: callback cục bộ chỉ có hiệu lực trong hàm bao ngoài; chủ yếu đọc, kiểm tra hoặc biến đổi dữ liệu.
    def _scope_to_company(qs, company):
        if has_company_fk:
            return qs.filter(company=company)
        return qs.filter(owner__company_membership__company=company)

    # Là gì: `pending` là endpoint REST của nhóm xây dựng các view chia sẻ tài nguyên theo đối tượng người nhận; nó là điểm nhận request từ client đã đi qua router và lớp permission.
    # Chức năng backend: Hàm xử lý phần việc `pending` theo dữ liệu và ngữ cảnh được truyền vào; đầu vào được kiểm tra hoặc chuẩn hóa trước khi tạo kết quả.
    # Vai trò với UI: Kết quả được các màn hình tài nguyên được chia sẻ trong công ty sử dụng trực tiếp để hiển thị dữ liệu, tải tệp hoặc cập nhật trạng thái thao tác.
    # Mối liên hệ: Hàm phối hợp với `get_user_company`, `model.objects.filter`, `_scope_to_company` và trả dữ liệu về cho lớp gọi kế tiếp trong cùng luồng.
    # Bản chất và tác dụng: view mỏng ở biên HTTP; chủ yếu đọc, kiểm tra hoặc biến đổi dữ liệu; chuyển kết quả thành HTTP response.
    @api_view(['GET'])
    @permission_classes([IsAuthenticated])
    def pending(request):
        company = get_user_company(request.user)
        if company is None:
            return Response([])

        viewer = request.user
        base_qs = model.objects.filter(peer_share_status=PEER_PENDING_LEADER)
        if viewer.is_superuser:
            qs = _scope_to_company(base_qs, company)
        else:
            leader_group_ids = list(
                UserGroupMembership.objects
                .filter(user=viewer, role='leader')
                .values_list('group_id', flat=True)
            )
            if not leader_group_ids:
                return Response([])
            owner_ids = list(
                UserGroupMembership.objects
                .filter(group_id__in=leader_group_ids)
                .values_list('user_id', flat=True)
                .distinct()
            )
            qs = _scope_to_company(base_qs.filter(owner_id__in=owner_ids), company)
        qs = qs.select_related('owner').order_by('-peer_share_submitted_at')[:100]
        return Response([_peer_card_payload(entity, fk_name, audience_model) for entity in qs])

    return {
        'audience': audience,
        'list_audience': list_audience,
        'update_audience': update_audience,
        'submit': submit,
        'approve': approve,
        'reject': reject,
        'pending': pending,
    }
