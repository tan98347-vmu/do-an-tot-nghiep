from django.conf import settings
from django.db import models

from accounts.storage_paths import company_media_path
from documents.models import Document


def _word_ai_artifact_upload(instance, filename):
    return company_media_path(
        company=getattr(instance, 'company', None) or getattr(getattr(instance, 'document', None), 'company', None),
        section='word_ai/jobs',
        parts=[f'job_{instance.pk or "pending"}'],
        filename=filename,
    )


class WordWorkerStatus(models.TextChoices):
    IDLE = 'idle', 'Idle'
    BUSY = 'busy', 'Busy'
    PAUSED = 'paused', 'Paused'
    OFFLINE = 'offline', 'Offline'


class WordEditJobStatus(models.TextChoices):
    QUEUED = 'queued', 'Queued'
    CLAIMED = 'claimed', 'Claimed'
    EDITING = 'editing', 'Editing'
    UPLOADING = 'uploading', 'Uploading'
    COMPLETED = 'completed', 'Completed'
    FAILED = 'failed', 'Failed'
    CANCELLED = 'cancelled', 'Cancelled'
    NEEDS_REVIEW = 'needs_review', 'Needs review'


class WordWorker(models.Model):
    worker_key = models.CharField(max_length=100, unique=True)
    slot_label = models.CharField(max_length=32)
    host_name = models.CharField(max_length=120, blank=True)
    status = models.CharField(
        max_length=16,
        choices=WordWorkerStatus.choices,
        default=WordWorkerStatus.IDLE,
    )
    metadata = models.JSONField(default=dict, blank=True)
    last_seen_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['worker_key']

    def __str__(self):
        return f'{self.worker_key} ({self.slot_label})'


class WordEditJob(models.Model):
    document = models.ForeignKey(
        Document,
        on_delete=models.CASCADE,
        related_name='word_ai_jobs',
    )
    company = models.ForeignKey(
        'accounts.Company',
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name='word_ai_jobs',
    )
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='requested_word_ai_jobs',
    )
    current_worker = models.ForeignKey(
        WordWorker,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='claimed_jobs',
    )
    result_version = models.ForeignKey(
        'documents.DocumentVersion',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='word_ai_jobs',
    )
    applied_prompt = models.ForeignKey(
        'prompts.Prompt',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='word_ai_jobs',
    )
    instruction = models.TextField()
    edit_mode = models.CharField(max_length=32, default='direct_addin_mcp')
    plan_mode = models.CharField(max_length=32, blank=True)
    preferred_slot = models.CharField(max_length=32, blank=True)
    current_slot_label = models.CharField(max_length=32, blank=True)
    track_changes = models.BooleanField(default=False)
    status = models.CharField(
        max_length=24,
        choices=WordEditJobStatus.choices,
        default=WordEditJobStatus.QUEUED,
        db_index=True,
    )
    llm_model_name = models.CharField(max_length=120, blank=True)
    llm_temperature = models.FloatField(default=0)
    ollama_base_url = models.CharField(max_length=255, blank=True)
    prompt_version = models.CharField(max_length=64, blank=True)
    allow_cloud_model = models.BooleanField(default=True)
    plan_payload = models.JSONField(default=dict, blank=True)
    mcp_session_id = models.CharField(max_length=120, blank=True)
    execution_payload = models.JSONField(default=dict, blank=True)
    heartbeat_payload = models.JSONField(default=dict, blank=True)
    tool_transcript = models.JSONField(default=list, blank=True)
    verification_summary = models.JSONField(default=dict, blank=True)
    artifact_manifest = models.JSONField(default=dict, blank=True)
    document_checksums = models.JSONField(default=dict, blank=True)
    result_summary = models.TextField(blank=True)
    change_note = models.CharField(max_length=500, blank=True)
    error_code = models.CharField(max_length=120, blank=True)
    error_detail = models.TextField(blank=True)
    artifact_file = models.FileField(
        upload_to=_word_ai_artifact_upload,
        max_length=500,
        blank=True,
        null=True,
    )
    claimed_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    failed_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'created_at'], name='word_ai_job_status_created_idx'),
            models.Index(fields=['document', 'status'], name='word_ai_job_doc_status_idx'),
        ]

    def __str__(self):
        return f'WordEditJob#{self.pk} {self.document_id} {self.status}'

    def save(self, *args, **kwargs):
        if self.company_id is None and self.document_id and getattr(self.document, 'company_id', None):
            self.company = self.document.company
        super().save(*args, **kwargs)

    @property
    def is_terminal(self):
        return self.status in {
            WordEditJobStatus.COMPLETED,
            WordEditJobStatus.FAILED,
            WordEditJobStatus.CANCELLED,
            WordEditJobStatus.NEEDS_REVIEW,
        }


class WordEditJobEvent(models.Model):
    job = models.ForeignKey(
        WordEditJob,
        on_delete=models.CASCADE,
        related_name='events',
    )
    worker = models.ForeignKey(
        WordWorker,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='events',
    )
    level = models.CharField(max_length=16, default='info')
    step = models.CharField(max_length=64, blank=True)
    status = models.CharField(max_length=32, blank=True)
    message = models.TextField(blank=True)
    payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at', 'id']

    def __str__(self):
        return f'WordEditJobEvent#{self.pk} job={self.job_id} step={self.step}'
