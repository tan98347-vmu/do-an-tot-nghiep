import uuid

from django.conf import settings
from django.db import models

from accounts.storage_paths import company_media_path

def _manual_edit_working_copy_upload_to(instance, filename):
    ext = '.docx'
    raw_name = str(filename or '').strip()
    if '.' in raw_name:
        ext = f".{raw_name.rsplit('.', 1)[-1].lower()}"
    return company_media_path(
        company=getattr(instance, 'company', None) or getattr(getattr(instance, 'document', None), 'company', None),
        section='manual_edit_working_copies',
        parts=[f'document_{instance.document_id or "unknown"}'],
        filename=f'{instance.wopi_file_id}{ext}',
    )


class DocumentManualEditSession(models.Model):
    class Status(models.TextChoices):
        CREATED = 'created', 'Created'
        ACTIVE = 'active', 'Active'
        SAVING = 'saving', 'Saving'
        FINISHED = 'finished', 'Finished'
        CANCELLED = 'cancelled', 'Cancelled'
        EXPIRED = 'expired', 'Expired'
        FAILED = 'failed', 'Failed'

    document = models.ForeignKey(
        'documents.Document',
        on_delete=models.CASCADE,
        related_name='manual_edit_sessions',
    )
    company = models.ForeignKey(
        'accounts.Company',
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name='manual_edit_sessions',
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='document_manual_edit_sessions',
    )
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.CREATED,
        db_index=True,
    )
    provider = models.CharField(max_length=32, default='collabora')
    access_token = models.CharField(max_length=128, unique=True, db_index=True)
    wopi_file_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    working_copy_file = models.FileField(
        upload_to=_manual_edit_working_copy_upload_to,
        max_length=500,
        blank=True,
        null=True,
    )
    working_copy_updated_at = models.DateTimeField(null=True, blank=True)
    base_version_number = models.IntegerField(default=1)
    committed_version = models.ForeignKey(
        'documents.DocumentVersion',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='manual_edit_source_sessions',
    )
    lock_token = models.CharField(max_length=255, blank=True)
    lock_token_refreshed_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(db_index=True)
    last_activity_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if self.company_id is None and self.document_id and getattr(self.document, 'company_id', None):
            self.company = self.document.company
        super().save(*args, **kwargs)

    @classmethod
    def active_statuses(cls):
        return [
            cls.Status.CREATED,
            cls.Status.ACTIVE,
            cls.Status.SAVING,
        ]

    @property
    def is_active(self):
        return self.status in self.active_statuses()


class DocumentManualEditSessionEvent(models.Model):
    session = models.ForeignKey(
        DocumentManualEditSession,
        on_delete=models.CASCADE,
        related_name='events',
    )
    level = models.CharField(max_length=16, default='info')
    step = models.CharField(max_length=64, blank=True)
    session_status = models.CharField(max_length=16, blank=True)
    message = models.TextField()
    payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['id']
