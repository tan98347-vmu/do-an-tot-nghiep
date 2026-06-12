from __future__ import annotations

from rest_framework import serializers

from accounts.permissions import can_delete_prompt, can_edit_prompt
from accounts.peer_permissions import get_peer_permission_level, max_peer_permission_level
from api.security.prompt_guard import (
    prompt_check_expected_payload,
    verify_prompt_check_token,
)
from prompts.models import Prompt, PromptCategory, USAGE_SCOPES, default_prompt_usage_scopes


# def _prompt_permission_for_user để prompt permission for user (trong serializer).
# vd: nhận đầu vào -> trả kết quả đã xử lý.
def _prompt_permission_for_user(user, prompt) -> str | None:
    if not user or not user.is_authenticated:
        return None
    if prompt.owner_id == user.id:
        return 'owner'
    if user.is_superuser:
        return 'delete'

    base_level = 'view'
    if can_delete_prompt(user, prompt):
        base_level = 'delete'
    elif can_edit_prompt(user, prompt):
        base_level = 'edit'

    peer_level = get_peer_permission_level(user, prompt)
    return max_peer_permission_level(base_level, peer_level) or base_level


# class PromptCategorySerializer là serializer định nghĩa dữ liệu vào/ra (PromptCategory).
# vd: serializer.data -> JSON cho frontend; is_valid() kiểm tra dữ liệu gửi lên.
class PromptCategorySerializer(serializers.ModelSerializer):
    # class Meta khai báo metadata (fields, ordering, ràng buộc...) cho model/serializer.
    # vd: ordering=['-created_at'] -> bản ghi mới nhất lên đầu.
    class Meta:
        model = PromptCategory
        fields = ('id', 'name', 'description')


# class _PromptBaseSerializer là serializer định nghĩa dữ liệu vào/ra (_PromptBase).
# vd: serializer.data -> JSON cho frontend; is_valid() kiểm tra dữ liệu gửi lên.
class _PromptBaseSerializer(serializers.ModelSerializer):
    owner_name = serializers.SerializerMethodField()
    category_name = serializers.SerializerMethodField()
    group_name = serializers.SerializerMethodField()
    is_mine = serializers.SerializerMethodField()
    can_approve = serializers.SerializerMethodField()
    can_edit = serializers.SerializerMethodField()
    can_delete = serializers.SerializerMethodField()
    my_permission = serializers.SerializerMethodField()
    peer_share_status = serializers.CharField(read_only=True)
    peer_share_approver_note = serializers.CharField(read_only=True)
    peer_audience_count = serializers.SerializerMethodField()
    is_peer_shared_to_me = serializers.SerializerMethodField()

    # def _current_user để current user (trong serializer).
    # vd: nhận đầu vào -> trả kết quả đã xử lý.
    def _current_user(self):
        request = self.context.get('request') if hasattr(self, 'context') else None
        return getattr(request, 'user', None) if request else None

    # def get_owner_name để lấy owner name (trong serializer).
    # vd: nhận điều kiện -> trả về dữ liệu phù hợp.
    def get_owner_name(self, obj):
        return obj.owner.get_full_name() or obj.owner.username

    # def get_category_name để lấy category name (trong serializer).
    # vd: nhận điều kiện -> trả về dữ liệu phù hợp.
    def get_category_name(self, obj):
        return obj.category.name if obj.category else None

    # def get_group_name để lấy group name (trong serializer).
    # vd: nhận điều kiện -> trả về dữ liệu phù hợp.
    def get_group_name(self, obj):
        return obj.group.name if obj.group else None

    # def get_is_mine để lấy is mine (trong serializer).
    # vd: nhận điều kiện -> trả về dữ liệu phù hợp.
    def get_is_mine(self, obj):
        user = self._current_user()
        return bool(user and user.is_authenticated and obj.owner_id == user.pk)

    # def get_can_approve để lấy can approve (trong serializer).
    # vd: nhận đầu vào -> trả kết quả đã xử lý.
    def get_can_approve(self, obj):
        from prompts.status_rules import can_approve_prompt

        ok, _ = can_approve_prompt(self._current_user(), obj)
        return ok

    # def get_can_edit để lấy can edit (trong serializer).
    # vd: nhận điều kiện -> trả về dữ liệu phù hợp.
    def get_can_edit(self, obj):
        user = self._current_user()
        return can_edit_prompt(user, obj)

    # def get_can_delete để lấy can delete (trong serializer).
    # vd: nhận đầu vào -> trả kết quả đã xử lý.
    def get_can_delete(self, obj):
        user = self._current_user()
        return can_delete_prompt(user, obj)

    # def get_my_permission để lấy my permission (trong serializer).
    # vd: nhận điều kiện -> trả về dữ liệu phù hợp.
    def get_my_permission(self, obj):
        return _prompt_permission_for_user(self._current_user(), obj)

    # def get_peer_audience_count để lấy peer audience count (trong serializer).
    # vd: nhận đầu vào -> trả kết quả đã xử lý.
    def get_peer_audience_count(self, obj):
        return obj.audience_members.count() if hasattr(obj, 'audience_members') else 0

    # def get_is_peer_shared_to_me để lấy is peer shared to me (trong serializer).
    # vd: nhận điều kiện -> trả về dữ liệu phù hợp.
    def get_is_peer_shared_to_me(self, obj):
        user = self._current_user()
        if not user or not user.is_authenticated or obj.owner_id == user.pk:
            return False
        return obj.audience_members.filter(user=user).exists()


