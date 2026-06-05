# Chức năng web liên quan: Văn bản của tôi, Văn bản chia sẻ trong nhóm, Văn bản chia sẻ công khai, Văn bản yêu thích, Văn bản đã lưu trữ, Tất cả văn bản (Admin), Hòm thư và Yêu cầu phê duyệt.
# Vai trò backend trong luồng: Tệp này gắn hook khởi tạo hoặc side effect nền cho danh sách văn bản, chi tiết văn bản, version, preview, chia sẻ, ký số và hòm thư, bảo đảm các tab danh sách văn bản, màn chi tiết văn bản, preview hoặc tải file, lịch sử version, vùng khởi động ký số và màn Hòm thư nhìn thấy trạng thái nhất quán mà không cần endpoint nào xử lý bù.
# Đầu vào/đầu ra chính: Lắng nghe quá trình khởi động hoặc thay đổi model để gắn thêm bước đồng bộ nền mà endpoint không trực tiếp xử lý.
# Người dùng sẽ thấy trên web: Người dùng sẽ thấy dữ liệu, badge trạng thái, quyền nút và thông báo trên các chức năng Văn bản của tôi, Văn bản chia sẻ trong nhóm, Văn bản chia sẻ công khai, Văn bản yêu thích, Văn bản đã lưu trữ, Tất cả văn bản (Admin), Hòm thư và Yêu cầu phê duyệt thay đổi đúng theo kết quả nghiệp vụ.

from django.apps import AppConfig

# [Web] `DocumentsConfig` gom một cụm xử lý backend dùng chung cho nhóm màn Văn bản và Hòm thư.

class DocumentsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'documents'
    verbose_name = 'Van Ban'

    # [Web] `ready` là bước nội bộ của class để hỗ trợ dữ liệu hoặc trạng thái mà nhóm màn Văn bản và Hòm thư đang cần.

    def ready(self):
        from . import signals  # noqa: F401
