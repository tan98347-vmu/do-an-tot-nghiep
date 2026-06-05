"""
Thuoc chuc nang nao: Lop du lieu cho tro ly AI, chat/RAG, audio va logging su dung model.
Vai tro backend: File nay luu tri thuc do user nap vao, luu session hoi thoai, tung tin nhan, tep audio cua che do giong noi va nhat ky goi model AI de cac service/endpoint co noi doc ghi tap trung.
Vai tro cua no trong frontend: Man chat AI, man tro ly moi, lich su hoi dap RAG, danh sach audio va mot so thong tin quan tri AI deu bat nguon tu cac model trong file nay.
Moi lien he voi nhung ham / source khac: Duoc `api/views/chat.py`, `api/views/assistant.py`, `ai_engine.rag_engine`, `ai_engine.rag_index`, `ai_engine.assistant_engine` va signal cleanup trong `ai_engine.signals` su dung.
Tac dung: Lam tang du lieu cot loi cho toan bo tinh nang AI, tu luu hoi thoai den quan ly tri thuc va thong ke goi model.
"""

from django.db import models
from django.contrib.auth.models import User
from accounts.storage_paths import company_media_path
from my_tennis_club.soft_delete import ActiveOnlyManager


def _chat_audio_upload(instance, filename):
    return company_media_path(
        company=getattr(getattr(instance, 'session', None), 'company', None),
        section='chat_audio',
        filename=filename,
    )

class KnowledgeBase(models.Model):
    """
    Thuoc chuc nang nao: Kho tri thuc nguoi dung nap vao cho AI tra cuu.
    Vai tro backend: Model nay luu cac manh tri thuc dang text hoac PDF kem chu so huu va co chia se hay khong, de backend co the dua noi dung vao RAG/index hoac tra cuu theo user.
    Vai tro cua no trong frontend: Frontend co the hien danh sach nguon tri thuc, trang thai chia se va noi dung da nap cho AI tu du lieu cua model nay.
    Moi lien he voi nhung ham / source khac: `ai_engine.rag_engine.add_to_knowledge_base` va cac luong hoi dap AI co the doc model nay; lien ket voi `User` qua field `owner`.
    Tac dung: Tao kho noi dung goc cho nhung tinh nang hoi dap AI duoc boi canh boi tai lieu nguoi dung dua vao.
    """
    SOURCE_TEXT = 'text'
    SOURCE_PDF = 'pdf'
    SOURCE_CHOICES = [
        (SOURCE_TEXT, 'Văn bản'),
        (SOURCE_PDF, 'PDF'),
    ]

    title = models.CharField(max_length=255, verbose_name='Tiêu đề')
    content = models.TextField(verbose_name='Nội dung')
    company = models.ForeignKey(
        'accounts.Company',
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name='knowledge_bases',
    )
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='knowledge_items')
    is_shared = models.BooleanField(default=False, verbose_name='Chia sẻ')
    source_type = models.CharField(max_length=10, choices=SOURCE_CHOICES, default=SOURCE_TEXT)
    created_at = models.DateTimeField(auto_now_add=True)

    

    class Meta:
        """
        Thuoc chuc nang nao: Metadata cho kho tri thuc AI.
        Vai tro backend: Khoi nay dat ten hien thi va sap xep mac dinh theo thoi gian tao giam dan de ban ghi moi nhat duoc uu tien khi xem admin hay liet ke.
        Vai tro cua no trong frontend: Danh sach nguon tri thuc thuong hien noi dung moi nhat truoc ma khong can endpoint nao sap xep lai neu khong can.
        Moi lien he voi nhung ham / source khac: Django admin, ORM va serializer huong thu tu `ordering` nay khi truy van mac dinh.
        Tac dung: Dat quy tac hien thi co ban ngay tren tang model.
        """
        verbose_name = 'Knowledge Base'
        verbose_name_plural = 'Knowledge Base'
        ordering = ['-created_at']

    

    def __str__(self):
        """
        Thuoc chuc nang nao: Chuoi dai dien cho mot muc tri thuc.
        Vai tro backend: Ham nay dung `title` lam nhan dai dien de log, admin va relation field de doc.
        Vai tro cua no trong frontend: Neu giao dien hoac serializer gián tiep dung string cua model, user se thay tieu de tri thuc thay vi ID.
        Moi lien he voi nhung ham / source khac: Duoc admin, shell va debug log goi khi ep doi tuong thanh chuoi.
        Tac dung: Tao cach nhan dien nhanh cho ban ghi tri thuc.
        """
        return self.title

    def save(self, *args, **kwargs):
        if self.company_id is None and self.owner_id and getattr(getattr(self.owner, 'company_membership', None), 'company_id', None):
            self.company = self.owner.company_membership.company
        super().save(*args, **kwargs)

