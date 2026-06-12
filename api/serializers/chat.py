"""
Thuoc chuc nang nao: Tro ly AI, Hoi dap tai lieu, Sinh van ban tu mau, Guest tao van ban va cac luong AI nen.
Vai tro backend: File `api/serializers/chat.py` giu hoac ho tro luong backend cho chat, RAG, OCR, prefill ho so, sinh van ban, luu session va quan ly tri thuc AI.
Vai tro cua no trong frontend: Cac man `/chat`, `/rag`, `/ai-doc`, `/guest` va cac dialog AI phu tro phu thuoc vao ket qua ma file nay sinh ra.
Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `ai_engine.models`, `ai_engine.rag_engine`, `ai_engine.rag_index`, `ai_engine.doc_creator`, `accounts.models`.
Tac dung: Bao dam prompt, ket qua AI, session hoi thoai, du lieu trich xuat va chi muc RAG phuc vu dung ngu canh cua nguoi dung hien tai.
"""

from rest_framework import serializers
from ai_engine.models import ChatAudioAttachment, ChatSession, ChatMessage, KnowledgeBase

# class ChatAudioAttachmentSerializer là serializer định nghĩa dữ liệu vào/ra (ChatAudioAttachment).
# vd: serializer.data -> JSON cho frontend; is_valid() kiểm tra dữ liệu gửi lên.
class ChatAudioAttachmentSerializer(serializers.ModelSerializer):
    """
    Thuoc chuc nang nao: Tro ly AI, Hoi dap tai lieu, Sinh van ban tu mau, Guest tao van ban va cac luong AI nen.
    Vai tro backend: Lop `ChatAudioAttachmentSerializer` chuan hoa payload vao/ra va luat validate cua file `api/serializers/chat.py`.
    Vai tro cua no trong frontend: Frontend nhan hoac gui JSON qua serializer nay de du lieu hien thi va du lieu submit co cung cau truc voi backend mong doi.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `ai_engine.models`, `ai_engine.rag_engine`, `ai_engine.rag_index`, `ai_engine.doc_creator`, `accounts.models`. Nam trong pham vi module hien tai.
    Tac dung: Giam viec lap rule chuyen doi du lieu giua request, response va model lien quan toi `ChatAudioAttachmentSerializer`.
    """
    download_url = serializers.SerializerMethodField()
    session_id = serializers.IntegerField(source='session.id', read_only=True)
    session_title = serializers.CharField(source='session.title', read_only=True)
    message_id = serializers.IntegerField(source='message.id', read_only=True, allow_null=True)

    

    # class Meta khai báo metadata (fields, ordering, ràng buộc...) cho model/serializer.
    # vd: ordering=['-created_at'] -> bản ghi mới nhất lên đầu.
    class Meta:
        """
        Thuoc chuc nang nao: Tro ly AI, Hoi dap tai lieu, Sinh van ban tu mau, Guest tao van ban va cac luong AI nen.
        Vai tro backend: Lop `Meta` dong goi mot cum hanh vi hoac cau hinh backend cua file `api/serializers/chat.py`.
        Vai tro cua no trong frontend: Frontend khong goi truc tiep lop nay; cac endpoint hoac service cua cung tinh nang se su dung no de tao du lieu trinh bay hoac kiem soat luong xu ly.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `ai_engine.models`, `ai_engine.rag_engine`, `ai_engine.rag_index`, `ai_engine.doc_creator`, `accounts.models`. Nam trong pham vi cua `ChatAudioAttachmentSerializer` va cung dung chung ngu canh cua file nay.
        Tac dung: To chuc logic lien quan toi `Meta` thanh mot don vi ro rang de nhung ham khac goi lai de hon.
        """
        model = ChatAudioAttachment
        fields = (
            'id',
            'session_id',
            'session_title',
            'message_id',
            'title',
            'transcript',
            'mime_type',
            'duration_seconds',
            'download_url',
            'created_at',
        )

    

    # def get_download_url để lấy download url (trong serializer).
    # vd: nhận điều kiện -> trả về dữ liệu phù hợp.
    def get_download_url(self, obj):
        """
        Thuoc chuc nang nao: Tro ly AI, Hoi dap tai lieu, Sinh van ban tu mau, Guest tao van ban va cac luong AI nen.
        Vai tro backend: Ham `get_download_url` xu ly phan tra tep de frontend tai xuong cua serializer trong file `api/serializers/chat.py` trong lop `ChatAudioAttachmentSerializer`.
        Vai tro cua no trong frontend: Frontend khong goi ham nay truc tiep, nhung JSON ma giao dien gui hoac nhan se bi chi phoi boi buoc tra tep de frontend tai xuong nay.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `ai_engine.models`, `ai_engine.rag_engine`, `ai_engine.rag_index`, `ai_engine.doc_creator`, `accounts.models`. Nam trong lop `ChatAudioAttachmentSerializer` va phuc vu luong xu ly cua lop nay.
        Tac dung: Giu cho qua trinh tra tep de frontend tai xuong dien ra ngay tai serializer thay vi dan trai sang view hoac client.
        """
        request = self.context.get('request')
        if not request:
            return ''
        return request.build_absolute_uri(f'/api/assistant/audio/{obj.pk}/download/')

