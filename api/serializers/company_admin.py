from django.contrib.auth.models import User
from rest_framework import serializers

from accounts.models import CompanyAIConfig, CompanyPosition, Department, UserGroup, UserGroupMembership


# class CompanyAdminUserSerializer là serializer định nghĩa dữ liệu vào/ra (CompanyAdminUser).
# vd: serializer.data -> JSON cho frontend; is_valid() kiểm tra dữ liệu gửi lên.
class CompanyAdminUserSerializer(serializers.ModelSerializer):
    username = serializers.SerializerMethodField()
    technical_username = serializers.CharField(source='username', read_only=True)
    chuc_danh = serializers.SerializerMethodField()
    groups = serializers.SerializerMethodField()
    company_role = serializers.SerializerMethodField()

    # class Meta khai báo metadata (fields, ordering, ràng buộc...) cho model/serializer.
    # vd: ordering=['-created_at'] -> bản ghi mới nhất lên đầu.
    class Meta:
        model = User
        fields = (
            'id',
            'username',
            'technical_username',
            'email',
            'first_name',
            'last_name',
            'is_staff',
            'is_superuser',
            'is_active',
            'company_role',
            'chuc_danh',
            'groups',
            'date_joined',
        )

    # def get_username để lấy username (trong serializer).
    # vd: nhận điều kiện -> trả về dữ liệu phù hợp.
    def get_username(self, obj):
        membership = getattr(obj, 'company_membership', None)
        return membership.local_username if membership else obj.username

    # def get_chuc_danh để lấy chuc danh (trong serializer).
    # vd: nhận điều kiện -> trả về dữ liệu phù hợp.
    def get_chuc_danh(self, obj):
        try:
            return obj.profile.chuc_danh
        except Exception:
            return ''

    # def get_groups để lấy groups (trong serializer).
    # vd: nhận điều kiện -> trả về dữ liệu phù hợp.
    def get_groups(self, obj):
        memberships = obj.group_memberships.select_related('group').all()
        company = self.context.get('company')
        if company is not None:
            memberships = memberships.filter(group__company=company)
        return [
            {'id': membership.group_id, 'name': membership.group.name, 'role': membership.role}
            for membership in memberships
        ]

    # def get_company_role để lấy company role (trong serializer).
    # vd: nhận điều kiện -> trả về dữ liệu phù hợp.
    def get_company_role(self, obj):
        membership = getattr(obj, 'company_membership', None)
        return getattr(membership, 'role', None)


# class CompanyAdminGroupSerializer là serializer định nghĩa dữ liệu vào/ra (CompanyAdminGroup).
# vd: serializer.data -> JSON cho frontend; is_valid() kiểm tra dữ liệu gửi lên.
class CompanyAdminGroupSerializer(serializers.ModelSerializer):
    member_count = serializers.SerializerMethodField()
    document_count = serializers.SerializerMethodField()
    template_count = serializers.SerializerMethodField()

    # class Meta khai báo metadata (fields, ordering, ràng buộc...) cho model/serializer.
    # vd: ordering=['-created_at'] -> bản ghi mới nhất lên đầu.
    class Meta:
        model = UserGroup
        fields = (
            'id',
            'name',
            'description',
            'member_count',
            'document_count',
            'template_count',
            'created_at',
        )

    # def get_member_count để lấy member count (trong serializer).
    # vd: nhận đầu vào -> trả kết quả đã xử lý.
    def get_member_count(self, obj):
        return obj.memberships.count()

    # def get_document_count để lấy document count (trong serializer).
    # vd: nhận đầu vào -> trả kết quả đã xử lý.
    def get_document_count(self, obj):
        return obj.documents.count()

    # def get_template_count để lấy template count (trong serializer).
    # vd: nhận đầu vào -> trả kết quả đã xử lý.
    def get_template_count(self, obj):
        return obj.templates.count()


