# Chức năng web liên quan: Thùng rác.
# Vai trò backend trong luồng: Tệp này chạy tác vụ nền hoặc lệnh vận hành cho thùng rác, khôi phục và xóa vĩnh viễn dữ liệu; kết quả của nó thường làm mới hoặc sửa dữ liệu mà màn Thùng rác, danh sách bản ghi đã xóa và các nút khôi phục hoặc xóa vĩnh viễn đang đọc.
# Đầu vào/đầu ra chính: Nhận tham số CLI, chạy job nền và cập nhật dữ liệu hoặc cấu hình mà các màn web sẽ đọc lại sau đó.
# Người dùng sẽ thấy trên web: Sau khi tác vụ chạy xong, dữ liệu nền mà các chức năng Thùng rác đang dùng sẽ được làm mới hoặc sửa về trạng thái đúng.

from django.core.management.base import BaseCommand

from api.trash_services import purge_expired_trash

# [Web] `Command` gom tác vụ vận hành nền làm mới dữ liệu hoặc cấu hình mà các màn web đang dựa vào.

class Command(BaseCommand):
    help = 'Purge expired soft-deleted templates, documents, and chat sessions.'

    # [Web] `handle` là điểm chạy chính của lệnh nền này; admin dùng nó để sửa dữ liệu ngoài giao diện web.

    def handle(self, *args, **options):
        payload = purge_expired_trash()
        total = sum(payload.values())
        self.stdout.write(
            self.style.SUCCESS(
                f'Purged {total} expired trash items: {payload}'
            )
        )