# class ChatMessageSerializer là serializer định nghĩa dữ liệu vào/ra (ChatMessage).
# vd: serializer.data -> JSON cho frontend; is_valid() kiểm tra dữ liệu gửi lên.
class ChatMessageSerializer(serializers.ModelSerializer):
    """
    Thuoc chuc nang nao: Tro ly AI, Hoi dap tai lieu, Sinh van ban tu mau, Guest tao van ban va cac luong AI nen.
    Vai tro backend: Lop `ChatMessageSerializer` chuan hoa payload vao/ra va luat validate cua file `api/serializers/chat.py`.
    Vai tro cua no trong frontend: Frontend nhan hoac gui JSON qua serializer nay de du lieu hien thi va du lieu submit co cung cau truc voi backend mong doi.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `ai_engine.models`, `ai_engine.rag_engine`, `ai_engine.rag_index`, `ai_engine.doc_creator`, `accounts.models`. Nam trong pham vi module hien tai.
    Tac dung: Giam viec lap rule chuyen doi du lieu giua request, response va model lien quan toi `ChatMessageSerializer`.
    """
    audio_attachments = ChatAudioAttachmentSerializer(many=True, read_only=True)

    

    # class Meta khai báo metadata (fields, ordering, ràng buộc...) cho model/serializer.
    # vd: ordering=['-created_at'] -> bản ghi mới nhất lên đầu.
    class Meta:
        """
        Thuoc chuc nang nao: Tro ly AI, Hoi dap tai lieu, Sinh van ban tu mau, Guest tao van ban va cac luong AI nen.
        Vai tro backend: Lop `Meta` dong goi mot cum hanh vi hoac cau hinh backend cua file `api/serializers/chat.py`.
        Vai tro cua no trong frontend: Frontend khong goi truc tiep lop nay; cac endpoint hoac service cua cung tinh nang se su dung no de tao du lieu trinh bay hoac kiem soat luong xu ly.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `ai_engine.models`, `ai_engine.rag_engine`, `ai_engine.rag_index`, `ai_engine.doc_creator`, `accounts.models`. Nam trong pham vi cua `ChatMessageSerializer` va cung dung chung ngu canh cua file nay.
        Tac dung: To chuc logic lien quan toi `Meta` thanh mot don vi ro rang de nhung ham khac goi lai de hon.
        """
        model = ChatMessage
        fields = ('id', 'role', 'content', 'citations', 'payload', 'audio_attachments', 'created_at')

