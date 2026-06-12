'''
  Cụ thể, accounts đảm nhiệm:

  - Quản lý công ty và vòng đời công ty.
  - Quản lý tài khoản cùng hồ sơ nhân viên.
  - Phân biệt Platform Admin, Company Admin và Company User.
  - Quản lý phòng ban, nhóm và trưởng nhóm.
  - Xác thực đăng nhập bằng username, email hoặc mã nhân viên.
  - Cô lập dữ liệu và file giữa các công ty.
  - Quản lý cấu hình AI theo từng công ty.
  - Cung cấp thông tin nhân viên làm ngữ cảnh cho AI.
  - Tìm người nhận theo tên, bí danh hoặc mã nhân viên.
  - Cung cấp lớp tương thích phân quyền cho document, template và prompt.
'''
'''
File accounts/models.py có trọng trách định nghĩa cấu trúc dữ liệu cốt lõi cho tài khoản, công ty và tổ chức trong database.
  Nó trả lời câu hỏi:
  > Hệ thống cần lưu những dữ liệu gì về công ty, người dùng và mối quan hệ giữa chúng?
'''


from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import models
from django.db.utils import DatabaseError, OperationalError, ProgrammingError
from django.utils.text import slugify

from .identity_normalization import normalize_lookup_value
from .storage_paths import company_media_path


def _avatar_upload(instance, filename):
    return company_media_path(
        company=getattr(instance, 'company', None),
        section='avatars',
        filename=filename,
    )


class CompanyStatus(models.TextChoices):
    DRAFT = 'draft', 'Draft'
    ACTIVE = 'active', 'Active'
    LOCKED = 'locked', 'Locked'
    ARCHIVED = 'archived', 'Archived'
    DELETED = 'deleted', 'Deleted'


class Company(models.Model):
    code = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(max_length=80, unique=True, blank=True)
    name = models.CharField(max_length=255)
    status = models.CharField(
        max_length=16,
        choices=CompanyStatus.choices,
        default=CompanyStatus.DRAFT,
    )
    description = models.TextField(blank=True)
    industry = models.CharField(max_length=255, blank=True)
    address = models.CharField(max_length=255, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=50, blank=True)
    website = models.URLField(blank=True)
    company_context = models.TextField(blank=True)
    created_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='created_companies',
    )
    updated_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='updated_companies',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
# class Meta để đảm bảo rằng các công ty được sắp xếp theo tên và mã khi truy vấn, giúp dễ dàng tìm kiếm và hiển thị danh sách công ty một cách có tổ chức.
    class Meta:
        ordering = ['name', 'code']
# def __str__ để trả về một chuỗi đại diện cho đối tượng công ty, bao gồm mã và tên của công ty, giúp dễ dàng nhận biết khi làm việc với các đối tượng công ty trong Django admin hoặc khi in ra console.
    def __str__(self):
        return f'{self.code} - {self.name}'
# def save để tự động tạo slug dựa trên mã hoặc tên của công ty nếu slug chưa được cung cấp, đồng thời đảm bảo rằng slug là duy nhất trong cơ sở dữ liệu bằng cách thêm hậu tố nếu cần thiết.
#  Trong hệ thống này, slug chủ yếu dùng để tạo đường dẫn lưu file riêng cho công ty vd: companies/cong-ty-hoang-gia/avatars/avatar.png: ,  
    '''
    Chỉ tự tạo slug nếu slug chưa có.

  Điều này có nghĩa:

  - Tạo công ty mới chưa nhập slug: tự sinh.
  - Công ty đã có slug: giữ nguyên.
  - Đổi tên hoặc mã công ty: slug cũ không tự thay đổi.

  ## Ví Dụ Hoạt Động

  Giả sử tạo ba công ty có cùng mã:

  Company.objects.create(code="ABC", name="Công ty ABC")
  Company.objects.create(code="ABC-2", name="Công ty khác")

  Nó được sử dụng bởi:

  - storage_paths.py: tạo đường dẫn file.
  - runtime_guard.py: kiểm tra file có thuộc đúng công ty.
  - company_lifecycle_services.py: tìm thư mục cần xóa khi xóa cứng công ty.

    '''

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.code or self.name)[:70] or 'company'
            slug = base_slug
            counter = 1
            while Company.objects.exclude(pk=self.pk).filter(slug=slug).exists():
                suffix = f'-{counter}'
                slug = f'{base_slug[: max(1, 70 - len(suffix))]}{suffix}'
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

