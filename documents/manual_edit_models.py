import uuid

from django.conf import settings
from django.db import models

from accounts.storage_paths import company_media_path

# def _manual_edit_working_copy_upload_to xác định đường dẫn lưu bản sao làm việc (.docx) khi sửa văn bản bằng trình soạn web (Collabora), theo công ty + document.
# vd: -> 'companies/<slug>/manual_edit_working_copies/document_5/<wopi_id>.docx'.
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


# class DocumentManualEditSession là một phiên chỉnh sửa VĂN BẢN thủ công qua Collabora/WOPI: bản sao làm việc (working_copy), token truy cập, wopi_file_id, trạng thái vòng đời, lock WOPI, origin trình duyệt để postMessage, hạn dùng.
# vd: bấm 'Sửa bằng trình soạn web' văn bản #5 -> tạo 1 session active mở editor Collabora.
class DocumentManualEditSession(models.Model):
    # class Status liệt kê trạng thái vòng đời phiên sửa (created -> active -> saving -> finished/cancelled/expired/failed).
    # vd: đang mở editor -> ACTIVE; bấm 'Lưu & hoàn tất' xong -> FINISHED.
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
    # Origin that cua trinh duyet (noi nhung iframe), bat tu request tao phien.
    # Collabora dung lam targetOrigin khi postMessage ve frame cha -> phai dung origin
    # nay thi "Luu & hoan tat" moi nhan duoc phan hoi handshake.
    post_message_origin = models.CharField(max_length=255, blank=True, default='')
    expires_at = models.DateTimeField(db_index=True)
    last_activity_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # class Meta: sắp xếp phiên mới nhất lên đầu.
    # vd: liệt kê phiên sửa gần nhất trước.
    class Meta:
        ordering = ['-created_at']

    # def save tự gán company theo document nếu chưa có.
    # vd: tạo phiên cho văn bản công ty A -> session.company=A.
    def save(self, *args, **kwargs):
        if self.company_id is None and self.document_id and getattr(self.document, 'company_id', None):
            self.company = self.document.company
        super().save(*args, **kwargs)

    # def active_statuses (classmethod) trả danh sách trạng thái được coi là 'đang hoạt động' (created/active/saving).
    # vd: dùng để lọc các phiên còn đang mở.
    @classmethod
    def active_statuses(cls):
        return [
            cls.Status.CREATED,
            cls.Status.ACTIVE,
            cls.Status.SAVING,
        ]

    # def is_active (property) cho biết phiên còn đang hoạt động không.
    # vd: status='finished' -> False.
    @property
    def is_active(self):
        return self.status in self.active_statuses()


# class DocumentManualEditSessionEvent ghi nhật ký sự kiện trong 1 phiên sửa văn bản (level/bước/trạng thái/message/payload) để debug luồng Collabora/WOPI.
# vd: lỗi handshake -> 1 event level='error' kèm chi tiết.
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

    # class Meta: sắp xếp event theo id tăng dần (đúng dòng thời gian).
    # vd: xem chuỗi sự kiện của 1 phiên theo thứ tự.
    class Meta:
        ordering = ['id']
