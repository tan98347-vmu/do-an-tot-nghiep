from __future__ import annotations

import argparse
import ast
import re
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE_SUFFIXES = {".py", ".dart", ".html", ".css", ".js"}
EXCLUDED_PARTS = {
    "migrations",
    ".dart_tool",
    "__pycache__",
    "build",
    "media",
    "backups",
    "flutter_app",
    ".git",
    ".claude",
    ".codex-tmp-pyc",
    "tools",
}

DIAGRAM_RELATED = {
    "SO_DO_KIEN_TRUC_TONG_THE_HE_THONG.puml": [
        "api/urls.py",
        "flutter_frontend/lib/core/router.dart",
        "flutter_frontend/lib/core/api_client.dart",
        "accounts/models.py",
        "document_templates/models.py",
        "documents/models.py",
        "ai_engine/models.py",
        "signing/models.py",
        "documents/mailbox_services.py",
        "signing/services.py",
        "api/serializers/documents.py",
        "api/serializers/templates.py",
    ],
    "plantuml_nav/00_NAV_INDEX.puml": [
        "SO_DO_KIEN_TRUC_TONG_THE_HE_THONG.puml",
    ],
    "plantuml_nav/01_dashboard_nav.puml": [
        "flutter_frontend/lib/screens/dashboard/dashboard_screen.dart",
        "flutter_frontend/lib/screens/dashboard/dashboard_hub_screen.dart",
        "flutter_frontend/lib/providers/dashboard_provider.dart",
        "flutter_frontend/lib/models/dashboard_stats.dart",
        "api/serializers/notifications.py",
        "api/views/notifications.py",
        "templates/dashboard/index.html",
    ],
    "plantuml_nav/02_generate_from_template_nav.puml": [
        "flutter_frontend/lib/screens/ai_doc/ai_doc_screen.dart",
        "flutter_frontend/lib/screens/ai_doc/ai_doc_fill_screen.dart",
        "flutter_frontend/lib/providers/templates_provider.dart",
        "api/serializers/templates.py",
        "documents/models.py",
    ],
    "plantuml_nav/03_document_qa_nav.puml": [
        "flutter_frontend/lib/screens/rag/rag_screen.dart",
        "flutter_frontend/lib/screens/rag/rag_history_screen.dart",
        "flutter_frontend/lib/providers/chat_provider.dart",
        "flutter_frontend/lib/models/chat.dart",
        "api/serializers/chat.py",
        "documents/models.py",
    ],
    "plantuml_nav/04_ai_assistant_nav.puml": [
        "flutter_frontend/lib/screens/assistant/chat_ai_hub_screen.dart",
        "flutter_frontend/lib/screens/assistant/assistant_chat_screen.dart",
        "flutter_frontend/lib/screens/assistant/assistant_voice_screen.dart",
        "flutter_frontend/lib/screens/assistant/assistant_audio_library_screen.dart",
        "flutter_frontend/lib/screens/assistant/assistant_rag_result_screen.dart",
        "flutter_frontend/lib/providers/chat_provider.dart",
        "flutter_frontend/lib/models/chat.dart",
        "api/serializers/chat.py",
        "ai_engine/models.py",
    ],
    "plantuml_nav/05_signing_requests_nav.puml": [
        "flutter_frontend/lib/screens/signing/signing_inbox_screen_modern.dart",
        "flutter_frontend/lib/screens/signing/signing_inbox_screen.dart",
        "flutter_frontend/lib/providers/signing_summary_provider.dart",
        "flutter_frontend/lib/models/signing.dart",
        "api/serializers/signing.py",
    ],
    "plantuml_nav/06_signed_pdfs_nav.puml": [
        "flutter_frontend/lib/screens/signing/signed_pdf_list_screen_modern.dart",
        "flutter_frontend/lib/screens/signing/signed_pdf_list_screen.dart",
        "flutter_frontend/lib/screens/signing/signed_pdf_detail_screen_pki.dart",
        "flutter_frontend/lib/screens/signing/signed_pdf_detail_screen.dart",
        "flutter_frontend/lib/models/signing.dart",
        "api/serializers/signing.py",
    ],
    "plantuml_nav/07_mailbox_nav.puml": [
        "flutter_frontend/lib/screens/documents/mailbox_screen_modern.dart",
        "flutter_frontend/lib/screens/documents/mailbox_screen.dart",
        "flutter_frontend/lib/screens/documents/mailbox_detail_screen_modern.dart",
        "flutter_frontend/lib/screens/documents/mailbox_detail_screen.dart",
        "flutter_frontend/lib/providers/documents_provider.dart",
        "flutter_frontend/lib/models/document.dart",
        "api/serializers/documents.py",
    ],
    "plantuml_nav/08_signing_delegation_nav.puml": [
        "flutter_frontend/lib/screens/signing/signing_delegation_screen.dart",
        "flutter_frontend/lib/models/signing.dart",
        "api/serializers/signing.py",
        "signing/permissions.py",
    ],
    "plantuml_nav/09_create_template_nav.puml": [
        "flutter_frontend/lib/screens/templates/template_creation_hub_screen.dart",
        "flutter_frontend/lib/screens/templates/template_form_screen.dart",
        "flutter_frontend/lib/screens/templates/bulk_upload_screen.dart",
        "flutter_frontend/lib/providers/templates_provider.dart",
        "flutter_frontend/lib/models/template.dart",
        "api/serializers/templates.py",
        "document_templates/forms.py",
    ],
    "plantuml_nav/10_templates_shared_nav.puml": [
        "flutter_frontend/lib/screens/templates/template_list_screen.dart",
        "flutter_frontend/lib/screens/templates/template_detail_screen.dart",
        "flutter_frontend/lib/providers/templates_provider.dart",
        "flutter_frontend/lib/models/template.dart",
        "api/serializers/templates.py",
    ],
    "plantuml_nav/11_templates_my_department_nav.puml": [
        "flutter_frontend/lib/screens/templates/template_list_screen.dart",
        "flutter_frontend/lib/providers/templates_provider.dart",
        "flutter_frontend/lib/models/template.dart",
        "api/serializers/templates.py",
    ],
    "plantuml_nav/12_templates_my_private_nav.puml": [
        "flutter_frontend/lib/screens/templates/template_list_screen.dart",
        "flutter_frontend/lib/providers/templates_provider.dart",
        "flutter_frontend/lib/models/template.dart",
        "api/serializers/templates.py",
    ],
    "plantuml_nav/13_templates_favorites_nav.puml": [
        "flutter_frontend/lib/screens/templates/template_list_screen.dart",
        "flutter_frontend/lib/providers/templates_provider.dart",
        "flutter_frontend/lib/models/template.dart",
        "api/serializers/templates.py",
    ],
    "plantuml_nav/14_templates_admin_nav.puml": [
        "flutter_frontend/lib/screens/admin/admin_screen.dart",
        "flutter_frontend/lib/providers/templates_provider.dart",
        "flutter_frontend/lib/models/template.dart",
        "api/serializers/admin_s.py",
        "templates/admin_panel/knowledge.html",
    ],
    "plantuml_nav/15_documents_my_nav.puml": [
        "flutter_frontend/lib/screens/documents/document_list_screen.dart",
        "flutter_frontend/lib/screens/documents/document_detail_screen.dart",
        "flutter_frontend/lib/providers/documents_provider.dart",
        "flutter_frontend/lib/models/document.dart",
        "api/serializers/documents.py",
        "documents/pdf_preview.py",
    ],
    "plantuml_nav/16_documents_group_nav.puml": [
        "flutter_frontend/lib/screens/documents/document_list_screen.dart",
        "flutter_frontend/lib/providers/documents_provider.dart",
        "flutter_frontend/lib/models/document.dart",
        "api/serializers/documents.py",
    ],
    "plantuml_nav/17_documents_public_nav.puml": [
        "flutter_frontend/lib/screens/documents/document_list_screen.dart",
        "flutter_frontend/lib/providers/documents_provider.dart",
        "flutter_frontend/lib/models/document.dart",
        "api/serializers/documents.py",
    ],
    "plantuml_nav/18_documents_favorites_nav.puml": [
        "flutter_frontend/lib/screens/documents/document_list_screen.dart",
        "flutter_frontend/lib/providers/documents_provider.dart",
        "flutter_frontend/lib/models/document.dart",
        "api/serializers/documents.py",
    ],
    "plantuml_nav/19_documents_archived_nav.puml": [
        "flutter_frontend/lib/screens/documents/document_list_screen.dart",
        "flutter_frontend/lib/providers/documents_provider.dart",
        "flutter_frontend/lib/models/document.dart",
        "api/serializers/documents.py",
    ],
    "plantuml_nav/20_documents_admin_nav.puml": [
        "flutter_frontend/lib/screens/admin/admin_screen.dart",
        "flutter_frontend/lib/providers/documents_provider.dart",
        "flutter_frontend/lib/models/document.dart",
        "api/serializers/admin_s.py",
    ],
    "plantuml_nav/21_trash_nav.puml": [
        "flutter_frontend/lib/screens/system/trash_screen.dart",
        "flutter_frontend/lib/models/trash.dart",
        "api/trash_services.py",
        "templates/documents/archive_list.html",
    ],
    "plantuml_nav/22_profile_nav.puml": [
        "flutter_frontend/lib/screens/profile/profile_screen.dart",
        "flutter_frontend/lib/providers/auth_provider.dart",
        "flutter_frontend/lib/models/user.dart",
        "api/serializers/auth.py",
        "accounts/forms.py",
    ],
    "plantuml_nav/23_approval_requests_nav.puml": [
        "flutter_frontend/lib/screens/documents/pending_approvals_screen.dart",
        "flutter_frontend/lib/providers/pending_approvals_provider.dart",
        "api/serializers/documents.py",
        "templates/document_templates/pending_approvals.html",
    ],
    "plantuml_nav/24_ai_settings_nav.puml": [
        "flutter_frontend/lib/screens/admin/ai_config_screen.dart",
        "api/serializers/admin_s.py",
        "templates/admin_panel/ai_config.html",
        "prompts/models.py",
    ],
    "plantuml_nav/25_accounts_departments_nav.puml": [
        "flutter_frontend/lib/screens/admin/admin_screen.dart",
        "api/serializers/admin_s.py",
        "accounts/forms.py",
        "templates/admin_panel/users.html",
        "templates/admin_panel/departments.html",
        "templates/admin_panel/groups.html",
    ],
    "plantuml_nav/26_backups_nav.puml": [
        "flutter_frontend/lib/screens/admin/backup_screen.dart",
        "api/serializers/admin_s.py",
        "templates/admin_panel/backup.html",
        "my_tennis_club/management/commands/reset_db.py",
    ],
    "plantuml_nav/27_guest_generate_nav.puml": [
        "flutter_frontend/lib/screens/guest/guest_ai_screen.dart",
        "flutter_frontend/lib/screens/guest/guest_doc_screen.dart",
        "flutter_frontend/lib/models/document.dart",
        "api/serializers/documents.py",
        "flutter_frontend/web/voice_assistant_bridge.js",
    ],
    "plantuml_nav/28_guest_latest_document_nav.puml": [
        "flutter_frontend/lib/screens/guest/guest_document_detail_screen.dart",
        "flutter_frontend/lib/models/document.dart",
        "api/serializers/documents.py",
    ],
}

FEATURE_LABELS = {
    "plantuml_nav/01_dashboard_nav.puml": "Dashboard tổng quan",
    "plantuml_nav/02_generate_from_template_nav.puml": "Sinh văn bản từ mẫu",
    "plantuml_nav/03_document_qa_nav.puml": "Hỏi đáp tài liệu",
    "plantuml_nav/04_ai_assistant_nav.puml": "Trợ lý AI",
    "plantuml_nav/05_signing_requests_nav.puml": "Hộp thư yêu cầu ký số",
    "plantuml_nav/06_signed_pdfs_nav.puml": "Danh sách PDF đã ký",
    "plantuml_nav/07_mailbox_nav.puml": "Mailbox văn bản",
    "plantuml_nav/08_signing_delegation_nav.puml": "Ủy quyền ký số",
    "plantuml_nav/09_create_template_nav.puml": "Tạo mẫu văn bản",
    "plantuml_nav/10_templates_shared_nav.puml": "Kho mẫu dùng chung",
    "plantuml_nav/11_templates_my_department_nav.puml": "Mẫu theo phòng ban",
    "plantuml_nav/12_templates_my_private_nav.puml": "Mẫu riêng tư",
    "plantuml_nav/13_templates_favorites_nav.puml": "Mẫu yêu thích",
    "plantuml_nav/14_templates_admin_nav.puml": "Quản trị mẫu và tri thức",
    "plantuml_nav/15_documents_my_nav.puml": "Văn bản của tôi",
    "plantuml_nav/16_documents_group_nav.puml": "Văn bản nhóm",
    "plantuml_nav/17_documents_public_nav.puml": "Văn bản công khai",
    "plantuml_nav/18_documents_favorites_nav.puml": "Văn bản yêu thích",
    "plantuml_nav/19_documents_archived_nav.puml": "Kho lưu trữ văn bản",
    "plantuml_nav/20_documents_admin_nav.puml": "Quản trị văn bản",
    "plantuml_nav/21_trash_nav.puml": "Thùng rác",
    "plantuml_nav/22_profile_nav.puml": "Hồ sơ cá nhân",
    "plantuml_nav/23_approval_requests_nav.puml": "Danh sách chờ phê duyệt",
    "plantuml_nav/24_ai_settings_nav.puml": "Cấu hình AI",
    "plantuml_nav/25_accounts_departments_nav.puml": "Quản trị tài khoản, phòng ban và nhóm",
    "plantuml_nav/26_backups_nav.puml": "Sao lưu và khôi phục",
    "plantuml_nav/27_guest_generate_nav.puml": "Cổng khách tạo văn bản",
    "plantuml_nav/28_guest_latest_document_nav.puml": "Cổng khách xem văn bản mới nhất",
}

