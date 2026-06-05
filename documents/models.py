"""
Thuoc chuc nang nao: Van ban cua toi, Van ban chia se trong nhom, Van ban chia se cong khai, Van ban yeu thich, Van ban da luu tru, Hom thu, Thung rac va Yeu cau phe duyet.
Vai tro backend: File `documents/models.py` giu hoac ho tro luong backend cho danh sach van ban, chi tiet van ban, version, chia se, luu tru, preview PDF, hom thu va xoa mem.
Vai tro cua no trong frontend: Cac man `/documents`, `/mailbox`, `/trash` va badge phe duyet doc ket qua do file nay cung cap hoac gian tiep lam thay doi.
Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/documents.py`, `documents.models`, `documents.mailbox_services`, `documents.pdf_preview`, `accounts.permissions`.
Tac dung: Bao dam vong doi van ban tu luc tao, chia se, xu ly hom thu toi luc phuc hoi hoac xoa vinh vien khong bi lech trang thai.
"""

from django.contrib.auth.models import User
from django.db import models

from accounts.peer_permissions import PeerPermissionLevel
from accounts.storage_paths import company_media_path
from document_templates.models import DocumentTemplate, TemplateCategory
from my_tennis_club.soft_delete import ActiveOnlyManager

DOC_STATUS_DRAFT = 'draft'
DOC_STATUS_FINAL = 'final'
DOC_STATUS_ARCHIVED = 'archived'
DOC_STATUS_CHOICES = [
    (DOC_STATUS_DRAFT, 'Nhap'),
    (DOC_STATUS_FINAL, 'Chinh thuc'),
    (DOC_STATUS_ARCHIVED, 'Luu tru'),
]


def _document_output_upload(instance, filename):
    return company_media_path(
        company=getattr(instance, 'company', None),
        section='generated_docs',
        filename=filename,
    )


def _document_version_output_upload(instance, filename):
    company = getattr(getattr(instance, 'document', None), 'company', None)
    return company_media_path(
        company=company,
        section='doc_versions',
        parts=[f'document_{instance.document_id or "unknown"}'],
        filename=filename,
    )