class ChatSession(models.Model):
    """
    Thuoc chuc nang nao: Phien hoi thoai cho chat AI, RAG, assistant va che do giong noi.
    Vai tro backend: Model nay luu mot thread hoi thoai cua user, loai session dang chay, mode RAG, thong tin soft-delete va thoi gian cap nhat de backend quan ly lich su tra loi.
    Vai tro cua no trong frontend: Sidebar/session list, viec tiep tuc cuoc tro chuyen cu, xoa mem session va phan loai text/voice/RAG tren frontend deu dua vao model nay.
    Moi lien he voi nhung ham / source khac: Co quan he `messages` toi `ChatMessage`, `audio_attachments` toi `ChatAudioAttachment`; `api/views/chat.py` va `api/views/assistant.py` tao/doc/xoa session; `ActiveOnlyManager` loc session da xoa mem.
    Tac dung: Tro thanh don vi goc de gom nhom cac tin nhan AI theo tung cuoc hoi thoai.
    """
    SESSION_CHAT = 'chat'
    SESSION_RAG = 'rag'
    SESSION_ASSISTANT = 'assistant'
    SESSION_VOICE = 'voice'
    SESSION_TYPE_CHOICES = [
        (SESSION_CHAT, 'Chat AI'),
        (SESSION_RAG, 'Hỏi đáp RAG'),
        (SESSION_ASSISTANT, 'Trợ lý AI'),
        (SESSION_VOICE, 'Giọng nói AI'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='chat_sessions')
    title = models.CharField(max_length=255, default='Cuộc trò chuyện mới')
    company = models.ForeignKey(
        'accounts.Company',
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name='chat_sessions',
    )
    session_type = models.CharField(max_length=10, choices=SESSION_TYPE_CHOICES, default=SESSION_CHAT)
    
    rag_mode = models.CharField(max_length=20, blank=True, default='')  
    is_deleted = models.BooleanField(default=False, db_index=True)
    deleted_at = models.DateTimeField(null=True, blank=True, db_index=True)
    deleted_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='deleted_chat_sessions',
    )
    assistant_state = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = ActiveOnlyManager()
    all_objects = models.Manager()

    

    class Meta:
        """
        Thuoc chuc nang nao: Metadata cho session hoi thoai AI.
        Vai tro backend: Khoi nay sap xep session theo `updated_at` giam dan de thread vua co tin nhan moi luon noi len dau trong truy van mac dinh.
        Vai tro cua no trong frontend: Danh sach session tren giao dien chat/assistant se uu tien cuoc tro chuyen vua dien ra gan nhat.
        Moi lien he voi nhung ham / source khac: Cac endpoint liet ke session huong loi tu `ordering` nay neu khong dat sap xep lai.
        Tac dung: Giu thu tu session phu hop voi trai nghiem hoi thoai.
        """
        ordering = ['-updated_at', '-created_at']

    

    def __str__(self):
        """
        Thuoc chuc nang nao: Chuoi dai dien cho session AI.
        Vai tro backend: Ham nay ghep username va title session de admin/log nhanh biet thread nao thuoc user nao.
        Vai tro cua no trong frontend: Frontend huong loi gian tiep neu serializer/admin can render string cua session trong moi truong debug hay quan tri.
        Moi lien he voi nhung ham / source khac: Doc field `user` va `title`; thuong xuat hien trong admin/shell.
        Tac dung: Lam cho session de nhan dien hon khi can hien thi bang chuoi.
        """
        return f'{self.user.username} - {self.title}'

    def save(self, *args, **kwargs):
        if self.company_id is None and self.user_id and getattr(getattr(self.user, 'company_membership', None), 'company_id', None):
            self.company = self.user.company_membership.company
        super().save(*args, **kwargs)