# class ChatSessionSerializer là serializer định nghĩa dữ liệu vào/ra (ChatSession).
# vd: serializer.data -> JSON cho frontend; is_valid() kiểm tra dữ liệu gửi lên.
class ChatSessionSerializer(serializers.ModelSerializer):
    """
    Thuoc chuc nang nao: Tro ly AI, Hoi dap tai lieu, Sinh van ban tu mau, Guest tao van ban va cac luong AI nen.
    Vai tro backend: Lop `ChatSessionSerializer` chuan hoa payload vao/ra va luat validate cua file `api/serializers/chat.py`.
    Vai tro cua no trong frontend: Frontend nhan hoac gui JSON qua serializer nay de du lieu hien thi va du lieu submit co cung cau truc voi backend mong doi.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `ai_engine.models`, `ai_engine.rag_engine`, `ai_engine.rag_index`, `ai_engine.doc_creator`, `accounts.models`. Nam trong pham vi module hien tai.
    Tac dung: Giam viec lap rule chuyen doi du lieu giua request, response va model lien quan toi `ChatSessionSerializer`.
    """
    message_count = serializers.SerializerMethodField()
    audio_count = serializers.SerializerMethodField()

    

    # class Meta khai báo metadata (fields, ordering, ràng buộc...) cho model/serializer.
    # vd: ordering=['-created_at'] -> bản ghi mới nhất lên đầu.
    class Meta:
        """
        Thuoc chuc nang nao: Tro ly AI, Hoi dap tai lieu, Sinh van ban tu mau, Guest tao van ban va cac luong AI nen.
        Vai tro backend: Lop `Meta` dong goi mot cum hanh vi hoac cau hinh backend cua file `api/serializers/chat.py`.
        Vai tro cua no trong frontend: Frontend khong goi truc tiep lop nay; cac endpoint hoac service cua cung tinh nang se su dung no de tao du lieu trinh bay hoac kiem soat luong xu ly.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `ai_engine.models`, `ai_engine.rag_engine`, `ai_engine.rag_index`, `ai_engine.doc_creator`, `accounts.models`. Nam trong pham vi cua `ChatSessionSerializer` va cung dung chung ngu canh cua file nay.
        Tac dung: To chuc logic lien quan toi `Meta` thanh mot don vi ro rang de nhung ham khac goi lai de hon.
        """
        model = ChatSession
        fields = ('id', 'title', 'session_type', 'rag_mode', 'message_count', 'audio_count', 'created_at', 'updated_at')

    

    # def get_message_count để lấy message count (trong serializer).
    # vd: nhận đầu vào -> trả kết quả đã xử lý.
    def get_message_count(self, obj):
        """
        Thuoc chuc nang nao: Tro ly AI, Hoi dap tai lieu, Sinh van ban tu mau, Guest tao van ban va cac luong AI nen.
        Vai tro backend: Ham `get_message_count` xu ly phan dem so ban ghi hoac so muc theo dieu kien cua serializer trong file `api/serializers/chat.py` trong lop `ChatSessionSerializer`.
        Vai tro cua no trong frontend: Frontend khong goi ham nay truc tiep, nhung JSON ma giao dien gui hoac nhan se bi chi phoi boi buoc dem so ban ghi hoac so muc theo dieu kien nay.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `ai_engine.models`, `ai_engine.rag_engine`, `ai_engine.rag_index`, `ai_engine.doc_creator`, `accounts.models`. Phoi hop truc tiep voi cac method nhu `get_audio_count` trong cung lop.
        Tac dung: Giu cho qua trinh dem so ban ghi hoac so muc theo dieu kien dien ra ngay tai serializer thay vi dan trai sang view hoac client.
        """
        return obj.messages.count()

    

    # def get_audio_count để lấy audio count (trong serializer).
    # vd: nhận đầu vào -> trả kết quả đã xử lý.
    def get_audio_count(self, obj):
        """
        Thuoc chuc nang nao: Tro ly AI, Hoi dap tai lieu, Sinh van ban tu mau, Guest tao van ban va cac luong AI nen.
        Vai tro backend: Ham `get_audio_count` xu ly phan dem so ban ghi hoac so muc theo dieu kien cua serializer trong file `api/serializers/chat.py` trong lop `ChatSessionSerializer`.
        Vai tro cua no trong frontend: Frontend khong goi ham nay truc tiep, nhung JSON ma giao dien gui hoac nhan se bi chi phoi boi buoc dem so ban ghi hoac so muc theo dieu kien nay.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `ai_engine.models`, `ai_engine.rag_engine`, `ai_engine.rag_index`, `ai_engine.doc_creator`, `accounts.models`. Phoi hop truc tiep voi cac method nhu `get_message_count` trong cung lop.
        Tac dung: Giu cho qua trinh dem so ban ghi hoac so muc theo dieu kien dien ra ngay tai serializer thay vi dan trai sang view hoac client.
        """
        return obj.audio_attachments.count()

