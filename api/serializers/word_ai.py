from rest_framework import serializers

from api.serializers.documents import DocumentDetailSerializer, DocumentVersionSerializer
from word_ai.models import WordEditJob, WordEditJobEvent, WordWorker


class WordEditJobCreateSerializer(serializers.Serializer):
    document_id = serializers.IntegerField()
    instruction = serializers.CharField()
    prompt_id = serializers.IntegerField(required=False, allow_null=True)
    edit_mode = serializers.CharField(required=False, allow_blank=True, default='')
    track_changes = serializers.BooleanField(required=False, default=False)
    preferred_slot = serializers.CharField(required=False, allow_blank=True, default='')


class WordEditJobEventSerializer(serializers.ModelSerializer):
    worker_key = serializers.CharField(source='worker.worker_key', read_only=True)

    class Meta:
        model = WordEditJobEvent
        fields = (
            'id',
            'created_at',
            'level',
            'step',
            'status',
            'message',
            'payload',
            'worker_key',
        )


class WordEditJobSerializer(serializers.ModelSerializer):
    document_title = serializers.CharField(source='document.title', read_only=True)
    requested_by_name = serializers.SerializerMethodField()
    applied_prompt = serializers.SerializerMethodField()
    current_worker_key = serializers.CharField(source='current_worker.worker_key', read_only=True)
    latest_event = serializers.SerializerMethodField()

    class Meta:
        model = WordEditJob
        fields = (
            'id',
            'document',
            'document_title',
            'requested_by',
            'requested_by_name',
            'instruction',
            'applied_prompt',
            'edit_mode',
            'plan_mode',
            'preferred_slot',
            'current_slot_label',
            'track_changes',
            'status',
            'llm_model_name',
            'llm_temperature',
            'ollama_base_url',
            'prompt_version',
            'mcp_session_id',
            'plan_payload',
            'execution_payload',
            'tool_transcript',
            'verification_summary',
            'artifact_manifest',
            'document_checksums',
            'result_summary',
            'change_note',
            'error_code',
            'error_detail',
            'current_worker_key',
            'claimed_at',
            'completed_at',
            'failed_at',
            'cancelled_at',
            'created_at',
            'updated_at',
            'latest_event',
        )

    def get_requested_by_name(self, obj):
        return obj.requested_by.get_full_name() or obj.requested_by.username

    def get_applied_prompt(self, obj):
        prompt = getattr(obj, 'applied_prompt', None)
        if prompt is None:
            return None
        return {
            'id': prompt.id,
            'title': prompt.title,
        }

    def get_latest_event(self, obj):
        event = obj.events.order_by('-created_at', '-id').first()
        if not event:
            return None
        return WordEditJobEventSerializer(event).data


class WordEditJobDetailSerializer(WordEditJobSerializer):
    events = WordEditJobEventSerializer(many=True, read_only=True)
    document_detail = DocumentDetailSerializer(source='document', read_only=True)

    class Meta(WordEditJobSerializer.Meta):
        fields = WordEditJobSerializer.Meta.fields + ('events', 'document_detail')


class WordWorkerClaimSerializer(serializers.Serializer):
    worker_key = serializers.CharField()
    slot_label = serializers.CharField()
    host_name = serializers.CharField(required=False, allow_blank=True, default='')
    metadata = serializers.JSONField(required=False)


class WordWorkerHeartbeatSerializer(serializers.Serializer):
    worker_key = serializers.CharField()
    slot_label = serializers.CharField()
    status = serializers.CharField(required=False, allow_blank=True, default='')
    metadata = serializers.JSONField(required=False)
    current_job_id = serializers.IntegerField(required=False, allow_null=True)


class WordEditJobCompleteSerializer(serializers.Serializer):
    worker_key = serializers.CharField()
    summary = serializers.CharField(required=False, allow_blank=True, default='')
    change_note = serializers.CharField(required=False, allow_blank=True, default='')
    content_text = serializers.CharField(required=False, allow_blank=True, default='')
    tool_transcript = serializers.JSONField(required=False, default=list)
    verification_summary = serializers.JSONField(required=False, default=dict)
    artifact_manifest = serializers.JSONField(required=False, default=dict)
    document_checksums = serializers.JSONField(required=False, default=dict)
    output_file = serializers.FileField()


class WordEditJobFailSerializer(serializers.Serializer):
    worker_key = serializers.CharField()
    error_code = serializers.CharField()
    error_detail = serializers.CharField(required=False, allow_blank=True, default='')
    tool_transcript = serializers.JSONField(required=False, default=list)
    verification_summary = serializers.JSONField(required=False, default=dict)
    failure_payload = serializers.JSONField(required=False)


class WordEditJobWorkerEventSerializer(serializers.Serializer):
    worker_key = serializers.CharField()
    step = serializers.CharField()
    status = serializers.CharField(required=False, allow_blank=True, default='')
    message = serializers.CharField(required=False, allow_blank=True, default='')
    level = serializers.CharField(required=False, allow_blank=True, default='info')
    payload = serializers.JSONField(required=False)


class WordEditJobMcpAdvanceSerializer(serializers.Serializer):
    worker_key = serializers.CharField()
    session_id = serializers.CharField()
    latest_command = serializers.JSONField(required=False, default=dict)
    tool_transcript = serializers.JSONField(required=False, default=list)
    session_snapshot = serializers.JSONField(required=False, default=dict)


class WordEditJobCompleteResponseSerializer(serializers.Serializer):
    job = WordEditJobDetailSerializer()
    document = DocumentDetailSerializer()
    version = DocumentVersionSerializer()


class WordWorkerSerializer(serializers.ModelSerializer):
    class Meta:
        model = WordWorker
        fields = (
            'id',
            'worker_key',
            'slot_label',
            'host_name',
            'status',
            'metadata',
            'last_seen_at',
            'created_at',
            'updated_at',
        )
