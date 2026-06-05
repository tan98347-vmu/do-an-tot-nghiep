# Chức năng web liên quan: Hồ sơ cá nhân và Tài khoản, phòng ban và nhóm.
# Vai trò backend trong luồng: Tệp này giữ phần logic backend dùng chung cho hồ sơ cá nhân, tài khoản, phòng ban, nhóm và phân quyền truy cập, để các flow ở màn Hồ sơ cá nhân, màn đăng nhập/đăng ký và các dialog quản trị tài khoản, phòng ban, nhóm không phải lặp lại cùng một rule ở nhiều nơi.
# Đầu vào/đầu ra chính: Giữ các helper, cấu hình và rule backend dùng lại ở nhiều flow khác nhau.
# Người dùng sẽ thấy trên web: Người dùng sẽ thấy dữ liệu, badge trạng thái, quyền nút và thông báo trên các chức năng Hồ sơ cá nhân và Tài khoản, phòng ban và nhóm thay đổi đúng theo kết quả nghiệp vụ.

from django.contrib import admin
from .models import Department, DepartmentMembership, GlobalAIConfig, UserProfile

# [Web] `UserProfileAdmin` gom một cụm xử lý backend dùng chung cho nhóm màn Hồ sơ, tài khoản và quản trị người dùng.

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'bio')
    search_fields = ('user__username', 'user__email')

# [Web] `DepartmentAdmin` gom một cụm xử lý backend dùng chung cho nhóm màn Hồ sơ, tài khoản và quản trị người dùng.

@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'manager', 'created_at')
    search_fields = ('name', 'code')

# [Web] `DepartmentMembershipAdmin` gom một cụm xử lý backend dùng chung cho nhóm màn Hồ sơ, tài khoản và quản trị người dùng.

@admin.register(DepartmentMembership)
class DepartmentMembershipAdmin(admin.ModelAdmin):
    list_display = ('department', 'user', 'is_active', 'joined_at')
    list_filter = ('department', 'is_active')
    search_fields = ('department__name', 'department__code', 'user__username', 'user__first_name', 'user__last_name')

# [Web] `GlobalAIConfigAdmin` gom một cụm xử lý backend dùng chung cho nhóm màn Hồ sơ, tài khoản và quản trị người dùng.

@admin.register(GlobalAIConfig)
class GlobalAIConfigAdmin(admin.ModelAdmin):
    list_display = (
        'ai_model',
        'ocr_model',
        'image_ocr_model',
        'ai_temperature',
        'ai_max_results',
        'ai_internet_results',
        'ai_search_engine',
        'embedding_model',
        'updated_by',
        'updated_at',
    )
