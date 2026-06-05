from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from PIL import Image, ImageDraw, ImageFont


BASE_DIR = Path(__file__).resolve().parents[1]
OUT_DIR = BASE_DIR / "slide_assets" / "diagrams"

WIDTH = 2560
HEIGHT = 1440

BG = "#F7F9FC"
TITLE = "#0F172A"
TEXT = "#334155"
MUTED = "#64748B"
GRID = "#D7E0EA"
SHADOW = "#CBD5E14D"

FONT_REGULAR = r"C:\Windows\Fonts\segoeui.ttf"
FONT_BOLD = r"C:\Windows\Fonts\segoeuib.ttf"

PALETTES = {
    "orange": ("#FFF4E5", "#F59E0B"),
    "blue": ("#EAF3FF", "#2563EB"),
    "green": ("#ECFDF3", "#16A34A"),
    "teal": ("#E6FFFB", "#0F766E"),
    "purple": ("#F4ECFF", "#9333EA"),
    "pink": ("#FCE7F3", "#DB2777"),
    "yellow": ("#FFFBE6", "#CA8A04"),
    "cyan": ("#ECFEFF", "#0891B2"),
    "slate": ("#FFFFFF", "#94A3B8"),
}


def get_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(FONT_BOLD if bold else FONT_REGULAR, size=size)


TITLE_FONT = get_font(44, bold=True)
SUBTITLE_FONT = get_font(21)
SECTION_FONT = get_font(22, bold=True)
BOX_TITLE_FONT = get_font(26, bold=True)
LABEL_FONT = get_font(18, bold=True)


@dataclass
class Box:
    x: int
    y: int
    w: int
    h: int
    title: str
    bullets: list[str]
    palette: str


def new_canvas() -> tuple[Image.Image, ImageDraw.ImageDraw]:
    image = Image.new("RGBA", (WIDTH, HEIGHT), BG)
    draw = ImageDraw.Draw(image)
    return image, draw


def text_wh(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont) -> tuple[int, int]:
    left, top, right, bottom = draw.textbbox((0, 0), text, font=font)
    return right - left, bottom - top


def wrap_text(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont, max_width: int) -> list[str]:
    words = text.split()
    if not words:
        return [""]
    lines: list[str] = []
    current = words[0]
    for word in words[1:]:
        candidate = f"{current} {word}"
        if draw.textlength(candidate, font=font) <= max_width:
            current = candidate
        else:
            lines.append(current)
            current = word
    lines.append(current)
    return lines


def wrap_paragraphs(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont, max_width: int) -> list[str]:
    lines: list[str] = []
    for para in text.split("\n"):
        if not para.strip():
            lines.append("")
        else:
            lines.extend(wrap_text(draw, para, font, max_width))
    return lines


def fit_bullets(
    draw: ImageDraw.ImageDraw,
    bullets: Iterable[str],
    max_width: int,
    max_height: int,
    start_size: int = 21,
    min_size: int = 15,
) -> tuple[ImageFont.FreeTypeFont, list[list[str]], int]:
    items = list(bullets)
    for size in range(start_size, min_size - 1, -1):
        font = get_font(size)
        line_height = text_wh(draw, "Ag", font)[1] + 4
        gap = 8 if size >= 19 else 6
        wrapped_items: list[list[str]] = []
        total_h = 0
        for item in items:
            lines = wrap_paragraphs(draw, item, font, max_width - 26)
            wrapped_items.append(lines)
            total_h += len(lines) * line_height + gap
        if total_h <= max_height:
            return font, wrapped_items, line_height
    font = get_font(min_size)
    line_height = text_wh(draw, "Ag", font)[1] + 3
    wrapped_items = [wrap_paragraphs(draw, item, font, max_width - 26) for item in items]
    return font, wrapped_items, line_height


def draw_header(draw: ImageDraw.ImageDraw, title: str, subtitle: str) -> None:
    draw.text((70, 48), title, font=TITLE_FONT, fill=TITLE)
    draw.text((70, 108), subtitle, font=SUBTITLE_FONT, fill=MUTED)
    draw.rounded_rectangle((70, 150, WIDTH - 70, 154), radius=3, fill=GRID)


