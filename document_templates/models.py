"""
 ## Luồng kèm các hàm

  1. User mở màn “Chỉnh sửa mẫu”
     Flutter: _loadSession()
         ↓
  2. Gọi API tạo/lấy phiên chỉnh sửa
     Flutter: ensureSession(templateId)
         ↓
  3. Django tiếp nhận request
     View: template_manual_edit_session_create()
         ↓
  4. Kiểm tra quyền và tạo session
     Service: create_template_manual_edit_session()
         ↓
  5. Đảm bảo mẫu có file DOCX
     Service: _ensure_template_docx_source()
         ↓
  6. Tạo working copy từ DOCX gốc
     Service: _read_file_field_bytes()
              _save_field_bytes()
         ↓
  7. Tạo URL mở Collabora
     Serializer: get_editor_url()
     Provider: build_manual_edit_editor_url()
               build_manual_edit_wopi_src()
         ↓
  8. Flutter mở Collabora trong iframe
     Widget: ManualEditIFrame.build()
         ↓
  9. Collabora hỏi thông tin file
     View: template_manual_edit_wopi_file()
         ↓
  10. Collabora tải working copy
      View: template_manual_edit_wopi_contents() [GET]
         ↓
  11. User chỉnh sửa trong Collabora
         ↓
  12. Collabora khóa file
      View: _handle_wopi_lock_override()
         ↓
  13. Collabora autosave DOCX về Django
      View: template_manual_edit_wopi_contents() [PUT]
         ↓
  14. Django ghi DOCX mới vào working copy
      Service: update_template_manual_edit_working_copy()
               _save_field_bytes()
         ↓
  15. User bấm “Lưu & hoàn tất”
      Flutter: _finishSession()
         ↓
  16. Flutter yêu cầu Collabora lưu lần cuối
      Flutter: _flushEditorChanges()
               requestManualEditIFrameSave()
               _ManualEditFrameBridge.save()
               _requestSave()
         ↓
  17. Collabora gửi Action_Save_Resp
      Flutter: _ManualEditFrameBridge.handleMessage()
         ↓
  18. Flutter chờ working copy đã cập nhật
      Flutter: _waitForWorkingCopySync()
               getSession(sessionId)
         ↓
  19. Flutter gọi API hoàn tất
      Provider: finishSession(sessionId)
         ↓
  20. Django tiếp nhận
      View: template_manual_edit_session_finish()
         ↓
  21. Commit working copy thành mẫu chính
      Service: finish_template_manual_edit_session()
         ↓
  22. Lưu phiên bản cũ
      Versioning: create_template_version_snapshot()
         ↓
  23. Tăng version
      Service: _bump_template_version()
         ↓
  24. Cập nhật mẫu hiện hành
      Service: _save_field_bytes(template, 'docx_file')
      Model: template.save()
         ↓
  25. Xóa working copy và đóng session
      Service: _delete_session_working_copy()

  ## Giải thích từng nhóm hàm

  ### 1. Mở phiên chỉnh sửa

  _loadSession() tại template_manual_edit_screen.dart được chạy khi màn hình mở:

  final session = await ref
      .read(templateManualEditApiProvider)
      .ensureSession(widget.templateId);

  ensureSession() gọi:

  POST /api/templates/<id>/manual-edit/session/

  template_manual_edit_session_create() nhận request, lấy mẫu user được phép truy cập rồi gọi:

  create_template_manual_edit_session(
      user=request.user,
      template=template,
  )

  ## 2. Tạo working copy

  create_template_manual_edit_session() thực hiện:

  _require_manual_edit_provider()

  Kiểm tra Collabora đã cấu hình và hoạt động.

  get_active_template_manual_edit_session(template)

  Kiểm tra mẫu có đang bị người khác chỉnh sửa không.

  can_edit_template(user, template)

  Kiểm tra user có quyền sửa mẫu không.

  _ensure_template_docx_source(template)

  Đảm bảo mẫu có DOCX. Nếu mẫu chỉ có text thì render text thành DOCX.

  _read_file_field_bytes(template.docx_file)

  Đọc toàn bộ DOCX gốc thành bytes.

  _save_field_bytes(
      session,
      'working_copy_file',
      file_bytes=source_bytes,
  )

  Sao chép bytes sang working copy của session.

  ## 3. Tạo editor URL

  TemplateManualEditSessionSerializer.get_editor_url() gọi:

  build_manual_edit_editor_url()

  Hàm này tiếp tục gọi:

  build_manual_edit_wopi_src()

  Kết quả:

  Collabora URL
   + WOPISrc của Django
   + access_token
   + token TTL

  ## 4. Collabora lấy file

  ManualEditIFrame.build() nhúng URL Collabora:

  html.IFrameElement()..src = editorUrl;

  Collabora gọi template_manual_edit_wopi_file() để lấy:

  - Tên file.
  - Kích thước.
  - User.
  - Quyền ghi.
  - Phiên bản.
  - Khả năng lock.

  Sau đó Collabora gọi:

  template_manual_edit_wopi_contents()

  với HTTP GET để Django trả:

  FileResponse(session.working_copy_file.open('rb'))

  ## 5. Collabora lưu working copy

  Collabora gọi cùng endpoint template_manual_edit_wopi_contents() nhưng kèm:

  X-WOPI-Override: PUT

  View kiểm tra khóa bằng:

  _handle_wopi_lock_override()

  Sau đó gọi:

  update_template_manual_edit_working_copy(
      session=session,
      file_bytes=request.body,
  )

  Service dùng _save_field_bytes() để ghi DOCX mới vào working copy và cập nhật:

  session.working_copy_updated_at = timezone.now()

  ## 6. Lưu lần cuối

  Khi user bấm Lưu & hoàn tất, _finishSession() gọi:

  _flushEditorChanges(session)

  Hàm này gọi:

  requestManualEditIFrameSave()

  _ManualEditFrameBridge._requestSave() gửi vào iframe:

  {
    "MessageId": "Action_Save"
  }

  Collabora nhận lệnh, gửi DOCX mới về WOPI rồi trả:

  Action_Save_Resp

  handleMessage() nhận kết quả xác nhận.

  _waitForWorkingCopySync() liên tục gọi getSession() để chờ working_copy_updated_at thay đổi.

  ## 7. Commit mẫu

  Sau khi working copy đã đồng bộ, Flutter gọi:

  finishSession(session.id)

  View template_manual_edit_session_finish() gọi:

  finish_template_manual_edit_session()

  Trong đó:

  create_template_version_snapshot(template)

  Lưu DOCX và nội dung cũ vào TemplateVersion.

  template.version = _bump_template_version(template.version)

  Tăng 1.0 → 1.1.

  template.content = _extract_text_from_docx(...)

  Trích text từ DOCX mới.

  _save_field_bytes(template, 'docx_file', file_bytes=file_bytes)

  Thay DOCX hiện hành bằng file đã sửa.

  _delete_session_working_copy(session)

  Xóa file tạm và kết thúc session.

  Tóm tắt lời gọi:

  _loadSession
  → ensureSession
  → template_manual_edit_session_create
  → create_template_manual_edit_session
  → build_manual_edit_editor_url
  → ManualEditIFrame
  → template_manual_edit_wopi_file
  → template_manual_edit_wopi_contents GET/PUT
  → update_template_manual_edit_working_copy
  → _finishSession
  → requestManualEditIFrameSave
  → finishSession
  → template_manual_edit_session_finish
  → finish_template_manual_edit_session
  → create_template_version_snapshot
  → cập nhật DocumentTemplate
  → xóa working copy
"""

import re
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from accounts.peer_permissions import PeerPermissionLevel
from accounts.record_codes import TEMPLATE_RECORD_PREFIX, format_record_code
from accounts.storage_paths import company_media_path
from my_tennis_club.soft_delete import ActiveOnlyManager


# def _template_docx_upload xác định đường dẫn lưu file DOCX gốc của mẫu theo công ty.
# vd: upload mẫu DOCX công ty A -> 'companies/<slug-A>/template_docx/<file>.docx'.
def _template_docx_upload(instance, filename):
    return company_media_path(
        company=getattr(instance, 'company', None),
        section='template_docx',
        filename=filename,
    )


