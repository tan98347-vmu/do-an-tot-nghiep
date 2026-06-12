"""
## Quan hệ chính xác

  services.py
      │ ra lệnh ký
      ▼
  pki.sign_pdf_incremental()
      │ private key + SHA-256
      ▼
  PDF có chữ ký

  services.py
      │ yêu cầu kiểm tra
      ▼
  pki.validate_pdf_signatures()
      │ public key + hash tính lại
      ▼
  safe / untrusted / invalid / tampered

  services.py
      │ xử lý kết quả
      ▼
  Cập nhật task, packet và database

  Vì vậy, kết luận chính xác là:

  > services.py quản lý luồng nghiệp vụ; pki.py là bộ máy mật mã thực hiện cả ký bằng private key lẫn xác minh bằng public key. 

  
  SHA-256 = máy tạo dấu vân tay của PDF
  RSA private key = công cụ tạo chữ ký
  X.509 certificate = giấy chứng minh người ký
  PKCS#7 = phong bì đóng gói tất cả thông tin trên
  PDF = tài liệu chứa phong bì đó

  ## PKCS#7 chứa gì?

  Một chữ ký PKCS#7 thường chứa:

  SignedData
  ├── Digest algorithm: SHA-256
  ├── Certificate của người ký
  │   ├── Tên người ký
  │   ├── Public key
  │   ├── Serial number
  │   ├── Issuer/CA
  │   └── Thời hạn certificate
  ├── Signed attributes
  │   ├── Hash của nội dung PDF
  │   ├── Loại nội dung
  │   └── Thời gian người ký khai báo
  └── Signature value
      └── Kết quả ký bằng RSA private key
"""

import uuid

from django.conf import settings
from django.db import models, transaction
from django.db.utils import DatabaseError, OperationalError, ProgrammingError
from accounts.storage_paths import company_media_path

DELEGATION_APPROVE_PROPOSAL = 'approve_signing_proposal'
DELEGATION_VIEW_SIGNED_PDF = 'view_signed_pdf'
DELEGATION_PERMISSION_CHOICES = [
    (DELEGATION_APPROVE_PROPOSAL, 'Duyet de xuat danh sach nguoi ky'),
    (DELEGATION_VIEW_SIGNED_PDF, 'Xem PDF da ky'),
]

PROPOSAL_PENDING_HR_REVIEW = 'pending_hr_review'
PROPOSAL_APPROVED = 'approved'
PROPOSAL_REJECTED = 'rejected'
PROPOSAL_INVALIDATED = 'invalidated'
PROPOSAL_STATUS_CHOICES = [
    (PROPOSAL_PENDING_HR_REVIEW, 'Cho Nhan su duyet'),
    (PROPOSAL_APPROVED, 'Da duyet'),
    (PROPOSAL_REJECTED, 'Bi tu choi'),
    (PROPOSAL_INVALIDATED, 'Khong con hieu luc'),
]

PACKET_ACTIVE = 'active'
PACKET_REJECTED = 'rejected'
PACKET_COMPLETED = 'completed'
PACKET_INVALIDATED = 'invalidated'
PACKET_CANCELLED = 'cancelled'
PACKET_STATUS_CHOICES = [
    (PACKET_ACTIVE, 'Dang cho ky'),
    (PACKET_REJECTED, 'Bi tu choi ky'),
    (PACKET_COMPLETED, 'Da hoan tat'),
    (PACKET_INVALIDATED, 'Khong con hieu luc'),
    (PACKET_CANCELLED, 'Da huy'),
]

TASK_BLOCKED = 'blocked'
TASK_AVAILABLE = 'available'
TASK_SIGNED = 'signed'
TASK_REJECTED = 'rejected'
TASK_CANCELLED = 'cancelled'
TASK_STATUS_CHOICES = [
    (TASK_BLOCKED, 'Chua mo buoc ky'),
    (TASK_AVAILABLE, 'Can ky'),
    (TASK_SIGNED, 'Da ky'),
    (TASK_REJECTED, 'Tu choi ky'),
    (TASK_CANCELLED, 'Khong can xu ly nua'),
]

SIGNATURE_MODE_INTERNAL_APPROVAL = 'internal_approval'
SIGNATURE_MODE_PDF_PKCS7 = 'pdf_pkcs7'
SIGNATURE_MODE_CHOICES = [
    (SIGNATURE_MODE_INTERNAL_APPROVAL, 'Internal approval confirmation'),
    (SIGNATURE_MODE_PDF_PKCS7, 'Embedded PDF CMS/PKCS#7'),
]

CREDENTIAL_PROVIDER_INTERNAL_PKI = 'internal_pki'
CREDENTIAL_PROVIDER_REMOTE_HSM = 'remote_hsm'

CREDENTIAL_STATUS_ACTIVE = 'active'
CREDENTIAL_STATUS_INACTIVE = 'inactive'
CREDENTIAL_STATUS_REVOKED = 'revoked'
CREDENTIAL_STATUS_EXPIRED = 'expired'
CREDENTIAL_STATUS_CHOICES = [
    (CREDENTIAL_STATUS_ACTIVE, 'Dang hoat dong'),
    (CREDENTIAL_STATUS_INACTIVE, 'Tam ngung'),
    (CREDENTIAL_STATUS_REVOKED, 'Da thu hoi'),
    (CREDENTIAL_STATUS_EXPIRED, 'Het han'),
]

VERIFY_STATUS_UNKNOWN = 'unknown'
VERIFY_STATUS_SAFE = 'safe'
VERIFY_STATUS_INVALID = 'invalid'
VERIFY_STATUS_UNTRUSTED = 'untrusted'
VERIFY_STATUS_TAMPERED = 'tampered'
VERIFY_STATUS_INTERNAL_APPROVAL = 'internal_approval'
VERIFY_STATUS_CHOICES = [
    (VERIFY_STATUS_UNKNOWN, 'Chua xac minh'),
    (VERIFY_STATUS_SAFE, 'Hop le'),
    (VERIFY_STATUS_INVALID, 'Khong hop le'),
    (VERIFY_STATUS_UNTRUSTED, 'Khong trust duoc CA'),
    (VERIFY_STATUS_TAMPERED, 'File da bi thay doi'),
    (VERIFY_STATUS_INTERNAL_APPROVAL, 'Internal approval'),
]