# get_default để lấy hoặc tạo một công ty mặc định với mã 'default-company'. Điều này hữu ích để đảm bảo rằng luôn có một công ty mặc định trong hệ thống, đặc biệt khi cần liên kết dữ liệu với một công ty nhưng không có công ty cụ thể nào được chỉ định.
# @classmethod cho phép gọi phương thức này trực tiếp từ lớp mà không cần phải tạo một instance của lớp đó trước. Khi gọi Company.get_default(), nó sẽ trả về một instance của Company với mã 'default-company', nếu chưa tồn tại thì sẽ được tạo mới với tên 'Default Company' và trạng thái ACTIVE.

    @classmethod
    def get_default(cls):
        obj, _ = cls.objects.get_or_create(
            code='default-company',
            defaults={
                'name': 'Default Company',
                'status': CompanyStatus.ACTIVE,
                'slug': 'default-company',
            },
        )
        return obj

#@property là một decorator cho phép định nghĩa một phương thức như một thuộc tính. Trong trường hợp này, is_login_enabled sẽ trả về True nếu trạng thái của công ty là ACTIVE, ngược lại sẽ trả về False. Điều này giúp dễ dàng kiểm tra xem công ty có cho phép đăng nhập hay không chỉ bằng cách truy cập thuộc tính này mà không cần phải gọi nó như một phương thức.

    @property
    def is_login_enabled(self):
        return self.status == CompanyStatus.ACTIVE

# class Department đại diện cho một phòng ban trong công ty, với các trường như tên, mã, mô tả, quản lý và trạng thái hoạt động. Nó có liên kết đến công ty và người dùng quản lý phòng ban. Các ràng buộc duy nhất đảm bảo rằng mỗi phòng ban trong cùng một công ty phải có tên và mã riêng biệt.
class Department(models.Model):
    company = models.ForeignKey(
        Company,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name='departments',
    )
    name = models.CharField(max_length=100, verbose_name='Ten phong ban')
    code = models.CharField(max_length=20, verbose_name='Ma phong ban')
    description = models.TextField(blank=True, verbose_name='Mo ta')
    manager = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='managed_departments',
        verbose_name='Truong phong',
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
# class Meta để định nghĩa các thuộc tính meta cho model Department, bao gồm tên hiển thị, thứ tự sắp xếp và các ràng buộc duy nhất để đảm bảo rằng mỗi phòng ban trong cùng một công ty phải có tên và mã riêng biệt. Điều này giúp duy trì tính toàn vẹn của dữ liệu và tránh trùng lặp thông tin về phòng ban trong cùng một công ty.
    class Meta:
        verbose_name = 'Phong ban'
        verbose_name_plural = 'Phong ban'
        ordering = ['name']
        constraints = [
            models.UniqueConstraint(fields=['company', 'name'], name='uniq_department_company_name'),
            models.UniqueConstraint(fields=['company', 'code'], name='uniq_department_company_code'),
        ]
# def __str__ để trả về một chuỗi đại diện cho đối tượng phòng ban, bao gồm mã và tên của phòng ban, giúp dễ dàng nhận biết khi làm việc với các đối tượng phòng ban trong Django admin hoặc khi in ra console.
    def __str__(self):
        return f"{self.code} - {self.name}"

# class DepartmentMembership đại diện cho mối quan hệ giữa người dùng và phòng ban, cho biết người dùng nào là thành viên của phòng ban nào, trạng thái hoạt động của thành viên đó và thời điểm họ gia nhập phòng ban. Ràng buộc duy nhất đảm bảo rằng mỗi người dùng chỉ có thể là thành viên của một phòng ban cụ thể một lần, giúp duy trì tính toàn vẹn của dữ liệu về thành viên phòng ban.
class DepartmentMembership(models.Model):
    department = models.ForeignKey(
        Department,
        on_delete=models.CASCADE,
        related_name='memberships',
        verbose_name='Phong ban',
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='department_memberships',
        verbose_name='Nhan vien',
    )
    is_active = models.BooleanField(default=True, verbose_name='Dang hoat dong')
    joined_at = models.DateTimeField(auto_now_add=True)