class ChatMessage(models.Model):
    """
    Thuoc chuc nang nao: Tung turn tin nhan ben trong mot session AI.
    Vai tro backend: Model nay luu role user/assistant, noi dung, citations va payload bo sung cua moi luot hoi dap de backend co the phat lai lich su, mirror ket qua RAG va luu metadata hanh dong.
    Vai tro cua no trong frontend: Bong chat, lich su hoi dap, duong dan nguon trich dan va cac action gan voi ket qua AI deu doc du lieu tu model nay.
    Moi lien he voi nhung ham / source khac: Thuoc ve `ChatSession`; duoc tao boi `api/views/chat.py`, `api/views/assistant.py` va doc boi serializer chat.
    Tac dung: Giu trang thai va du lieu hien thi cua tung luot chat AI.
    """
    ROLE_USER = 'user'
    ROLE_ASSISTANT = 'assistant'
    ROLE_CHOICES = [
        (ROLE_USER, 'User'),
        (ROLE_ASSISTANT, 'Assistant'),
    ]

    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name='messages')
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    content = models.TextField()
    citations = models.JSONField(null=True, blank=True)  
    payload = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    

    class Meta:
        """
        Thuoc chuc nang nao: Metadata cho tin nhan AI.
        Vai tro backend: Khoi nay sap xep tin nhan tang dan theo `created_at` de backend luon phat lai lich su theo dung thu tu phat sinh.
        Vai tro cua no trong frontend: Bong chat va lich su session se hien dung thu tu hoi dap tu tren xuong duoi.
        Moi lien he voi nhung ham / source khac: Cac serializer/view doc queryset mac dinh cua `messages` huong truc tiep thu tu nay.
        Tac dung: Giu tinh tuyen tinh cua lich su chat.
        """
        ordering = ['created_at']

    

    def __str__(self):
        """
        Thuoc chuc nang nao: Chuoi dai dien ngan cho mot tin nhan chat.
        Vai tro backend: Ham nay lay role va 50 ky tu dau noi dung de log/admin nhin nhanh duoc day la message nao ma khong mo toan bo payload.
        Vai tro cua no trong frontend: Frontend khong goi truc tiep, nhung cong cu debug va admin co chuoi ngan gon de nhan dien tin nhan.
        Moi lien he voi nhung ham / source khac: Dung field `role` va `content`; duoc co che string cua Django su dung.
        Tac dung: Tao nhan ngan cho ban ghi tin nhan.
        """
        return f'{self.role}: {self.content[:50]}'

class ChatAudioAttachment(models.Model):
    """
    Thuoc chuc nang nao: Tep audio va metadata cho phien tro ly giong noi.
    Vai tro backend: Model nay luu tep ghi am, transcript, mime type, do dai va lien ket toi session/message de backend co the tai lai, phat lai hoac xoa audio dung ngu canh.
    Vai tro cua no trong frontend: Man voice assistant va lich su audio dua vao model nay de hien danh sach file da ghi, cho phep nghe lai hoac tai xuong.
    Moi lien he voi nhung ham / source khac: Gan voi `ChatSession`, `ChatMessage` va `User`; `api/views/assistant.py` tao/list/download ban ghi, `ai_engine.signals` don dep file sau khi xoa.
    Tac dung: Tach tai nguyen audio ra khoi message text nhung van lien ket chat che voi phien hoi thoai.
    """
    session = models.ForeignKey(
        ChatSession,
        on_delete=models.CASCADE,
        related_name='audio_attachments',
    )
    message = models.ForeignKey(
        ChatMessage,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='audio_attachments',
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='chat_audio_attachments',
    )
    title = models.CharField(max_length=255, blank=True)
    transcript = models.TextField(blank=True)
    mime_type = models.CharField(max_length=120, blank=True)
    duration_seconds = models.FloatField(default=0)
    audio_file = models.FileField(upload_to=_chat_audio_upload, max_length=500)
    created_at = models.DateTimeField(auto_now_add=True)

    

    class Meta:
        """
        Thuoc chuc nang nao: Metadata cho file audio tro ly.
        Vai tro backend: Sap xep audio moi nhat len dau de danh sach tai nguyen giong noi luon hien ban ghi vua tao gan nhat.
        Vai tro cua no trong frontend: Man lich su audio co thu tu hop trai nghiem ma khong can endpoint sap xep them.
        Moi lien he voi nhung ham / source khac: Serializer va endpoint list audio huong `ordering` nay.
        Tac dung: Dinh nghia thu tu xem audio mac dinh.
        """
        ordering = ['-created_at']

    

    def __str__(self):
        """
        Thuoc chuc nang nao: Chuoi dai dien cho ban ghi audio.
        Vai tro backend: Ham nay uu tien `title`, neu chua co thi tao nhan du phong theo `pk` de admin/log van co cach goi ten ban ghi audio.
        Vai tro cua no trong frontend: Frontend huong loi gian tiep trong cac ngu canh debug/quan tri khi audio chua co tieu de ro rang.
        Moi lien he voi nhung ham / source khac: Dung field `title` va `pk`; duoc goi boi co che string cua Django.
        Tac dung: Tao nhan ngan cho tep audio da luu.
        """
        return self.title or f'Audio #{self.pk}'