def draw_shadow_box(draw: ImageDraw.ImageDraw, rect: tuple[int, int, int, int], radius: int, fill: str, outline: str, width: int = 3) -> None:
    x1, y1, x2, y2 = rect
    draw.rounded_rectangle((x1 + 7, y1 + 9, x2 + 7, y2 + 9), radius=radius, fill=SHADOW)
    draw.rounded_rectangle(rect, radius=radius, fill=fill, outline=outline, width=width)


def draw_panel(draw: ImageDraw.ImageDraw, x: int, y: int, w: int, h: int, title: str, palette: str) -> None:
    fill, border = PALETTES[palette]
    draw_shadow_box(draw, (x, y, x + w, y + h), 30, fill, border)
    draw.rounded_rectangle((x + 16, y + 14, x + w - 16, y + 64), radius=18, fill=border)
    draw.text((x + 28, y + 24), title, font=SECTION_FONT, fill="white")


def draw_content_box(draw: ImageDraw.ImageDraw, box: Box) -> None:
    fill, border = PALETTES[box.palette]
    draw_shadow_box(draw, (box.x, box.y, box.x + box.w, box.y + box.h), 24, "#FFFFFF", border)
    draw.rounded_rectangle((box.x + 14, box.y + 12, box.x + box.w - 14, box.y + 56), radius=16, fill=fill)
    title_lines = wrap_paragraphs(draw, box.title, BOX_TITLE_FONT, box.w - 34)
    title_y = box.y + 18
    for line in title_lines:
        draw.text((box.x + 22, title_y), line, font=BOX_TITLE_FONT, fill=TITLE)
        title_y += text_wh(draw, line, BOX_TITLE_FONT)[1] + 2
    separator_y = box.y + 68
    draw.line((box.x + 18, separator_y, box.x + box.w - 18, separator_y), fill=border, width=2)

    body_top = box.y + 82
    body_height = box.h - 98
    body_width = box.w - 34
    font, wrapped_items, line_height = fit_bullets(draw, box.bullets, body_width, body_height)

    current_y = body_top
    for lines in wrapped_items:
        bullet_x = box.x + 24
        draw.ellipse((bullet_x, current_y + 8, bullet_x + 8, current_y + 16), fill=border)
        text_x = bullet_x + 18
        for line in lines:
            draw.text((text_x, current_y), line, font=font, fill=TEXT)
            current_y += line_height
        current_y += 6


