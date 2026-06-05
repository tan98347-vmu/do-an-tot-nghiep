from __future__ import annotations

from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from tools.render_slide_diagrams import (
    Box,
    SECTION_FONT,
    TITLE,
    TEXT,
    draw_arrow,
    draw_content_box,
    draw_header,
    draw_panel,
    draw_shadow_box,
    get_font,
    new_canvas,
    save,
    text_wh,
    wrap_paragraphs,
)


OUTPUT_NAME = "v2_06_luong_ket_noi_hang_ngang.png"


def draw_footer(draw, title: str, text: str) -> None:
    rect = (120, 1280, 2440, 1388)
    draw_shadow_box(draw, rect, 22, "#FFFFFF", "#94A3B8", width=2)
    draw.text((155, 1306), title, font=SECTION_FONT, fill=TITLE)
    draw.line((155, 1340, 2405, 1340), fill="#94A3B8", width=2)
    font = get_font(20)
    y = 1350
    for line in wrap_paragraphs(draw, text, font, 2200):
        draw.text((155, y), line, font=font, fill=TEXT)
        y += text_wh(draw, line, font)[1] + 2


def build_diagram() -> Path:
    image, draw = new_canvas()
    draw_header(
        draw,
        "Sơ đồ 6. Luồng kết nối hàng ngang từ user vào hệ thống",
        "Đọc từ trái sang phải để thấy request đi qua các lớp nào, rồi từ phải sang trái để thấy response quay lại giao diện người dùng.",
    )

    draw_panel(draw, 80, 215, 2400, 430, "Hàng 1 - Request đi vào hệ thống", "orange")
    draw_panel(draw, 80, 690, 2400, 430, "Hàng 2 - Response quay về người dùng", "blue")

    request_boxes = [
        Box(
            110, 310, 235, 190,
            "1. User mở web",
            [
                "Người dùng mở domain hoặc http://127.0.0.1:8080.",
                "Truy cập bằng browser, không đi thẳng vào Django :8000.",
            ],
            "orange",
        ),
        Box(
            390, 310, 210, 190,
            "2. ngrok",
            [
                "Chỉ xuất hiện nếu cần public ra Internet.",
                "Tunnel request về cổng Nginx 8080.",
            ],
            "orange",
        ),
        Box(
            645, 285, 305, 240,
            "3. Nginx public",
            [
                "Là cửa vào web thật của hệ thống.",
                "Nhận mọi request từ browser.",
                "Quyết định serve Flutter hay proxy API/admin.",
            ],
            "orange",
        ),
        Box(
            995, 285, 305, 240,
            "4. Flutter static shell",
            [
                "Nginx trả index.html từ flutter_frontend/build/web.",
                "Các asset JS/CSS của Flutter được tải về browser.",
            ],
            "blue",
        ),
        Box(
            1345, 285, 305, 240,
            "5. Router + screen",
            [
                "main.dart khởi động app.",
                "router.dart map /dashboard, /documents, /chat...",
                "AppShell/GuestShell dựng layout phù hợp.",
            ],
            "blue",
        ),
        Box(
            1695, 285, 305, 240,
            "6. ApiClient gọi /api/*",
            [
                "api_client.dart dùng same-origin /api/ trên web.",
                "Gửi JWT, refresh token, request nghiệp vụ.",
            ],
            "teal",
        ),
        Box(
            2045, 285, 395, 240,
            "7. Nginx proxy -> Waitress -> Django",
            [
                "Nginx proxy /api/, /api/auth/refresh/, /django-admin/ sang 127.0.0.1:8000.",
                "my_tennis_club/urls.py nhận request rồi chuyển vào api/urls.py hoặc admin.",
            ],
            "green",
        ),
    ]

    for box in request_boxes:
        draw_content_box(draw, box)

    for left, right, label in zip(
        request_boxes[:-1],
        request_boxes[1:],
        ["mở web", "tunnel", "serve", "boot", "route", "/api/*"],
        strict=True,
    ):
        start = (left.x + left.w, left.y + left.h // 2)
        end = (right.x, right.y + right.h // 2)
        draw_arrow(draw, start, end, color="#64748B", label=label)

    response_boxes = [
        Box(
            2045, 760, 395, 250,
            "8. Domain apps xử lý",
            [
                "api/views + api/serializers điều phối request.",
                "accounts, documents, document_templates, ai_engine, signing, prompts giữ logic thật.",
                "Khi cần sẽ gọi PostgreSQL, PGVector, Ollama, media/staticfiles.",
            ],
            "green",
        ),
        Box(
            1600, 760, 400, 250,
            "9. Django trả kết quả",
            [
                "Trả JSON cho Flutter API.",
                "Hoặc trả admin HTML/CSS qua /django-admin/.",
                "Hoặc sinh file download/preview/media.",
            ],
            "green",
        ),
        Box(
            1175, 760, 380, 250,
            "10. Nginx trả về browser",
            [
                "Forward JSON/API response.",
                "Hoặc phục vụ trực tiếp /media/ và /static/.",
            ],
            "teal",
        ),
        Box(
            770, 760, 360, 250,
            "11. Flutter cập nhật UI",
            [
                "providers/models parse dữ liệu backend.",
                "Screen rebuild và hiển thị trạng thái mới.",
            ],
            "blue",
        ),
        Box(
            365, 760, 360, 250,
            "12. Người dùng thấy kết quả",
            [
                "Dashboard, document list, AI result, signing status...",
                "F5 ở route sâu vẫn vào lại được vì Nginx luôn trả index.html.",
            ],
            "orange",
        ),
    ]

    for box in response_boxes:
        draw_content_box(draw, box)

    for right, left, label in zip(
        response_boxes[:-1],
        response_boxes[1:],
        ["JSON / file", "proxy back", "state update", "render"],
        strict=True,
    ):
        start = (right.x, right.y + right.h // 2)
        end = (left.x + left.w, left.y + left.h // 2)
        draw_arrow(draw, start, end, color="#2563EB", label=label)

    draw_arrow(draw, (2240, 525), (2240, 760), color="#16A34A", label="xử lý")
    draw_arrow(draw, (520, 760), (520, 525), color="#2563EB", label="màn hình")

    draw_footer(
        draw,
        "Ý nghĩa chính của sơ đồ",
        "Request web luôn đi vào Nginx trước. Nếu là route UI thì Nginx trả Flutter shell và Flutter tự điều hướng nội bộ; nếu là /api/* hoặc /django-admin/* thì Nginx mới proxy sang Waitress/Django. Kết quả xử lý từ backend lại quay về browser để Flutter cập nhật màn hình cho người dùng.",
    )

    return save(image, OUTPUT_NAME)


def main() -> None:
    path = build_diagram()
    print(path)


if __name__ == "__main__":
    main()
