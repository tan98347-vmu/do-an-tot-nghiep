# Chức năng web liên quan: Cấu hình AI.
# Vai trò backend trong luồng: Tệp này đăng ký Prompt và PromptCategory vào Django admin
# để quản trị viên xem/sửa/lọc prompt và danh mục trực tiếp trong trang admin.

from django.contrib import admin
from .models import Prompt, PromptCategory

# class PromptCategoryAdmin cấu hình trang admin cho PromptCategory: hiển thị tên/mô tả/ngày tạo và cho tìm theo tên.
# vd: vào /django-admin/ -> mục Danh mục prompt -> tìm 'Pháp chế' để xem/sửa danh mục.
@admin.register(PromptCategory)
class PromptCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'created_at')
    search_fields = ('name',)

# class PromptAdmin cấu hình trang admin cho Prompt: hiển thị tiêu đề/chủ sở hữu/danh mục/chia sẻ/ngày tạo, lọc theo is_shared + danh mục, tìm theo tiêu đề/owner/tags.
# vd: admin lọc các prompt is_shared=True của một danh mục để rà soát nội dung dùng chung.
@admin.register(Prompt)
class PromptAdmin(admin.ModelAdmin):
    list_display = ('title', 'owner', 'category', 'is_shared', 'created_at')
    list_filter = ('is_shared', 'category')
    search_fields = ('title', 'owner__username', 'tags')
