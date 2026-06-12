# Chức năng web liên quan: Sao lưu dữ liệu.
# Vai trò backend trong luồng: Tệp này chạy tác vụ nền hoặc lệnh vận hành cho sao lưu dữ liệu, dọn dữ liệu và vận hành hệ thống; kết quả của nó thường làm mới hoặc sửa dữ liệu mà màn Sao lưu dữ liệu, danh sách file backup và các thao tác tạo, tải, xóa backup đang đọc.
# Đầu vào/đầu ra chính: Nhận tham số CLI, chạy job nền và cập nhật dữ liệu hoặc cấu hình mà các màn web sẽ đọc lại sau đó.
# Người dùng sẽ thấy trên web: Sau khi tác vụ chạy xong, dữ liệu nền mà các chức năng Sao lưu dữ liệu đang dùng sẽ được làm mới hoặc sửa về trạng thái đúng.

"""
Management command: reset_db
Xoa toan bo du lieu tru admin, tao/cap nhat tai khoan admin.

BAO MAT: truoc day lenh nay hard-code mat khau 'admin123' (default credentials).
Nay mat khau lay tu env RESET_DB_ADMIN_PASSWORD; neu khong dat se SINH NGAU NHIEN
va in ra mot lan duy nhat. Lenh tu choi chay khi DEBUG=False (moi truong that)
tru khi truyen --force, de tranh vo tinh reset DB production.
"""
import os
import secrets

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User

# [Web] `Command` gom tác vụ vận hành nền làm mới dữ liệu hoặc cấu hình mà các màn web đang dựa vào.

class Command(BaseCommand):
    help = 'Reset DB: delete all data except admin, recreate the admin account (password from env or random)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Cho phep chay ngay ca khi DEBUG=False (moi truong production).',
        )

    # [Web] `handle` là điểm chạy chính của lệnh nền này; admin dùng nó để sửa dữ liệu ngoài giao diện web.

    def handle(self, *args, **options):
        if not settings.DEBUG and not options.get('force'):
            raise CommandError(
                'reset_db bi chan khi DEBUG=False. Day la lenh xoa toan bo du lieu. '
                'Neu thuc su muon chay tren moi truong nay, them co --force.'
            )
        self.stdout.write('Starting DB reset...')

        # 1. AI engine data
        self._delete('ai_engine', 'ChatMessage')
        self._delete('ai_engine', 'ChatSession')
        self._delete('ai_engine', 'KnowledgeBase')

        # 2. Documents & templates
        self._delete('documents', 'Document')
        self._delete('document_templates', 'TemplateVersion')
        self._delete('document_templates', 'TemplatePermission')
        self._delete('document_templates', 'TemplateApprovalLog')
        self._delete('document_templates', 'DocumentTemplate')

        # 3. Configs
        self._delete('documents', 'DocumentNumberConfig')
        self._delete('document_templates', 'TemplateCategory')
        self._delete('accounts', 'Department')

        # 4. Groups
        self._delete('accounts', 'UserGroupMembership')
        self._delete('accounts', 'UserGroup')

        # 5. Profiles & non-admin users
        self._delete('accounts', 'UserProfile')
        deleted_count, _ = User.objects.exclude(username='admin').delete()
        self.stdout.write(f'  Deleted {deleted_count} users (kept admin)')

        # 6. Create/update admin
        raw_password = os.getenv('RESET_DB_ADMIN_PASSWORD', '').strip()
        generated = False
        if not raw_password:
            raw_password = secrets.token_urlsafe(18)
            generated = True
        admin, created = User.objects.get_or_create(username='admin')
        admin.set_password(raw_password)
        admin.is_superuser = True
        admin.is_staff = True
        admin.is_active = True
        admin.email = 'admin@example.com'
        admin.first_name = 'Admin'
        admin.last_name = ''
        admin.save()
        action = 'Created' if created else 'Updated'
        if generated:
            self.stdout.write(self.style.WARNING(
                f'  {action} admin -> username=admin, password (sinh ngau nhien, luu lai ngay): {raw_password}'
            ))
        else:
            self.stdout.write(f'  {action} admin -> username=admin (mat khau lay tu RESET_DB_ADMIN_PASSWORD)')

        self.stdout.write(self.style.SUCCESS('DB reset complete!'))

    # [Web] `_delete` là bước nội bộ của class để hỗ trợ dữ liệu hoặc trạng thái mà màn Sao lưu dữ liệu đang cần.

    def _delete(self, app_label, model_name):
        from django.apps import apps
        try:
            Model = apps.get_model(app_label, model_name)
            count, _ = Model.objects.all().delete()
            self.stdout.write(f'  Deleted {count} {model_name}')
        except LookupError:
            self.stdout.write(f'  [skip] {app_label}.{model_name} not found')
        except Exception as e:
            self.stdout.write(f'  [error] {app_label}.{model_name}: {e}')