# def _template_version_docx_upload xác định đường dẫn lưu file DOCX của từng version mẫu (theo công ty + template_id).
# vd: -> 'companies/<slug>/template_versions/template_5/<file>.docx'.
def _template_version_docx_upload(instance, filename):
    company = getattr(getattr(instance, 'template', None), 'company', None)
    return company_media_path(
        company=company,
        section='template_versions',
        parts=[f'template_{instance.template_id or "unknown"}'],
        filename=filename,
    )

STATUS_DRAFT = 'draft'
STATUS_PENDING = 'pending'
STATUS_PENDING_LEADER = 'pending_leader'
STATUS_APPROVED = 'approved'
STATUS_REJECTED = 'rejected'
STATUS_CHOICES = [
    (STATUS_DRAFT, 'Nháp'),
    (STATUS_PENDING, 'Chờ duyệt'),
    (STATUS_PENDING_LEADER, 'Chờ trưởng nhóm duyệt'),
    (STATUS_APPROVED, 'Đã duyệt'),
    (STATUS_REJECTED, 'Bị từ chối'),
]

# class TemplateCategory là danh mục mẫu văn bản (theo công ty) để phân loại và lọc các DocumentTemplate.
# vd: 'Hợp đồng', 'Công văn' -> nhóm các mẫu cùng loại để dễ tìm.
class TemplateCategory(models.Model):
    """
    Thuoc chuc nang nao: Tao mau van ban, Mau dung chung, Mau phong ban, Mau rieng, Mau yeu thich va Tat ca mau (Admin).
    Vai tro backend: Lop `TemplateCategory` khai bao thuc the du lieu hoac bang nghiep vu cot loi cua file `document_templates/models.py`.
    Vai tro cua no trong frontend: Frontend khong khoi tao lop nay truc tiep; serializer, service va API doc trang thai cua model de dung danh sach, badge, form va man chi tiet.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/templates.py`, `accounts.permissions`, `document_templates.models`, `document_templates.utils`, `document_templates.versioning`. Nam trong pham vi module hien tai.
    Tac dung: Luu schema, quan he va hanh vi mac dinh de cac luong doc/ghi du lieu ve `TemplateCategory` khong bi lech trang thai.
    """
    name = models.CharField(max_length=100, verbose_name='Tên danh mục')
    description = models.TextField(blank=True, verbose_name='Mô tả')
    company = models.ForeignKey(
        'accounts.Company',
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name='template_categories',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    

    # class Meta: sắp xếp theo tên + ràng buộc tên danh mục là duy nhất trong mỗi công ty (uniq_template_category_company_name).
    # vd: công ty A không thể có 2 danh mục cùng tên 'Hợp đồng'.
    class Meta:
        """
        Thuoc chuc nang nao: Tao mau van ban, Mau dung chung, Mau phong ban, Mau rieng, Mau yeu thich va Tat ca mau (Admin).
        Vai tro backend: Lop `Meta` dong goi mot cum hanh vi hoac cau hinh backend cua file `document_templates/models.py`.
        Vai tro cua no trong frontend: Frontend khong goi truc tiep lop nay; cac endpoint hoac service cua cung tinh nang se su dung no de tao du lieu trinh bay hoac kiem soat luong xu ly.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/templates.py`, `accounts.permissions`, `document_templates.models`, `document_templates.utils`, `document_templates.versioning`. Nam trong pham vi cua `TemplateCategory` va cung dung chung ngu canh cua file nay.
        Tac dung: To chuc logic lien quan toi `Meta` thanh mot don vi ro rang de nhung ham khac goi lai de hon.
        """
        verbose_name = 'Danh mục mẫu'
        verbose_name_plural = 'Danh mục mẫu'
        ordering = ['name']
        constraints = [
            models.UniqueConstraint(fields=['company', 'name'], name='uniq_template_category_company_name'),
        ]

    

    # def __str__ hiển thị danh mục bằng chính tên của nó.
    # vd: -> 'Hợp đồng'.
    def __str__(self):
        """
        Thuoc chuc nang nao: Tao mau van ban, Mau dung chung, Mau phong ban, Mau rieng, Mau yeu thich va Tat ca mau (Admin).
        Vai tro backend: Ham `__str__` la helper gan voi model hoac storage trong file `document_templates/models.py` trong lop `TemplateCategory`, chu yeu de tra nhan hien thi gon cua doi tuong.
        Vai tro cua no trong frontend: Frontend khong goi truc tiep helper nay; no chi thay hau qua cua buoc tra nhan hien thi gon cua doi tuong qua ten file, duong dan luu hoac trang thai model duoc render ra giao dien.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/templates.py`, `accounts.permissions`, `document_templates.models`, `document_templates.utils`, `document_templates.versioning`. Nam trong lop `TemplateCategory` va phuc vu luong xu ly cua lop nay.
        Tac dung: Chuan hoa buoc tra nhan hien thi gon cua doi tuong ngay sat model de phan con lai cua code khong phai lap lai quy tac luu tru.
        """
        return self.name

# class DocumentTemplate là MẪU văn bản — thực thể lõi của module: nguồn (nhập thủ công / file DOCX), nội dung + biến {{...}}, phạm vi (private/group/public), quy trình duyệt (status), công ty/phòng ban/nhóm sở hữu, file DOCX gốc, chia sẻ ngang hàng (peer_share) và soft-delete. Dùng để sinh văn bản bằng cách điền biến.
# vd: mẫu 'Đơn xin nghỉ' (source=docx, visibility=group, status=approved) -> dùng để sinh đơn cho nhân viên.
class DocumentTemplate(models.Model):
    """
    Thuoc chuc nang nao: Tao mau van ban, Mau dung chung, Mau phong ban, Mau rieng, Mau yeu thich va Tat ca mau (Admin).
    Vai tro backend: Lop `DocumentTemplate` khai bao thuc the du lieu hoac bang nghiep vu cot loi cua file `document_templates/models.py`.
    Vai tro cua no trong frontend: Frontend khong khoi tao lop nay truc tiep; serializer, service va API doc trang thai cua model de dung danh sach, badge, form va man chi tiet.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/templates.py`, `accounts.permissions`, `document_templates.models`, `document_templates.utils`, `document_templates.versioning`. Nam trong pham vi module hien tai.
    Tac dung: Luu schema, quan he va hanh vi mac dinh de cac luong doc/ghi du lieu ve `DocumentTemplate` khong bi lech trang thai.
    """
    SOURCE_MANUAL = 'manual'
    SOURCE_DOCX = 'docx'
    SOURCE_CHOICES = [
        (SOURCE_MANUAL, 'Nhập thủ công'),
        (SOURCE_DOCX, 'Upload file DOCX'),
    ]

    VISIBILITY_PRIVATE = 'private'
    VISIBILITY_GROUP = 'group'
    VISIBILITY_PUBLIC = 'public'
    VISIBILITY_CHOICES = [
        (VISIBILITY_PRIVATE, 'Riêng tư'),
        (VISIBILITY_GROUP, 'Nhóm'),
        (VISIBILITY_PUBLIC, 'Công khai'),
    ]

    title = models.CharField(max_length=255, verbose_name='Tên mẫu')
    description = models.TextField(blank=True, verbose_name='Mô tả')
    content = models.TextField(verbose_name='Nội dung mẫu (text)')
    company = models.ForeignKey(
        'accounts.Company',
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name='document_templates',
    )
    source_type = models.CharField(
        max_length=10, choices=SOURCE_CHOICES,
        default=SOURCE_MANUAL, verbose_name='Loại nguồn'
    )
    docx_file = models.FileField(
        upload_to=_template_docx_upload, max_length=500, blank=True, null=True,
        verbose_name='File DOCX gốc'
    )
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='templates')
    is_shared = models.BooleanField(default=False, verbose_name='Chia sẻ')

    
    category = models.ForeignKey(
        TemplateCategory, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='templates',
        verbose_name='Danh mục'
    )
    department = models.ForeignKey(
        'accounts.Department', null=True, blank=True,
        on_delete=models.SET_NULL, related_name='templates',
        verbose_name='Phòng ban'
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES,
        default=STATUS_DRAFT, verbose_name='Trạng thái'
    )
    notes = models.CharField(max_length=500, blank=True, verbose_name='Ghi chú')
    tags = models.JSONField(default=list, blank=True, verbose_name='Tags')
    effective_date = models.DateField(null=True, blank=True, verbose_name='Ngày hiệu lực')
    end_date = models.DateField(null=True, blank=True, verbose_name='Ngày kết thúc hiệu lực')
    version = models.CharField(max_length=20, default='1.0', verbose_name='Phiên bản')
    approved_by = models.ForeignKey(
        User, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='approved_templates',
        verbose_name='Người duyệt'
    )
    approved_at = models.DateTimeField(null=True, blank=True, verbose_name='Ngày duyệt')
    approver_note = models.TextField(blank=True, verbose_name='Ghi chú người duyệt')

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
        verbose_name='Trạng thái chia sẻ đồng nghiệp',
    )
    peer_share_approved_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL,
        related_name='peer_approved_templates',
    )
    peer_share_approved_at = models.DateTimeField(null=True, blank=True)
    peer_share_approver_note = models.TextField(blank=True)
    peer_share_submitted_at = models.DateTimeField(null=True, blank=True)

    visibility = models.CharField(
        max_length=10, choices=VISIBILITY_CHOICES,
        default=VISIBILITY_PRIVATE, verbose_name='Phạm vi hiển thị'
    )
    group = models.ForeignKey(
        'accounts.UserGroup', null=True, blank=True,
        on_delete=models.SET_NULL, related_name='templates',
        verbose_name='Nhóm'
    )
    parent_template = models.ForeignKey(
        'self', null=True, blank=True,
        on_delete=models.SET_NULL, related_name='derived_templates',
        verbose_name='Mẫu gốc'
    )

    is_deleted = models.BooleanField(default=False, db_index=True)
    deleted_at = models.DateTimeField(null=True, blank=True, db_index=True)
    deleted_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='deleted_templates',
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = ActiveOnlyManager()
    all_objects = models.Manager()

    

    # class Meta: cấu hình sắp xếp / index / soft-delete cho DocumentTemplate.
    # vd: danh sách mẫu hiển thị theo thứ tự đã cấu hình.
    class Meta:
        """
        Thuoc chuc nang nao: Tao mau van ban, Mau dung chung, Mau phong ban, Mau rieng, Mau yeu thich va Tat ca mau (Admin).
        Vai tro backend: Lop `Meta` dong goi mot cum hanh vi hoac cau hinh backend cua file `document_templates/models.py`.
        Vai tro cua no trong frontend: Frontend khong goi truc tiep lop nay; cac endpoint hoac service cua cung tinh nang se su dung no de tao du lieu trinh bay hoac kiem soat luong xu ly.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/templates.py`, `accounts.permissions`, `document_templates.models`, `document_templates.utils`, `document_templates.versioning`. Nam trong pham vi cua `DocumentTemplate` va cung dung chung ngu canh cua file nay.
        Tac dung: To chuc logic lien quan toi `Meta` thanh mot don vi ro rang de nhung ham khac goi lai de hon.
        """
        verbose_name = 'Mẫu văn bản'
        verbose_name_plural = 'Mẫu văn bản'
        ordering = ['-updated_at']

    

    # def __str__ hiển thị mẫu bằng tiêu đề.
    # vd: -> 'Đơn xin nghỉ phép'.
    def __str__(self):
        """
        Thuoc chuc nang nao: Tao mau van ban, Mau dung chung, Mau phong ban, Mau rieng, Mau yeu thich va Tat ca mau (Admin).
        Vai tro backend: Ham `__str__` la helper gan voi model hoac storage trong file `document_templates/models.py` trong lop `DocumentTemplate`, chu yeu de tra nhan hien thi gon cua doi tuong.
        Vai tro cua no trong frontend: Frontend khong goi truc tiep helper nay; no chi thay hau qua cua buoc tra nhan hien thi gon cua doi tuong qua ten file, duong dan luu hoac trang thai model duoc render ra giao dien.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/templates.py`, `accounts.permissions`, `document_templates.models`, `document_templates.utils`, `document_templates.versioning`. Phoi hop truc tiep voi cac method nhu `get_variables`, `render`, `render_as_docx` trong cung lop.
        Tac dung: Chuan hoa buoc tra nhan hien thi gon cua doi tuong ngay sat model de phan con lai cua code khong phai lap lai quy tac luu tru.
        """
        return self.title

    # def record_code (property) sinh mã định danh hiển thị của mẫu theo tiền tố + id (format_record_code).
    # vd: pk=5 -> mã kiểu 'MAU-000005'.
    @property
    def record_code(self):
        return format_record_code(TEMPLATE_RECORD_PREFIX, self.pk)

    # def save tự suy ra company nếu chưa có: ưu tiên theo category -> department -> group -> owner, đảm bảo mẫu luôn thuộc đúng công ty (phân quyền đa công ty).
    # vd: tạo mẫu gắn category của công ty A nhưng chưa set company -> tự gán company=A.
    def save(self, *args, **kwargs):
        if self.company_id is None:
            if self.category_id and getattr(self.category, 'company_id', None):
                self.company = self.category.company
            elif self.department_id and getattr(self.department, 'company_id', None):
                self.company = self.department.company
            elif self.group_id and getattr(self.group, 'company_id', None):
                self.company = self.group.company
            elif self.owner_id and getattr(getattr(self.owner, 'company_membership', None), 'company_id', None):
                self.company = self.owner.company_membership.company
        super().save(*args, **kwargs)

    

    # def get_variables trích danh sách tên biến {{...}} của mẫu: ưu tiên đọc từ file DOCX gốc (khớp đúng lúc sinh văn bản), fallback sang trường content; có cache _cached_variables.
    # vd: mẫu chứa {{ho_ten}}, {{ngay}} -> ['ho_ten','ngay'].
    def get_variables(self):
        """
        Thuoc chuc nang nao: Tao mau van ban, Mau dung chung, Mau phong ban, Mau rieng, Mau yeu thich va Tat ca mau (Admin).
        Vai tro backend: Ham `get_variables` la method gan voi model trong file `document_templates/models.py` trong lop `DocumentTemplate`, phu trach phuc vu hanh vi phu tro quanh model hien tai.
        Vai tro cua no trong frontend: Frontend khong goi method model truc tiep, nhung serializer va API se dua vao ket qua phuc vu hanh vi phu tro quanh model hien tai nay de dung trang thai hoac nhan tren giao dien.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/templates.py`, `accounts.permissions`, `document_templates.models`, `document_templates.utils`, `document_templates.versioning`. Phoi hop truc tiep voi cac method nhu `__str__`, `render`, `render_as_docx` trong cung lop.
        Tac dung: Dua hanh vi phuc vu hanh vi phu tro quanh model hien tai ve dung noi du lieu duoc quan ly thay vi rai sang nhieu view hoac service khac.
        """
        
        from .utils import extract_template_variables
        # Mau nguon DOCX duoc render tu chinh file .docx (render_docx_from_template),
        # nen phai detect bien tu file do de khop voi luc sinh van ban. Truong text
        # `content` co the bi lech (vi du sau khi chinh sua tren trinh soan web /
        # Collabora, file .docx duoc cap nhat nhung `content` chua dong bo), nen chi
        # dung `content` lam phuong an du phong.
        if getattr(self, '_cached_variables', None) is not None:
            return self._cached_variables

        variables = []
        docx_file = getattr(self, 'docx_file', None)
        if self.source_type == self.SOURCE_DOCX and docx_file:
            try:
                import os

                from .utils import extract_text_from_docx

                docx_path = getattr(docx_file, 'path', '')
                if docx_path and os.path.exists(docx_path):
                    with docx_file.open('rb') as handle:
                        variables = extract_template_variables(
                            extract_text_from_docx(handle)
                        )
            except Exception:
                variables = []

        if not variables:
            variables = extract_template_variables(self.content)

        self._cached_variables = variables
        return variables

    

    # def render điền giá trị biến vào nội dung text/HTML của mẫu (fill_variables_in_text), trả về nội dung đã điền.
    # vd: '{{ho_ten}}' + {'ho_ten':'A'} -> 'A'.
    def render(self, variables_dict):
        """
        Thuoc chuc nang nao: Tao mau van ban, Mau dung chung, Mau phong ban, Mau rieng, Mau yeu thich va Tat ca mau (Admin).
        Vai tro backend: Ham `render` la method gan voi model trong file `document_templates/models.py` trong lop `DocumentTemplate`, phu trach render noi dung dau ra de tra ve hoac luu tru.
        Vai tro cua no trong frontend: Frontend khong goi method model truc tiep, nhung serializer va API se dua vao ket qua render noi dung dau ra de tra ve hoac luu tru nay de dung trang thai hoac nhan tren giao dien.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/templates.py`, `accounts.permissions`, `document_templates.models`, `document_templates.utils`, `document_templates.versioning`. Phoi hop truc tiep voi cac method nhu `__str__`, `get_variables`, `render_as_docx` trong cung lop.
        Tac dung: Dua hanh vi render noi dung dau ra de tra ve hoac luu tru ve dung noi du lieu duoc quan ly thay vi rai sang nhieu view hoac service khac.
        """
        from .utils import fill_variables_in_text
        return fill_variables_in_text(self.content, variables_dict)

    

    # def render_as_docx xuất mẫu thành file DOCX đã điền biến: mẫu DOCX còn file gốc -> render giữ đúng định dạng (render_docx_from_template); không thì dựng DOCX từ HTML/text của content; allow_content_fallback=False mà mất file gốc -> ValueError.
    # vd: mẫu DOCX -> file .docx điền biến giữ nguyên layout.
    def render_as_docx(self, variables_dict=None, *, allow_content_fallback=True):
        """
        Thuoc chuc nang nao: Tao mau van ban, Mau dung chung, Mau phong ban, Mau rieng, Mau yeu thich va Tat ca mau (Admin).
        Vai tro backend: Ham `render_as_docx` la method gan voi model trong file `document_templates/models.py` trong lop `DocumentTemplate`, phu trach render noi dung dau ra de tra ve hoac luu tru.
        Vai tro cua no trong frontend: Frontend khong goi method model truc tiep, nhung serializer va API se dua vao ket qua render noi dung dau ra de tra ve hoac luu tru nay de dung trang thai hoac nhan tren giao dien.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/templates.py`, `accounts.permissions`, `document_templates.models`, `document_templates.utils`, `document_templates.versioning`. Phoi hop truc tiep voi cac method nhu `__str__`, `get_variables`, `render` trong cung lop.
        Tac dung: Dua hanh vi render noi dung dau ra de tra ve hoac luu tru ve dung noi du lieu duoc quan ly thay vi rai sang nhieu view hoac service khac.
        """
        import os

        from .utils import create_docx_from_html, create_docx_from_text, render_docx_from_template
        variables_dict = variables_dict or {}
        docx_source_name = getattr(self.docx_file, 'name', '') if getattr(self, 'docx_file', None) else ''
        docx_source_path = getattr(self.docx_file, 'path', '') if docx_source_name else ''
        has_docx_source = bool(docx_source_path) and os.path.exists(docx_source_path)
        if self.source_type == self.SOURCE_DOCX and has_docx_source:
            return render_docx_from_template(docx_source_path, variables_dict)
        if self.source_type == self.SOURCE_DOCX and not allow_content_fallback:
            raise ValueError('Mau DOCX nay khong con file DOCX goc de xuat dung dinh dang.')
        if self.content and self.content.strip():
            
            rendered_html = self.render(variables_dict)
            try:
                return create_docx_from_html(rendered_html)
            except Exception:
                rendered_text = re.sub(r'<[^>]+>', '', rendered_html)
                return create_docx_from_text(rendered_text)
        return create_docx_from_text(self.render(variables_dict))

    

    # def can_be_used cho biết mẫu có dùng được để sinh văn bản chưa: đã duyệt (approved) HOẶC là mẫu thủ công riêng tư (private + manual).
    # vd: mẫu group chưa duyệt -> False; mẫu private thủ công -> True.
    def can_be_used(self):
        """
        Thuoc chuc nang nao: Tao mau van ban, Mau dung chung, Mau phong ban, Mau rieng, Mau yeu thich va Tat ca mau (Admin).
        Vai tro backend: Ham `can_be_used` la method gan voi model trong file `document_templates/models.py` trong lop `DocumentTemplate`, phu trach phuc vu hanh vi phu tro quanh model hien tai.
        Vai tro cua no trong frontend: Frontend khong goi method model truc tiep, nhung serializer va API se dua vao ket qua phuc vu hanh vi phu tro quanh model hien tai nay de dung trang thai hoac nhan tren giao dien.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/templates.py`, `accounts.permissions`, `document_templates.models`, `document_templates.utils`, `document_templates.versioning`. Phoi hop truc tiep voi cac method nhu `__str__`, `get_variables`, `render` trong cung lop.
        Tac dung: Dua hanh vi phuc vu hanh vi phu tro quanh model hien tai ve dung noi du lieu duoc quan ly thay vi rai sang nhieu view hoac service khac.
        """
        return self.status == STATUS_APPROVED or (
            self.source_type == self.SOURCE_MANUAL and self.visibility == self.VISIBILITY_PRIVATE
        )

    

    # def submit_for_approval đặt trạng thái duyệt theo phạm vi + vai trò: superuser/private -> approved ngay; group mà là trưởng nhóm -> approved, không phải -> pending_leader; public -> pending; tự điền approved_by/at khi cần.
    # vd: nhân viên gửi mẫu group -> status='pending_leader' (chờ trưởng nhóm duyệt).
    def submit_for_approval(self):
        """
        Thuoc chuc nang nao: Tao mau van ban, Mau dung chung, Mau phong ban, Mau rieng, Mau yeu thich va Tat ca mau (Admin).
        Vai tro backend: Ham `submit_for_approval` la method gan voi model trong file `document_templates/models.py` trong lop `DocumentTemplate`, phu trach gui yeu cau sang buoc duyet hoac buoc xu ly ke tiep.
        Vai tro cua no trong frontend: Frontend khong goi method model truc tiep, nhung serializer va API se dua vao ket qua gui yeu cau sang buoc duyet hoac buoc xu ly ke tiep nay de dung trang thai hoac nhan tren giao dien.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/templates.py`, `accounts.permissions`, `document_templates.models`, `document_templates.utils`, `document_templates.versioning`. Phoi hop truc tiep voi cac method nhu `__str__`, `get_variables`, `render` trong cung lop.
        Tac dung: Dua hanh vi gui yeu cau sang buoc duyet hoac buoc xu ly ke tiep ve dung noi du lieu duoc quan ly thay vi rai sang nhieu view hoac service khac.
        """
        from accounts.permissions import is_leader_of

        if self.owner and self.owner.is_superuser:
            self.status = STATUS_APPROVED
            self.approved_by = self.owner
            self.approved_at = timezone.now()
            self.approver_note = ''
            self.save(update_fields=['status', 'approved_by', 'approved_at', 'approver_note'])
            return
        if self.visibility == self.VISIBILITY_PRIVATE:
            self.status = STATUS_APPROVED
        elif self.visibility == self.VISIBILITY_GROUP and self.group and is_leader_of(self.owner, self.group):
            self.status = STATUS_APPROVED
        elif self.visibility == self.VISIBILITY_GROUP:
            self.status = STATUS_PENDING_LEADER
        else:
            self.status = STATUS_PENDING
        if self.status != STATUS_APPROVED:
            self.approved_by = None
            self.approved_at = None
            self.approver_note = ''
            self.save(update_fields=['status', 'approved_by', 'approved_at', 'approver_note'])
            return
        if self.visibility != self.VISIBILITY_PRIVATE and self.owner and not self.approved_by:
            self.approved_by = self.owner
            self.approved_at = timezone.now()
            self.approver_note = ''
            self.save(update_fields=['status', 'approved_by', 'approved_at', 'approver_note'])
            return
        self.save(update_fields=['status'])

    

    # def get_status_badge_class ánh xạ trạng thái -> class màu badge cho UI (draft→secondary, pending→warning, approved→success, rejected→danger).
    # vd: status='approved' -> 'success' (badge xanh).
    def get_status_badge_class(self):
        """
        Thuoc chuc nang nao: Tao mau van ban, Mau dung chung, Mau phong ban, Mau rieng, Mau yeu thich va Tat ca mau (Admin).
        Vai tro backend: Ham `get_status_badge_class` la method gan voi model trong file `document_templates/models.py` trong lop `DocumentTemplate`, phu trach phuc vu hanh vi phu tro quanh model hien tai.
        Vai tro cua no trong frontend: Frontend khong goi method model truc tiep, nhung serializer va API se dua vao ket qua phuc vu hanh vi phu tro quanh model hien tai nay de dung trang thai hoac nhan tren giao dien.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/templates.py`, `accounts.permissions`, `document_templates.models`, `document_templates.utils`, `document_templates.versioning`. Phoi hop truc tiep voi cac method nhu `__str__`, `get_variables`, `render` trong cung lop.
        Tac dung: Dua hanh vi phuc vu hanh vi phu tro quanh model hien tai ve dung noi du lieu duoc quan ly thay vi rai sang nhieu view hoac service khac.
        """
        return {
            STATUS_DRAFT: 'secondary',
            STATUS_PENDING: 'warning',
            STATUS_APPROVED: 'success',
            STATUS_REJECTED: 'danger',
        }.get(self.status, 'secondary')

    

    # def get_tag_list tách trường notes thành danh sách tag (ngăn cách bởi dấu phẩy, bỏ rỗng).
    # vd: notes='hanh chinh, mau moi' -> ['hanh chinh','mau moi'].
    def get_tag_list(self):
        """
        Thuoc chuc nang nao: Tao mau van ban, Mau dung chung, Mau phong ban, Mau rieng, Mau yeu thich va Tat ca mau (Admin).
        Vai tro backend: Ham `get_tag_list` la method gan voi model trong file `document_templates/models.py` trong lop `DocumentTemplate`, phu trach tra danh sach du lieu theo bo loc hien tai.
        Vai tro cua no trong frontend: Frontend khong goi method model truc tiep, nhung serializer va API se dua vao ket qua tra danh sach du lieu theo bo loc hien tai nay de dung trang thai hoac nhan tren giao dien.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/templates.py`, `accounts.permissions`, `document_templates.models`, `document_templates.utils`, `document_templates.versioning`. Phoi hop truc tiep voi cac method nhu `__str__`, `get_variables`, `render` trong cung lop.
        Tac dung: Dua hanh vi tra danh sach du lieu theo bo loc hien tai ve dung noi du lieu duoc quan ly thay vi rai sang nhieu view hoac service khac.
        """
        return [t.strip() for t in self.notes.split(',') if t.strip()]