LEGACY_HEADER_PHRASES = [
    "Tệp này dùng để:",
    "Cách hoạt động:",
    "Vai trò trong hệ thống:",
    "Tác dụng khi hệ thống vận hành:",
]
LEGACY_SYMBOL_PHRASES = [
    "Mục đích:",
    "Cách hoạt động:",
    "Vai trò trong hệ thống:",
    "Tác dụng khi hệ thống vận hành:",
]
LEGACY_PY_INLINE_PHRASES = [
    "Đọc dữ liệu đầu vào từ request để chuẩn bị cho bước kiểm tra và xử lý tiếp theo.",
    "Lấy tệp người dùng gửi lên để gắn vào đúng luồng xử lý media hoặc tài liệu.",
    "Thực hiện truy vấn hoặc ghi dữ liệu ORM để đồng bộ trạng thái nghiệp vụ với cơ sở dữ liệu.",
    "Đóng gói kết quả nghiệp vụ thành phản hồi API chuẩn cho frontend hoặc client gọi vào.",
    "Trả về HTML hoặc điều hướng sang màn tiếp theo ở lớp giao diện Django.",
    "Ghi thay đổi hiện tại xuống tầng lưu trữ để trạng thái mới có hiệu lực trong runtime.",
    "Gọi sang lớp dịch vụ hoặc AI runtime để xử lý phần nghiệp vụ nặng của request hiện tại.",
    "Chặn lỗi ở biên xử lý để hệ thống còn cơ hội ghi log và trả phản hồi lỗi kiểm soát được.",
]
BACKEND_HEADER_PHRASES = [
    "Chức năng web liên quan:",
    "Vai trò backend trong luồng:",
    "Đầu vào/đầu ra chính:",
    "Người dùng sẽ thấy trên web:",
]
BACKEND_SYMBOL_PHRASES = [
    "Chức năng web liên quan:",
    "Vai trò backend:",
    "Cách xử lý chính:",
    "Kết quả trả về cho web:",
    "[Web]",
    "[UI]",
]
DART_KEY_TEXTS = [
    "Khởi tạo khung ứng dụng theo kiểu router để toàn bộ điều hướng dùng chung một điểm vào.",
    "Nhóm nhiều route dưới cùng một shell để chia sẻ layout và navigation chung.",
    "Định nghĩa một route cụ thể để router biết màn nào cần dựng khi URL khớp.",
    "Lắng nghe provider để widget tự động dựng lại khi dữ liệu hoặc trạng thái thay đổi.",
    "Đọc provider theo nhu cầu hành động mà không buộc widget đăng ký rebuild liên tục.",
    "Gọi API hoặc tác vụ bất đồng bộ rồi chờ kết quả trước khi cập nhật giao diện.",
    "Điều hướng người dùng sang màn phù hợp theo kết quả thao tác hiện tại.",
    "Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.",
    "Dựng khung màn hình chính để chứa app bar, body, action và các vùng giao diện khác.",
]
JS_KEY_TEXTS = [
    "Gắn sự kiện trình duyệt để giao diện phản ứng đúng với thao tác của người dùng.",
    "Quét DOM để lấy đúng nhóm phần tử cần áp dụng hành vi client-side.",
    "Hiển thị hộp thoại xác nhận nhằm chặn thao tác nhạy cảm trước khi gửi tiếp.",
    "Đưa dữ liệu vào clipboard để hỗ trợ thao tác nhanh ngay trên trình duyệt.",
]
HTML_KEY_TEXTS = [
    "Khối template này mở ra một vùng nội dung để view hoặc template con bơm dữ liệu vào đúng vị trí.",
    "Khối điều hướng này chứa các liên kết hoặc hành động chính mà người dùng có thể tương tác trên trang.",
    "Khối nội dung chính này giữ phần thông tin trung tâm mà trang đang phục vụ cho người dùng.",
    "Khối giao diện này nhóm một vùng nội dung cùng chủ đề để việc render và đọc mã dễ theo dõi hơn.",
    "Biểu mẫu này thu thập dữ liệu đầu vào từ người dùng trước khi gửi về backend hoặc xử lý ở client.",
    "Bảng này trình bày danh sách dữ liệu theo cột để người dùng theo dõi và thao tác thuận tiện.",
    "Khối script này nạp hoặc ghép hành vi client-side cần thiết cho trang hiện tại.",
]
PUML_COMMENT_LINES = [
    "' Khối này gom các thành phần cùng lớp kiến trúc hoặc cùng miền nghiệp vụ để sơ đồ dễ đọc và bám sát runtime.",
    "' Thành phần này biểu diễn một điểm xử lý, màn hình hoặc dịch vụ có vai trò cụ thể trong luồng hệ thống.",
    "' Thành phần dữ liệu này thể hiện nơi trạng thái nghiệp vụ được lưu bền vững hoặc truy vấn lại.",
    "' Thành phần lưu trữ này mô tả vùng chứa tệp hoặc artefact mà runtime đọc ghi trong quá trình vận hành.",
    "' Thành phần tích hợp ngoài này đại diện cho dịch vụ hoặc hệ thống không nằm hoàn toàn trong codebase nội bộ.",
    "' Actor này đại diện cho đối tượng bên ngoài tương tác với hệ thống thông qua giao diện hoặc API.",
    "' Legend này tóm tắt cách đọc sơ đồ và các ý nghĩa vận hành quan trọng của luồng.",
    "' Note này ghi chú thêm bối cảnh vận hành hoặc danh sách file liên quan để đối chiếu source.",
]


