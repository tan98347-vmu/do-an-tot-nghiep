# Chức năng web liên quan: Tạo mẫu văn bản, Mẫu dùng chung, Mẫu phòng ban của tôi, Mẫu riêng của tôi, Mẫu yêu thích và Tất cả mẫu (Admin).
# Vai trò backend trong luồng: Tệp này gắn hook khởi tạo hoặc side effect nền cho danh sách mẫu, chi tiết mẫu, form tạo mẫu, bulk upload và preview biến, bảo đảm các tab Mẫu dùng chung, Mẫu phòng ban, Mẫu riêng, Mẫu yêu thích, màn chi tiết mẫu, form tạo mẫu và bulk upload nhìn thấy trạng thái nhất quán mà không cần endpoint nào xử lý bù.
# Đầu vào/đầu ra chính: Lắng nghe quá trình khởi động hoặc thay đổi model để gắn thêm bước đồng bộ nền mà endpoint không trực tiếp xử lý.
# Người dùng sẽ thấy trên web: Người dùng sẽ thấy dữ liệu, badge trạng thái, quyền nút và thông báo trên các chức năng Tạo mẫu văn bản, Mẫu dùng chung, Mẫu phòng ban của tôi, Mẫu riêng của tôi, Mẫu yêu thích và Tất cả mẫu (Admin) thay đổi đúng theo kết quả nghiệp vụ.

from django.apps import AppConfig

# [Web] `DocumentTemplatesConfig` gom một cụm xử lý backend dùng chung cho nhóm màn Mẫu văn bản.

# vd: gom các thuộc tính/method liên quan vào một nơi.
class DocumentTemplatesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'document_templates'
    verbose_name = 'Mẫu Văn Bản'