class DocumentNumberConfig(models.Model):
    """
    Thuoc chuc nang nao: Van ban cua toi, Van ban chia se trong nhom, Van ban chia se cong khai, Van ban yeu thich, Van ban da luu tru, Hom thu, Thung rac va Yeu cau phe duyet.
    Vai tro backend: Lop `DocumentNumberConfig` khai bao thuc the du lieu hoac bang nghiep vu cot loi cua file `documents/models.py`.
    Vai tro cua no trong frontend: Frontend khong khoi tao lop nay truc tiep; serializer, service va API doc trang thai cua model de dung danh sach, badge, form va man chi tiet.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/documents.py`, `documents.models`, `documents.mailbox_services`, `documents.pdf_preview`, `accounts.permissions`. Nam trong pham vi module hien tai.
    Tac dung: Luu schema, quan he va hanh vi mac dinh de cac luong doc/ghi du lieu ve `DocumentNumberConfig` khong bi lech trang thai.
    """
    department = models.ForeignKey(
        'accounts.Department',
        on_delete=models.CASCADE,
        related_name='number_configs',
        verbose_name='Phong ban',
    )
    category = models.ForeignKey(
        TemplateCategory,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        verbose_name='Danh muc',
    )
    prefix = models.CharField(max_length=20, verbose_name='Tien to')
    year = models.IntegerField(verbose_name='Nam')
    last_number = models.IntegerField(default=0, verbose_name='So cuoi')
    format_str = models.CharField(
        max_length=100,
        default='{prefix}-{number:04d}/{year}',
        verbose_name='Dinh dang ma so',
    )

    

    class Meta:
        """
        Thuoc chuc nang nao: Van ban cua toi, Van ban chia se trong nhom, Van ban chia se cong khai, Van ban yeu thich, Van ban da luu tru, Hom thu, Thung rac va Yeu cau phe duyet.
        Vai tro backend: Lop `Meta` dong goi mot cum hanh vi hoac cau hinh backend cua file `documents/models.py`.
        Vai tro cua no trong frontend: Frontend khong goi truc tiep lop nay; cac endpoint hoac service cua cung tinh nang se su dung no de tao du lieu trinh bay hoac kiem soat luong xu ly.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/documents.py`, `documents.models`, `documents.mailbox_services`, `documents.pdf_preview`, `accounts.permissions`. Nam trong pham vi cua `DocumentNumberConfig` va cung dung chung ngu canh cua file nay.
        Tac dung: To chuc logic lien quan toi `Meta` thanh mot don vi ro rang de nhung ham khac goi lai de hon.
        """
        verbose_name = 'Cau hinh ma so van ban'
        verbose_name_plural = 'Cau hinh ma so van ban'
        unique_together = ('department', 'prefix', 'year')

    

    def __str__(self):
        """
        Thuoc chuc nang nao: Van ban cua toi, Van ban chia se trong nhom, Van ban chia se cong khai, Van ban yeu thich, Van ban da luu tru, Hom thu, Thung rac va Yeu cau phe duyet.
        Vai tro backend: Ham `__str__` la helper gan voi model hoac storage trong file `documents/models.py` trong lop `DocumentNumberConfig`, chu yeu de tra nhan hien thi gon cua doi tuong.
        Vai tro cua no trong frontend: Frontend khong goi truc tiep helper nay; no chi thay hau qua cua buoc tra nhan hien thi gon cua doi tuong qua ten file, duong dan luu hoac trang thai model duoc render ra giao dien.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/documents.py`, `documents.models`, `documents.mailbox_services`, `documents.pdf_preview`, `accounts.permissions`. Phoi hop truc tiep voi cac method nhu `next_number` trong cung lop.
        Tac dung: Chuan hoa buoc tra nhan hien thi gon cua doi tuong ngay sat model de phan con lai cua code khong phai lap lai quy tac luu tru.
        """
        return f'{self.prefix} - {self.department.code} - {self.year}'

    

    def next_number(self):
        """
        Thuoc chuc nang nao: Van ban cua toi, Van ban chia se trong nhom, Van ban chia se cong khai, Van ban yeu thich, Van ban da luu tru, Hom thu, Thung rac va Yeu cau phe duyet.
        Vai tro backend: Ham `next_number` la method gan voi model trong file `documents/models.py` trong lop `DocumentNumberConfig`, phu trach phuc vu hanh vi phu tro quanh model hien tai.
        Vai tro cua no trong frontend: Frontend khong goi method model truc tiep, nhung serializer va API se dua vao ket qua phuc vu hanh vi phu tro quanh model hien tai nay de dung trang thai hoac nhan tren giao dien.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/documents.py`, `documents.models`, `documents.mailbox_services`, `documents.pdf_preview`, `accounts.permissions`. Phoi hop truc tiep voi cac method nhu `__str__` trong cung lop.
        Tac dung: Dua hanh vi phuc vu hanh vi phu tro quanh model hien tai ve dung noi du lieu duoc quan ly thay vi rai sang nhieu view hoac service khac.
        """
        from django.db import transaction

        with transaction.atomic():
            obj = DocumentNumberConfig.objects.select_for_update().get(pk=self.pk)
            obj.last_number += 1
            obj.save(update_fields=['last_number'])
            return obj.format_str.format(
                prefix=obj.prefix,
                number=obj.last_number,
                year=obj.year,
            )

SOURCE_GENERATED = 'generated'
SOURCE_UPLOADED = 'uploaded'
SOURCE_TYPE_CHOICES = [
    (SOURCE_GENERATED, 'Tao tu server'),
    (SOURCE_UPLOADED, 'Upload'),
]

VIS_PRIVATE = 'private'
VIS_GROUP = 'group'
VIS_PUBLIC = 'public'

SHARE_ACTIVE = 'active'
SHARE_PENDING_LEADER = 'pending_leader'
SHARE_PENDING_ADMIN = 'pending_admin'
SHARE_REJECTED = 'rejected'

MAILBOX_STATUS_VIEW = 'view'
MAILBOX_STATUS_FORWARDED = 'forward'
MAILBOX_STATUS_COMPLETED = 'completed'
MAILBOX_STATUS_REJECTED = 'rejected'
MAILBOX_STATUS_CHOICES = [
    (MAILBOX_STATUS_VIEW, 'Xem'),
    (MAILBOX_STATUS_FORWARDED, 'Dang duoc forward'),
    (MAILBOX_STATUS_COMPLETED, 'Da hoan thanh'),
    (MAILBOX_STATUS_REJECTED, 'Da bi tu choi'),
]

