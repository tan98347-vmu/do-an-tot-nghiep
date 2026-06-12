# Chức năng web liên quan: Tạo mẫu văn bản, Mẫu dùng chung, Mẫu phòng ban của tôi, Mẫu riêng của tôi, Mẫu yêu thích và Tất cả mẫu (Admin).
# Vai trò backend trong luồng: Tệp này giữ phần logic backend dùng chung cho danh sách mẫu, chi tiết mẫu, form tạo mẫu, bulk upload và preview biến, để các flow ở các tab Mẫu dùng chung, Mẫu phòng ban, Mẫu riêng, Mẫu yêu thích, màn chi tiết mẫu, form tạo mẫu và bulk upload không phải lặp lại cùng một rule ở nhiều nơi.
# Đầu vào/đầu ra chính: Giữ các helper, cấu hình và rule backend dùng lại ở nhiều flow khác nhau.
# Người dùng sẽ thấy trên web: Người dùng sẽ thấy dữ liệu, badge trạng thái, quyền nút và thông báo trên các chức năng Tạo mẫu văn bản, Mẫu dùng chung, Mẫu phòng ban của tôi, Mẫu riêng của tôi, Mẫu yêu thích và Tất cả mẫu (Admin) thay đổi đúng theo kết quả nghiệp vụ.

from django.contrib import admin
from .models import (
    DocumentTemplate,
    TemplateCategory,
    TemplateVersion,
    TemplatePermission,
    TemplateApprovalLog,
    TemplateAudienceMember,
)

# [Web] `TemplateCategoryAdmin` gom một cụm xử lý backend dùng chung cho nhóm màn Mẫu văn bản.

# vd: trang admin hiển thị/lọc các bản ghi của model này.
@admin.register(TemplateCategory)
class TemplateCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'created_at')
    search_fields = ('name',)

# [Web] `DocumentTemplateAdmin` gom một cụm xử lý backend dùng chung cho nhóm màn Mẫu văn bản.

# vd: trang admin hiển thị/lọc các bản ghi của model này.
@admin.register(DocumentTemplate)
class DocumentTemplateAdmin(admin.ModelAdmin):
    list_display = ('title', 'owner', 'status', 'version', 'category', 'department', 'is_shared', 'created_at')
    list_filter = ('status', 'is_shared', 'category', 'department')
    search_fields = ('title', 'description', 'owner__username', 'tags')

# [Web] `TemplateVersionAdmin` gom một cụm xử lý backend dùng chung cho nhóm màn Mẫu văn bản.

# vd: trang admin hiển thị/lọc các bản ghi của model này.
@admin.register(TemplateVersion)
class TemplateVersionAdmin(admin.ModelAdmin):
    list_display = ('template', 'version_number', 'created_by', 'created_at')
    list_filter = ('template',)

# [Web] `TemplatePermissionAdmin` gom một cụm xử lý backend dùng chung cho nhóm màn Mẫu văn bản.

# vd: trang admin hiển thị/lọc các bản ghi của model này.
@admin.register(TemplatePermission)
class TemplatePermissionAdmin(admin.ModelAdmin):
    list_display = ('template', 'user', 'can_view', 'can_edit', 'can_use', 'can_approve')
    list_filter = ('can_view', 'can_edit', 'can_use', 'can_approve')

# [Web] `TemplateApprovalLogAdmin` gom một cụm xử lý backend dùng chung cho nhóm màn Mẫu văn bản.

# vd: trang admin hiển thị/lọc các bản ghi của model này.
@admin.register(TemplateApprovalLog)
class TemplateApprovalLogAdmin(admin.ModelAdmin):
    list_display = ('template', 'action', 'actor', 'created_at')
    list_filter = ('action',)

# [Web] `TemplateAudienceMemberAdmin` gom một cụm xử lý backend dùng chung cho nhóm màn Mẫu văn bản.

# vd: trang admin hiển thị/lọc các bản ghi của model này.
@admin.register(TemplateAudienceMember)
class TemplateAudienceMemberAdmin(admin.ModelAdmin):
    list_display = ('template', 'user', 'created_at')
    search_fields = ('template__title', 'user__username', 'user__first_name', 'user__last_name')