def normalize_signature_mode(value):
    return value


def is_internal_approval_mode(value):
    return normalize_signature_mode(value) == SIGNATURE_MODE_INTERNAL_APPROVAL


def normalize_verification_status(value):
    return value


def is_internal_approval_status(value):
    return normalize_verification_status(value) == VERIFY_STATUS_INTERNAL_APPROVAL

def _signing_snapshot_upload(instance, filename):
    """
    Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
    Vai tro backend: Ham `_signing_snapshot_upload` la helper gan voi model hoac storage trong file `signing/models.py`, chu yeu de nhan tep tu frontend va luu xuong backend.
    Vai tro cua no trong frontend: Frontend khong goi truc tiep helper nay; no chi thay hau qua cua buoc nhan tep tu frontend va luu xuong backend qua ten file, duong dan luu hoac trang thai model duoc render ra giao dien.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/signing.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`. Dung cung cap voi cac ham `_signing_working_upload`, `_signed_pdf_upload` trong module nay.
    Tac dung: Chuan hoa buoc nhan tep tu frontend va luu xuong backend ngay sat model de phan con lai cua code khong phai lap lai quy tac luu tru.
    """
    return company_media_path(
        company=getattr(instance, 'company', None) or getattr(getattr(instance, 'document', None), 'company', None),
        section='signing/snapshots',
        parts=[f'proposal_{instance.proposal_id or "unknown"}'],
        filename=filename,
    )

def _signing_working_upload(instance, filename):
    """
    Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
    Vai tro backend: Ham `_signing_working_upload` la helper gan voi model hoac storage trong file `signing/models.py`, chu yeu de nhan tep tu frontend va luu xuong backend.
    Vai tro cua no trong frontend: Frontend khong goi truc tiep helper nay; no chi thay hau qua cua buoc nhan tep tu frontend va luu xuong backend qua ten file, duong dan luu hoac trang thai model duoc render ra giao dien.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/signing.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`. Dung cung cap voi cac ham `_signing_snapshot_upload`, `_signed_pdf_upload` trong module nay.
    Tac dung: Chuan hoa buoc nhan tep tu frontend va luu xuong backend ngay sat model de phan con lai cua code khong phai lap lai quy tac luu tru.
    """
    return company_media_path(
        company=getattr(instance, 'company', None) or getattr(getattr(instance, 'document', None), 'company', None),
        section='signing/working',
        parts=[f'proposal_{instance.proposal_id or "unknown"}'],
        filename=filename,
    )

def _signed_pdf_upload(instance, filename):
    """
    Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
    Vai tro backend: Ham `_signed_pdf_upload` la helper gan voi model hoac storage trong file `signing/models.py`, chu yeu de nhan tep tu frontend va luu xuong backend.
    Vai tro cua no trong frontend: Frontend khong goi truc tiep helper nay; no chi thay hau qua cua buoc nhan tep tu frontend va luu xuong backend qua ten file, duong dan luu hoac trang thai model duoc render ra giao dien.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/signing.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`. Dung cung cap voi cac ham `_signing_snapshot_upload`, `_signing_working_upload` trong module nay.
    Tac dung: Chuan hoa buoc nhan tep tu frontend va luu xuong backend ngay sat model de phan con lai cua code khong phai lap lai quy tac luu tru.
    """
    return company_media_path(
        company=getattr(instance, 'company', None) or getattr(getattr(instance, 'source_document', None), 'company', None),
        section='signed_pdfs',
        parts=[f'document_{instance.source_document_id or "unknown"}'],
        filename=filename,
    )

class SigningSystemConfig(models.Model):
    """
    Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
    Vai tro backend: Lop `SigningSystemConfig` khai bao thuc the du lieu hoac bang nghiep vu cot loi cua file `signing/models.py`.
    Vai tro cua no trong frontend: Frontend khong khoi tao lop nay truc tiep; serializer, service va API doc trang thai cua model de dung danh sach, badge, form va man chi tiet.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/signing.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`. Nam trong pham vi module hien tai.
    Tac dung: Luu schema, quan he va hanh vi mac dinh de cac luong doc/ghi du lieu ve `SigningSystemConfig` khong bi lech trang thai.
    """
    company = models.OneToOneField(
        'accounts.Company',
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name='signing_config',
    )
    hr_department = models.ForeignKey(
        'accounts.Department',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='signing_hr_configs',
        verbose_name='Phong Nhan su',
    )
    accounting_department = models.ForeignKey(
        'accounts.Department',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='signing_accounting_configs',
        verbose_name='Phong Ke toan',
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='updated_signing_configs',
    )
    updated_at = models.DateTimeField(auto_now=True)

    

    class Meta:
        """
        Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
        Vai tro backend: Lop `Meta` dong goi mot cum hanh vi hoac cau hinh backend cua file `signing/models.py`.
        Vai tro cua no trong frontend: Frontend khong goi truc tiep lop nay; cac endpoint hoac service cua cung tinh nang se su dung no de tao du lieu trinh bay hoac kiem soat luong xu ly.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/signing.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`. Nam trong pham vi cua `SigningSystemConfig` va cung dung chung ngu canh cua file nay.
        Tac dung: To chuc logic lien quan toi `Meta` thanh mot don vi ro rang de nhung ham khac goi lai de hon.
        """
        verbose_name = 'Cau hinh ky so'
        verbose_name_plural = 'Cau hinh ky so'

    

    def __str__(self):
        """
        Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
        Vai tro backend: Ham `__str__` la helper gan voi model hoac storage trong file `signing/models.py` trong lop `SigningSystemConfig`, chu yeu de tra nhan hien thi gon cua doi tuong.
        Vai tro cua no trong frontend: Frontend khong goi truc tiep helper nay; no chi thay hau qua cua buoc tra nhan hien thi gon cua doi tuong qua ten file, duong dan luu hoac trang thai model duoc render ra giao dien.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/signing.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`. Phoi hop truc tiep voi cac method nhu `get_config` trong cung lop.
        Tac dung: Chuan hoa buoc tra nhan hien thi gon cua doi tuong ngay sat model de phan con lai cua code khong phai lap lai quy tac luu tru.
        """
        if self.company_id:
            return f'SigningSystemConfig[{self.company_id}]'
        return 'SigningSystemConfig'

    

    @classmethod
    def get_config(cls, company=None):
        """
        Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
        Vai tro backend: Ham `get_config` la method gan voi model trong file `signing/models.py` trong lop `SigningSystemConfig`, phu trach phuc vu hanh vi phu tro quanh model hien tai.
        Vai tro cua no trong frontend: Frontend khong goi method model truc tiep, nhung serializer va API se dua vao ket qua phuc vu hanh vi phu tro quanh model hien tai nay de dung trang thai hoac nhan tren giao dien.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/signing.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`. Phoi hop truc tiep voi cac method nhu `__str__` trong cung lop.
        Tac dung: Dua hanh vi phuc vu hanh vi phu tro quanh model hien tai ve dung noi du lieu duoc quan ly thay vi rai sang nhieu view hoac service khac.
        """
        try:
            if company is not None:
                obj, _ = cls.objects.get_or_create(company=company)
                return obj
            obj, _ = cls.objects.get_or_create(pk=1)
            return obj
        except (ProgrammingError, OperationalError, DatabaseError):
            if company is not None:
                return cls(company=company)
            return cls(pk=1)