class Document(models.Model):
    """
    Thuoc chuc nang nao: Van ban cua toi, Van ban chia se trong nhom, Van ban chia se cong khai, Van ban yeu thich, Van ban da luu tru, Hom thu, Thung rac va Yeu cau phe duyet.
    Vai tro backend: Lop `Document` khai bao thuc the du lieu hoac bang nghiep vu cot loi cua file `documents/models.py`.
    Vai tro cua no trong frontend: Frontend khong khoi tao lop nay truc tiep; serializer, service va API doc trang thai cua model de dung danh sach, badge, form va man chi tiet.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/documents.py`, `documents.models`, `documents.mailbox_services`, `documents.pdf_preview`, `accounts.permissions`. Nam trong pham vi module hien tai.
    Tac dung: Luu schema, quan he va hanh vi mac dinh de cac luong doc/ghi du lieu ve `Document` khong bi lech trang thai.
    """
    title = models.CharField(max_length=255, verbose_name='Tieu de')
    company = models.ForeignKey(
        'accounts.Company',
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name='documents',
    )
    content = models.TextField(verbose_name='Noi dung (text)', blank=True)
    output_file = models.FileField(
        upload_to=_document_output_upload,
        max_length=500,
        blank=True,
        null=True,
        verbose_name='File DOCX da tao',
    )
    source_type = models.CharField(
        max_length=20,
        choices=SOURCE_TYPE_CHOICES,
        default=SOURCE_GENERATED,
        verbose_name='Nguon tao',
    )
    template = models.ForeignKey(
        DocumentTemplate,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='documents',
        verbose_name='Mau',
    )
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='documents')
    doc_number = models.CharField(max_length=100, blank=True, verbose_name='Ma so van ban')
    department = models.ForeignKey(
        'accounts.Department',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='documents',
        verbose_name='Phong ban',
    )
    category = models.ForeignKey(
        TemplateCategory,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='documents',
        verbose_name='Danh muc',
    )
    status = models.CharField(
        max_length=20,
        choices=DOC_STATUS_CHOICES,
        default=DOC_STATUS_DRAFT,
        verbose_name='Trang thai',
    )
    notes = models.TextField(blank=True, verbose_name='Ghi chu')
    tags = models.JSONField(default=list, blank=True, verbose_name='Tags')
    version_number = models.IntegerField(default=1, verbose_name='Phien ban')
    is_archived = models.BooleanField(default=False, verbose_name='Da luu tru')
    archived_at = models.DateTimeField(null=True, blank=True, verbose_name='Ngay luu tru')
    visibility = models.CharField(
        max_length=10,
        choices=[
            (VIS_PRIVATE, 'Rieng tu'),
            (VIS_GROUP, 'Nhom'),
            (VIS_PUBLIC, 'Cong khai'),
        ],
        default=VIS_PRIVATE,
        verbose_name='Pham vi hien thi',
    )
    group = models.ForeignKey(
        'accounts.UserGroup',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='documents',
        verbose_name='Nhom',
    )
    share_status = models.CharField(
        max_length=20,
        choices=[
            (SHARE_ACTIVE, 'Dang hoat dong'),
            (SHARE_PENDING_LEADER, 'Cho truong nhom duyet'),
            (SHARE_PENDING_ADMIN, 'Cho admin duyet'),
            (SHARE_REJECTED, 'Bi tu choi'),
        ],
        default=SHARE_ACTIVE,
        verbose_name='Trang thai chia se',
    )
    is_deleted = models.BooleanField(default=False, db_index=True)
    deleted_at = models.DateTimeField(null=True, blank=True, db_index=True)
    deleted_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='deleted_documents',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    prompt = models.ForeignKey(
        'prompts.Prompt',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='documents_using',
        verbose_name='Prompt da ap dung',
    )
    applied_prompt_snapshot = models.JSONField(
        null=True, blank=True,
        verbose_name='Snapshot prompt khi sinh',
    )

    PEER_SHARE_NONE = 'none'
    PEER_SHARE_PENDING_LEADER = 'pending_leader'
    PEER_SHARE_ACTIVE = 'active'
    PEER_SHARE_REJECTED = 'rejected'
    PEER_SHARE_STATUS_CHOICES = [
        (PEER_SHARE_NONE, 'Không chia sẻ'),
        (PEER_SHARE_PENDING_LEADER, 'Chờ trưởng nhóm duyệt'),
        (PEER_SHARE_ACTIVE, 'Đã kích hoạt'),
        (PEER_SHARE_REJECTED, 'Bị từ chối'),
    ]
    peer_share_status = models.CharField(
        max_length=20, choices=PEER_SHARE_STATUS_CHOICES,
        default=PEER_SHARE_NONE, db_index=True,
    )
    peer_share_approved_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL,
        related_name='peer_approved_documents',
    )
    peer_share_approved_at = models.DateTimeField(null=True, blank=True)
    peer_share_approver_note = models.TextField(blank=True)
    peer_share_submitted_at = models.DateTimeField(null=True, blank=True)

    objects = ActiveOnlyManager()
    all_objects = models.Manager()

    

    class Meta:
        """
        Thuoc chuc nang nao: Van ban cua toi, Van ban chia se trong nhom, Van ban chia se cong khai, Van ban yeu thich, Van ban da luu tru, Hom thu, Thung rac va Yeu cau phe duyet.
        Vai tro backend: Lop `Meta` dong goi mot cum hanh vi hoac cau hinh backend cua file `documents/models.py`.
        Vai tro cua no trong frontend: Frontend khong goi truc tiep lop nay; cac endpoint hoac service cua cung tinh nang se su dung no de tao du lieu trinh bay hoac kiem soat luong xu ly.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/documents.py`, `documents.models`, `documents.mailbox_services`, `documents.pdf_preview`, `accounts.permissions`. Nam trong pham vi cua `Document` va cung dung chung ngu canh cua file nay.
        Tac dung: To chuc logic lien quan toi `Meta` thanh mot don vi ro rang de nhung ham khac goi lai de hon.
        """
        verbose_name = 'Van ban'
        verbose_name_plural = 'Van ban'
        ordering = ['-updated_at']

    

    def __str__(self):
        """
        Thuoc chuc nang nao: Van ban cua toi, Van ban chia se trong nhom, Van ban chia se cong khai, Van ban yeu thich, Van ban da luu tru, Hom thu, Thung rac va Yeu cau phe duyet.
        Vai tro backend: Ham `__str__` la helper gan voi model hoac storage trong file `documents/models.py` trong lop `Document`, chu yeu de tra nhan hien thi gon cua doi tuong.
        Vai tro cua no trong frontend: Frontend khong goi truc tiep helper nay; no chi thay hau qua cua buoc tra nhan hien thi gon cua doi tuong qua ten file, duong dan luu hoac trang thai model duoc render ra giao dien.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/documents.py`, `documents.models`, `documents.mailbox_services`, `documents.pdf_preview`, `accounts.permissions`. Phoi hop truc tiep voi cac method nhu `get_status_badge_class`, `get_tag_list` trong cung lop.
        Tac dung: Chuan hoa buoc tra nhan hien thi gon cua doi tuong ngay sat model de phan con lai cua code khong phai lap lai quy tac luu tru.
        """
        return self.title

    def save(self, *args, **kwargs):
        if self.company_id is None:
            if self.template_id and getattr(self.template, 'company_id', None):
                self.company = self.template.company
            elif self.department_id and getattr(self.department, 'company_id', None):
                self.company = self.department.company
            elif self.category_id and getattr(self.category, 'company_id', None):
                self.company = self.category.company
            elif self.group_id and getattr(self.group, 'company_id', None):
                self.company = self.group.company
            elif self.owner_id and getattr(getattr(self.owner, 'company_membership', None), 'company_id', None):
                self.company = self.owner.company_membership.company
        super().save(*args, **kwargs)

    def get_tag_list(self):
        normalized = []
        seen = set()
        for raw_tag in self.tags or []:
            tag = ' '.join(str(raw_tag or '').strip().split())
            if not tag:
                continue
            key = tag.casefold()
            if key in seen:
                continue
            seen.add(key)
            normalized.append(tag)
        return normalized

    

    def get_status_badge_class(self):
        """
        Thuoc chuc nang nao: Van ban cua toi, Van ban chia se trong nhom, Van ban chia se cong khai, Van ban yeu thich, Van ban da luu tru, Hom thu, Thung rac va Yeu cau phe duyet.
        Vai tro backend: Ham `get_status_badge_class` la method gan voi model trong file `documents/models.py` trong lop `Document`, phu trach phuc vu hanh vi phu tro quanh model hien tai.
        Vai tro cua no trong frontend: Frontend khong goi method model truc tiep, nhung serializer va API se dua vao ket qua phuc vu hanh vi phu tro quanh model hien tai nay de dung trang thai hoac nhan tren giao dien.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/documents.py`, `documents.models`, `documents.mailbox_services`, `documents.pdf_preview`, `accounts.permissions`. Phoi hop truc tiep voi cac method nhu `__str__`, `get_tag_list` trong cung lop.
        Tac dung: Dua hanh vi phuc vu hanh vi phu tro quanh model hien tai ve dung noi du lieu duoc quan ly thay vi rai sang nhieu view hoac service khac.
        """
        return {
            DOC_STATUS_DRAFT: 'secondary',
            DOC_STATUS_FINAL: 'success',
            DOC_STATUS_ARCHIVED: 'dark',
        }.get(self.status, 'secondary')

    

    def get_tag_list(self):
        """
        Thuoc chuc nang nao: Van ban cua toi, Van ban chia se trong nhom, Van ban chia se cong khai, Van ban yeu thich, Van ban da luu tru, Hom thu, Thung rac va Yeu cau phe duyet.
        Vai tro backend: Ham `get_tag_list` la method gan voi model trong file `documents/models.py` trong lop `Document`, phu trach tra danh sach du lieu theo bo loc hien tai.
        Vai tro cua no trong frontend: Frontend khong goi method model truc tiep, nhung serializer va API se dua vao ket qua tra danh sach du lieu theo bo loc hien tai nay de dung trang thai hoac nhan tren giao dien.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/documents.py`, `documents.models`, `documents.mailbox_services`, `documents.pdf_preview`, `accounts.permissions`. Phoi hop truc tiep voi cac method nhu `__str__`, `get_status_badge_class` trong cung lop.
        Tac dung: Dua hanh vi tra danh sach du lieu theo bo loc hien tai ve dung noi du lieu duoc quan ly thay vi rai sang nhieu view hoac service khac.
        """
        return []