# class TemplateVersion lưu một phiên bản (snapshot) nội dung + file DOCX của mẫu qua từng lần chỉnh sửa, phục vụ lịch sử và khôi phục.
# vd: mỗi lần 'Lưu & hoàn tất' khi sửa mẫu -> tạo 1 TemplateVersion mới.
class TemplateVersion(models.Model):
    """
    Thuoc chuc nang nao: Tao mau van ban, Mau dung chung, Mau phong ban, Mau rieng, Mau yeu thich va Tat ca mau (Admin).
    Vai tro backend: Lop `TemplateVersion` khai bao thuc the du lieu hoac bang nghiep vu cot loi cua file `document_templates/models.py`.
    Vai tro cua no trong frontend: Frontend khong khoi tao lop nay truc tiep; serializer, service va API doc trang thai cua model de dung danh sach, badge, form va man chi tiet.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/templates.py`, `accounts.permissions`, `document_templates.models`, `document_templates.utils`, `document_templates.versioning`. Nam trong pham vi module hien tai.
    Tac dung: Luu schema, quan he va hanh vi mac dinh de cac luong doc/ghi du lieu ve `TemplateVersion` khong bi lech trang thai.
    """
    template = models.ForeignKey(
        DocumentTemplate, related_name='versions', on_delete=models.CASCADE
    )
    version_number = models.CharField(max_length=20, verbose_name='Số phiên bản')
    content = models.TextField(verbose_name='Nội dung snapshot')
    docx_file = models.FileField(
        upload_to=_template_version_docx_upload, max_length=500, blank=True, null=True,
        verbose_name='File DOCX phiên bản'
    )
    change_note = models.TextField(blank=True, verbose_name='Ghi chú thay đổi')
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name='template_versions'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    is_hidden = models.BooleanField(default=False, verbose_name='Ẩn phiên bản')

    

    # class Meta: sắp xếp các version (theo số version/thời gian) gắn với template.
    # vd: liệt kê lịch sử version của 1 mẫu.
    class Meta:
        """
        Thuoc chuc nang nao: Tao mau van ban, Mau dung chung, Mau phong ban, Mau rieng, Mau yeu thich va Tat ca mau (Admin).
        Vai tro backend: Lop `Meta` dong goi mot cum hanh vi hoac cau hinh backend cua file `document_templates/models.py`.
        Vai tro cua no trong frontend: Frontend khong goi truc tiep lop nay; cac endpoint hoac service cua cung tinh nang se su dung no de tao du lieu trinh bay hoac kiem soat luong xu ly.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/templates.py`, `accounts.permissions`, `document_templates.models`, `document_templates.utils`, `document_templates.versioning`. Nam trong pham vi cua `TemplateVersion` va cung dung chung ngu canh cua file nay.
        Tac dung: To chuc logic lien quan toi `Meta` thanh mot don vi ro rang de nhung ham khac goi lai de hon.
        """
        verbose_name = 'Phiên bản mẫu'
        verbose_name_plural = 'Phiên bản mẫu'
        ordering = ['-created_at']

    

    # def __str__ hiển thị version dạng mẫu + số version.
    # vd: -> 'Đơn xin nghỉ v1.2'.
    def __str__(self):
        """
        Thuoc chuc nang nao: Tao mau van ban, Mau dung chung, Mau phong ban, Mau rieng, Mau yeu thich va Tat ca mau (Admin).
        Vai tro backend: Ham `__str__` la helper gan voi model hoac storage trong file `document_templates/models.py` trong lop `TemplateVersion`, chu yeu de tra nhan hien thi gon cua doi tuong.
        Vai tro cua no trong frontend: Frontend khong goi truc tiep helper nay; no chi thay hau qua cua buoc tra nhan hien thi gon cua doi tuong qua ten file, duong dan luu hoac trang thai model duoc render ra giao dien.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/templates.py`, `accounts.permissions`, `document_templates.models`, `document_templates.utils`, `document_templates.versioning`. Nam trong lop `TemplateVersion` va phuc vu luong xu ly cua lop nay.
        Tac dung: Chuan hoa buoc tra nhan hien thi gon cua doi tuong ngay sat model de phan con lai cua code khong phai lap lai quy tac luu tru.
        """
        return f"{self.template.title} v{self.version_number}"