def rel_path(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def is_excluded(path: Path) -> bool:
    return any(part in EXCLUDED_PARTS for part in path.parts)


def resolve_cli_paths(raw_paths: list[str] | None) -> list[Path]:
    resolved: list[Path] = []
    for raw_path in raw_paths or []:
        candidate = Path(raw_path)
        if not candidate.is_absolute():
            candidate = ROOT / candidate
        resolved.append(candidate.resolve())
    return resolved


def path_matches_selection(path: Path, selected_paths: list[Path]) -> bool:
    if not selected_paths:
        return True
    resolved = path.resolve()
    return any(resolved == selected or selected in resolved.parents for selected in selected_paths)


def is_backend_python_file(path: Path) -> bool:
    if path.suffix != ".py":
        return False
    relative = rel_path(path)
    if relative == "manage.py":
        return True
    backend_roots = {
        "accounts",
        "admin_panel",
        "ai_engine",
        "api",
        "chatbot",
        "dashboard",
        "document_templates",
        "documents",
        "members",
        "my_tennis_club",
        "prompts",
        "signing",
    }
    first_part = Path(relative).parts[0] if Path(relative).parts else ""
    return first_part in backend_roots


def iter_source_files(selected_paths: list[Path] | None = None, *, backend_only: bool = False) -> list[Path]:
    files = []
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix not in SOURCE_SUFFIXES:
            continue
        if is_excluded(path):
            continue
        if selected_paths and not path_matches_selection(path, selected_paths):
            continue
        if backend_only and not is_backend_python_file(path):
            continue
        files.append(path)
    return sorted(files)


def iter_diagram_files(selected_paths: list[Path] | None = None) -> list[Path]:
    files = [ROOT / "SO_DO_KIEN_TRUC_TONG_THE_HE_THONG.puml"]
    files.extend(sorted((ROOT / "plantuml_nav").glob("*.puml")))
    return [path for path in files if path.exists() and path_matches_selection(path, selected_paths or [])]


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8").replace("\ufeff", "")


def write_text(path: Path, text: str) -> None:
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def split_snake(name: str) -> str:
    text = name.replace("_", " ").replace("-", " ")
    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


FEATURES_BY_BACKEND_FILE: dict[str, list[str]] = defaultdict(list)
for diagram_path, related_files in DIAGRAM_RELATED.items():
    feature_label = FEATURE_LABELS.get(diagram_path)
    if not feature_label:
        continue
    for related_file in related_files:
        if related_file.endswith(".py"):
            FEATURES_BY_BACKEND_FILE[related_file].append(feature_label)


def dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        cleaned = item.strip()
        if not cleaned or cleaned in seen:
            continue
        seen.add(cleaned)
        result.append(cleaned)
    return result


def join_labels(items: list[str]) -> str:
    unique_items = dedupe(items)
    if not unique_items:
        return ""
    if len(unique_items) == 1:
        return unique_items[0]
    if len(unique_items) == 2:
        return f"{unique_items[0]} và {unique_items[1]}"
    return f"{', '.join(unique_items[:-1])} và {unique_items[-1]}"


def backend_features_for_path(relative: str) -> list[str]:
    if "guest" in relative:
        return ["Cổng khách tạo văn bản", "Cổng khách xem văn bản mới nhất"]
    if "trash" in relative:
        return ["Thùng rác"]
    if "notifications" in relative:
        return ["Dashboard tổng quan", "thông báo trạng thái trên web"]
    if "backup" in relative or "reset_db" in relative or "purge_trash" in relative:
        return ["Sao lưu và khôi phục"]
    if "auth" in relative or relative.startswith("accounts/"):
        return ["Đăng nhập", "Đăng ký", "Hồ sơ cá nhân", "Quản trị tài khoản, phòng ban và nhóm"]
    if "prompt" in relative:
        return ["Cấu hình AI", "Quản trị prompt"]
    if "signing" in relative or "pki" in relative:
        return ["Hộp thư yêu cầu ký số", "Danh sách PDF đã ký", "Ủy quyền ký số"]
    if "template" in relative:
        return ["Tạo mẫu văn bản", "Kho mẫu dùng chung", "Mẫu theo phòng ban", "Mẫu riêng tư", "Mẫu yêu thích"]
    if "chat" in relative or "assistant" in relative or "rag" in relative or "ai_doc" in relative or relative.startswith("ai_engine/"):
        return ["Trợ lý AI", "Hỏi đáp tài liệu", "Sinh văn bản từ mẫu"]
    if "documents" in relative or "mailbox" in relative:
        return ["Văn bản của tôi", "Văn bản nhóm", "Văn bản công khai", "Văn bản yêu thích", "Kho lưu trữ văn bản", "Mailbox văn bản"]
    if "dashboard" in relative:
        return ["Dashboard tổng quan"]
    if relative.startswith("admin_panel/"):
        return ["Quản trị tài khoản, phòng ban và nhóm", "Cấu hình AI", "Sao lưu và khôi phục"]
    lookup_features = FEATURES_BY_BACKEND_FILE.get(relative, [])
    if lookup_features:
        return lookup_features
    return ["các màn quản trị và nghiệp vụ của hệ thống web"]


def ui_summary_for_path(relative: str) -> str:
    features = backend_features_for_path(relative)
    if features == ["các màn quản trị và nghiệp vụ của hệ thống web"]:
        return features[0]
    return f"các màn {join_labels(features)}"


def resource_label_for_path(relative: str) -> str:
    if "guest" in relative:
        return "cổng khách và luồng truy cập không đăng nhập"
    if "trash" in relative:
        return "thùng rác và khôi phục dữ liệu"
    if "notifications" in relative:
        return "thông báo hệ thống"
    if "backup" in relative or "reset_db" in relative or "purge_trash" in relative:
        return "sao lưu, dọn dữ liệu và vận hành hệ thống"
    if "auth" in relative or relative.startswith("accounts/"):
        return "tài khoản, hồ sơ và phân quyền"
    if "prompt" in relative:
        return "prompt và cấu hình AI"
    if "signing" in relative or "pki" in relative:
        return "ký số, PDF đã ký và kiểm chứng"
    if "template" in relative:
        return "mẫu văn bản"
    if "chat" in relative or "assistant" in relative or "rag" in relative or "ai_doc" in relative or relative.startswith("ai_engine/"):
        return "trợ lý AI, RAG và sinh văn bản"
    if "documents" in relative or "mailbox" in relative:
        return "văn bản và mailbox văn bản"
    if "dashboard" in relative:
        return "dashboard tổng quan"
    if relative.startswith("admin_panel/"):
        return "quản trị hệ thống"
    return "nghiệp vụ web của hệ thống"


def python_layer_for_path(relative: str) -> str:
    if relative == "manage.py" or "management/commands/" in relative:
        return "command"
    if relative.endswith("urls.py"):
        return "routing"
    if relative.endswith("apps.py") or relative.endswith("signals.py"):
        return "bootstrap"
    if relative.startswith("api/views/"):
        return "view"
    if relative.startswith("api/serializers/"):
        return "serializer"
    if "permissions.py" in relative:
        return "permission"
    if relative.endswith("models.py"):
        return "model"
    if relative.endswith("forms.py"):
        return "form"
    service_markers = ("services", "pdf_preview", "rag_", "assistant_engine", "doc_creator", "internal_pki", "pki", "runtime_")
    if any(marker in relative for marker in service_markers):
        return "service"
    return "module"


def backend_file_role_sentence(layer: str, resource_label: str) -> str:
    if layer == "view":
        return f"Tệp này chứa các API endpoint và helper backend cho {resource_label}."
    if layer == "serializer":
        return f"Tệp này định nghĩa contract dữ liệu mà web dùng để đọc hoặc gửi dữ liệu {resource_label}."
    if layer == "permission":
        return f"Tệp này chốt các rule phân quyền và điều kiện trạng thái cho {resource_label}."
    if layer == "model":
        return f"Tệp này mô tả cấu trúc lưu trữ và quan hệ dữ liệu của {resource_label}."
    if layer == "form":
        return f"Tệp này kiểm tra và chuẩn hóa dữ liệu nhập cho {resource_label}."
    if layer == "command":
        return f"Tệp này chạy tác vụ vận hành nền liên quan tới {resource_label}."
    if layer == "routing":
        return f"Tệp này ánh xạ route để request đi đúng luồng backend của {resource_label}."
    if layer == "bootstrap":
        return f"Tệp này gắn hook khởi tạo hoặc đồng bộ side effect cho {resource_label}."
    if layer == "service":
        return f"Tệp này đóng gói nghiệp vụ nhiều bước hoặc side effect khó của {resource_label}."
    return f"Tệp này giữ phần logic backend dùng chung cho {resource_label}."


def backend_file_io_sentence(layer: str) -> str:
    if layer == "view":
        return "Nhận request, query params hoặc body từ client rồi trả JSON/HTTP status để frontend dựng list, detail, form hoặc thông báo lỗi."
    if layer == "serializer":
        return "Nhận model hoặc payload trung gian, ánh xạ thành field mà web dùng cho bảng, form, chi tiết và trạng thái nút."
    if layer == "permission":
        return "Nhận user, object hoặc context hiện tại rồi trả cờ cho phép, queryset hoặc verdict để endpoint và serializer tiếp tục dùng."
    if layer == "model":
        return "Giữ các field, quan hệ và helper mà API, serializer và service đọc lại như nguồn sự thật của nghiệp vụ."
    if layer == "form":
        return "Nhận dữ liệu submit từ admin hoặc luồng legacy, validate và chuẩn hóa trước khi lưu."
    if layer == "command":
        return "Nhận tham số CLI, chạy job nền và cập nhật dữ liệu hoặc cấu hình mà web sẽ đọc lại sau đó."
    if layer == "routing":
        return "Nhận đường dẫn đầu vào và chuyển request sang đúng view, API hoặc app con."
    if layer == "bootstrap":
        return "Lắng nghe quá trình khởi động hoặc thay đổi model để gắn thêm logic đồng bộ nền."
    if layer == "service":
        return "Nhận dữ liệu đã qua bước kiểm tra, xử lý side effect hoặc transaction rồi trả kết quả trung gian cho endpoint."
    return "Giữ các helper và cấu hình backend dùng lại ở nhiều flow."


def backend_file_effect_sentence(layer: str, ui_summary: str) -> str:
    ui_scope = ui_summary[8:] if ui_summary.startswith("các màn ") else ui_summary
    if layer == "serializer":
        return f"Các màn trong {ui_scope} nhận đúng field, đúng nhãn trạng thái và đúng cờ thao tác để render nhất quán."
    if layer == "permission":
        return f"Nút bấm, hành động và phản hồi lỗi trên {ui_scope} bật hoặc khóa đúng người, đúng trạng thái."
    if layer == "model":
        return f"Dữ liệu mà người dùng nhìn trên {ui_scope} giữ được tính nhất quán sau mỗi thao tác."
    if layer == "service":
        return f"Các thao tác nhiều bước trên {ui_scope} hoàn tất nhất quán thay vì rải logic ở nhiều endpoint."
    if layer == "command":
        return f"Sau khi tác vụ chạy xong, dữ liệu nền mà {ui_scope} đang dùng sẽ được làm mới hoặc sửa về trạng thái đúng."
    return f"Người dùng thấy dữ liệu, trạng thái thao tác và thông báo trên {ui_summary} thay đổi đúng theo kết quả nghiệp vụ."


def generic_file_context(path: Path) -> dict[str, str]:
    relative = rel_path(path)
    parts = Path(relative).parts
    subsystem = parts[0] if parts else path.stem
    role = "một thành phần của hệ thống"
    purpose = f"duy trì logic trong tệp {relative}"
    operation = "được gọi từ lớp phía trên, xử lý dữ liệu theo vai trò hiện có và trả kết quả về cho luồng gọi."
    effect = f"giữ cho luồng nghiệp vụ thuộc `{subsystem}` chạy ổn định trong runtime."

    if relative.startswith("flutter_frontend/lib/core/"):
        role = "lớp lõi Flutter Web"
        purpose = f"định nghĩa hạ tầng client như router, API client, theme hoặc locale trong {relative}"
        operation = "được nạp sớm khi app Flutter khởi động để các màn và provider dùng chung cấu hình nền."
        effect = "quyết định cách frontend khởi chạy, điều hướng và gọi API."
    elif relative.startswith("flutter_frontend/lib/providers/"):
        role = "lớp state management của Flutter"
        purpose = f"điều phối state, gọi API và đồng bộ dữ liệu màn hình trong {relative}"
        operation = "theo dõi trạng thái, gọi backend khi cần và phát dữ liệu mới xuống widget tree."
        effect = "giữ giao diện và dữ liệu runtime đồng bộ theo từng phiên làm việc."
    elif relative.startswith("flutter_frontend/lib/models/"):
        role = "lớp model dữ liệu phía Flutter"
        purpose = f"mô tả cấu trúc dữ liệu client dùng để đọc và ghi API trong {relative}"
        effect = "giúp frontend ánh xạ dữ liệu server thành đối tượng rõ nghĩa để render và xử lý."
    elif relative.startswith("flutter_frontend/lib/screens/"):
        role = "màn hình Flutter mà người dùng tương tác trực tiếp"
        purpose = f"dựng giao diện và orchestration UI trong {relative}"
        operation = "nhận state từ provider, dựng widget, phản ứng sự kiện và gửi thao tác ngược về backend khi người dùng tương tác."
        effect = "biến nghiệp vụ backend thành trải nghiệm thao tác cụ thể trên web."
    elif relative.startswith("flutter_frontend/lib/widgets/"):
        role = "widget tái sử dụng của Flutter"
        purpose = f"đóng gói khối giao diện hoặc hành vi lặp lại trong {relative}"
        effect = "giúp các màn hình dùng lại cùng một cách hiển thị hoặc tương tác."
    elif relative.startswith("flutter_frontend/lib/l10n/"):
        role = "lớp ngôn ngữ hóa của Flutter"
        purpose = f"quản lý chuỗi đa ngôn ngữ trong {relative}"
        effect = "giúp app đổi ngôn ngữ mà vẫn giữ nội dung nhất quán trên toàn web."
    elif relative.startswith("flutter_frontend/web/"):
        role = "tài nguyên web đầu vào của Flutter"
        purpose = f"hỗ trợ bootstrap hoặc bridge web trong {relative}"
        effect = "giúp bản build web hoạt động đúng trong trình duyệt."
    elif relative.startswith("templates/"):
        role = "giao diện HTML Django"
        purpose = f"render trang hoặc partial ở {relative}"
        operation = "nhận context từ view, ghép layout và xuất HTML cho các màn legacy hoặc admin."
        effect = "giữ các flow HTML cũ vẫn hoạt động song song với Flutter web."
    elif relative.startswith("static/js/"):
        role = "logic tương tác phía trình duyệt cho giao diện Django"
        purpose = f"xử lý sự kiện DOM và hành vi client-side trong {relative}"
        effect = "bổ sung các tương tác nhanh mà không cần round-trip về server."
    elif relative.startswith("static/css/"):
        role = "lớp style tĩnh của giao diện Django"
        purpose = f"định nghĩa giao diện hiển thị trong {relative}"
        effect = "kiểm soát cách người dùng nhìn thấy các màn HTML legacy."

    return {
        "relative": relative,
        "role": role,
        "purpose": purpose,
        "operation": operation,
        "effect": effect,
        "subsystem": subsystem,
    }


def backend_features_for_path(relative: str) -> list[str]:
    if "guest" in relative:
        return ["Guest tạo văn bản", "Guest xem văn bản vừa tạo"]
    if "trash" in relative:
        return ["Thùng rác"]
    if "notifications" in relative or "dashboard" in relative:
        return ["Bảng điều khiển"]
    if "backup" in relative or "reset_db" in relative or "purge_trash" in relative:
        return ["Sao lưu dữ liệu"]
    if "auth" in relative or relative.startswith("accounts/"):
        return ["Hồ sơ cá nhân", "Tài khoản, phòng ban và nhóm"]
    if "prompt" in relative:
        return ["Cấu hình AI"]
    if "signing" in relative or "pki" in relative:
        return ["Yêu cầu ký", "PDF đã ký", "Hòm thư", "Ủy quyền ký số"]
    if "template" in relative:
        return ["Tạo mẫu văn bản", "Mẫu dùng chung", "Mẫu phòng ban của tôi", "Mẫu riêng của tôi", "Mẫu yêu thích", "Tất cả mẫu (Admin)"]
    if "chat" in relative or "assistant" in relative or "rag" in relative or "ai_doc" in relative or relative.startswith("ai_engine/"):
        return ["Trợ lý AI", "Hỏi đáp tài liệu", "Sinh văn bản từ mẫu"]
    if "documents" in relative or "mailbox" in relative:
        return ["Văn bản của tôi", "Văn bản chia sẻ trong nhóm", "Văn bản chia sẻ công khai", "Văn bản yêu thích", "Văn bản đã lưu trữ", "Tất cả văn bản (Admin)", "Hòm thư", "Yêu cầu phê duyệt"]
    if relative.startswith("admin_panel/"):
        return ["Tài khoản, phòng ban và nhóm", "Cấu hình AI", "Sao lưu dữ liệu"]
    lookup_features = FEATURES_BY_BACKEND_FILE.get(relative, [])
    if lookup_features:
        return lookup_features
    return ["các chức năng quản trị và nghiệp vụ đang hiển thị trên web"]


def ui_summary_for_path(relative: str) -> str:
    return join_labels(backend_features_for_path(relative))


def resource_label_for_path(relative: str) -> str:
    if "guest" in relative:
        return "cổng guest, phiên tạm và document tạo không cần đăng nhập"
    if "trash" in relative:
        return "thùng rác, khôi phục và xóa vĩnh viễn dữ liệu"
    if "notifications" in relative or "dashboard" in relative:
        return "thống kê, thông báo và số liệu tổng quan trên Bảng điều khiển"
    if "backup" in relative or "reset_db" in relative or "purge_trash" in relative:
        return "sao lưu dữ liệu, dọn dữ liệu và vận hành hệ thống"
    if "auth" in relative or relative.startswith("accounts/"):
        return "hồ sơ cá nhân, tài khoản, phòng ban, nhóm và phân quyền truy cập"
    if "prompt" in relative:
        return "cấu hình AI, prompt và ngữ cảnh dùng chung cho web"
    if "signing" in relative or "pki" in relative:
        return "đề xuất ký, nhiệm vụ ký, PDF đã ký, xác minh chữ ký và ủy quyền ký số"
    if "template" in relative:
        return "danh sách mẫu, chi tiết mẫu, form tạo mẫu, bulk upload và preview biến"
    if "chat" in relative or "assistant" in relative or "rag" in relative or "ai_doc" in relative or relative.startswith("ai_engine/"):
        return "trợ lý AI, RAG, OCR/prefill và sinh văn bản từ mẫu"
    if "documents" in relative or "mailbox" in relative:
        return "danh sách văn bản, chi tiết văn bản, version, preview, chia sẻ, ký số và hòm thư"
    if relative.startswith("admin_panel/"):
        return "các màn quản trị hệ thống"
    return "nghiệp vụ backend đang phục vụ các chức năng web hiện hành"


def backend_surface_for_path(relative: str) -> str:
    if "guest" in relative:
        return "màn Guest tạo văn bản, màn Guest xem văn bản vừa tạo và các bước lưu trạng thái guest theo cookie/session"
    if "trash" in relative:
        return "màn Thùng rác, danh sách bản ghi đã xóa và các nút khôi phục hoặc xóa vĩnh viễn"
    if "notifications" in relative or "dashboard" in relative:
        return "Bảng điều khiển, badge chờ xử lý và các card thống kê tổng quan"
    if "backup" in relative or "reset_db" in relative or "purge_trash" in relative:
        return "màn Sao lưu dữ liệu, danh sách file backup và các thao tác tạo, tải, xóa backup"
    if "auth" in relative or relative.startswith("accounts/"):
        return "màn Hồ sơ cá nhân, màn đăng nhập/đăng ký và các dialog quản trị tài khoản, phòng ban, nhóm"
    if "prompt" in relative:
        return "màn Cấu hình AI, các form chỉnh model/context và những luồng AI đọc cấu hình này"
    if "signing" in relative or "pki" in relative:
        return "màn Yêu cầu ký, chi tiết ký, PDF đã ký, dialog đề xuất ký, dialog chọn người ký và màn Ủy quyền ký số"
    if "template" in relative:
        return "các tab Mẫu dùng chung, Mẫu phòng ban, Mẫu riêng, Mẫu yêu thích, màn chi tiết mẫu, form tạo mẫu và bulk upload"
    if "chat" in relative or "assistant" in relative or "rag" in relative or "ai_doc" in relative or relative.startswith("ai_engine/"):
        return "màn Trợ lý AI, Hỏi đáp tài liệu, kết quả RAG và luồng Sinh văn bản từ mẫu"
    if "documents" in relative or "mailbox" in relative:
        return "các tab danh sách văn bản, màn chi tiết văn bản, preview hoặc tải file, lịch sử version, vùng khởi động ký số và màn Hòm thư"
    return "các màn web đang hiển thị chức năng nghiệp vụ hiện hành"


def backend_file_role_sentence(layer: str, resource_label: str, surface: str) -> str:
    if layer == "view":
        return f"Tệp này là lớp nhận request trực tiếp từ web cho {resource_label}; nó quyết định API nào cấp dữ liệu, nhận action và trả lỗi về cho {surface}."
    if layer == "serializer":
        return f"Tệp này chốt contract JSON cho {resource_label}; mọi bảng, card, badge, dialog và form ở {surface} đều đọc hoặc submit dữ liệu theo cấu trúc tại đây."
    if layer == "permission":
        return f"Tệp này giữ các rule phân quyền và rule trạng thái cho {resource_label}; nó quyết định record nào được nhìn thấy và nút nào được bật ở {surface}."
    if layer == "model":
        return f"Tệp này là nguồn sự thật dữ liệu của {resource_label}; trạng thái hiển thị ở {surface} cuối cùng đều được suy ra từ model và quan hệ định nghĩa tại đây."
    if layer == "form":
        return f"Tệp này kiểm tra dữ liệu nhập từ các flow admin hoặc legacy liên quan tới {resource_label}, trước khi dữ liệu đó quay lại tác động lên {surface}."
    if layer == "command":
        return f"Tệp này chạy tác vụ nền hoặc lệnh vận hành cho {resource_label}; kết quả của nó thường làm mới hoặc sửa dữ liệu mà {surface} đang đọc."
    if layer == "routing":
        return f"Tệp này ánh xạ route backend cho {resource_label}; nếu route ở đây sai thì {surface} sẽ gọi nhầm endpoint hoặc không nhận được dữ liệu đúng."
    if layer == "bootstrap":
        return f"Tệp này gắn hook khởi tạo hoặc side effect nền cho {resource_label}, bảo đảm {surface} nhìn thấy trạng thái nhất quán mà không cần endpoint nào xử lý bù."
    if layer == "service":
        return f"Tệp này gom nghiệp vụ nhiều bước, transaction và side effect khó của {resource_label}; nó đứng sau các nút thao tác quan trọng xuất hiện ở {surface}."
    return f"Tệp này giữ phần logic backend dùng chung cho {resource_label}, để các flow ở {surface} không phải lặp lại cùng một rule ở nhiều nơi."


def backend_file_io_sentence(layer: str) -> str:
    if layer == "view":
        return "Nhận request, query params hoặc body từ client, áp quyền, lọc dữ liệu theo đúng ngữ cảnh người dùng rồi trả JSON hoặc HTTP status để web dựng list, detail, form, preview hoặc thông báo lỗi."
    if layer == "serializer":
        return "Nhận model hoặc payload trung gian, ánh xạ thành field mà web dùng cho bảng, card, detail, quyền nút, timeline, badge trạng thái và dữ liệu submit ngược về backend."
    if layer == "permission":
        return "Nhận user, object hoặc context hiện tại rồi trả verdict, queryset hoặc cờ cho phép để view và serializer biết nên cho thấy record nào và chặn action nào."
    if layer == "model":
        return "Giữ field, quan hệ, trạng thái và helper mà API, serializer, service và các job nền đọc lại như nguồn dữ liệu chuẩn của nghiệp vụ."
    if layer == "form":
        return "Nhận dữ liệu submit từ admin hoặc luồng legacy, validate và chuẩn hóa trước khi lưu để dữ liệu quay lại web không bị sai cấu trúc."
    if layer == "command":
        return "Nhận tham số CLI, chạy job nền và cập nhật dữ liệu hoặc cấu hình mà các màn web sẽ đọc lại sau đó."
    if layer == "routing":
        return "Nhận đường dẫn đầu vào và chuyển request sang đúng view, API hoặc app con để luồng web không bị đứt quãng."
    if layer == "bootstrap":
        return "Lắng nghe quá trình khởi động hoặc thay đổi model để gắn thêm bước đồng bộ nền mà endpoint không trực tiếp xử lý."
    if layer == "service":
        return "Nhận dữ liệu đã qua bước kiểm tra, thực hiện transaction, cập nhật nhiều bản ghi, đụng tới file, storage, integrity hoặc gọi engine ngoài rồi trả kết quả trung gian cho endpoint."
    return "Giữ các helper, cấu hình và rule backend dùng lại ở nhiều flow khác nhau."


def backend_file_effect_sentence(layer: str, ui_summary: str) -> str:
    if layer == "serializer":
        return f"Web ở các chức năng {ui_summary} nhận đúng field, đúng nhãn trạng thái, đúng cờ quyền và đúng dữ liệu submit để render nhất quán."
    if layer == "permission":
        return f"Nút bấm, action menu, dữ liệu danh sách và phản hồi lỗi ở các chức năng {ui_summary} được bật hoặc khóa đúng người, đúng thời điểm."
    if layer == "model":
        return f"Dữ liệu mà người dùng đang nhìn ở các chức năng {ui_summary} giữ được tính nhất quán sau mỗi thao tác tạo, sửa, chia sẻ, ký hoặc xóa."
    if layer == "service":
        return f"Các thao tác nhiều bước ở các chức năng {ui_summary} hoàn tất nhất quán; web không rơi vào trạng thái nửa chừng giữa DB, file, badge và timeline."
    if layer == "command":
        return f"Sau khi tác vụ chạy xong, dữ liệu nền mà các chức năng {ui_summary} đang dùng sẽ được làm mới hoặc sửa về trạng thái đúng."
    return f"Người dùng sẽ thấy dữ liệu, badge trạng thái, quyền nút và thông báo trên các chức năng {ui_summary} thay đổi đúng theo kết quả nghiệp vụ."


def file_context(path: Path) -> dict[str, str]:
    if path.suffix != ".py" or not is_backend_python_file(path):
        return generic_file_context(path)

    relative = rel_path(path)
    parts = Path(relative).parts
    subsystem = parts[0] if parts else path.stem
    layer = python_layer_for_path(relative)
    resource_label = resource_label_for_path(relative)
    ui_summary = ui_summary_for_path(relative)
    surface = backend_surface_for_path(relative)

    return {
        "relative": relative,
        "role": backend_file_role_sentence(layer, resource_label, surface).rstrip("."),
        "purpose": ui_summary,
        "operation": backend_file_io_sentence(layer),
        "effect": backend_file_effect_sentence(layer, ui_summary),
        "subsystem": subsystem,
        "layer": layer,
        "resource_label": resource_label,
        "ui_summary": ui_summary,
        "surface": surface,
    }


def comment_block(ext: str, lines: list[str], indent: str = "") -> list[str]:
    if ext == ".py":
        return [f"{indent}# {line}" for line in lines]
    if ext in {".dart", ".js"}:
        return [f"{indent}// {line}" for line in lines]
    if ext == ".css":
        return [f"{indent}/* {line} */" for line in lines]
    if ext == ".html":
        return [f"{indent}<!-- {line} -->" for line in lines]
    return lines


def header_lines(path: Path) -> list[str]:
    info = file_context(path)
    if path.suffix == ".py" and is_backend_python_file(path):
        return comment_block(
            path.suffix,
            [
                f"Chức năng web liên quan: {info['purpose']}.",
                f"Vai trò backend trong luồng: {info['role']}.",
                f"Đầu vào/đầu ra chính: {info['operation']}",
                f"Người dùng sẽ thấy trên web: {info['effect']}",
            ],
        )
    return comment_block(
        path.suffix,
        [
            f"Tệp này dùng để: {info['purpose']}.",
            f"Cách hoạt động: {info['operation']}",
            f"Vai trò trong hệ thống: Đây là {info['role']}.",
            f"Tác dụng khi hệ thống vận hành: {info['effect']}",
        ],
    )


def has_header(lines: list[str]) -> bool:
    header_window = "\n".join(lines[:12])
    return "Tệp này dùng để:" in header_window or "Chức năng web liên quan:" in header_window


def find_header_insertion_index(path: Path, lines: list[str]) -> int:
    if path.suffix == ".py":
        index = 0
        while index < len(lines) and (
            lines[index].startswith("#!")
            or re.match(r"#\s*-\*-\s*coding:", lines[index])
            or re.match(r"from __future__ import ", lines[index])
            or not lines[index].strip()
        ):
            index += 1
        return index
    if path.suffix == ".html":
        index = 0
        while index < len(lines) and lines[index].strip().startswith("{%") and (
            "extends" in lines[index] or "load" in lines[index]
        ):
            index += 1
        if index < len(lines) and lines[index].strip().lower().startswith("<!doctype"):
            index += 1
        return index
    return 0


def extract_comment_content(path: Path, line: str) -> str:
    stripped = line.strip()
    if path.suffix == ".py" and stripped.startswith("#"):
        return stripped.lstrip("#").strip()
    if path.suffix in {".dart", ".js"} and stripped.startswith("//"):
        return stripped.lstrip("/").strip()
    if path.suffix == ".html" and stripped.startswith("<!--"):
        return stripped.replace("<!--", "").replace("-->", "").strip()
    if path.suffix == ".css" and stripped.startswith("/*"):
        return stripped.replace("/*", "").replace("*/", "").strip()
    return ""


def generated_phrases_for(path: Path) -> list[str]:
    if path.suffix == ".py":
        return LEGACY_HEADER_PHRASES + LEGACY_SYMBOL_PHRASES + LEGACY_PY_INLINE_PHRASES + BACKEND_HEADER_PHRASES + BACKEND_SYMBOL_PHRASES
    if path.suffix == ".dart":
        return LEGACY_HEADER_PHRASES + LEGACY_SYMBOL_PHRASES + DART_KEY_TEXTS
    if path.suffix == ".js":
        return LEGACY_HEADER_PHRASES + LEGACY_SYMBOL_PHRASES + JS_KEY_TEXTS
    if path.suffix == ".html":
        return LEGACY_HEADER_PHRASES + HTML_KEY_TEXTS
    if path.suffix == ".css":
        return LEGACY_HEADER_PHRASES + ["Khối style `"]
    return []


def collapse_blank_lines(lines: list[str]) -> list[str]:
    collapsed: list[str] = []
    blank_run = 0
    for line in lines:
        if line.strip():
            blank_run = 0
            collapsed.append(line)
            continue
        blank_run += 1
        if blank_run <= 1:
            collapsed.append(line)
    return collapsed


def strip_generated_comments(path: Path, lines: list[str]) -> list[str]:
    phrases = generated_phrases_for(path)
    cleaned: list[str] = []
    last_removed = False
    for line in lines:
        content = extract_comment_content(path, line)
        if content and any(phrase in content for phrase in phrases):
            last_removed = True
            continue
        if last_removed and not line.strip():
            last_removed = False
            continue
        cleaned.append(line)
        last_removed = False
    return collapse_blank_lines(cleaned)


def insert_header(path: Path, lines: list[str]) -> list[str]:
    if has_header(lines):
        return lines
    index = find_header_insertion_index(path, lines)
    return lines[:index] + header_lines(path) + [""] + lines[index:]


def previous_non_empty(lines: list[str], index: int) -> str:
    cursor = index - 1
    while cursor >= 0:
        if lines[cursor].strip():
            return lines[cursor]
        cursor -= 1
    return ""


def has_recent_annotation(lines: list[str], index: int, phrase: str, lookback: int = 5) -> bool:
    start = max(0, index - lookback)
    return any(phrase in line for line in lines[start:index])


ACTION_MAP = [
    ("list", "tải danh sách"),
    ("create", "tạo mới"),
    ("detail", "lấy chi tiết"),
    ("update", "cập nhật"),
    ("delete", "xóa"),
    ("archive", "lưu trữ"),
    ("restore", "khôi phục"),
    ("trash", "đưa vào thùng rác"),
    ("favorite", "đánh dấu yêu thích"),
    ("share", "chia sẻ"),
    ("approve", "phê duyệt"),
    ("reject", "từ chối"),
    ("sign", "ký số"),
    ("verify", "xác minh chữ ký"),
    ("parse", "phân tích đầu vào"),
    ("extract", "trích xuất dữ liệu"),
    ("preview", "xem trước"),
    ("content", "lấy nội dung HTML"),
    ("html", "lấy nội dung HTML"),
    ("download", "tải xuống"),
    ("upload", "tải lên"),
    ("search", "tìm kiếm"),
    ("query", "tra cứu"),
    ("chat", "hỏi đáp"),
    ("assistant", "điều phối trợ lý AI"),
    ("rag", "truy xuất tri thức"),
    ("generate", "sinh dữ liệu"),
    ("fill", "điền dữ liệu"),
    ("prefill", "điền sẵn dữ liệu"),
    ("backup", "sao lưu"),
    ("reset", "đặt lại dữ liệu"),
    ("import", "nhập dữ liệu"),
    ("export", "xuất dữ liệu"),
    ("notify", "xử lý thông báo"),
    ("mailbox", "xử lý luồng mailbox"),
    ("forward", "chuyển tiếp"),
    ("pending", "xử lý hàng chờ"),
    ("history", "đọc lịch sử"),
    ("session", "đọc trạng thái phiên"),
    ("cleanup", "dọn phiên tạm"),
    ("stats", "lấy thống kê"),
    ("check", "kiểm tra dữ liệu"),
    ("org", "đọc cây tổ chức"),
    ("config", "cấu hình"),
    ("login", "đăng nhập"),
    ("register", "đăng ký"),
    ("profile", "cập nhật hồ sơ"),
    ("finalize", "chốt bản cuối"),
    ("unarchive", "bỏ lưu trữ"),
    ("version", "khôi phục phiên bản"),
]


def extract_actions(name: str) -> list[str]:
    lowered = split_snake(name).lower().split()
    actions = [label for token, label in ACTION_MAP if token in lowered or token in name.lower()]
    return dedupe(actions)


def python_base_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    if isinstance(node, ast.Subscript):
        return python_base_name(node.value)
    return ""


def classify_python_symbol(relative: str, node: ast.AST, parent: ast.AST | None) -> str:
    name = getattr(node, "name", "")
    if isinstance(node, ast.ClassDef):
        if name == "Meta":
            return "serializer_meta"
        if relative.startswith("api/serializers/") and name.endswith("Serializer"):
            return "serializer"
        if "permissions.py" in relative or name.endswith("Permission"):
            return "permission_class"
        if relative.endswith("models.py"):
            return "model"
        if relative.endswith("forms.py"):
            return "form"
        if "management/commands/" in relative and name == "Command":
            return "command_class"
        return "class"

    if isinstance(parent, ast.ClassDef):
        if parent.name.endswith("Serializer"):
            if name.startswith("get_"):
                return "serializer_field_method"
            return "serializer_method"
        if parent.name == "Command" and name == "handle":
            return "command_handler"
        if "permissions.py" in relative or parent.name.endswith("Permission"):
            return "permission_method"
        if relative.endswith("forms.py"):
            return "form_method"
        if relative.endswith("models.py"):
            return "model_method"
        return "method"

    if isinstance(parent, (ast.FunctionDef, ast.AsyncFunctionDef)):
        return "nested_function"

    if relative.startswith("api/views/") and not name.startswith("_"):
        return "endpoint"
    if relative.startswith("api/views/") and name.startswith("_"):
        return "helper_function"
    if relative.startswith("api/serializers/"):
        return "serializer_helper"
    if "permissions.py" in relative or name.startswith(("can_", "is_", "has_", "get_accessible_")):
        return "permission_rule"
    if relative.endswith("signals.py"):
        return "signal_handler"
    if relative.endswith("urls.py"):
        return "route_helper"
    if python_layer_for_path(relative) == "service":
        return "service_function"
    if python_layer_for_path(relative) == "command":
        return "command_function"
    return "function"


class PythonSymbolCollector(ast.NodeVisitor):
    def __init__(self, path: Path, source_lines: list[str]) -> None:
        self.path = path
        self.relative = rel_path(path)
        self.source_lines = source_lines
        self.parents: list[ast.AST] = []
        self.symbols: list[dict[str, str | int]] = []

    def _register(self, node: ast.AST) -> None:
        parent = self.parents[-1] if self.parents else None
        start_line = getattr(node, "lineno", 1)
        decorators = getattr(node, "decorator_list", [])
        if decorators:
            start_line = min(item.lineno for item in decorators)
        start_index = max(0, start_line - 1)
        indent = re.match(r"^\s*", self.source_lines[start_index]).group(0)
        self.symbols.append(
            {
                "name": getattr(node, "name", ""),
                "category": classify_python_symbol(self.relative, node, parent),
                "parent_name": getattr(parent, "name", "") if parent else "",
                "start_index": start_index,
                "indent": indent,
            }
        )

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self._register(node)
        self.parents.append(node)
        self.generic_visit(node)
        self.parents.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._register(node)
        self.parents.append(node)
        self.generic_visit(node)
        self.parents.pop()

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._register(node)
        self.parents.append(node)
        self.generic_visit(node)
        self.parents.pop()


def symbol_action_text(name: str, resource_label: str, fallback: str) -> str:
    actions = extract_actions(name)
    return join_labels(actions) if actions else fallback.format(resource_label=resource_label)


def ui_scope_text(ui_summary: str) -> str:
    return ui_summary[8:] if ui_summary.startswith("các màn ") else ui_summary


def symbol_role_sentence(info: dict[str, str], category: str, name: str, parent_name: str) -> str:
    resource_label = info["resource_label"]
    if category == "endpoint":
        actions = extract_actions(name)
        if actions:
            return f"Endpoint `{name}` là điểm vào backend cho thao tác {join_labels(actions)} của {resource_label}."
        return f"Endpoint `{name}` là điểm vào backend cho một thao tác chính của {resource_label}."
    if category == "helper_function":
        actions = extract_actions(name)
        if actions:
            return f"Hàm `{name}` tách riêng bước phụ trợ cho thao tác {join_labels(actions)} để các endpoint cùng dùng chung một rule."
        return f"Hàm `{name}` tách riêng một bước phụ trợ của {resource_label} để các endpoint cùng dùng chung một rule."
    if category == "nested_function":
        return f"Hàm lồng `{name}` cô lập một bước tính toán nhỏ bên trong flow của {resource_label} để khối logic chính dễ đọc hơn."
    if category == "serializer":
        return f"Lớp `{name}` định nghĩa payload JSON mà web dùng để hiển thị và gửi dữ liệu {resource_label}."
    if category == "serializer_meta":
        return f"Lớp `Meta` chốt model và bộ field cho payload mà `{parent_name}` sẽ trả về hoặc nhận vào."
    if category == "serializer_field_method":
        field_name = name[4:] if name.startswith("get_") else name
        if field_name.startswith("can_"):
            action_name = field_name[4:].replace("_", " ")
            return f"Phương thức `{name}` tính cờ quyền `{field_name}` để web biết có nên bật thao tác {action_name} hay không."
        if "status_display" in field_name or field_name.endswith("_display"):
            return f"Phương thức `{name}` đổi mã trạng thái nội bộ thành nhãn dễ đọc cho payload của web."
        if field_name == "is_favorite":
            return f"Phương thức `{name}` tính trạng thái yêu thích để danh sách và chi tiết hiển thị bookmark đúng người dùng."
        return f"Phương thức `{name}` tính field dẫn xuất `{field_name}` mà frontend cần thêm ngoài dữ liệu raw."
    if category == "serializer_method":
        return f"Phương thức `{name}` áp quy tắc serialize hoặc validate cho payload mà web dùng trong flow {resource_label}."
    if category == "serializer_helper":
        return f"Hàm `{name}` hỗ trợ chuẩn hóa dữ liệu cho serializer và giữ contract API của {resource_label} ổn định."
    if category == "permission_rule":
        actions = extract_actions(name)
        if actions:
            return f"Hàm `{name}` quyết định người dùng có được thực hiện thao tác {join_labels(actions)} hay không."
        return f"Hàm `{name}` quyết định người dùng có được thực hiện thao tác trên {resource_label} hay không."
    if category == "permission_class":
        return f"Lớp `{name}` gom các rule phân quyền backend cho {resource_label}."
    if category == "permission_method":
        return f"Phương thức `{name}` kiểm tra quyền hoặc điều kiện trạng thái trước khi backend cho phép tiếp tục flow."
    if category == "service_function":
        actions = extract_actions(name)
        if actions:
            return f"Hàm `{name}` đóng gói nghiệp vụ nhiều bước cho thao tác {join_labels(actions)} để endpoint không phải lặp logic."
        return f"Hàm `{name}` đóng gói một phần nghiệp vụ lõi của {resource_label} để endpoint không phải lặp logic."
    if category == "model":
        return f"Model `{name}` lưu trạng thái nghiệp vụ mà các màn web đang đọc và cập nhật."
    if category == "model_method":
        return f"Phương thức `{name}` tính hoặc thay đổi trạng thái của model theo quy tắc nghiệp vụ."
    if category == "form":
        return f"Lớp `{name}` kiểm tra dữ liệu nhập từ admin hoặc flow legacy liên quan tới {resource_label}."
    if category == "form_method":
        return f"Phương thức `{name}` áp luật validate hoặc biến đổi dữ liệu cho form backend."
    if category == "command_class":
        return "Lớp `Command` gom tác vụ vận hành nền phục vụ dữ liệu hoặc cấu hình mà web đang dựa vào."
    if category == "command_handler":
        return "Phương thức `handle` là điểm chạy chính của tác vụ vận hành này."
    if category == "command_function":
        return f"Hàm `{name}` hỗ trợ tác vụ vận hành hoặc xử lý dữ liệu nền liên quan tới {resource_label}."
    if category == "signal_handler":
        return f"Hàm `{name}` đồng bộ side effect sau khi model thay đổi để các màn {info['ui_summary']} không bị lệch trạng thái."
    if category == "route_helper":
        return f"Hàm `{name}` hỗ trợ map route hoặc redirect cho luồng {resource_label}."
    if category == "class":
        return f"Lớp `{name}` giữ một phần logic backend dùng chung cho {resource_label}."
    if category == "method":
        return f"Phương thức `{name}` thực thi một bước xử lý nội bộ trong class phục vụ {resource_label}."
    return f"Hàm `{name}` xử lý một phần logic backend của {resource_label}."


def symbol_process_sentence(info: dict[str, str], category: str, name: str) -> str:
    if category == "endpoint":
        return "Hàm đọc tham số từ request, áp quyền và trạng thái nghiệp vụ, gọi query hoặc service cần thiết rồi serialize response về cho client."
    if category in {"helper_function", "nested_function", "function", "method"}:
        return "Khối này chuẩn hóa dữ liệu trung gian, tách một bước xử lý phụ hoặc gom logic lặp lại để flow chính ngắn và dễ kiểm soát hơn."
    if category == "serializer":
        return "Serializer ánh xạ field, validate dữ liệu và bổ sung các field tính toán mà UI cần trước khi render."
    if category == "serializer_meta":
        return "Khối này chốt model nguồn, danh sách field và chính sách read/write để contract giữa backend với frontend không bị lệch."
    if category == "serializer_field_method":
        field_name = name[4:] if name.startswith("get_") else name
        if field_name.startswith("can_"):
            return f"Khối này đọc request, user và object hiện tại rồi áp rule quyền để trả cờ `{field_name}`."
        if "status_display" in field_name or field_name.endswith("_display"):
            return "Khối này đổi mã trạng thái nội bộ thành text dễ đọc trước khi serialize ra API."
        return f"Khối này suy ra field `{field_name}` từ model, context hoặc request hiện tại rồi chèn vào payload."
    if category == "serializer_method":
        return "Khối này can thiệp vào bước validate hoặc serialize để payload phản ánh đúng rule nghiệp vụ."
    if category in {"permission_rule", "permission_class", "permission_method"}:
        return "Khối này đọc user, object và bối cảnh hiện tại rồi trả verdict hoặc rule mà endpoint và serializer tiếp tục dùng."
    if category == "service_function":
        return "Khối này gom transaction, side effect, gọi engine ngoài hoặc cập nhật nhiều bản ghi thành một điểm dùng lại."
    if category == "model":
        return "Khối này định nghĩa field, quan hệ và helper mà serializer, view và service dựa vào như nguồn dữ liệu chuẩn."
    if category == "model_method":
        return "Khối này cập nhật hoặc suy ra trạng thái model để các luồng nghiệp vụ dùng chung cùng một quy tắc."
    if category in {"form", "form_method"}:
        return "Khối này validate, làm sạch hoặc ánh xạ dữ liệu submit trước khi backend chấp nhận lưu."
    if category in {"command_class", "command_handler", "command_function"}:
        return "Khối này đọc tham số CLI, chạy job nền rồi cập nhật dữ liệu hoặc cấu hình để hệ thống dùng lại."
    if category == "signal_handler":
        return "Khối này lắng nghe thay đổi model và tự động kích hoạt bước đồng bộ nền đi kèm."
    if category == "route_helper":
        return "Khối này giúp route hoặc redirect đi đúng hướng mà không lặp lại cấu hình ở nhiều nơi."
    return "Khối này giữ phần xử lý dùng chung cho backend."


def symbol_effect_sentence(info: dict[str, str], category: str, name: str) -> str:
    ui_summary = info["ui_summary"]
    ui_scope = ui_scope_text(ui_summary)
    if category == "endpoint":
        return f"Frontend dùng response của hàm này để làm mới dữ liệu, mở chi tiết, đổi trạng thái nút hoặc hiển thị lỗi nghiệp vụ trên {ui_summary}."
    if category in {"helper_function", "nested_function", "function", "method"}:
        return f"Cùng một rule xử lý được áp nhất quán trên {ui_scope}, giảm lệch hành vi giữa các API."
    if category == "serializer":
        return f"List, form và màn chi tiết trong {ui_summary} nhận đúng cấu trúc JSON mà không phải suy luận thêm."
    if category == "serializer_meta":
        return f"Frontend chỉ nhìn thấy các field đã được chốt ở đây nên contract hiển thị và submit trên {ui_scope} giữ ổn định."
    if category == "serializer_field_method":
        field_name = name[4:] if name.startswith("get_") else name
        if field_name.startswith("can_"):
            return f"Nút hoặc action tương ứng trên {ui_summary} được bật, ẩn hoặc khóa đúng người và đúng trạng thái."
        if "status_display" in field_name or field_name.endswith("_display"):
            return f"Bảng và màn chi tiết trong {ui_summary} hiển thị nhãn trạng thái dễ đọc thay vì mã kỹ thuật."
        if field_name == "is_favorite":
            return f"Icon yêu thích và các bộ lọc liên quan trên {ui_summary} hiển thị đúng trạng thái người dùng."
        return f"Frontend nhận thêm field `{field_name}` để render đúng trên {ui_summary} mà không cần gọi API phụ."
    if category in {"permission_rule", "permission_class", "permission_method"}:
        return f"Backend chặn đúng thao tác không hợp lệ và giúp UI trên {ui_scope} bật hoặc tắt quyền chính xác."
    if category == "service_function":
        return f"Các thao tác nhiều bước như mailbox, ký số, preview, AI hoặc đồng bộ dữ liệu trong {ui_summary} hoàn tất nhất quán trước khi UI cập nhật."
    if category in {"model", "model_method"}:
        return f"Dữ liệu lưu dưới khối này là nguồn sự thật để {ui_summary} hiển thị trạng thái mới nhất."
    if category in {"form", "form_method"}:
        return f"Người dùng ở các màn nhập liệu thuộc {ui_summary} nhận lỗi validate đúng chỗ và đúng rule."
    if category in {"command_class", "command_handler", "command_function"}:
        return f"Sau khi tác vụ chạy xong, dữ liệu hoặc cấu hình nền mà {ui_summary} đang dựa vào sẽ được làm mới."
    if category == "signal_handler":
        return f"Những thay đổi phát sinh từ {ui_summary} vẫn kéo theo các đồng bộ nền cần thiết mà không phải làm tay ở từng endpoint."
    if category == "route_helper":
        return f"Request hoặc redirect đi đúng luồng nên người dùng không bị văng sai màn trong {ui_summary}."
    return f"Khối này góp phần giữ cho {ui_summary} hiển thị đúng dữ liệu và đúng hành vi."


def ui_scope_text(ui_summary: str) -> str:
    return ui_summary


def endpoint_ui_trigger(name: str) -> str:
    lowered = name.lower()
    if "summary" in lowered or "stats" in lowered or "pending" in lowered:
        return "mở header, badge hoặc vùng tóm tắt cần số liệu tổng hợp"
    if "candidate" in lowered:
        return "mở dialog chọn người ký hoặc chọn người được ủy quyền"
    if "list" in lowered or "history" in lowered or "search" in lowered or "query" in lowered:
        return "mở danh sách, đổi tab, gõ tìm kiếm hoặc làm mới dữ liệu"
    if "detail" in lowered or "context" in lowered or "profile" in lowered:
        return "mở màn chi tiết, vùng thông tin phụ hoặc sidebar nghiệp vụ"
    if "preview" in lowered or "content_html" in lowered or "download" in lowered or "export" in lowered:
        return "bấm xem trước, mở HTML render hoặc tải file"
    if any(token in lowered for token in ("create", "write", "upload", "import", "generate", "fill", "prefill", "parse", "start", "proposal")):
        return "gửi form, upload tệp hoặc bấm nút tạo hay khởi chạy một flow mới"
    if any(token in lowered for token in ("approve", "reject", "sign", "forward", "complete", "favorite", "archive", "restore", "delete", "share", "finalize")):
        return "bấm một nút hành động nghiệp vụ trên giao diện"
    return "đi vào đúng chức năng tương ứng trên web"


def helper_focus(name: str, resource_label: str) -> str:
    lowered = name.lower()
    if "error" in lowered or "response" in lowered:
        return "quy đổi lỗi nội bộ thành mã trạng thái và thông điệp mà web có thể hiện thẳng lên toast hoặc dialog"
    if "build" in lowered and "search" in lowered:
        return "ghép điều kiện tìm kiếm nhiều trường cho ô tra cứu của danh sách"
    if "multi_value_query_param" in lowered:
        return "gom nhiều query param lặp lại thành một danh sách sạch để bộ lọc trên web dùng tiếp"
    if "sha256" in lowered or "hash" in lowered:
        if "docx" in lowered:
            return "khóa dấu vân tay của file DOCX đang gắn với văn bản để các flow ký số, Hòm thư hoặc kiểm tra toàn vẹn biết người dùng còn đang thao tác trên đúng phiên bản"
        return "tạo dấu vân tay cho file nguồn hoặc PDF đã ký để backend còn đối chiếu toàn vẹn ở các bước sau"
    if "filename" in lowered:
        return "chuẩn hóa tên file trước khi ghi storage hoặc trả về cho nút tải xuống, tránh lỗi ký tự ở file sinh ra"
    if "source_version" in lowered or "current_version" in lowered:
        return "chốt đúng phiên bản văn bản mà người dùng vừa thao tác để proposal, PDF đã ký hoặc luồng Hòm thư không bám nhầm sang bản cũ"
    if "display_name" in lowered:
        return "chuẩn hóa tên hiển thị của người thao tác để timeline, lịch sử ký và thông báo trên web đọc dễ hơn"
    if "thread_status" in lowered:
        return "cập nhật trạng thái tổng của thread Hòm thư để danh sách và màn chi tiết cùng phản ánh một kết quả"
    if "search" in lowered or "query" in lowered or "multi_value" in lowered or "normalize" in lowered:
        return "chuẩn hóa dữ liệu bộ lọc hoặc ô tìm kiếm trước khi danh sách và bộ lọc trên web dùng tiếp"
    if "resolve" in lowered and "signer" in lowered:
        return "chuẩn hóa danh sách người ký mà dialog chọn người trên web vừa gửi lên"
    if "extract" in lowered or "parse" in lowered or "html" in lowered or "docx" in lowered:
        return "bóc tách nội dung file hoặc text trung gian để preview, OCR hoặc detect biến hiển thị đúng trên web"
    if "validate" in lowered or "ensure" in lowered or "check" in lowered:
        return "chặn sớm các trạng thái không hợp lệ trước khi web đi tiếp sang bước thay đổi dữ liệu"
    if "preview" in lowered or "context" in lowered:
        return "chuẩn bị dữ liệu preview hoặc context mà màn hình chi tiết cần trước khi render"
    return f"tách một bước xử lý phụ của {resource_label} ra khỏi endpoint chính để nhiều flow dùng chung cùng một rule"


def service_internal_focus(name: str, relative: str) -> str:
    lowered = name.lower()
    if "sha256" in lowered or "hash" in lowered:
        if "docx" in lowered:
            return "đóng băng đúng dấu vân tay của file DOCX hiện hành, để backend phát hiện văn bản đã bị sửa sau lúc người dùng khởi tạo luồng ký hoặc luồng Hòm thư"
        return "tạo dấu vân tay cho file nguồn hoặc PDF đã ký, làm mốc so sánh toàn vẹn giữa DB và file thực tế"
    if "safe_filename" in lowered or "filename" in lowered:
        return "làm sạch tên file trước khi lưu ra storage hoặc phát cho nút tải xuống trên web"
    if "source_version" in lowered or "current_version" in lowered:
        return "chốt đúng version văn bản mà người dùng vừa nhìn thấy, để proposal ký, PDF đã ký hoặc Hòm thư không bám sang bản cũ"
    if "display_name" in lowered:
        return "chuẩn hóa tên hiển thị của người thao tác trong timeline Hòm thư, lịch sử ký và thông báo trạng thái"
    if "thread_status" in lowered:
        return "ghi trạng thái tổng, người thao tác cuối và lý do của thread Hòm thư để list và detail cùng đồng bộ"
    if "latest_forwardable_signed_pdf" in lowered or "latest_safe_signed_pdf" in lowered:
        return "chọn đúng bản PDF đã ký an toàn mới nhất mà flow hiện tại được phép dùng tiếp"
    if "invalidate_open_flows" in lowered:
        return "đóng các proposal, packet và task cũ trước khi mở quy trình ký mới cho cùng một văn bản"
    if "default_signature_mode" in lowered:
        return "chọn chế độ ký mặc định mà dialog Đề xuất ký và packet thực tế phải cùng hiểu giống nhau"
    if "validate" in lowered and "signing" in lowered:
        return "chặn sớm văn bản chưa đủ điều kiện ký trước khi web đi sâu hơn vào flow Đề xuất ký"
    if "integrity_report" in lowered or "signature_context" in lowered:
        return "tổng hợp trạng thái an toàn, chứng thư và bối cảnh file để màn PDF đã ký hoặc chi tiết ký hiển thị đúng"
    if "ensure" in lowered and "signing_task" in lowered:
        return "bảo đảm người nhận trong Hòm thư hoặc signer hiện tại có đủ nhiệm vụ ký tương ứng trước khi web cho họ đi tiếp"
    if "mailbox" in relative:
        return "cô lập một bước trung gian của luồng Hòm thư để transaction chính không phải lặp lại cùng một rule"
    if "signing" in relative or "pki" in relative:
        return "cô lập một bước trung gian của luồng ký số để transaction chính không phải lặp lại cùng một rule"
    return "cô lập một bước transaction, integrity hoặc đồng bộ trạng thái mà service chính phải dùng lặp lại"


def serializer_target(name: str) -> str:
    lowered = name.lower()
    if "list" in lowered:
        return "bảng hoặc tab danh sách"
    if "detail" in lowered:
        return "màn chi tiết, drawer thông tin hoặc vùng preview"
    if "write" in lowered or "input" in lowered or "create" in lowered or "form" in lowered:
        return "form submit hoặc dialog nhập liệu"
    if "version" in lowered:
        return "danh sách phiên bản, diff hoặc nút khôi phục"
    if "candidate" in lowered:
        return "dialog chọn người hoặc autocomplete"
    if "proposal" in lowered:
        return "card đề xuất ký và phần mô tả danh sách người ký"
    if "task" in lowered:
        return "card nhiệm vụ ký và màn chi tiết ký"
    if "thread" in lowered or "mailbox" in lowered:
        return "timeline hoặc chi tiết hòm thư"
    if "summary" in lowered:
        return "badge, header hoặc khối tổng hợp"
    return "một vùng dữ liệu hiển thị trên web"


def serializer_field_ui_role(field_name: str) -> str:
    lowered = field_name.lower()
    if lowered.startswith("can_"):
        return f"cờ quyền `{field_name}` để web biết có bật nút hoặc action tương ứng hay không"
    if lowered == "is_favorite":
        return "trạng thái bookmark mà icon yêu thích và bộ lọc yêu thích đang đọc"
    if lowered.endswith("_display") or "status_display" in lowered:
        return "nhãn trạng thái dễ đọc để badge và bảng không phải tự suy luận từ mã nội bộ"
    if lowered.endswith("_count"):
        return f"badge hoặc số đếm `{field_name}` mà web đang hiển thị cạnh tab, card hoặc vùng chi tiết"
    if lowered.endswith("_id"):
        return f"khóa định danh `{field_name}` để web mở đúng dialog, detail hoặc gọi action tiếp theo"
    if lowered.endswith("_name") or lowered.endswith("_title"):
        return f"text hiển thị `{field_name}` để card, bảng và tiêu đề chi tiết không phải gọi thêm API phụ"
    if "status" in lowered:
        return f"trạng thái `{field_name}` để web bật đúng màu badge, nút và thông báo"
    if "file" in lowered or "download" in lowered or "preview" in lowered:
        return f"thông tin `{field_name}` để web biết có cho xem trước hoặc tải file hay không"
    return f"field dẫn xuất `{field_name}` mà web cần thêm ngoài dữ liệu raw"


def service_ui_trigger(name: str, relative: str) -> str:
    lowered = name.lower()
    if "thread_status" in lowered:
        return "forward, hoàn thành hoặc từ chối trên màn Hòm thư và backend cần đồng bộ lại trạng thái tổng của thread"
    if "display_name" in lowered:
        return "mở timeline Hòm thư, xem lịch sử ký hoặc backend cần ghi lại ai vừa thao tác"
    if ("sha256" in lowered or "hash" in lowered) and "mailbox" in relative:
        return "forward văn bản, hoàn thành một entry Hòm thư hoặc backend cần khóa đúng file đã dùng để chuyển tiếp"
    if "sha256" in lowered or "hash" in lowered:
        return "bấm Đề xuất ký, Ký hoặc backend cần đối chiếu lại đúng file nguồn hay PDF của quy trình ký"
    if "default_signature_mode" in lowered:
        return "mở dialog Đề xuất ký hoặc khởi tạo packet ký mới"
    if "source_version" in lowered or "current_version" in lowered:
        return "tạo đề xuất ký, mở PDF đã ký hoặc forward một văn bản đang có nhiều version"
    if "invalidate_open_flows" in lowered:
        return "tạo đề xuất ký mới để thay thế quy trình cũ của cùng văn bản"
    if "validate" in lowered and "signing" in lowered:
        return "bấm Đề xuất ký từ chi tiết văn bản và backend phải chặn sớm văn bản chưa đủ điều kiện"
    if "latest_forwardable_signed_pdf" in lowered:
        return "bấm Forward trên Hòm thư và backend phải tìm đúng bản PDF đã ký an toàn mới nhất để chuyển tiếp"
    if "forward" in lowered or "mailbox" in lowered:
        return "bấm Forward, Hoàn thành hoặc Từ chối trên màn Hòm thư"
    if "sign_task" in lowered or lowered == "sign_task":
        return "bấm nút Ký trên màn chi tiết yêu cầu ký"
    if "reject_task" in lowered:
        return "bấm nút Từ chối trên màn chi tiết yêu cầu ký"
    if "approve_signing_proposal" in lowered:
        return "duyệt đề xuất ký từ vùng chờ phê duyệt hoặc từ flow ký số"
    if "reject_signing_proposal" in lowered:
        return "từ chối đề xuất ký từ vùng chờ phê duyệt"
    if "signing_proposal" in lowered or "start_signing_flow" in lowered:
        return "bấm nút Đề xuất ký hoặc Khởi động quy trình ký từ chi tiết văn bản"
    if "signed_pdf" in lowered or "integrity" in lowered or "signature_context" in lowered:
        return "mở PDF đã ký, mở màn verify hoặc tải chi tiết ngữ cảnh ký"
    if "archive" in lowered or "favorite" in lowered or "share" in lowered or "version" in lowered:
        return "bấm action trên danh sách hoặc chi tiết văn bản, mẫu hoặc file"
    if "preview" in lowered or "parse" in lowered or "extract" in lowered or "prefill" in lowered:
        return "bấm xem trước, parse file hoặc sinh dữ liệu trung gian trên web"
    if "backup" in lowered:
        return "bấm tạo, tải hoặc xóa backup từ màn Sao lưu dữ liệu"
    if "import" in lowered:
        return "upload file import từ giao diện quản trị"
    return f"thực hiện một thao tác nhiều bước mà endpoint thuộc `{relative}` cần đẩy xuống service"


def service_effect_hint(name: str, ui_summary: str) -> str:
    lowered = name.lower()
    if "thread_status" in lowered:
        return f"danh sách Hòm thư, số lượng chờ xử lý và màn chi tiết thread trong {ui_summary} cùng đổi sang một trạng thái tổng thống nhất"
    if "display_name" in lowered:
        return f"timeline Hòm thư, lịch sử ký và các câu mô tả trạng thái trong {ui_summary} hiển thị đúng tên người thao tác thay vì tên thiếu ngữ cảnh"
    if "sha256" in lowered or "hash" in lowered:
        return f"các flow ký số, forward Hòm thư và kiểm tra toàn vẹn trong {ui_summary} bám đúng cùng một phiên bản file, tránh ký hoặc forward nhầm bản đã bị sửa"
    if "source_version" in lowered or "current_version" in lowered:
        return f"proposal ký, PDF đã ký và Hòm thư trong {ui_summary} bám đúng version văn bản mà người dùng vừa thao tác"
    if "filename" in lowered:
        return f"file sinh ra cho {ui_summary} có tên ổn định, giúp nút tải xuống và lưu trữ không lỗi ký tự"
    if "default_signature_mode" in lowered:
        return f"dialog Đề xuất ký và packet thực tế của {ui_summary} cùng hiểu một chế độ ký mặc định"
    if "invalidate_open_flows" in lowered:
        return f"màn Yêu cầu ký và các badge liên quan trong {ui_summary} không còn song song proposal cũ sau khi người dùng mở quy trình mới"
    if "forward" in lowered or "mailbox" in lowered:
        return f"timeline, trạng thái entry, người nhận tiếp theo và badge Hòm thư trong {ui_summary} đổi đồng bộ sau một lần thao tác"
    if "sign" in lowered or "signed_pdf" in lowered or "integrity" in lowered:
        return f"trạng thái ký, badge an toàn, danh sách PDF đã ký và chi tiết ký trong {ui_summary} không bị lệch giữa DB và file thật"
    if "favorite" in lowered or "archive" in lowered or "restore" in lowered or "delete" in lowered:
        return f"danh sách, bộ lọc và badge số lượng trong {ui_summary} cập nhật đồng bộ ngay sau action của người dùng"
    if "preview" in lowered or "parse" in lowered or "extract" in lowered or "prefill" in lowered:
        return f"preview, danh sách biến, dữ liệu OCR hoặc kết quả sinh file trong {ui_summary} hiển thị đúng dữ liệu vừa xử lý"
    if "backup" in lowered or "import" in lowered:
        return f"các màn quản trị trong {ui_summary} nhìn thấy ngay kết quả mới mà không cần sửa tay dữ liệu nền"
    return f"các bước nhiều trạng thái trong {ui_summary} được chốt nhất quán trước khi web làm mới giao diện"


def feature_group_label(relative: str) -> str:
    if "guest" in relative:
        return "cổng guest"
    if "trash" in relative:
        return "màn Thùng rác"
    if "notifications" in relative or "dashboard" in relative:
        return "Bảng điều khiển"
    if "backup" in relative or "reset_db" in relative or "purge_trash" in relative:
        return "màn Sao lưu dữ liệu"
    if "auth" in relative or relative.startswith("accounts/"):
        return "nhóm màn Hồ sơ, tài khoản và quản trị người dùng"
    if "prompt" in relative:
        return "màn Cấu hình AI"
    if "signing" in relative or "pki" in relative:
        return "nhóm màn Yêu cầu ký, PDF đã ký và Ủy quyền ký số"
    if "template" in relative:
        return "nhóm màn Mẫu văn bản"
    if "chat" in relative or "assistant" in relative or "rag" in relative or "ai_doc" in relative or relative.startswith("ai_engine/"):
        return "nhóm màn AI và hỏi đáp tài liệu"
    if "documents" in relative or "mailbox" in relative:
        return "nhóm màn Văn bản và Hòm thư"
    return "các màn web hiện hành"


def endpoint_output_focus(name: str, relative: str) -> str:
    lowered = name.lower()
    if "summary" in lowered:
        return "trả số liệu tổng hợp cho badge hoặc khối header"
    if "candidate" in lowered:
        return "trả danh sách người dùng cho dialog chọn người"
    if "list" in lowered and "create" in lowered:
        return "cấp dữ liệu cho tab danh sách và nhận submit tạo mới"
    if "list" in lowered:
        return "cấp dữ liệu cho danh sách và bộ lọc"
    if "detail" in lowered:
        return "trả dữ liệu chi tiết và xử lý action trên một bản ghi"
    if "preview" in lowered or "content_html" in lowered or "html" in lowered:
        return "trả preview hoặc HTML để web mở ngay"
    if "download" in lowered or "file" in lowered:
        return "trả file cho thao tác tải xuống"
    if "candidate" in lowered or "suggest" in lowered:
        return "trả dữ liệu cho autocomplete hoặc dialog chọn người"
    if "proposal" in lowered and ("create" in lowered or "start" in lowered):
        return "nhận đề xuất ký từ dialog và khởi động flow tương ứng"
    if "integrity" in lowered or "verify" in lowered:
        return "trả trạng thái an toàn và kết quả kiểm tra"
    if "mailbox" in lowered:
        return "điều phối action của luồng Hòm thư"
    return "điều phối request chính của màn hình này"


def endpoint_ui_result(name: str, relative: str) -> str:
    lowered = name.lower()
    if "summary" in lowered:
        return "Badge và số liệu tổng hợp trên giao diện được làm mới từ response này."
    if "candidate" in lowered:
        return "Dialog chọn người chỉ hiện đúng các lựa chọn mà backend cho phép."
    if "preview" in lowered or "html" in lowered:
        return "Web biết có thể mở preview hay phải hiện lỗi ngay tại chỗ."
    if "download" in lowered or "file" in lowered:
        return "Nút tải xuống nhận đúng file cần trả về."
    if "integrity" in lowered or "verify" in lowered:
        return "Badge an toàn, cảnh báo sửa file và màn chi tiết xác minh đều bám theo response này."
    if "mailbox" in relative or "mailbox" in lowered:
        return "Timeline, trạng thái entry và các nút action trên Hòm thư đổi theo đúng response trả về."
    return "Danh sách, dialog hoặc badge trên giao diện cập nhật trực tiếp theo response này."


def helper_ui_result(name: str) -> str:
    lowered = name.lower()
    if "error" in lowered or "response" in lowered:
        return "Các endpoint cùng trả một kiểu thông báo lỗi, nên toast và dialog trên web không bị lệch câu chữ."
    if "build" in lowered and "search" in lowered:
        return "Mọi tab danh sách cho cùng một kết quả khi người dùng nhập một cụm từ hoặc nhiều từ khóa."
    if "multi_value_query_param" in lowered:
        return "Bộ lọc nhiều lựa chọn trên web gửi lên thế nào thì backend hiểu lại đúng như vậy."
    if "search" in lowered or "query" in lowered or "normalize" in lowered:
        return "Mọi tab danh sách hiểu cùng một từ khóa, kể cả khi người dùng gõ dấu câu hoặc nhiều khoảng trắng."
    if "resolve" in lowered and "signer" in lowered:
        return "Dialog chọn người ký gửi dữ liệu thế nào thì backend hiểu thống nhất như vậy."
    if "preview" in lowered or "parse" in lowered or "extract" in lowered or "html" in lowered or "docx" in lowered:
        return "Preview, OCR hoặc danh sách biến trên web đọc đúng dữ liệu trung gian vừa được backend chuẩn hóa."
    if "validate" in lowered or "ensure" in lowered or "check" in lowered:
        return "Người dùng bị chặn sớm ở đúng bước, thay vì đi sâu hơn rồi mới vỡ flow."
    return "Các endpoint dùng chung một quy tắc, nên hành vi giữa các màn không bị lệch nhau."


def serializer_ui_result(name: str) -> str:
    lowered = name.lower()
    if "list" in lowered:
        return "Bảng danh sách đọc trực tiếp payload này để dựng từng dòng, badge và nút action."
    if "detail" in lowered:
        return "Màn chi tiết và drawer thông tin lấy dữ liệu từ đây, không phải vá thêm bằng API phụ."
    if "write" in lowered or "input" in lowered or "create" in lowered or "form" in lowered:
        return "Form submit bám đúng contract này nên backend và frontend không lệch field."
    if "proposal" in lowered:
        return "Card đề xuất ký và danh sách signer hiển thị đúng từng vai trò, thứ tự và trạng thái."
    if "task" in lowered:
        return "Card nhiệm vụ ký có đủ cờ trạng thái và ngữ cảnh để bật đúng nút trên web."
    if "thread" in lowered or "mailbox" in lowered:
        return "Timeline Hòm thư dựng từ payload này nên từng entry hiện đúng người, đúng trạng thái và đúng lý do."
    return "Frontend đọc trực tiếp payload này để dựng giao diện mà không phải suy luận thêm."


def serializer_field_ui_result(field_name: str) -> str:
    lowered = field_name.lower()
    if lowered.startswith("can_"):
        return "Frontend dùng cờ này để bật, ẩn hoặc khóa đúng nút thao tác."
    if lowered.endswith("_display") or "status_display" in lowered or "status" in lowered:
        return "Badge và text trạng thái trên giao diện đọc trực tiếp từ field này."
    if lowered == "is_favorite":
        return "Icon yêu thích và bộ lọc yêu thích đổi đúng theo field này."
    if lowered.endswith("_count"):
        return "Số đếm trên tab, card hoặc vùng chi tiết lấy trực tiếp từ field này."
    if lowered.endswith("_id"):
        return "Web dùng ID này để mở đúng detail, dialog hoặc action tiếp theo."
    if lowered.endswith("_name") or lowered.endswith("_title"):
        return "Giao diện không phải gọi thêm API chỉ để lấy text hiển thị."
    if "file" in lowered or "download" in lowered or "preview" in lowered:
        return "Frontend biết có cho xem trước hoặc tải file ở bước này hay không."
    return ""


def service_ui_result_short(name: str) -> str:
    lowered = name.lower()
    if "validate" in lowered or "ensure" in lowered or "check" in lowered:
        return "Người dùng bị chặn đúng lúc nếu điều kiện nghiệp vụ chưa đạt."
    if "thread_status" in lowered:
        return "List Hòm thư, số lượng chờ xử lý và màn chi tiết thread cùng nhìn một trạng thái tổng."
    if "display_name" in lowered:
        return "Timeline và lịch sử ký hiển thị đúng tên người vừa thao tác."
    if "sha256" in lowered or "hash" in lowered:
        return "Flow đang mở bám đúng phiên bản file, tránh ký hoặc chuyển tiếp nhầm bản đã bị sửa."
    if "source_version" in lowered or "current_version" in lowered:
        return "Proposal ký, PDF đã ký hoặc Hòm thư không bám nhầm sang version cũ."
    if "filename" in lowered:
        return "File sinh ra có tên ổn định để nút tải xuống và lưu trữ không lỗi."
    if "default_signature_mode" in lowered:
        return "Dialog đề xuất ký và packet thực tế cùng hiểu một chế độ ký mặc định."
    if "invalidate_open_flows" in lowered:
        return "Màn Yêu cầu ký không còn song song proposal cũ sau khi mở quy trình mới."
    if "forward" in lowered or "mailbox" in lowered:
        return "Timeline, người nhận tiếp theo và badge Hòm thư được đồng bộ sau thao tác này."
    if "sign" in lowered or "signed_pdf" in lowered or "integrity" in lowered:
        return "Badge an toàn, trạng thái ký và danh sách PDF đã ký đổi đúng theo file thật."
    if "favorite" in lowered or "archive" in lowered or "restore" in lowered or "delete" in lowered:
        return "Danh sách và bộ lọc đổi ngay sau action của người dùng."
    if "preview" in lowered or "parse" in lowered or "extract" in lowered or "prefill" in lowered:
        return "Preview, OCR hoặc dữ liệu sinh file hiển thị đúng đầu ra vừa xử lý."
    return "DB, file và trạng thái hiển thị được giữ đồng bộ sau cùng."


def compact_symbol_comment_lines(info: dict[str, str], category: str, name: str, parent_name: str) -> list[str]:
    group = feature_group_label(info["relative"])
    resource_label = info["resource_label"]
    if category == "endpoint":
        return [
            f"[Web] Trong {group}, endpoint `{name}` được gọi khi người dùng {endpoint_ui_trigger(name)}.",
            f"[UI] Nó {endpoint_output_focus(name, info['relative'])}; {endpoint_ui_result(name, info['relative']).lower()}",
        ]
    if category == "helper_function":
        return [
            f"[Web] Trong {group}, `{name}` tách riêng bước {helper_focus(name, resource_label)}.",
            f"[UI] {helper_ui_result(name)}",
        ]
    if category == "nested_function":
        return [
            f"[Web] `{name}` là bước con bên trong `{parent_name}` để tách một phép xử lý nhỏ cho dễ đọc và khó sai hơn.",
        ]
    if category == "serializer":
        return [
            f"[Web] `{name}` chốt payload cho {serializer_target(name)} của {group}.",
            f"[UI] {serializer_ui_result(name)}",
        ]
    if category == "serializer_meta":
        return [
            f"[Web] `Meta` của `{parent_name}` khóa đúng model và bộ field mà frontend được phép đọc hoặc submit.",
        ]
    if category == "serializer_field_method":
        field_name = name[4:] if name.startswith("get_") else name
        line = f"[Web] `{name}` tính {serializer_field_ui_role(field_name)}."
        return [line]
    if category == "serializer_method":
        return [
            f"[Web] `{name}` can thiệp vào bước validate hoặc serialize để payload của {group} bám đúng rule nghiệp vụ.",
        ]
    if category == "serializer_helper":
        return [
            f"[Web] `{name}` chuẩn hóa dữ liệu phụ cho serializer, tránh lệch contract giữa các API của {group}.",
        ]
    if category == "permission_rule":
        action_text = symbol_action_text(name, resource_label, "thao tác tương ứng")
        return [
            f"[Web] `{name}` quyết định user có được {action_text} và có được thấy đúng record trong {group} hay không.",
            "[UI] Nếu rule này không đạt, web sẽ ẩn nút hoặc bị chặn action ngay từ response của backend.",
        ]
    if category == "permission_class":
        return [
            f"[Web] `{name}` gom các rule phân quyền cho {group}, đặc biệt là các màn có nút action theo vai trò.",
        ]
    if category == "permission_method":
        return [
            f"[Web] `{name}` kiểm tra quyền hoặc điều kiện trạng thái trước khi backend cho phép flow đi tiếp trong {group}.",
        ]
    if category == "service_function":
        if name.startswith("_"):
            return [
                f"[Web] `{name}` là bước nội bộ của service để {service_internal_focus(name, info['relative'])}.",
                f"[UI] {service_ui_result_short(name)}",
            ]
        trigger = service_ui_trigger(name, info["relative"])
        return [
            f"[Web] `{name}` thực thi nghiệp vụ chính khi người dùng {trigger}.",
            f"[UI] {service_ui_result_short(name)}",
        ]
    if category == "model":
        return [
            f"[Web] Model `{name}` là nơi lưu trạng thái nghiệp vụ gốc mà {group} đang đọc để dựng danh sách, badge và màn chi tiết.",
        ]
    if category == "model_method":
        return [
            f"[Web] `{name}` thay đổi hoặc suy ra trạng thái của model; kết quả đó sẽ phản ánh lại lên giao diện sau khi reload.",
        ]
    if category == "form":
        return [
            f"[Web] `{name}` kiểm tra dữ liệu nhập từ admin hoặc flow legacy trước khi dữ liệu quay lại ảnh hưởng lên {group}.",
        ]
    if category == "form_method":
        return [
            f"[Web] `{name}` áp rule validate hoặc làm sạch dữ liệu để chặn lỗi ngay ở biên nhập liệu.",
        ]
    if category == "command_class":
        return [
            "[Web] `Command` gom tác vụ vận hành nền làm mới dữ liệu hoặc cấu hình mà các màn web đang dựa vào.",
        ]
    if category == "command_handler":
        return [
            "[Web] `handle` là điểm chạy chính của lệnh nền này; admin dùng nó để sửa dữ liệu ngoài giao diện web.",
        ]
    if category == "command_function":
        return [
            f"[Web] `{name}` hỗ trợ lệnh nền xử lý dữ liệu hoặc cấu hình phục vụ cho {group}.",
        ]
    if category == "signal_handler":
        return [
            f"[Web] `{name}` đồng bộ side effect nền sau khi model đổi, tránh để UI và DB lệch nhau trong {group}.",
        ]
    if category == "route_helper":
        return [
            f"[Web] `{name}` giữ route backend đi đúng đích để request của {group} không bị lệch sang view khác.",
        ]
    if category == "class":
        if name.endswith("Error") or name.endswith("Exception"):
            return [
                f"[Web] `{name}` gom lỗi nghiệp vụ của {group} để endpoint map ra đúng toast, dialog hoặc HTTP error.",
            ]
        return [
            f"[Web] `{name}` gom một cụm xử lý backend dùng chung cho {group}.",
        ]
    if category == "method":
        return [
            f"[Web] `{name}` là bước nội bộ của class để hỗ trợ dữ liệu hoặc trạng thái mà {group} đang cần.",
        ]
    return [
        f"[Web] `{name}` xử lý một phần logic backend phục vụ cho {group}.",
    ]


def symbol_role_sentence(info: dict[str, str], category: str, name: str, parent_name: str) -> str:
    resource_label = info["resource_label"]
    ui_summary = info["ui_summary"]
    surface = info["surface"]
    if category == "endpoint":
        action_text = symbol_action_text(name, resource_label, "xử lý request chính của {resource_label}")
        trigger = endpoint_ui_trigger(name)
        return f"Endpoint `{name}` là điểm backend mà web gọi khi người dùng {trigger} trong {surface}; nó chịu trách nhiệm {action_text} cho các chức năng {ui_summary}."
    if category == "helper_function":
        return f"Hàm `{name}` được tách riêng để {helper_focus(name, resource_label)}; nhiều endpoint của {ui_summary} có thể dùng lại cùng một bước này mà không phải sao chép logic."
    if category == "nested_function":
        return f"Hàm lồng `{name}` cô lập một phép biến đổi nhỏ bên trong khối xử lý lớn hơn, để bước phụ trợ cho {ui_summary} dễ đọc và khó sai lệch hơn."
    if category == "serializer":
        return f"Lớp `{name}` chốt payload cho {serializer_target(name)} trong {surface}, để web nhận đúng dữ liệu mà không phải đoán thêm từ response."
    if category == "serializer_meta":
        return f"Lớp `Meta` khóa model nguồn và bộ field mà `{parent_name}` được phép phát ra hoặc nhận vào, tức là khóa luôn hợp đồng dữ liệu mà màn hình web đang dựa vào."
    if category == "serializer_field_method":
        field_name = name[4:] if name.startswith("get_") else name
        return f"Phương thức `{name}` tính {serializer_field_ui_role(field_name)}."
    if category == "serializer_method":
        return f"Phương thức `{name}` can thiệp vào bước validate hoặc serialize để payload mà {surface} đọc được bám đúng rule nghiệp vụ."
    if category == "serializer_helper":
        return f"Hàm `{name}` hỗ trợ serializer chuẩn hóa dữ liệu hoặc dựng field phụ, để contract API của {ui_summary} không bị lệch giữa các endpoint."
    if category == "permission_rule":
        action_text = symbol_action_text(name, resource_label, "thực hiện thao tác trên {resource_label}")
        return f"Hàm `{name}` quyết định người dùng có được {action_text} hay nhìn thấy đúng record hay không trước khi web bật action ở {surface}."
    if category == "permission_class":
        return f"Lớp `{name}` gom các rule phân quyền backend cho {resource_label}, đặc biệt là những rule quyết định ai được mở màn, thấy dữ liệu và bấm nút ở {surface}."
    if category == "permission_method":
        return f"Phương thức `{name}` kiểm tra quyền hoặc điều kiện trạng thái trước khi backend cho phép flow ở {surface} đi tiếp."
    if category == "service_function":
        if name.startswith("_"):
            trigger = service_ui_trigger(name, info["relative"])
            return f"Hàm nội bộ `{name}` chạy phía sau service để {service_internal_focus(name, info['relative'])}; nó được gọi ngầm khi người dùng {trigger}."
        action_text = symbol_action_text(name, resource_label, "xử lý nghiệp vụ lõi của {resource_label}")
        trigger = service_ui_trigger(name, info["relative"])
        return f"Hàm `{name}` là lõi nghiệp vụ cho bước {action_text}; web chạm tới hàm này khi người dùng {trigger}."
    if category == "model":
        return f"Model `{name}` lưu trạng thái nghiệp vụ gốc mà các chức năng {ui_summary} đang đọc để vẽ danh sách, badge, timeline và màn chi tiết."
    if category == "model_method":
        return f"Phương thức `{name}` thay đổi hoặc suy ra trạng thái model theo rule nghiệp vụ, tức là thay đổi điều mà người dùng sẽ nhìn thấy lại trên {surface}."
    if category == "form":
        return f"Lớp `{name}` kiểm tra dữ liệu nhập từ admin hoặc luồng legacy liên quan tới {resource_label}, trước khi dữ liệu đó quay lại ảnh hưởng lên các chức năng {ui_summary}."
    if category == "form_method":
        return f"Phương thức `{name}` áp rule validate hoặc biến đổi dữ liệu cho form backend, nhằm chặn lỗi từ sớm trước khi thông tin sai xuất hiện trên web."
    if category == "command_class":
        return "Lớp `Command` gom tác vụ vận hành nền phục vụ dữ liệu hoặc cấu hình mà web đang dựa vào."
    if category == "command_handler":
        return "Phương thức `handle` là điểm chạy chính của lệnh vận hành; nó kích hoạt toàn bộ job mà admin chủ động chạy ngoài giao diện web."
    if category == "command_function":
        return f"Hàm `{name}` hỗ trợ lệnh nền thao tác dữ liệu hoặc cấu hình phục vụ các chức năng {ui_summary}."
    if category == "signal_handler":
        return f"Hàm `{name}` đồng bộ side effect sau khi model thay đổi, để dữ liệu trên {surface} không cần sửa tay ở từng endpoint."
    if category == "route_helper":
        return f"Hàm `{name}` hỗ trợ route hoặc redirect backend để request của các chức năng {ui_summary} đi đúng đích."
    if category == "class":
        if name.endswith("Error") or name.endswith("Exception"):
            return f"Lớp `{name}` chuẩn hóa lỗi nghiệp vụ của {resource_label}; service và endpoint ném kiểu lỗi này khi cần dừng flow để web hiển thị đúng thông báo trên {surface}."
        return f"Lớp `{name}` gom một cụm xử lý backend dùng chung cho {resource_label}, giúp code giữ được một đầu mối rõ ràng cho flow mà web đang dùng."
    if category == "method":
        return f"Phương thức `{name}` xử lý một bước nội bộ trong class để hỗ trợ dữ liệu hoặc trạng thái mà {surface} đang cần."
    return f"Hàm `{name}` xử lý một phần logic backend của {resource_label} phục vụ các chức năng {ui_summary}."


def symbol_process_sentence(info: dict[str, str], category: str, name: str) -> str:
    if category == "endpoint":
        return "Khối này đọc request từ web, gom bộ lọc hoặc payload, áp phân quyền, gọi queryset hoặc service phù hợp rồi serialize hoặc trả lỗi theo đúng hợp đồng mà frontend đang mong đợi."
    if category == "helper_function":
        return f"Khối này tách riêng bước “{helper_focus(name, info['resource_label'])}”, để các endpoint dùng chung một nơi thay vì mỗi nơi tự xử lý một kiểu."
    if category == "nested_function":
        return "Khối này cô lập một phép biến đổi cục bộ hoặc một vòng lặp nhỏ bên trong flow lớn hơn, nhờ vậy phần xử lý chính bớt rối và dễ kiểm tra hơn."
    if category == "serializer":
        return "Serializer ánh xạ model hoặc payload thành JSON, đồng thời bổ sung các field phụ mà UI cần để quyết định text hiển thị, badge trạng thái và action khả dụng."
    if category == "serializer_meta":
        return "Khối này chốt model nguồn, danh sách field và chính sách read-only hoặc write-only để contract giữa backend với frontend không bị lệch theo thời gian."
    if category == "serializer_field_method":
        field_name = name[4:] if name.startswith("get_") else name
        return f"Khối này suy ra field `{field_name}` từ object, request hoặc context hiện tại rồi chèn vào payload cuối cùng mà web nhận được."
    if category == "serializer_method":
        return "Khối này can thiệp vào bước validate hoặc serialize để dữ liệu đi ra và đi vào luôn bám đúng rule nghiệp vụ của màn hình."
    if category in {"permission_rule", "permission_class", "permission_method"}:
        return "Khối này đọc user, object, quan hệ nhóm hoặc phòng ban và trạng thái hiện tại rồi trả verdict cho phép, chặn hoặc thu hẹp dữ liệu mà web được phép thấy."
    if category == "service_function":
        if name.startswith("_"):
            return "Khối này không lộ ra endpoint riêng; service chính gọi nó như một bước ngầm để khóa dữ liệu trung gian, kiểm tra điều kiện hoặc đồng bộ trạng thái trước khi transaction hoàn tất."
        return "Khối này gom transaction, cập nhật nhiều bản ghi, đồng bộ file hoặc integrity, gọi engine ngoài nếu cần và chỉ trả kết quả sau khi toàn bộ bước quan trọng đã được chốt."
    if category == "model":
        return "Khối này định nghĩa field, quan hệ và helper mà mọi lớp view, serializer, permission và service dùng như nguồn dữ liệu chuẩn."
    if category == "model_method":
        return "Khối này thay đổi hoặc suy ra trạng thái model tại đúng chỗ lưu trữ gốc, giúp các lớp phía trên không phải mỗi nơi tự hiểu nghiệp vụ một kiểu."
    if category in {"form", "form_method"}:
        return "Khối này validate, làm sạch hoặc ánh xạ dữ liệu submit trước khi backend chấp nhận lưu, nhằm chặn sai lệch ngay ở biên nhập liệu."
    if category in {"command_class", "command_handler", "command_function"}:
        return "Khối này chạy job nền, đọc tham số CLI và cập nhật dữ liệu hoặc cấu hình mà web sẽ đọc lại ở các lần mở màn sau."
    if category == "signal_handler":
        return "Khối này được gọi khi model thay đổi để tự động kéo theo những bước đồng bộ nền mà endpoint không trực tiếp đụng tới."
    if category == "route_helper":
        return "Khối này giúp route hoặc redirect backend đi đúng hướng mà không phải lặp lại cấu hình ở nhiều nơi."
    if category == "class" and (name.endswith("Error") or name.endswith("Exception")):
        return "Khối này không tự xử lý dữ liệu nghiệp vụ; nó giữ thông điệp lỗi có cấu trúc để service và view bắt lại, map ra response hoặc dừng luồng tại đúng thời điểm."
    return "Khối này giữ phần xử lý dùng chung cho backend và được gọi lại từ những flow nghiệp vụ liên quan."


def symbol_effect_sentence(info: dict[str, str], category: str, name: str) -> str:
    ui_summary = info["ui_summary"]
    surface = info["surface"]
    if category == "endpoint":
        return f"Web dùng response của hàm này để làm mới dữ liệu, đóng hoặc mở dialog, đổi badge trạng thái, bật tắt nút và hiển thị thông báo lỗi trên {surface} thuộc các chức năng {ui_summary}."
    if category == "helper_function":
        return f"Nhờ dùng chung helper này, các màn trong {ui_summary} giữ cùng một cách hiểu về dữ liệu và lỗi, nên người dùng không gặp cảnh mỗi API phản ứng một kiểu."
    if category == "nested_function":
        return f"Logic cục bộ bên trong flow lớn hơn được giữ nhất quán, từ đó dữ liệu trả về cho {surface} ít bị sai lệch ở những trường hợp biên."
    if category == "serializer":
        return f"Bảng, card, detail, dialog hoặc form trong {surface} nhận đúng cấu trúc JSON để render mà không cần gọi thêm API phụ chỉ để vá thiếu field."
    if category == "serializer_meta":
        return f"Nếu cần thêm hoặc bỏ field cho web, đây là điểm khóa hợp đồng; vì vậy các màn thuộc {ui_summary} giữ được hành vi ổn định khi backend đổi logic."
    if category == "serializer_field_method":
        field_name = name[4:] if name.startswith("get_") else name
        return f"Frontend nhận thêm field `{field_name}` ngay trong payload chính, nên badge, text, quyền nút hoặc link điều hướng ở {surface} hiển thị đúng ngay lần render đầu."
    if category == "serializer_method":
        return f"Payload mà {surface} nhận được bám đúng nghiệp vụ hơn, nhờ đó web không phải tự xử lý bù các trường hợp đặc biệt ở phía client."
    if category in {"permission_rule", "permission_class", "permission_method"}:
        return f"Record, nút bấm và thông báo lỗi ở các chức năng {ui_summary} chỉ xuất hiện cho đúng người và đúng trạng thái nghiệp vụ."
    if category == "service_function":
        return service_effect_hint(name, ui_summary) + "."
    if category in {"model", "model_method"}:
        return f"Dữ liệu lưu dưới khối này là nguồn sự thật cuối cùng để {surface} hiển thị trạng thái mới nhất sau mỗi lần web làm mới."
    if category in {"form", "form_method"}:
        return f"Người dùng hoặc admin nhìn thấy lỗi validate đúng chỗ và dữ liệu lưu ra sau cùng không làm hỏng các chức năng {ui_summary}."
    if category in {"command_class", "command_handler", "command_function"}:
        return f"Sau khi lệnh nền chạy xong, dữ liệu hoặc cấu hình phục vụ {ui_summary} sẽ được sửa về trạng thái mà web có thể đọc lại an toàn."
    if category == "signal_handler":
        return f"Những thay đổi phát sinh từ {ui_summary} vẫn kéo theo các đồng bộ nền cần thiết, giúp UI không bị lệch giữa trạng thái hiển thị và trạng thái lưu trữ."
    if category == "route_helper":
        return f"Request hoặc redirect đi đúng luồng nên người dùng không bị văng sai màn trong các chức năng {ui_summary}."
    if category == "class" and (name.endswith("Error") or name.endswith("Exception")):
        return f"Khi service hoặc endpoint ném lỗi này, người dùng ở {surface} nhận đúng toast, dialog hoặc HTTP error theo ngữ cảnh thay vì một lỗi mơ hồ khó truy vết."
    return f"Khối này góp phần giữ cho {surface} hiển thị đúng dữ liệu và đúng hành vi theo logic backend mới nhất."


def symbol_annotation(path: Path, kind: str, name: str, indent: str, *, parent_name: str = "") -> list[str]:
    info = file_context(path)
    if path.suffix == ".py" and is_backend_python_file(path):
        return comment_block(path.suffix, compact_symbol_comment_lines(info, kind, name, parent_name), indent)

    kind_text = {
        "class": "lớp",
        "function": "hàm",
        "method": "phương thức",
        "provider": "provider",
        "widget": "widget",
        "selector": "khối style",
        "handler": "trình xử lý",
    }.get(kind, "thành phần")
    human_name = split_snake(name) or name
    return comment_block(
        path.suffix,
        [
            f"Mục đích: {kind_text.capitalize()} `{name}` triển khai phần việc `{human_name}` trong {info['relative']}.",
            "Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.",
            f"Vai trò trong hệ thống: Đây là {kind_text} thuộc {info['role']}.",
            f"Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `{info['subsystem']}` chạy đúng trách nhiệm tại đúng thời điểm.",
        ],
        indent,
    )


def apply_inserts(lines: list[str], inserts: dict[int, list[list[str]]]) -> list[str]:
    result: list[str] = []
    for index, line in enumerate(lines):
        for block in inserts.get(index, []):
            result.extend(block)
            result.append("")
        result.append(line)
    return result


def annotate_python(lines: list[str], path: Path) -> list[str]:
    if not is_backend_python_file(path):
        return lines

    source = "\n".join(lines)
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return lines

    collector = PythonSymbolCollector(path, lines)
    collector.visit(tree)
    inserts: dict[int, list[list[str]]] = defaultdict(list)
    for symbol in collector.symbols:
        start_index = int(symbol["start_index"])
        if has_recent_annotation(lines, start_index, "Chức năng web liên quan:"):
            continue
        inserts[start_index].append(
            symbol_annotation(
                path,
                str(symbol["category"]),
                str(symbol["name"]),
                str(symbol["indent"]),
                parent_name=str(symbol["parent_name"]),
            )
        )

    return apply_inserts(lines, inserts)


DART_SYMBOL_RE = re.compile(
    r"^(?P<indent>\s*)(?:(class|enum|extension)\s+(?P<symbol>[A-Za-z_][A-Za-z0-9_]*)|final\s+(?P<provider>[A-Za-z_][A-Za-z0-9_]*Provider)\s*=|(?P<rtype>Future<[^>]+>|Future|Widget|void|String|int|double|bool|Locale)\s+(?P<func>[A-Za-z_][A-Za-z0-9_]*)\s*\()"
)
DART_KEY_PATTERNS = [
    (re.compile(r"MaterialApp\.router"), DART_KEY_TEXTS[0]),
    (re.compile(r"\bShellRoute\("), DART_KEY_TEXTS[1]),
    (re.compile(r"\bGoRoute\("), DART_KEY_TEXTS[2]),
    (re.compile(r"\bref\.watch\("), DART_KEY_TEXTS[3]),
    (re.compile(r"\bref\.read\("), DART_KEY_TEXTS[4]),
    (re.compile(r"\bawait\b.*\b(api|client|dio)\b", re.IGNORECASE), DART_KEY_TEXTS[5]),
    (re.compile(r"\bcontext\.(go|push|pop)\b"), DART_KEY_TEXTS[6]),
    (re.compile(r"\bsetState\("), DART_KEY_TEXTS[7]),
    (re.compile(r"\bScaffold\("), DART_KEY_TEXTS[8]),
]


def annotate_dart(lines: list[str], path: Path) -> list[str]:
    inserts: dict[int, list[list[str]]] = defaultdict(list)
    for index, line in enumerate(lines):
        match = DART_SYMBOL_RE.match(line)
        if match and not has_recent_annotation(lines, index, "Mục đích:"):
            indent = match.group("indent")
            if match.group("provider"):
                inserts[index].append(symbol_annotation(path, "provider", match.group("provider"), indent))
            elif match.group("symbol"):
                kind = "widget" if "screen" in match.group("symbol").lower() or "shell" in match.group("symbol").lower() else "class"
                inserts[index].append(symbol_annotation(path, kind, match.group("symbol"), indent))
            elif match.group("func") and match.group("func") not in {"if", "for", "while", "switch"}:
                kind = "method" if indent else "function"
                inserts[index].append(symbol_annotation(path, kind, match.group("func"), indent))

        stripped = line.strip()
        if not stripped or stripped.startswith("//"):
            continue
        for pattern, text in DART_KEY_PATTERNS:
            if pattern.search(line) and not previous_non_empty(lines, index).strip().startswith("//"):
                if not has_recent_annotation(lines, index, text, lookback=2):
                    indent = re.match(r"^\s*", line).group(0)
                    inserts[index].append(comment_block(path.suffix, [text], indent))
                break
    return apply_inserts(lines, inserts)


JS_SYMBOL_RE = re.compile(r"^(?P<indent>\s*)(?:function\s+(?P<func>[A-Za-z_][A-Za-z0-9_]*)\s*\(|const\s+(?P<const>[A-Za-z_][A-Za-z0-9_]*)\s*=.*=>)")
JS_KEY_PATTERNS = [
    (re.compile(r"addEventListener\("), JS_KEY_TEXTS[0]),
    (re.compile(r"querySelectorAll\("), JS_KEY_TEXTS[1]),
    (re.compile(r"Swal\.fire\("), JS_KEY_TEXTS[2]),
    (re.compile(r"navigator\.clipboard"), JS_KEY_TEXTS[3]),
]


def annotate_js(lines: list[str], path: Path) -> list[str]:
    inserts: dict[int, list[list[str]]] = defaultdict(list)
    for index, line in enumerate(lines):
        match = JS_SYMBOL_RE.match(line)
        if match and not has_recent_annotation(lines, index, "Mục đích:"):
            name = match.group("func") or match.group("const")
            kind = "handler" if "handle" in name.lower() or "listener" in name.lower() else "function"
            inserts[index].append(symbol_annotation(path, kind, name, match.group("indent")))

        stripped = line.strip()
        if not stripped or stripped.startswith("//"):
            continue
        for pattern, text in JS_KEY_PATTERNS:
            if pattern.search(line) and not previous_non_empty(lines, index).strip().startswith("//"):
                if not has_recent_annotation(lines, index, text, lookback=2):
                    indent = re.match(r"^\s*", line).group(0)
                    inserts[index].append(comment_block(path.suffix, [text], indent))
                break
    return apply_inserts(lines, inserts)


HTML_SECTION_PATTERNS = [
    (re.compile(r"{%\s*block\s+([A-Za-z_][A-Za-z0-9_]*)"), HTML_KEY_TEXTS[0]),
    (re.compile(r"<nav\b", re.IGNORECASE), HTML_KEY_TEXTS[1]),
    (re.compile(r"<main\b", re.IGNORECASE), HTML_KEY_TEXTS[2]),
    (re.compile(r"<section\b", re.IGNORECASE), HTML_KEY_TEXTS[3]),
    (re.compile(r"<form\b", re.IGNORECASE), HTML_KEY_TEXTS[4]),
    (re.compile(r"<table\b", re.IGNORECASE), HTML_KEY_TEXTS[5]),
    (re.compile(r"<script\b", re.IGNORECASE), HTML_KEY_TEXTS[6]),
]


def annotate_html(lines: list[str], path: Path) -> list[str]:
    inserts: dict[int, list[list[str]]] = defaultdict(list)
    for index, line in enumerate(lines):
        stripped = line.strip()
        if not stripped or stripped.startswith("<!--"):
            continue
        for pattern, text in HTML_SECTION_PATTERNS:
            if pattern.search(line) and not previous_non_empty(lines, index).strip().startswith("<!--"):
                if not has_recent_annotation(lines, index, text, lookback=2):
                    indent = re.match(r"^\s*", line).group(0)
                    inserts[index].append(comment_block(path.suffix, [text], indent))
                break
    return apply_inserts(lines, inserts)


CSS_SELECTOR_RE = re.compile(r"^(?P<indent>\s*)(?P<selector>[#.A-Za-z][^{]+)\{\s*$")


def annotate_css(lines: list[str], path: Path) -> list[str]:
    inserts: dict[int, list[list[str]]] = defaultdict(list)
    for index, line in enumerate(lines):
        match = CSS_SELECTOR_RE.match(line)
        if match and not has_recent_annotation(lines, index, "Mục đích:"):
            selector = match.group("selector").strip()
            inserts[index].append(
                comment_block(
                    path.suffix,
                    [
                        f"Mục đích: Khối style `{selector}` kiểm soát cách thành phần tương ứng hiển thị trên giao diện.",
                        "Cách hoạt động: Các thuộc tính bên dưới sẽ được trình duyệt áp lên selector khớp để tạo ra bố cục, màu sắc và hành vi hiển thị cần thiết.",
                        "Vai trò trong hệ thống: Đây là khối style thuộc lớp giao diện tĩnh.",
                        "Tác dụng khi hệ thống vận hành: Khối này giúp màn hình giữ được tính dễ dùng và nhận diện nhất quán.",
                    ],
                    match.group("indent"),
                )
            )
    return apply_inserts(lines, inserts)


def annotate_source_file(path: Path) -> bool:
    raw_original = path.read_text(encoding="utf-8")
    original = raw_original.replace("\ufeff", "")
    lines = strip_generated_comments(path, original.splitlines())
    lines = insert_header(path, lines)

    if path.suffix == ".py":
        lines = annotate_python(lines, path)
    elif path.suffix == ".dart":
        lines = annotate_dart(lines, path)
    elif path.suffix == ".js":
        lines = annotate_js(lines, path)
    elif path.suffix == ".html":
        lines = annotate_html(lines, path)
    elif path.suffix == ".css":
        lines = annotate_css(lines, path)

    updated = "\n".join(lines).rstrip() + "\n"
    if updated != raw_original:
        write_text(path, updated)
        return True
    return False


COMPONENT_RE = re.compile(r"^\s*(actor|package|component|database|folder|cloud|legend|note)\b")
PATH_RE = re.compile(r"(?<![A-Za-z0-9_])([A-Za-z0-9_./-]+\.(?:py|dart|html|js|css|puml))")


def extract_primary_files(lines: list[str]) -> list[str]:
    primary: list[str] = []
    for line in lines:
        normalized = line.replace("\\n", "\n")
        for match in PATH_RE.findall(normalized):
            cleaned = match.lstrip("./")
            if cleaned not in primary:
                primary.append(cleaned)
    return primary


def component_comment(line: str) -> str | None:
    stripped = line.strip()
    if stripped.startswith("package "):
        return PUML_COMMENT_LINES[0]
    if stripped.startswith("component "):
        return PUML_COMMENT_LINES[1]
    if stripped.startswith("database "):
        return PUML_COMMENT_LINES[2]
    if stripped.startswith("folder "):
        return PUML_COMMENT_LINES[3]
    if stripped.startswith("cloud "):
        return PUML_COMMENT_LINES[4]
    if stripped.startswith("actor "):
        return PUML_COMMENT_LINES[5]
    if stripped.startswith("legend "):
        return PUML_COMMENT_LINES[6]
    if stripped.startswith("note "):
        return PUML_COMMENT_LINES[7]
    return None


def note_lines(path: Path, lines: list[str]) -> list[str]:
    relative = rel_path(path)
    primary = extract_primary_files(lines)
    related = []
    for item in DIAGRAM_RELATED.get(relative, []):
        if item not in primary and item not in related:
            related.append(item)
    note = ["note bottom", "Files referenced", "Primary files:"]
    note.extend([f"- {item}" for item in primary] or ["- Khong co file path duoc viet truc tiep trong component label"])
    note.append("Related files:")
    note.extend([f"- {item}" for item in related] or ["- Khong co file bo tro duoc khai bao rieng"])
    note.append("end note")
    return note


def strip_existing_file_note(lines: list[str]) -> list[str]:
    trimmed = [line for line in lines if line.strip() not in PUML_COMMENT_LINES]
    start = None
    end = None
    for index in range(len(trimmed) - 1):
        if trimmed[index].strip() == "note bottom" and index + 1 < len(trimmed) and trimmed[index + 1].strip() == "Files referenced":
            start = index
            for cursor in range(index + 2, len(trimmed)):
                if trimmed[cursor].strip() == "end note":
                    end = cursor
                    break
            break
    if start is not None and end is not None:
        return trimmed[:start] + trimmed[end + 1 :]
    return trimmed


def annotate_diagram(path: Path) -> bool:
    original = read_text(path)
    lines = strip_existing_file_note(original.splitlines())

    enriched: list[str] = []
    for index, line in enumerate(lines):
        if COMPONENT_RE.match(line):
            comment = component_comment(line)
            previous = lines[index - 1].strip() if index > 0 else ""
            if comment and previous != comment:
                enriched.append(comment)
        enriched.append(line)

    enduml_index = next((i for i, line in enumerate(enriched) if line.strip() == "@enduml"), len(enriched))
    file_note = note_lines(path, enriched)
    updated_lines = enriched[:enduml_index] + [""] + file_note + [""] + enriched[enduml_index:]
    updated = "\n".join(updated_lines).rstrip() + "\n"
    if updated != original:
        write_text(path, updated)
        return True
    return False


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Annotate repository source files with contextual comments.")
    parser.add_argument("--backend-only", action="store_true", help="Only annotate backend Python files.")
    parser.add_argument("--paths", nargs="+", help="Optional file or directory paths to limit the annotation scope.")
    parser.add_argument("--skip-diagrams", action="store_true", help="Skip PlantUML diagram annotation.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    selected_paths = resolve_cli_paths(args.paths)

    changed = 0
    if not args.skip_diagrams:
        for path in iter_diagram_files(selected_paths):
            changed += int(annotate_diagram(path))
    for path in iter_source_files(selected_paths, backend_only=args.backend_only):
        changed += int(annotate_source_file(path))
    print(f"Annotated files: {changed}")


if __name__ == "__main__":
    main()
