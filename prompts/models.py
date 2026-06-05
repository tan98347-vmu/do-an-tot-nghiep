"""
Thuoc chuc nang nao: Tro ly AI, Hoi dap tai lieu, Sinh van ban tu mau, Guest tao van ban va cac luong AI nen.
Vai tro backend: File `prompts/models.py` giu hoac ho tro luong backend cho chat, RAG, OCR, prefill ho so, sinh van ban, luu session va quan ly tri thuc AI.
Vai tro cua no trong frontend: Cac man `/chat`, `/rag`, `/ai-doc`, `/guest` va cac dialog AI phu tro phu thuoc vao ket qua ma file nay sinh ra.
Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `ai_engine.models`, `ai_engine.rag_engine`, `ai_engine.rag_index`, `ai_engine.doc_creator`, `accounts.models`.
Tac dung: Bao dam prompt, ket qua AI, session hoi thoai, du lieu trich xuat va chi muc RAG phuc vu dung ngu canh cua nguoi dung hien tai.
"""

from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.contrib.auth.models import User

from accounts.peer_permissions import PeerPermissionLevel

PROMPT_STATUS_APPROVED       = 'approved'
PROMPT_STATUS_PENDING        = 'pending'          
PROMPT_STATUS_PENDING_LEADER = 'pending_leader'   
PROMPT_STATUS_REJECTED       = 'rejected'

PROMPT_STATUS_CHOICES = [
    (PROMPT_STATUS_APPROVED,       'Đã duyệt'),
    (PROMPT_STATUS_PENDING,        'Chờ admin duyệt'),
    (PROMPT_STATUS_PENDING_LEADER, 'Chờ trưởng nhóm duyệt'),
    (PROMPT_STATUS_REJECTED,       'Bị từ chối'),
]

USAGE_SCOPES: dict[str, str] = {
    'template_fill': 'Sinh van ban tu mau',
    'summary': 'Tom tat van ban',
    'word_ai_edit': 'Sua van ban voi AI',
    'chat': 'Tro ly AI / Hoi thoai',
    'compliance_check': 'Kiem tra theo prompt',
    'template_var_detect': 'Nhan dien bien khi upload mau',
}


def default_prompt_usage_scopes():
    return ['template_fill']


class PromptCategory(models.Model):
    """
    Thuoc chuc nang nao: Tro ly AI, Hoi dap tai lieu, Sinh van ban tu mau, Guest tao van ban va cac luong AI nen.
    Vai tro backend: Lop `PromptCategory` khai bao thuc the du lieu hoac bang nghiep vu cot loi cua file `prompts/models.py`.
    Vai tro cua no trong frontend: Frontend khong khoi tao lop nay truc tiep; serializer, service va API doc trang thai cua model de dung danh sach, badge, form va man chi tiet.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `ai_engine.models`, `ai_engine.rag_engine`, `ai_engine.rag_index`, `ai_engine.doc_creator`, `accounts.models`. Nam trong pham vi module hien tai.
    Tac dung: Luu schema, quan he va hanh vi mac dinh de cac luong doc/ghi du lieu ve `PromptCategory` khong bi lech trang thai.
    """
    name = models.CharField(max_length=100, unique=True, verbose_name='Tên danh mục')
    description = models.TextField(blank=True, verbose_name='Mô tả')
    created_at = models.DateTimeField(auto_now_add=True)

    

    class Meta:
        """
        Thuoc chuc nang nao: Tro ly AI, Hoi dap tai lieu, Sinh van ban tu mau, Guest tao van ban va cac luong AI nen.
        Vai tro backend: Lop `Meta` dong goi mot cum hanh vi hoac cau hinh backend cua file `prompts/models.py`.
        Vai tro cua no trong frontend: Frontend khong goi truc tiep lop nay; cac endpoint hoac service cua cung tinh nang se su dung no de tao du lieu trinh bay hoac kiem soat luong xu ly.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `ai_engine.models`, `ai_engine.rag_engine`, `ai_engine.rag_index`, `ai_engine.doc_creator`, `accounts.models`. Nam trong pham vi cua `PromptCategory` va cung dung chung ngu canh cua file nay.
        Tac dung: To chuc logic lien quan toi `Meta` thanh mot don vi ro rang de nhung ham khac goi lai de hon.
        """
        verbose_name = 'Danh mục prompt'
        verbose_name_plural = 'Danh mục prompt'
        ordering = ['name']

    

    def __str__(self):
        """
        Thuoc chuc nang nao: Tro ly AI, Hoi dap tai lieu, Sinh van ban tu mau, Guest tao van ban va cac luong AI nen.
        Vai tro backend: Ham `__str__` la helper gan voi model hoac storage trong file `prompts/models.py` trong lop `PromptCategory`, chu yeu de tra nhan hien thi gon cua doi tuong.
        Vai tro cua no trong frontend: Frontend khong goi truc tiep helper nay; no chi thay hau qua cua buoc tra nhan hien thi gon cua doi tuong qua ten file, duong dan luu hoac trang thai model duoc render ra giao dien.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `ai_engine.models`, `ai_engine.rag_engine`, `ai_engine.rag_index`, `ai_engine.doc_creator`, `accounts.models`. Nam trong lop `PromptCategory` va phuc vu luong xu ly cua lop nay.
        Tac dung: Chuan hoa buoc tra nhan hien thi gon cua doi tuong ngay sat model de phan con lai cua code khong phai lap lai quy tac luu tru.
        """
        return self.name