# class Meta để định nghĩa các thuộc tính meta cho model DepartmentMembership, bao gồm tên hiển thị, thứ tự sắp xếp và ràng buộc duy nhất để đảm bảo rằng mỗi người dùng chỉ có thể là thành viên của một phòng ban cụ thể một lần. Điều này giúp duy trì tính toàn vẹn của dữ liệu về thành viên phòng ban và tránh trùng lặp thông tin về mối quan hệ giữa người dùng và phòng ban.
    class Meta:
        verbose_name = 'Thanh vien phong ban'
        verbose_name_plural = 'Thanh vien phong ban'
        unique_together = ('department', 'user')
        ordering = ['department__name', 'user__username']

    def __str__(self):
        return f'{self.user.username} -> {self.department.code}'

# class GlobalAIConfig đại diện cho cấu hình AI toàn cục của hệ thống, bao gồm các trường như mô hình AI, mô hình chat AI, mô hình OCR, nhiệt độ AI, số lượng kết quả tối đa và các cài đặt liên quan đến tìm kiếm trên Internet. Nó cũng có liên kết đến người dùng cập nhật cấu hình và thời điểm cập nhật. Phương thức get_config được sử dụng để lấy hoặc tạo một cấu hình mặc định nếu chưa tồn tại, giúp đảm bảo rằng luôn có một cấu hình AI toàn cục trong hệ thống.
class GlobalAIConfig(models.Model):
    ai_model = models.CharField(max_length=100, default='kimi-k2.6:cloud', verbose_name='Model AI')
    chat_ai_model = models.CharField(
        max_length=100,
        default='kimi-k2.6:cloud',
        verbose_name='Model Chat AI',
        help_text='Model dung rieng cho tinh nang Tro ly chat (text + voice). De trong de dung Model AI mac dinh.',
    )
    ocr_model = models.CharField(max_length=100, default='qwen3-vl:4b', verbose_name='Model OCR')
    image_ocr_model = models.CharField(max_length=100, default='qwen3-vl:235b-cloud', verbose_name='Model OCR anh')
    ai_temperature = models.FloatField(default=0.0, verbose_name='Temperature')
    ai_max_results = models.IntegerField(default=6, verbose_name='So ket qua toi da')
    embedding_model = models.CharField(max_length=100, default='mxbai-embed-large', verbose_name='Embedding Model')
    company_context = models.TextField(blank=True, verbose_name='Ngu canh cong ty')
    ai_internet_results = models.IntegerField(default=3, verbose_name='So ket qua Internet')
    ai_search_engine = models.CharField(max_length=20, default='thuvienphapluat', verbose_name='Search engine Internet')
    updated_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        verbose_name='Cap nhat boi',
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Cau hinh AI toan cuc'

    def __str__(self):
        return f'GlobalAIConfig [{self.ai_model}]'

    @classmethod
    def get_config(cls):
        try:
            obj, _ = cls.objects.get_or_create(pk=1)
            return obj
        except (ProgrammingError, OperationalError, DatabaseError):
            return cls(pk=1)

#class CompanyAIConfig đại diện cho cấu hình AI riêng của từng công ty, cho phép mỗi công ty có thể tùy chỉnh các cài đặt AI của mình dựa trên cấu hình toàn cục. Nó bao gồm các trường tương tự như GlobalAIConfig nhưng liên kết trực tiếp đến một công ty cụ thể. Phương thức seed_defaults được sử dụng để tạo hoặc cập nhật cấu hình AI cho một công ty dựa trên cấu hình toàn cục, giúp đảm bảo rằng mỗi công ty có một cấu hình AI mặc định khi được tạo ra hoặc khi ngữ cảnh công ty được cập nhật.
# class CompanyAIConfig có thể ghi đè các giá trị mặc định từ GlobalAIConfig để phù hợp với nhu cầu cụ thể của từng công ty, đồng thời vẫn giữ được khả năng cập nhật ngữ cảnh công ty khi có sự thay đổi trong thông tin công ty.
class CompanyAIConfig(models.Model):
    company = models.OneToOneField(
        Company,
        on_delete=models.CASCADE,
        related_name='ai_config',
    )
    ai_model = models.CharField(max_length=100, default='kimi-k2.6:cloud')
    chat_ai_model = models.CharField(max_length=100, default='kimi-k2.6:cloud')
    ocr_model = models.CharField(max_length=100, default='qwen3-vl:4b')
    image_ocr_model = models.CharField(max_length=100, default='qwen3-vl:235b-cloud')
    ai_temperature = models.FloatField(default=0.0)
    ai_max_results = models.IntegerField(default=6)
    embedding_model = models.CharField(max_length=100, default='mxbai-embed-large')
    company_context = models.TextField(blank=True)
    ai_internet_results = models.IntegerField(default=3)
    ai_search_engine = models.CharField(max_length=20, default='thuvienphapluat')
    updated_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='updated_company_ai_configs',
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['company__name']
# def __str__ để trả về một chuỗi đại diện cho đối tượng cấu hình AI của công ty, bao gồm mã của công ty và thông tin về cấu hình AI, giúp dễ dàng nhận biết khi làm việc với các đối tượng cấu hình AI trong Django admin hoặc khi in ra console.
    def __str__(self):
        return f'{self.company.code} AI config'
