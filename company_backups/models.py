from django.conf import settings
from django.contrib.auth.models import User
from django.db import models


KIND_MANUAL = 'manual'
KIND_AUTO = 'auto'
KIND_CHOICES = [
    (KIND_MANUAL, 'Thu cong'),
    (KIND_AUTO, 'Tu dong'),
]

STATUS_CREATING = 'creating'
STATUS_READY = 'ready'
STATUS_FAILED = 'failed'
STATUS_RESTORING = 'restoring'
STATUS_RESTORED = 'restored'
STATUS_DELETED = 'deleted'
STATUS_CHOICES = [
    (STATUS_CREATING, 'Dang tao'),
    (STATUS_READY, 'San sang'),
    (STATUS_FAILED, 'That bai'),
    (STATUS_RESTORING, 'Dang khoi phuc'),
    (STATUS_RESTORED, 'Da khoi phuc'),
    (STATUS_DELETED, 'Da xoa'),
]

# === BEGIN R5: signature status enum ===
SIGNATURE_STATUS_UNSIGNED = 'unsigned'
SIGNATURE_STATUS_SIGNED = 'signed'
SIGNATURE_STATUS_INVALID = 'invalid'
SIGNATURE_STATUS_CHOICES = [
    (SIGNATURE_STATUS_UNSIGNED, 'Chua ky'),
    (SIGNATURE_STATUS_SIGNED, 'Da ky'),
    (SIGNATURE_STATUS_INVALID, 'Chu ky khong hop le'),
]
# === END R5 ===


# class CompanyBackup là bản ghi một gói sao lưu của 1 công ty: loại (manual/auto), các thành phần được sao (components), đường dẫn file zip + kích thước, vòng đời trạng thái (creating → ready/failed → restoring → restored/deleted), manifest, tiến độ, và thông tin mã hóa + chữ ký (R5).
# vd: bấm 'Sao lưu ngay' -> tạo CompanyBackup(kind='manual', status='creating') rồi cập nhật dần tới 'ready'.
class CompanyBackup(models.Model):
    company = models.ForeignKey(
        'accounts.Company', on_delete=models.CASCADE, related_name='backups',
    )
    name = models.CharField(max_length=255)
    kind = models.CharField(max_length=10, choices=KIND_CHOICES, db_index=True)
    components = models.JSONField(default=list, blank=True)
    file_path = models.CharField(max_length=500, blank=True)
    size_bytes = models.BigIntegerField(default=0)
    status = models.CharField(
        max_length=16, choices=STATUS_CHOICES, default=STATUS_CREATING, db_index=True,
    )
    error_message = models.TextField(blank=True)
    manifest = models.JSONField(default=dict, blank=True)
    progress_percent = models.PositiveSmallIntegerField(default=0)
    progress_stage = models.CharField(max_length=64, blank=True)
    progress_detail = models.CharField(max_length=255, blank=True)
    created_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL,
        related_name='company_backups_created',
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    downloaded_at = models.DateTimeField(null=True, blank=True)
    restored_at = models.DateTimeField(null=True, blank=True)
    restored_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL,
        related_name='company_backups_restored',
    )
    # === BEGIN R5: encryption + signature fields ===
    encryption_meta = models.JSONField(null=True, blank=True)
    signature_path = models.CharField(max_length=500, blank=True, default='')
    signature_status = models.CharField(
        max_length=16, choices=SIGNATURE_STATUS_CHOICES,
        default=SIGNATURE_STATUS_UNSIGNED, db_index=True,
    )
    # === END R5 ===

    # class Meta: sắp xếp bản sao lưu mới nhất lên đầu + index theo (company, thời gian) và (company, kind, thời gian) để liệt kê nhanh theo công ty.
    # vd: trang sao lưu của công ty A -> hiện bản mới nhất trước.
    class Meta:
        verbose_name = 'Ban sao luu doanh nghiep'
        verbose_name_plural = 'Ban sao luu doanh nghiep'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['company', '-created_at']),
            models.Index(fields=['company', 'kind', '-created_at']),
        ]

    # def is_encrypted (property) cho biết gói sao lưu có được mã hóa hay không (dựa vào có encryption_meta).
    # vd: gói tạo khi công ty đã bật mật khẩu sao lưu -> True.
    @property
    def is_encrypted(self) -> bool:
        return bool(self.encryption_meta)

    # def __str__ hiển thị gói sao lưu dạng 'tên (loại/trạng thái)'.
    # vd: -> 'Backup 2026-06 (manual/ready)'.
    def __str__(self):
        return f'{self.name} ({self.kind}/{self.status})'


# class CompanyBackupSettings là cấu hình sao lưu tự động của mỗi công ty (one-to-one): bật/tắt auto, chu kỳ (ngày), mật khẩu mã hóa (lưu dạng hash), số bản giữ lại (retention), mốc auto gần nhất, có gửi email cho admin hay không.
# vd: auto_enabled=True, auto_interval_days=30 -> scheduler tự sao lưu công ty mỗi 30 ngày.
class CompanyBackupSettings(models.Model):
    company = models.OneToOneField(
        'accounts.Company', on_delete=models.CASCADE, related_name='backup_settings',
    )
    auto_enabled = models.BooleanField(default=True)
    auto_interval_days = models.PositiveIntegerField(default=30)
    backup_password_hash = models.CharField(max_length=255, blank=True)
    retention_count = models.PositiveIntegerField(default=12)
    last_auto_run_at = models.DateTimeField(null=True, blank=True)
    notify_admin_email = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # class Meta: đặt tên hiển thị tiếng Việt cho cấu hình sao lưu trong trang admin.
    # vd: admin thấy mục 'Cau hinh sao luu doanh nghiep'.
    class Meta:
        verbose_name = 'Cau hinh sao luu doanh nghiep'
        verbose_name_plural = 'Cau hinh sao luu doanh nghiep'

    # def __str__ hiển thị cấu hình dạng 'Backup settings for <công ty>'.
    # vd: -> 'Backup settings for Công ty A'.
    def __str__(self):
        return f'Backup settings for {self.company}'

    # def has_password (property) cho biết công ty đã đặt mật khẩu sao lưu (để mã hóa gói) hay chưa.
    # vd: đã đặt mật khẩu -> True; chưa -> False.
    @property
    def has_password(self) -> bool:
        return bool(self.backup_password_hash)
