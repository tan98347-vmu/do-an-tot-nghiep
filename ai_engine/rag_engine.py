"""
  rag_index.py
  = Người xây và bảo trì thư viện vector

  rag_search.py
  = Người tìm đúng sách và đúng đoạn trong thư viện

  rag_engine.py
  = Người đưa các đoạn đó cho LLM và yêu cầu LLM trả lời



rag_engine.py là gì?

  ai_engine/rag_engine.py:1 là cổng trung tâm kết nối các chức năng AI với LLM, embedding và hệ thống RAG.

  Bản chất:

  > Các file khác không tự tạo ChatOllama, OllamaEmbeddings hay tự xây prompt RAG. Chúng gọi các hàm dùng chung trong rag_engine.py.

  ## Vai trò trong hệ thống

  ChatAI / Trợ lý AI / RAG / AI Document
                      ↓
                rag_engine.py
                      ↓
         Ollama LLM + Embedding + PGVector

  Nó phục vụ nhiều giao diện:

  - /chat/text, /chat/voice: cung cấp LLM và RAG cho Assistant.
  - /rag: hỏi đáp mẫu hoặc văn bản.
  - /ai-doc: gọi LLM, trích PDF và điền dữ liệu.
  - Tóm tắt văn bản, Word AI và một số chức năng AI khác.

   rag_engine.py có ba trọng trách chính:

  1. Cung cấp LLM và embedding dùng chung cho toàn hệ thống.
  2. Trích xuất dữ liệu đầu vào, đặc biệt là PDF.
  3. Điều phối hỏi đáp RAG bằng cách lấy tài liệu liên quan, xây prompt, gọi LLM và trả citations.

   Vì vậy, bản chất chính xác:

  rag_engine.py
  ├── LLM provider dùng chung
  ├── Embedding provider
  ├── PDF/OCR helper
  ├── KnowledgeBase vector store cũ
  └── RAG answer orchestration

  Có thể nói tên phù hợp hơn về mặt kiến trúc sẽ là ai_runtime.py, llm_service.py hoặc tách thành:
"""

import re
import threading
import time as _time
import urllib.parse
from collections import OrderedDict

import pdfplumber
from django.conf import settings
from langchain_community.vectorstores import PGVector
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_ollama import ChatOllama, OllamaEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

from .rag_index import (
    DOCUMENT_RAG_COLLECTION,
    TEMPLATE_RAG_COLLECTION,
    purge_document_index,
    purge_template_index,
    sync_document_index,
    sync_template_index,
)
from .rag_search import _db_search_documents, _db_search_templates

_OLLAMA_TIMEOUT_SECONDS = max(
    int(getattr(settings, 'AI_REQUEST_TIMEOUT_SECONDS', 1200) or 1200),
    1200,
)

import logging as _logging
_pdf_logger = _logging.getLogger('ai_engine')

# def _ollama_client_kwargs để tạo dict cấu hình client cho Ollama (chủ yếu là timeout), dùng chung cho embeddings và LLM.
# vd: -> {'timeout': 600} truyền cho ChatOllama/OllamaEmbeddings.
def _ollama_client_kwargs():
    """
    Thuoc chuc nang nao: Tro ly AI, Hoi dap tai lieu, Sinh van ban tu mau, Guest tao van ban va cac luong AI nen.
    Vai tro backend: Ham `_ollama_client_kwargs` la helper noi bo trong file `ai_engine/rag_engine.py`, chiu trach nhiem thuc hien phan xu ly chuyen trach cua symbol hien tai trong mot luong backend nhieu buoc.
    Vai tro cua no trong frontend: Frontend hiem khi goi truc tiep ham kieu nay; endpoint, command hoac signal se goi no khi can thuc hien phan xu ly chuyen trach cua symbol hien tai roi moi phan anh ket qua len man hinh.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `ai_engine.models`, `ai_engine.rag_engine`, `ai_engine.rag_index`, `ai_engine.doc_creator`, `accounts.models`. Thuong duoc cac ham public nhu `get_embeddings`, `get_llm`, `get_collection_name` goi lai.
    Tac dung: Don buoc thuc hien phan xu ly chuyen trach cua symbol hien tai xuong service hoac engine de view khong phai tu trien khai lai logic ky thuat.
    """
    return {'timeout': _OLLAMA_TIMEOUT_SECONDS}

# def _record_ai_usage để ghi một dòng AIUsageLog (user, model, trạng thái success/error) cho mỗi lần gọi AI; nuốt lỗi để việc log không ảnh hưởng luồng chính.
# vd: gọi LLM lỗi -> ghi AIUsageLog(status='error') để theo dõi.
def _record_ai_usage(user=None, model=None, status='success'):
    """
    Thuoc chuc nang nao: Tro ly AI, Hoi dap tai lieu, Sinh van ban tu mau, Guest tao van ban va cac luong AI nen.
    Vai tro backend: Ham `_record_ai_usage` la helper noi bo trong file `ai_engine/rag_engine.py`, chiu trach nhiem thuc hien phan xu ly chuyen trach cua symbol hien tai trong mot luong backend nhieu buoc.
    Vai tro cua no trong frontend: Frontend hiem khi goi truc tiep ham kieu nay; endpoint, command hoac signal se goi no khi can thuc hien phan xu ly chuyen trach cua symbol hien tai roi moi phan anh ket qua len man hinh.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `ai_engine.models`, `ai_engine.rag_engine`, `ai_engine.rag_index`, `ai_engine.doc_creator`, `accounts.models`. Thuong duoc cac ham public nhu `get_embeddings`, `get_llm`, `get_collection_name` goi lai.
    Tac dung: Don buoc thuc hien phan xu ly chuyen trach cua symbol hien tai xuong service hoac engine de view khong phai tu trien khai lai logic ky thuat.
    """
    try:
        from ai_engine.models import AIUsageLog

        log_user = user if getattr(user, 'is_authenticated', False) else None
        AIUsageLog.objects.create(
            user=log_user,
            model_name=str(model or '')[:120],
            status=status,
        )
    except Exception:
        pass

# def _truncate_llm_debug_text để rút gọn văn bản về 1 dòng và tối đa `limit` ký tự cho log debug LLM.
# vd: prompt 5000 ký tự -> log chỉ 180 ký tự đầu + '...'.
def _truncate_llm_debug_text(value, *, limit=180):
    """
    Thuoc chuc nang nao: Tro ly AI, Hoi dap tai lieu, Sinh van ban tu mau, Guest tao van ban va cac luong AI nen.
    Vai tro backend: Ham `_truncate_llm_debug_text` la helper noi bo trong file `ai_engine/rag_engine.py`, chiu trach nhiem thuc hien phan xu ly chuyen trach cua symbol hien tai trong mot luong backend nhieu buoc.
    Vai tro cua no trong frontend: Frontend hiem khi goi truc tiep ham kieu nay; endpoint, command hoac signal se goi no khi can thuc hien phan xu ly chuyen trach cua symbol hien tai roi moi phan anh ket qua len man hinh.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `ai_engine.models`, `ai_engine.rag_engine`, `ai_engine.rag_index`, `ai_engine.doc_creator`, `accounts.models`. Thuong duoc cac ham public nhu `get_embeddings`, `get_llm`, `get_collection_name` goi lai.
    Tac dung: Don buoc thuc hien phan xu ly chuyen trach cua symbol hien tai xuong service hoac engine de view khong phai tu trien khai lai logic ky thuat.
    """
    text = str(value or '')
    text = ' '.join(text.replace('\r', ' ').replace('\n', ' ').split())
    if len(text) <= limit:
        return text
    return f'{text[:limit]}...'