class DepartmentDelegation(models.Model):
    """
    Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
    Vai tro backend: Lop `DepartmentDelegation` khai bao thuc the du lieu hoac bang nghiep vu cot loi cua file `signing/models.py`.
    Vai tro cua no trong frontend: Frontend khong khoi tao lop nay truc tiep; serializer, service va API doc trang thai cua model de dung danh sach, badge, form va man chi tiet.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/signing.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`. Nam trong pham vi module hien tai.
    Tac dung: Luu schema, quan he va hanh vi mac dinh de cac luong doc/ghi du lieu ve `DepartmentDelegation` khong bi lech trang thai.
    """
    department = models.ForeignKey(
        'accounts.Department',
        on_delete=models.CASCADE,
        related_name='delegations',
    )
    delegate_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='department_delegations',
    )
    permission_type = models.CharField(
        max_length=64,
        choices=DELEGATION_PERMISSION_CHOICES,
    )
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='created_department_delegations',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    

    class Meta:
        """
        Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
        Vai tro backend: Lop `Meta` dong goi mot cum hanh vi hoac cau hinh backend cua file `signing/models.py`.
        Vai tro cua no trong frontend: Frontend khong goi truc tiep lop nay; cac endpoint hoac service cua cung tinh nang se su dung no de tao du lieu trinh bay hoac kiem soat luong xu ly.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/signing.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`. Nam trong pham vi cua `DepartmentDelegation` va cung dung chung ngu canh cua file nay.
        Tac dung: To chuc logic lien quan toi `Meta` thanh mot don vi ro rang de nhung ham khac goi lai de hon.
        """
        verbose_name = 'Uy quyen phong ban cho ky so'
        verbose_name_plural = 'Uy quyen phong ban cho ky so'
        unique_together = ('department', 'delegate_user', 'permission_type')

    

    def __str__(self):
        """
        Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
        Vai tro backend: Ham `__str__` la helper gan voi model hoac storage trong file `signing/models.py` trong lop `DepartmentDelegation`, chu yeu de tra nhan hien thi gon cua doi tuong.
        Vai tro cua no trong frontend: Frontend khong goi truc tiep helper nay; no chi thay hau qua cua buoc tra nhan hien thi gon cua doi tuong qua ten file, duong dan luu hoac trang thai model duoc render ra giao dien.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/signing.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`. Nam trong lop `DepartmentDelegation` va phuc vu luong xu ly cua lop nay.
        Tac dung: Chuan hoa buoc tra nhan hien thi gon cua doi tuong ngay sat model de phan con lai cua code khong phai lap lai quy tac luu tru.
        """
        return f'{self.department} -> {self.delegate_user} [{self.permission_type}]'