# class TemplatePermission là phân quyền (legacy) trên mẫu cho user/nhóm: xem / sửa / xóa.
# vd: cấp quyền sửa mẫu #5 cho user #12.
class TemplatePermission(models.Model):
    """
    Thuoc chuc nang nao: Tao mau van ban, Mau dung chung, Mau phong ban, Mau rieng, Mau yeu thich va Tat ca mau (Admin).
    Vai tro backend: Lop `TemplatePermission` khai bao thuc the du lieu hoac bang nghiep vu cot loi cua file `document_templates/models.py`.
    Vai tro cua no trong frontend: Frontend khong khoi tao lop nay truc tiep; serializer, service va API doc trang thai cua model de dung danh sach, badge, form va man chi tiet.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/templates.py`, `accounts.permissions`, `document_templates.models`, `document_templates.utils`, `document_templates.versioning`. Nam trong pham vi module hien tai.
    Tac dung: Luu schema, quan he va hanh vi mac dinh de cac luong doc/ghi du lieu ve `TemplatePermission` khong bi lech trang thai.
    """
    template = models.ForeignKey(
        DocumentTemplate, related_name='permissions', on_delete=models.CASCADE
    )
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='template_permissions'
    )
    can_view = models.BooleanField(default=True, verbose_name='Xem')
    can_edit = models.BooleanField(default=False, verbose_name='Sửa nội dung')
    can_delete = models.BooleanField(default=False, verbose_name='Xóa mẫu')
    can_use = models.BooleanField(default=True, verbose_name='Dùng tạo văn bản')
    can_approve = models.BooleanField(default=False, verbose_name='Duyệt mẫu')

    

    # class Meta: ràng buộc không trùng quyền + index tra cứu.
    # vd: 1 cặp (mẫu, user) chỉ có 1 bản ghi quyền.
    class Meta:
        """
        Thuoc chuc nang nao: Tao mau van ban, Mau dung chung, Mau phong ban, Mau rieng, Mau yeu thich va Tat ca mau (Admin).
        Vai tro backend: Lop `Meta` dong goi mot cum hanh vi hoac cau hinh backend cua file `document_templates/models.py`.
        Vai tro cua no trong frontend: Frontend khong goi truc tiep lop nay; cac endpoint hoac service cua cung tinh nang se su dung no de tao du lieu trinh bay hoac kiem soat luong xu ly.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/templates.py`, `accounts.permissions`, `document_templates.models`, `document_templates.utils`, `document_templates.versioning`. Nam trong pham vi cua `TemplatePermission` va cung dung chung ngu canh cua file nay.
        Tac dung: To chuc logic lien quan toi `Meta` thanh mot don vi ro rang de nhung ham khac goi lai de hon.
        """
        verbose_name = 'Phân quyền mẫu'
        verbose_name_plural = 'Phân quyền mẫu'
        unique_together = ('template', 'user')

    

    # def __str__ hiển thị quyền dạng mẫu -> đối tượng.
    # vd: -> 'template 5 -> user 12'.
    def __str__(self):
        """
        Thuoc chuc nang nao: Tao mau van ban, Mau dung chung, Mau phong ban, Mau rieng, Mau yeu thich va Tat ca mau (Admin).
        Vai tro backend: Ham `__str__` la helper gan voi model hoac storage trong file `document_templates/models.py` trong lop `TemplatePermission`, chu yeu de tra nhan hien thi gon cua doi tuong.
        Vai tro cua no trong frontend: Frontend khong goi truc tiep helper nay; no chi thay hau qua cua buoc tra nhan hien thi gon cua doi tuong qua ten file, duong dan luu hoac trang thai model duoc render ra giao dien.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/templates.py`, `accounts.permissions`, `document_templates.models`, `document_templates.utils`, `document_templates.versioning`. Nam trong lop `TemplatePermission` va phuc vu luong xu ly cua lop nay.
        Tac dung: Chuan hoa buoc tra nhan hien thi gon cua doi tuong ngay sat model de phan con lai cua code khong phai lap lai quy tac luu tru.
        """
        return f"{self.template.title} – {self.user.username}"

