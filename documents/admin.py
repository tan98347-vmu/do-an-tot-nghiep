# Chức năng web liên quan: Văn bản của tôi, Văn bản chia sẻ trong nhóm, Văn bản chia sẻ công khai, Văn bản yêu thích, Văn bản đã lưu trữ, Tất cả văn bản (Admin), Hòm thư và Yêu cầu phê duyệt.
# Vai trò backend trong luồng: Tệp này giữ phần logic backend dùng chung cho danh sách văn bản, chi tiết văn bản, version, preview, chia sẻ, ký số và hòm thư, để các flow ở các tab danh sách văn bản, màn chi tiết văn bản, preview hoặc tải file, lịch sử version, vùng khởi động ký số và màn Hòm thư không phải lặp lại cùng một rule ở nhiều nơi.
# Đầu vào/đầu ra chính: Giữ các helper, cấu hình và rule backend dùng lại ở nhiều flow khác nhau.
# Người dùng sẽ thấy trên web: Người dùng sẽ thấy dữ liệu, badge trạng thái, quyền nút và thông báo trên các chức năng Văn bản của tôi, Văn bản chia sẻ trong nhóm, Văn bản chia sẻ công khai, Văn bản yêu thích, Văn bản đã lưu trữ, Tất cả văn bản (Admin), Hòm thư và Yêu cầu phê duyệt thay đổi đúng theo kết quả nghiệp vụ.

from django.contrib import admin
from .models import Document, DocumentNumberConfig

# [Web] `DocumentAdmin` gom một cụm xử lý backend dùng chung cho nhóm màn Văn bản và Hòm thư.

@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ('title', 'doc_number', 'owner', 'status', 'department', 'category', 'template', 'created_at')
    search_fields = ('title', 'doc_number', 'owner__username', 'tags')
    list_filter = ('status', 'is_archived', 'department', 'category', 'template')

# [Web] `DocumentNumberConfigAdmin` gom một cụm xử lý backend dùng chung cho nhóm màn Văn bản và Hòm thư.

@admin.register(DocumentNumberConfig)
class DocumentNumberConfigAdmin(admin.ModelAdmin):
    list_display = ('department', 'prefix', 'year', 'last_number', 'category')
    list_filter = ('department', 'year')
