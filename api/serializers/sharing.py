"""
Serializer cho ShareGrant - dung chung cho ca 3 entity (Template/Document/Prompt).
"""

from __future__ import annotations

from rest_framework import serializers

from sharing.constants import (
    APPROVAL_PENDING_ADMIN,
    APPROVAL_PENDING_LEADER,
    PERMISSION_CHOICES,
    SCOPE_CHOICES,
    SCOPE_COLLEAGUES,
    SCOPE_EVERYONE,
    SCOPE_GROUP,
    SCOPE_PRIVATE,
    APPROVAL_CHOICES,
)
from sharing.models import ShareGrant


# def serialize_user_brief để tuần tự hóa user brief (trong serializer).
# vd: nhận tham số đầu vào -> trả cấu trúc dữ liệu/chuỗi đã dựng.
def serialize_user_brief(user):
    if user is None:
        return None
    profile = getattr(user, 'profile', None)
    full_name = f'{user.first_name} {user.last_name}'.strip() or user.username
    return {
        'id': user.pk,
        'username': user.username,
        'full_name': full_name,
        'email': user.email,
        'position': (profile.chuc_danh if profile else '') or '',
    }


# def serialize_group_brief để tuần tự hóa group brief (trong serializer).
# vd: nhận tham số đầu vào -> trả cấu trúc dữ liệu/chuỗi đã dựng.
def serialize_group_brief(group):
    if group is None:
        return None
    return {
        'id': group.pk,
        'name': group.name,
    }


# class ShareGrantSerializer là serializer định nghĩa dữ liệu vào/ra (ShareGrant).
# vd: serializer.data -> JSON cho frontend; is_valid() kiểm tra dữ liệu gửi lên.
class ShareGrantSerializer(serializers.ModelSerializer):
    target_user_info = serializers.SerializerMethodField()
    target_group_info = serializers.SerializerMethodField()
    submitted_by_info = serializers.SerializerMethodField()
    approved_by_info = serializers.SerializerMethodField()
    required_approver = serializers.SerializerMethodField()

    # class Meta khai báo metadata (fields, ordering, ràng buộc...) cho model/serializer.
    # vd: ordering=['-created_at'] -> bản ghi mới nhất lên đầu.
    class Meta:
        model = ShareGrant
        fields = (
            'id',
            'scope',
            'permission_level',
            'target_user',
            'target_user_info',
            'target_group',
            'target_group_info',
            'approval_status',
            'submitted_at',
            'submitted_by',
            'submitted_by_info',
            'approved_at',
            'approved_by',
            'approved_by_info',
            'approver_note',
            'required_approver',
            'created_at',
            'updated_at',
        )
        read_only_fields = (
            'approval_status',
            'submitted_at', 'submitted_by',
            'approved_at', 'approved_by',
            'approver_note',
            'created_at', 'updated_at',
        )

    # def get_target_user_info để lấy target user info (trong serializer).
    # vd: nhận điều kiện -> trả về dữ liệu phù hợp.
    def get_target_user_info(self, obj):
        return serialize_user_brief(obj.target_user)

    # def get_target_group_info để lấy target group info (trong serializer).
    # vd: nhận điều kiện -> trả về dữ liệu phù hợp.
    def get_target_group_info(self, obj):
        return serialize_group_brief(obj.target_group)

    # def get_submitted_by_info để lấy submitted by info (trong serializer).
    # vd: nhận điều kiện -> trả về dữ liệu phù hợp.
    def get_submitted_by_info(self, obj):
        return serialize_user_brief(obj.submitted_by)

    # def get_approved_by_info để lấy approved by info (trong serializer).
    # vd: nhận điều kiện -> trả về dữ liệu phù hợp.
    def get_approved_by_info(self, obj):
        return serialize_user_brief(obj.approved_by)

    # def get_required_approver để lấy required approver (trong serializer).
    # vd: nhận điều kiện -> trả về dữ liệu phù hợp.
    def get_required_approver(self, obj):
        # Suy ra tu trang thai duyet THUC TE de luon nhat quan voi
        # sharing.services._initial_approval_status (vd: dong nghiep khac nhom
        # -> pending_admin -> 'admin'; chung nhom -> pending_leader -> 'leader').
        # Khong dung required_approver_role(scope) vi ham do luon tra 'leader'
        # cho colleagues, khong phan biet duoc chung/khac nhom.
        if obj.approval_status == APPROVAL_PENDING_ADMIN:
            return 'admin'
        if obj.approval_status == APPROVAL_PENDING_LEADER:
            return 'leader'
        return 'none'


# class ShareGrantCreateSerializer là serializer định nghĩa dữ liệu vào/ra (ShareGrantCreate).
# vd: serializer.data -> JSON cho frontend; is_valid() kiểm tra dữ liệu gửi lên.
class ShareGrantCreateSerializer(serializers.Serializer):
    scope = serializers.ChoiceField(choices=[s for s, _ in SCOPE_CHOICES])
    permission_level = serializers.ChoiceField(choices=[p for p, _ in PERMISSION_CHOICES])
    target_user = serializers.IntegerField(required=False, allow_null=True)
    target_group = serializers.IntegerField(required=False, allow_null=True)
    auto_submit = serializers.BooleanField(default=True)

    # def validate để kiểm tra hợp lệ (trong serializer).
    # vd: dữ liệu sai -> báo lỗi/False; hợp lệ -> True hoặc giá trị đã chuẩn hóa.
    def validate(self, attrs):
        scope = attrs.get('scope')
        if scope == SCOPE_GROUP and not attrs.get('target_group'):
            raise serializers.ValidationError({'target_group': 'Bat buoc khi scope=group'})
        if scope == SCOPE_COLLEAGUES and not attrs.get('target_user'):
            raise serializers.ValidationError({'target_user': 'Bat buoc khi scope=colleagues'})
        if scope in (SCOPE_PRIVATE, SCOPE_EVERYONE):
            attrs['target_user'] = None
            attrs['target_group'] = None
        return attrs
