from django.core.management.base import BaseCommand
'''
ai_engine/management/commands/seed_compliance_prompts.py:1 là một Django management command dùng để tạo sẵn các prompt mẫu phục vụ chức năng kiểm tra
  tuân thủ văn bản.

  Chạy bằng lệnh:

  python manage.py seed_compliance_prompts

  ## Nó tạo những prompt nào?

  File định nghĩa ba prompt:

  1. Compliance - Hanh chinh co ban
      - Kiểm tra tiêu đề.
      - Số hiệu.
      - Ngày tháng.
      - Nội dung.
      - Cấu trúc và thành phần bắt buộc.

  2. Compliance - Quy trinh noi bo
      - Kiểm tra vai trò và trách nhiệm.
      - Mốc thời gian.
      - Điều kiện kích hoạt.
      - Các bước phê duyệt.

  3. Compliance - Mau van ban phap che
      - Kiểm tra căn cứ.
      - Phạm vi áp dụng.
      - Nghĩa vụ.
      - Ngoại lệ.
      - Hiệu lực.
      - Cơ chế theo dõi.

  Các prompt này sau đó được ComplianceChecker dùng làm bộ yêu cầu để đối chiếu với nội dung văn bản hoặc mẫu.
 ## Người dùng tương tác thế nào?

  Trên UI, người dùng:

  1. Chọn đối tượng cần kiểm tra:
      - Một Document.
      - Hoặc một DocumentTemplate.

  2. Chọn prompt có scope compliance_check.
  3. Bấm Kiểm tra.
  4. Xem kết quả đạt/không đạt.
  5. Xem các yêu cầu còn thiếu.
  6. Xem lịch sử 10 lần kiểm tra gần nhất.


'''
from accounts.models import CompanyStatus, CompanyUserMembership
from prompts.models import PROMPT_STATUS_APPROVED, Prompt

_PROMPT_DEFINITIONS = [
    {
        'title': 'Compliance - Hanh chinh co ban',
        'system_content': (
            'Ban la tro ly danh gia muc do tuan thu cua van ban hanh chinh. '
            'Chi duoc danh gia theo cac yeu cau duoc cung cap.'
        ),
        'rules_content': (
            'Kiem tra tieu de, so hieu, ngay thang, noi dung, co cau muc va '
            'cac thanh phan bat buoc. Neu thieu, neu ro muc thieu va vi sao.'
        ),
    },
    {
        'title': 'Compliance - Quy trinh noi bo',
        'system_content': (
            'Ban la tro ly kiem tra van ban theo quy trinh noi bo cua doanh nghiep.'
        ),
        'rules_content': (
            'Doi chieu vai tro, trach nhiem, moc thoi gian, dieu kien kich hoat '
            'va buoc phe duyet. Chi ra cac muc chua dap ung.'
        ),
    },
    {
        'title': 'Compliance - Mau van ban phap che',
        'system_content': (
            'Ban la tro ly ra soat van ban phap che noi bo theo checklist quy dinh.'
        ),
        'rules_content': (
            'Tap trung vao can cu, pham vi ap dung, dieu khoan nghia vu, '
            'ngoai le, hieu luc va co che theo doi. Neu dat, xac nhan dat.'
        ),
    },
]


# class Command là lệnh quản trị 'seed_compliance_prompts' để tạo sẵn các prompt mẫu cho scope compliance_check cho từng công ty.
# vd: python manage.py seed_compliance_prompts -> tạo prompt compliance mẫu cho mọi công ty đang active.
class Command(BaseCommand):
    help = 'Seed prompt mau cho scope compliance_check.'

    # def handle để duyệt từng công ty đang hoạt động, chọn một owner đại diện rồi update_or_create các prompt compliance mẫu (đặt public, đã duyệt); in số lượng tạo mới/cập nhật/bỏ qua.
    # vd: công ty A chưa có prompt -> tạo mới; đã có -> cập nhật; in created/updated/skipped.
    def handle(self, *args, **options):
        memberships = (
            CompanyUserMembership.objects
            .select_related('user', 'company')
            .filter(
                is_active=True,
                user__is_active=True,
                company__status=CompanyStatus.ACTIVE,
            )
            .order_by('company_id', 'role', 'user_id')
        )

        owners_by_company = {}
        for membership in memberships:
            owners_by_company.setdefault(membership.company_id, membership.user)

        created_count = 0
        updated_count = 0
        skipped_companies = 0

        for company_id, owner in owners_by_company.items():
            for definition in _PROMPT_DEFINITIONS:
                prompt, created = Prompt.objects.update_or_create(
                    owner=owner,
                    title=definition['title'],
                    defaults={
                        'system_content': definition['system_content'],
                        'rules_content': definition['rules_content'],
                        'tags': 'scope:compliance_check,seed:compliance',
                        'visibility': Prompt.VISIBILITY_PUBLIC,
                        'status': PROMPT_STATUS_APPROVED,
                        'source': Prompt.SOURCE_CURATED,
                    },
                )
                if created:
                    created_count += 1
                else:
                    updated_count += 1
            self.stdout.write(
                self.style.SUCCESS(
                    f'Seeded compliance prompts for company #{company_id} via user {owner.username}.'
                )
            )

        if not owners_by_company:
            skipped_companies = 1
            self.stdout.write(
                self.style.WARNING(
                    'Khong tim thay company membership nao de seed prompt compliance.'
                )
            )

        self.stdout.write(
            self.style.SUCCESS(
                f'Hoan tat seed compliance prompts. created={created_count} updated={updated_count} skipped={skipped_companies}'
            )
        )
