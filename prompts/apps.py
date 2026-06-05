"""
Thuoc chuc nang nao: Tro ly AI, Hoi dap tai lieu, Sinh van ban tu mau, Guest tao van ban va cac luong AI nen.
Vai tro backend: File `prompts/apps.py` giu hoac ho tro luong backend cho chat, RAG, OCR, prefill ho so, sinh van ban, luu session va quan ly tri thuc AI.
Vai tro cua no trong frontend: Cac man `/chat`, `/rag`, `/ai-doc`, `/guest` va cac dialog AI phu tro phu thuoc vao ket qua ma file nay sinh ra.
Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `ai_engine.models`, `ai_engine.rag_engine`, `ai_engine.rag_index`, `ai_engine.doc_creator`, `accounts.models`.
Tac dung: Bao dam prompt, ket qua AI, session hoi thoai, du lieu trich xuat va chi muc RAG phuc vu dung ngu canh cua nguoi dung hien tai.
"""

from django.apps import AppConfig


_DEFAULT_ASSISTANT_DOCUMENT_RULES = (
    "- Dien day du tat ca variables cua mau da chon\n"
    "- Neu user chua cung cap du du lieu cho mot bien thi de chuoi rong ''\n"
    "- KHONG suy luan, KHONG bia, KHONG tu bu thong tin con thieu\n"
    "- Chon template phu hop nhat voi yeu cau, dua vao title + description + content_preview\n"
    "- Chi tra ve JSON thuan tuy, khong markdown, khong giai thich ben ngoai JSON"
)


class _CuratedAssistantDocumentRules:
    def __str__(self) -> str:
        from django.db.utils import OperationalError, ProgrammingError

        try:
            from prompts.models import PROMPT_STATUS_APPROVED, Prompt

            prompt = (
                Prompt.objects.filter(
                    source=Prompt.SOURCE_CURATED,
                    status=PROMPT_STATUS_APPROVED,
                    visibility=Prompt.VISIBILITY_PUBLIC,
                    usage_scope__overlap=['chat'],
                    tags__icontains='seed:default-chat-primary',
                )
                .only('system_content', 'rules_content')
                .order_by('id')
                .first()
            )
        except (OperationalError, ProgrammingError):
            return _DEFAULT_ASSISTANT_DOCUMENT_RULES
        except Exception:
            return _DEFAULT_ASSISTANT_DOCUMENT_RULES

        if prompt is None:
            return _DEFAULT_ASSISTANT_DOCUMENT_RULES

        rules_text = '\n\n'.join(
            part.strip()
            for part in [prompt.system_content or '', prompt.rules_content or '']
            if part and part.strip()
        )
        return rules_text or _DEFAULT_ASSISTANT_DOCUMENT_RULES


class PromptsConfig(AppConfig):
    """
    Thuoc chuc nang nao: Tro ly AI, Hoi dap tai lieu, Sinh van ban tu mau, Guest tao van ban va cac luong AI nen.
    Vai tro backend: Lop `PromptsConfig` dang ky cau hinh khoi dong va hook `ready()` cua app trong file `prompts/apps.py`.
    Vai tro cua no trong frontend: Frontend khong goi truc tiep lop nay; no tac dong gian tiep bang cach bao dam signal, runtime override hoac side effect nen da san sang truoc khi API phuc vu man hinh.
    Moi lien he voi nhung ham / source khac: Tuong tac truc tiep voi `api/urls.py`, `ai_engine.models`, `ai_engine.rag_engine`, `ai_engine.rag_index`, `ai_engine.doc_creator`, `accounts.models`. Nam trong pham vi module hien tai.
    Tac dung: Kich hoat dung wiring cua app khi Django khoi dong de cac man nav khong gap trang thai thieu hook nen.
    """
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'prompts'
    verbose_name = 'Prompts'

    def ready(self):
        try:
            from ai_engine import assistant_engine

            assistant_engine.ASSISTANT_DOCUMENT_RULES = _CuratedAssistantDocumentRules()
        except Exception:
            pass
