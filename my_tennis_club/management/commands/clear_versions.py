# Chức năng web liên quan: các chức năng quản trị và nghiệp vụ đang hiển thị trên web.
# Vai trò backend trong luồng: Tệp này chạy tác vụ nền hoặc lệnh vận hành cho nghiệp vụ backend đang phục vụ các chức năng web hiện hành; kết quả của nó thường làm mới hoặc sửa dữ liệu mà các màn web đang hiển thị chức năng nghiệp vụ hiện hành đang đọc.
# Đầu vào/đầu ra chính: Nhận tham số CLI, chạy job nền và cập nhật dữ liệu hoặc cấu hình mà các màn web sẽ đọc lại sau đó.
# Người dùng sẽ thấy trên web: Sau khi tác vụ chạy xong, dữ liệu nền mà các chức năng các chức năng quản trị và nghiệp vụ đang hiển thị trên web đang dùng sẽ được làm mới hoặc sửa về trạng thái đúng.

from django.core.management.base import BaseCommand
from document_templates.models import TemplateVersion, DocumentTemplate

# [Web] `Command` gom tác vụ vận hành nền làm mới dữ liệu hoặc cấu hình mà các màn web đang dựa vào.

class Command(BaseCommand):
    help = 'Xóa tất cả TemplateVersion (snapshot cũ) khỏi DB, giữ nguyên DocumentTemplate'

    # [Web] `handle` là điểm chạy chính của lệnh nền này; admin dùng nó để sửa dữ liệu ngoài giao diện web.

    def handle(self, *args, **options):
        count = TemplateVersion.objects.count()
        TemplateVersion.objects.all().delete()

        # Reset version của mọi template về 1.0 để bắt đầu lại sạch
        updated = DocumentTemplate.objects.update(version='1.0')

        self.stdout.write(self.style.SUCCESS(
            f'Deleted {count} TemplateVersion records. '
            f'Reset version=1.0 on {updated} templates.'
        ))