class AIUsageLog(models.Model):
    """
    Thuoc chuc nang nao: Nhat ky goi model AI.
    Vai tro backend: Model nay ghi lai ai da goi model nao va trang thai thanh cong/loi, de backend co the thong ke usage, debug su co va theo doi tac dong cua cac luong AI.
    Vai tro cua no trong frontend: Hien tai frontend chu yeu huong loi gian tiep qua cac dashboard/bao cao quan tri neu co, thay vi goi truc tiep model nay.
    Moi lien he voi nhung ham / source khac: `ai_engine.rag_engine._record_ai_usage` ghi du lieu vao day moi khi goi model LLM.
    Tac dung: Tao audit trail toi thieu cho cac tac vu AI.
    """
    STATUS_SUCCESS = 'success'
    STATUS_ERROR = 'error'
    STATUS_CHOICES = [
        (STATUS_SUCCESS, 'Success'),
        (STATUS_ERROR, 'Error'),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='ai_usage_logs',
    )
    model_name = models.CharField(max_length=120, blank=True, default='')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_SUCCESS)
    created_at = models.DateTimeField(auto_now_add=True)

    

    class Meta:
        """
        Thuoc chuc nang nao: Metadata cho nhat ky su dung AI.
        Vai tro backend: Sap xep log moi nhat len dau de viec xem su co va quan sat luong goi model de hon.
        Vai tro cua no trong frontend: Neu co man quan tri/thong ke, du lieu moi nhat se o tren cung ngay ca khi khong dat sap xep rieng.
        Moi lien he voi nhung ham / source khac: ORM va admin su dung `ordering` nay khi doc model.
        Tac dung: Uu tien hien thi ban ghi usage moi tao.
        """
        ordering = ['-created_at']

    

    def __str__(self):
        """
        Thuoc chuc nang nao: Chuoi dai dien cho mot ban ghi usage AI.
        Vai tro backend: Ham nay hien owner, ten model va trang thai de khi xem admin/log co the biet nhanh lan goi nao da thanh cong hay that bai.
        Vai tro cua no trong frontend: Frontend khong goi truc tiep, nhung cac cong cu quan tri/developer thay duoc thong tin usage ro rang hon.
        Moi lien he voi nhung ham / source khac: Dung field `user`, `model_name`, `status`; phu hop voi du lieu ma `_record_ai_usage` ghi vao.
        Tac dung: Tao nhan ngan cho tung dong usage log.
        """
        owner = self.user.username if self.user_id else 'guest'
        return f'{owner} - {self.model_name or "unknown"} - {self.status}'


class ComplianceCheckResult(models.Model):
    TARGET_DOCUMENT = 'document'
    TARGET_TEMPLATE = 'template'
    TARGET_CHOICES = [
        (TARGET_DOCUMENT, 'Document'),
        (TARGET_TEMPLATE, 'Template'),
    ]

    target_type = models.CharField(
        max_length=16,
        choices=TARGET_CHOICES,
        db_index=True,
    )
    target_id = models.IntegerField(db_index=True)
    prompt = models.ForeignKey(
        'prompts.Prompt',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='compliance_checks',
    )
    passed = models.BooleanField()
    items_missing_json = models.JSONField(default=list, blank=True)
    content_hash = models.CharField(max_length=64, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    created_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='created_compliance_checks',
    )

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(
                fields=['target_type', 'target_id', 'prompt', 'content_hash']
            ),
        ]

    def __str__(self):
        return (
            f'{self.target_type}:{self.target_id} '
            f'prompt={self.prompt_id or "none"} '
            f'passed={self.passed}'
        )