# class KnowledgeBaseSerializer là serializer định nghĩa dữ liệu vào/ra (KnowledgeBase).
# vd: serializer.data -> JSON cho frontend; is_valid() kiểm tra dữ liệu gửi lên.
class KnowledgeBaseSerializer(serializers.ModelSerializer):
    """
    Thuoc chuc nang nao: Tro ly AI, Hoi dap tai lieu, Sinh van ban tu mau, Guest tao van ban va cac luong AI nen.
    Vai tro backend: Lop `KnowledgeBaseSerializer` chuan hoa payload vao/ra va luat validate cua file `api/serializers/chat.py`.
    Vai tro cua no trong frontend: Frontend nhan hoac gui JSON qua serializer nay de du lieu hien thi va du lieu submit co cung cau truc voi backend mong doi.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `ai_engine.models`, `ai_engine.rag_engine`, `ai_engine.rag_index`, `ai_engine.doc_creator`, `accounts.models`. Nam trong pham vi module hien tai.
    Tac dung: Giam viec lap rule chuyen doi du lieu giua request, response va model lien quan toi `KnowledgeBaseSerializer`.
    """
    owner_name = serializers.SerializerMethodField()

    

    # class Meta khai báo metadata (fields, ordering, ràng buộc...) cho model/serializer.
    # vd: ordering=['-created_at'] -> bản ghi mới nhất lên đầu.
    class Meta:
        """
        Thuoc chuc nang nao: Tro ly AI, Hoi dap tai lieu, Sinh van ban tu mau, Guest tao van ban va cac luong AI nen.
        Vai tro backend: Lop `Meta` dong goi mot cum hanh vi hoac cau hinh backend cua file `api/serializers/chat.py`.
        Vai tro cua no trong frontend: Frontend khong goi truc tiep lop nay; cac endpoint hoac service cua cung tinh nang se su dung no de tao du lieu trinh bay hoac kiem soat luong xu ly.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `ai_engine.models`, `ai_engine.rag_engine`, `ai_engine.rag_index`, `ai_engine.doc_creator`, `accounts.models`. Nam trong pham vi cua `KnowledgeBaseSerializer` va cung dung chung ngu canh cua file nay.
        Tac dung: To chuc logic lien quan toi `Meta` thanh mot don vi ro rang de nhung ham khac goi lai de hon.
        """
        model = KnowledgeBase
        fields = ('id', 'title', 'source_type', 'is_shared', 'owner_name', 'created_at')

    

    # def get_owner_name để lấy owner name (trong serializer).
    # vd: nhận điều kiện -> trả về dữ liệu phù hợp.
    def get_owner_name(self, obj):
        """
        Thuoc chuc nang nao: Tro ly AI, Hoi dap tai lieu, Sinh van ban tu mau, Guest tao van ban va cac luong AI nen.
        Vai tro backend: Ham `get_owner_name` xu ly phan thuc hien phan xu ly chuyen trach cua symbol hien tai cua serializer trong file `api/serializers/chat.py` trong lop `KnowledgeBaseSerializer`.
        Vai tro cua no trong frontend: Frontend khong goi ham nay truc tiep, nhung JSON ma giao dien gui hoac nhan se bi chi phoi boi buoc thuc hien phan xu ly chuyen trach cua symbol hien tai nay.
        Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `ai_engine.models`, `ai_engine.rag_engine`, `ai_engine.rag_index`, `ai_engine.doc_creator`, `accounts.models`. Nam trong lop `KnowledgeBaseSerializer` va phuc vu luong xu ly cua lop nay.
        Tac dung: Giu cho qua trinh thuc hien phan xu ly chuyen trach cua symbol hien tai dien ra ngay tai serializer thay vi dan trai sang view hoac client.
        """
        return obj.owner.get_full_name() or obj.owner.username