#@classmethod seed_defaults để tạo hoặc cập nhật cấu hình AI cho một công ty dựa trên cấu hình toàn cục, giúp đảm bảo rằng mỗi công ty có một cấu hình AI mặc định khi được tạo ra hoặc khi ngữ cảnh công ty được cập nhật. Nếu cấu hình đã tồn tại và ngữ cảnh công ty mới khác với ngữ cảnh hiện tại, nó sẽ cập nhật ngữ cảnh công ty và thông tin người cập nhật.
    @classmethod
    def seed_defaults(cls, company, *, actor=None):
        defaults = GlobalAIConfig.get_config()
        obj, created = cls.objects.get_or_create(
            company=company,
            defaults={
                'ai_model': defaults.ai_model,
                'chat_ai_model': defaults.chat_ai_model or defaults.ai_model,
                'ocr_model': defaults.ocr_model,
                'image_ocr_model': defaults.image_ocr_model,
                'ai_temperature': defaults.ai_temperature,
                'ai_max_results': defaults.ai_max_results,
                'embedding_model': defaults.embedding_model,
                'company_context': company.company_context or defaults.company_context,
                'ai_internet_results': defaults.ai_internet_results,
                'ai_search_engine': defaults.ai_search_engine,
                'updated_by': actor,
            },
        )
        if not created and company.company_context and obj.company_context != company.company_context:
            obj.company_context = company.company_context
            obj.updated_by = actor
            obj.save(update_fields=['company_context', 'updated_by', 'updated_at'])
        return obj

# class UserGroup đại diện cho một nhóm người dùng trong công ty, với các trường như tên nhóm, mô tả, người tạo và thời điểm tạo. Nó có liên kết đến công ty và người dùng tạo nhóm. Ràng buộc duy nhất đảm bảo rằng mỗi nhóm trong cùng một công ty phải có tên riêng biệt. Phương thức member_count trả về số lượng thành viên trong nhóm, trong khi phương thức get_leaders trả về danh sách người dùng là trưởng nhóm của nhóm đó.
class UserGroup(models.Model):
    company = models.ForeignKey(
        Company,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name='user_groups',
    )
    name = models.CharField(max_length=100, verbose_name='Ten nhom')
    description = models.TextField(blank=True, verbose_name='Mo ta')
    created_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='created_groups',
        verbose_name='Nguoi tao',
    )
    created_at = models.DateTimeField(auto_now_add=True)
# class Meta để định nghĩa các thuộc tính meta cho model UserGroup, bao gồm tên hiển thị, thứ tự sắp xếp và ràng buộc duy nhất để đảm bảo rằng mỗi nhóm trong cùng một công ty phải có tên riêng biệt. Điều này giúp duy trì tính toàn vẹn của dữ liệu về nhóm người dùng và tránh trùng lặp thông tin về nhóm trong cùng một công ty.
    class Meta:
        verbose_name = 'Nhom nguoi dung'
        verbose_name_plural = 'Nhom nguoi dung'
        ordering = ['name']
        constraints = [
            models.UniqueConstraint(fields=['company', 'name'], name='uniq_user_group_company_name'),
        ]

    def __str__(self):
        return self.name

    def member_count(self):
        return self.memberships.count()

    def get_leaders(self):
        return User.objects.filter(
            group_memberships__group=self,
            group_memberships__role=UserGroupMembership.ROLE_LEADER,
        )

