'''
  ## Vai Trò

  models.py định nghĩa dữ liệu:

  UserProfile
  Department
  DepartmentMembership
  GlobalAIConfig

  Còn admin.py quyết định:

  - Model nào xuất hiện trong Django Admin.
  - Danh sách hiển thị những cột nào.
  - Có thể tìm kiếm bằng trường nào.
  - Có thể lọc theo trường nào.

  Nó không tạo API cho Flutter và không thay đổi cấu trúc database.
'''

from django.contrib import admin
from .models import Department, DepartmentMembership, GlobalAIConfig, UserProfile

# [Web] `UserProfileAdmin` gom một cụm xử lý backend dùng chung cho nhóm màn Hồ sơ, tài khoản và quản trị người dùng.
# @admin.register(UserProfile) để đăng ký model UserProfile với Django Admin, cho phép quản trị viên quản lý các hồ sơ người dùng thông qua giao diện quản trị của Django. Điều này giúp dễ dàng xem, chỉnh sửa và tìm kiếm thông tin hồ sơ người dùng trong hệ thống.
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
