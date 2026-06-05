import uuid

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import models


TASK_TYPE_DOC_CREATE = 'doc_create'
TASK_TYPE_PREFILL_PROFILE = 'prefill_profile'
TASK_TYPE_PREFILL_COMPANY = 'prefill_company'
TASK_TYPE_EXTRACT_PDF = 'extract_pdf'
TASK_TYPE_EXTRACT_IMAGE = 'extract_image'
TASK_TYPE_SUMMARIZE = 'summarize'
TASK_TYPE_CHAT = 'chat'
TASK_TYPE_VOICE = 'voice'
TASK_TYPE_VOICE_CHAT = 'voice_chat'
TASK_TYPE_BULK_TEMPLATE_UPLOAD = 'bulk_template_upload'
TASK_TYPE_DOCUMENT_SUMMARY = 'document_summary'
TASK_TYPE_COMPLIANCE_CHECK = 'compliance_check'
TASK_TYPE_WORD_AI_EDIT = 'word_ai_edit'
TASK_TYPE_COMPANY_BACKUP_EXPORT = 'company_backup_export'

TASK_TYPE_CHOICES = [
    (TASK_TYPE_DOC_CREATE, 'Sinh văn bản từ mẫu'),
    (TASK_TYPE_PREFILL_PROFILE, 'Điền từ hồ sơ'),
    (TASK_TYPE_PREFILL_COMPANY, 'Điền từ ngữ cảnh công ty'),
    (TASK_TYPE_EXTRACT_PDF, 'Trích xuất PDF'),
    (TASK_TYPE_EXTRACT_IMAGE, 'Trích xuất ảnh/camera'),
    (TASK_TYPE_SUMMARIZE, 'Tóm tắt văn bản'),
    (TASK_TYPE_CHAT, 'Chat AI'),
    (TASK_TYPE_VOICE, 'Voice AI'),
    (TASK_TYPE_VOICE_CHAT, 'Voice chat background'),
    (TASK_TYPE_BULK_TEMPLATE_UPLOAD, 'Bulk upload biểu mẫu'),
    (TASK_TYPE_DOCUMENT_SUMMARY, 'Tóm tắt văn bản nền'),
    (TASK_TYPE_COMPLIANCE_CHECK, 'Kiểm tra tuân thủ'),
    (TASK_TYPE_WORD_AI_EDIT, 'Word AI edit'),
    (TASK_TYPE_COMPANY_BACKUP_EXPORT, 'Xuất backup công ty'),
]

STATUS_QUEUED = 'queued'
STATUS_RUNNING = 'running'
STATUS_COMPLETED = 'completed'
STATUS_FAILED = 'failed'
STATUS_CANCELLED = 'cancelled'

STATUS_CHOICES = [
    (STATUS_QUEUED, 'Chờ chạy'),
    (STATUS_RUNNING, 'Đang chạy'),
    (STATUS_COMPLETED, 'Hoàn tất'),
    (STATUS_FAILED, 'Thất bại'),
    (STATUS_CANCELLED, 'Đã dừng'),
]

CANCEL_MODE_SOFT = 'soft'
CANCEL_MODE_HARD = 'hard'
CANCEL_MODE_CHOICES = [
    (CANCEL_MODE_SOFT, 'Soft (cooperative)'),
    (CANCEL_MODE_HARD, 'Hard (abort connection)'),
]

TERMINAL_STATUSES = {STATUS_COMPLETED, STATUS_FAILED, STATUS_CANCELLED}


def validate_deeplink(value: str) -> None:
    if not value:
        return
    if not isinstance(value, str) or not value.startswith('/'):
        raise ValidationError('deeplink phải bắt đầu bằng "/".')
    if '\\' in value or '..' in value:
        raise ValidationError('deeplink không hợp lệ.')


class AITaskProgress(models.Model):
    task_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='ai_tasks')
    task_type = models.CharField(max_length=32, choices=TASK_TYPE_CHOICES, db_index=True)
    status = models.CharField(
        max_length=16, choices=STATUS_CHOICES, default=STATUS_QUEUED, db_index=True,
    )
    progress_percent = models.PositiveSmallIntegerField(default=0)
    progress_stage = models.CharField(max_length=64, blank=True)
    progress_detail = models.CharField(max_length=255, blank=True)
    cancel_requested = models.BooleanField(default=False)
    cancel_mode = models.CharField(
        max_length=8, choices=CANCEL_MODE_CHOICES, default=CANCEL_MODE_SOFT,
    )
    result = models.JSONField(null=True, blank=True)
    error_message = models.TextField(blank=True)
    streaming_chunks = models.JSONField(default=list, blank=True)
    related_entity_type = models.CharField(max_length=32, blank=True)
    related_entity_id = models.IntegerField(null=True, blank=True)
    deeplink = models.CharField(
        max_length=512,
        blank=True,
        default='',
        validators=[validate_deeplink],
    )
    title_summary = models.CharField(max_length=255, blank=True, default='')
    client_request_id = models.CharField(max_length=64, blank=True, default='', db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = 'AI Task Progress'
        verbose_name_plural = 'AI Task Progress'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['status', '-created_at']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'client_request_id'],
                condition=models.Q(client_request_id__gt=''),
                name='uniq_user_client_request',
            ),
        ]

    def __str__(self):
        title = f' {self.title_summary}' if self.title_summary else ''
        return f'{self.task_type}/{self.status}{title} {self.progress_percent}%'

    @property
    def is_terminal(self) -> bool:
        return self.status in TERMINAL_STATUSES

    @property
    def is_dismissed(self) -> bool:
        return bool((self.result or {}).get('dismissed'))
