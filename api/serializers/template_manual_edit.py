from rest_framework import serializers

from document_templates.manual_edit_models import TemplateManualEditSession
from documents.manual_edit_provider import (
    build_manual_edit_editor_url,
    get_manual_edit_provider_status,
)


# class TemplateManualEditFinishSerializer là serializer định nghĩa dữ liệu vào/ra (TemplateManualEditFinish).
# vd: serializer.data -> JSON cho frontend; is_valid() kiểm tra dữ liệu gửi lên.
class TemplateManualEditFinishSerializer(serializers.Serializer):
    change_note = serializers.CharField(required=False, allow_blank=True, max_length=500)


# class TemplateManualEditSessionSerializer là serializer định nghĩa dữ liệu vào/ra (TemplateManualEditSession).
# vd: serializer.data -> JSON cho frontend; is_valid() kiểm tra dữ liệu gửi lên.
class TemplateManualEditSessionSerializer(serializers.ModelSerializer):
    template_title = serializers.CharField(source='template.title', read_only=True)
    created_by_name = serializers.SerializerMethodField()
    editor_url = serializers.SerializerMethodField()
    provider_ready = serializers.SerializerMethodField()
    provider_status_code = serializers.SerializerMethodField()
    provider_status_detail = serializers.SerializerMethodField()
    is_active = serializers.SerializerMethodField()

    # class Meta khai báo metadata (fields, ordering, ràng buộc...) cho model/serializer.
    # vd: ordering=['-created_at'] -> bản ghi mới nhất lên đầu.
    class Meta:
        model = TemplateManualEditSession
        fields = (
            'id',
            'template',
            'template_title',
            'created_by',
            'created_by_name',
            'status',
            'provider',
            'base_version_label',
            'working_copy_updated_at',
            'expires_at',
            'last_activity_at',
            'finished_at',
            'cancelled_at',
            'created_at',
            'updated_at',
            'editor_url',
            'provider_ready',
            'provider_status_code',
            'provider_status_detail',
            'is_active',
        )
        read_only_fields = fields

    # def _provider_status để provider status (trong serializer).
    # vd: nhận đầu vào -> trả kết quả đã xử lý.
    def _provider_status(self):
        cached = self.context.get('_manual_edit_provider_status')
        if cached is not None:
            return cached
        cached = get_manual_edit_provider_status()
        self.context['_manual_edit_provider_status'] = cached
        return cached

    # def get_created_by_name để lấy created by name (trong serializer).
    # vd: nhận điều kiện -> trả về dữ liệu phù hợp.
    def get_created_by_name(self, obj):
        if obj.created_by_id:
            return obj.created_by.get_full_name() or obj.created_by.username
        return ''

    # def get_editor_url để lấy editor url (trong serializer).
    # vd: nhận điều kiện -> trả về dữ liệu phù hợp.
    def get_editor_url(self, obj):
        request = self.context.get('request')
        if request is None:
            return None
        return build_manual_edit_editor_url(
            obj,
            request,
            wopi_route_name='api:template_manual_edit_wopi_file',
        )

    # def get_provider_ready để lấy provider ready (trong serializer).
    # vd: nhận điều kiện -> trả về dữ liệu phù hợp.
    def get_provider_ready(self, obj):
        return self._provider_status().is_ready

    # def get_provider_status_code để lấy provider status code (trong serializer).
    # vd: nhận điều kiện -> trả về dữ liệu phù hợp.
    def get_provider_status_code(self, obj):
        return self._provider_status().code

    # def get_provider_status_detail để lấy provider status detail (trong serializer).
    # vd: nhận đầu vào -> trả kết quả đã xử lý.
    def get_provider_status_detail(self, obj):
        return self._provider_status().detail

    # def get_is_active để lấy is active (trong serializer).
    # vd: nhận điều kiện -> trả về dữ liệu phù hợp.
    def get_is_active(self, obj):
        return obj.is_active