# class UserGroupMembership đại diện cho mối quan hệ giữa người dùng và nhóm người dùng, cho biết người dùng nào là thành viên của nhóm nào, vai trò của họ trong nhóm (thành viên hoặc trưởng nhóm), trạng thái hoạt động của thành viên đó và thời điểm họ gia nhập nhóm. Ràng buộc duy nhất đảm bảo rằng mỗi người dùng chỉ có thể là thành viên của một nhóm cụ thể một lần, giúp duy trì tính toàn vẹn của dữ liệu về thành viên nhóm và tránh trùng lặp thông tin về mối quan hệ giữa người dùng và nhóm.
class UserGroupMembership(models.Model):
    ROLE_MEMBER = 'member'
    ROLE_LEADER = 'leader'
    ROLE_CHOICES = [
        (ROLE_MEMBER, 'Thanh vien'),
        (ROLE_LEADER, 'Truong nhom'),
    ]

    group = models.ForeignKey(UserGroup, related_name='memberships', on_delete=models.CASCADE)
    user = models.ForeignKey(User, related_name='group_memberships', on_delete=models.CASCADE)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default=ROLE_MEMBER)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Thanh vien nhom'
        verbose_name_plural = 'Thanh vien nhom'
        unique_together = ('group', 'user')

    def __str__(self):
        return f'{self.user.username} -> {self.group.name} ({self.get_role_display()})'

'''
 CompanyPosition không phải chức vụ trưởng nhóm hoặc trưởng phòng. Trong source hiện tại, nó là danh mục chức danh/chức vụ do từng công ty định nghĩa.

  class CompanyPosition(models.Model):
      company = models.ForeignKey(Company, ...)
      code = models.CharField(...)
      name = models.CharField(...)
      description = models.TextField(...)
      is_active = models.BooleanField(...)

  Ví dụ dữ liệu:

   Công ty      Mã     Tên chức danh
  ━━━━━━━━━━━  ━━━━━  ━━━━━━━━━━━━━━━━
   Công ty A    CV     Chuyên viên
  ───────────  ─────  ────────────────
   Công ty A    TP     Trưởng phòng
  ───────────  ─────  ────────────────
   Công ty A    GD     Giám đốc
  ───────────  ─────  ────────────────
   Công ty B    KT     Kế toán trưởng
'''
# class CompanyPosition đại diện cho một vị trí công việc trong công ty, với các trường như mã vị trí, tên, mô tả, trạng thái hoạt động và thời điểm tạo. Nó có liên kết đến công ty mà vị trí đó thuộc về. Ràng buộc duy nhất đảm bảo rằng mỗi vị trí trong cùng một công ty phải có mã và tên riêng biệt, giúp duy trì tính toàn vẹn của dữ liệu về vị trí công việc trong công ty.
class CompanyPosition(models.Model):
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name='positions',
    )
    code = models.CharField(max_length=50, blank=True)
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']
        constraints = [
            models.UniqueConstraint(fields=['company', 'code'], name='uniq_company_position_code'),
            models.UniqueConstraint(fields=['company', 'name'], name='uniq_company_position_name'),
        ]

    def __str__(self):
        return self.name

# class CompanyRole đại diện cho các vai trò có thể có của người dùng trong công ty, bao gồm vai trò quản trị viên công ty và vai trò người dùng công ty. Nó sử dụng TextChoices để định nghĩa các lựa chọn có thể có cho trường role trong model CompanyUserMembership, giúp đảm bảo rằng chỉ có các giá trị hợp lệ được lưu trữ trong cơ sở dữ liệu.
class CompanyRole(models.TextChoices):
    COMPANY_ADMIN = 'company_admin', 'Company admin'
    COMPANY_USER = 'company_user', 'Company user'


'''
 CompanyUserMembership là model xác định một tài khoản thuộc công ty nào và có quyền cấp công ty gì.

  Nó không biểu diễn chức danh nghề nghiệp, phòng ban hay trưởng nhóm.

  Model này là bản ghi thành viên công ty:

  User + Company + vai trò trong công ty

  Ví dụ:

   user       company        local_username    role
  ━━━━━━━━━  ━━━━━━━━━━━━━  ━━━━━━━━━━━━━━━━  ━━━━━━━━━━━━━━━
   User 15    Công ty ABC    nguyenvana        company_user
  ─────────  ─────────────  ────────────────  ───────────────
   User 16    Công ty ABC    admin             company_admin

  Nếu chỉ có User, hệ thống biết tài khoản là ai nhưng chưa biết:

  - Thuộc công ty nào.
  - Username hiển thị trong công ty là gì.
  - Có phải quản trị viên công ty không.
  - Membership có đang hoạt động không.
'''

