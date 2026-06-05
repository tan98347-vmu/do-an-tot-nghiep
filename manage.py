#!/usr/bin/env python
# Chức năng web liên quan: các chức năng quản trị và nghiệp vụ đang hiển thị trên web.
# Vai trò backend trong luồng: Tệp này chạy tác vụ nền hoặc lệnh vận hành cho nghiệp vụ backend đang phục vụ các chức năng web hiện hành; kết quả của nó thường làm mới hoặc sửa dữ liệu mà các màn web đang hiển thị chức năng nghiệp vụ hiện hành đang đọc.
# Đầu vào/đầu ra chính: Nhận tham số CLI, chạy job nền và cập nhật dữ liệu hoặc cấu hình mà các màn web sẽ đọc lại sau đó.
# Người dùng sẽ thấy trên web: Sau khi tác vụ chạy xong, dữ liệu nền mà các chức năng các chức năng quản trị và nghiệp vụ đang hiển thị trên web đang dùng sẽ được làm mới hoặc sửa về trạng thái đúng.

"""Django's command-line utility for administrative tasks."""
import os
import sys

# [Web] `main` hỗ trợ lệnh nền xử lý dữ liệu hoặc cấu hình phục vụ cho các màn web hiện hành.

def main():
    """Run administrative tasks."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'my_tennis_club.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)

if __name__ == '__main__':
    main()
