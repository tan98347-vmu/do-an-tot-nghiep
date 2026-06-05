from rest_framework import serializers

from document_templates.manual_edit_models import TemplateManualEditSession
from documents.manual_edit_provider import (
    build_manual_edit_editor_url,
    get_manual_edit_provider_status,
)


class TemplateManualEditFinishSerializer(serializers.Serializer):
    change_note = serializers.CharField(required=False, allow_blank=True, max_length=500)


class TemplateManualEditSessionSerializer(serializers.ModelSerializer):
    template_title = serializers.CharField(source='template.title', read_only=True)
    created_by_name = serializers.SerializerMethodField()
    editor_url = serializers.SerializerMethodField()
    provider_ready = serializers.SerializerMethodField()
    provider_status_code = serializers.SerializerMethodField()
    provider_status_detail = serializers.SerializerMethodField()
    is_active = serializers.SerializerMethodField()

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

    def _provider_status(self):
        cached = self.context.get('_manual_edit_provider_status')
        if cached is not None:
            return cached
        cached = get_manual_edit_provider_status()
        self.context['_manual_edit_provider_status'] = cached
        return cached

    def get_created_by_name(self, obj):
        if obj.created_by_id:
            return obj.created_by.get_full_name() or obj.created_by.username
        return ''

    def get_editor_url(self, obj):
        request = self.context.get('request')
        if request is None:
            return None
        return build_manual_edit_editor_url(
            obj,
            request,
            wopi_route_name='api:template_manual_edit_wopi_file',
        )

    def get_provider_ready(self, obj):
        return self._provider_status().is_ready

    def get_provider_status_code(self, obj):
        return self._provider_status().code

    def get_provider_status_detail(self, obj):
        return self._provider_status().detail

    def get_is_active(self, obj):
        return obj.is_active
