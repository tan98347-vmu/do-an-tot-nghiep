from __future__ import annotations

import re
import textwrap
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLANTUML_DIR = ROOT / "plantuml_nav"
API_URLS = ROOT / "api" / "urls.py"
ROUTER_DART = ROOT / "flutter_frontend" / "lib" / "core" / "router.dart"
API_CLIENT_DART = ROOT / "flutter_frontend" / "lib" / "core" / "api_client.dart"
URLS_PY = ROOT / "my_tennis_club" / "urls.py"

ENTITY_RE = re.compile(
    r'^(\s*)(actor|component|database|folder|cloud|node|rectangle)\s+"([\s\S]*?)"\s+as\s+(\w+)(.*)$',
    re.M,
)
INDEX_RECT_RE = re.compile(r'^(\s*rectangle)\s+"([^"]+)"\s*\{', re.M)
TITLE_RE = re.compile(r"^title\s+(.+)$", re.M)
NOTE_BOTTOM_RE = re.compile(r"\nnote bottom\n[\s\S]*?\nend note(?=\s*@enduml)", re.M)
PY_DEF_RE = re.compile(r"^\s*def\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(", re.M)
PY_CLASS_RE = re.compile(r"^\s*class\s+([A-Za-z_][A-Za-z0-9_]*)\s*(?:\(|:)", re.M)
DART_CLASS_RE = re.compile(r"^\s*class\s+([A-Za-z_][A-Za-z0-9_]*)\s+", re.M)
DART_METHOD_RE = re.compile(
    r"^\s*(?:@override\s+)?(?:static\s+)?(?:Future<[^>]+>|Future<void>|Future<bool>|Future<int>|Future<String>|Future<Uint8List\?>|"
    r"Future<Uint8List>|void|bool|int|double|String|Widget|FormData|Uint8List\?|Uint8List|List<[^>]+>|Map<[^>]+>|dynamic|"
    r"[A-Za-z_][A-Za-z0-9_<>,? ]+)\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(",
    re.M,
)
ROUTE_RE = re.compile(r"path\('([^']+)'\s*,\s*([A-Za-z_][A-Za-z0-9_]*)\.([A-Za-z_][A-Za-z0-9_]*)")

SCREEN_FILE_OVERRIDES = {
    "DashboardScreen": "flutter_frontend/lib/screens/dashboard/dashboard_hub_screen.dart",
    "MailboxScreen": "flutter_frontend/lib/screens/documents/mailbox_screen_modern.dart",
    "MailboxDetailScreen": "flutter_frontend/lib/screens/documents/mailbox_detail_screen_modern.dart",
    "SigningInboxScreen": "flutter_frontend/lib/screens/signing/signing_inbox_screen_modern.dart",
    "SigningTaskDetailScreen": "flutter_frontend/lib/screens/signing/signing_task_detail_screen_pki.dart",
    "SignedPdfListScreen": "flutter_frontend/lib/screens/signing/signed_pdf_list_screen_modern.dart",
    "SignedPdfDetailScreen": "flutter_frontend/lib/screens/signing/signed_pdf_detail_screen_pki.dart",
}

PROVIDER_FILE_HINTS = {
    "ragProvider": "flutter_frontend/lib/providers/chat_provider.dart",
    "dashboardStatsProvider": "flutter_frontend/lib/providers/dashboard_provider.dart",
    "orgNodeStatsProvider": "flutter_frontend/lib/providers/dashboard_provider.dart",
    "templateCollectionProvider": "flutter_frontend/lib/providers/templates_provider.dart",
    "templateDetailProvider": "flutter_frontend/lib/providers/templates_provider.dart",
    "pendingApprovalsCountProvider": "flutter_frontend/lib/providers/pending_approvals_provider.dart",
}

INFRA_SUMMARY = {
    "PostgreSQL": "Tang luu tru quan he trung tam cho du lieu nghiep vu, session va audit.",
    "PGVector": "Tang vector search de semantic retrieval va RAG.",
    "Media Storage": "Khu vuc luu tep DOCX, PDF, preview, audio va artefact sinh ra tu backend.",
    "Ollama": "Lop goi model AI de sinh cau tra loi, OCR/prefill hoac detect bien.",
    "Remote HSM optional": "Dich vu ky so tu xa duoc goi khi he thong chay che do ky PDF PKCS7.",
    "Excel import files": "Tap tin tam cho luong import user bang Excel.",
    "backups/*.json": "Thu muc sinh file backup JSON cua he thong.",
    "media/guest_sessions": "Thu muc session tam cho guest portal.",
    "Ollama optional for detect": "Model AI tuy chon de ho tro detect bien hoac OCR trong guest flow.",
}