class DocumentFavorite(models.Model):
    """
    Thuoc chuc nang nao: Van ban cua toi, Van ban chia se trong nhom, Van ban chia se cong khai, Van ban yeu thich, Van ban da luu tru, Hom thu, Thung rac va Yeu cau phe duyet.
    Vai tro backend: Lop `DocumentFavorite` khai bao thuc the du lieu hoac bang nghiep vu cot loi cua file `documents/models.py`.
    Vai tro cua no trong frontend: Frontend khong khoi tao lop nay truc tiep; serializer, service va API doc trang thai cua model de dung danh sach, badge, form va man chi tiet.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/documents.py`, `documents.models`, `documents.mailbox_services`, `documents.pdf_preview`, `accounts.permissions`. Nam trong pham vi module hien tai.
    Tac dung: Luu schema, quan he va hanh vi mac dinh de cac luong doc/ghi du lieu ve `DocumentFavorite` khong bi lech trang thai.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='favorite_documents')
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='favorites')
    created_at = models.DateTimeField(auto_now_add=True)

    

    class Meta:
        """
        Thuoc chuc nang nao: Van ban cua toi, Van ban chia se trong nhom, Van ban chia se cong khai, Van ban yeu thich, Van ban da luu tru, Hom thu, Thung rac va Yeu cau phe duyet.
        Vai tro backend: Lop `Meta` dong goi mot cum hanh vi hoac cau hinh backend cua file `documents/models.py`.
        Vai tro cua no trong frontend: Frontend khong goi truc tiep lop nay; cac endpoint hoac service cua cung tinh nang se su dung no de tao du lieu trinh bay hoac kiem soat luong xu ly.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/documents.py`, `documents.models`, `documents.mailbox_services`, `documents.pdf_preview`, `accounts.permissions`. Nam trong pham vi cua `DocumentFavorite` va cung dung chung ngu canh cua file nay.
        Tac dung: To chuc logic lien quan toi `Meta` thanh mot don vi ro rang de nhung ham khac goi lai de hon.
        """
        unique_together = ('user', 'document')
        verbose_name = 'Van ban ua thich'

    

    def __str__(self):
        """
        Thuoc chuc nang nao: Van ban cua toi, Van ban chia se trong nhom, Van ban chia se cong khai, Van ban yeu thich, Van ban da luu tru, Hom thu, Thung rac va Yeu cau phe duyet.
        Vai tro backend: Ham `__str__` la helper gan voi model hoac storage trong file `documents/models.py` trong lop `DocumentFavorite`, chu yeu de tra nhan hien thi gon cua doi tuong.
        Vai tro cua no trong frontend: Frontend khong goi truc tiep helper nay; no chi thay hau qua cua buoc tra nhan hien thi gon cua doi tuong qua ten file, duong dan luu hoac trang thai model duoc render ra giao dien.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/documents.py`, `documents.models`, `documents.mailbox_services`, `documents.pdf_preview`, `accounts.permissions`. Nam trong lop `DocumentFavorite` va phuc vu luong xu ly cua lop nay.
        Tac dung: Chuan hoa buoc tra nhan hien thi gon cua doi tuong ngay sat model de phan con lai cua code khong phai lap lai quy tac luu tru.
        """
        return f'{self.user.username} likes {self.document.title}'

class DocumentVersion(models.Model):
    """
    Thuoc chuc nang nao: Van ban cua toi, Van ban chia se trong nhom, Van ban chia se cong khai, Van ban yeu thich, Van ban da luu tru, Hom thu, Thung rac va Yeu cau phe duyet.
    Vai tro backend: Lop `DocumentVersion` khai bao thuc the du lieu hoac bang nghiep vu cot loi cua file `documents/models.py`.
    Vai tro cua no trong frontend: Frontend khong khoi tao lop nay truc tiep; serializer, service va API doc trang thai cua model de dung danh sach, badge, form va man chi tiet.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/documents.py`, `documents.models`, `documents.mailbox_services`, `documents.pdf_preview`, `accounts.permissions`. Nam trong pham vi module hien tai.
    Tac dung: Luu schema, quan he va hanh vi mac dinh de cac luong doc/ghi du lieu ve `DocumentVersion` khong bi lech trang thai.
    """
    document = models.ForeignKey(
        Document,
        on_delete=models.CASCADE,
        related_name='versions',
        verbose_name='Van ban',
    )
    version_number = models.IntegerField(default=1, verbose_name='So phien ban')
    content = models.TextField(blank=True, verbose_name='Noi dung')
    output_file = models.FileField(
        upload_to=_document_version_output_upload,
        max_length=500,
        blank=True,
        null=True,
        verbose_name='File DOCX',
    )
    change_note = models.CharField(max_length=500, blank=True, verbose_name='Ghi chu thay doi')
    variables_used = models.JSONField(default=dict, blank=True, verbose_name='Bien da dung')
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='doc_versions',
        verbose_name='Nguoi tao',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    is_hidden = models.BooleanField(default=False, verbose_name='An')

    

    class Meta:
        """
        Thuoc chuc nang nao: Van ban cua toi, Van ban chia se trong nhom, Van ban chia se cong khai, Van ban yeu thich, Van ban da luu tru, Hom thu, Thung rac va Yeu cau phe duyet.
        Vai tro backend: Lop `Meta` dong goi mot cum hanh vi hoac cau hinh backend cua file `documents/models.py`.
        Vai tro cua no trong frontend: Frontend khong goi truc tiep lop nay; cac endpoint hoac service cua cung tinh nang se su dung no de tao du lieu trinh bay hoac kiem soat luong xu ly.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/documents.py`, `documents.models`, `documents.mailbox_services`, `documents.pdf_preview`, `accounts.permissions`. Nam trong pham vi cua `DocumentVersion` va cung dung chung ngu canh cua file nay.
        Tac dung: To chuc logic lien quan toi `Meta` thanh mot don vi ro rang de nhung ham khac goi lai de hon.
        """
        verbose_name = 'Phien ban van ban'
        verbose_name_plural = 'Phien ban van ban'
        ordering = ['-version_number']

    

    def __str__(self):
        """
        Thuoc chuc nang nao: Van ban cua toi, Van ban chia se trong nhom, Van ban chia se cong khai, Van ban yeu thich, Van ban da luu tru, Hom thu, Thung rac va Yeu cau phe duyet.
        Vai tro backend: Ham `__str__` la helper gan voi model hoac storage trong file `documents/models.py` trong lop `DocumentVersion`, chu yeu de tra nhan hien thi gon cua doi tuong.
        Vai tro cua no trong frontend: Frontend khong goi truc tiep helper nay; no chi thay hau qua cua buoc tra nhan hien thi gon cua doi tuong qua ten file, duong dan luu hoac trang thai model duoc render ra giao dien.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/documents.py`, `documents.models`, `documents.mailbox_services`, `documents.pdf_preview`, `accounts.permissions`. Nam trong lop `DocumentVersion` va phuc vu luong xu ly cua lop nay.
        Tac dung: Chuan hoa buoc tra nhan hien thi gon cua doi tuong ngay sat model de phan con lai cua code khong phai lap lai quy tac luu tru.
        """
        return f'{self.document.title} v{self.version_number}'

class DocumentMailboxThread(models.Model):
    """
    Thuoc chuc nang nao: Van ban cua toi, Van ban chia se trong nhom, Van ban chia se cong khai, Van ban yeu thich, Van ban da luu tru, Hom thu, Thung rac va Yeu cau phe duyet.
    Vai tro backend: Lop `DocumentMailboxThread` khai bao thuc the du lieu hoac bang nghiep vu cot loi cua file `documents/models.py`.
    Vai tro cua no trong frontend: Frontend khong khoi tao lop nay truc tiep; serializer, service va API doc trang thai cua model de dung danh sach, badge, form va man chi tiet.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/documents.py`, `documents.models`, `documents.mailbox_services`, `documents.pdf_preview`, `accounts.permissions`. Nam trong pham vi module hien tai.
    Tac dung: Luu schema, quan he va hanh vi mac dinh de cac luong doc/ghi du lieu ve `DocumentMailboxThread` khong bi lech trang thai.
    """
    document = models.ForeignKey(
        Document,
        on_delete=models.CASCADE,
        related_name='mailbox_threads',
    )
    company = models.ForeignKey(
        'accounts.Company',
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name='mailbox_threads',
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='created_mailbox_threads',
    )
    source_version_number = models.IntegerField(default=1)
    source_docx_sha256 = models.CharField(max_length=64, blank=True)
    source_signed_pdf = models.ForeignKey(
        'signing.SignedPdfDocument',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='mailbox_threads',
    )
    status = models.CharField(
        max_length=32,
        choices=MAILBOX_STATUS_CHOICES,
        default=MAILBOX_STATUS_VIEW,
    )
    last_action_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='mailbox_thread_actions',
    )
    last_action_at = models.DateTimeField(null=True, blank=True)
    last_action_summary = models.CharField(max_length=500, blank=True)
    last_action_reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    

    class Meta:
        """
        Thuoc chuc nang nao: Van ban cua toi, Van ban chia se trong nhom, Van ban chia se cong khai, Van ban yeu thich, Van ban da luu tru, Hom thu, Thung rac va Yeu cau phe duyet.
        Vai tro backend: Lop `Meta` dong goi mot cum hanh vi hoac cau hinh backend cua file `documents/models.py`.
        Vai tro cua no trong frontend: Frontend khong goi truc tiep lop nay; cac endpoint hoac service cua cung tinh nang se su dung no de tao du lieu trinh bay hoac kiem soat luong xu ly.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/documents.py`, `documents.models`, `documents.mailbox_services`, `documents.pdf_preview`, `accounts.permissions`. Nam trong pham vi cua `DocumentMailboxThread` va cung dung chung ngu canh cua file nay.
        Tac dung: To chuc logic lien quan toi `Meta` thanh mot don vi ro rang de nhung ham khac goi lai de hon.
        """
        verbose_name = 'Luong hom thu van ban'
        verbose_name_plural = 'Luong hom thu van ban'
        ordering = ['-updated_at', '-created_at']

    def __str__(self):
        """
        Thuoc chuc nang nao: Van ban cua toi, Van ban chia se trong nhom, Van ban chia se cong khai, Van ban yeu thich, Van ban da luu tru, Hom thu, Thung rac va Yeu cau phe duyet.
        Vai tro backend: Ham `__str__` la helper gan voi model hoac storage trong file `documents/models.py` trong lop `DocumentMailboxThread`, chu yeu de tra nhan hien thi gon cua doi tuong.
        Vai tro cua no trong frontend: Frontend khong goi truc tiep helper nay; no chi thay hau qua cua buoc tra nhan hien thi gon cua doi tuong qua ten file, duong dan luu hoac trang thai model duoc render ra giao dien.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/documents.py`, `documents.models`, `documents.mailbox_services`, `documents.pdf_preview`, `accounts.permissions`. Nam trong lop `DocumentMailboxThread` va phuc vu luong xu ly cua lop nay.
        Tac dung: Chuan hoa buoc tra nhan hien thi gon cua doi tuong ngay sat model de phan con lai cua code khong phai lap lai quy tac luu tru.
        """
        return f'MailboxThread #{self.pk} - {self.document.title}'

    def save(self, *args, **kwargs):
        if self.company_id is None:
            if self.document_id and getattr(self.document, 'company_id', None):
                self.company = self.document.company
            elif self.source_signed_pdf_id and getattr(self.source_signed_pdf, 'company_id', None):
                self.company = self.source_signed_pdf.company
            elif self.created_by_id and getattr(getattr(self.created_by, 'company_membership', None), 'company_id', None):
                self.company = self.created_by.company_membership.company
        super().save(*args, **kwargs)

class DocumentMailboxEntry(models.Model):
    """
    Thuoc chuc nang nao: Van ban cua toi, Van ban chia se trong nhom, Van ban chia se cong khai, Van ban yeu thich, Van ban da luu tru, Hom thu, Thung rac va Yeu cau phe duyet.
    Vai tro backend: Lop `DocumentMailboxEntry` khai bao thuc the du lieu hoac bang nghiep vu cot loi cua file `documents/models.py`.
    Vai tro cua no trong frontend: Frontend khong khoi tao lop nay truc tiep; serializer, service va API doc trang thai cua model de dung danh sach, badge, form va man chi tiet.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/documents.py`, `documents.models`, `documents.mailbox_services`, `documents.pdf_preview`, `accounts.permissions`. Nam trong pham vi module hien tai.
    Tac dung: Luu schema, quan he va hanh vi mac dinh de cac luong doc/ghi du lieu ve `DocumentMailboxEntry` khong bi lech trang thai.
    """
    thread = models.ForeignKey(
        DocumentMailboxThread,
        on_delete=models.CASCADE,
        related_name='entries',
    )
    company = models.ForeignKey(
        'accounts.Company',
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name='mailbox_entries',
    )
    parent_entry = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name='children',
    )
    forwarded_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='mailbox_entries_sent',
    )
    forwarded_to = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='mailbox_entries_received',
    )
    signed_pdf = models.ForeignKey(
        'signing.SignedPdfDocument',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='mailbox_entries',
    )
    status = models.CharField(
        max_length=32,
        choices=MAILBOX_STATUS_CHOICES,
        default=MAILBOX_STATUS_VIEW,
    )
    note = models.TextField(blank=True)
    action_reason = models.TextField(blank=True)
    actioned_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='mailbox_entry_actions',
    )
    actioned_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    

    class Meta:
        """
        Thuoc chuc nang nao: Van ban cua toi, Van ban chia se trong nhom, Van ban chia se cong khai, Van ban yeu thich, Van ban da luu tru, Hom thu, Thung rac va Yeu cau phe duyet.
        Vai tro backend: Lop `Meta` dong goi mot cum hanh vi hoac cau hinh backend cua file `documents/models.py`.
        Vai tro cua no trong frontend: Frontend khong goi truc tiep lop nay; cac endpoint hoac service cua cung tinh nang se su dung no de tao du lieu trinh bay hoac kiem soat luong xu ly.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/documents.py`, `documents.models`, `documents.mailbox_services`, `documents.pdf_preview`, `accounts.permissions`. Nam trong pham vi cua `DocumentMailboxEntry` va cung dung chung ngu canh cua file nay.
        Tac dung: To chuc logic lien quan toi `Meta` thanh mot don vi ro rang de nhung ham khac goi lai de hon.
        """
        verbose_name = 'Entry hom thu van ban'
        verbose_name_plural = 'Entry hom thu van ban'
        ordering = ['-created_at']

    

    def __str__(self):
        """
        Thuoc chuc nang nao: Van ban cua toi, Van ban chia se trong nhom, Van ban chia se cong khai, Van ban yeu thich, Van ban da luu tru, Hom thu, Thung rac va Yeu cau phe duyet.
        Vai tro backend: Ham `__str__` la helper gan voi model hoac storage trong file `documents/models.py` trong lop `DocumentMailboxEntry`, chu yeu de tra nhan hien thi gon cua doi tuong.
        Vai tro cua no trong frontend: Frontend khong goi truc tiep helper nay; no chi thay hau qua cua buoc tra nhan hien thi gon cua doi tuong qua ten file, duong dan luu hoac trang thai model duoc render ra giao dien.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/documents.py`, `documents.models`, `documents.mailbox_services`, `documents.pdf_preview`, `accounts.permissions`. Nam trong lop `DocumentMailboxEntry` va phuc vu luong xu ly cua lop nay.
        Tac dung: Chuan hoa buoc tra nhan hien thi gon cua doi tuong ngay sat model de phan con lai cua code khong phai lap lai quy tac luu tru.
        """
        return f'Entry #{self.pk} -> {self.forwarded_to}'

    def save(self, *args, **kwargs):
        if self.company_id is None:
            if self.thread_id and getattr(self.thread, 'company_id', None):
                self.company = self.thread.company
            elif self.signed_pdf_id and getattr(self.signed_pdf, 'company_id', None):
                self.company = self.signed_pdf.company
            elif self.forwarded_by_id and getattr(getattr(self.forwarded_by, 'company_membership', None), 'company_id', None):
                self.company = self.forwarded_by.company_membership.company
            elif self.forwarded_to_id and getattr(getattr(self.forwarded_to, 'company_membership', None), 'company_id', None):
                self.company = self.forwarded_to.company_membership.company
        super().save(*args, **kwargs)


class DocumentAudienceMember(models.Model):
    document = models.ForeignKey(
        Document, related_name='audience_members', on_delete=models.CASCADE,
    )
    user = models.ForeignKey(
        User, related_name='document_audience_memberships', on_delete=models.CASCADE,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    added_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL,
        related_name='document_audience_added',
    )
    permission_level = models.CharField(
        max_length=8,
        choices=PeerPermissionLevel.choices,
        default=PeerPermissionLevel.VIEW,
    )

    class Meta:
        verbose_name = 'Người được chia sẻ văn bản'
        verbose_name_plural = 'Người được chia sẻ văn bản'
        unique_together = ('document', 'user')
        indexes = [
            models.Index(fields=['document', 'user']),
            models.Index(fields=['user', '-created_at']),
        ]

    def __str__(self):
        return f'{self.document_id} -> {self.user_id}'


from .manual_edit_models import DocumentManualEditSession, DocumentManualEditSessionEvent  # noqa: E402