# def _summarize_llm_payload để tóm tắt danh sách message gửi LLM (số message, tổng ký tự, preview vài cái đầu) phục vụ log.
# vd: nếu payload là một list có 3 message (SystemMessage, HumanMessage, AIMessage) với content lần lượt là "You are a helpful assistant.", "What is the capital of France?", "The capital of France is Paris.", thì kết quả của hàm sẽ là {'message_count': 3, 'total_chars': 79, 'preview': 'SystemMessage:You are a helpful assistant. || HumanMessage:What is the capital of France? || AIMessage:The capital of France is Paris.'}, giúp log có cái nhìn nhanh về nội dung và kích thước của payload gửi đến LLM mà không cần in ra toàn bộ nội dung có thể rất dài.
def _summarize_llm_payload(payload):

    messages = payload if isinstance(payload, (list, tuple)) else [payload]
    total_chars = 0
    previews = []
    for item in messages:
        content = getattr(item, 'content', item)
        if isinstance(content, list):
            content = ' '.join(str(part) for part in content)
        text = str(content or '')
        total_chars += len(text)
        previews.append(f'{type(item).__name__}:{_truncate_llm_debug_text(text, limit=80)}')
    return {
        'message_count': len(messages),
        'total_chars': total_chars,
        'preview': ' || '.join(previews[:3]),
    }

# =============================================================================
# LLM client cache: reuse ChatOllama (and its httpx.Client connection pool)
# across requests so we don't pay TLS handshake on every chat / voice turn.
# Key = (model, base_url, temperature, timeout). Streaming callback is NOT
# part of the key — it's bound per call via _TrackedChatOllama.invoke().
# =============================================================================
_LLM_CACHE_MAX = 32
_llm_client_cache: 'OrderedDict[tuple, ChatOllama]' = OrderedDict()
_llm_cache_lock = threading.Lock()


# def _llm_cache_key để tạo khóa cache cho client LLM theo (model, base_url, temperature, timeout).
# vd: -> ('kimi-k2.6:cloud','http://...:11434',0.0,600).
def _llm_cache_key(model, base_url, temperature, timeout):
    return (
        str(model or ''),
        str(base_url or ''),
        round(float(temperature or 0.0), 4),
        int(timeout or 0),
    )


# def _get_cached_chat_ollama để tái sử dụng client ChatOllama theo khóa cache (giữ connection pool, tránh handshake TLS mỗi lượt); tạo mới nếu chưa có và giới hạn kích thước cache kiểu LRU.
# vd: 2 lượt chat cùng model/temperature -> dùng lại 1 client, không bắt tay TLS lần 2.
def _get_cached_chat_ollama(model, base_url, temperature, timeout):
    key = _llm_cache_key(model, base_url, temperature, timeout)
    with _llm_cache_lock:
        cached = _llm_client_cache.get(key)
        if cached is not None:
            _llm_client_cache.move_to_end(key)
            return cached
        if len(_llm_client_cache) >= _LLM_CACHE_MAX:
            try:
                _llm_client_cache.popitem(last=False)
            except KeyError:
                pass
        client_kwargs = {'timeout': timeout}
        llm = ChatOllama(
            model=model,
            temperature=temperature,
            base_url=base_url,
            streaming=True,
            client_kwargs=client_kwargs,
            async_client_kwargs=client_kwargs,
            sync_client_kwargs=client_kwargs,
        )
        _llm_client_cache[key] = llm
        _pdf_logger.info(
            '[llm.cache] new client | model=%s | temp=%s | cache_size=%d',
            model, temperature, len(_llm_client_cache),
        )
        return llm


# def flush_llm_cache để xóa toàn bộ client LLM đã cache (hữu ích sau khi đổi cấu hình hoặc hot reload).
# vd: sau khi đổi DEFAULT_AI_MODEL -> gọi flush để lần sau tạo client mới.
def flush_llm_cache():
    """Drop cached LLM clients (useful after config change / hot reload)."""
    with _llm_cache_lock:
        _llm_client_cache.clear()


# def _looks_like_cloud_model để nhận biết model có phải bản cloud không (tên kết thúc '-cloud' hoặc chứa ':cloud').
# vd: 'kimi-k2.6:cloud' -> True; 'llama3' -> False.
def _looks_like_cloud_model(model_name):
    """
    Thuoc chuc nang nao: Tro ly AI, Hoi dap tai lieu, Sinh van ban tu mau, Guest tao van ban va cac luong AI nen.
    Vai tro backend: Ham `_looks_like_cloud_model` la helper noi bo trong file `ai_engine/rag_engine.py`, chiu trach nhiem thuc hien phan xu ly chuyen trach cua symbol hien tai trong mot luong backend nhieu buoc.
    Vai tro cua no trong frontend: Frontend hiem khi goi truc tiep ham kieu nay; endpoint, command hoac signal se goi no khi can thuc hien phan xu ly chuyen trach cua symbol hien tai roi moi phan anh ket qua len man hinh.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `ai_engine.models`, `ai_engine.rag_engine`, `ai_engine.rag_index`, `ai_engine.doc_creator`, `accounts.models`. Thuong duoc cac ham public nhu `get_embeddings`, `get_llm`, `get_collection_name` goi lai.
    Tac dung: Don buoc thuc hien phan xu ly chuyen trach cua symbol hien tai xuong service hoac engine de view khong phai tu trien khai lai logic ky thuat.
    """
    lowered = str(model_name or '').strip().lower()
    if not lowered:
        return False
    return lowered.endswith('-cloud') or ':cloud' in lowered

