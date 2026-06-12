"""
 App ai_engine là gì?

  ai_engine là tầng nghiệp vụ trung tâm cho toàn bộ chức năng AI của hệ thống.

  Nó không chỉ “gọi AI để trả lời”, mà còn chịu trách nhiệm:

  - Quản lý phiên hội thoại.
  - Lưu lịch sử tin nhắn và audio.
  - Kết nối mô hình LLM/Ollama.
  - Trích xuất nội dung PDF, ảnh.
  - Tạo embedding và quản lý vector database.
  - Tìm kiếm RAG theo quyền người dùng.
  - Tạo văn bản từ mẫu.
  - Điều phối AI Assistant bằng tool calling.
  - Chuẩn bị quy trình gửi và ký văn bản.
  - Kiểm tra mức độ tuân thủ của tài liệu.
  - Ghi nhận lịch sử sử dụng AI.

  trong file models.py này, chúng ta định nghĩa các model dữ liệu cốt lõi cho các chức năng AI, bao gồm:
    - KnowledgeBase: Lưu trữ các mục tri thức có thể được sử dụng trong các phiên hội thoại AI hoặc RAG.
    - ChatSession: Quản lý các phiên hội thoại AI, bao gồm thông tin về người dùng, tiêu đề, công ty liên quan, loại phiên hội thoại, chế độ RAG nếu có, trạng thái xóa mềm và thời gian tạo/cập nhật.
    - ChatMessage: Lưu trữ các tin nhắn trong các phiên hội thoại AI
    - ChatAudioAttachment: Quản lý các tệp âm thanh liên quan đến các phiên hội thoại chat AI.
    - AIUsageLog: Ghi lại lịch sử sử dụng AI, bao gồm thông tin về người dùng, tên mô hình được gọi, trạng thái của cuộc gọi và thời gian tạo.
    - ComplianceCheckResult: Lưu trữ kết quả kiểm tra tuân thủ của các tài liệu hoặc mẫu tài liệu dựa trên các prompt đã được định nghĩa trước đó.
    

"""

from django.db import models
from django.contrib.auth.models import User
from accounts.storage_paths import company_media_path
from my_tennis_club.soft_delete import ActiveOnlyManager

# def _chat_audio_upload để tạo đường dẫn lưu trữ cho file audio liên quan đến một phiên hội thoại chat AI. Nó sử dụng hàm company_media_path để xây dựng đường dẫn lưu trữ dựa trên công ty của phiên hội thoại và khu vực lưu trữ 'chat_audio', cùng với tên file gốc đã được làm sạch. Kết quả của hàm này là một chuỗi đường dẫn lưu trữ an toàn và có tổ chức cho các file audio liên quan đến các phiên hội thoại chat AI trong hệ thống lưu trữ.
# vd: -> 'companies/<slug-cong-ty>/chat_audio/<ten-file>' (đường dẫn lưu file audio).
def _chat_audio_upload(instance, filename):
    return company_media_path(
        company=getattr(getattr(instance, 'session', None), 'company', None),
        section='chat_audio',
        filename=filename,
    )
# class KnowledgeBase để lưu trữ các mục tri thức (knowledge items) có thể được sử dụng trong các phiên hội thoại AI hoặc RAG. Mỗi mục tri thức bao gồm tiêu đề, nội dung, công ty liên quan, người sở hữu, trạng thái chia sẻ, loại nguồn (văn bản hoặc PDF) và thời gian tạo. Model này cho phép quản lý và tổ chức các nguồn tri thức một cách hiệu quả, đồng thời hỗ trợ việc truy cập và sử dụng chúng trong các tính năng AI của hệ thống.
# vd: lưu 1 quy chế/biểu mẫu nội bộ để dùng cho hỏi đáp RAG.
class KnowledgeBase(models.Model):
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

    

    # class Meta để đặt tên hiển thị (Knowledge Base) và sắp xếp các mục tri thức mới nhất lên đầu (created_at giảm dần).
    # vd: danh sách KnowledgeBase trong admin -> mục tạo gần nhất hiển thị trên cùng.
    class Meta:
        verbose_name = 'Knowledge Base'
        verbose_name_plural = 'Knowledge Base'
        ordering = ['-created_at']

    

    # def __str__ để hiển thị mục tri thức bằng chính tiêu đề của nó cho dễ nhận biết trong admin/log.
    # vd: mục có title 'Quy che nghi phep' -> str() = 'Quy che nghi phep'.
    def __str__(self):
        return self.title

    # def save để tự gán company theo công ty của owner nếu chưa có, đảm bảo mục tri thức luôn thuộc đúng công ty trước khi lưu.
    # vd: owner thuộc công ty A, tạo mục chưa set company -> tự gán company = A.
    def save(self, *args, **kwargs):
        if self.company_id is None and self.owner_id and getattr(getattr(self.owner, 'company_membership', None), 'company_id', None):
            self.company = self.owner.company_membership.company
        super().save(*args, **kwargs)