#class CompanyUserMembership đại diện cho mối quan hệ giữa người dùng và công ty, cho biết người dùng nào thuộc về công ty nào, tên người dùng hiển thị trong công ty, vai trò của họ trong công ty (quản trị viên hoặc người dùng), trạng thái hoạt động của thành viên đó, yêu cầu đổi mật khẩu và thời điểm họ gia nhập công ty. Ràng buộc duy nhất đảm bảo rằng mỗi người dùng chỉ có thể có một tài khoản thành viên trong một công ty cụ thể một lần, giúp duy trì tính toàn vẹn của dữ liệu về thành viên công ty và tránh trùng lặp thông tin về mối quan hệ giữa người dùng và công ty.


class CompanyUserMembership(models.Model):
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name='memberships',
    )
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='company_membership',
    )
    local_username = models.CharField(max_length=150)
    role = models.CharField(
        max_length=24,
        choices=CompanyRole.choices,
        default=CompanyRole.COMPANY_USER,
    )
    is_active = models.BooleanField(default=True)
    must_change_password = models.BooleanField(default=False)
    joined_at = models.DateTimeField(auto_now_add=True)
    last_login_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['company__name', 'local_username']
        constraints = [
            models.UniqueConstraint(fields=['company', 'local_username'], name='uniq_company_local_username'),
        ]

    def __str__(self):
        return f'{self.company.code}:{self.local_username}'



# class CompanyImportBatch đại diện cho một batch nhập khẩu công ty, với các trường như loại nguồn dữ liệu, trạng thái của batch, người tải lên, payload xem trước, lỗi xác thực, tóm tắt commit và công ty mục tiêu. Nó cũng có các trường thời gian tạo và cập nhật để theo dõi quá trình nhập khẩu. Ràng buộc duy nhất đảm bảo rằng mỗi batch nhập khẩu có một ID duy nhất, giúp duy trì tính toàn vẹn của dữ liệu về quá trình nhập khẩu công ty.