# class _TrackedChatOllama là lớp bọc quanh ChatOllama để ghi log + AIUsageLog mỗi lần invoke và gắn streaming_callback theo từng lần gọi; các thuộc tính khác ủy quyền cho LLM gốc.
# vd: bọc ChatOllama để mỗi .invoke() đều log thời gian và ghi AIUsageLog.
class _TrackedChatOllama:
    

    """
    Thuoc chuc nang nao: Tro ly AI, Hoi dap tai lieu, Sinh van ban tu mau, Guest tao van ban va cac luong AI nen.
    Vai tro backend: Lop `_TrackedChatOllama` dong goi mot cum hanh vi hoac cau hinh backend cua file `ai_engine/rag_engine.py`.
    Vai tro cua no trong frontend: Frontend khong goi truc tiep lop nay; cac endpoint hoac service cua cung tinh nang se su dung no de tao du lieu trinh bay hoac kiem soat luong xu ly.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `ai_engine.models`, `ai_engine.rag_engine`, `ai_engine.rag_index`, `ai_engine.doc_creator`, `accounts.models`. Nam trong pham vi module hien tai.
    Tac dung: To chuc logic lien quan toi `_TrackedChatOllama` thanh mot don vi ro rang de nhung ham khac goi lai de hon.
    """
    # def __init__ để lưu LLM gốc cùng user, tên model và streaming_callback dùng cho lần gọi.
    # vd: _TrackedChatOllama(llm, user=u, model='kimi...', streaming_callback=cb).
    def __init__(self, llm, user=None, model=None, streaming_callback=None):
        """Wrapper logging + record usage. streaming_callback ban per-call qua config."""
        self._llm = llm
        self._user = user
        self._model = model
        self._streaming_callback = streaming_callback

    

    # def invoke để gọi LLM gốc: gắn streaming handler nếu có callback, đo thời gian, ghi log + AIUsageLog (success/error) rồi trả response (hoặc ném lại lỗi).
    # vd: invoke(messages) -> response; thành công ghi success, lỗi ghi error rồi ném lại.
    def invoke(self, *args, **kwargs):
 
        invocation_id = hex(_time.time_ns())[-8:]
        started_at = _time.perf_counter()
        payload = args[0] if args else None
        payload_stats = _summarize_llm_payload(payload)
        _pdf_logger.debug(
            '[llm.invoke] start | id=%s | model=%s | user_id=%s | message_count=%s | total_chars=%s | preview=%s',
            invocation_id,
            self._model,
            getattr(self._user, 'id', None),
            payload_stats['message_count'],
            payload_stats['total_chars'],
            payload_stats['preview'],
        )
        if self._streaming_callback is not None:
            try:
                from ai_tasks.services.streaming import StreamingHandler
                handler = StreamingHandler(on_token=self._streaming_callback)
                existing_cfg = kwargs.get('config') or {}
                if not isinstance(existing_cfg, dict):
                    existing_cfg = {}
                merged_cb = list(existing_cfg.get('callbacks') or [])
                merged_cb.append(handler)
                new_cfg = dict(existing_cfg)
                new_cfg['callbacks'] = merged_cb
                kwargs['config'] = new_cfg
            except Exception:
                _pdf_logger.exception('[llm.invoke] streaming callback bind failed')
        try:
            response = self._llm.invoke(*args, **kwargs)
            _record_ai_usage(self._user, self._model, status='success')
            elapsed_ms = (_time.perf_counter() - started_at) * 1000
            response_text = getattr(response, 'content', '') or ''
            _pdf_logger.debug(
                '[llm.invoke] done | id=%s | model=%s | elapsed_ms=%.0f | response_chars=%s | response_preview=%s',
                invocation_id,
                self._model,
                elapsed_ms,
                len(response_text),
                _truncate_llm_debug_text(response_text, limit=240),
            )
            return response
        except Exception as exc:
            _record_ai_usage(self._user, self._model, status='error')
            elapsed_ms = (_time.perf_counter() - started_at) * 1000
            _pdf_logger.exception(
                '[llm.invoke] error | id=%s | model=%s | elapsed_ms=%.0f | error=%s',
                invocation_id,
                self._model,
                elapsed_ms,
                exc,
            )
            raise

    

    # def __getattr__ để ủy quyền mọi thuộc tính/phương thức không định nghĩa ở wrapper xuống LLM gốc.
    # vd: wrapper.bind_tools(...) -> tự gọi sang llm gốc.bind_tools(...).
    def __getattr__(self, name):

        return getattr(self._llm, name)

# def get_embeddings để tạo OllamaEmbeddings theo model embedding của cấu hình AI (theo user/công ty).
# vd: get_embeddings(user) -> OllamaEmbeddings(model='mxbai-embed-large').
def get_embeddings(user=None):
    """
    Thuoc chuc nang nao: Tro ly AI, Hoi dap tai lieu, Sinh van ban tu mau, Guest tao van ban va cac luong AI nen.
    Vai tro backend: Ham `get_embeddings` la ham nghiep vu chinh trong file `ai_engine/rag_engine.py`, chiu trach nhiem thuc hien phan xu ly chuyen trach cua symbol hien tai trong mot luong backend nhieu buoc.
    Vai tro cua no trong frontend: Frontend hiem khi goi truc tiep ham kieu nay; endpoint, command hoac signal se goi no khi can thuc hien phan xu ly chuyen trach cua symbol hien tai roi moi phan anh ket qua len man hinh.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `ai_engine.models`, `ai_engine.rag_engine`, `ai_engine.rag_index`, `ai_engine.doc_creator`, `accounts.models`. Dung cung cap voi cac ham `_ollama_client_kwargs`, `_record_ai_usage`, `_truncate_llm_debug_text` trong module nay.
    Tac dung: Don buoc thuc hien phan xu ly chuyen trach cua symbol hien tai xuong service hoac engine de view khong phai tu trien khai lai logic ky thuat.
    """
    from accounts.tenancy import build_effective_ai_context, resolve_ai_config

    model = resolve_ai_config(user=user).embedding_model
    return OllamaEmbeddings(
        model=model,
        base_url=settings.OLLAMA_BASE_URL,
        client_kwargs=_ollama_client_kwargs(),
        async_client_kwargs=_ollama_client_kwargs(),
        sync_client_kwargs=_ollama_client_kwargs(),
    )

# def get_llm để lấy LLM dùng chung: chọn model/temperature theo cấu hình (cho phép override), hạ về model mặc định nếu model cloud bị cấm, lấy client từ cache rồi bọc _TrackedChatOllama (kèm streaming_callback).
# vd: get_llm(user, temperature_override=0) -> client LLM đã cache, bọc tracking.
def get_llm(user=None, model_override=None, temperature_override=None, allow_cloud_model=True,
            streaming_callback=None):
    """
    Thuoc chuc nang nao: Tro ly AI, Hoi dap tai lieu, Sinh van ban tu mau, Guest tao van ban va cac luong AI nen.
    Vai tro backend: Ham `get_llm` la ham nghiep vu chinh trong file `ai_engine/rag_engine.py`, chiu trach nhiem thuc hien phan xu ly chuyen trach cua symbol hien tai trong mot luong backend nhieu buoc.
    Vai tro cua no trong frontend: Frontend hiem khi goi truc tiep ham kieu nay; endpoint, command hoac signal se goi no khi can thuc hien phan xu ly chuyen trach cua symbol hien tai roi moi phan anh ket qua len man hinh.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `ai_engine.models`, `ai_engine.rag_engine`, `ai_engine.rag_index`, `ai_engine.doc_creator`, `accounts.models`. Dung cung cap voi cac ham `_ollama_client_kwargs`, `_record_ai_usage`, `_truncate_llm_debug_text` trong module nay.
    Tac dung: Don buoc thuc hien phan xu ly chuyen trach cua symbol hien tai xuong service hoac engine de view khong phai tu trien khai lai logic ky thuat.
    """
    from accounts.tenancy import build_effective_ai_context, resolve_ai_config

    cfg = resolve_ai_config(user=user)
    model = model_override or cfg.ai_model
    temperature = cfg.ai_temperature if temperature_override is None else float(temperature_override)
    routed_via = f'ChatOllama({settings.OLLAMA_BASE_URL})'
    if _looks_like_cloud_model(model) and not allow_cloud_model:
        fallback_model = getattr(settings, 'DEFAULT_AI_MODEL', 'kimi-k2.6:cloud')
        _pdf_logger.warning(
            '[llm.get] cloud_named_model_detected | requested=%s | fallback=%s | routed_via=%s',
            model,
            fallback_model,
            routed_via,
        )
        model = fallback_model
    _pdf_logger.debug(
        '[llm.get] select | user_id=%s | model=%s | temperature=%s | routed_via=%s | override_model=%s | override_temp=%s',
        getattr(user, 'id', None),
        model,
        temperature,
        routed_via,
        bool(model_override),
        temperature_override is not None,
    )
    base_url = settings.OLLAMA_BASE_URL
    timeout = _OLLAMA_TIMEOUT_SECONDS
    llm = _get_cached_chat_ollama(model, base_url, temperature, timeout)
    return _TrackedChatOllama(
        llm,
        user=user,
        model=model,
        streaming_callback=streaming_callback,
    )

