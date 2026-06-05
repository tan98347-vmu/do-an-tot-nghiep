from rest_framework import serializers

from ai_tasks.models import AITaskProgress


class AITaskProgressSerializer(serializers.ModelSerializer):
    is_terminal = serializers.BooleanField(read_only=True)
    is_dismissed = serializers.SerializerMethodField()

    class Meta:
        model = AITaskProgress
        fields = (
            'task_id', 'task_type', 'status',
            'progress_percent', 'progress_stage', 'progress_detail',
            'cancel_requested', 'cancel_mode',
            'result', 'error_message', 'streaming_chunks',
            'related_entity_type', 'related_entity_id',
            'deeplink', 'title_summary', 'client_request_id',
            'created_at', 'updated_at', 'completed_at',
            'is_terminal', 'is_dismissed',
        )
        read_only_fields = fields

    def get_is_dismissed(self, obj: AITaskProgress) -> bool:
        return obj.is_dismissed