# class PromptListSerializer là serializer định nghĩa dữ liệu vào/ra (PromptList).
# vd: serializer.data -> JSON cho frontend; is_valid() kiểm tra dữ liệu gửi lên.
class PromptListSerializer(_PromptBaseSerializer):
    # class Meta khai báo metadata (fields, ordering, ràng buộc...) cho model/serializer.
    # vd: ordering=['-created_at'] -> bản ghi mới nhất lên đầu.
    class Meta:
        model = Prompt
        fields = (
            'id',
            'title',
            'system_content',
            'rules_content',
            'usage_scope',
            'status',
            'visibility',
            'owner',
            'owner_name',
            'category_name',
            'group',
            'group_name',
            'tags',
            'source',
            'usage_count',
            'is_mine',
            'can_approve',
            'can_edit',
            'can_delete',
            'my_permission',
            'peer_share_status',
            'peer_share_approver_note',
            'peer_audience_count',
            'is_peer_shared_to_me',
            'created_at',
            'updated_at',
        )


# class PromptDetailSerializer là serializer định nghĩa dữ liệu vào/ra (PromptDetail).
# vd: serializer.data -> JSON cho frontend; is_valid() kiểm tra dữ liệu gửi lên.
class PromptDetailSerializer(_PromptBaseSerializer):
    # class Meta khai báo metadata (fields, ordering, ràng buộc...) cho model/serializer.
    # vd: ordering=['-created_at'] -> bản ghi mới nhất lên đầu.
    class Meta:
        model = Prompt
        fields = (
            'id',
            'title',
            'system_content',
            'rules_content',
            'usage_scope',
            'status',
            'visibility',
            'owner',
            'owner_name',
            'category',
            'category_name',
            'group',
            'group_name',
            'tags',
            'source',
            'usage_count',
            'approver_note',
            'is_mine',
            'can_approve',
            'can_edit',
            'can_delete',
            'my_permission',
            'peer_share_status',
            'peer_share_approver_note',
            'peer_audience_count',
            'is_peer_shared_to_me',
            'created_at',
            'updated_at',
        )
        read_only_fields = (
            'id',
            'owner',
            'owner_name',
            'category_name',
            'group_name',
            'source',
            'usage_count',
            'approver_note',
            'is_mine',
            'can_approve',
            'can_edit',
            'can_delete',
            'my_permission',
            'peer_share_status',
            'peer_share_approver_note',
            'peer_audience_count',
            'is_peer_shared_to_me',
            'created_at',
            'updated_at',
        )