class Prompt(models.Model):
    """
    Thuoc chuc nang nao: Tro ly AI, Hoi dap tai lieu, Sinh van ban tu mau, Guest tao van ban va cac luong AI nen.
    Vai tro backend: Lop `Prompt` khai bao thuc the du lieu hoac bang nghiep vu cot loi cua file `prompts/models.py`.
    Vai tro cua no trong frontend: Frontend khong khoi tao lop nay truc tiep; serializer, service va API doc trang thai cua model de dung danh sach, badge, form va man chi tiet.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `ai_engine.models`, `ai_engine.rag_engine`, `ai_engine.rag_index`, `ai_engine.doc_creator`, `accounts.models`. Nam trong pham vi module hien tai.
    Tac dung: Luu schema, quan he va hanh vi mac dinh de cac luong doc/ghi du lieu ve `Prompt` khong bi lech trang thai.
    """
    title = models.CharField(max_length=255, verbose_name='Tiêu đề')
    system_content = models.TextField(
        blank=True,
        verbose_name='Hệ tư tưởng (System Ideology)',
        help_text='Thay thế toàn bộ danh tính gốc của AI. Ví dụ: "Bạn là trợ lý pháp chế của tập đoàn ABC. Luôn trả lời bằng văn phong trang trọng."'
    )
    rules_content = models.TextField(
        blank=True,
        verbose_name='Suy luận (In-Context Rules)',
        help_text='Ghi đè phần QUY TẮC trong tạo văn bản. Ví dụ: "Tuyệt đối không tự điền thông tin thiếu, hãy ghi [chưa cung cấp]."'
    )
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='prompts')
    is_shared = models.BooleanField(default=False, verbose_name='Chia sẻ nội bộ')

    
    VISIBILITY_PRIVATE = 'private'
    VISIBILITY_GROUP   = 'group'
    VISIBILITY_PUBLIC  = 'public'
    VISIBILITY_CHOICES = [
        ('private', 'Riêng tư'),
        ('group',   'Nhóm'),
        ('public',  'Công khai'),
    ]
    visibility  = models.CharField(
        max_length=10, choices=VISIBILITY_CHOICES, default='private',
        verbose_name='Phạm vi'
    )
    group = models.ForeignKey(
        'accounts.UserGroup', null=True, blank=True,
        on_delete=models.SET_NULL, related_name='prompts',
        verbose_name='Nhóm'
    )
    status = models.CharField(
        max_length=20, choices=PROMPT_STATUS_CHOICES,
        default=PROMPT_STATUS_APPROVED,
        verbose_name='Trạng thái'
    )
    approved_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL,
        related_name='approved_prompts', verbose_name='Người duyệt'
    )
    approved_at = models.DateTimeField(null=True, blank=True, verbose_name='Ngày duyệt')
    approver_note = models.TextField(blank=True, verbose_name='Ghi chú duyệt')

    category = models.ForeignKey(
        PromptCategory, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='prompts',
        verbose_name='Danh mục'
    )
    tags = models.CharField(max_length=255, blank=True, verbose_name='Tags')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    SOURCE_CURATED = 'curated'
    SOURCE_USER_INLINE = 'user_inline'
    SOURCE_IMPORTED = 'imported'
    SOURCE_CHOICES = [
        (SOURCE_CURATED, 'Curated'),
        (SOURCE_USER_INLINE, 'User inline'),
        (SOURCE_IMPORTED, 'Imported'),
    ]
    source = models.CharField(
        max_length=20, choices=SOURCE_CHOICES, default=SOURCE_CURATED,
        db_index=True, verbose_name='Nguồn',
    )
    usage_scope = ArrayField(
        models.CharField(max_length=32),
        default=default_prompt_usage_scopes,
        blank=True,
        verbose_name='Phạm vi sử dụng',
    )
    safety_score = models.FloatField(null=True, blank=True, verbose_name='Điểm rủi ro')
    safety_flags = models.JSONField(default=list, blank=True, verbose_name='Cờ rủi ro')
    original_raw_text = models.TextField(blank=True, verbose_name='Văn bản gốc (trước sanitize)')
    original_raw_text_hash = models.CharField(
        max_length=64, blank=True, db_index=True, verbose_name='Hash văn bản gốc',
    )
    usage_count = models.PositiveIntegerField(default=0, verbose_name='Số lần dùng')

    PEER_SHARE_NONE = 'none'
    PEER_SHARE_PENDING_LEADER = 'pending_leader'
    PEER_SHARE_ACTIVE = 'active'
    PEER_SHARE_REJECTED = 'rejected'
    PEER_SHARE_STATUS_CHOICES = [
        (PEER_SHARE_NONE, 'Không chia sẻ'),
        (PEER_SHARE_PENDING_LEADER, 'Chờ trưởng nhóm duyệt'),
        (PEER_SHARE_ACTIVE, 'Đã kích hoạt'),
        (PEER_SHARE_REJECTED, 'Bị từ chối'),
    ]
    peer_share_status = models.CharField(
        max_length=20, choices=PEER_SHARE_STATUS_CHOICES,
        default=PEER_SHARE_NONE, db_index=True,
    )
    peer_share_approved_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL,
        related_name='peer_approved_prompts',
    )
    peer_share_approved_at = models.DateTimeField(null=True, blank=True)
    peer_share_approver_note = models.TextField(blank=True)
    peer_share_submitted_at = models.DateTimeField(null=True, blank=True)

    

    class Meta:
        """
        Thuoc chuc nang nao: Tro ly AI, Hoi dap tai lieu, Sinh van ban tu mau, Guest tao van ban va cac luong AI nen.
        Vai tro backend: Lop `Meta` dong goi mot cum hanh vi hoac cau hinh backend cua file `prompts/models.py`.
        Vai tro cua no trong frontend: Frontend khong goi truc tiep lop nay; cac endpoint hoac service cua cung tinh nang se su dung no de tao du lieu trinh bay hoac kiem soat luong xu ly.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `ai_engine.models`, `ai_engine.rag_engine`, `ai_engine.rag_index`, `ai_engine.doc_creator`, `accounts.models`. Nam trong pham vi cua `Prompt` va cung dung chung ngu canh cua file nay.
        Tac dung: To chuc logic lien quan toi `Meta` thanh mot don vi ro rang de nhung ham khac goi lai de hon.
        """
        verbose_name = 'Prompt'
        verbose_name_plural = 'Prompts'
        ordering = ['-updated_at']
        constraints = [
            models.UniqueConstraint(
                fields=['owner', 'title'],
                name='uniq_prompt_owner_title',
            ),
        ]

    

    def __str__(self):
        """
        Thuoc chuc nang nao: Tro ly AI, Hoi dap tai lieu, Sinh van ban tu mau, Guest tao van ban va cac luong AI nen.
        Vai tro backend: Ham `__str__` la helper gan voi model hoac storage trong file `prompts/models.py` trong lop `Prompt`, chu yeu de tra nhan hien thi gon cua doi tuong.
        Vai tro cua no trong frontend: Frontend khong goi truc tiep helper nay; no chi thay hau qua cua buoc tra nhan hien thi gon cua doi tuong qua ten file, duong dan luu hoac trang thai model duoc render ra giao dien.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `ai_engine.models`, `ai_engine.rag_engine`, `ai_engine.rag_index`, `ai_engine.doc_creator`, `accounts.models`. Phoi hop truc tiep voi cac method nhu `get_tag_list` trong cung lop.
        Tac dung: Chuan hoa buoc tra nhan hien thi gon cua doi tuong ngay sat model de phan con lai cua code khong phai lap lai quy tac luu tru.
        """
        return self.title

    

    def get_tag_list(self):
        """
        Thuoc chuc nang nao: Tro ly AI, Hoi dap tai lieu, Sinh van ban tu mau, Guest tao van ban va cac luong AI nen.
        Vai tro backend: Ham `get_tag_list` la method gan voi model trong file `prompts/models.py` trong lop `Prompt`, phu trach tra danh sach du lieu theo bo loc hien tai.
        Vai tro cua no trong frontend: Frontend khong goi method model truc tiep, nhung serializer va API se dua vao ket qua tra danh sach du lieu theo bo loc hien tai nay de dung trang thai hoac nhan tren giao dien.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `ai_engine.models`, `ai_engine.rag_engine`, `ai_engine.rag_index`, `ai_engine.doc_creator`, `accounts.models`. Phoi hop truc tiep voi cac method nhu `__str__` trong cung lop.
        Tac dung: Dua hanh vi tra danh sach du lieu theo bo loc hien tai ve dung noi du lieu duoc quan ly thay vi rai sang nhieu view hoac service khac.
        """
        return [t.strip() for t in self.tags.split(',') if t.strip()]


