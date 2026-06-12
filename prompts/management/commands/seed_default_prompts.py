from django.core.management.base import BaseCommand

from accounts.models import CompanyStatus, CompanyUserMembership
from prompts.models import PROMPT_STATUS_APPROVED, Prompt


DEFAULT_PROMPTS = (
    {
        'title': 'Template Fill - Cong van hanh chinh',
        'system_content': 'Ban la tro ly dien mau van ban hanh chinh noi bo mot cach chinh xac.',
        'rules_content': 'Chi dien vao cac bien co du lieu. Neu thieu du lieu, de chuoi rong va khong tu bo sung.',
        'usage_scope': ['template_fill'],
        'tags': 'seed:r1-default,scope:template_fill,style:formal',
    },
    {
        'title': 'Template Fill - Van ban an toan du lieu thieu',
        'system_content': 'Ban la tro ly dien mau uu tien tinh an toan va nhat quan.',
        'rules_content': 'Khong suy doan thong tin con thieu. Giu nguyen cau truc mau va uu tien tinh ngan gon.',
        'usage_scope': ['template_fill'],
        'tags': 'seed:r1-default,scope:template_fill,style:safe',
    },
    {
        'title': 'Summary - Tom tat dieu hanh',
        'system_content': 'Ban la tro ly tom tat tai lieu cho lanh dao.',
        'rules_content': 'Rut ra y chinh, ket luan va hanh dong tiep theo trong van phong chuyen nghiep.',
        'usage_scope': ['summary'],
        'tags': 'seed:r1-default,scope:summary,style:executive',
    },
    {
        'title': 'Summary - Tom tat rui ro va viec can lam',
        'system_content': 'Ban la tro ly tong hop van ban theo huong quan tri rui ro.',
        'rules_content': 'Nham vao rui ro, van de con mo va danh sach viec can xu ly. Khong viet lan man.',
        'usage_scope': ['summary'],
        'tags': 'seed:r1-default,scope:summary,style:risk',
    },
    {
        'title': 'Word AI Edit - Chinh sua van phong',
        'system_content': 'Ban la tro ly chinh sua van ban cong viec de ro rang hon ma khong doi y.',
        'rules_content': 'Trau chuot cau chu, giu nguyen so lieu va ten rieng, khong them noi dung moi neu khong co yeu cau.',
        'usage_scope': ['word_ai_edit'],
        'tags': 'seed:r1-default,scope:word_ai_edit,style:polish',
    },
    {
        'title': 'Word AI Edit - Viet lai cau truc ro rang',
        'system_content': 'Ban la tro ly viet lai van ban theo huong de doc, de duyet va co cau truc hon.',
        'rules_content': 'Duoc phep tach doan, dat lai tieu de phu va rut gon cau dai, nhung phai giu dung nghia goc.',
        'usage_scope': ['word_ai_edit'],
        'tags': 'seed:r1-default,scope:word_ai_edit,style:rewrite',
    },
    {
        'title': 'Chat - Tro ly noi bo mac dinh',
        'system_content': 'Ban la tro ly AI noi bo cho nen tang quan ly van ban doanh nghiep.',
        'rules_content': (
            "- Dien day du tat ca variables cua mau da chon\n"
            "- Neu user chua cung cap du du lieu cho mot bien thi de chuoi rong ''\n"
            "- KHONG suy luan, KHONG bia, KHONG tu bu thong tin con thieu\n"
            "- Chon template phu hop nhat voi yeu cau, dua vao title + description + content_preview\n"
            "- Chi tra ve JSON thuan tuy, khong markdown, khong giai thich ben ngoai JSON"
        ),
        'usage_scope': ['chat'],
        'tags': 'seed:r1-default,scope:chat,seed:default-chat-primary',
    },
    {
        'title': 'Chat - Tro ly hoi dap tung buoc',
        'system_content': 'Ban la tro ly hoi dap noi bo, uu tien huong dan tung buoc de nguoi dung de lam theo.',
        'rules_content': 'Tra loi ngan gon, xac nhan ro khi thieu thong tin, va neu can thi dua ra cac buoc hanh dong tiep theo.',
        'usage_scope': ['chat'],
        'tags': 'seed:r1-default,scope:chat,style:guided',
    },
)


# class Command là lệnh quản trị 'seed_default_prompts': tạo sẵn bộ prompt mẫu (curated) theo từng scope cho mỗi công ty đang active.
# vd: python manage.py seed_default_prompts -> tạo các prompt 'Template Fill...', 'Summary...', 'Word AI Edit...'.
class Command(BaseCommand):
    help = 'Seed prompt mac dinh cho cac scope template_fill, summary, word_ai_edit, chat.'

    # def handle duyệt từng công ty active (qua một owner đại diện) và update_or_create các prompt mẫu trong DEFAULT_PROMPTS (đặt approved/public/curated); in số tạo mới/cập nhật.
    # vd: công ty A -> tạo/cập nhật các prompt seed gắn owner đại diện của A.
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

        for company_id, owner in owners_by_company.items():
            for definition in DEFAULT_PROMPTS:
                prompt, created = Prompt.objects.update_or_create(
                    owner=owner,
                    title=definition['title'],
                    defaults={
                        'system_content': definition['system_content'],
                        'rules_content': definition['rules_content'],
                        'tags': definition['tags'],
                        'visibility': Prompt.VISIBILITY_PUBLIC,
                        'status': PROMPT_STATUS_APPROVED,
                        'source': Prompt.SOURCE_CURATED,
                        'usage_scope': list(definition['usage_scope']),
                    },
                )
                if created:
                    created_count += 1
                else:
                    updated_count += 1

            self.stdout.write(
                self.style.SUCCESS(
                    f'Seeded default prompts for company #{company_id} via user {owner.username}.'
                )
            )

        if not owners_by_company:
            self.stdout.write(
                self.style.WARNING(
                    'Khong tim thay company membership nao de seed default prompts.'
                )
            )

        self.stdout.write(
            self.style.SUCCESS(
                f'Hoan tat seed default prompts. created={created_count} updated={updated_count}'
            )
        )