# class ChatSession để quản lý các phiên hội thoại AI, bao gồm thông tin về người dùng, tiêu đề, công ty liên quan, loại phiên hội thoại (chat, RAG, trợ lý AI hoặc giọng nói AI), chế độ RAG nếu có, trạng thái xóa mềm và thời gian tạo/cập nhật. Model này cho phép tổ chức và quản lý các phiên hội thoại một cách hiệu quả, đồng thời hỗ trợ việc truy cập và sử dụng chúng trong các tính năng AI của hệ thống.
# vd: 1 cuộc trò chuyện = 1 ChatSession (type: chat / rag / assistant / voice).
class ChatSession(models.Model):
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

    
# class Meta để định nghĩa metadata cho model ChatSession, bao gồm việc sắp xếp các bản ghi theo thứ tự giảm dần của trường updated_at và created_at. Điều này đảm bảo rằng khi truy vấn các phiên hội thoại, những phiên mới nhất sẽ được hiển thị trước, giúp người dùng dễ dàng tiếp cận với các phiên hội thoại gần đây nhất trong hệ thống.
    # vd: danh sách phiên -> phiên cập nhật gần nhất lên đầu.
    class Meta:
        ordering = ['-updated_at', '-created_at']

    
# def __str__ để tạo một chuỗi đại diện cho một phiên hội thoại chat, bao gồm tên người dùng và tiêu đề của phiên hội thoại. Điều này giúp dễ dàng nhận diện và phân biệt các phiên hội thoại trong các công cụ quản lý hoặc giao diện người dùng, đặc biệt khi có nhiều phiên hội thoại được tạo bởi cùng một người dùng hoặc có tiêu đề tương tự.
    # vd: -> 'nguyenvana - Cuoc tro chuyen moi'.
    def __str__(self):
        return f'{self.user.username} - {self.title}'

    # def save để tự gán company theo công ty của user nếu chưa có, giúp phiên hội thoại luôn gắn đúng công ty (phục vụ phân quyền đa công ty).
    # vd: user thuộc công ty A mở phiên chat mới -> session.company tự = A.
    def save(self, *args, **kwargs):
        if self.company_id is None and self.user_id and getattr(getattr(self.user, 'company_membership', None), 'company_id', None):
            self.company = self.user.company_membership.company
        super().save(*args, **kwargs)

# class ChatMessage để lưu từng tin nhắn trong một phiên hội thoại: vai trò (user/assistant), nội dung, trích dẫn (citations) và payload kèm theo, cùng thời điểm tạo.
# vd: 1 lượt hỏi của user + 1 lượt trả lời của assistant = 2 bản ghi ChatMessage trong cùng session.
class ChatMessage(models.Model):

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

    
# class Meta để định nghĩa metadata cho model ChatMessage, bao gồm việc sắp xếp các bản ghi theo thứ tự tăng dần của trường created_at. Điều này đảm bảo rằng khi truy vấn các tin nhắn trong một phiên hội thoại, chúng sẽ được hiển thị theo thứ tự thời gian từ cũ đến mới, giúp người dùng dễ dàng theo dõi diễn biến của cuộc trò chuyện một cách logic và mạch lạc.   
    # vd: tin nhắn trong phiên -> cũ ở trên, mới ở dưới (đúng dòng thời gian).
    class Meta:
        ordering = ['created_at']

    
# def __str__ để tạo một chuỗi đại diện cho một tin nhắn trong phiên hội thoại, bao gồm vai trò của người gửi (user hoặc assistant) và một phần nội dung của tin nhắn (giới hạn 50 ký tự). Điều này giúp dễ dàng nhận diện và phân biệt các tin nhắn trong các công cụ quản lý hoặc giao diện người dùng, đặc biệt khi có nhiều tin nhắn được gửi bởi cùng một vai trò hoặc có nội dung tương tự.
    # vd: -> 'user: Xin chao...'.
    def __str__(self):
        return f'{self.role}: {self.content[:50]}'

# class ChatAudioAttachment để quản lý các tệp âm thanh liên quan đến các phiên hội thoại chat AI, bao gồm thông tin về phiên hội thoại, tin nhắn liên quan (nếu có), người tạo, tiêu đề, bản ghi chuyển đổi văn bản (transcript), loại MIME, thời lượng, tệp âm thanh và thời gian tạo. Model này cho phép lưu trữ và quản lý các tệp âm thanh một cách hiệu quả, đồng thời hỗ trợ việc truy cập và sử dụng chúng trong các tính năng AI của hệ thống.
# vd: lưu file ghi âm + transcript của 1 lượt VoiceAI.
class ChatAudioAttachment(models.Model):

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

    

    # class Meta để sắp xếp các tệp audio mới nhất lên đầu (created_at giảm dần) cho danh sách lịch sử giọng nói.
    # vd: danh sách audio của 1 phiên -> file ghi gần nhất nằm trên đầu.
    class Meta:
        """
        Thuoc chuc nang nao: Metadata cho file audio tro ly.
        Vai tro backend: Sap xep audio moi nhat len dau de danh sach tai nguyen giong noi luon hien ban ghi vua tao gan nhat.
        Vai tro cua no trong frontend: Man lich su audio co thu tu hop trai nghiem ma khong can endpoint sap xep them.
        Moi lien he voi nhung ham / source khac: Serializer va endpoint list audio huong `ordering` nay.
        Tac dung: Dinh nghia thu tu xem audio mac dinh.
        """
        ordering = ['-created_at']

    

    # def __str__ để đặt tên hiển thị cho bản ghi audio: ưu tiên title, nếu trống thì dùng 'Audio #<pk>'.
    # vd: bản ghi chưa đặt title, pk=7 -> str() = 'Audio #7'.
    def __str__(self):
        """
        Thuoc chuc nang nao: Chuoi dai dien cho ban ghi audio.
        Vai tro backend: Ham nay uu tien `title`, neu chua co thi tao nhan du phong theo `pk` de admin/log van co cach goi ten ban ghi audio.
        Vai tro cua no trong frontend: Frontend huong loi gian tiep trong cac ngu canh debug/quan tri khi audio chua co tieu de ro rang.
        Moi lien he voi nhung ham / source khac: Dung field `title` va `pk`; duoc goi boi co che string cua Django.
        Tac dung: Tao nhan ngan cho tep audio da luu.
        """
        return self.title or f'Audio #{self.pk}'