# class CompanyAdminGroupDetailSerializer là serializer định nghĩa dữ liệu vào/ra (CompanyAdminGroupDetail).
# vd: serializer.data -> JSON cho frontend; is_valid() kiểm tra dữ liệu gửi lên.
class CompanyAdminGroupDetailSerializer(CompanyAdminGroupSerializer):
    members = serializers.SerializerMethodField()

    # class Meta khai báo metadata (fields, ordering, ràng buộc...) cho model/serializer.
    # vd: ordering=['-created_at'] -> bản ghi mới nhất lên đầu.
    class Meta(CompanyAdminGroupSerializer.Meta):
        fields = CompanyAdminGroupSerializer.Meta.fields + ('members',)

    # def get_members để lấy members (trong serializer).
    # vd: nhận điều kiện -> trả về dữ liệu phù hợp.
    def get_members(self, obj):
        memberships = obj.memberships.select_related('user').all()
        return [
            {
                'user_id': membership.user_id,
                'username': getattr(membership.user.company_membership, 'local_username', membership.user.username),
                'full_name': membership.user.get_full_name() or membership.user.username,
                'role': membership.role,
            }
            for membership in memberships
        ]


# class CompanyAIConfigSerializer là serializer định nghĩa dữ liệu vào/ra (CompanyAIConfig).
# vd: serializer.data -> JSON cho frontend; is_valid() kiểm tra dữ liệu gửi lên.
class CompanyAIConfigSerializer(serializers.ModelSerializer):
    # class Meta khai báo metadata (fields, ordering, ràng buộc...) cho model/serializer.
    # vd: ordering=['-created_at'] -> bản ghi mới nhất lên đầu.
    class Meta:
        model = CompanyAIConfig
        fields = (
            'ai_model',
            'chat_ai_model',
            'ocr_model',
            'image_ocr_model',
            'ai_temperature',
            'ai_max_results',
            'embedding_model',
            'company_context',
            'ai_internet_results',
            'ai_search_engine',
            'updated_at',
        )

    # def validate_chat_ai_model để kiểm tra hợp lệ chat ai model (trong serializer).
    # vd: dữ liệu sai -> báo lỗi/False; hợp lệ -> True hoặc giá trị đã chuẩn hóa.
    def validate_chat_ai_model(self, value):
        return str(value or '').strip()


# class CompanyAdminDepartmentSerializer là serializer định nghĩa dữ liệu vào/ra (CompanyAdminDepartment).
# vd: serializer.data -> JSON cho frontend; is_valid() kiểm tra dữ liệu gửi lên.
class CompanyAdminDepartmentSerializer(serializers.ModelSerializer):
    member_count = serializers.SerializerMethodField()

    # class Meta khai báo metadata (fields, ordering, ràng buộc...) cho model/serializer.
    # vd: ordering=['-created_at'] -> bản ghi mới nhất lên đầu.
    class Meta:
        model = Department
        fields = (
            'id',
            'name',
            'code',
            'description',
            'is_active',
            'member_count',
            'created_at',
        )

    # def get_member_count để lấy member count (trong serializer).
    # vd: nhận đầu vào -> trả kết quả đã xử lý.
    def get_member_count(self, obj):
        return obj.memberships.filter(is_active=True).count()


# class CompanyAdminPositionSerializer là serializer định nghĩa dữ liệu vào/ra (CompanyAdminPosition).
# vd: serializer.data -> JSON cho frontend; is_valid() kiểm tra dữ liệu gửi lên.
class CompanyAdminPositionSerializer(serializers.ModelSerializer):
    user_count = serializers.SerializerMethodField()

    # class Meta khai báo metadata (fields, ordering, ràng buộc...) cho model/serializer.
    # vd: ordering=['-created_at'] -> bản ghi mới nhất lên đầu.
    class Meta:
        model = CompanyPosition
        fields = (
            'id',
            'code',
            'name',
            'description',
            'is_active',
            'user_count',
            'created_at',
        )

    # def get_user_count để lấy user count (trong serializer).
    # vd: nhận đầu vào -> trả kết quả đã xử lý.
    def get_user_count(self, obj):
        return obj.company.profiles.filter(chuc_danh__iexact=obj.name).count()