SPECIAL_COMPONENTS = {
    "accounts + documents +\n document_templates + ai_engine models": {
        "summary": "Cum model tong hop ma dashboard doc de tinh thong ke toan he thong.",
        "files": [
            "accounts/models.py",
            "documents/models.py",
            "document_templates/models.py",
            "ai_engine/models.py",
        ],
        "refs": [
            ("api/views/dashboard.py", "dashboard_stats", "Tap hop so lieu tong hop cho dashboard."),
            ("api/views/dashboard.py", "dashboard_org_node_stats", "Tinh thong ke theo cay to chuc."),
            ("api/views/dashboard.py", "pending_approvals_count", "Dem phien duyet dang cho xu ly."),
        ],
    },
    "document_templates\nDocumentTemplate.render_as_docx()": {
        "summary": "Model mau van ban va ham sinh DOCX dau ra tu template da dien bien.",
        "files": ["document_templates/models.py"],
        "refs": [
            ("document_templates/models.py", "get_variables", "Tach danh sach bien {{...}} tu noi dung mau."),
            ("document_templates/models.py", "render", "Thay gia tri bien vao noi dung text/HTML."),
            ("document_templates/models.py", "render_as_docx", "Sinh file DOCX tu template da duoc dien du lieu."),
        ],
    },
    "documents\nDocument + versioning": {
        "summary": "Cum model van ban sinh ra tu mau va thong tin version phuc vu theo doi thay doi.",
        "files": ["documents/models.py", "api/views/documents.py"],
        "refs": [
            ("api/views/documents.py", "document_list_create", "Tao va liet ke van ban sinh ra."),
            ("api/views/documents.py", "document_detail_view", "Doc cap nhat thong tin van ban."),
            ("api/views/documents.py", "document_versions", "Tra lich su version cua van ban."),
        ],
    },
    "ai_engine\nget_llm() / OCR / prefill": {
        "summary": "Lop AI backend dung cho prefill, OCR va goi model khi sinh van ban tu mau.",
        "files": ["ai_engine/rag_engine.py", "api/views/ai_doc.py"],
        "refs": [
            ("ai_engine/rag_engine.py", "get_llm", "Khoi tao client model AI theo cau hinh hien tai."),
            ("ai_engine/rag_engine.py", "extract_pdf_text", "Rut text/OCR tu PDF de bo sung du lieu dien."),
            ("api/views/ai_doc.py", "ai_doc_prefill_profile", "Sinh goi y thong tin ca nhan cho form dien bien."),
        ],
    },
    "OCR + DOCX/PDF tools": {
        "summary": "Nhom ham xu ly tai lieu dung de OCR, parse van ban va chuyen doi DOCX/PDF.",
        "files": ["ai_engine/rag_engine.py", "document_templates/models.py", "documents/pdf_preview.py"],
        "refs": [
            ("ai_engine/rag_engine.py", "extract_pdf_text", "Lay text tu PDF, co the OCR neu can."),
            ("document_templates/models.py", "render_as_docx", "Sinh DOCX sau khi thay bien vao template."),
            ("documents/pdf_preview.py", "build_template_preview_pdf", "Tao preview PDF de frontend xem nhanh."),
        ],
    },
    "accounts.permissions + documents + templates": {
        "summary": "Cum quyen truy cap va domain du lieu ma luong RAG dung de loc nguon hop le.",
        "files": ["accounts/permissions.py", "documents/models.py", "document_templates/models.py"],
        "refs": [
            ("accounts/permissions.py", "get_accessible_templates", "Loc mau ma user duoc phep doc."),
            ("accounts/permissions.py", "get_accessible_documents", "Loc van ban ma user duoc phep doc."),
            ("ai_engine/rag_engine.py", "rag_query", "Ket hop quyen va nguon du lieu truoc khi goi model."),
        ],
    },
    "ChatSession / ChatMessage": {
        "summary": "Model session va message luu lich su hoi dap RAG/chat.",
        "files": ["ai_engine/models.py", "api/views/chat.py"],
        "refs": [
            ("ai_engine/models.py", "ChatSession", "Bang session gom thread hoi dap theo tung ngu canh."),
            ("ai_engine/models.py", "ChatMessage", "Bang message luu moi turn user/assistant."),
            ("api/views/chat.py", "rag_query_view", "Tao session va ghi message moi khi user gui cau hoi RAG."),
        ],
    },
    "ChatSession / ChatMessage /\n ChatAudioAttachment": {
        "summary": "Cum model luu session, message va file audio cho tro ly AI text/voice.",
        "files": ["ai_engine/models.py", "api/views/assistant.py"],
        "refs": [
            ("ai_engine/models.py", "ChatSession", "Luu thread assistant text/voice."),
            ("ai_engine/models.py", "ChatAudioAttachment", "Luu file ghi am va transcript."),
            ("api/views/assistant.py", "assistant_turn", "Ghi user message, audio va assistant answer vao DB."),
        ],
    },
    "SigningTask / SigningPacket /\n SignedPdfDocument": {
        "summary": "Cum model nghiep vu cho packet ky, task ky tung nguoi va tai lieu PDF da ky.",
        "files": ["signing/models.py", "signing/services.py"],
        "refs": [
            ("signing/services.py", "get_signature_context_for_task", "Doc packet/task de tao du lieu ky cho UI."),
            ("signing/services.py", "sign_task", "Cap nhat task, packet va tai lieu sau khi ky."),
            ("signing/services.py", "reject_task", "Cap nhat packet/task khi nguoi dung tu choi ky."),
        ],
    },
    "SignedPdfDocument +\n PdfSignatureRecord": {
        "summary": "Cum model luu PDF da ky va ket qua xac thuc tung chu ky trong file.",
        "files": ["signing/models.py", "signing/services.py"],
        "refs": [
            ("signing/services.py", "refresh_signed_pdf_verification", "Chay xac thuc lai chu ky trong PDF."),
            ("signing/services.py", "get_signed_pdf_integrity_report", "Tong hop bao cao integrity/verification cho UI."),
            ("signing/services.py", "ensure_signed_pdf_integrity", "Dam bao ban ghi verify duoc cap nhat truoc khi tra ve client."),
        ],
    },
    "guest session files + metadata": {
        "summary": "Vung luu session tam cua guest gom template, file sinh ra va metadata cookie.",
        "files": ["api/views/guest_portal_cookie.py"],
        "refs": [
            ("api/views/guest_portal_cookie.py", "_guest_root", "Xac dinh thu muc goc cua guest session."),
            ("api/views/guest_portal_cookie.py", "_read_guest_meta", "Doc metadata cua session guest hien tai."),
            ("api/views/guest_portal_cookie.py", "_write_guest_meta", "Cap nhat metadata sau moi buoc parse/generate."),
        ],
    },
    "guest document metadata": {
        "summary": "Metadata cua tai lieu guest vua duoc sinh de man detail/doc/download doc lai.",
        "files": ["api/views/guest_portal_cookie.py"],
        "refs": [
            ("api/views/guest_portal_cookie.py", "_guest_document_payload", "Tong hop thong tin tai lieu guest moi nhat."),
            ("api/views/guest_portal_cookie.py", "guest_document_detail", "Tra metadata chi tiet cho client."),
            ("api/views/guest_portal_cookie.py", "guest_document_download", "Tra file DOCX/PDF theo metadata session."),
        ],
    },
    "DOCX parse / OCR / replacement tools": {
        "summary": "Cum helper guest portal dung de parse template, OCR PDF va thay bien vao tai lieu tam.",
        "files": ["api/views/guest_portal_cookie.py"],
        "refs": [
            ("api/views/guest_portal_cookie.py", "_extract_docx_text", "Rut noi dung text tu template DOCX guest tai len."),
            ("api/views/guest_portal_cookie.py", "_extract_pdf_text", "Rut text/OCR tu PDF bo sung cua guest."),
            ("api/views/guest_portal_cookie.py", "_apply_replacements_to_docx", "Thay bien vao template guest truoc khi tai ve."),
        ],
    },
    "DOCX/PDF tools": {
        "summary": "Cum ham tao export/preview cho template duoc xem tu frontend.",
        "files": ["documents/pdf_preview.py", "document_templates/models.py"],
        "refs": [
            ("documents/pdf_preview.py", "build_template_preview_pdf", "Sinh PDF preview cho template detail."),
            ("document_templates/models.py", "render_as_docx", "Sinh DOCX export tu template."),
            ("api/views/documents.py", "template_content_html", "Tra HTML preview noi dung template cho web."),
        ],
    },
    "LibreOffice / DOCX tools": {
        "summary": "Cum ham chuyen DOCX thanh PDF preview cho van ban da tao.",
        "files": ["documents/pdf_preview.py"],
        "refs": [
            ("documents/pdf_preview.py", "_run_libreoffice_convert", "Goi LibreOffice de convert DOCX sang PDF."),
            ("documents/pdf_preview.py", "build_document_preview_pdf", "Tao preview PDF cho document detail."),
            ("documents/pdf_preview.py", "_preview_timeout_seconds", "Gioi han thoi gian cho qua trinh convert."),
        ],
    },
    "DocumentTemplate + TemplateFavorite": {
        "summary": "Model mau van ban va bang danh dau yeu thich cua user.",
        "files": ["document_templates/models.py", "api/views/templates.py"],
        "refs": [
            ("api/views/templates.py", "template_list_create", "Liet ke mau chia se theo bo loc he thong."),
            ("api/views/templates.py", "template_detail", "Lay chi tiet mau khi user mo detail."),
            ("api/views/templates.py", "template_favorite", "Bat/tat yeu thich tren template."),
        ],
    },
    "DocumentTemplate +\n TemplateAudienceMember": {
        "summary": "Model mau van ban va bang audience de chia template theo doi nhom/phong ban.",
        "files": ["document_templates/models.py", "api/views/templates.py"],
        "refs": [
            ("api/views/templates.py", "template_list_create", "Loc tap mau team ma user duoc phep thay."),
            ("accounts/permissions.py", "get_accessible_templates", "Kiem tra quyen hien thi theo audience."),
            ("api/views/templates.py", "template_detail", "Mo chi tiet template trong nhom."),
        ],
    },
    "DocumentTemplate +\n TemplateVersion + TemplateApprovalLog": {
        "summary": "Model template rieng, lich su version va nhat ky submit/duyet.",
        "files": ["document_templates/models.py", "api/views/templates.py"],
        "refs": [
            ("api/views/templates.py", "template_detail", "Cap nhat va xoa template rieng."),
            ("api/views/templates.py", "template_submit", "Gui template vao luong phe duyet."),
            ("api/views/templates.py", "template_versions", "Tra lich su version cho owner."),
        ],
    },
    "TemplateFavorite + DocumentTemplate": {
        "summary": "Bang relation yeu thich va template goc dung de hien nhom favorite.",
        "files": ["document_templates/models.py", "api/views/templates.py"],
        "refs": [
            ("api/views/templates.py", "template_list_create", "Loc danh sach template favorite."),
            ("api/views/templates.py", "template_favorite", "Them/bo danh dau favorite."),
            ("api/views/templates.py", "template_detail", "Mo chi tiet tu danh sach favorite."),
        ],
    },
    "DocumentTemplate": {
        "summary": "Model template trung tam cho danh muc admin.",
        "files": ["document_templates/models.py", "api/views/templates.py"],
        "refs": [
            ("api/views/templates.py", "template_list_create", "Liet ke template o che do admin."),
            ("api/views/templates.py", "template_detail", "Doc chi tiet va thong tin cua mot template."),
            ("document_templates/models.py", "render_as_docx", "Sinh export/preview khi can."),
        ],
    },
    "Document + DocumentVersion + DocumentFavorite": {
        "summary": "Cum model van ban, lich su version va bang yeu thich cua owner.",
        "files": ["documents/models.py", "api/views/documents.py"],
        "refs": [
            ("api/views/documents.py", "document_list_create", "Liet ke/tai len van ban cua toi."),
            ("api/views/documents.py", "document_versions", "Tra lich su version cua van ban."),
            ("api/views/documents.py", "document_favorite", "Bat/tat favorite cho van ban."),
        ],
    },
    "Document + UserGroupMembership": {
        "summary": "Van ban chia se theo group va relation thanh vien nhom de loc quyen truy cap.",
        "files": ["documents/models.py", "accounts/models.py", "accounts/permissions.py"],
        "refs": [
            ("accounts/permissions.py", "get_accessible_documents", "Loc van ban group theo membership cua user."),
            ("api/views/documents.py", "document_list_create", "Liet ke van ban theo bo loc group."),
            ("api/views/documents.py", "document_detail_view", "Mo chi tiet document trong nhom."),
        ],
    },
    "Document": {
        "summary": "Model van ban duoc doc trong cac nhom public/admin/archived.",
        "files": ["documents/models.py", "api/views/documents.py"],
        "refs": [
            ("api/views/documents.py", "document_list_create", "Liet ke document theo bo loc hien tai."),
            ("api/views/documents.py", "document_detail_view", "Tra chi tiet cho document detail."),
            ("documents/models.py", "Document", "Thuc the trung tam luu metadata va file van ban."),
        ],
    },
    "DocumentFavorite + Document": {
        "summary": "Bang relation yeu thich document va document goc.",
        "files": ["documents/models.py", "api/views/documents.py"],
        "refs": [
            ("api/views/documents.py", "document_list_create", "Loc nhom document favorite."),
            ("api/views/documents.py", "document_favorite", "Bat/tat document yeu thich."),
            ("api/views/documents.py", "document_detail_view", "Mo chi tiet tu danh sach favorite."),
        ],
    },
    "DocumentMailboxThread /\n DocumentMailboxEntry": {
        "summary": "Model hom thu phan phoi van ban theo thread va tung buoc xu ly.",
        "files": ["documents/models.py", "documents/mailbox_services.py"],
        "refs": [
            ("documents/mailbox_services.py", "forward_document", "Tao thread/entry moi khi forward van ban."),
            ("documents/mailbox_services.py", "complete_mailbox_entry", "Dong entry khi nguoi xu ly hoan tat."),
            ("documents/mailbox_services.py", "reject_mailbox_entry", "Danh dau entry bi tu choi."),
        ],
    },
    "DepartmentDelegation model": {
        "summary": "Model uy quyen ky theo phong ban/nhom cho signing flow.",
        "files": ["signing/models.py", "api/views/signing.py"],
        "refs": [
            ("api/views/signing.py", "signing_delegations", "Liet ke va tao uy quyen ky."),
            ("api/views/signing.py", "signing_delegation_detail", "Sua/xoa mot dong uy quyen."),
            ("signing/permissions.py", "can_manage_hr_delegations", "Kiem tra nguoi dung co quyen quan ly uy quyen hay khong."),
        ],
    },
    "DocumentTemplate /\n Document /\n ChatSession": {
        "summary": "Ba loai doi tuong co ho tro xoa mem va phuc hoi tu thung rac.",
        "files": ["document_templates/models.py", "documents/models.py", "ai_engine/models.py", "api/trash_services.py"],
        "refs": [
            ("api/trash_services.py", "list_trash_entries", "Tong hop danh sach thung rac tu ba bang."),
            ("api/trash_services.py", "restore_trash_items", "Phuc hoi doi tuong da xoa mem."),
            ("api/trash_services.py", "permanently_delete_trash_items", "Xoa han doi tuong khoi he thong."),
        ],
    },
    "UserSerializer + UserMeUpdateSerializer": {
        "summary": "Cap serializer dung de doc va cap nhat profile nguoi dung dang dang nhap.",
        "files": ["api/serializers/auth.py", "api/views/auth.py"],
        "refs": [
            ("api/views/auth.py", "me", "Doc/ghi thong tin user hien tai."),
            ("api/views/auth.py", "prefill_from_bio", "Dung thong tin profile lam dau vao AI prefill."),
            ("api/views/auth.py", "_ensure_signing_credential", "Khoi tao thong tin credential ky neu user chua co."),
        ],
    },
    "accounts profile +\n signing credential bootstrap": {
        "summary": "Du lieu profile va logic khoi tao credential ky gan voi user.",
        "files": ["accounts/models.py", "api/views/auth.py"],
        "refs": [
            ("api/views/auth.py", "me", "Cap nhat profile nguoi dung."),
            ("api/views/auth.py", "prefill_from_bio", "Dua profile vao AI de goi y field."),
            ("api/views/auth.py", "_ensure_signing_credential", "Dam bao user co credential ky co ban."),
        ],
    },
    "ai_engine/get_llm()": {
        "summary": "Ham lay model AI phu hop theo cau hinh va moi truong hien tai.",
        "files": ["ai_engine/rag_engine.py"],
        "refs": [
            ("ai_engine/rag_engine.py", "get_llm", "Khoi tao client model AI."),
            ("api/views/auth.py", "prefill_from_bio", "Goi AI de rut thong tin tu bio cua user."),
        ],
    },
    "GlobalAIConfig model": {
        "summary": "Model luu cau hinh model AI, endpoint va thong so dung chung.",
        "files": ["accounts/models.py", "api/views/admin_v.py"],
        "refs": [
            ("accounts/models.py", "GlobalAIConfig", "Bang cau hinh AI dung chung toan he thong."),
            ("api/views/admin_v.py", "ai_config", "Doc va cap nhat cau hinh AI tu giao dien admin."),
            ("api/views/admin_v.py", "ollama_models", "Lay danh sach model kha dung de admin chon."),
        ],
    },
    "accounts models\nUser / UserProfile /\nUserGroup / Membership": {
        "summary": "Cum model tai khoan, profile, nhom va membership dung trong man admin.",
        "files": ["accounts/models.py", "api/views/admin_v.py"],
        "refs": [
            ("api/views/admin_v.py", "user_list", "Liet ke va tao user moi."),
            ("api/views/admin_v.py", "group_list", "Liet ke va tao group moi."),
            ("api/views/admin_v.py", "group_members", "Gan/thao thanh vien vao group."),
        ],
    },
    "django call_command('dumpdata')": {
        "summary": "Loi goi backup JSON tu Django management command.",
        "files": ["api/views/admin_v.py"],
        "refs": [
            ("api/views/admin_v.py", "backup_create", "Goi dumpdata de tao file backup."),
            ("api/views/admin_v.py", "backup_list", "Liet ke cac file backup da co."),
            ("api/views/admin_v.py", "backup_download", "Cho phep tai file backup ve may client."),
        ],
    },
    "signing.permissions.py": {
        "summary": "Module quyen ky so, loc task ky va xac dinh ai co the xem packet/PDF.",
        "files": ["signing/permissions.py"],
        "refs": [
            ("signing/permissions.py", "get_signing_summary", "Tong hop KPI task ky theo quyen user."),
            ("signing/permissions.py", "get_accessible_signing_tasks", "Loc task ky ma user hien tai duoc xu ly."),
            ("signing/permissions.py", "get_accessible_signed_pdfs", "Loc danh sach PDF da ky user duoc xem."),
        ],
    },
    "signing/services.py": {
        "summary": "Service ky so trung tam dieu phoi packet, task, verify va file PDF dau ra.",
        "files": ["signing/services.py"],
        "refs": [
            ("signing/services.py", "get_signature_context_for_task", "Tong hop du lieu ky cho UI detail."),
            ("signing/services.py", "sign_task", "Ky task va cap nhat packet/task/signed PDF."),
            ("signing/services.py", "reject_task", "Tu choi task ky va dong bo trang thai."),
        ],
    },
    "signing/pki.py": {
        "summary": "Tang PKI/HSM ky so PDF incremental va xac thuc chu ky.",
        "files": ["signing/pki.py"],
        "refs": [
            ("signing/pki.py", "prepare_pdf_signature_fields", "Chuan bi field ky tren PDF."),
            ("signing/pki.py", "sign_pdf_incremental", "Ky incremental PDF bang local key hoac HSM."),
            ("signing/pki.py", "validate_pdf_signatures", "Xac thuc chu ky da co trong PDF."),
        ],
    },
    "documents/mailbox_services.py": {
        "summary": "Service hom thu dieu phoi forward, complete, reject va integrity cua thread xu ly van ban.",
        "files": ["documents/mailbox_services.py"],
        "refs": [
            ("documents/mailbox_services.py", "forward_document", "Tao buoc forward van ban vao hom thu nguoi nhan."),
            ("documents/mailbox_services.py", "complete_mailbox_entry", "Dong buoc xu ly hom thu."),
            ("documents/mailbox_services.py", "reject_mailbox_entry", "Danh dau buoc hom thu bi tu choi."),
        ],
    },
    "ai_engine/rag_search.py + rag_index.py": {
        "summary": "Cum ham truy hoi RAG gom text search, semantic search va dong bo chi muc vector.",
        "files": ["ai_engine/rag_search.py", "ai_engine/rag_index.py"],
        "refs": [
            ("ai_engine/rag_search.py", "_semantic_rank_map", "Tinh diem semantic retrieval tu vector store."),
            ("ai_engine/rag_search.py", "_db_search_templates", "Tim template lien quan trong nguon co quyen."),
            ("ai_engine/rag_index.py", "sync_document_index", "Dong bo embedding document vao vector index."),
        ],
    },
    "pdf_preview.py": {
        "summary": "Module build preview PDF cho document/template de frontend xem nhanh.",
        "files": ["documents/pdf_preview.py"],
        "refs": [
            ("documents/pdf_preview.py", "build_document_preview_pdf", "Sinh preview PDF cho document."),
            ("documents/pdf_preview.py", "build_template_preview_pdf", "Sinh preview PDF cho template."),
            ("documents/pdf_preview.py", "_run_libreoffice_convert", "Goi LibreOffice de convert sang PDF."),
        ],
    },
}