class CompanyImportBatch(models.Model):
    SOURCE_EXCEL = 'excel'
    SOURCE_MANUAL = 'manual'
    STATUS_PREVIEWED = 'previewed'
    STATUS_COMMITTED = 'committed'
    STATUS_FAILED = 'failed'

    source_type = models.CharField(max_length=20, default=SOURCE_EXCEL)
    status = models.CharField(max_length=20, default=STATUS_PREVIEWED)
    uploaded_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='company_import_batches',
    )
    preview_payload = models.JSONField(default=dict, blank=True)
    validation_errors = models.JSONField(default=list, blank=True)
    commit_summary = models.JSONField(default=dict, blank=True)
    target_company = models.ForeignKey(
        Company,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='import_batches',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

# class UserAlias đại diện cho một bí danh của người dùng trong công ty, với các trường như người dùng, công ty, bí danh, bí danh đã được chuẩn hóa, gợi ý ưu tiên và thời điểm tạo và cập nhật. Ràng buộc duy nhất đảm bảo rằng mỗi bí danh trong cùng một công ty phải có giá trị chuẩn hóa riêng biệt cho mỗi người dùng, giúp duy trì tính toàn vẹn của dữ liệu về bí danh người dùng trong công ty. Phương thức clean được sử dụng để làm sạch và xác thực dữ liệu trước khi lưu, đảm bảo rằng bí danh không được để trống, thuộc về cùng công ty với người dùng và không trùng lặp với các bí danh khác của cùng người dùng trong cùng công ty. Nếu có lỗi xác thực, nó sẽ ném ra ValidationError với thông tin chi tiết về lỗi
class UserAlias(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='aliases',
    )
    company = models.ForeignKey(
        Company,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='user_aliases',
    )
    alias = models.CharField(max_length=150)
    normalized_alias = models.CharField(max_length=150, editable=False)
    is_primary_hint = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-is_primary_hint', 'alias', 'id']
        constraints = [
            models.UniqueConstraint(
                fields=['company', 'user', 'normalized_alias'],
                name='uniq_user_alias_company_user_value',
            ),
        ]

    def __str__(self):
        return f'{self.user.username}: {self.alias}'
# def clean để làm sạch và xác thực dữ liệu trước khi lưu, đảm bảo rằng bí danh không được để trống, thuộc về cùng công ty với người dùng và không trùng lặp với các bí danh khác của cùng người dùng trong cùng công ty. Nếu có lỗi xác thực, nó sẽ ném ra ValidationError với thông tin chi tiết về lỗi.
    def clean(self):
        cleaned_alias = ' '.join(str(self.alias or '').split()).strip()
        normalized_alias = normalize_lookup_value(cleaned_alias)
        if not normalized_alias:
            raise ValidationError({'alias': 'Bi danh khong duoc de trong.'})

        membership = getattr(self.user, 'company_membership', None) if self.user_id else None
        membership_company = getattr(membership, 'company', None)
        if membership_company is not None:
            if self.company_id not in (None, membership_company.id):
                raise ValidationError({'company': 'Bi danh phai thuoc cung cong ty voi user.'})
            self.company = membership_company
        elif self.company_id is not None:
            raise ValidationError({'company': 'User hien tai chua thuoc cong ty nao.'})

        duplicate_qs = UserAlias.objects.filter(
            user=self.user,
            normalized_alias=normalized_alias,
        )
        if membership_company is not None:
            duplicate_qs = duplicate_qs.filter(company=membership_company)
        else:
            duplicate_qs = duplicate_qs.filter(company__isnull=True)
        if self.pk:
            duplicate_qs = duplicate_qs.exclude(pk=self.pk)
        if duplicate_qs.exists():
            raise ValidationError({'alias': 'Bi danh nay da ton tai trong cong ty hien tai.'})

        if self.is_primary_hint and self.user_id:
            primary_qs = UserAlias.objects.filter(
                user=self.user,
                is_primary_hint=True,
            )
            if membership_company is not None:
                primary_qs = primary_qs.filter(company=membership_company)
            else:
                primary_qs = primary_qs.filter(company__isnull=True)
            if self.pk:
                primary_qs = primary_qs.exclude(pk=self.pk)
            if primary_qs.exists():
                raise ValidationError({'is_primary_hint': 'Chi duoc danh dau mot bi danh uu tien.'})

        self.alias = cleaned_alias
        self.normalized_alias = normalized_alias

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

# class UserProfile đại diện cho hồ sơ người dùng, với các trường như người dùng, công ty, avatar, tiểu sử, chức danh, số CCCD, ngày sinh, tuổi, mã nhân viên, trạng thái tài khoản quản trị viên nền tảng, sơ yếu lý lịch, số điện thoại và địa chỉ. Nó có liên kết một-một với model User và liên kết nhiều-một với model Company. Phương thức __str__ trả về tên người dùng của người dùng liên kết với hồ sơ, giúp dễ dàng nhận biết khi làm việc với các đối tượng hồ sơ người dùng trong Django admin hoặc khi in ra console.
class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    company = models.ForeignKey(
        Company,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='profiles',
    )
    avatar = models.ImageField(upload_to=_avatar_upload, max_length=500, blank=True, null=True)
    bio = models.TextField(blank=True)
    chuc_danh = models.CharField(max_length=150, blank=True, verbose_name='Chuc danh')
    cccd = models.CharField(max_length=20, blank=True, verbose_name='So CCCD')
    ngay_sinh = models.DateField(null=True, blank=True, verbose_name='Ngay sinh')
    age_years = models.PositiveIntegerField(null=True, blank=True, verbose_name='Tuoi')
    ma_nhan_vien = models.CharField(max_length=50, blank=True, verbose_name='Ma nhan vien')
    is_platform_admin_account = models.BooleanField(default=False)
    so_yeu_ly_lich = models.TextField(blank=True, verbose_name='So yeu ly lich')
    so_dien_thoai = models.CharField(max_length=20, blank=True, verbose_name='So dien thoai')
    dia_chi = models.CharField(max_length=255, blank=True, verbose_name='Dia chi')

    def __str__(self):
        return self.user.username
