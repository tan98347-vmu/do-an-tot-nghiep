from __future__ import annotations

from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from tools.render_slide_diagrams import (
    BOX_TITLE_FONT,
    SECTION_FONT,
    SUBTITLE_FONT,
    TITLE,
    TEXT,
    Box,
    draw_arrow,
    draw_content_box,
    draw_h_arrow_between_boxes,
    draw_header,
    draw_panel,
    draw_shadow_box,
    get_font,
    new_canvas,
    save,
    text_wh,
    wrap_paragraphs,
)


OUTPUT_NAME = "v2_05_cau_truc_chuong_trinh_chi_tiet.png"


def draw_footer(draw, text: str) -> None:
    rect = (180, 1310, 2380, 1388)
    draw_shadow_box(draw, rect, 20, "#FFFFFF", "#94A3B8", width=2)
    draw.text((215, 1332), "Luồng request điển hình", font=SECTION_FONT, fill=TITLE)
    draw.line((215, 1364, 2345, 1364), fill="#94A3B8", width=2)
    body_font = get_font(20)
    y = 1372
    for line in wrap_paragraphs(draw, text, body_font, 2080):
        draw.text((215, y), line, font=body_font, fill=TEXT)
        y += text_wh(draw, line, body_font)[1] + 2


def build_diagram() -> Path:
    image, draw = new_canvas()
    draw_header(
        draw,
        "Sơ đồ 5. Cấu trúc chương trình chi tiết",
        "Kiến trúc runtime hiện tại sau khi tách Nginx public, Flutter Web frontend và Django/Waitress backend. Mỗi tầng ghi rõ source of truth và đường đi request thật.",
    )

    draw_panel(draw, 80, 210, 2400, 210, "Tầng 1 - Edge và public entry", "orange")
    draw_panel(draw, 80, 450, 1180, 820, "Tầng 2 - Frontend Flutter Web", "blue")
    draw_panel(draw, 1300, 450, 1180, 560, "Tầng 3 - Django API + Waitress", "green")
    draw_panel(draw, 1300, 1040, 1180, 230, "Tầng 4 - Data và runtime services", "yellow")

    edge_user = Box(
        120,
        268,
        300,
        120,
        "Người dùng + browser",
        [
            "Mở http://127.0.0.1:8080 hoặc domain ngrok.",
            "Chỉ đi qua Nginx, không dùng trực tiếp :8000.",
        ],
        "orange",
    )
    edge_ngrok = Box(
        465,
        268,
        270,
        120,
        "ngrok (tuỳ chọn)",
        [
            "Publish cổng 8080 ra Internet.",
            "Không publish Django trực tiếp.",
        ],
        "orange",
    )
    edge_nginx = Box(
        780,
        245,
        520,
        160,
        "Nginx public web server",
        [
            "Serve / từ flutter_frontend/build/web.",
            "Proxy /api/, /api/auth/refresh/, /django-admin/.",
            "Serve /media/ và /static/ trực tiếp.",
        ],
        "orange",
    )
    edge_routes = Box(
        1340,
        245,
        1090,
        160,
        "Bảng định tuyến thực tế ở public edge",
        [
            "Route UI như /dashboard, /documents/1, /chat... -> index.html -> Flutter Router.",
            "/api/* và /api/auth/refresh/ -> Waitress :8000 -> Django API.",
            "/django-admin/* -> Django admin; /media/* -> media/; /static/* -> staticfiles/.",
        ],
        "teal",
    )
    for box in (edge_user, edge_ngrok, edge_nginx, edge_routes):
        draw_content_box(draw, box)
    draw_h_arrow_between_boxes(draw, edge_user, edge_ngrok, label="web")
    draw_h_arrow_between_boxes(draw, edge_ngrok, edge_nginx, label="tunnel")
    draw_h_arrow_between_boxes(draw, edge_nginx, edge_routes, label="route")

    frontend_core = Box(
        120,
        520,
        500,
        185,
        "Frontend entry + core",
        [
            "web/index.html và build/web là shell tĩnh do Nginx phục vụ.",
            "lib/main.dart khởi động app.",
            "lib/core/router.dart quyết định route sống.",
            "widgets/shell/app_shell.dart và guest_shell.dart bọc layout.",
        ],
        "blue",
    )
    frontend_state = Box(
        650,
        520,
        560,
        185,
        "Client state + API contract",
        [
            "lib/core/api_client.dart dùng same-origin /api/ trên web.",
            "providers/* quản lý auth, dashboard, templates, documents, signing...",
            "models/* chuẩn hoá JSON backend thành dữ liệu Flutter.",
        ],
        "blue",
    )
    frontend_screens = Box(
        120,
        740,
        1090,
        240,
        "Nhóm màn hình đang sống trong router Flutter",
        [
            "Auth: login, register; guest shell: guest, guest/document.",
            "Nghiệp vụ: dashboard, templates, documents, mailbox, pending approvals.",
            "AI: AI Doc, assistant chat/voice/audio, RAG history, rag-result.",
            "Ký số + quản trị: signing inbox/task/detail, signed PDFs, delegation, admin, AI config, backup, profile, trash.",
        ],
        "blue",
    )
    frontend_boundary = Box(
        120,
        1020,
        1090,
        170,
        "Boundary frontend cần giữ",
        [
            "Source of truth UI: flutter_frontend/lib/core/router.dart.",
            "User-facing screens ở Flutter; không quay lại Django HTML flow.",
            "Deep link được Nginx trả index.html rồi Flutter tự route nội bộ.",
        ],
        "purple",
    )
    for box in (frontend_core, frontend_state, frontend_screens, frontend_boundary):
        draw_content_box(draw, box)
    draw_h_arrow_between_boxes(draw, frontend_core, frontend_state, label="router + state")
    draw_arrow(draw, (370, 705), (370, 740), color="#2563EB")
    draw_arrow(draw, (930, 705), (930, 740), color="#2563EB")
    draw_arrow(draw, (665, 980), (665, 1020), color="#9333EA")

    backend_root = Box(
        1340,
        520,
        420,
        165,
        "Django edge routes",
        [
            "my_tennis_club/urls.py chỉ còn 3 nhánh sống.",
            "django-admin/, api/, api/auth/refresh/.",
            "Django không còn serve / hay catch-all Flutter.",
        ],
        "green",
    )
    backend_api = Box(
        1790,
        520,
        620,
        215,
        "api/urls.py là source of truth backend",
        [
            "Auth + profile + social login.",
            "Templates, documents, mailbox, trash.",
            "Signing, signed PDFs, delegations.",
            "Assistant, chat, RAG, AI doc, admin, dashboard, notifications, guest portal.",
        ],
        "green",
    )
    backend_layers = Box(
        1340,
        790,
        1070,
        170,
        "Lớp xử lý phía sau API",
        [
            "api/views/* điều phối request và response.",
            "api/serializers/* validate input/output.",
            "Domain apps giữ logic thật: accounts, documents, document_templates, ai_engine, signing, prompts.",
        ],
        "green",
    )
    for box in (backend_root, backend_api, backend_layers):
        draw_content_box(draw, box)
    draw_h_arrow_between_boxes(draw, backend_root, backend_api, label="/api/*")
    draw_arrow(draw, (1550, 685), (1550, 790), color="#16A34A")
    draw_arrow(draw, (2100, 735), (2100, 790), color="#16A34A")

    service_db = Box(
        1340,
        1095,
        255,
        140,
        "PostgreSQL + PGVector",
        [
            "Lưu user, template, document, signing.",
            "PGVector cho RAG và semantic search.",
        ],
        "yellow",
    )
    service_ai = Box(
        1625,
        1095,
        245,
        140,
        "Ollama + AI runtime",
        [
            "Chat, OCR, embeddings.",
            "ai_engine điều phối model usage.",
        ],
        "yellow",
    )
    service_files = Box(
        1900,
        1095,
        245,
        140,
        "Media + staticfiles",
        [
            "media/ lưu DOCX, PDF, audio, signed PDF.",
            "staticfiles/ phục vụ django-admin.",
        ],
        "yellow",
    )
    service_ops = Box(
        2175,
        1095,
        265,
        140,
        "Waitress + ops",
        [
            "Waitress nghe 127.0.0.1:8000 sau Nginx.",
            "collectstatic, purge_trash, clear_versions, rebuild_rag_index...",
        ],
        "yellow",
    )
    for box in (service_db, service_ai, service_files, service_ops):
        draw_content_box(draw, box)

    draw_arrow(draw, (1875, 960), (1465, 1095), color="#16A34A", label="DB")
    draw_arrow(draw, (1875, 960), (1740, 1095), color="#16A34A", label="AI")
    draw_arrow(draw, (1875, 960), (2015, 1095), color="#16A34A", label="file")
    draw_arrow(draw, (1875, 960), (2300, 1095), color="#16A34A", label="ops")
    draw_arrow(draw, (1040, 388), (1040, 520), color="#2563EB", label="index.html")
    draw_arrow(draw, (1710, 405), (1710, 520), color="#16A34A", label="proxy")

    draw_footer(
        draw,
        "1. User mở /dashboard trên Nginx -> 2. Nginx trả index.html từ build/web -> 3. Flutter Router dựng screen phù hợp -> 4. ApiClient gọi /api/... cùng origin -> 5. Nginx proxy sang Waitress :8000 -> 6. Django views/serializers/domain apps xử lý -> 7. DB, AI, media hoặc admin trả kết quả -> 8. Frontend nhận JSON và cập nhật UI.",
    )

    return save(image, OUTPUT_NAME)


def main() -> None:
    path = build_diagram()
    print(path)


if __name__ == "__main__":
    main()