REASON_HINTS = {
    "build": "Dung layout, widget va mapping state ra giao dien.",
    "initState": "Khoi dong state va tai du lieu ban dau khi man hinh mo.",
    "didChangeDependencies": "Dong bo query param/route state voi man hinh hien tai.",
    "dispose": "Don dep controller va resource cua widget.",
    "_loadSessions": "Tai danh sach session tu backend de do lich su.",
    "_loadMessages": "Tai message cua session dang mo.",
    "_send": "Gui request tu UI xuong backend va cap nhat ket qua tra ve.",
    "_openHistoryManager": "Mo dialog quan ly lich su va xu ly xoa/mo lai thread.",
    "_newConversation": "Reset state de bat dau thread moi.",
    "_refreshTemplateCollections": "Invalidate provider de dong bo lai danh sach template sau khi sua.",
    "_resolveStoredDocxBytes": "Nap file DOCX goc de replace/export khi user dang sua template.",
    "_buildDocxFormData": "Dong goi payload FormData de gui template DOCX len API.",
    "query": "Gui cau hoi RAG va luu citations/session vao state provider.",
    "sendMessage": "Gui tin nhan chat AI va chen answer vao state provider.",
    "loadAssistantResult": "Nap ket qua RAG ma assistant da mirror sang provider.",
    "clear": "Xoa state runtime cua provider/man hinh.",
    "get_llm": "Khoi tao client model AI theo cau hinh hien tai.",
    "rag_query": "Thuc hien truy hoi context, goi model va tra citations.",
    "run_assistant_turn": "Dieu phoi 1 turn tro ly AI va chon tool phu hop.",
    "render_as_docx": "Sinh DOCX dau ra tu template da duoc dien bien.",
    "render": "Thay bien vao noi dung mau de tao output text/HTML.",
    "get_variables": "Rut danh sach bien trong template.",
    "sign_task": "Thuc hien ky so va cap nhat packet/task.",
    "reject_task": "Tu choi task ky va cap nhat trang thai packet.",
    "get_signature_context_for_task": "Tong hop du lieu ky hien thi cho UI detail.",
    "refresh_signed_pdf_verification": "Xac thuc lai chu ky trong PDF da ky.",
    "forward_document": "Forward van ban vao hom thu cua nguoi nhan.",
    "complete_mailbox_entry": "Dong luong xu ly hom thu khi da hoan tat.",
    "reject_mailbox_entry": "Danh dau buoc xu ly hom thu bi tu choi.",
    "list_trash_entries": "Tong hop danh sach doi tuong da xoa mem.",
    "restore_trash_items": "Phuc hoi doi tuong tu thung rac.",
    "permanently_delete_trash_items": "Xoa han doi tuong ra khoi he thong.",
}