# def get_collection_name để sinh tên collection vector theo công ty + user (hoặc shared), phục vụ cô lập tri thức theo công ty/người dùng.
# vd: nếu user có id=5 thuộc company id=2, thì get_collection_name(user) sẽ trả về 'company_2_user_5_kb'; nếu shared=True và company id=2, sẽ trả về 'company_2_shared_kb'; nếu không có user và shared=False, sẽ trả về 'shared_kb'. Cách đặt tên này giúp phân tách dữ liệu vector theo công ty và người dùng một cách rõ ràng trong PGVector.
def get_collection_name(user=None, shared=False):
    """
    Thuoc chuc nang nao: Tro ly AI, Hoi dap tai lieu, Sinh van ban tu mau, Guest tao van ban va cac luong AI nen.
    Vai tro backend: Ham `get_collection_name` la ham nghiep vu chinh trong file `ai_engine/rag_engine.py`, chiu trach nhiem thuc hien phan xu ly chuyen trach cua symbol hien tai trong mot luong backend nhieu buoc.
    Vai tro cua no trong frontend: Frontend hiem khi goi truc tiep ham kieu nay; endpoint, command hoac signal se goi no khi can thuc hien phan xu ly chuyen trach cua symbol hien tai roi moi phan anh ket qua len man hinh.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `ai_engine.models`, `ai_engine.rag_engine`, `ai_engine.rag_index`, `ai_engine.doc_creator`, `accounts.models`. Dung cung cap voi cac ham `_ollama_client_kwargs`, `_record_ai_usage`, `_truncate_llm_debug_text` trong module nay.
    Tac dung: Don buoc thuc hien phan xu ly chuyen trach cua symbol hien tai xuong service hoac engine de view khong phai tu trien khai lai logic ky thuat.
    """
    from accounts.tenancy import get_user_company

    company = get_user_company(user) if user is not None else None
    company_prefix = f'company_{company.id}_' if company is not None else ''
    if shared:
        return f'{company_prefix}shared_kb' if company_prefix else 'shared_kb'
    if user:
        return f'{company_prefix}user_{user.id}_kb' if company_prefix else f'user_{user.id}_kb'
    return 'shared_kb'

# def get_vectorstore để tạo PGVector trỏ vào đúng collection (theo user/shared) với hàm embedding tương ứng.
# vd: nếu user có id=5 thuộc company id=2 và shared=False, get_vectorstore(user) sẽ tạo PGVector với collection_name='company_2_user_5_kb' và embedding_function là OllamaEmbeddings theo cấu hình của user đó; nếu shared=True và company id=2, sẽ tạo PGVector với collection_name='company_2_shared_kb'; nếu không có user và shared=False, sẽ tạo PGVector với collection_name='shared_kb'. Điều này đảm bảo rằng dữ liệu vector được lưu trữ và truy vấn đúng theo phạm vi người dùng hoặc chia sẻ trong hệ thống RAG.
def get_vectorstore(user=None, shared=False):
    """
    Thuoc chuc nang nao: Tro ly AI, Hoi dap tai lieu, Sinh van ban tu mau, Guest tao van ban va cac luong AI nen.
    Vai tro backend: Ham `get_vectorstore` la ham nghiep vu chinh trong file `ai_engine/rag_engine.py`, chiu trach nhiem thuc hien phan xu ly chuyen trach cua symbol hien tai trong mot luong backend nhieu buoc.
    Vai tro cua no trong frontend: Frontend hiem khi goi truc tiep ham kieu nay; endpoint, command hoac signal se goi no khi can thuc hien phan xu ly chuyen trach cua symbol hien tai roi moi phan anh ket qua len man hinh.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `ai_engine.models`, `ai_engine.rag_engine`, `ai_engine.rag_index`, `ai_engine.doc_creator`, `accounts.models`. Dung cung cap voi cac ham `_ollama_client_kwargs`, `_record_ai_usage`, `_truncate_llm_debug_text` trong module nay.
    Tac dung: Don buoc thuc hien phan xu ly chuyen trach cua symbol hien tai xuong service hoac engine de view khong phai tu trien khai lai logic ky thuat.
    """
    collection_name = get_collection_name(user, shared)
    return PGVector(
        collection_name=collection_name,
        connection_string=settings.PGVECTOR_CONNECTION_STRING,
        embedding_function=get_embeddings(user),
    )

# def _emit_task_progress để gọi callback báo tiến độ (phần trăm, bước, chi tiết) nếu có; nuốt lỗi để không làm hỏng tác vụ.
# vd: _emit_task_progress(cb, 40, 'OCR', 'trang 2/5') -> đẩy 40% cho UI.
def _emit_task_progress(callback, percent, stage, detail=''):
    if callback is None:
        return
    try:
        callback(percent, stage, detail)
    except Exception:
        pass


# def _run_cancel_check để gọi callback kiểm tra hủy (nếu có), cho phép dừng giữa chừng các tác vụ dài như OCR/extract.
# vd: người dùng bấm Dừng -> callback ném lỗi để thoát vòng OCR giữa chừng.
def _run_cancel_check(callback):
    if callback is None:
        return
    callback()


# def _ocr_pdf để OCR file PDF scan bằng Tesseract (render từng trang qua PyMuPDF rồi nhận dạng vie+eng), có báo tiến độ và kiểm tra hủy; trả text ghép các trang.
# vd: PDF scan 3 trang -> render 300DPI rồi Tesseract vie+eng, ghép text 3 trang.
def _ocr_pdf(pdf_file, *, on_progress=None, cancel_check=None) -> str:
    """
    Thuoc chuc nang nao: Tro ly AI, Hoi dap tai lieu, Sinh van ban tu mau, Guest tao van ban va cac luong AI nen.
    Vai tro backend: Ham `_ocr_pdf` la helper noi bo trong file `ai_engine/rag_engine.py`, chiu trach nhiem thuc hien phan xu ly chuyen trach cua symbol hien tai trong mot luong backend nhieu buoc.
    Vai tro cua no trong frontend: Frontend hiem khi goi truc tiep ham kieu nay; endpoint, command hoac signal se goi no khi can thuc hien phan xu ly chuyen trach cua symbol hien tai roi moi phan anh ket qua len man hinh.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `ai_engine.models`, `ai_engine.rag_engine`, `ai_engine.rag_index`, `ai_engine.doc_creator`, `accounts.models`. Thuong duoc cac ham public nhu `get_embeddings`, `get_llm`, `get_collection_name` goi lai.
    Tac dung: Don buoc thuc hien phan xu ly chuyen trach cua symbol hien tai xuong service hoac engine de view khong phai tu trien khai lai logic ky thuat.
    """
    import io

    import fitz
    import pytesseract
    from PIL import Image
    from django.conf import settings as _settings

    tesseract_cmd = getattr(_settings, 'TESSERACT_CMD', None)
    if tesseract_cmd:
        pytesseract.pytesseract.tesseract_cmd = tesseract_cmd

    if hasattr(pdf_file, 'seek'):
        pdf_file.seek(0)
    if hasattr(pdf_file, 'read'):
        pdf_bytes = pdf_file.read()
    else:
        with open(pdf_file, 'rb') as handle:
            pdf_bytes = handle.read()

    document = fitz.open(stream=pdf_bytes, filetype='pdf')
    pages = []
    total_pages = max(int(getattr(document, 'page_count', 0) or 0), 1)
    for index, page in enumerate(document, start=1):
        _run_cancel_check(cancel_check)
        progress = 40 + int(18 * index / total_pages)
        _emit_task_progress(
            on_progress,
            progress,
            'Tesseract OCR',
            f'OCR trang {index}/{total_pages}',
        )
        pixmap = page.get_pixmap(matrix=fitz.Matrix(300 / 72, 300 / 72))
        image = Image.open(io.BytesIO(pixmap.tobytes('png')))
        page_text = pytesseract.image_to_string(image, lang='vie+eng')
        if page_text.strip():
            pages.append(page_text)
        _run_cancel_check(cancel_check)
    document.close()
    return '\n'.join(pages)

