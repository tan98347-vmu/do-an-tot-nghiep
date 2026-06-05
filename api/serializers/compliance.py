from rest_framework import serializers

from ai_engine.models import ComplianceCheckResult

PASS_MESSAGE = 'Văn bản/mẫu văn bản đã đáp ứng được những yêu cầu mà bạn đưa ra'


class ComplianceCheckRunSerializer(serializers.Serializer):
    target_type = serializers.ChoiceField(choices=('document', 'template'))
    target_id = serializers.IntegerField(min_value=1)
    prompt_id = serializers.IntegerField(min_value=1)
    force = serializers.BooleanField(required=False, default=False)


class ComplianceCheckResultSerializer(serializers.ModelSerializer):
    items_missing = serializers.JSONField(source='items_missing_json', read_only=True)
    message = serializers.SerializerMethodField()
    checked_at = serializers.SerializerMethodField()
    prompt_title = serializers.SerializerMethodField()
    created_by_name = serializers.SerializerMethodField()

    class Meta:
        model = ComplianceCheckResult
        fields = (
            'id',
            'passed',
            'items_missing',
            'message',
            'checked_at',
            'prompt_id',
            'prompt_title',
            'target_type',
            'target_id',
            'created_by_name',
        )

    def get_message(self, obj):
        if obj.passed:
            return PASS_MESSAGE
        return None

    def get_checked_at(self, obj):
        return obj.created_at.isoformat()

    def get_prompt_title(self, obj):
        prompt = getattr(obj, 'prompt', None)
        return prompt.title if prompt else None

    def get_created_by_name(self, obj):
        user = getattr(obj, 'created_by', None)
        if user is None:
            return ''
        return user.get_full_name().strip() or user.username
