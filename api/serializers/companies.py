from rest_framework import serializers

from accounts.company_lifecycle_services import get_company_bootstrap_admin_membership
from accounts.models import Company, CompanyAIConfig, CompanyStatus


# class CompanySummarySerializer là serializer định nghĩa dữ liệu vào/ra (CompanySummary).
# vd: serializer.data -> JSON cho frontend; is_valid() kiểm tra dữ liệu gửi lên.
class CompanySummarySerializer(serializers.ModelSerializer):
    user_count = serializers.SerializerMethodField()
    department_count = serializers.SerializerMethodField()
    position_count = serializers.SerializerMethodField()
    group_count = serializers.SerializerMethodField()

    # class Meta khai báo metadata (fields, ordering, ràng buộc...) cho model/serializer.
    # vd: ordering=['-created_at'] -> bản ghi mới nhất lên đầu.
    class Meta:
        model = Company
        fields = (
            'id',
            'code',
            'slug',
            'name',
            'status',
            'description',
            'industry',
            'email',
            'phone',
            'website',
            'updated_at',
            'user_count',
            'department_count',
            'position_count',
            'group_count',
        )

    # def get_user_count để lấy user count (trong serializer).
    # vd: nhận đầu vào -> trả kết quả đã xử lý.
    def get_user_count(self, obj):
        return obj.memberships.count()

    # def get_department_count để lấy department count (trong serializer).
    # vd: nhận đầu vào -> trả kết quả đã xử lý.
    def get_department_count(self, obj):
        return obj.departments.count()

    # def get_position_count để lấy position count (trong serializer).
    # vd: nhận đầu vào -> trả kết quả đã xử lý.
    def get_position_count(self, obj):
        return obj.positions.count()

    # def get_group_count để lấy group count (trong serializer).
    # vd: nhận đầu vào -> trả kết quả đã xử lý.
    def get_group_count(self, obj):
        return obj.user_groups.count()


# class CompanyDetailSerializer là serializer định nghĩa dữ liệu vào/ra (CompanyDetail).
# vd: serializer.data -> JSON cho frontend; is_valid() kiểm tra dữ liệu gửi lên.
class CompanyDetailSerializer(CompanySummarySerializer):
    bootstrap_admin = serializers.SerializerMethodField()
    recent_import_batches = serializers.SerializerMethodField()

    # class Meta khai báo metadata (fields, ordering, ràng buộc...) cho model/serializer.
    # vd: ordering=['-created_at'] -> bản ghi mới nhất lên đầu.
    class Meta(CompanySummarySerializer.Meta):
        fields = CompanySummarySerializer.Meta.fields + (
            'address',
            'company_context',
            'created_at',
            'bootstrap_admin',
            'recent_import_batches',
        )

    # def get_bootstrap_admin để lấy bootstrap admin (trong serializer).
    # vd: nhận điều kiện -> trả về dữ liệu phù hợp.
    def get_bootstrap_admin(self, obj):
        membership = get_company_bootstrap_admin_membership(obj)
        if membership is None:
            return None
        return {
            'user_id': membership.user_id,
            'username': membership.local_username,
            'email': membership.user.email,
            'must_change_password': membership.must_change_password,
        }

    # def get_recent_import_batches để lấy recent import batches (trong serializer).
    # vd: nhận điều kiện -> trả về dữ liệu phù hợp.
    def get_recent_import_batches(self, obj):
        return [
            {
                'id': batch.id,
                'status': batch.status,
                'source_type': batch.source_type,
                'validation_error_count': len(batch.validation_errors or []),
                'created_at': batch.created_at,
            }
            for batch in obj.import_batches.order_by('-created_at')[:10]
        ]


# class CompanyCreateUpdateSerializer là serializer định nghĩa dữ liệu vào/ra (CompanyCreateUpdate).
# vd: serializer.data -> JSON cho frontend; is_valid() kiểm tra dữ liệu gửi lên.
class CompanyCreateUpdateSerializer(serializers.Serializer):
    code = serializers.CharField(max_length=50)
    name = serializers.CharField(max_length=255)
    status = serializers.ChoiceField(choices=CompanyStatus.choices, required=False)
    description = serializers.CharField(required=False, allow_blank=True)
    industry = serializers.CharField(required=False, allow_blank=True)
    address = serializers.CharField(required=False, allow_blank=True)
    email = serializers.EmailField(required=False, allow_blank=True)
    phone = serializers.CharField(required=False, allow_blank=True)
    website = serializers.CharField(required=False, allow_blank=True)
    company_context = serializers.CharField(required=False, allow_blank=True)
    admin_email = serializers.EmailField(required=False, allow_blank=True)
    admin_full_name = serializers.CharField(required=False, allow_blank=True)
    admin_password = serializers.CharField(required=False, allow_blank=True)
    departments = serializers.ListField(child=serializers.DictField(), required=False)
    positions = serializers.ListField(child=serializers.DictField(), required=False)
    employees = serializers.ListField(child=serializers.DictField(), required=False)

    # def validate_code để kiểm tra hợp lệ code (trong serializer).
    # vd: dữ liệu sai -> báo lỗi/False; hợp lệ -> True hoặc giá trị đã chuẩn hóa.
    def validate_code(self, value):
        return str(value or '').strip().lower()

    # def validate_name để kiểm tra hợp lệ name (trong serializer).
    # vd: dữ liệu sai -> báo lỗi/False; hợp lệ -> True hoặc giá trị đã chuẩn hóa.
    def validate_name(self, value):
        value = str(value or '').strip()
        if not value:
            raise serializers.ValidationError('Ten cong ty khong duoc de trong.')
        return value

    # def validate để kiểm tra hợp lệ (trong serializer).
    # vd: dữ liệu sai -> báo lỗi/False; hợp lệ -> True hoặc giá trị đã chuẩn hóa.
    def validate(self, attrs):
        company = self.context.get('company')
        code = attrs.get('code')
        qs = Company.objects.filter(code__iexact=code)
        if company is not None:
            qs = qs.exclude(pk=company.pk)
        if qs.exists():
            raise serializers.ValidationError({'code': 'Ma cong ty da ton tai.'})
        return attrs


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