# class PromptWriteSerializer là serializer định nghĩa dữ liệu vào/ra (PromptWrite).
# vd: serializer.data -> JSON cho frontend; is_valid() kiểm tra dữ liệu gửi lên.
class PromptWriteSerializer(serializers.ModelSerializer):
    usage_scope = serializers.ListField(
        child=serializers.ChoiceField(choices=[(key, key) for key in USAGE_SCOPES]),
        required=False,
        allow_empty=False,
    )
    prompt_check_token = serializers.CharField(
        required=False,
        allow_blank=True,
        write_only=True,
    )

    # class Meta khai báo metadata (fields, ordering, ràng buộc...) cho model/serializer.
    # vd: ordering=['-created_at'] -> bản ghi mới nhất lên đầu.
    class Meta:
        model = Prompt
        fields = (
            'title',
            'system_content',
            'rules_content',
            'category',
            'tags',
            'visibility',
            'group',
            'usage_scope',
            'prompt_check_token',
        )

    # def validate_title để kiểm tra hợp lệ title (trong serializer).
    # vd: dữ liệu sai -> báo lỗi/False; hợp lệ -> True hoặc giá trị đã chuẩn hóa.
    def validate_title(self, value):
        title = (value or '').strip()
        if not title:
            raise serializers.ValidationError('Ten prompt khong duoc de trong.')
        if len(title) > 255:
            raise serializers.ValidationError('Ten prompt khong duoc qua 255 ky tu.')
        return title

    # def validate_usage_scope để kiểm tra hợp lệ usage scope (trong serializer).
    # vd: dữ liệu sai -> báo lỗi/False; hợp lệ -> True hoặc giá trị đã chuẩn hóa.
    def validate_usage_scope(self, value):
        scopes = []
        for item in value or []:
            normalized = str(item or '').strip()
            if normalized not in USAGE_SCOPES:
                raise serializers.ValidationError(f"'{normalized}' khong phai scope hop le.")
            if normalized not in scopes:
                scopes.append(normalized)
        if not scopes:
            raise serializers.ValidationError('Phai chon it nhat 1 scope.')
        return scopes

    # def validate để kiểm tra hợp lệ (trong serializer).
    # vd: dữ liệu sai -> báo lỗi/False; hợp lệ -> True hoặc giá trị đã chuẩn hóa.
    def validate(self, attrs):
        request = self.context.get('request')
        user = request.user if request else None
        prompt_check_token = str(attrs.pop('prompt_check_token', '') or '').strip()
        title = (attrs.get('title') or '').strip()
        if user and title:
            qs = Prompt.objects.filter(owner=user, title__iexact=title)
            if self.instance is not None:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError(
                    {'title': 'Ban da co prompt khac cung ten. Vui long doi ten khac.'}
                )

        visibility = attrs.get('visibility') or (self.instance.visibility if self.instance else Prompt.VISIBILITY_PRIVATE)
        group = attrs.get('group', serializers.empty)
        if visibility == Prompt.VISIBILITY_GROUP:
            resolved_group = group if group is not serializers.empty else getattr(self.instance, 'group', None)
            if resolved_group is None:
                raise serializers.ValidationError({'group': 'Phai chon nhom khi pham vi la "Nhom".'})
        elif group is serializers.empty:
            attrs['group'] = None

        if self.instance is None and 'usage_scope' not in attrs:
            attrs['usage_scope'] = default_prompt_usage_scopes()
        if self.instance is not None and 'usage_scope' in attrs and not attrs['usage_scope']:
            raise serializers.ValidationError({'usage_scope': 'Phai chon it nhat 1 scope.'})

        system_content = attrs.get(
            'system_content',
            getattr(self.instance, 'system_content', '') if self.instance else '',
        )
        rules_content = attrs.get(
            'rules_content',
            getattr(self.instance, 'rules_content', '') if self.instance else '',
        )
        prompt_text = '\n\n'.join(
            part.strip()
            for part in (str(system_content or ''), str(rules_content or ''))
            if part.strip()
        )
        if not prompt_text:
            raise serializers.ValidationError({
                'rules_content': 'Prompt phai co noi dung de AI ap dung.',
            })
        if user:
            expected = prompt_check_expected_payload(
                user_id=user.pk,
                scope='saved_prompt',
                context='prompt_library',
                prompt_role='saved_prompt',
                prompt_text=prompt_text,
            )
            ok, why = verify_prompt_check_token(prompt_check_token, expected)
            if not ok:
                raise serializers.ValidationError({
                    'prompt_check_token': (
                        f'Cần kiểm tra lại prompt trước khi lưu ({why}).'
                    ),
                })
        return attrs

    # def create để tạo mới (trong serializer).
    # vd: nhận đầu vào -> trả kết quả đã xử lý.
    def create(self, validated_data):
        from prompts.status_rules import resolve_prompt_status_on_create

        user = self.context['request'].user
        validated_data['owner'] = user
        validated_data['status'] = resolve_prompt_status_on_create(
            user,
            validated_data.get('visibility', Prompt.VISIBILITY_PRIVATE),
            group=validated_data.get('group'),
        )
        validated_data.setdefault('source', Prompt.SOURCE_USER_INLINE)
        validated_data.setdefault('usage_scope', default_prompt_usage_scopes())
        return Prompt.objects.create(**validated_data)

    # def update để cập nhật (trong serializer).
    # vd: nhận đầu vào -> trả kết quả đã xử lý.
    def update(self, instance, validated_data):
        from prompts.status_rules import resolve_prompt_status_on_create

        user = self.context['request'].user
        new_visibility = validated_data.get('visibility', instance.visibility)
        new_group = validated_data.get('group', instance.group)
        if new_visibility != instance.visibility or new_group != instance.group:
            validated_data['status'] = resolve_prompt_status_on_create(user, new_visibility, group=new_group)
        for key, value in validated_data.items():
            setattr(instance, key, value)
        if instance.visibility != Prompt.VISIBILITY_GROUP:
            instance.group = None
        instance.save()
        return instance