class PromptInjectionLog(models.Model):
    LAYER_CHOICES = [
        ('L1_limit', 'L1 - Hard limit'),
        ('L2_regex', 'L2 - Sanitize regex'),
        ('L3_wrap', 'L3 - XML wrapping'),
        ('L4_heuristic', 'L4 - Heuristic'),
        ('L5_llm', 'L5 - LLM classifier'),
        ('L6_output', 'L6 - Output validation'),
    ]
    VERDICT_CHOICES = [
        ('allow', 'Allow'),
        ('redact', 'Redact'),
        ('block', 'Block'),
        ('escalate', 'Escalate'),
    ]

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='prompt_injection_logs',
    )
    prompt = models.ForeignKey(
        Prompt, null=True, blank=True, on_delete=models.SET_NULL,
        related_name='injection_logs',
    )
    raw_input = models.TextField(blank=True)
    sanitized_input = models.TextField(blank=True)
    layer = models.CharField(max_length=20, choices=LAYER_CHOICES, db_index=True)
    verdict = models.CharField(max_length=16, choices=VERDICT_CHOICES, db_index=True)
    score = models.FloatField(default=0.0)
    flags = models.JSONField(default=list, blank=True)
    llm_classifier_response = models.TextField(blank=True)
    latency_ms = models.IntegerField(default=0)
    ip = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=512, blank=True)
    request_id = models.CharField(max_length=64, blank=True, db_index=True)
    incident_id = models.CharField(max_length=32, blank=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = 'Prompt injection log'
        verbose_name_plural = 'Prompt injection logs'
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['verdict', '-created_at']),
        ]
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.layer}/{self.verdict} - {self.created_at:%Y-%m-%d %H:%M}'


class PromptAudienceMember(models.Model):
    prompt = models.ForeignKey(
        Prompt, related_name='audience_members', on_delete=models.CASCADE,
    )
    user = models.ForeignKey(
        User, related_name='prompt_audience_memberships', on_delete=models.CASCADE,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    added_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL,
        related_name='prompt_audience_added',
    )
    permission_level = models.CharField(
        max_length=8,
        choices=PeerPermissionLevel.choices,
        default=PeerPermissionLevel.VIEW,
    )

    class Meta:
        verbose_name = 'Người được chia sẻ prompt'
        verbose_name_plural = 'Người được chia sẻ prompt'
        unique_together = ('prompt', 'user')
        indexes = [
            models.Index(fields=['prompt', 'user']),
            models.Index(fields=['user', '-created_at']),
        ]

    def __str__(self):
        return f'{self.prompt_id} -> {self.user_id}'