# def extract_pdf_text để trích text PDF: ưu tiên pdfplumber (PDF có sẵn text), nếu rỗng thì fallback OCR (_ocr_pdf); trả chuỗi rỗng nếu cả hai đều không ra.
# vd: PDF có text -> pdfplumber; PDF scan -> tự chuyển sang OCR.
def extract_pdf_text(pdf_file, *, on_progress=None, cancel_check=None) -> str:
    """
    Thuoc chuc nang nao: Tro ly AI, Hoi dap tai lieu, Sinh van ban tu mau, Guest tao van ban va cac luong AI nen.
    Vai tro backend: Ham `extract_pdf_text` la ham nghiep vu chinh trong file `ai_engine/rag_engine.py`, chiu trach nhiem trich xuat noi dung hoac gia tri trung gian trong mot luong backend nhieu buoc.
    Vai tro cua no trong frontend: Frontend hiem khi goi truc tiep ham kieu nay; endpoint, command hoac signal se goi no khi can trich xuat noi dung hoac gia tri trung gian roi moi phan anh ket qua len man hinh.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `ai_engine.models`, `ai_engine.rag_engine`, `ai_engine.rag_index`, `ai_engine.doc_creator`, `accounts.models`. Dung cung cap voi cac ham `_ollama_client_kwargs`, `_record_ai_usage`, `_truncate_llm_debug_text` trong module nay.
    Tac dung: Don buoc trich xuat noi dung hoac gia tri trung gian xuong service hoac engine de view khong phai tu trien khai lai logic ky thuat.
    """
    text = ''
    try:
        with pdfplumber.open(pdf_file) as pdf:
            total_pages = max(len(pdf.pages), 1)
            for index, page in enumerate(pdf.pages, start=1):
                _run_cancel_check(cancel_check)
                progress = 20 + int(15 * index / total_pages)
                _emit_task_progress(
                    on_progress,
                    progress,
                    'pdfplumber extract',
                    f'Trang {index}/{total_pages}',
                )
                page_text = page.extract_text()
                if page_text:
                    text += page_text + '\n'
                _run_cancel_check(cancel_check)
    except Exception as exc:
        _pdf_logger.warning('[extract_pdf_text] pdfplumber error: %s', exc)

    if text.strip():
        _pdf_logger.debug('[extract_pdf_text] pdfplumber OK: %d chars', len(text))
        return text

    _pdf_logger.info('[extract_pdf_text] pdfplumber returned empty -> trying OCR')
    try:
        _emit_task_progress(on_progress, 40, 'Tesseract OCR', 'Khoi dong OCR')
        _run_cancel_check(cancel_check)
        ocr_text = _ocr_pdf(
            pdf_file,
            on_progress=on_progress,
            cancel_check=cancel_check,
        )
        if ocr_text.strip():
            _pdf_logger.info('[extract_pdf_text] OCR OK: %d chars', len(ocr_text))
            return ocr_text
        _pdf_logger.warning('[extract_pdf_text] OCR returned empty')
        return ''
    except ImportError as exc:
        _pdf_logger.warning('[extract_pdf_text] OCR unavailable: %s', exc)
        return ''
    except Exception as exc:
        _pdf_logger.error('[extract_pdf_text] OCR error: %s', exc)
        return ''

# def add_to_knowledge_base để chia nhỏ nội dung thành chunk rồi nạp vào vector store của user (và cả shared nếu is_shared) phục vụ tra cứu RAG.
# vd: dán 1 quy chế 5000 ký tự -> chia ~7 chunk và nạp vào KB của user.
def add_to_knowledge_base(content, user, is_shared=False, metadata=None):
    """
    Thuoc chuc nang nao: Tro ly AI, Hoi dap tai lieu, Sinh van ban tu mau, Guest tao van ban va cac luong AI nen.
    Vai tro backend: Ham `add_to_knowledge_base` la ham nghiep vu chinh trong file `ai_engine/rag_engine.py`, chiu trach nhiem thuc hien phan xu ly chuyen trach cua symbol hien tai trong mot luong backend nhieu buoc.
    Vai tro cua no trong frontend: Frontend hiem khi goi truc tiep ham kieu nay; endpoint, command hoac signal se goi no khi can thuc hien phan xu ly chuyen trach cua symbol hien tai roi moi phan anh ket qua len man hinh.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `ai_engine.models`, `ai_engine.rag_engine`, `ai_engine.rag_index`, `ai_engine.doc_creator`, `accounts.models`. Dung cung cap voi cac ham `_ollama_client_kwargs`, `_record_ai_usage`, `_truncate_llm_debug_text` trong module nay.
    Tac dung: Don buoc thuc hien phan xu ly chuyen trach cua symbol hien tai xuong service hoac engine de view khong phai tu trien khai lai logic ky thuat.
    """
    splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=100)
    chunks = splitter.split_text(content or '')
    if not chunks:
        return

    meta = metadata or {}
    meta['owner_id'] = user.id if user else None
    meta['is_shared'] = is_shared
    docs_with_meta = [{'text': chunk, 'metadata': meta} for chunk in chunks]

    vs = get_vectorstore(user, shared=False)
    vs.add_texts(
        texts=[item['text'] for item in docs_with_meta],
        metadatas=[item['metadata'] for item in docs_with_meta],
    )

    if is_shared:
        shared_vs = get_vectorstore(shared=True)
        shared_vs.add_texts(
            texts=[item['text'] for item in docs_with_meta],
            metadatas=[item['metadata'] for item in docs_with_meta],
        )