class UserSigningCredential(models.Model):
    """
    Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
    Vai tro backend: Lop `UserSigningCredential` khai bao thuc the du lieu hoac bang nghiep vu cot loi cua file `signing/models.py`.
    Vai tro cua no trong frontend: Frontend khong khoi tao lop nay truc tiep; serializer, service va API doc trang thai cua model de dung danh sach, badge, form va man chi tiet.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/signing.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`. Nam trong pham vi module hien tai.
    Tac dung: Luu schema, quan he va hanh vi mac dinh de cac luong doc/ghi du lieu ve `UserSigningCredential` khong bi lech trang thai.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='signing_credentials',
    )
    provider = models.CharField(max_length=64)
    key_alias = models.CharField(max_length=255, blank=True)
    key_id = models.CharField(max_length=255, blank=True)
    certificate_pem = models.TextField()
    subject_dn = models.CharField(max_length=1000)
    serial_number = models.CharField(max_length=128)
    issuer_dn = models.CharField(max_length=1000)
    valid_from = models.DateTimeField()
    valid_to = models.DateTimeField()
    status = models.CharField(
        max_length=32,
        choices=CREDENTIAL_STATUS_CHOICES,
        default=CREDENTIAL_STATUS_INACTIVE,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    

    class Meta:
        """
        Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
        Vai tro backend: Lop `Meta` dong goi mot cum hanh vi hoac cau hinh backend cua file `signing/models.py`.
        Vai tro cua no trong frontend: Frontend khong goi truc tiep lop nay; cac endpoint hoac service cua cung tinh nang se su dung no de tao du lieu trinh bay hoac kiem soat luong xu ly.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/signing.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`. Nam trong pham vi cua `UserSigningCredential` va cung dung chung ngu canh cua file nay.
        Tac dung: To chuc logic lien quan toi `Meta` thanh mot don vi ro rang de nhung ham khac goi lai de hon.
        """
        verbose_name = 'Rang buoc chung thu ky cua user'
        verbose_name_plural = 'Rang buoc chung thu ky cua user'
        ordering = ['user_id', '-updated_at']
        constraints = [
            models.UniqueConstraint(
                fields=['user'],
                condition=models.Q(status=CREDENTIAL_STATUS_ACTIVE),
                name='uniq_active_signing_credential_per_user',
            ),
        ]

    

    def __str__(self):
        """
        Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
        Vai tro backend: Ham `__str__` la helper gan voi model hoac storage trong file `signing/models.py` trong lop `UserSigningCredential`, chu yeu de tra nhan hien thi gon cua doi tuong.
        Vai tro cua no trong frontend: Frontend khong goi truc tiep helper nay; no chi thay hau qua cua buoc tra nhan hien thi gon cua doi tuong qua ten file, duong dan luu hoac trang thai model duoc render ra giao dien.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/signing.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`. Phoi hop truc tiep voi cac method nhu `save` trong cung lop.
        Tac dung: Chuan hoa buoc tra nhan hien thi gon cua doi tuong ngay sat model de phan con lai cua code khong phai lap lai quy tac luu tru.
        """
        return f'{self.user} [{self.provider}] {self.serial_number}'

    

    def save(self, *args, **kwargs):
        """
        Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
        Vai tro backend: Ham `save` la method gan voi model trong file `signing/models.py` trong lop `UserSigningCredential`, phu trach luu va chuan hoa du lieu truoc hoac sau khi ghi vao database.
        Vai tro cua no trong frontend: Frontend khong goi method model truc tiep, nhung serializer va API se dua vao ket qua luu va chuan hoa du lieu truoc hoac sau khi ghi vao database nay de dung trang thai hoac nhan tren giao dien.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/signing.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`. Phoi hop truc tiep voi cac method nhu `__str__` trong cung lop.
        Tac dung: Dua hanh vi luu va chuan hoa du lieu truoc hoac sau khi ghi vao database ve dung noi du lieu duoc quan ly thay vi rai sang nhieu view hoac service khac.
        """
        if self.user_id and self.status == CREDENTIAL_STATUS_ACTIVE:
            with transaction.atomic():
                (
                    UserSigningCredential.objects.filter(
                        user_id=self.user_id,
                        status=CREDENTIAL_STATUS_ACTIVE,
                    )
                    .exclude(pk=self.pk)
                    .update(status=CREDENTIAL_STATUS_INACTIVE)
                )
                return super().save(*args, **kwargs)
        return super().save(*args, **kwargs)

class UserSigningKeySecret(models.Model):
    """
    Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
    Vai tro backend: Lop `UserSigningKeySecret` khai bao thuc the du lieu hoac bang nghiep vu cot loi cua file `signing/models.py`.
    Vai tro cua no trong frontend: Frontend khong khoi tao lop nay truc tiep; serializer, service va API doc trang thai cua model de dung danh sach, badge, form va man chi tiet.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/signing.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`. Nam trong pham vi module hien tai.
    Tac dung: Luu schema, quan he va hanh vi mac dinh de cac luong doc/ghi du lieu ve `UserSigningKeySecret` khong bi lech trang thai.
    """
    credential = models.OneToOneField(
        UserSigningCredential,
        on_delete=models.CASCADE,
        related_name='key_secret',
    )
    encrypted_private_key_pem = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    

    class Meta:
        """
        Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
        Vai tro backend: Lop `Meta` dong goi mot cum hanh vi hoac cau hinh backend cua file `signing/models.py`.
        Vai tro cua no trong frontend: Frontend khong goi truc tiep lop nay; cac endpoint hoac service cua cung tinh nang se su dung no de tao du lieu trinh bay hoac kiem soat luong xu ly.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/signing.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`. Nam trong pham vi cua `UserSigningKeySecret` va cung dung chung ngu canh cua file nay.
        Tac dung: To chuc logic lien quan toi `Meta` thanh mot don vi ro rang de nhung ham khac goi lai de hon.
        """
        verbose_name = 'Bi mat khoa rieng cua user'
        verbose_name_plural = 'Bi mat khoa rieng cua user'

    

    def __str__(self):
        """
        Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
        Vai tro backend: Ham `__str__` la helper gan voi model hoac storage trong file `signing/models.py` trong lop `UserSigningKeySecret`, chu yeu de tra nhan hien thi gon cua doi tuong.
        Vai tro cua no trong frontend: Frontend khong goi truc tiep helper nay; no chi thay hau qua cua buoc tra nhan hien thi gon cua doi tuong qua ten file, duong dan luu hoac trang thai model duoc render ra giao dien.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/signing.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`. Nam trong lop `UserSigningKeySecret` va phuc vu luong xu ly cua lop nay.
        Tac dung: Chuan hoa buoc tra nhan hien thi gon cua doi tuong ngay sat model de phan con lai cua code khong phai lap lai quy tac luu tru.
        """
        return f'key-secret:{self.credential_id}'

class InternalPkiConfig(models.Model):
    """
    Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
    Vai tro backend: Lop `InternalPkiConfig` khai bao thuc the du lieu hoac bang nghiep vu cot loi cua file `signing/models.py`.
    Vai tro cua no trong frontend: Frontend khong khoi tao lop nay truc tiep; serializer, service va API doc trang thai cua model de dung danh sach, badge, form va man chi tiet.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/signing.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`. Nam trong pham vi module hien tai.
    Tac dung: Luu schema, quan he va hanh vi mac dinh de cac luong doc/ghi du lieu ve `InternalPkiConfig` khong bi lech trang thai.
    """
    ca_certificate_pem = models.TextField(blank=True)
    encrypted_private_key_pem = models.TextField(blank=True)
    valid_from = models.DateTimeField(null=True, blank=True)
    valid_to = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    

    class Meta:
        """
        Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
        Vai tro backend: Lop `Meta` dong goi mot cum hanh vi hoac cau hinh backend cua file `signing/models.py`.
        Vai tro cua no trong frontend: Frontend khong goi truc tiep lop nay; cac endpoint hoac service cua cung tinh nang se su dung no de tao du lieu trinh bay hoac kiem soat luong xu ly.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/signing.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`. Nam trong pham vi cua `InternalPkiConfig` va cung dung chung ngu canh cua file nay.
        Tac dung: To chuc logic lien quan toi `Meta` thanh mot don vi ro rang de nhung ham khac goi lai de hon.
        """
        verbose_name = 'Cau hinh CA PKI noi bo'
        verbose_name_plural = 'Cau hinh CA PKI noi bo'

    

    def __str__(self):
        """
        Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
        Vai tro backend: Ham `__str__` la helper gan voi model hoac storage trong file `signing/models.py` trong lop `InternalPkiConfig`, chu yeu de tra nhan hien thi gon cua doi tuong.
        Vai tro cua no trong frontend: Frontend khong goi truc tiep helper nay; no chi thay hau qua cua buoc tra nhan hien thi gon cua doi tuong qua ten file, duong dan luu hoac trang thai model duoc render ra giao dien.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/signing.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`. Phoi hop truc tiep voi cac method nhu `get_config` trong cung lop.
        Tac dung: Chuan hoa buoc tra nhan hien thi gon cua doi tuong ngay sat model de phan con lai cua code khong phai lap lai quy tac luu tru.
        """
        return 'InternalPkiConfig'

    

    @classmethod
    def get_config(cls):
        """
        Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
        Vai tro backend: Ham `get_config` la method gan voi model trong file `signing/models.py` trong lop `InternalPkiConfig`, phu trach phuc vu hanh vi phu tro quanh model hien tai.
        Vai tro cua no trong frontend: Frontend khong goi method model truc tiep, nhung serializer va API se dua vao ket qua phuc vu hanh vi phu tro quanh model hien tai nay de dung trang thai hoac nhan tren giao dien.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/signing.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`. Phoi hop truc tiep voi cac method nhu `__str__` trong cung lop.
        Tac dung: Dua hanh vi phuc vu hanh vi phu tro quanh model hien tai ve dung noi du lieu duoc quan ly thay vi rai sang nhieu view hoac service khac.
        """
        try:
            obj, _ = cls.objects.get_or_create(pk=1)
            return obj
        except (ProgrammingError, OperationalError, DatabaseError):
            return cls(pk=1)

class SigningProposal(models.Model):
    """
    Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
    Vai tro backend: Lop `SigningProposal` khai bao thuc the du lieu hoac bang nghiep vu cot loi cua file `signing/models.py`.
    Vai tro cua no trong frontend: Frontend khong khoi tao lop nay truc tiep; serializer, service va API doc trang thai cua model de dung danh sach, badge, form va man chi tiet.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/signing.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`. Nam trong pham vi module hien tai.
    Tac dung: Luu schema, quan he va hanh vi mac dinh de cac luong doc/ghi du lieu ve `SigningProposal` khong bi lech trang thai.
    """
    document = models.ForeignKey(
        'documents.Document',
        on_delete=models.CASCADE,
        related_name='signing_proposals',
    )
    company = models.ForeignKey(
        'accounts.Company',
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name='signing_proposals',
    )
    source_version = models.ForeignKey(
        'documents.DocumentVersion',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='signing_proposals',
    )
    source_version_number = models.IntegerField(default=1)
    source_docx_sha256 = models.CharField(max_length=64, blank=True)
    proposed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='signing_proposals_created',
    )
    proposal_note = models.TextField(blank=True)
    status = models.CharField(
        max_length=32,
        choices=PROPOSAL_STATUS_CHOICES,
        default=PROPOSAL_PENDING_HR_REVIEW,
    )
    review_note = models.TextField(blank=True)
    hr_reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='signing_proposals_reviewed',
    )
    hr_reviewed_at = models.DateTimeField(null=True, blank=True)
    invalidated_reason = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    

    class Meta:
        """
        Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
        Vai tro backend: Lop `Meta` dong goi mot cum hanh vi hoac cau hinh backend cua file `signing/models.py`.
        Vai tro cua no trong frontend: Frontend khong goi truc tiep lop nay; cac endpoint hoac service cua cung tinh nang se su dung no de tao du lieu trinh bay hoac kiem soat luong xu ly.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/signing.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`. Nam trong pham vi cua `SigningProposal` va cung dung chung ngu canh cua file nay.
        Tac dung: To chuc logic lien quan toi `Meta` thanh mot don vi ro rang de nhung ham khac goi lai de hon.
        """
        verbose_name = 'De xuat ky so'
        verbose_name_plural = 'De xuat ky so'
        ordering = ['-created_at']

    

    def __str__(self):
        """
        Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
        Vai tro backend: Ham `__str__` la helper gan voi model hoac storage trong file `signing/models.py` trong lop `SigningProposal`, chu yeu de tra nhan hien thi gon cua doi tuong.
        Vai tro cua no trong frontend: Frontend khong goi truc tiep helper nay; no chi thay hau qua cua buoc tra nhan hien thi gon cua doi tuong qua ten file, duong dan luu hoac trang thai model duoc render ra giao dien.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/signing.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`. Nam trong lop `SigningProposal` va phuc vu luong xu ly cua lop nay.
        Tac dung: Chuan hoa buoc tra nhan hien thi gon cua doi tuong ngay sat model de phan con lai cua code khong phai lap lai quy tac luu tru.
        """
        return f'{self.document.title} [{self.get_status_display()}]'

    def save(self, *args, **kwargs):
        if self.company_id is None:
            if self.document_id and getattr(self.document, 'company_id', None):
                self.company = self.document.company
            elif self.proposed_by_id and getattr(getattr(self.proposed_by, 'company_membership', None), 'company_id', None):
                self.company = self.proposed_by.company_membership.company
        super().save(*args, **kwargs)

class SigningProposalSigner(models.Model):
    """
    Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
    Vai tro backend: Lop `SigningProposalSigner` khai bao thuc the du lieu hoac bang nghiep vu cot loi cua file `signing/models.py`.
    Vai tro cua no trong frontend: Frontend khong khoi tao lop nay truc tiep; serializer, service va API doc trang thai cua model de dung danh sach, badge, form va man chi tiet.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/signing.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`. Nam trong pham vi module hien tai.
    Tac dung: Luu schema, quan he va hanh vi mac dinh de cac luong doc/ghi du lieu ve `SigningProposalSigner` khong bi lech trang thai.
    """
    proposal = models.ForeignKey(
        SigningProposal,
        on_delete=models.CASCADE,
        related_name='signers',
    )
    signer_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='signing_slots',
    )
    display_role = models.CharField(max_length=200)
    group_context = models.CharField(max_length=200, blank=True)
    step_no = models.PositiveIntegerField(default=1)
    sort_order = models.PositiveIntegerField(default=0)
    required = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    

    class Meta:
        """
        Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
        Vai tro backend: Lop `Meta` dong goi mot cum hanh vi hoac cau hinh backend cua file `signing/models.py`.
        Vai tro cua no trong frontend: Frontend khong goi truc tiep lop nay; cac endpoint hoac service cua cung tinh nang se su dung no de tao du lieu trinh bay hoac kiem soat luong xu ly.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/signing.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`. Nam trong pham vi cua `SigningProposalSigner` va cung dung chung ngu canh cua file nay.
        Tac dung: To chuc logic lien quan toi `Meta` thanh mot don vi ro rang de nhung ham khac goi lai de hon.
        """
        verbose_name = 'Nguoi ky de xuat'
        verbose_name_plural = 'Nguoi ky de xuat'
        ordering = ['step_no', 'sort_order', 'id']

    

    def __str__(self):
        """
        Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
        Vai tro backend: Ham `__str__` la helper gan voi model hoac storage trong file `signing/models.py` trong lop `SigningProposalSigner`, chu yeu de tra nhan hien thi gon cua doi tuong.
        Vai tro cua no trong frontend: Frontend khong goi truc tiep helper nay; no chi thay hau qua cua buoc tra nhan hien thi gon cua doi tuong qua ten file, duong dan luu hoac trang thai model duoc render ra giao dien.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/signing.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`. Nam trong lop `SigningProposalSigner` va phuc vu luong xu ly cua lop nay.
        Tac dung: Chuan hoa buoc tra nhan hien thi gon cua doi tuong ngay sat model de phan con lai cua code khong phai lap lai quy tac luu tru.
        """
        return f'{self.signer_user} / step {self.step_no} / {self.display_role}'

class SigningPacket(models.Model):
    """
    Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
    Vai tro backend: Lop `SigningPacket` khai bao thuc the du lieu hoac bang nghiep vu cot loi cua file `signing/models.py`.
    Vai tro cua no trong frontend: Frontend khong khoi tao lop nay truc tiep; serializer, service va API doc trang thai cua model de dung danh sach, badge, form va man chi tiet.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/signing.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`. Nam trong pham vi module hien tai.
    Tac dung: Luu schema, quan he va hanh vi mac dinh de cac luong doc/ghi du lieu ve `SigningPacket` khong bi lech trang thai.
    """
    proposal = models.OneToOneField(
        SigningProposal,
        on_delete=models.CASCADE,
        related_name='packet',
    )
    company = models.ForeignKey(
        'accounts.Company',
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name='signing_packets',
    )
    document = models.ForeignKey(
        'documents.Document',
        on_delete=models.CASCADE,
        related_name='signing_packets',
    )
    source_version = models.ForeignKey(
        'documents.DocumentVersion',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='signing_packets',
    )
    source_version_number = models.IntegerField(default=1)
    source_docx_sha256 = models.CharField(max_length=64, blank=True)
    pdf_snapshot = models.FileField(
        upload_to=_signing_snapshot_upload,
        max_length=500,
        verbose_name='PDF snapshot ban dau',
    )
    working_pdf = models.FileField(
        upload_to=_signing_working_upload,
        max_length=500,
        verbose_name='PDF dang duoc ky',
    )
    pdf_hash = models.CharField(max_length=64, blank=True)
    signature_mode = models.CharField(
        max_length=32,
        choices=SIGNATURE_MODE_CHOICES,
        default=SIGNATURE_MODE_INTERNAL_APPROVAL,
    )
    status = models.CharField(
        max_length=32,
        choices=PACKET_STATUS_CHOICES,
        default=PACKET_ACTIVE,
    )
    current_step = models.PositiveIntegerField(default=1)
    rejection_reason = models.TextField(blank=True)
    activated_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    invalidated_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    

    class Meta:
        """
        Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
        Vai tro backend: Lop `Meta` dong goi mot cum hanh vi hoac cau hinh backend cua file `signing/models.py`.
        Vai tro cua no trong frontend: Frontend khong goi truc tiep lop nay; cac endpoint hoac service cua cung tinh nang se su dung no de tao du lieu trinh bay hoac kiem soat luong xu ly.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/signing.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`. Nam trong pham vi cua `SigningPacket` va cung dung chung ngu canh cua file nay.
        Tac dung: To chuc logic lien quan toi `Meta` thanh mot don vi ro rang de nhung ham khac goi lai de hon.
        """
        verbose_name = 'Phien ky PDF'
        verbose_name_plural = 'Phien ky PDF'
        ordering = ['-activated_at']

    

    def __str__(self):
        """
        Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
        Vai tro backend: Ham `__str__` la helper gan voi model hoac storage trong file `signing/models.py` trong lop `SigningPacket`, chu yeu de tra nhan hien thi gon cua doi tuong.
        Vai tro cua no trong frontend: Frontend khong goi truc tiep helper nay; no chi thay hau qua cua buoc tra nhan hien thi gon cua doi tuong qua ten file, duong dan luu hoac trang thai model duoc render ra giao dien.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/signing.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`. Nam trong lop `SigningPacket` va phuc vu luong xu ly cua lop nay.
        Tac dung: Chuan hoa buoc tra nhan hien thi gon cua doi tuong ngay sat model de phan con lai cua code khong phai lap lai quy tac luu tru.
        """
        return f'Packet #{self.pk} - {self.document.title}'

    def save(self, *args, **kwargs):
        if self.company_id is None:
            if self.proposal_id and getattr(self.proposal, 'company_id', None):
                self.company = self.proposal.company
            elif self.document_id and getattr(self.document, 'company_id', None):
                self.company = self.document.company
        super().save(*args, **kwargs)

class SigningTask(models.Model):
    """
    Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
    Vai tro backend: Lop `SigningTask` khai bao thuc the du lieu hoac bang nghiep vu cot loi cua file `signing/models.py`.
    Vai tro cua no trong frontend: Frontend khong khoi tao lop nay truc tiep; serializer, service va API doc trang thai cua model de dung danh sach, badge, form va man chi tiet.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/signing.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`. Nam trong pham vi module hien tai.
    Tac dung: Luu schema, quan he va hanh vi mac dinh de cac luong doc/ghi du lieu ve `SigningTask` khong bi lech trang thai.
    """
    packet = models.ForeignKey(
        SigningPacket,
        on_delete=models.CASCADE,
        related_name='tasks',
    )
    company = models.ForeignKey(
        'accounts.Company',
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name='signing_tasks',
    )
    proposal_signer = models.ForeignKey(
        SigningProposalSigner,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='tasks',
    )
    signer_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='signing_tasks',
    )
    display_role = models.CharField(max_length=200)
    group_context = models.CharField(max_length=200, blank=True)
    step_no = models.PositiveIntegerField(default=1)
    sort_order = models.PositiveIntegerField(default=0)
    required = models.BooleanField(default=True)
    signature_field_name = models.CharField(max_length=255, blank=True)
    status = models.CharField(
        max_length=32,
        choices=TASK_STATUS_CHOICES,
        default=TASK_BLOCKED,
    )
    notified_at = models.DateTimeField(null=True, blank=True)
    opened_at = models.DateTimeField(null=True, blank=True)
    signed_at = models.DateTimeField(null=True, blank=True)
    rejected_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    

    class Meta:
        """
        Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
        Vai tro backend: Lop `Meta` dong goi mot cum hanh vi hoac cau hinh backend cua file `signing/models.py`.
        Vai tro cua no trong frontend: Frontend khong goi truc tiep lop nay; cac endpoint hoac service cua cung tinh nang se su dung no de tao du lieu trinh bay hoac kiem soat luong xu ly.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/signing.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`. Nam trong pham vi cua `SigningTask` va cung dung chung ngu canh cua file nay.
        Tac dung: To chuc logic lien quan toi `Meta` thanh mot don vi ro rang de nhung ham khac goi lai de hon.
        """
        verbose_name = 'Yeu cau ky'
        verbose_name_plural = 'Yeu cau ky'
        ordering = ['status', 'step_no', 'sort_order', 'id']

    

    def __str__(self):
        """
        Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
        Vai tro backend: Ham `__str__` la helper gan voi model hoac storage trong file `signing/models.py` trong lop `SigningTask`, chu yeu de tra nhan hien thi gon cua doi tuong.
        Vai tro cua no trong frontend: Frontend khong goi truc tiep helper nay; no chi thay hau qua cua buoc tra nhan hien thi gon cua doi tuong qua ten file, duong dan luu hoac trang thai model duoc render ra giao dien.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/signing.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`. Nam trong lop `SigningTask` va phuc vu luong xu ly cua lop nay.
        Tac dung: Chuan hoa buoc tra nhan hien thi gon cua doi tuong ngay sat model de phan con lai cua code khong phai lap lai quy tac luu tru.
        """
        return f'Task #{self.pk} - {self.signer_user} - {self.packet}'

    def save(self, *args, **kwargs):
        if self.company_id is None:
            if self.packet_id and getattr(self.packet, 'company_id', None):
                self.company = self.packet.company
            elif self.proposal_signer_id and getattr(getattr(self.proposal_signer, 'proposal', None), 'company_id', None):
                self.company = self.proposal_signer.proposal.company
            elif self.signer_user_id and getattr(getattr(self.signer_user, 'company_membership', None), 'company_id', None):
                self.company = self.signer_user.company_membership.company
        super().save(*args, **kwargs)

class SignedPdfDocument(models.Model):
    """
    Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
    Vai tro backend: Lop `SignedPdfDocument` khai bao thuc the du lieu hoac bang nghiep vu cot loi cua file `signing/models.py`.
    Vai tro cua no trong frontend: Frontend khong khoi tao lop nay truc tiep; serializer, service va API doc trang thai cua model de dung danh sach, badge, form va man chi tiet.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/signing.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`. Nam trong pham vi module hien tai.
    Tac dung: Luu schema, quan he va hanh vi mac dinh de cac luong doc/ghi du lieu ve `SignedPdfDocument` khong bi lech trang thai.
    """
    packet = models.OneToOneField(
        SigningPacket,
        on_delete=models.CASCADE,
        related_name='signed_document',
    )
    title = models.CharField(max_length=255)
    company = models.ForeignKey(
        'accounts.Company',
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name='signed_pdf_records',
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='owned_signed_pdfs',
    )
    source_document = models.ForeignKey(
        'documents.Document',
        on_delete=models.CASCADE,
        related_name='signed_pdf_records',
    )
    source_version_number = models.IntegerField(default=1)
    signed_pdf_file = models.FileField(
        upload_to=_signed_pdf_upload,
        max_length=500,
    )
    file_hash = models.CharField(max_length=64, blank=True)
    signature_mode = models.CharField(
        max_length=32,
        choices=SIGNATURE_MODE_CHOICES,
        default=SIGNATURE_MODE_INTERNAL_APPROVAL,
    )
    verification_status = models.CharField(
        max_length=32,
        choices=VERIFY_STATUS_CHOICES,
        default=VERIFY_STATUS_UNKNOWN,
    )
    verification_checked_at = models.DateTimeField(null=True, blank=True)
    signature_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    

    class Meta:
        """
        Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
        Vai tro backend: Lop `Meta` dong goi mot cum hanh vi hoac cau hinh backend cua file `signing/models.py`.
        Vai tro cua no trong frontend: Frontend khong goi truc tiep lop nay; cac endpoint hoac service cua cung tinh nang se su dung no de tao du lieu trinh bay hoac kiem soat luong xu ly.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/signing.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`. Nam trong pham vi cua `SignedPdfDocument` va cung dung chung ngu canh cua file nay.
        Tac dung: To chuc logic lien quan toi `Meta` thanh mot don vi ro rang de nhung ham khac goi lai de hon.
        """
        verbose_name = 'PDF da ky'
        verbose_name_plural = 'PDF da ky'
        ordering = ['-created_at']

    

    def __str__(self):
        """
        Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
        Vai tro backend: Ham `__str__` la helper gan voi model hoac storage trong file `signing/models.py` trong lop `SignedPdfDocument`, chu yeu de tra nhan hien thi gon cua doi tuong.
        Vai tro cua no trong frontend: Frontend khong goi truc tiep helper nay; no chi thay hau qua cua buoc tra nhan hien thi gon cua doi tuong qua ten file, duong dan luu hoac trang thai model duoc render ra giao dien.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/signing.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`. Nam trong lop `SignedPdfDocument` va phuc vu luong xu ly cua lop nay.
        Tac dung: Chuan hoa buoc tra nhan hien thi gon cua doi tuong ngay sat model de phan con lai cua code khong phai lap lai quy tac luu tru.
        """
        return self.title

    def save(self, *args, **kwargs):
        if self.company_id is None:
            if self.source_document_id and getattr(self.source_document, 'company_id', None):
                self.company = self.source_document.company
            elif self.packet_id and getattr(self.packet, 'company_id', None):
                self.company = self.packet.company
        super().save(*args, **kwargs)


class AssistantQuickSignPlan(models.Model):
    class Status(models.TextChoices):
        READY = 'ready', 'Ready'
        BLOCKED = 'blocked', 'Blocked'
        IN_PROGRESS = 'in_progress', 'In progress'
        COMPLETED = 'completed', 'Completed'
        PARTIAL = 'partial', 'Partial'
        FAILED = 'failed', 'Failed'
        CANCELLED = 'cancelled', 'Cancelled'

    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    company = models.ForeignKey(
        'accounts.Company',
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name='assistant_quick_sign_plans',
    )
    session = models.ForeignKey(
        'ai_engine.ChatSession',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='assistant_quick_sign_plans',
    )
    document = models.ForeignKey(
        'documents.Document',
        on_delete=models.CASCADE,
        related_name='assistant_quick_sign_plans',
    )
    document_version_number = models.PositiveIntegerField(default=1)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='assistant_quick_sign_plans',
    )
    recipient_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='received_assistant_quick_sign_plans',
    )
    recipient_snapshot = models.JSONField(default=dict, blank=True)
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.READY,
    )
    signature_mode = models.CharField(
        max_length=32,
        choices=SIGNATURE_MODE_CHOICES,
        default=SIGNATURE_MODE_INTERNAL_APPROVAL,
    )
    signing_task = models.ForeignKey(
        SigningTask,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='assistant_quick_sign_plans',
    )
    signing_packet = models.ForeignKey(
        SigningPacket,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='assistant_quick_sign_plans',
    )
    signed_pdf = models.ForeignKey(
        SignedPdfDocument,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='assistant_quick_sign_plans',
    )
    mailbox_thread = models.ForeignKey(
        'documents.DocumentMailboxThread',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='assistant_quick_sign_plans',
    )
    requires_reauth_password = models.BooleanField(default=True)
    credential_required = models.BooleanField(default=False)
    can_sign_now = models.BooleanField(default=False)
    already_signed = models.BooleanField(default=False)
    blocking_code = models.CharField(max_length=64, blank=True)
    blocking_reason = models.TextField(blank=True)
    last_error_code = models.CharField(max_length=64, blank=True)
    last_error_message = models.TextField(blank=True)
    forward_note = models.TextField(blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at', '-created_at']

    def __str__(self):
        return f'QuickSignPlan[{self.token}] -> document {self.document_id}'

    def save(self, *args, **kwargs):
        if self.company_id is None:
            if self.document_id and getattr(self.document, 'company_id', None):
                self.company = self.document.company
            elif self.created_by_id and getattr(getattr(self.created_by, 'company_membership', None), 'company_id', None):
                self.company = self.created_by.company_membership.company
        if not self.document_version_number and self.document_id:
            self.document_version_number = self.document.version_number
        super().save(*args, **kwargs)


class PdfSignatureRecord(models.Model):
    """
    Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
    Vai tro backend: Lop `PdfSignatureRecord` khai bao thuc the du lieu hoac bang nghiep vu cot loi cua file `signing/models.py`.
    Vai tro cua no trong frontend: Frontend khong khoi tao lop nay truc tiep; serializer, service va API doc trang thai cua model de dung danh sach, badge, form va man chi tiet.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/signing.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`. Nam trong pham vi module hien tai.
    Tac dung: Luu schema, quan he va hanh vi mac dinh de cac luong doc/ghi du lieu ve `PdfSignatureRecord` khong bi lech trang thai.
    """
    signed_pdf = models.ForeignKey(
        SignedPdfDocument,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name='signature_records',
    )
    packet = models.ForeignKey(
        SigningPacket,
        on_delete=models.CASCADE,
        related_name='signature_records',
    )
    task = models.OneToOneField(
        SigningTask,
        on_delete=models.CASCADE,
        related_name='signature_record',
    )
    signer_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='pdf_signature_records',
    )
    signature_field_name = models.CharField(max_length=255, blank=True)
    certificate_fingerprint = models.CharField(max_length=128)
    certificate_subject_dn = models.CharField(max_length=1000, blank=True)
    certificate_serial_number = models.CharField(max_length=128, blank=True)
    certificate_issuer_dn = models.CharField(max_length=1000, blank=True)
    signature_algorithm = models.CharField(max_length=128, blank=True)
    digest_algorithm = models.CharField(max_length=64, blank=True)
    provider_transaction_id = models.CharField(max_length=255, blank=True)
    signed_at = models.DateTimeField()
    verification_status = models.CharField(
        max_length=32,
        choices=VERIFY_STATUS_CHOICES,
        default=VERIFY_STATUS_UNKNOWN,
    )
    verification_report = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    

    class Meta:
        """
        Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
        Vai tro backend: Lop `Meta` dong goi mot cum hanh vi hoac cau hinh backend cua file `signing/models.py`.
        Vai tro cua no trong frontend: Frontend khong goi truc tiep lop nay; cac endpoint hoac service cua cung tinh nang se su dung no de tao du lieu trinh bay hoac kiem soat luong xu ly.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/signing.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`. Nam trong pham vi cua `PdfSignatureRecord` va cung dung chung ngu canh cua file nay.
        Tac dung: To chuc logic lien quan toi `Meta` thanh mot don vi ro rang de nhung ham khac goi lai de hon.
        """
        verbose_name = 'Lan ky PDF thuc'
        verbose_name_plural = 'Lan ky PDF thuc'
        ordering = ['signed_at', 'id']

    

    def __str__(self):
        """
        Thuoc chuc nang nao: Yeu cau ky, PDF da ky, Hom thu va Uy quyen ky so.
        Vai tro backend: Ham `__str__` la helper gan voi model hoac storage trong file `signing/models.py` trong lop `PdfSignatureRecord`, chu yeu de tra nhan hien thi gon cua doi tuong.
        Vai tro cua no trong frontend: Frontend khong goi truc tiep helper nay; no chi thay hau qua cua buoc tra nhan hien thi gon cua doi tuong qua ten file, duong dan luu hoac trang thai model duoc render ra giao dien.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/signing.py`, `signing.models`, `signing.permissions`, `signing.pki`, `signing.services`. Nam trong lop `PdfSignatureRecord` va phuc vu luong xu ly cua lop nay.
        Tac dung: Chuan hoa buoc tra nhan hien thi gon cua doi tuong ngay sat model de phan con lai cua code khong phai lap lai quy tac luu tru.
        """
        return f'{self.signer_user} -> packet {self.packet_id} [{self.verification_status}]'
