# Chức năng web liên quan: Cấu hình AI.
# Vai trò backend trong luồng: Tệp này giữ phần logic backend dùng chung cho cấu hình AI, prompt và ngữ cảnh dùng chung cho web, để các flow ở màn Cấu hình AI, các form chỉnh model/context và những luồng AI đọc cấu hình này không phải lặp lại cùng một rule ở nhiều nơi.
# Đầu vào/đầu ra chính: Giữ các helper, cấu hình và rule backend dùng lại ở nhiều flow khác nhau.
# Người dùng sẽ thấy trên web: Người dùng sẽ thấy dữ liệu, badge trạng thái, quyền nút và thông báo trên các chức năng Cấu hình AI thay đổi đúng theo kết quả nghiệp vụ.

from django.contrib import admin
from .models import Prompt, PromptCategory

# [Web] `PromptCategoryAdmin` gom một cụm xử lý backend dùng chung cho màn Cấu hình AI.

@admin.register(PromptCategory)
class PromptCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'created_at')
    search_fields = ('name',)

# [Web] `PromptAdmin` gom một cụm xử lý backend dùng chung cho màn Cấu hình AI.

@admin.register(Prompt)
class PromptAdmin(admin.ModelAdmin):
    list_display = ('title', 'owner', 'category', 'is_shared', 'created_at')
    list_filter = ('is_shared', 'category')
    search_fields = ('title', 'owner__username', 'tags')