# def ask_ai để hỏi đáp dựa trên tri thức người dùng: truy hồi (similarity search) các đoạn liên quan rồi ghép ngữ cảnh + prompt và gọi LLM trả lời.
# vd: 'quy dinh nghi phep the nao?' -> tìm đoạn liên quan trong KB rồi để LLM trả lời.
def ask_ai(
    question,
    user,
    extra_context='',
    prompt_system_ideology=None,
    prompt_rules_content=None,
    model_override=None,
    temperature_override=None,
    max_results_override=None,
    allow_cloud_model=True,
):
    """
    Thuoc chuc nang nao: Tro ly AI, Hoi dap tai lieu, Sinh van ban tu mau, Guest tao van ban va cac luong AI nen.
    Vai tro backend: Ham `ask_ai` la ham nghiep vu chinh trong file `ai_engine/rag_engine.py`, chiu trach nhiem thuc hien phan xu ly chuyen trach cua symbol hien tai trong mot luong backend nhieu buoc.
    Vai tro cua no trong frontend: Frontend hiem khi goi truc tiep ham kieu nay; endpoint, command hoac signal se goi no khi can thuc hien phan xu ly chuyen trach cua symbol hien tai roi moi phan anh ket qua len man hinh.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `ai_engine.models`, `ai_engine.rag_engine`, `ai_engine.rag_index`, `ai_engine.doc_creator`, `accounts.models`. Dung cung cap voi cac ham `_ollama_client_kwargs`, `_record_ai_usage`, `_truncate_llm_debug_text` trong module nay.
    Tac dung: Don buoc thuc hien phan xu ly chuyen trach cua symbol hien tai xuong service hoac engine de view khong phai tu trien khai lai logic ky thuat.
    """
    from accounts.tenancy import build_effective_ai_context, resolve_ai_config

    cfg = resolve_ai_config(user=user)
    k = int(max_results_override if max_results_override is not None else cfg.ai_max_results)

    retrieved_docs = []
    try:
        retrieved_docs.extend(get_vectorstore(user, shared=False).similarity_search(question, k=k))
    except Exception:
        pass
    try:
        retrieved_docs.extend(get_vectorstore(shared=True).similarity_search(question, k=k))
    except Exception:
        pass

    context_parts = [doc.page_content for doc in retrieved_docs]
    if extra_context:
        context_parts.insert(0, extra_context)
    context = '\n\n'.join(context_parts)

    if prompt_system_ideology:
        system_content = prompt_system_ideology
    else:
        system_content = (
            'Ban la tro ly AI huu ich. Hay tra loi dua tren thong tin duoc cung cap. '
            'Neu khong co du thong tin, hay noi ro dieu do. Tra loi bang tieng Viet.'
        )
    if prompt_rules_content:
        system_content += f'\n\n{prompt_rules_content}'
    effective_context = build_effective_ai_context(user=user)
    if effective_context:
        system_content += f'\n\nNgu canh nguoi dung hien tai:\n{effective_context}'
    if context:
        system_content += f'\n\nThong tin tham khao:\n{context}'

    llm = get_llm(
        user,
        model_override=model_override,
        temperature_override=temperature_override,
        allow_cloud_model=allow_cloud_model,
    )
    response = llm.invoke([
        SystemMessage(content=system_content),
        HumanMessage(content=question),
    ])
    return response.content, system_content

# def index_template để đánh chỉ mục/đồng bộ một mẫu văn bản vào vector index (gọi sync_template_index).
# vd: vừa duyệt 1 mẫu -> index_template(mau) để RAG tìm được nó.
def index_template(template):
    """
    Thuoc chuc nang nao: Tro ly AI, Hoi dap tai lieu, Sinh van ban tu mau, Guest tao van ban va cac luong AI nen.
    Vai tro backend: Ham `index_template` la ham nghiep vu chinh trong file `ai_engine/rag_engine.py`, chiu trach nhiem xu ly du lieu hoac thao tac lien quan toi mau van ban trong mot luong backend nhieu buoc.
    Vai tro cua no trong frontend: Frontend hiem khi goi truc tiep ham kieu nay; endpoint, command hoac signal se goi no khi can xu ly du lieu hoac thao tac lien quan toi mau van ban roi moi phan anh ket qua len man hinh.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `ai_engine.models`, `ai_engine.rag_engine`, `ai_engine.rag_index`, `ai_engine.doc_creator`, `accounts.models`. Dung cung cap voi cac ham `_ollama_client_kwargs`, `_record_ai_usage`, `_truncate_llm_debug_text` trong module nay.
    Tac dung: Don buoc xu ly du lieu hoac thao tac lien quan toi mau van ban xuong service hoac engine de view khong phai tu trien khai lai logic ky thuat.
    """
    return sync_template_index(template)

# def index_document để đánh chỉ mục/đồng bộ một tài liệu vào vector index (gọi sync_document_index).
# vd: vừa tạo 1 văn bản -> index_document(vb) để hỏi đáp được.
def index_document(document):
    """
    Thuoc chuc nang nao: Tro ly AI, Hoi dap tai lieu, Sinh van ban tu mau, Guest tao van ban va cac luong AI nen.
    Vai tro backend: Ham `index_document` la ham nghiep vu chinh trong file `ai_engine/rag_engine.py`, chiu trach nhiem xu ly du lieu hoac thao tac lien quan toi van ban trong mot luong backend nhieu buoc.
    Vai tro cua no trong frontend: Frontend hiem khi goi truc tiep ham kieu nay; endpoint, command hoac signal se goi no khi can xu ly du lieu hoac thao tac lien quan toi van ban roi moi phan anh ket qua len man hinh.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `ai_engine.models`, `ai_engine.rag_engine`, `ai_engine.rag_index`, `ai_engine.doc_creator`, `accounts.models`. Dung cung cap voi cac ham `_ollama_client_kwargs`, `_record_ai_usage`, `_truncate_llm_debug_text` trong module nay.
    Tac dung: Don buoc xu ly du lieu hoac thao tac lien quan toi van ban xuong service hoac engine de view khong phai tu trien khai lai logic ky thuat.
    """
    return sync_document_index(document)

# def _internet_search_debug để in log debug cho luồng gợi ý tra cứu trên Thư Viện Pháp Luật.
# vd: in '[TVPL_SEARCH] build url ...' khi gợi ý tra cứu.
def _internet_search_debug(message):
    """
    Thuoc chuc nang nao: Tro ly AI, Hoi dap tai lieu, Sinh van ban tu mau, Guest tao van ban va cac luong AI nen.
    Vai tro backend: Ham `_internet_search_debug` la helper noi bo trong file `ai_engine/rag_engine.py`, chiu trach nhiem tim kiem hoac loc du lieu theo cau hoi dau vao trong mot luong backend nhieu buoc.
    Vai tro cua no trong frontend: Frontend hiem khi goi truc tiep ham kieu nay; endpoint, command hoac signal se goi no khi can tim kiem hoac loc du lieu theo cau hoi dau vao roi moi phan anh ket qua len man hinh.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `ai_engine.models`, `ai_engine.rag_engine`, `ai_engine.rag_index`, `ai_engine.doc_creator`, `accounts.models`. Thuong duoc cac ham public nhu `get_embeddings`, `get_llm`, `get_collection_name` goi lai.
    Tac dung: Don buoc tim kiem hoac loc du lieu theo cau hoi dau vao xuong service hoac engine de view khong phai tu trien khai lai logic ky thuat.
    """
    print(f'[TVPL_SEARCH] {message}', flush=True)