@dataclass
class CodeRef:
    path: str
    symbol: str
    line: int | None
    reason: str


@dataclass
class RouteRef:
    route: str
    norm_route: str
    module: str
    handler: str
    path: str
    line: int


@dataclass
class Component:
    kind: str
    alias: str
    label: str
    raw: str


@dataclass
class DiagramContext:
    name: str
    title: str
    components: list[Component]
    route_refs: list[tuple[Component, RouteRef]]


def rel(path: Path | str) -> str:
    return str(Path(path).as_posix() if isinstance(path, str) else path.relative_to(ROOT).as_posix())


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def write_text(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8", newline="\n")


def normalize_label(label: str) -> str:
    label = label.replace("\\n", "\n")
    lines = []
    for line in label.split("\n"):
        line = re.sub(r"\s*\[F\d+\]\s*$", "", line).rstrip()
        lines.append(line)
    return "\n".join(lines).strip()


def normalize_route(route: str) -> str:
    route = route.strip()
    route = route.removeprefix("/").removeprefix("api/").removeprefix("/api/")
    route = route.strip("/")
    route = re.sub(r"<[^>]+>", "{param}", route)
    route = re.sub(r"\{[^}]+\}", "{param}", route)
    return route


def sanitize_path_hint(path: str) -> str:
    path = path.strip().replace("\\", "/")
    if (ROOT / path).exists():
        return path
    if path.endswith(".py") and "/" not in path and path.count(".") >= 2:
        parts = path.split(".")
        candidate = "/".join(parts[:-1]) + ".py"
        if (ROOT / candidate).exists():
            return candidate
    if "/" not in path and path.endswith((".py", ".dart")):
        basename = Path(path).name
        for candidate in ROOT.rglob(basename):
            if candidate.is_file():
                return rel(candidate)
    return path


def component_title(label: str) -> str:
    return normalize_label(label).replace("\n", " / ")


def load_route_map() -> dict[str, RouteRef]:
    text = read_text(API_URLS)
    lines = text.splitlines()
    mapping: dict[str, RouteRef] = {}
    for idx, line in enumerate(lines, start=1):
        match = ROUTE_RE.search(line)
        if not match:
            continue
        raw_route, module, handler = match.groups()
        norm = normalize_route(raw_route)
        mapping[norm] = RouteRef(
            route=raw_route,
            norm_route=norm,
            module=module,
            handler=handler,
            path=rel(ROOT / "api" / "views" / f"{module}.py"),
            line=idx,
        )
    return mapping


def scan_dart_classes() -> dict[str, list[str]]:
    mapping: dict[str, list[str]] = {}
    for path in (ROOT / "flutter_frontend" / "lib").rglob("*.dart"):
        text = read_text(path)
        for match in DART_CLASS_RE.finditer(text):
            mapping.setdefault(match.group(1), []).append(rel(path))
    return mapping


def find_line_literal(path: Path | str, literal: str, *, last: bool = False) -> int | None:
    p = ROOT / path if isinstance(path, str) else path
    lines = read_text(p).splitlines()
    hits = [idx for idx, line in enumerate(lines, start=1) if literal in line]
    if not hits:
        return None
    return hits[-1] if last else hits[0]


def find_def_line(path: Path | str, symbol: str, *, kind: str = "def", last: bool = True) -> int | None:
    p = ROOT / path if isinstance(path, str) else path
    lines = read_text(p).splitlines()
    if kind == "class":
        pattern = re.compile(rf"^\s*class\s+{re.escape(symbol)}\s*(?:\(|:)")
    elif kind == "provider":
        pattern = re.compile(rf"\b{re.escape(symbol)}\b")
    else:
        pattern = re.compile(rf"^\s*def\s+{re.escape(symbol)}\s*\(")
    hits = [idx for idx, line in enumerate(lines, start=1) if pattern.search(line)]
    if not hits:
        return None
    return hits[-1] if last else hits[0]


def find_dart_symbol_line(path: Path | str, symbol: str, *, class_symbol: bool = False) -> int | None:
    p = ROOT / path if isinstance(path, str) else path
    lines = read_text(p).splitlines()
    if class_symbol:
        pattern = re.compile(rf"^\s*class\s+{re.escape(symbol)}\s+")
    else:
        pattern = re.compile(rf"\b{re.escape(symbol)}\b")
    for idx, line in enumerate(lines, start=1):
        if pattern.search(line):
            return idx
    return None


def list_python_defs(path: str) -> list[str]:
    text = read_text(ROOT / path)
    return [m.group(1) for m in PY_DEF_RE.finditer(text)]


def list_dart_methods(path: str) -> list[str]:
    text = read_text(ROOT / path)
    methods = []
    for match in DART_METHOD_RE.finditer(text):
        name = match.group(1)
        if name in {"if", "for", "switch", "while", "catch"}:
            continue
        methods.append(name)
    return methods


def prettify_name(name: str) -> str:
    name = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", name)
    name = name.replace("_", " ")
    return name.strip()


def extract_keywords(ctx: DiagramContext, component: Component) -> set[str]:
    raw = " ".join(
        [
            ctx.title,
            ctx.name.replace(".puml", "").replace("_", " "),
            normalize_label(component.label).replace("\n", " "),
        ]
    ).lower()
    tokens = set(re.findall(r"[a-z][a-z0-9_]+", raw))
    extras = set()
    if "template" in tokens:
        extras |= {"template", "templates"}
    if "document" in tokens or "documents" in tokens:
        extras |= {"document", "documents"}
    if "signing" in tokens or "signed" in tokens:
        extras |= {"signing", "signed", "signature", "pdf"}
    if "mailbox" in tokens:
        extras |= {"mailbox", "forward", "complete", "reject"}
    if "guest" in tokens:
        extras |= {"guest", "parse", "generate", "cleanup"}
    if "backup" in tokens:
        extras |= {"backup", "download", "delete", "create"}
    if "approval" in tokens or "pending" in tokens:
        extras |= {"approve", "reject", "pending"}
    if "rag" in tokens or "assistant" in tokens or "chat" in tokens:
        extras |= {"chat", "rag", "assistant", "session", "message"}
    return tokens | extras


def score_symbol(symbol: str, keywords: set[str]) -> int:
    lowered = symbol.lower()
    score = 0
    if lowered == "build":
        score += 10
    if lowered in {"initstate", "didchangedependencies"}:
        score += 8
    for token in keywords:
        if token and token in lowered:
            score += 5
    for token in [
        "load",
        "send",
        "open",
        "create",
        "update",
        "delete",
        "preview",
        "sign",
        "reject",
        "approve",
        "download",
        "parse",
        "generate",
        "favorite",
        "archive",
        "restore",
        "query",
        "session",
        "message",
        "verify",
        "group",
        "user",
        "member",
    ]:
        if token in lowered:
            score += 3
    if lowered.startswith("_"):
        score += 1
    return score


def best_python_defs(path: str, keywords: set[str], limit: int = 3) -> list[str]:
    defs = list_python_defs(path)
    ranked = sorted(defs, key=lambda item: (-score_symbol(item, keywords), item))
    output = []
    for symbol in ranked:
        if symbol.startswith("__"):
            continue
        if symbol not in output:
            output.append(symbol)
        if len(output) >= limit:
            break
    return output


def best_dart_methods(path: str, keywords: set[str], limit: int = 3) -> list[str]:
    methods = list_dart_methods(path)
    ranked = sorted(methods, key=lambda item: (-score_symbol(item, keywords), item))
    output = []
    for symbol in ranked:
        if symbol in {"createState", "setState"}:
            continue
        if symbol and symbol[0].isupper():
            continue
        if symbol.startswith("_") and len(symbol) > 1 and symbol[1].isupper():
            continue
        if symbol not in output:
            output.append(symbol)
        if len(output) >= limit:
            break
    return output


def reason_for_symbol(symbol: str, fallback: str) -> str:
    return REASON_HINTS.get(symbol, fallback)


def wrap_lines(lines: list[str], width: int = 140) -> list[str]:
    wrapped: list[str] = []
    for line in lines:
        if not line:
            wrapped.append("")
            continue
        indent = re.match(r"^\s*", line).group(0)
        content = line[len(indent) :]
        parts = textwrap.wrap(
            content,
            width=width,
            break_long_words=False,
            break_on_hyphens=False,
            initial_indent=indent,
            subsequent_indent=indent + "  ",
        )
        wrapped.extend(parts or [line])
    return wrapped


def build_ref(path: str, symbol: str, reason: str, *, kind: str = "def", line_hint: str | None = None) -> CodeRef:
    path = sanitize_path_hint(path)
    if line_hint:
        line = find_line_literal(path, line_hint, last=True)
    else:
        line = find_def_line(path, symbol, kind=kind, last=True)
        if line is None and kind == "provider":
            line = find_dart_symbol_line(path, symbol)
    return CodeRef(path=path, symbol=symbol, line=line, reason=reason)


def build_dart_ref(path: str, symbol: str, reason: str) -> CodeRef:
    path = sanitize_path_hint(path)
    return CodeRef(path=path, symbol=symbol, line=find_dart_symbol_line(path, symbol), reason=reason)


def route_ref_from_label(label: str, route_map: dict[str, RouteRef]) -> RouteRef | None:
    clean = normalize_label(label).replace("\n", " ")
    match = re.search(r"/api/([^\s]+)", clean)
    if not match:
        return None
    norm = normalize_route(match.group(1))
    return route_map.get(norm)


def find_router_line_for_screen(screen_name: str) -> int | None:
    return find_line_literal(ROUTER_DART, screen_name)


def determine_screen_file(screen_name: str, dart_classes: dict[str, list[str]]) -> str | None:
    if screen_name in SCREEN_FILE_OVERRIDES:
        return SCREEN_FILE_OVERRIDES[screen_name]
    matches = dart_classes.get(screen_name, [])
    if not matches:
        return None
    if len(matches) == 1:
        return matches[0]
    return sorted(matches)[0]


def component_from_match(match: re.Match[str]) -> Component:
    indent, kind, label, alias, rest = match.groups()
    raw = match.group(0)
    return Component(kind=kind, alias=alias, label=label, raw=raw)


def parse_components(text: str) -> list[Component]:
    return [component_from_match(match) for match in ENTITY_RE.finditer(text)]


def parse_index_rectangles(text: str) -> list[Component]:
    items: list[Component] = []
    for match in INDEX_RECT_RE.finditer(text):
        prefix, label = match.groups()
        raw = match.group(0)
        items.append(Component(kind="rectangle", alias="", label=label, raw=raw))
    return items


def build_context(path: Path, text: str, route_map: dict[str, RouteRef]) -> DiagramContext:
    title_match = TITLE_RE.search(text)
    title = title_match.group(1).strip() if title_match else path.stem
    components = parse_components(text)
    route_refs: list[tuple[Component, RouteRef]] = []
    for component in components:
        route = route_ref_from_label(component.label, route_map)
        if route:
            route_refs.append((component, route))
    return DiagramContext(name=path.name, title=title, components=components, route_refs=route_refs)


def route_handlers_for_path(ctx: DiagramContext, path: str) -> list[RouteRef]:
    return [route for _, route in ctx.route_refs if route.path == path]


def route_handlers_for_component(ctx: DiagramContext) -> list[RouteRef]:
    return [route for _, route in ctx.route_refs]


def special_component_footnote(label: str) -> dict | None:
    return SPECIAL_COMPONENTS.get(normalize_label(label))


def footnote_for_actor(ctx: DiagramContext, component: Component) -> tuple[str, list[str], list[CodeRef]]:
    summary = f"Tac nhan ben ngoai kich hoat luong {ctx.title} thong qua giao dien web va API."
    files = [
        "Khong phai file ma nguon; tac dong vao he thong qua router Flutter va REST API."
    ]
    refs = [
        build_ref("my_tennis_club/urls.py", "flutter_app", "Nhan URL dau vao va tra shell Flutter web."),
        build_dart_ref("flutter_frontend/lib/core/router.dart", "routerProvider", "Dieu huong user vao man phu hop sau khi mo route."),
        CodeRef(
            path="flutter_frontend/lib/core/api_client.dart",
            symbol="_internal",
            line=find_line_literal("flutter_frontend/lib/core/api_client.dart", "ApiClient._internal"),
            reason="Gan JWT va gui request tu phia client.",
        ),
    ]
    return summary, files, refs


def footnote_for_root_router() -> tuple[str, list[str], list[CodeRef]]:
    summary = "Entry point route chung giua Django API va Flutter Web shell."
    files = ["my_tennis_club/urls.py"]
    refs = [
        build_ref("my_tennis_club/urls.py", "flutter_app", "Phuc vu index.html hoac file build Flutter khi mo route frontend."),
        build_ref("my_tennis_club/urls.py", "path('api/'", "Dang ky namespace API ve api.urls.", kind="literal", line_hint="path('api/'"),
        build_ref("my_tennis_club/urls.py", "re_path", "Bat moi route con lai de frontend tu xu ly deep-link.", kind="literal", line_hint="re_path(r'^(?P<path>.*)$'"),
    ]
    return summary, files, refs


def footnote_for_entry_client() -> tuple[str, list[str], list[CodeRef]]:
    summary = "Ha tang Flutter dieu huong route va dong bo HTTP/JWT/timeout voi backend."
    files = [
        "flutter_frontend/lib/core/router.dart",
        "flutter_frontend/lib/core/api_client.dart",
    ]
    refs = [
        build_dart_ref("flutter_frontend/lib/core/router.dart", "routerProvider", "Khai bao GoRouter va map cac route sang man Flutter."),
        CodeRef(
            path="flutter_frontend/lib/core/api_client.dart",
            symbol="_internal",
            line=find_line_literal("flutter_frontend/lib/core/api_client.dart", "ApiClient._internal"),
            reason="Khoi tao Dio, chen Authorization va retry refresh token.",
        ),
        build_dart_ref("flutter_frontend/lib/core/api_client.dart", "_isOllamaEndpoint", "Nang timeout cho cac endpoint AI/chuyen doi tai lieu."),
    ]
    return summary, files, refs


def footnote_for_api_endpoint(ctx: DiagramContext, component: Component, route: RouteRef) -> tuple[str, list[str], list[CodeRef]]:
    methods = normalize_label(component.label).split(" /api/", 1)[0].strip()
    summary = f"Endpoint REST {methods} /api/{route.route} duoc frontend goi trong luong {ctx.title}."
    files = ["api/urls.py", route.path]
    refs = [
        CodeRef(path="api/urls.py", symbol=f"path('{route.route}', {route.module}.{route.handler})", line=route.line, reason="Dang ky URL voi ham xu ly tuong ung."),
        build_ref(route.path, route.handler, "Xu ly request va tra JSON/file cho frontend."),
    ]
    downstream = downstream_refs_for_handler(route.handler)
    refs.extend(downstream)
    return summary, files, refs[:3]


def downstream_refs_for_handler(handler: str) -> list[CodeRef]:
    mapping = {
        "rag_query_view": [build_ref("ai_engine/rag_engine.py", "rag_query", "Truy hoi context va goi model RAG.")],
        "rag_sessions": [build_ref("api/trash_services.py", "soft_delete_chat_sessions", "Xu ly xoa mem session RAG khi nguoi dung xoa lich su.")],
        "assistant_turn": [build_ref("ai_engine/assistant_engine.py", "run_assistant_turn", "Dieu phoi turn tro ly AI.")],
        "assistant_sessions": [build_ref("api/trash_services.py", "soft_delete_chat_sessions", "Xoa mem session assistant/voice da chon.")],
        "assistant_audio_download": [build_ref("api/views/assistant.py", "assistant_audio_download", "Tra file audio da luu cho client tai ve.")],
        "ai_doc_create": [build_ref("document_templates/models.py", "render_as_docx", "Sinh DOCX tu template va bo bien da dien.")],
        "ai_doc_extract_pdf": [build_ref("ai_engine/rag_engine.py", "extract_pdf_text", "Rut text/OCR tu PDF de dien bien.")],
        "ai_doc_extract_image": [build_ref("api/views/ai_doc.py", "ai_doc_extract_image", "Xu ly OCR/AI tren anh upload.")],
        "ai_doc_prefill_profile": [build_ref("ai_engine/rag_engine.py", "get_llm", "Khoi tao model AI de goi y field profile.")],
        "template_generate_tags": [build_ref("ai_engine/rag_engine.py", "get_llm", "Khoi tao model AI de sinh tag cho template.")],
        "template_import_docx": [build_ref("api/views/templates.py", "_extract_docx_text", "Rut text tu DOCX de detect bien/import.")],
        "template_import_from_url": [build_ref("api/views/templates.py", "_filename_stem_from_url", "Chuan hoa ten nguon va metadata khi import tu URL.")],
        "bulk_parse_excel": [build_ref("api/views/bulk_upload.py", "_vn_normalize", "Chuan hoa ten cot/du lieu khi parse Excel.")],
        "bulk_upload_single": [build_ref("api/views/bulk_upload.py", "bulk_upload_single", "Upload tung mau trong luong bulk.")],
        "template_replace_docx": [build_ref("api/views/bulk_upload.py", "template_replace_docx", "Thay file DOCX goc cua template.")],
        "signing_summary": [build_ref("signing/permissions.py", "get_signing_summary", "Tong hop KPI task ky theo quyen user.")],
        "signing_task_signature_context": [build_ref("signing/services.py", "get_signature_context_for_task", "Tong hop du lieu ky/credential cho UI detail.")],
        "signing_task_sign": [build_ref("signing/services.py", "sign_task", "Thuc hien ky so va cap nhat packet/task.")],
        "signing_task_reject": [build_ref("signing/services.py", "reject_task", "Tu choi task ky va cap nhat trang thai.")],
        "signed_pdf_verify": [build_ref("signing/services.py", "refresh_signed_pdf_verification", "Xac thuc lai chu ky tren PDF da ky.")],
        "mailbox_entry_forward": [build_ref("documents/mailbox_services.py", "forward_document", "Tao buoc forward trong hom thu.")],
        "mailbox_entry_complete": [build_ref("documents/mailbox_services.py", "complete_mailbox_entry", "Dong buoc xu ly hom thu.")],
        "mailbox_entry_reject": [build_ref("documents/mailbox_services.py", "reject_mailbox_entry", "Danh dau buoc hom thu bi tu choi.")],
        "mailbox_entry_sign": [build_ref("signing/services.py", "sign_task", "Ky task duoc tao ra tu mailbox entry.")],
        "trash_restore": [build_ref("api/trash_services.py", "restore_trash_items", "Phuc hoi doi tuong da xoa mem.")],
        "trash_delete": [build_ref("api/trash_services.py", "permanently_delete_trash_items", "Xoa han doi tuong ra khoi he thong.")],
        "trash_entries": [build_ref("api/trash_services.py", "list_trash_entries", "Tong hop danh sach thung rac cho client.")],
        "prefill_from_bio": [build_ref("ai_engine/rag_engine.py", "get_llm", "Khoi tao model AI de trich thong tin tu bio.")],
        "ai_config": [build_ref("accounts/models.py", "GlobalAIConfig", "Doc/ghi cau hinh AI dung chung.", kind="class")],
        "ollama_models": [build_ref("api/views/admin_v.py", "ollama_models", "Tra danh sach model kha dung cho giao dien admin.")],
        "backup_create": [build_ref("api/views/admin_v.py", "backup_create", "Tao file backup dumpdata.")],
        "guest_parse_template": [build_ref("api/views/guest_portal_cookie.py", "_auto_detect_template_variables", "Detect bien tren template guest.")],
        "guest_parse_pdf": [build_ref("api/views/guest_portal_cookie.py", "_extract_pdf_text", "OCR/rut text tu PDF guest upload.")],
        "guest_generate": [build_ref("api/views/guest_portal_cookie.py", "_apply_replacements_to_docx", "Thay bien vao template guest de sinh tai lieu.")],
        "dashboard_stats": [build_ref("api/views/dashboard.py", "_build_org_structure", "Tong hop du lieu dashboard va cay to chuc.")],
        "dashboard_org_node_stats": [build_ref("api/views/dashboard.py", "_can_view_org_node_stats", "Kiem tra quyen xem thong ke nut to chuc.")],
        "pending_approvals_count": [build_ref("api/views/dashboard.py", "pending_approvals_count", "Dem so yeu cau cho phe duyet.")],
    }
    return mapping.get(handler, [])


def footnote_for_screen(ctx: DiagramContext, component: Component, dart_classes: dict[str, list[str]]) -> tuple[str, list[str], list[CodeRef]] | None:
    screen = normalize_label(component.label).split("\n", 1)[0].strip()
    path = determine_screen_file(screen, dart_classes)
    if not path:
        return None
    summary = f"Man hinh Flutter dung de hien thi va dieu phoi thao tac cua {prettify_name(screen.replace('Screen', ''))}."
    files = [path, "flutter_frontend/lib/core/router.dart"]
    refs: list[CodeRef] = []
    router_line = find_router_line_for_screen(screen)
    refs.append(CodeRef(path="flutter_frontend/lib/core/router.dart", symbol=screen, line=router_line, reason="Route builder dung man nay khi URL khop."))
    methods = best_dart_methods(path, extract_keywords(ctx, component), limit=3)
    for symbol in methods:
        refs.append(
            CodeRef(
                path=path,
                symbol=symbol,
                line=find_dart_symbol_line(path, symbol),
                reason=reason_for_symbol(symbol, "Thuc hien mot phan logic UI hoac goi API tu man hinh nay."),
            )
        )
    dedup: list[CodeRef] = []
    seen = set()
    for ref in refs:
        key = (ref.path, ref.symbol)
        if key not in seen:
            seen.add(key)
            dedup.append(ref)
    return summary, files, dedup[:3]


def footnote_for_provider(ctx: DiagramContext, component: Component) -> tuple[str, list[str], list[CodeRef]] | None:
    label = normalize_label(component.label)
    symbols = [token.strip() for token in label.replace(".dart", "").split("\n") if token.strip()]
    provider_names = []
    file_hint = None
    for token in symbols:
        if token in PROVIDER_FILE_HINTS:
            provider_names.append(token)
            file_hint = PROVIDER_FILE_HINTS[token]
        if token.endswith("Provider") and token not in provider_names:
            provider_names.append(token)
            file_hint = file_hint or PROVIDER_FILE_HINTS.get(token)
    if not file_hint and ".dart" in label:
        match = re.search(r"([A-Za-z0-9_/.-]+\.dart)", label)
        if match:
            file_hint = match.group(1).replace("\\", "/")
    if not file_hint:
        return None
    summary = "Provider Flutter quan ly state, goi API va dong bo du lieu cho man hinh lien quan."
    files = [file_hint]
    refs: list[CodeRef] = []
    for provider in provider_names:
        refs.append(
            CodeRef(
                path=file_hint,
                symbol=provider,
                line=find_dart_symbol_line(file_hint, provider),
                reason="Diem dang ky provider de widget tree watch/read du lieu.",
            )
        )
    methods = best_dart_methods(file_hint, extract_keywords(ctx, component), limit=3)
    for symbol in methods:
        reason = "Khoi tao state mac dinh cua provider." if symbol == "build" else reason_for_symbol(symbol, "Xu ly state va goi backend cho provider nay.")
        refs.append(
            CodeRef(
                path=file_hint,
                symbol=symbol,
                line=find_dart_symbol_line(file_hint, symbol),
                reason=reason,
            )
        )
    dedup: list[CodeRef] = []
    seen = set()
    for ref in refs:
        key = (ref.path, ref.symbol)
        if key not in seen:
            seen.add(key)
            dedup.append(ref)
    return summary, files, dedup[:3]


def footnote_for_special(ctx: DiagramContext, component: Component) -> tuple[str, list[str], list[CodeRef]] | None:
    hint = special_component_footnote(component.label)
    if not hint:
        return None
    refs = [build_ref(path, symbol, reason, kind="class" if symbol and symbol[0].isupper() and "(" not in symbol and "/" not in symbol else "def") for path, symbol, reason in hint["refs"]]
    return hint["summary"], hint["files"], refs


def footnote_for_module(ctx: DiagramContext, component: Component) -> tuple[str, list[str], list[CodeRef]] | None:
    label = normalize_label(component.label)
    file_match = re.search(r"([A-Za-z0-9_/.-]+\.py)", label)
    if not file_match:
        return None
    path = sanitize_path_hint(file_match.group(1))
    summary = f"Module backend {path} tham gia xu ly luong {ctx.title}."
    files = [path]
    explicit_symbols = re.findall(r"([A-Za-z_][A-Za-z0-9_]*)\(\)", label)
    refs: list[CodeRef] = []
    for symbol in explicit_symbols:
        refs.append(
            CodeRef(
                path=path,
                symbol=symbol,
                line=find_def_line(path, symbol, kind="def", last=True),
                reason=reason_for_symbol(symbol, "Ham duoc ghi ro ngay trong nhan cua component nay."),
            )
        )
    if not refs:
        handlers = route_handlers_for_path(ctx, path)
        for route in handlers[:3]:
            refs.append(
                CodeRef(
                    path=path,
                    symbol=route.handler,
                    line=find_def_line(path, route.handler, kind="def", last=True),
                    reason="Ham xu ly API trong cung so do dang tro vao module nay.",
                )
            )
    if not refs:
        for symbol in best_python_defs(path, extract_keywords(ctx, component), limit=3):
            refs.append(
                CodeRef(
                    path=path,
                    symbol=symbol,
                    line=find_def_line(path, symbol, kind="def", last=True),
                    reason=reason_for_symbol(symbol, "Ham chinh duoc module nay goi trong luong hien tai."),
                )
            )
    return summary, files, refs[:3]


def footnote_for_explicit_model_method(component: Component) -> tuple[str, list[str], list[CodeRef]] | None:
    label = normalize_label(component.label)
    if "DocumentTemplate.render_as_docx()" in label:
        return footnote_for_special(None, component)  # type: ignore[arg-type]
    return None


def footnote_for_infra(ctx: DiagramContext, component: Component) -> tuple[str, list[str], list[CodeRef]] | None:
    label = normalize_label(component.label)
    if label not in INFRA_SUMMARY:
        return None
    summary = INFRA_SUMMARY[label]
    files = []
    refs: list[CodeRef] = []
    if label == "PostgreSQL":
        files = ["my_tennis_club/settings.py", "cac file models.py lien quan den so do hien tai"]
        for route in route_handlers_for_component(ctx)[:3]:
            refs.append(
                CodeRef(
                    path=route.path,
                    symbol=route.handler,
                    line=find_def_line(route.path, route.handler, kind="def", last=True),
                    reason="Ham nay doc/ghi bang du lieu nghiep vu tren PostgreSQL trong luong hien tai.",
                )
            )
    elif label == "PGVector":
        files = ["ai_engine/rag_search.py", "ai_engine/rag_index.py"]
        refs = [
            build_ref("ai_engine/rag_search.py", "_semantic_rank_map", "Doc vector similarity tu collection semantic."),
            build_ref("ai_engine/rag_index.py", "sync_template_index", "Dong bo embedding cho template vao vector store."),
            build_ref("ai_engine/rag_index.py", "sync_document_index", "Dong bo embedding cho document vao vector store."),
        ]
    elif label == "Media Storage":
        files = ["documents/models.py", "ai_engine/models.py", "signing/services.py"]
        refs = [
            build_ref("documents/models.py", "Document", "Luu output_file va artefact cua document.", kind="class"),
            build_ref("ai_engine/models.py", "ChatAudioAttachment", "Luu tep ghi am cua tro ly voice.", kind="class"),
            build_ref("signing/services.py", "_copy_path_to_field", "Sao chep file PDF da ky vao field luu tru."),
        ]
    elif label == "Ollama":
        files = ["ai_engine/rag_engine.py", "my_tennis_club/settings.py"]
        refs = [
            build_ref("ai_engine/rag_engine.py", "get_llm", "Khoi tao client model AI."),
            build_ref("ai_engine/rag_engine.py", "rag_query", "Goi model de tong hop cau tra loi co citations."),
            build_ref("ai_engine/assistant_engine.py", "run_assistant_turn", "Dieu phoi assistant va goi model khi can."),
        ]
    elif label == "Remote HSM optional":
        files = ["signing/pki.py", "signing/services.py"]
        refs = [
            build_ref("signing/pki.py", "RemoteHsmSigner", "Dong goi adapter ky so tu xa.", kind="class"),
            build_ref("signing/pki.py", "sign_pdf_incremental", "Ky incremental PDF bang PKCS7/HSM."),
            build_ref("signing/services.py", "sign_task", "Goi tang PKI/HSM khi user ky task."),
        ]
    elif label == "Excel import files":
        files = ["api/views/admin_v.py"]
        refs = [
            build_ref("api/views/admin_v.py", "import_users_template", "Sinh mau Excel de nguoi dung dien du lieu."),
            build_ref("api/views/admin_v.py", "import_users_excel", "Doc file Excel va tao/sua user."),
            build_ref("api/views/admin_v.py", "_col_idx", "Map ten cot trong file Excel sang logic import."),
        ]
    elif label == "backups/*.json":
        files = ["api/views/admin_v.py"]
        refs = [
            build_ref("api/views/admin_v.py", "backup_create", "Tao file JSON backup."),
            build_ref("api/views/admin_v.py", "backup_list", "Liet ke backup trong thu muc."),
            build_ref("api/views/admin_v.py", "backup_delete", "Xoa file backup khong con can dung."),
        ]
    elif label == "media/guest_sessions":
        files = ["api/views/guest_portal_cookie.py"]
        refs = [
            build_ref("api/views/guest_portal_cookie.py", "_guest_root", "Xac dinh thu muc luu session guest."),
            build_ref("api/views/guest_portal_cookie.py", "_store_guest_template", "Luu template guest vao media/guest_sessions."),
            build_ref("api/views/guest_portal_cookie.py", "guest_cleanup", "Don session tam khoi thu muc guest."),
        ]
    elif label == "Ollama optional for detect":
        files = ["api/views/guest_portal_cookie.py", "ai_engine/rag_engine.py"]
        refs = [
            build_ref("api/views/guest_portal_cookie.py", "_auto_detect_template_variables", "Co the goi AI de detect bien trong template guest."),
            build_ref("ai_engine/rag_engine.py", "get_llm", "Khoi tao model AI neu guest flow can detect nang cao."),
        ]
    return summary, files, refs[:3]


def footnote_for_rectangle(component: Component) -> tuple[str, list[str], list[CodeRef]]:
    label = normalize_label(component.label)
    summary = f"Khoi tong hop trong file PlantUML index dung de nhom cac so do theo chu de: {label}."
    files = ["plantuml_nav/00_NAV_INDEX.puml"]
    refs = [
        CodeRef(path="plantuml_nav/00_NAV_INDEX.puml", symbol="rectangle", line=find_line_literal("plantuml_nav/00_NAV_INDEX.puml", f'rectangle "{label.splitlines()[0]}'), reason="Khai bao khoi nhom trong file index PlantUML."),
    ]
    return summary, files, refs


def index_marker(raw: str, marker: str) -> str:
    match = INDEX_RECT_RE.match(raw)
    if not match:
        return raw
    prefix, label = match.groups()
    clean = normalize_label(label)
    return f'{prefix} "{clean} [{marker}]" {{'


def generic_component_footnote(ctx: DiagramContext, component: Component) -> tuple[str, list[str], list[CodeRef]]:
    label = normalize_label(component.label)
    summary = f"Thanh phan {component_title(component.label)} trong luong {ctx.title}."
    files = ["Chua suy ra duoc file cu the tu nhan component; can bo sung tay neu muon rat sat runtime."]
    refs: list[CodeRef] = []
    return summary, files, refs


def build_footnote(ctx: DiagramContext, component: Component, route_map: dict[str, RouteRef], dart_classes: dict[str, list[str]]) -> tuple[str, list[str], list[CodeRef]]:
    route = route_ref_from_label(component.label, route_map)
    if component.kind == "actor":
        return footnote_for_actor(ctx, component)
    if component.kind == "rectangle":
        return footnote_for_rectangle(component)
    if normalize_label(component.label) == "Root Router\nmy_tennis_club/urls.py":
        return footnote_for_root_router()
    if normalize_label(component.label) == "GoRouter + ApiClient":
        return footnote_for_entry_client()
    if route:
        return footnote_for_api_endpoint(ctx, component, route)
    special = footnote_for_special(ctx, component)
    if special:
        return special
    if component.kind in {"database", "folder", "cloud"}:
        infra = footnote_for_infra(ctx, component)
        if infra:
            return infra
    provider = footnote_for_provider(ctx, component)
    if provider:
        return provider
    screen = footnote_for_screen(ctx, component, dart_classes)
    if screen:
        return screen
    module = footnote_for_module(ctx, component)
    if module:
        return module
    return generic_component_footnote(ctx, component)


def inject_marker(raw: str, marker: str) -> str:
    match = ENTITY_RE.match(raw)
    if not match:
        return raw
    indent, kind, label, alias, rest = match.groups()
    clean = normalize_label(label)
    if "\n" in clean:
        lines = clean.split("\n")
        lines[-1] = f"{lines[-1]} [{marker}]"
        clean = "\n".join(lines)
    else:
        clean = f"{clean} [{marker}]"
    escaped = clean.replace("\n", "\\n")
    return f'{indent}{kind} "{escaped}" as {alias}{rest}'


def format_footnote_block(entries: list[tuple[str, Component, tuple[str, list[str], list[CodeRef]]]]) -> str:
    lines = ["note bottom", "Footnotes"]
    for marker, component, (summary, files, refs) in entries:
        lines.append(f"[{marker}] {component_title(component.label)}")
        lines.append(f"- Chuc nang: {summary}")
        lines.append(f"- File: {'; '.join(files)}")
        if refs:
            lines.append("- Ham / diem lien quan:")
            for ref in refs:
                location = f"{ref.path}:{ref.line if ref.line is not None else '?'}"
                lines.append(f"  - {ref.symbol} | {location} | {ref.reason}")
        else:
            lines.append("- Ham / diem lien quan: Khong co ham rieng; day la thanh phan khai niem hoac ha tang.")
        lines.append("")
    lines.append("end note")
    return "\n".join(wrap_lines(lines))


def replace_bottom_note(text: str, block: str) -> str:
    if NOTE_BOTTOM_RE.search(text):
        return NOTE_BOTTOM_RE.sub("\n" + block, text, count=1)
    return text.replace("@enduml", "\n" + block + "\n\n@enduml")


def rewrite_diagram(path: Path, route_map: dict[str, RouteRef], dart_classes: dict[str, list[str]]) -> None:
    text = read_text(path)
    ctx = build_context(path, text, route_map)
    components = parse_components(text)
    entries: list[tuple[str, Component, tuple[str, list[str], list[CodeRef]]]] = []
    rebuilt = text

    for index, component in enumerate(components, start=1):
        marker = f"F{index:02d}"
        footnote = build_footnote(ctx, component, route_map, dart_classes)
        entries.append((marker, component, footnote))
        rebuilt = rebuilt.replace(component.raw, inject_marker(component.raw, marker), 1)

    block = format_footnote_block(entries)
    rebuilt = replace_bottom_note(rebuilt, block)
    write_text(path, rebuilt)


def rewrite_index_diagram(path: Path) -> None:
    text = read_text(path)
    components = parse_index_rectangles(text)
    entries: list[tuple[str, Component, tuple[str, list[str], list[CodeRef]]]] = []
    rebuilt = text
    for index, component in enumerate(components, start=1):
        marker = f"F{index:02d}"
        footnote = footnote_for_rectangle(component)
        entries.append((marker, component, footnote))
        rebuilt = rebuilt.replace(component.raw, index_marker(component.raw, marker), 1)
    block = format_footnote_block(entries)
    rebuilt = replace_bottom_note(rebuilt, block)
    write_text(path, rebuilt)


def main() -> None:
    route_map = load_route_map()
    dart_classes = scan_dart_classes()
    for path in sorted(PLANTUML_DIR.glob("*.puml")):
        if path.name == "00_NAV_INDEX.puml":
            rewrite_index_diagram(path)
        else:
            rewrite_diagram(path, route_map, dart_classes)
        print(f"updated {rel(path)}")


if __name__ == "__main__":
    main()