# class TemplateAudienceMember là bản ghi chia sẻ mẫu cho một đồng nghiệp cụ thể (peer share) kèm mức quyền (view/edit...).
# vd: chia sẻ mẫu #5 cho user #12 quyền VIEW.
class TemplateAudienceMember(models.Model):
    """
    Thuoc chuc nang nao: Tao mau van ban, Mau dung chung, Mau phong ban, Mau rieng, Mau yeu thich va Tat ca mau (Admin).
    Vai tro backend: Lop `TemplateAudienceMember` khai bao thuc the du lieu hoac bang nghiep vu cot loi cua file `document_templates/models.py`.
    Vai tro cua no trong frontend: Frontend khong khoi tao lop nay truc tiep; serializer, service va API doc trang thai cua model de dung danh sach, badge, form va man chi tiet.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/templates.py`, `accounts.permissions`, `document_templates.models`, `document_templates.utils`, `document_templates.versioning`. Nam trong pham vi module hien tai.
    Tac dung: Luu schema, quan he va hanh vi mac dinh de cac luong doc/ghi du lieu ve `TemplateAudienceMember` khong bi lech trang thai.
    """
    template = models.ForeignKey(
        DocumentTemplate,
        related_name='audience_members',
        on_delete=models.CASCADE,
        verbose_name='Mau van ban',
    )
    user = models.ForeignKey(
        User,
        related_name='template_audience_memberships',
        on_delete=models.CASCADE,
        verbose_name='Nguoi duoc dung mau',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    added_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL,
        related_name='template_audience_added',
    )
    permission_level = models.CharField(
        max_length=8,
        choices=PeerPermissionLevel.choices,
        default=PeerPermissionLevel.VIEW,
    )

    

    # class Meta: mỗi cặp (template, user) là duy nhất + index để tra cứu nhanh.
    # vd: không chia sẻ trùng 1 mẫu cho cùng một user.
    class Meta:
        """
        Thuoc chuc nang nao: Tao mau van ban, Mau dung chung, Mau phong ban, Mau rieng, Mau yeu thich va Tat ca mau (Admin).
        Vai tro backend: Lop `Meta` dong goi mot cum hanh vi hoac cau hinh backend cua file `document_templates/models.py`.
        Vai tro cua no trong frontend: Frontend khong goi truc tiep lop nay; cac endpoint hoac service cua cung tinh nang se su dung no de tao du lieu trinh bay hoac kiem soat luong xu ly.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/templates.py`, `accounts.permissions`, `document_templates.models`, `document_templates.utils`, `document_templates.versioning`. Nam trong pham vi cua `TemplateAudienceMember` va cung dung chung ngu canh cua file nay.
        Tac dung: To chuc logic lien quan toi `Meta` thanh mot don vi ro rang de nhung ham khac goi lai de hon.
        """
        verbose_name = 'Nguoi duoc dung mau theo nhom'
        verbose_name_plural = 'Nguoi duoc dung mau theo nhom'
        unique_together = ('template', 'user')

    

    # def __str__ hiển thị quan hệ chia sẻ dạng template -> user.
    # vd: -> '5 -> 12'.
    def __str__(self):
        """
        Thuoc chuc nang nao: Tao mau van ban, Mau dung chung, Mau phong ban, Mau rieng, Mau yeu thich va Tat ca mau (Admin).
        Vai tro backend: Ham `__str__` la helper gan voi model hoac storage trong file `document_templates/models.py` trong lop `TemplateAudienceMember`, chu yeu de tra nhan hien thi gon cua doi tuong.
        Vai tro cua no trong frontend: Frontend khong goi truc tiep helper nay; no chi thay hau qua cua buoc tra nhan hien thi gon cua doi tuong qua ten file, duong dan luu hoac trang thai model duoc render ra giao dien.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/templates.py`, `accounts.permissions`, `document_templates.models`, `document_templates.utils`, `document_templates.versioning`. Nam trong lop `TemplateAudienceMember` va phuc vu luong xu ly cua lop nay.
        Tac dung: Chuan hoa buoc tra nhan hien thi gon cua doi tuong ngay sat model de phan con lai cua code khong phai lap lai quy tac luu tru.
        """
        return f'{self.template.title} -> {self.user.username}'