# def _default_internet_search_keyword để chuẩn hóa câu hỏi thành từ khóa tìm kiếm (gộp khoảng trắng, bỏ ký tự thừa, cắt còn 180 ký tự).
# vd: '  Hợp đồng thuê nhà??? ' -> 'Hợp đồng thuê nhà'.
def _default_internet_search_keyword(question):
    """
    Thuoc chuc nang nao: Tro ly AI, Hoi dap tai lieu, Sinh van ban tu mau, Guest tao van ban va cac luong AI nen.
    Vai tro backend: Ham `_default_internet_search_keyword` la helper noi bo trong file `ai_engine/rag_engine.py`, chiu trach nhiem tim kiem hoac loc du lieu theo cau hoi dau vao trong mot luong backend nhieu buoc.
    Vai tro cua no trong frontend: Frontend hiem khi goi truc tiep ham kieu nay; endpoint, command hoac signal se goi no khi can tim kiem hoac loc du lieu theo cau hoi dau vao roi moi phan anh ket qua len man hinh.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `ai_engine.models`, `ai_engine.rag_engine`, `ai_engine.rag_index`, `ai_engine.doc_creator`, `accounts.models`. Thuong duoc cac ham public nhu `get_embeddings`, `get_llm`, `get_collection_name` goi lai.
    Tac dung: Don buoc tim kiem hoac loc du lieu theo cau hoi dau vao xuong service hoac engine de view khong phai tu trien khai lai logic ky thuat.
    """
    keyword = ' '.join((question or '').split()).strip()
    keyword = keyword.strip(' \t\r\n"\'`.,;:!?-')
    return keyword[:180]

# def _extract_internet_search_keyword để rút từ khóa tìm kiếm ngắn gọn (tối đa 8 từ) từ câu hỏi.
# vd: câu dài 20 từ -> giữ 8 từ đầu làm từ khóa.
def _extract_internet_search_keyword(
    question,
    user=None,
    model_override=None,
    allow_cloud_model=False,
):
    """
    Thuoc chuc nang nao: Tro ly AI, Hoi dap tai lieu, Sinh van ban tu mau, Guest tao van ban va cac luong AI nen.
    Vai tro backend: Ham `_extract_internet_search_keyword` la helper noi bo trong file `ai_engine/rag_engine.py`, chiu trach nhiem trich xuat noi dung hoac gia tri trung gian trong mot luong backend nhieu buoc.
    Vai tro cua no trong frontend: Frontend hiem khi goi truc tiep ham kieu nay; endpoint, command hoac signal se goi no khi can trich xuat noi dung hoac gia tri trung gian roi moi phan anh ket qua len man hinh.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `ai_engine.models`, `ai_engine.rag_engine`, `ai_engine.rag_index`, `ai_engine.doc_creator`, `accounts.models`. Thuong duoc cac ham public nhu `get_embeddings`, `get_llm`, `get_collection_name` goi lai.
    Tac dung: Don buoc trich xuat noi dung hoac gia tri trung gian xuong service hoac engine de view khong phai tu trien khai lai logic ky thuat.
    """
    keyword = _default_internet_search_keyword(question)
    if not keyword:
        return ''
    words = keyword.split()
    return ' '.join(words[:8])

# def _internet_search_url để dựng URL tra cứu biểu mẫu/hợp đồng trên thuvienphapluat.vn theo từ khóa.
# vd: -> 'https://thuvienphapluat.vn/bieumau?type=0&q=Hop+dong+thue+nha'.
def _internet_search_url(question, source_type='bieumau'):
    """
    Thuoc chuc nang nao: Tro ly AI, Hoi dap tai lieu, Sinh van ban tu mau, Guest tao van ban va cac luong AI nen.
    Vai tro backend: Ham `_internet_search_url` la helper noi bo trong file `ai_engine/rag_engine.py`, chiu trach nhiem tim kiem hoac loc du lieu theo cau hoi dau vao trong mot luong backend nhieu buoc.
    Vai tro cua no trong frontend: Frontend hiem khi goi truc tiep ham kieu nay; endpoint, command hoac signal se goi no khi can tim kiem hoac loc du lieu theo cau hoi dau vao roi moi phan anh ket qua len man hinh.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `ai_engine.models`, `ai_engine.rag_engine`, `ai_engine.rag_index`, `ai_engine.doc_creator`, `accounts.models`. Thuong duoc cac ham public nhu `get_embeddings`, `get_llm`, `get_collection_name` goi lai.
    Tac dung: Don buoc tim kiem hoac loc du lieu theo cau hoi dau vao xuong service hoac engine de view khong phai tu trien khai lai logic ky thuat.
    """
    cleaned_question = _default_internet_search_keyword(question)
    if not cleaned_question:
        return ''
    path = 'hopdong' if source_type == 'hopdong' else 'bieumau'
    return 'https://thuvienphapluat.vn/{path}?{query}'.format(
        path=path,
        query=urllib.parse.urlencode({'type': '0', 'q': cleaned_question}),
    )

# def _internet_search_source_label để trả nhãn nguồn hiển thị (BIEU MAU / HOP DONG) cho gợi ý internet.
# vd: 'hopdong' -> 'THU VIEN PHAP LUAT | HOP DONG'.
def _internet_search_source_label(source_type):
    """
    Thuoc chuc nang nao: Tro ly AI, Hoi dap tai lieu, Sinh van ban tu mau, Guest tao van ban va cac luong AI nen.
    Vai tro backend: Ham `_internet_search_source_label` la helper noi bo trong file `ai_engine/rag_engine.py`, chiu trach nhiem tim kiem hoac loc du lieu theo cau hoi dau vao trong mot luong backend nhieu buoc.
    Vai tro cua no trong frontend: Frontend hiem khi goi truc tiep ham kieu nay; endpoint, command hoac signal se goi no khi can tim kiem hoac loc du lieu theo cau hoi dau vao roi moi phan anh ket qua len man hinh.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `ai_engine.models`, `ai_engine.rag_engine`, `ai_engine.rag_index`, `ai_engine.doc_creator`, `accounts.models`. Thuong duoc cac ham public nhu `get_embeddings`, `get_llm`, `get_collection_name` goi lai.
    Tac dung: Don buoc tim kiem hoac loc du lieu theo cau hoi dau vao xuong service hoac engine de view khong phai tu trien khai lai logic ky thuat.
    """
    if source_type == 'hopdong':
        return 'THU VIEN PHAP LUAT | HOP DONG'
    return 'THU VIEN PHAP LUAT | BIEU MAU'

# def _build_internet_suggestion để tạo một gợi ý internet gồm context + citation (tiêu đề, URL, loại nguồn) trỏ tới thuvienphapluat.vn.
# vd: -> {'context':'[...] cau hoi','citation':{title,url,type:'internet'}}.
def _build_internet_suggestion(question, source_type='bieumau'):
    """
    Thuoc chuc nang nao: Tro ly AI, Hoi dap tai lieu, Sinh van ban tu mau, Guest tao van ban va cac luong AI nen.
    Vai tro backend: Ham `_build_internet_suggestion` la helper noi bo trong file `ai_engine/rag_engine.py`, chiu trach nhiem dung payload hoac cau truc du lieu trung gian trong mot luong backend nhieu buoc.
    Vai tro cua no trong frontend: Frontend hiem khi goi truc tiep ham kieu nay; endpoint, command hoac signal se goi no khi can dung payload hoac cau truc du lieu trung gian roi moi phan anh ket qua len man hinh.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `ai_engine.models`, `ai_engine.rag_engine`, `ai_engine.rag_index`, `ai_engine.doc_creator`, `accounts.models`. Thuong duoc cac ham public nhu `get_embeddings`, `get_llm`, `get_collection_name` goi lai.
    Tac dung: Don buoc dung payload hoac cau truc du lieu trung gian xuong service hoac engine de view khong phai tu trien khai lai logic ky thuat.
    """
    url = _internet_search_url(question, source_type=source_type)
    if not url:
        return None
    label = _internet_search_source_label(source_type)
    title = f'{label}: {question}'
    return {
        'context': f'[{label}]\n{question}',
        'citation': {
            'title': title,
            'url': url,
            'external_url': url,
            'type': 'internet',
            'source_group': 'internet',
            'status': label,
            'category': 'thuvienphapluat.vn',
            'source_type': source_type,
        },
    }