# class AIUsageLog để ghi lại lịch sử sử dụng AI, bao gồm thông tin về người dùng, tên mô hình được gọi, trạng thái của cuộc gọi (thành công hoặc lỗi) và thời gian tạo. Model này cho phép theo dõi và phân tích việc sử dụng AI trong hệ thống, đồng thời hỗ trợ việc quản lý và tối ưu hóa các cuộc gọi AI dựa trên dữ liệu lịch sử này.
# vd: mỗi lần gọi AI ghi 1 dòng (user, model, success/error) để thống kê.
class AIUsageLog(models.Model):

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

    
# class Meta để định nghĩa metadata cho model AIUsageLog, bao gồm việc sắp xếp các bản ghi theo thứ tự giảm dần của trường created_at. Điều này đảm bảo rằng khi truy vấn lịch sử sử dụng AI, những bản ghi mới nhất sẽ được hiển thị trước, giúp người quản trị hoặc nhà phát triển dễ dàng tiếp cận với các cuộc gọi AI gần đây nhất trong hệ thống.
    # vd: danh sách log -> bản ghi mới nhất lên đầu.
    class Meta:
        ordering = ['-created_at']

    
# def __str__ để tạo một chuỗi đại diện cho một bản ghi lịch sử sử dụng AI, bao gồm tên người dùng (hoặc 'guest' nếu không có người dùng liên kết), tên mô hình được gọi (hoặc 'unknown' nếu không có tên mô hình) và trạng thái của cuộc gọi. Điều này giúp dễ dàng nhận diện và phân biệt các bản ghi lịch sử sử dụng AI trong các công cụ quản lý hoặc giao diện người dùng, đặc biệt khi có nhiều bản ghi được tạo bởi cùng một người dùng hoặc có trạng thái tương tự.
    # vd: -> 'nguyenvana - kimi-k2.6:cloud - success'.
    def __str__(self):
 
        owner = self.user.username if self.user_id else 'guest'
        return f'{owner} - {self.model_name or "unknown"} - {self.status}'

# class ComplianceCheckResult để lưu trữ kết quả kiểm tra tuân thủ của các tài liệu hoặc mẫu tài liệu dựa trên các prompt đã được định nghĩa trước đó. Mỗi bản ghi bao gồm thông tin về loại đối tượng được kiểm tra (tài liệu hoặc mẫu tài liệu), ID của đối tượng đó, prompt liên quan, kết quả kiểm tra (đạt hay không đạt), các mục bị thiếu trong kết quả JSON, hash nội dung, thời gian tạo và người tạo. Model này cho phép theo dõi và quản lý các kết quả kiểm tra tuân thủ một cách hiệu quả, đồng thời hỗ trợ việc phân tích và cải thiện chất lượng của các tài liệu và mẫu tài liệu trong hệ thống.
# vd: một tài liệu có thể được kiểm tra tuân thủ dựa trên một prompt yêu cầu trích xuất thông tin cụ thể, và kết quả kiểm tra sẽ cho biết liệu tài liệu đó có đáp ứng các yêu cầu của prompt hay không, cùng với thông tin chi tiết về những phần nào của tài liệu không đáp ứng được yêu cầu đó.
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

    # class Meta để sắp xếp kết quả kiểm tra tuân thủ mới nhất lên đầu và thêm index (target_type, target_id, prompt, content_hash) phục vụ tra cứu/cache nhanh.
    # vd: cùng (tài liệu, prompt, content_hash) -> tra nhanh kết quả đã chấm nhờ index, khỏi gọi lại LLM.
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(
                fields=['target_type', 'target_id', 'prompt', 'content_hash']
            ),
        ]

    # def __str__ để tóm tắt kết quả kiểm tra tuân thủ dạng 'loại:đối_tượng prompt=… passed=…' cho dễ đọc trong admin/log.
    # vd: 'document:45 prompt=12 passed=False'.
    def __str__(self):
        return (
            f'{self.target_type}:{self.target_id} '
            f'prompt={self.prompt_id or "none"} '
            f'passed={self.passed}'
        )
