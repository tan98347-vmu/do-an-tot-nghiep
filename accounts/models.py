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

    class Meta:
        ordering = ['name', 'code']

    def __str__(self):
        return f'{self.code} - {self.name}'

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

    @property
    def is_login_enabled(self):
        return self.status == CompanyStatus.ACTIVE


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

    class Meta:
        verbose_name = 'Phong ban'
        verbose_name_plural = 'Phong ban'
        ordering = ['name']
        constraints = [
            models.UniqueConstraint(fields=['company', 'name'], name='uniq_department_company_name'),
            models.UniqueConstraint(fields=['company', 'code'], name='uniq_department_company_code'),
        ]

    def __str__(self):
        return f"{self.code} - {self.name}"


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

    class Meta:
        verbose_name = 'Thanh vien phong ban'
        verbose_name_plural = 'Thanh vien phong ban'
        unique_together = ('department', 'user')
        ordering = ['department__name', 'user__username']

    def __str__(self):
        return f'{self.user.username} -> {self.department.code}'


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

    def __str__(self):
        return f'{self.company.code} AI config'

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


class CompanyRole(models.TextChoices):
    COMPANY_ADMIN = 'company_admin', 'Company admin'
    COMPANY_USER = 'company_user', 'Company user'


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