# class PendingTemplateAssignment lưu việc gán/phân công mẫu đang ở trạng thái chờ xử lý (vd gán cho phòng ban/người khi mẫu chưa sẵn sàng).
# vd: gán mẫu cho phòng ban X, chờ xử lý/duyệt.
class PendingTemplateAssignment(models.Model):
    """
    Thuoc chuc nang nao: Tao mau van ban, Mau dung chung, Mau phong ban, Mau rieng, Mau yeu thich va Tat ca mau (Admin).
    Vai tro backend: Lop `PendingTemplateAssignment` khai bao thuc the du lieu hoac bang nghiep vu cot loi cua file `document_templates/models.py`.
    Vai tro cua no trong frontend: Frontend khong khoi tao lop nay truc tiep; serializer, service va API doc trang thai cua model de dung danh sach, badge, form va man chi tiet.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/templates.py`, `accounts.permissions`, `document_templates.models`, `document_templates.utils`, `document_templates.versioning`. Nam trong pham vi module hien tai.
    Tac dung: Luu schema, quan he va hanh vi mac dinh de cac luong doc/ghi du lieu ve `PendingTemplateAssignment` khong bi lech trang thai.
    """
    ASSIGN_GROUP   = 'group'
    ASSIGN_PRIVATE = 'private'
    ASSIGN_CHOICES = [('group', 'Nhóm'), ('private', 'Riêng tư')]

    template_name     = models.CharField(max_length=255, verbose_name='Tên mẫu (từ Excel)')
    assign_type       = models.CharField(max_length=10, choices=ASSIGN_CHOICES, verbose_name='Loại phân quyền')
    group             = models.ForeignKey(
        'accounts.UserGroup', null=True, blank=True,
        on_delete=models.CASCADE, related_name='pending_template_assignments',
        verbose_name='Nhóm'
    )
    user              = models.ForeignKey(
        User, null=True, blank=True,
        on_delete=models.CASCADE, related_name='pending_template_assignments',
        verbose_name='Người dùng'
    )
    document_template = models.ForeignKey(
        DocumentTemplate, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='pending_assignments',
        verbose_name='Mẫu đã áp dụng'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    

    # class Meta: cấu hình sắp xếp/ràng buộc cho bản ghi phân công chờ.
    # vd: liệt kê các phân công đang chờ.
    class Meta:
        """
        Thuoc chuc nang nao: Tao mau van ban, Mau dung chung, Mau phong ban, Mau rieng, Mau yeu thich va Tat ca mau (Admin).
        Vai tro backend: Lop `Meta` dong goi mot cum hanh vi hoac cau hinh backend cua file `document_templates/models.py`.
        Vai tro cua no trong frontend: Frontend khong goi truc tiep lop nay; cac endpoint hoac service cua cung tinh nang se su dung no de tao du lieu trinh bay hoac kiem soat luong xu ly.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/templates.py`, `accounts.permissions`, `document_templates.models`, `document_templates.utils`, `document_templates.versioning`. Nam trong pham vi cua `PendingTemplateAssignment` va cung dung chung ngu canh cua file nay.
        Tac dung: To chuc logic lien quan toi `Meta` thanh mot don vi ro rang de nhung ham khac goi lai de hon.
        """
        verbose_name = 'Chờ phân quyền mẫu'
        verbose_name_plural = 'Chờ phân quyền mẫu'

    

    # def __str__ tóm tắt bản ghi phân công ngắn gọn.
    # vd: -> mô tả việc gán mẫu cho đối tượng.
    def __str__(self):
        """
        Thuoc chuc nang nao: Tao mau van ban, Mau dung chung, Mau phong ban, Mau rieng, Mau yeu thich va Tat ca mau (Admin).
        Vai tro backend: Ham `__str__` la helper gan voi model hoac storage trong file `document_templates/models.py` trong lop `PendingTemplateAssignment`, chu yeu de tra nhan hien thi gon cua doi tuong.
        Vai tro cua no trong frontend: Frontend khong goi truc tiep helper nay; no chi thay hau qua cua buoc tra nhan hien thi gon cua doi tuong qua ten file, duong dan luu hoac trang thai model duoc render ra giao dien.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/templates.py`, `accounts.permissions`, `document_templates.models`, `document_templates.utils`, `document_templates.versioning`. Nam trong lop `PendingTemplateAssignment` va phuc vu luong xu ly cua lop nay.
        Tac dung: Chuan hoa buoc tra nhan hien thi gon cua doi tuong ngay sat model de phan con lai cua code khong phai lap lai quy tac luu tru.
        """
        target = self.group.name if self.group else (self.user.username if self.user else '?')
        return f'"{self.template_name}" → {self.assign_type}: {target}'

# class TemplateFavorite đánh dấu một user yêu thích (ghim) một mẫu để truy cập nhanh.
# vd: user #3 ghim mẫu #5 -> hiện ở tab 'Mẫu yêu thích'.
class TemplateFavorite(models.Model):
    """
    Thuoc chuc nang nao: Tao mau van ban, Mau dung chung, Mau phong ban, Mau rieng, Mau yeu thich va Tat ca mau (Admin).
    Vai tro backend: Lop `TemplateFavorite` khai bao thuc the du lieu hoac bang nghiep vu cot loi cua file `document_templates/models.py`.
    Vai tro cua no trong frontend: Frontend khong khoi tao lop nay truc tiep; serializer, service va API doc trang thai cua model de dung danh sach, badge, form va man chi tiet.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/templates.py`, `accounts.permissions`, `document_templates.models`, `document_templates.utils`, `document_templates.versioning`. Nam trong pham vi module hien tai.
    Tac dung: Luu schema, quan he va hanh vi mac dinh de cac luong doc/ghi du lieu ve `TemplateFavorite` khong bi lech trang thai.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='favorite_templates')
    template = models.ForeignKey(
        DocumentTemplate, on_delete=models.CASCADE, related_name='favorites'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    

    # class Meta: mỗi cặp (user, template) là duy nhất + index.
    # vd: không ghim trùng một mẫu.
    class Meta:
        """
        Thuoc chuc nang nao: Tao mau van ban, Mau dung chung, Mau phong ban, Mau rieng, Mau yeu thich va Tat ca mau (Admin).
        Vai tro backend: Lop `Meta` dong goi mot cum hanh vi hoac cau hinh backend cua file `document_templates/models.py`.
        Vai tro cua no trong frontend: Frontend khong goi truc tiep lop nay; cac endpoint hoac service cua cung tinh nang se su dung no de tao du lieu trinh bay hoac kiem soat luong xu ly.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/templates.py`, `accounts.permissions`, `document_templates.models`, `document_templates.utils`, `document_templates.versioning`. Nam trong pham vi cua `TemplateFavorite` va cung dung chung ngu canh cua file nay.
        Tac dung: To chuc logic lien quan toi `Meta` thanh mot don vi ro rang de nhung ham khac goi lai de hon.
        """
        unique_together = ('user', 'template')
        verbose_name = 'Mẫu ưa thích'

    

    # def __str__ hiển thị quan hệ yêu thích dạng user -> template.
    # vd: -> '3 ♥ 5'.
    def __str__(self):
        """
        Thuoc chuc nang nao: Tao mau van ban, Mau dung chung, Mau phong ban, Mau rieng, Mau yeu thich va Tat ca mau (Admin).
        Vai tro backend: Ham `__str__` la helper gan voi model hoac storage trong file `document_templates/models.py` trong lop `TemplateFavorite`, chu yeu de tra nhan hien thi gon cua doi tuong.
        Vai tro cua no trong frontend: Frontend khong goi truc tiep helper nay; no chi thay hau qua cua buoc tra nhan hien thi gon cua doi tuong qua ten file, duong dan luu hoac trang thai model duoc render ra giao dien.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/templates.py`, `accounts.permissions`, `document_templates.models`, `document_templates.utils`, `document_templates.versioning`. Nam trong lop `TemplateFavorite` va phuc vu luong xu ly cua lop nay.
        Tac dung: Chuan hoa buoc tra nhan hien thi gon cua doi tuong ngay sat model de phan con lai cua code khong phai lap lai quy tac luu tru.
        """
        return f"{self.user.username} ♥ {self.template.title}"

# class TemplateApprovalLog ghi nhật ký các hành động duyệt mẫu (ai duyệt/từ chối, thời điểm, ghi chú) để truy vết.
# vd: trưởng nhóm duyệt mẫu #5 -> 1 dòng log 'approved by ...'.
class TemplateApprovalLog(models.Model):
    """
    Thuoc chuc nang nao: Tao mau van ban, Mau dung chung, Mau phong ban, Mau rieng, Mau yeu thich va Tat ca mau (Admin).
    Vai tro backend: Lop `TemplateApprovalLog` khai bao thuc the du lieu hoac bang nghiep vu cot loi cua file `document_templates/models.py`.
    Vai tro cua no trong frontend: Frontend khong khoi tao lop nay truc tiep; serializer, service va API doc trang thai cua model de dung danh sach, badge, form va man chi tiet.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/templates.py`, `accounts.permissions`, `document_templates.models`, `document_templates.utils`, `document_templates.versioning`. Nam trong pham vi module hien tai.
    Tac dung: Luu schema, quan he va hanh vi mac dinh de cac luong doc/ghi du lieu ve `TemplateApprovalLog` khong bi lech trang thai.
    """
    ACTION_SUBMIT = 'submit'
    ACTION_APPROVE = 'approve'
    ACTION_REJECT = 'reject'
    ACTION_CHOICES = [
        (ACTION_SUBMIT, 'Gửi duyệt'),
        (ACTION_APPROVE, 'Duyệt'),
        (ACTION_REJECT, 'Từ chối'),
    ]

    template = models.ForeignKey(
        DocumentTemplate, related_name='approval_logs', on_delete=models.CASCADE
    )
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    actor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    comment = models.TextField(blank=True, verbose_name='Ghi chú')
    created_at = models.DateTimeField(auto_now_add=True)

    

    # class Meta: sắp xếp log mới nhất lên đầu + index.
    # vd: xem lịch sử duyệt của 1 mẫu.
    class Meta:
        """
        Thuoc chuc nang nao: Tao mau van ban, Mau dung chung, Mau phong ban, Mau rieng, Mau yeu thich va Tat ca mau (Admin).
        Vai tro backend: Lop `Meta` dong goi mot cum hanh vi hoac cau hinh backend cua file `document_templates/models.py`.
        Vai tro cua no trong frontend: Frontend khong goi truc tiep lop nay; cac endpoint hoac service cua cung tinh nang se su dung no de tao du lieu trinh bay hoac kiem soat luong xu ly.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/templates.py`, `accounts.permissions`, `document_templates.models`, `document_templates.utils`, `document_templates.versioning`. Nam trong pham vi cua `TemplateApprovalLog` va cung dung chung ngu canh cua file nay.
        Tac dung: To chuc logic lien quan toi `Meta` thanh mot don vi ro rang de nhung ham khac goi lai de hon.
        """
        verbose_name = 'Lịch sử phê duyệt'
        verbose_name_plural = 'Lịch sử phê duyệt'
        ordering = ['-created_at']

    

    # def __str__ tóm tắt một dòng log duyệt.
    # vd: -> 'template 5 approved ...'.
    def __str__(self):
        """
        Thuoc chuc nang nao: Tao mau van ban, Mau dung chung, Mau phong ban, Mau rieng, Mau yeu thich va Tat ca mau (Admin).
        Vai tro backend: Ham `__str__` la helper gan voi model hoac storage trong file `document_templates/models.py` trong lop `TemplateApprovalLog`, chu yeu de tra nhan hien thi gon cua doi tuong.
        Vai tro cua no trong frontend: Frontend khong goi truc tiep helper nay; no chi thay hau qua cua buoc tra nhan hien thi gon cua doi tuong qua ten file, duong dan luu hoac trang thai model duoc render ra giao dien.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/templates.py`, `accounts.permissions`, `document_templates.models`, `document_templates.utils`, `document_templates.versioning`. Nam trong lop `TemplateApprovalLog` va phuc vu luong xu ly cua lop nay.
        Tac dung: Chuan hoa buoc tra nhan hien thi gon cua doi tuong ngay sat model de phan con lai cua code khong phai lap lai quy tac luu tru.
        """
        return f"{self.template.title} – {self.get_action_display()} by {self.actor}"

# class TemplateReviewNotification là thông báo cho người duyệt khi có mẫu cần xem xét (chờ duyệt): gắn người nhận, mẫu và trạng thái đọc.
# vd: nhân viên gửi mẫu group -> tạo thông báo cho trưởng nhóm.
class TemplateReviewNotification(models.Model):
    """
    Thuoc chuc nang nao: Tao mau van ban, Mau dung chung, Mau phong ban, Mau rieng, Mau yeu thich va Tat ca mau (Admin).
    Vai tro backend: Lop `TemplateReviewNotification` khai bao thuc the du lieu hoac bang nghiep vu cot loi cua file `document_templates/models.py`.
    Vai tro cua no trong frontend: Frontend khong khoi tao lop nay truc tiep; serializer, service va API doc trang thai cua model de dung danh sach, badge, form va man chi tiet.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/templates.py`, `accounts.permissions`, `document_templates.models`, `document_templates.utils`, `document_templates.versioning`. Nam trong pham vi module hien tai.
    Tac dung: Luu schema, quan he va hanh vi mac dinh de cac luong doc/ghi du lieu ve `TemplateReviewNotification` khong bi lech trang thai.
    """
    ACTION_APPROVE = TemplateApprovalLog.ACTION_APPROVE
    ACTION_REJECT = TemplateApprovalLog.ACTION_REJECT
    ACTION_CHOICES = [
        (ACTION_APPROVE, 'Duyet'),
        (ACTION_REJECT, 'Tu choi'),
    ]

    recipient = models.ForeignKey(
        User,
        related_name='template_review_notifications',
        on_delete=models.CASCADE,
    )
    template = models.ForeignKey(
        DocumentTemplate,
        related_name='review_notifications',
        on_delete=models.CASCADE,
    )
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    actor = models.ForeignKey(
        User,
        related_name='template_review_notifications_sent',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    comment = models.TextField(blank=True)
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    

    # class Meta: sắp xếp mới nhất lên đầu + index theo người nhận.
    # vd: đếm số thông báo chưa đọc của trưởng nhóm.
    class Meta:
        """
        Thuoc chuc nang nao: Tao mau van ban, Mau dung chung, Mau phong ban, Mau rieng, Mau yeu thich va Tat ca mau (Admin).
        Vai tro backend: Lop `Meta` dong goi mot cum hanh vi hoac cau hinh backend cua file `document_templates/models.py`.
        Vai tro cua no trong frontend: Frontend khong goi truc tiep lop nay; cac endpoint hoac service cua cung tinh nang se su dung no de tao du lieu trinh bay hoac kiem soat luong xu ly.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/templates.py`, `accounts.permissions`, `document_templates.models`, `document_templates.utils`, `document_templates.versioning`. Nam trong pham vi cua `TemplateReviewNotification` va cung dung chung ngu canh cua file nay.
        Tac dung: To chuc logic lien quan toi `Meta` thanh mot don vi ro rang de nhung ham khac goi lai de hon.
        """
        verbose_name = 'Thong bao duyet mau'
        verbose_name_plural = 'Thong bao duyet mau'
        ordering = ['-created_at']

    

    # def __str__ tóm tắt thông báo duyệt.
    # vd: -> 'review: template 5 -> leader 8'.
    def __str__(self):
        """
        Thuoc chuc nang nao: Tao mau van ban, Mau dung chung, Mau phong ban, Mau rieng, Mau yeu thich va Tat ca mau (Admin).
        Vai tro backend: Ham `__str__` la helper gan voi model hoac storage trong file `document_templates/models.py` trong lop `TemplateReviewNotification`, chu yeu de tra nhan hien thi gon cua doi tuong.
        Vai tro cua no trong frontend: Frontend khong goi truc tiep helper nay; no chi thay hau qua cua buoc tra nhan hien thi gon cua doi tuong qua ten file, duong dan luu hoac trang thai model duoc render ra giao dien.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `api/serializers/templates.py`, `accounts.permissions`, `document_templates.models`, `document_templates.utils`, `document_templates.versioning`. Nam trong lop `TemplateReviewNotification` va phuc vu luong xu ly cua lop nay.
        Tac dung: Chuan hoa buoc tra nhan hien thi gon cua doi tuong ngay sat model de phan con lai cua code khong phai lap lai quy tac luu tru.
        """
        return f'{self.recipient.username} <- {self.template.title} ({self.action})'


from .manual_edit_models import (  # noqa: E402
    TemplateManualEditSession,
    TemplateManualEditSessionEvent,
)