def draw_arrow(
    draw: ImageDraw.ImageDraw,
    start: tuple[int, int],
    end: tuple[int, int],
    color: str = "#64748B",
    width: int = 6,
    label: str | None = None,
) -> None:
    x1, y1 = start
    x2, y2 = end
    draw.line((x1, y1, x2, y2), fill=color, width=width)
    if x1 == x2:
        head = [(x2, y2), (x2 - 12, y2 - 18), (x2 + 12, y2 - 18)] if y2 > y1 else [(x2, y2), (x2 - 12, y2 + 18), (x2 + 12, y2 + 18)]
    else:
        head = [(x2, y2), (x2 - 18, y2 - 12), (x2 - 18, y2 + 12)] if x2 > x1 else [(x2, y2), (x2 + 18, y2 - 12), (x2 + 18, y2 + 12)]
    draw.polygon(head, fill=color)
    if label:
        mx = (x1 + x2) // 2
        my = (y1 + y2) // 2
        tw, th = text_wh(draw, label, LABEL_FONT)
        draw.rounded_rectangle((mx - tw // 2 - 10, my - th // 2 - 6, mx + tw // 2 + 10, my + th // 2 + 6), radius=14, fill="#FFFFFF", outline=color, width=2)
        draw.text((mx - tw // 2, my - th // 2), label, font=LABEL_FONT, fill=TITLE)


def draw_h_arrow_between_boxes(draw: ImageDraw.ImageDraw, left_box: Box, right_box: Box, label: str | None = None, color: str = "#64748B") -> None:
    start = (left_box.x + left_box.w, left_box.y + left_box.h // 2)
    end = (right_box.x, right_box.y + right_box.h // 2)
    draw_arrow(draw, start, end, color=color, label=label)


def draw_v_arrow_between_boxes(draw: ImageDraw.ImageDraw, top_box: Box, bottom_box: Box, label: str | None = None, color: str = "#64748B") -> None:
    start = (top_box.x + top_box.w // 2, top_box.y + top_box.h)
    end = (bottom_box.x + bottom_box.w // 2, bottom_box.y)
    draw_arrow(draw, start, end, color=color, label=label)


def save(image: Image.Image, name: str) -> Path:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUT_DIR / name
    image.save(path)
    return path


def diagram_01() -> Path:
    image, draw = new_canvas()
    draw_header(
        draw,
        "Sơ đồ 1. Kiến trúc tổng thể hệ thống",
        "Bố cục tối giản theo luồng chính: Người dùng -> Flutter Web -> Django -> PostgreSQL/PGVector, Ollama và lưu trữ tài liệu.",
    )

    draw_panel(draw, 80, 205, 420, 1140, "1. Tác nhân sử dụng", "orange")
    draw_panel(draw, 560, 205, 520, 1140, "2. Frontend Flutter Web", "blue")
    draw_panel(draw, 1140, 205, 640, 1140, "3. Backend Django + REST API", "green")
    draw_panel(draw, 1840, 205, 640, 1140, "4. Data, AI và storage", "yellow")

    actor_boxes = [
        Box(120, 300, 340, 180, "Người dùng nội bộ", ["Nhân viên, trưởng phòng, admin.", "Sử dụng dashboard, quản lý mẫu, quản lý văn bản, ký số và trợ lý AI."], "orange"),
        Box(120, 545, 340, 155, "Người dùng guest", ["Tạo văn bản khách, parse template hoặc parse PDF qua guest portal."], "orange"),
        Box(120, 765, 340, 200, "Trình duyệt web", ["Một điểm truy cập duy nhất.", "Người dùng chỉ cần mở hệ thống qua browser, không cần cài app riêng."], "orange"),
    ]
    for b in actor_boxes:
        draw_content_box(draw, b)

    frontend_boxes = [
        Box(600, 280, 440, 220, "App Shell + điều hướng", ["Flutter Web là giao diện chính của hệ thống.", "Quản lý router, shell điều hướng, menu chức năng và trạng thái người dùng."], "blue"),
        Box(600, 545, 440, 240, "Các nhóm màn hình chính", ["Auth và profile.", "Dashboard và admin.", "Templates, documents, mailbox.", "AI Doc, ChatAI, RAG, Signing, Guest portal."], "blue"),
        Box(600, 835, 440, 235, "Ưu điểm triển khai", ["Giao diện hiện đại, nhiều màn nghiệp vụ nhưng vẫn thống nhất.", "Khi Django phục vụ build/web, frontend dùng same-origin để gọi API nên giảm độ phức tạp CORS."], "blue"),
    ]
    for b in frontend_boxes:
        draw_content_box(draw, b)

    backend_boxes = [
        Box(1180, 270, 560, 220, "Django serve hệ thống", ["Phục vụ luôn Flutter build/web.", "Cung cấp REST API cho frontend.", "Có thể giữ một số trang HTML cũ để tương thích."], "green"),
        Box(1180, 535, 560, 270, "Các module nghiệp vụ chính", ["accounts: auth, profile, nhóm, phòng ban, phân quyền.", "document_templates: mẫu văn bản và version.", "documents: văn bản, mailbox, preview, archive.", "signing: ký số và xác minh PDF."], "green"),
        Box(1180, 855, 560, 250, "AI và vận hành", ["ai_engine: ChatAI, RAG, AI Doc, OCR flow, rebuild index.", "Management commands cho backup, purge trash, rebuild RAG index.", "Django là bộ điều phối trung tâm giữa UI, dữ liệu và AI runtime."], "green"),
    ]
    for b in backend_boxes:
        draw_content_box(draw, b)

    data_boxes = [
        Box(1880, 260, 560, 230, "PostgreSQL + PGVector", ["PostgreSQL lưu dữ liệu người dùng, mẫu, văn bản, chat, ký số.", "PGVector lưu embedding và phục vụ semantic retrieval cho template và document."], "yellow"),
        Box(1880, 545, 560, 210, "Ollama runtime", ["Chạy chat model, embedding model và có thể mở rộng model OCR/multimodal.", "Phù hợp triển khai cục bộ hoặc server nội bộ."], "yellow"),
        Box(1880, 810, 560, 250, "Media + backup + file tools", ["Media lưu DOCX, PDF, preview, signed PDF và audio.", "Backup lưu các file JSON khôi phục.", "LibreOffice và Tesseract hỗ trợ preview PDF, parse và OCR."], "yellow"),
    ]
    for b in data_boxes:
        draw_content_box(draw, b)

    draw_h_arrow_between_boxes(draw, actor_boxes[2], frontend_boxes[0], label="truy cập")
    draw_h_arrow_between_boxes(draw, frontend_boxes[1], backend_boxes[1], label="/api/")
    draw_h_arrow_between_boxes(draw, backend_boxes[0], data_boxes[0], label="dữ liệu")
    draw_h_arrow_between_boxes(draw, backend_boxes[1], data_boxes[1], label="AI")
    draw_h_arrow_between_boxes(draw, backend_boxes[2], data_boxes[2], label="file / backup")

    draw_content_box(
        draw,
        Box(
            600,
            1125,
            1840,
            165,
            "Điểm nổi bật của kiến trúc",
            [
                "Một điểm truy cập web duy nhất nhưng vẫn gom đủ frontend, backend, dữ liệu, AI và storage.",
                "Kiến trúc phù hợp cho môi trường doanh nghiệp vì dễ triển khai nội bộ, dễ kiểm soát dữ liệu và không cần quá nhiều service tách rời ngay từ đầu."
            ],
            "slate",
        ),
    )

    return save(image, "v2_01_kien_truc_tong_the.png")


def diagram_02() -> Path:
    image, draw = new_canvas()
    draw_header(
        draw,
        "Sơ đồ 2. Quy trình setup môi trường",
        "Setup được chia thành 3 lane rõ ràng: Backend, Frontend và AI runtime. Mỗi lane đi theo chiều dọc rồi hội tụ ở bước smoke test cuối cùng.",
    )

    draw_panel(draw, 90, 210, 700, 860, "Lane A - Backend Django + PostgreSQL", "green")
    draw_panel(draw, 930, 210, 700, 860, "Lane B - Frontend Flutter Web", "blue")
    draw_panel(draw, 1770, 210, 700, 860, "Lane C - Ollama + file tools", "yellow")

    left = [
        Box(130, 295, 620, 145, "1. Chuẩn bị backend", ["Cài Python 3.10+ và pip.", "Tạo môi trường chạy Django."], "green"),
        Box(130, 475, 620, 155, "2. Tạo database", ["Cài PostgreSQL.", "Tạo `tennis_club_db` và bật extension `vector`."], "green"),
        Box(130, 665, 620, 165, "3. Cài package và cấu hình", ["`pip install -r requirements.txt`.", "Tạo `.env` với SECRET_KEY, DB_* và OLLAMA_*."], "green"),
        Box(130, 865, 620, 145, "4. Khởi tạo Django", ["`python manage.py migrate`.", "`python manage.py createsuperuser`."], "green"),
    ]
    mid = [
        Box(970, 295, 620, 145, "1. Chuẩn bị Flutter", ["Cài Flutter SDK.", "Kiểm tra `flutter doctor`."], "blue"),
        Box(970, 475, 620, 155, "2. Cài package frontend", ["`flutter pub get`.", "Kiểm tra routing, API client và state management."], "blue"),
        Box(970, 665, 620, 165, "3. Build giao diện web", ["`flutter build web`.", "Sinh ra `flutter_frontend/build/web` cho Django phục vụ."], "blue"),
        Box(970, 865, 620, 145, "4. Ghép với backend", ["Frontend web gọi cùng domain theo `/api/*`."], "blue"),
    ]
    right = [
        Box(1810, 295, 620, 145, "1. Cài Ollama", ["Khởi động runtime AI local hoặc trên máy chủ riêng."], "yellow"),
        Box(1810, 475, 620, 155, "2. Tải model cần dùng", ["`ollama pull llama3:8b`.", "`ollama pull mxbai-embed-large`.", "Nếu cần OCR: `qwen3-vl:4b`."], "yellow"),
        Box(1810, 665, 620, 165, "3. Cài công cụ xử lý file", ["Cài LibreOffice cho preview PDF.", "Cài Tesseract OCR cho PDF scan hoặc ảnh."], "yellow"),
        Box(1810, 865, 620, 145, "4. Đồng bộ chỉ mục RAG", ["`python manage.py rebuild_rag_index --scope all`."], "yellow"),
    ]
    for group in (left, mid, right):
        for box in group:
            draw_content_box(draw, box)
        for top, bottom in zip(group, group[1:]):
            draw_v_arrow_between_boxes(draw, top, bottom)

    final_box = Box(
        410,
        1115,
        1740,
        220,
        "5. Chạy thử và smoke test toàn hệ thống",
        [
            "`python manage.py runserver`.",
            "Kiểm tra đăng nhập, dashboard, tạo mẫu, sinh văn bản, hỏi đáp RAG, ký số và backup.",
            "Khi cả 3 lane hoàn tất, hệ thống sẵn sàng để demo hoặc deploy."
        ],
        "purple",
    )
    draw_content_box(draw, final_box)

    draw_arrow(draw, (440, 1010), (760, 1115), color="#16A34A", label="backend")
    draw_arrow(draw, (1280, 1010), (1280, 1115), color="#2563EB", label="frontend")
    draw_arrow(draw, (2120, 1010), (1800, 1115), color="#CA8A04", label="AI")

    return save(image, "v2_02_quy_trinh_setup.png")


def diagram_03() -> Path:
    image, draw = new_canvas()
    draw_header(
        draw,
        "Sơ đồ 3. Kiến trúc deploy production",
        "Triển khai production theo trục dọc rõ ràng: User -> Nginx -> Django. Từ Django mới tách ra dữ liệu, AI, media và backup.",
    )

    draw_panel(draw, 110, 210, 2340, 205, "Tầng 1 - Truy cập", "orange")
    draw_panel(draw, 110, 430, 2340, 330, "Tầng 2 - Ứng dụng", "green")
    draw_panel(draw, 110, 800, 2340, 520, "Tầng 3 - Dữ liệu và dịch vụ phụ trợ", "yellow")

    access_boxes = [
        Box(170, 286, 320, 112, "Người dùng", ["Nhân viên nội bộ, admin, guest."], "orange"),
        Box(565, 286, 360, 112, "Browser / domain", ["Một domain truy cập duy nhất."], "orange"),
        Box(1000, 274, 460, 126, "Nginx / reverse proxy", ["HTTPS termination.", "Route request và phục vụ static/media."], "orange"),
    ]
    for box in access_boxes:
        draw_content_box(draw, box)
    draw_h_arrow_between_boxes(draw, access_boxes[0], access_boxes[1], label="mở hệ thống")
    draw_h_arrow_between_boxes(draw, access_boxes[1], access_boxes[2], label="HTTPS")

    app_boxes = [
        Box(240, 500, 540, 190, "Flutter Web build", ["Giao diện chính người dùng nhìn thấy.", "Đặt tại `flutter_frontend/build/web`."], "blue"),
        Box(1010, 475, 540, 240, "Django application", ["Phục vụ Flutter Web build, REST API và JWT refresh.", "Chứa accounts, documents, templates, ai_engine, signing và admin."], "green"),
        Box(1780, 500, 420, 190, "REST API + admin ops", ["Frontend gọi API cùng domain.", "Xử lý backup, restore, purge trash và rebuild index."], "teal"),
    ]
    for box in app_boxes:
        draw_content_box(draw, box)
    draw_h_arrow_between_boxes(draw, app_boxes[0], app_boxes[1], label="serve")
    draw_h_arrow_between_boxes(draw, app_boxes[1], app_boxes[2], label="/api/*")
    draw_arrow(draw, (1230, 400), (1230, 475), color="#16A34A")

    data_boxes = [
        Box(170, 910, 500, 210, "PostgreSQL + PGVector", ["PostgreSQL lưu dữ liệu nghiệp vụ.", "PGVector lưu embedding cho RAG."], "yellow"),
        Box(700, 910, 500, 210, "Ollama server", ["Chạy chat model và embedding model.", "Có thể tách riêng khi tải AI tăng."], "yellow"),
        Box(1230, 910, 500, 210, "Media storage", ["Lưu DOCX, PDF, preview, signed PDF, audio và file tạm."], "yellow"),
        Box(1760, 910, 500, 210, "Backup storage", ["Lưu backup JSON và dữ liệu khôi phục khi có sự cố."], "yellow"),
    ]
    for box in data_boxes:
        draw_content_box(draw, box)

    draw_arrow(draw, (1280, 715), (420, 910), color="#16A34A", label="DB")
    draw_arrow(draw, (1280, 715), (950, 910), color="#16A34A", label="AI")
    draw_arrow(draw, (1280, 715), (1480, 910), color="#16A34A", label="file")
    draw_arrow(draw, (1280, 715), (2010, 910), color="#16A34A", label="backup")

    draw_shadow_box(draw, (420, 1160, 2140, 1288), 20, "#FFFFFF", "#94A3B8", width=2)
    draw.text((455, 1195), "Điểm mạnh của mô hình triển khai", font=get_font(24, True), fill=TITLE)
    draw.line((455, 1230, 2105, 1230), fill="#94A3B8", width=2)
    footer_lines = wrap_paragraphs(
        draw,
        "Một domain, một app backend trung tâm và các dịch vụ phụ trợ rõ vai trò; phù hợp cho môi trường doanh nghiệp cần triển khai nội bộ và dễ kiểm soát dữ liệu.",
        get_font(21),
        1610,
    )
    y = 1240
    for line in footer_lines:
        draw.text((455, y), line, font=get_font(21), fill=TEXT)
        y += 26

    return save(image, "v2_03_kien_truc_deploy_production.png")


def diagram_04() -> Path:
    image, draw = new_canvas()
    draw_header(
        draw,
        "Sơ đồ 4. Vận hành, backup và recovery",
        "Mỗi pha được tách rõ ràng: Runtime hằng ngày, job bảo trì định kỳ và quy trình recovery khi có sự cố. Không dùng mũi tên chéo giữa nhiều lớp.",
    )

    draw_panel(draw, 80, 215, 1830, 310, "Pha 1 - Runtime hằng ngày", "blue")
    draw_panel(draw, 80, 575, 1830, 300, "Pha 2 - Bảo trì định kỳ", "pink")
    draw_panel(draw, 80, 925, 1830, 300, "Pha 3 - Recovery khi có sự cố", "purple")
    draw_panel(draw, 1960, 215, 500, 1010, "Monitoring", "cyan")

    runtime = [
        Box(120, 290, 380, 165, "1. User request", ["Người dùng tạo, sửa, tra cứu văn bản hoặc dùng AI."], "blue"),
        Box(560, 290, 380, 165, "2. Auth + permission", ["Backend xác thực JWT hoặc session và kiểm tra quyền truy cập."], "blue"),
        Box(1000, 290, 380, 165, "3. Xử lý nghiệp vụ", ["documents, templates, ai_engine và signing xử lý logic tương ứng."], "blue"),
        Box(1440, 290, 380, 165, "4. Lưu và trả kết quả", ["Lưu DB, media, preview, signed PDF hoặc chat history rồi trả response cho frontend."], "blue"),
    ]
    for box in runtime:
        draw_content_box(draw, box)
    for left, right in zip(runtime, runtime[1:]):
        draw_h_arrow_between_boxes(draw, left, right)

    maintenance = [
        Box(120, 645, 380, 155, "1. Backup định kỳ", ["Backup full hoặc backup theo module để đảm bảo khả năng khôi phục."], "pink"),
        Box(560, 645, 380, 155, "2. Purge trash", ["Dọn dữ liệu soft-delete đã hết hạn bằng management command."], "pink"),
        Box(1000, 645, 380, 155, "3. Rebuild RAG index", ["Reindex khi import dữ liệu lớn hoặc khi cần đồng bộ semantic search."], "pink"),
        Box(1440, 645, 380, 155, "4. Health check", ["Theo dõi DB, Ollama, dung lượng media và timeout AI."], "pink"),
    ]
    for box in maintenance:
        draw_content_box(draw, box)
    for left, right in zip(maintenance, maintenance[1:]):
        draw_h_arrow_between_boxes(draw, left, right)

    recovery = [
        Box(120, 995, 380, 170, "1. Incident", ["Phát hiện mất dữ liệu, lỗi index, lỗi AI hoặc lỗi ký số."], "purple"),
        Box(560, 995, 380, 170, "2. Restore", ["Khôi phục database và media từ backup."], "purple"),
        Box(1000, 995, 380, 170, "3. Reindex", ["Rebuild lại PGVector để semantic retrieval khớp dữ liệu đã restore."], "purple"),
        Box(1440, 995, 380, 170, "4. Smoke test và ổn định", ["Kiểm tra login, document, chat, backup, signing và đưa hệ thống trở lại trạng thái ổn định."], "purple"),
    ]
    for box in recovery:
        draw_content_box(draw, box)
    for left, right in zip(recovery, recovery[1:]):
        draw_h_arrow_between_boxes(draw, left, right)

    monitoring_boxes = [
        Box(2000, 290, 420, 200, "Logs", ["Ghi log cho ai_engine, preview PDF, signing và các tác vụ vận hành."], "cyan"),
        Box(2000, 545, 420, 200, "Metrics", ["Theo dõi thời gian phản hồi, trạng thái DB, trạng thái Ollama và tài nguyên lưu trữ."], "cyan"),
        Box(2000, 800, 420, 200, "Alerts + runbook", ["Khi có lỗi, hệ thống cần cảnh báo và có quy trình restore, reindex và smoke test rõ ràng."], "cyan"),
    ]
    for box in monitoring_boxes:
        draw_content_box(draw, box)
    for top, bottom in zip(monitoring_boxes, monitoring_boxes[1:]):
        draw_v_arrow_between_boxes(draw, top, bottom)

    draw_arrow(draw, (1820, 372), (2000, 372), color="#0891B2", label="log")
    draw_arrow(draw, (1820, 722), (2000, 645), color="#0891B2", label="metrics")
    draw_arrow(draw, (1190, 800), (1190, 995), color="#7C3AED", label="sự cố")

    return save(image, "v2_04_van_hanh_backup_recovery.png")


def contact_sheet(paths: list[Path]) -> Path:
    image, draw = new_canvas()
    draw_header(
        draw,
        "Bộ sơ đồ phiên bản đơn giản hóa",
        "Preview gồm 4 ảnh PNG mới với bố cục rõ ràng hơn, ít mũi tên hơn và ưu tiên nội dung nằm gọn trong các box.",
    )

    slots = [
        (80, 210, 1160, 520, "01. Kiến trúc tổng thể"),
        (1320, 210, 1160, 520, "02. Quy trình setup"),
        (80, 790, 1160, 520, "03. Deploy production"),
        (1320, 790, 1160, 520, "04. Vận hành / recovery"),
    ]
    for path, (x, y, w, h, label) in zip(paths, slots, strict=True):
        thumb = Image.open(path).convert("RGBA")
        thumb.thumbnail((w - 30, h - 70))
        draw_shadow_box(draw, (x, y, x + w, y + h), 24, "#FFFFFF", "#CBD5E1", width=2)
        image.alpha_composite(thumb, (x + (w - thumb.width) // 2, y + 18))
        draw.text((x + 20, y + h - 42), label, font=SECTION_FONT, fill=TITLE)
    return save(image, "v2_00_preview_tong_hop.png")


def main() -> None:
    paths = [diagram_01(), diagram_02(), diagram_03(), diagram_04()]
    contact_sheet(paths)
    for path in paths:
        print(path)


if __name__ == "__main__":
    main()