# def _internet_search_suggestions để tạo danh sách gợi ý tra cứu internet (Thư Viện Pháp Luật) cho câu hỏi, tối đa `limit` mục.
# vd: limit=5 -> tối đa 5 link gợi ý từ thuvienphapluat.vn.
def _internet_search_suggestions(question, limit=5, engine='thuvienphapluat'):
    """
    Thuoc chuc nang nao: Tro ly AI, Hoi dap tai lieu, Sinh van ban tu mau, Guest tao van ban va cac luong AI nen.
    Vai tro backend: Ham `_internet_search_suggestions` la helper noi bo trong file `ai_engine/rag_engine.py`, chiu trach nhiem tim kiem hoac loc du lieu theo cau hoi dau vao trong mot luong backend nhieu buoc.
    Vai tro cua no trong frontend: Frontend hiem khi goi truc tiep ham kieu nay; endpoint, command hoac signal se goi no khi can tim kiem hoac loc du lieu theo cau hoi dau vao roi moi phan anh ket qua len man hinh.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `ai_engine.models`, `ai_engine.rag_engine`, `ai_engine.rag_index`, `ai_engine.doc_creator`, `accounts.models`. Thuong duoc cac ham public nhu `get_embeddings`, `get_llm`, `get_collection_name` goi lai.
    Tac dung: Don buoc tim kiem hoac loc du lieu theo cau hoi dau vao xuong service hoac engine de view khong phai tu trien khai lai logic ky thuat.
    """
    engine = str(engine or '').strip().lower() or 'thuvienphapluat'
    if engine != 'thuvienphapluat' or int(limit or 0) <= 0:
        return []

    keyword = _extract_internet_search_keyword(question)
    if not keyword:
        return []

    suggestions = []
    for source_type in ('bieumau', 'hopdong'):
        suggestion = _build_internet_suggestion(keyword, source_type=source_type)
        if suggestion is not None:
            suggestions.append(suggestion)
        if len(suggestions) >= int(limit):
            break
    _internet_search_debug(
        f'internet_stub_results | keyword={keyword!r} | returned={len(suggestions)}'
    )
    return suggestions

# def rag_query là điểm vào RAG cho hỏi đáp mẫu văn bản/tài liệu: truy hồi đoạn liên quan theo mode (template/document), ghép ngữ cảnh + gợi ý internet rồi gọi LLM, trả về (câu trả lời, danh sách citations).
# vd: mode='template', 'mau don xin nghi' -> (câu trả lời, [citation mẫu liên quan]).
def rag_query(
    question,
    user,
    mode='template',
    k=None,
    history=None,
    model_override=None,
    temperature_override=None,
    allow_cloud_model=True,
):
    """
    Thuoc chuc nang nao: Tro ly AI, Hoi dap tai lieu, Sinh van ban tu mau, Guest tao van ban va cac luong AI nen.
    Vai tro backend: Ham `rag_query` la ham nghiep vu chinh trong file `ai_engine/rag_engine.py`, chiu trach nhiem tim kiem hoac loc du lieu theo cau hoi dau vao trong mot luong backend nhieu buoc.
    Vai tro cua no trong frontend: Frontend hiem khi goi truc tiep ham kieu nay; endpoint, command hoac signal se goi no khi can tim kiem hoac loc du lieu theo cau hoi dau vao roi moi phan anh ket qua len man hinh.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `ai_engine.models`, `ai_engine.rag_engine`, `ai_engine.rag_index`, `ai_engine.doc_creator`, `accounts.models`. Dung cung cap voi cac ham `_ollama_client_kwargs`, `_record_ai_usage`, `_truncate_llm_debug_text` trong module nay.
    Tac dung: Don buoc tim kiem hoac loc du lieu theo cau hoi dau vao xuong service hoac engine de view khong phai tu trien khai lai logic ky thuat.
    """
    from accounts.tenancy import build_effective_ai_context, resolve_ai_config

    cfg = resolve_ai_config(user=user)
    if k is None:
        k = cfg.ai_max_results
    k = max(1, int(k or 1))
    active_model = model_override or cfg.ai_model
    active_temperature = cfg.ai_temperature if temperature_override is None else float(temperature_override)
    internet_limit = max(0, int(getattr(cfg, 'ai_internet_results', 0) or 0))
    internet_engine = str(getattr(cfg, 'ai_search_engine', 'thuvienphapluat') or 'thuvienphapluat').strip().lower()
    if internet_engine != 'thuvienphapluat':
        _internet_search_debug(
            f"ai_search_engine hien tai la {internet_engine!r}; chuyen ve 'thuvienphapluat'"
        )
        internet_engine = 'thuvienphapluat'

    if mode == 'template':
        items = _db_search_templates(question, user, k)
        source_label = 'mau van ban'
    else:
        items = _db_search_documents(question, user, k)
        source_label = 'van ban'

    local_citations = [item['citation'] for item in items]
    internet_citations = []
    if internet_limit > 0:
        keyword = _extract_internet_search_keyword(
            question,
            user=user,
            model_override=active_model,
            allow_cloud_model=allow_cloud_model,
        )
        internet_items = _internet_search_suggestions(keyword or question, limit=internet_limit, engine=internet_engine)
        internet_citations = [item['citation'] for item in internet_items]

    citations = [*local_citations, *internet_citations]
    context = '\n\n---\n\n'.join(item['context'] for item in items)

    if not local_citations:
        if internet_citations:
            return (
                'Khong tim thay ket qua local du suc lien quan trong he thong. '
                'Ben duoi la cac lien ket tim kiem THU VIEN PHAP LUAT de mo rong tra cuu.',
                internet_citations,
            )
        return (
            f'Khong tim thay {source_label} phu hop voi cau hoi trong he thong hien tai. '
            'Hay thu dien dat cu the hon hoac doi pham vi tim kiem.',
            [],
        )

    system = (
        f'Ban la tro ly tim kiem {source_label} noi bo. '
        'Hay tra loi cau hoi dua tren cac tai lieu duoc cung cap ben duoi. '
        'Trich dan ten tai lieu cu the khi tra loi. '
        'Neu khong tim thay thong tin lien quan trong tai lieu, hay noi ro dieu do. '
        'Tra loi bang tieng Viet.'
    )
    effective_context = build_effective_ai_context(user=user)
    if effective_context:
        system += f'\n\nNgu canh nguoi dung hien tai:\n{effective_context}'
    if context:
        system += f'\n\nTai lieu tham khao:\n{context}'

    messages = [SystemMessage(content=system)]
    if history:
        for turn in history[-6:]:
            if turn['role'] == 'user':
                messages.append(HumanMessage(content=turn['content']))
            else:
                messages.append(AIMessage(content=turn['content']))
    messages.append(HumanMessage(content=question))

    llm = get_llm(
        user,
        model_override=active_model,
        temperature_override=active_temperature,
        allow_cloud_model=allow_cloud_model,
    )
    response = llm.invoke(messages)
    answer = response.content
    if internet_citations:
        answer = (
            f'{answer}\n\n'
            f'Co them {len(internet_citations)} lien ket THU VIEN PHAP LUAT o phan nguon ben duoi de tra cuu bo sung.'
        )
    return answer, citations
