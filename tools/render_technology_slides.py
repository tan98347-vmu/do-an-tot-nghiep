from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from PIL import Image, ImageDraw, ImageFont


BASE_DIR = Path(__file__).resolve().parents[1]
OUT_DIR = BASE_DIR / "slide_assets" / "technology_slides"

WIDTH = 2560
HEIGHT = 1440

FONT_REGULAR = r"C:\Windows\Fonts\segoeui.ttf"
FONT_BOLD = r"C:\Windows\Fonts\segoeuib.ttf"


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(FONT_BOLD if bold else FONT_REGULAR, size=size)


TITLE_FONT = font(58, True)
SUBTITLE_FONT = font(26)
KICKER_FONT = font(22, True)
CARD_TITLE_FONT = font(30, True)
PILL_FONT = font(19, True)
TAKEAWAY_FONT = font(24)


TEXT = "#0F172A"
BODY = "#334155"
MUTED = "#64748B"
WHITE = "#FFFFFF"
SHADOW = "#A3B4C633"

THEMES = {
    "flutter": {"top": "#EAF4FF", "bottom": "#F9FBFF", "accent": "#2563EB", "accent2": "#0EA5E9", "soft": "#D7E8FF"},
    "django": {"top": "#ECFDF3", "bottom": "#FAFFFC", "accent": "#16A34A", "accent2": "#0F766E", "soft": "#D9F6E3"},
    "postgres": {"top": "#FFF8E8", "bottom": "#FFFCF6", "accent": "#CA8A04", "accent2": "#7C3AED", "soft": "#F9EAC1"},
    "ollama": {"top": "#FFF1F2", "bottom": "#FFF9F9", "accent": "#E11D48", "accent2": "#F97316", "soft": "#FFD9E0"},
    "compare": {"top": "#F4F6FA", "bottom": "#FCFDFE", "accent": "#0F172A", "accent2": "#2563EB", "soft": "#E4E9F1"},
    "deploy": {"top": "#ECFEFF", "bottom": "#F9FFFF", "accent": "#0891B2", "accent2": "#16A34A", "soft": "#CFF4F8"},
    "domain": {"top": "#EEF6FF", "bottom": "#FBFDFF", "accent": "#2563EB", "accent2": "#0F766E", "soft": "#DCEBFF"},
    "roadmap": {"top": "#F0FDFA", "bottom": "#FCFFFE", "accent": "#0F766E", "accent2": "#16A34A", "soft": "#D4F7EE"},
    "signing": {"top": "#F8FAFC", "bottom": "#FEFEFF", "accent": "#4338CA", "accent2": "#CA8A04", "soft": "#E4E9FF"},
    "testing": {"top": "#F8FAFC", "bottom": "#FFFFFF", "accent": "#0F172A", "accent2": "#0891B2", "soft": "#E5EDF5"},
    "evaluation": {"top": "#FFF7ED", "bottom": "#FFFDFC", "accent": "#EA580C", "accent2": "#7C3AED", "soft": "#FDE7CF"},
    "security": {"top": "#FFF5F5", "bottom": "#FFFCFC", "accent": "#B91C1C", "accent2": "#0F766E", "soft": "#FFE0E0"},
}


@dataclass
class Card:
    x: int
    y: int
    w: int
    h: int
    title: str
    bullets: list[str]
    accent: str
    fill: str = WHITE
    border: str | None = None


def hex_rgb(color: str) -> tuple[int, int, int]:
    color = color.lstrip("#")
    return int(color[0:2], 16), int(color[2:4], 16), int(color[4:6], 16)


def lerp(a: int, b: int, t: float) -> int:
    return int(a + (b - a) * t)


def gradient_image(top: str, bottom: str) -> Image.Image:
    image = Image.new("RGBA", (WIDTH, HEIGHT), top)
    pixels = image.load()
    r1, g1, b1 = hex_rgb(top)
    r2, g2, b2 = hex_rgb(bottom)
    for y in range(HEIGHT):
        t = y / max(1, HEIGHT - 1)
        r = lerp(r1, r2, t)
        g = lerp(g1, g2, t)
        b = lerp(b1, b2, t)
        for x in range(WIDTH):
            pixels[x, y] = (r, g, b, 255)
    return image


def new_slide(theme_key: str) -> tuple[Image.Image, ImageDraw.ImageDraw, dict]:
    theme = THEMES[theme_key]
    image = gradient_image(theme["top"], theme["bottom"])
    draw = ImageDraw.Draw(image)
    add_backdrop(draw, theme)
    return image, draw, theme


def add_backdrop(draw: ImageDraw.ImageDraw, theme: dict) -> None:
    draw.ellipse((-140, -120, 500, 500), fill=theme["soft"])
    draw.ellipse((2000, -90, 2760, 670), fill=theme["soft"])
    draw.ellipse((2100, 1030, 2780, 1700), fill=theme["soft"])
    draw.line((80, 160, WIDTH - 80, 160), fill="#D8E1EC", width=3)
    draw.rounded_rectangle((94, 72, 264, 118), radius=22, fill=theme["accent2"])


def text_wh(draw: ImageDraw.ImageDraw, text: str, fnt: ImageFont.ImageFont) -> tuple[int, int]:
    left, top, right, bottom = draw.textbbox((0, 0), text, font=fnt)
    return right - left, bottom - top


def wrap_text(draw: ImageDraw.ImageDraw, text: str, fnt: ImageFont.ImageFont, width: int) -> list[str]:
    words = text.split()
    if not words:
        return [""]
    lines: list[str] = []
    current = words[0]
    for word in words[1:]:
        test = f"{current} {word}"
        if draw.textlength(test, font=fnt) <= width:
            current = test
        else:
            lines.append(current)
            current = word
    lines.append(current)
    return lines


def wrap_paragraphs(draw: ImageDraw.ImageDraw, text: str, fnt: ImageFont.ImageFont, width: int) -> list[str]:
    output: list[str] = []
    for para in text.split("\n"):
        if not para.strip():
            output.append("")
        else:
            output.extend(wrap_text(draw, para, fnt, width))
    return output


def fit_font_for_bullets(
    draw: ImageDraw.ImageDraw,
    bullets: Iterable[str],
    width: int,
    height: int,
    start_size: int = 28,
    min_size: int = 20,
) -> tuple[ImageFont.FreeTypeFont, list[list[str]], int]:
    items = list(bullets)
    for size in range(start_size, min_size - 1, -1):
        fnt = font(size)
        line_h = text_wh(draw, "Ag", fnt)[1] + 5
        wrapped_items: list[list[str]] = []
        total_h = 0
        for item in items:
            wrapped = wrap_paragraphs(draw, item, fnt, width - 28)
            wrapped_items.append(wrapped)
            total_h += len(wrapped) * line_h + 12
        if total_h <= height:
            return fnt, wrapped_items, line_h
    fnt = font(min_size)
    line_h = text_wh(draw, "Ag", fnt)[1] + 4
    wrapped_items = [wrap_paragraphs(draw, item, fnt, width - 28) for item in items]
    return fnt, wrapped_items, line_h


def draw_shadow_card(draw: ImageDraw.ImageDraw, x: int, y: int, w: int, h: int, fill: str, border: str) -> None:
    draw.rounded_rectangle((x + 8, y + 10, x + w + 8, y + h + 10), radius=28, fill=SHADOW)
    draw.rounded_rectangle((x, y, x + w, y + h), radius=28, fill=fill, outline=border, width=3)


def draw_card(draw: ImageDraw.ImageDraw, card: Card) -> None:
    border = card.border or card.accent
    draw_shadow_card(draw, card.x, card.y, card.w, card.h, card.fill, border)
    draw.rounded_rectangle((card.x + 16, card.y + 14, card.x + card.w - 16, card.y + 60), radius=18, fill=card.accent)
    draw.text((card.x + 26, card.y + 23), card.title, font=CARD_TITLE_FONT, fill=WHITE)
    draw.line((card.x + 20, card.y + 74, card.x + card.w - 20, card.y + 74), fill=border, width=2)

    body_top = card.y + 92
    body_height = card.h - 112
    body_width = card.w - 46
    fnt, wrapped_items, line_h = fit_font_for_bullets(draw, card.bullets, body_width, body_height)

    y = body_top
    for item in wrapped_items:
        draw.ellipse((card.x + 26, y + 10, card.x + 36, y + 20), fill=card.accent)
        tx = card.x + 46
        for line in item:
            draw.text((tx, y), line, font=fnt, fill=BODY)
            y += line_h
        y += 10


def draw_kicker(draw: ImageDraw.ImageDraw, label: str) -> None:
    draw.text((114, 81), label, font=KICKER_FONT, fill=WHITE)


def draw_title(draw: ImageDraw.ImageDraw, title: str, subtitle: str) -> None:
    draw.text((90, 200), title, font=TITLE_FONT, fill=TEXT)
    lines = wrap_paragraphs(draw, subtitle, SUBTITLE_FONT, 1450)
    y = 280
    for line in lines:
        draw.text((92, y), line, font=SUBTITLE_FONT, fill=MUTED)
        y += text_wh(draw, line, SUBTITLE_FONT)[1] + 7


def draw_pills(draw: ImageDraw.ImageDraw, x: int, y: int, labels: list[str], accent: str, max_width: int = 1200) -> None:
    cx = x
    cy = y
    row_h = 48
    for label in labels:
        tw, th = text_wh(draw, label, PILL_FONT)
        w = tw + 34
        if cx + w > x + max_width:
            cx = x
            cy += row_h + 12
        draw.rounded_rectangle((cx, cy, cx + w, cy + row_h), radius=24, fill=WHITE, outline=accent, width=2)
        draw.text((cx + 17, cy + (row_h - th) // 2 - 1), label, font=PILL_FONT, fill=accent)
        cx += w + 14


def draw_takeaway(draw: ImageDraw.ImageDraw, text: str, accent: str) -> None:
    draw_shadow_card(draw, 90, 1230, 2380, 120, WHITE, accent)
    draw.text((120, 1260), "Kết luận nhanh", font=font(28, True), fill=accent)
    lines = wrap_paragraphs(draw, text, TAKEAWAY_FONT, 1990)
    y = 1258
    for line in lines:
        draw.text((430, y), line, font=TAKEAWAY_FONT, fill=TEXT)
        y += 33


def arrow(draw: ImageDraw.ImageDraw, x1: int, y1: int, x2: int, y2: int, color: str, label: str | None = None) -> None:
    draw.line((x1, y1, x2, y2), fill=color, width=6)
    if x2 > x1:
        head = [(x2, y2), (x2 - 18, y2 - 12), (x2 - 18, y2 + 12)]
    elif x2 < x1:
        head = [(x2, y2), (x2 + 18, y2 - 12), (x2 + 18, y2 + 12)]
    elif y2 > y1:
        head = [(x2, y2), (x2 - 12, y2 - 18), (x2 + 12, y2 - 18)]
    else:
        head = [(x2, y2), (x2 - 12, y2 + 18), (x2 + 12, y2 + 18)]
    draw.polygon(head, fill=color)
    if label:
        tw, th = text_wh(draw, label, PILL_FONT)
        mx = (x1 + x2) // 2
        my = (y1 + y2) // 2
        draw.rounded_rectangle((mx - tw // 2 - 12, my - th // 2 - 8, mx + tw // 2 + 12, my + th // 2 + 8), radius=16, fill=WHITE, outline=color, width=2)
        draw.text((mx - tw // 2, my - th // 2 - 1), label, font=PILL_FONT, fill=color)


def save(image: Image.Image, name: str) -> Path:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUT_DIR / name
    image.save(path)
    return path


def technology_slide(
    theme_key: str,
    slide_no: str,
    title: str,
    subtitle: str,
    pills: list[str],
    left_card: tuple[str, list[str]],
    mid_card: tuple[str, list[str]],
    right_card: tuple[str, list[str]],
    takeaway: str,
    filename: str,
) -> Path:
    image, draw, theme = new_slide(theme_key)
    draw_kicker(draw, f"TECH CHOICE {slide_no}")
    draw_title(draw, title, subtitle)
    draw_pills(draw, 90, 392, pills, theme["accent"], 1340)

    cards = [
        Card(90, 520, 740, 620, left_card[0], left_card[1], theme["accent"]),
        Card(910, 520, 740, 620, mid_card[0], mid_card[1], theme["accent2"]),
        Card(1730, 520, 740, 620, right_card[0], right_card[1], theme["accent"]),
    ]
    for card in cards:
        draw_card(draw, card)
    draw_takeaway(draw, takeaway, theme["accent"])
    return save(image, filename)


def draw_paragraph_block(
    draw: ImageDraw.ImageDraw,
    x: int,
    y: int,
    text: str,
    width: int,
    *,
    size: int = 26,
    fill: str = BODY,
    bold: bool = False,
    line_gap: int = 6,
) -> int:
    fnt = font(size, bold)
    for line in wrap_paragraphs(draw, text, fnt, width):
        draw.text((x, y), line, font=fnt, fill=fill)
        y += text_wh(draw, line, fnt)[1] + line_gap
    return y


def draw_bullet_block(
    draw: ImageDraw.ImageDraw,
    x: int,
    y: int,
    bullets: list[str],
    width: int,
    *,
    accent: str,
    size: int = 26,
    line_gap: int = 6,
    item_gap: int = 10,
) -> int:
    fnt = font(size)
    line_h = text_wh(draw, "Ag", fnt)[1] + line_gap
    for item in bullets:
        lines = wrap_paragraphs(draw, item, fnt, width - 24)
        draw.ellipse((x, y + 9, x + 10, y + 19), fill=accent)
        tx = x + 20
        for line in lines:
            draw.text((tx, y), line, font=fnt, fill=BODY)
            y += line_h
        y += item_gap
    return y


def draw_step_box(
    draw: ImageDraw.ImageDraw,
    x: int,
    y: int,
    w: int,
    h: int,
    *,
    number: str,
    title: str,
    bullets: list[str],
    accent: str,
    fill: str = WHITE,
) -> None:
    draw_shadow_card(draw, x, y, w, h, fill, accent)
    draw.ellipse((x + 22, y + 18, x + 74, y + 70), fill=accent)
    num_w, num_h = text_wh(draw, number, font(24, True))
    draw.text((x + 48 - num_w // 2, y + 42 - num_h // 2), number, font=font(24, True), fill=WHITE)
    draw.text((x + 92, y + 25), title, font=font(28, True), fill=TEXT)
    draw.line((x + 20, y + 84, x + w - 20, y + 84), fill=accent, width=2)
    draw_bullet_block(draw, x + 24, y + 106, bullets, w - 48, accent=accent, size=24, line_gap=5, item_gap=8)


def draw_metric_tile(
    draw: ImageDraw.ImageDraw,
    x: int,
    y: int,
    w: int,
    h: int,
    *,
    value: str,
    title: str,
    subtitle: str,
    accent: str,
    fill: str = WHITE,
) -> None:
    draw_shadow_card(draw, x, y, w, h, fill, accent)
    draw.text((x + 26, y + 22), value, font=font(50, True), fill=accent)
    draw.text((x + 26, y + 92), title, font=font(26, True), fill=TEXT)
    draw_paragraph_block(draw, x + 26, y + 132, subtitle, w - 52, size=22, fill=MUTED, line_gap=4)


def draw_band_panel(
    draw: ImageDraw.ImageDraw,
    x: int,
    y: int,
    w: int,
    h: int,
    *,
    title: str,
    bullets: list[str],
    accent: str,
) -> None:
    draw_shadow_card(draw, x, y, w, h, WHITE, accent)
    draw.text((x + 26, y + 22), title, font=font(30, True), fill=accent)
    draw.line((x + 24, y + 74, x + w - 24, y + 74), fill=accent, width=2)
    draw_bullet_block(draw, x + 26, y + 96, bullets, w - 52, accent=accent, size=25, line_gap=5, item_gap=8)


def slide_flutter() -> Path:
    return technology_slide(
        "flutter",
        "01",
        "Lý do chọn Flutter làm Frontend",
        "Flutter Web được chọn vì hệ thống này cần một giao diện giống ứng dụng quản trị doanh nghiệp: nhiều màn hình, nhiều trạng thái, nhiều form và nhiều tương tác liên tục.",
        ["Flutter Web", "Ứng dụng nhiều màn", "UI thống nhất", "Dễ mở rộng"],
        (
            "Flutter là gì?",
            [
                "Flutter là framework UI của Google.",
                "Nó xây dựng giao diện theo mô hình widget và hỗ trợ nhiều nền tảng.",
                "Trong đề tài này, nhóm sử dụng Flutter Web để chạy trực tiếp trên trình duyệt.",
            ],
        ),
        (
            "Vì sao chọn cho đề tài này?",
            [
                "Hệ thống có dashboard, quản lý mẫu, quản lý văn bản, ChatAI, AI Doc, ký số và admin.",
                "Frontend cần giữ trải nghiệm liền mạch như một ứng dụng thay vì các trang rời rạc.",
                "Flutter phù hợp với giao diện nhiều bước và nhiều trạng thái người dùng.",
            ],
        ),
        (
            "Ưu thế so với lựa chọn khác",
            [
                "So với Django template thuần: hiện đại hơn và linh hoạt hơn cho UI động.",
                "So với stack frontend ghép nhiều thư viện: thống nhất hơn về cấu trúc và thiết kế.",
                "Có lợi nếu sau này mở rộng cùng định hướng sang mobile.",
            ],
        ),
        "Flutter giúp phần trình bày nghiệp vụ của hệ thống rõ ràng hơn, hiện đại hơn và phù hợp với một ứng dụng quản trị văn bản có AI hơn là một website thông thường.",
        "01_ly_do_chon_flutter.png",
    )


def slide_django() -> Path:
    return technology_slide(
        "django",
        "02",
        "Lý do chọn Django làm Backend",
        "Django phù hợp với hệ thống có nhiều bảng dữ liệu, nhiều quy trình nghiệp vụ và nhiều vai trò người dùng. Đây là dạng bài toán rất điển hình của backend doanh nghiệp.",
        ["Python backend", "ORM mạnh", "Permission", "Migrations", "Management commands"],
        (
            "Django là gì?",
            [
                "Django là web framework backend viết bằng Python.",
                "Nó cung cấp sẵn ORM, authentication, admin, migrations và nhiều tiện ích cho ứng dụng dữ liệu.",
                "Trong hệ thống này, Django là trung tâm điều phối toàn bộ nghiệp vụ.",
            ],
        ),
        (
            "Vì sao chọn cho đề tài này?",
            [
                "Hệ thống cần quản lý template, document, version, approval, mailbox, signing và user group.",
                "Django rất phù hợp với dữ liệu quan hệ và quy trình xử lý theo vai trò.",
                "Django REST Framework cũng giúp kết nối tốt với frontend Flutter Web.",
            ],
        ),
        (
            "Ưu thế so với lựa chọn khác",
            [
                "So với Node.js tối giản: mạnh hơn ở CRUD, ORM và admin cho bài toán dữ liệu nội bộ.",
                "So với FastAPI: phù hợp hơn khi hệ thống không chỉ là API nhanh mà còn là backend nghiệp vụ đầy đủ.",
                "Dễ phát triển nhanh nhưng vẫn giữ cấu trúc rõ và dễ bảo trì.",
            ],
        ),
        "Django được chọn vì nó đáp ứng rất đúng bản chất của hệ thống: nhiều dữ liệu, nhiều quyền, nhiều quy trình và cần một backend ổn định để tích hợp AI.",
        "02_ly_do_chon_django.png",
    )


def slide_postgres() -> Path:
    return technology_slide(
        "postgres",
        "03",
        "Lý do chọn PostgreSQL kết hợp PGVector",
        "Hệ thống này vừa cần quản lý dữ liệu quan hệ chặt chẽ, vừa cần semantic retrieval cho AI. PostgreSQL + PGVector là một lựa chọn thực dụng và cân bằng cho cả hai nhu cầu đó.",
        ["Relational DB", "ACID", "PGVector", "Semantic retrieval", "RAG ready"],
        (
            "PostgreSQL + PGVector là gì?",
            [
                "PostgreSQL là hệ quản trị cơ sở dữ liệu quan hệ mã nguồn mở.",
                "PGVector là extension giúp PostgreSQL lưu và truy vấn vector embedding.",
                "Nhờ đó, cùng một nền tảng có thể phục vụ cả dữ liệu nghiệp vụ lẫn RAG.",
            ],
        ),
        (
            "Vì sao chọn cho đề tài này?",
            [
                "Dữ liệu có quan hệ chặt: user, template, document, version, approval, signing, chat session.",
                "Hệ thống AI cần embedding cho template và document để hỏi đáp theo ngữ cảnh.",
                "Giữ metadata và vector gần nhau sẽ đơn giản hơn cho backup, restore và vận hành.",
            ],
        ),
        (
            "Ưu thế so với lựa chọn khác",
            [
                "So với MongoDB: phù hợp hơn cho dữ liệu doanh nghiệp nhiều quan hệ và nhiều ràng buộc.",
                "So với relational DB + vector DB tách riêng: ít service hơn, dễ triển khai hơn.",
                "Đây là lựa chọn cân bằng giữa hệ thống truyền thống và nhu cầu AI hiện đại.",
            ],
        ),
        "PostgreSQL + PGVector giúp hệ thống vừa mạnh về dữ liệu doanh nghiệp, vừa đủ khả năng phục vụ RAG mà không làm kiến trúc trở nên quá nặng ở giai đoạn đầu.",
        "03_ly_do_chon_postgresql_pgvector.png",
    )


def slide_ollama() -> Path:
    return technology_slide(
        "ollama",
        "04",
        "Lý do chọn Ollama cho lớp AI Runtime",
        "Ollama được chọn vì nó giúp hệ thống AI có thể triển khai cục bộ hoặc nội bộ, phù hợp với dữ liệu doanh nghiệp và giảm phụ thuộc tuyệt đối vào dịch vụ AI bên ngoài.",
        ["Local AI", "Embeddings", "Chat runtime", "On-premise", "Dễ thay model"],
        (
            "Ollama là gì?",
            [
                "Ollama là runtime giúp tải và chạy mô hình AI trên máy local hoặc server riêng.",
                "Nó hỗ trợ chạy chat model và embedding model theo cách đơn giản hơn nhiều so với tự dựng inference stack.",
                "Trong đề tài này, Ollama là lớp suy luận chính cho ChatAI và RAG.",
            ],
        ),
        (
            "Vì sao chọn cho đề tài này?",
            [
                "Hệ thống cần chat AI, RAG, AI Doc, trích xuất tài liệu và embedding cho vector search.",
                "Dữ liệu văn bản doanh nghiệp thường nhạy cảm nên triển khai nội bộ là lợi thế lớn.",
                "Ollama giúp dựng demo và pilot nhanh hơn mà vẫn đủ thực tế.",
            ],
        ),
        (
            "Ưu thế so với lựa chọn khác",
            [
                "So với cloud AI API: chủ động hơn về dữ liệu, chi phí và mô hình triển khai nội bộ.",
                "So với tự dựng inference server từ đầu: nhanh hơn, nhẹ hơn và dễ vận hành hơn.",
                "Có thể chạy cùng máy ở quy mô nhỏ hoặc tách riêng khi tải AI tăng.",
            ],
        ),
        "Ollama là lựa chọn thực tiễn cho lớp AI của hệ thống: đủ mạnh để chạy ChatAI và RAG, nhưng vẫn giữ được tính chủ động và khả năng triển khai nội bộ.",
        "04_ly_do_chon_ollama.png",
    )


def slide_compare() -> Path:
    image, draw, theme = new_slide("compare")
    draw_kicker(draw, "TECH CHOICE 05")
    draw_title(
        draw,
        "Điểm mạnh so với các kiến trúc tương đồng",
        "Không có một stack tốt nhất tuyệt đối. Nhưng với bài toán quản lý văn bản doanh nghiệp có AI, lựa chọn hiện tại nổi bật ở tính cân bằng giữa giao diện, dữ liệu, AI và khả năng triển khai thực tế.",
    )
    draw_pills(draw, 90, 392, ["Flutter + Django + PostgreSQL/PGVector + Ollama", "Cân bằng", "Dễ triển khai pilot"], theme["accent2"], 1350)

    hero = Card(
        90,
        520,
        2380,
        240,
        "Kiến trúc hiện tại mạnh ở đâu?",
        [
            "Giao diện hiện đại nhờ Flutter Web, backend nghiệp vụ rõ ràng nhờ Django, dữ liệu quan hệ mạnh nhờ PostgreSQL và RAG khả thi nhờ PGVector + Ollama.",
            "Điểm quan trọng nhất là stack này đủ hiện đại để hỗ trợ AI, nhưng chưa đẩy hệ thống vào mức phức tạp vận hành quá cao cho đồ án hoặc giai đoạn thử nghiệm.",
        ],
        theme["accent2"],
    )
    draw_card(draw, hero)

    cards = [
        Card(
            90,
            820,
            740,
            330,
            "So với React + Node + Mongo + Cloud AI",
            [
                "Ít phụ thuộc hơn vào các thành phần ngoài và phù hợp hơn với dữ liệu quan hệ doanh nghiệp.",
                "Dễ kiểm soát bảo mật dữ liệu AI hơn khi triển khai nội bộ.",
                "Đỡ bị chẻ nhỏ công nghệ quá nhiều ở giai đoạn đầu.",
            ],
            theme["accent"],
        ),
        Card(
            910,
            820,
            740,
            330,
            "So với Django template thuần",
            [
                "Trải nghiệm người dùng tốt hơn nhờ Flutter Web và kiến trúc SPA.",
                "Dễ xây dựng dashboard, AI chat, form nhiều bước và điều hướng hiện đại hơn.",
                "Phần AI và frontend vì thế cũng thuyết phục hơn khi demo.",
            ],
            "#475569",
        ),
        Card(
            1730,
            820,
            740,
            330,
            "So với microservice quá sớm",
            [
                "Triển khai nhanh hơn, ít service hơn và dễ debug hơn.",
                "Phù hợp với pilot hoặc đồ án khi ưu tiên hoàn thiện nghiệp vụ trước.",
                "Vẫn còn không gian để scale riêng DB, AI hoặc storage khi cần.",
            ],
            "#7C3AED",
        ),
    ]
    for card in cards:
        draw_card(draw, card)

    draw_takeaway(draw, "Lựa chọn hiện tại không cực đoan theo hướng quá đơn giản hay quá phân tán. Nó mạnh ở tính thực dụng: đủ tốt để làm thật, đủ gọn để triển khai và đủ rõ để thuyết trình.", theme["accent2"])
    return save(image, "05_diem_manh_so_voi_kien_truc_tuong_dong.png")


def slide_deploy() -> Path:
    image, draw, theme = new_slide("deploy")
    draw_kicker(draw, "TECH CHOICE 06")
    draw_title(
        draw,
        "Mô hình triển khai và kết luận công nghệ",
        "Mô hình đề xuất ưu tiên một cổng truy cập duy nhất, Django làm bộ điều phối trung tâm, PostgreSQL + PGVector làm lõi dữ liệu, và Ollama đảm nhiệm lớp AI runtime.",
    )
    draw_pills(draw, 90, 392, ["One domain", "Same-origin API", "Dễ triển khai nội bộ", "Scale dần"], theme["accent"], 1300)

    user = Card(90, 540, 290, 170, "Người dùng", ["Nhân viên, admin và guest truy cập bằng trình duyệt."], theme["accent"])
    nginx = Card(430, 540, 290, 170, "Nginx", ["HTTPS và reverse proxy."], theme["accent2"])
    django = Card(770, 500, 480, 250, "Django + REST API", ["Phục vụ Flutter Web build.", "Phục vụ API, auth, permission và module nghiệp vụ."], "#16A34A")
    pg = Card(90, 860, 360, 200, "PostgreSQL + Vector", ["Lưu dữ liệu nghiệp vụ; phần vector do PGVector đảm nhiệm cho semantic retrieval."], "#0F766E")
    ollama = Card(490, 860, 360, 200, "Ollama", ["Chạy chat model, embedding model và các luồng AI nội bộ."], theme["accent"])
    media = Card(890, 860, 360, 200, "Media + backup", ["Lưu DOCX, PDF, signed PDF, preview, audio và file backup."], "#CA8A04")
    for card in (user, nginx, django, pg, ollama, media):
        draw_card(draw, card)

    arrow(draw, 380, 625, 430, 625, theme["accent"], "HTTPS")
    arrow(draw, 720, 625, 770, 625, theme["accent"], "route")
    arrow(draw, 1010, 750, 270, 860, "#16A34A", "DB")
    arrow(draw, 1010, 750, 670, 860, "#16A34A", "AI")
    arrow(draw, 1010, 750, 1070, 860, "#16A34A", "file")

    right_top = Card(
        1410,
        520,
        1060,
        270,
        "Vì sao mô hình triển khai này dễ dùng hơn",
        [
            "Frontend và backend dùng cùng domain nên giảm độ phức tạp CORS và xác thực.",
            "Django đứng giữa nên luồng tài liệu, AI và signing không bị chia nhỏ quá sớm.",
            "Phù hợp cho môi trường nội bộ nhưng vẫn còn đường mở để scale PostgreSQL, Ollama hoặc storage.",
        ],
        theme["accent"],
    )
    right_bottom = Card(
        1410,
        840,
        1060,
        270,
        "Kết luận lựa chọn công nghệ",
        [
            "Flutter phù hợp cho giao diện ứng dụng doanh nghiệp nhiều màn và nhiều trạng thái.",
            "Django phù hợp cho backend dữ liệu, phân quyền và quy trình văn bản.",
            "PostgreSQL + PGVector + Ollama tạo thành một lõi AI doanh nghiệp khả thi và thực dụng.",
        ],
        theme["accent2"],
    )
    draw_card(draw, right_top)
    draw_card(draw, right_bottom)
    draw_takeaway(draw, "Tổng thể, đây là một stack có tính thực dụng cao: đủ mạnh để thuyết phục về mặt kỹ thuật, đủ gọn để triển khai thử nghiệm và đủ rõ để tiếp tục mở rộng sau này.", theme["accent"])
    return save(image, "06_mo_hinh_trien_khai_va_ket_luan_cong_nghe.png")


def slide_domain_current() -> Path:
    return technology_slide(
        "domain",
        "07",
        "Cấu hình domain hiện tại với ngrok",
        "Hiện tại hệ thống đang dùng ngrok để mở server local ra Internet phục vụ demo, đăng nhập social và kiểm thử từ bên ngoài mạng nội bộ. Đây là mô hình phù hợp cho giai đoạn phát triển, chưa phải đích đến production lâu dài.",
        ["Ngrok tunnel", "Demo từ Internet", "Same-origin /api/", "Phù hợp dev"],
        (
            "Ngrok là gì?",
            [
                "Ngrok tạo một URL public tạm thời trỏ vào server đang chạy local.",
                "Nhờ đó nhóm có thể demo hệ thống cho người khác mà chưa cần thuê VPS ngay.",
                "Cách này hữu ích khi cần test callback, social login và luồng dùng thật.",
            ],
        ),
        (
            "Codebase đang cấu hình ra sao?",
            [
                "settings.py đã cho phép .ngrok-free.app trong ALLOWED_HOSTS.",
                "CSRF_TRUSTED_ORIGINS đã trust https://*.ngrok-free.app cho form và API.",
                "Flutter Web gọi API theo Uri.base.origin/api nên frontend và backend vẫn cùng origin.",
            ],
        ),
        (
            "Ưu điểm và giới hạn hiện tại",
            [
                "Ưu điểm là dựng nhanh, rẻ và rất tiện để chia sẻ bản demo đang phát triển.",
                "Giới hạn là URL thường thay đổi, độ ổn định phụ thuộc tunnel và khó xem là môi trường chính thức.",
                "Vì vậy ngrok phù hợp cho phát triển và trình bày hơn là vận hành doanh nghiệp lâu dài.",
            ],
        ),
        "Ngrok đang giải quyết tốt bài toán truy cập từ xa cho giai đoạn demo; nhưng khi muốn vận hành ổn định, hệ thống cần chuyển sang VPS và domain riêng.",
        "07_cau_hinh_domain_hien_tai_ngrok.png",
    )


def slide_domain_future() -> Path:
    return technology_slide(
        "roadmap",
        "08",
        "Lộ trình VPS và domain production",
        "Khi hệ thống chuyển từ demo sang vận hành thật, nhóm dự kiến mua VPS để host ứng dụng và mua domain riêng để tạo một điểm truy cập ổn định cho người dùng doanh nghiệp. Đây là bước cần thiết để tiến gần môi trường production.",
        ["VPS riêng", "Domain cố định", "HTTPS", "Sẵn sàng mở rộng"],
        (
            "VPS và domain là gì?",
            [
                "VPS là máy chủ ảo chạy 24/7 để host ứng dụng trên Internet.",
                "Domain là địa chỉ cố định giúp người dùng truy cập dễ nhớ và gắn HTTPS.",
                "Hai thành phần này biến bản demo thành hệ thống có thể vận hành ổn định hơn.",
            ],
        ),
        (
            "Mô hình dự định triển khai",
            [
                "Domain sẽ trỏ về Nginx, sau đó reverse proxy tới Django và Flutter Web.",
                "Django tiếp tục phục vụ API cùng frontend theo mô hình same-origin như hiện tại.",
                "PostgreSQL, PGVector, Ollama và media có thể đặt cùng VPS rồi tách dần khi tải tăng.",
            ],
        ),
        (
            "Lợi ích so với ngrok",
            [
                "URL ổn định hơn, thuận lợi cho nhân viên truy cập và cho việc trình diễn chính thức.",
                "Dễ cấu hình SSL, social login, backup, monitoring và phân quyền truy cập.",
                "Tạo nền để mở rộng sang staging, production và server AI riêng trong tương lai.",
            ],
        ),
        "Lộ trình hợp lý là dùng ngrok để phát triển nhanh, sau đó chuyển sang VPS và domain riêng khi cần tính ổn định, bảo mật và khả năng vận hành thật.",
        "08_lo_trinh_vps_va_domain_production.png",
    )


def slide_signing() -> Path:
    return technology_slide(
        "signing",
        "09",
        "Cơ chế ký số trong hệ thống",
        "Hệ thống hỗ trợ quy trình ký văn bản nhiều bước trên file PDF. Theo codebase hiện tại, tài liệu được chốt từ DOCX sang PDF rồi mới đưa vào luồng ký, ghi nhận chữ ký và xác minh toàn vẹn.",
        ["PDF signing", "PKCS#7", "Multi-step workflow", "Verify integrity"],
        (
            "Ký số trong hệ thống là gì?",
            [
                "Hệ thống không ký trực tiếp DOCX; tài liệu được chuyển sang PDF rồi mới ký.",
                "Chế độ chính hiện tại là pdf_pkcs7, phù hợp hơn với ký số PDF thực tế.",
                "Ngoài ra hệ thống vẫn giữ legacy_internal cho các trường hợp xác nhận nội bộ cũ.",
            ],
        ),
        (
            "Luồng ký đang được triển khai",
            [
                "Tạo SigningProposal, chọn signer và đóng băng đúng phiên bản tài liệu cần ký.",
                "Sinh SigningPacket và SigningTask cho từng người ký theo đúng thứ tự bước.",
                "Sau khi ký, hệ thống tạo SignedPdfDocument, lưu PdfSignatureRecord và cho phép verify.",
            ],
        ),
        (
            "Điểm mạnh của thiết kế này",
            [
                "Quy trình ký gắn với đúng phiên bản nội dung để tránh ký nhầm sau khi tài liệu bị sửa.",
                "Hệ thống chặn preview hoặc download khi PDF bị tamper và chỉ forward bản an toàn.",
                "Có sẵn nền cho internal PKI, auto credential và khả năng mở rộng sang remote HSM.",
            ],
        ),
        "Ký số là một điểm mạnh của đề tài vì hệ thống không chỉ hiển thị trạng thái ký, mà còn có cơ chế đóng băng phiên bản, ký theo bước và xác minh toàn vẹn PDF.",
        "09_co_che_ky_so_trong_he_thong.png",
    )


def slide_testing() -> Path:
    return technology_slide(
        "testing",
        "10",
        "Kiểm thử hệ thống",
        "Codebase đã có cả kiểm thử backend tự động và các luồng kiểm tra nghiệp vụ quan trọng. Điều này giúp giảm rủi ro khi chỉnh sửa các phần nhạy như AI, văn bản, mailbox và ký số.",
        ["Unit + integration", "Django TestCase", "Regression control", "Luồng rủi ro cao"],
        (
            "Các nhóm chức năng đã test",
            [
                "Xác thực và hồ sơ người dùng trong api/tests_auth_profile.py.",
                "Template API trong api/tests_templates.py.",
                "RAG và rebuild index trong ai_engine/tests_rag.py.",
            ],
        ),
        (
            "Các luồng nghiệp vụ quan trọng",
            [
                "Mailbox và forward bản đã ký trong documents/tests_mailbox.py.",
                "Quy trình ký số nhiều bước trong signing/tests.py.",
                "PDF PKCS#7 và credential PKI trong signing/tests_pki.py.",
            ],
        ),
        (
            "Ý nghĩa của phần kiểm thử",
            [
                "Kiểm thử không chỉ CRUD mà còn kiểm tra quyền truy cập, toàn vẹn file và trạng thái quy trình.",
                "Nhờ đó nhóm có thể phát hiện regression sớm khi sửa API, signing hoặc RAG.",
                "Đây là cơ sở để chứng minh hệ thống có thể bảo trì và mở rộng an toàn hơn.",
            ],
        ),
        "Nền kiểm thử hiện tại khá tốt cho một đề tài ứng dụng vì các test bám vào những luồng rủi ro cao, thay vì chỉ kiểm tra giao diện bề ngoài.",
        "10_kiem_thu_he_thong.png",
    )


def slide_evaluation() -> Path:
    return technology_slide(
        "evaluation",
        "11",
        "Đánh giá hệ thống và hướng phát triển",
        "Sau khi hoàn thiện phiên bản hiện tại, có thể đánh giá hệ thống theo ba góc độ chính: mức độ đáp ứng nghiệp vụ, giá trị của AI và khả năng triển khai thực tế trong doanh nghiệp.",
        ["Nghiệp vụ", "AI usefulness", "Triển khai thực tế", "Cần mở rộng thêm"],
        (
            "Kết quả đạt được",
            [
                "Đã kết nối được quản lý mẫu, sinh văn bản, hỏi đáp RAG, ký số và admin trong một hệ thống thống nhất.",
                "Frontend, backend, database và AI runtime đã phối hợp thành một quy trình end-to-end.",
                "Mô hình này đủ rõ để minh họa giá trị của AI agent trong quản lý văn bản doanh nghiệp.",
            ],
        ),
        (
            "Giới hạn hiện tại",
            [
                "Hạ tầng truy cập vẫn đang dựa vào ngrok nên chưa phải môi trường production chính thức.",
                "Hiệu năng AI còn phụ thuộc cấu hình máy chạy Ollama và chưa có kiểm thử tải lớn.",
                "Cần bổ sung monitoring, CI/CD và kiểm thử bảo mật nếu triển khai thực tế.",
            ],
        ),
        (
            "Định hướng phát triển tiếp",
            [
                "Chuyển sang VPS và domain riêng, sau đó tách dần các dịch vụ nặng khi tải tăng.",
                "Mở rộng đánh giá bằng UAT với người dùng thật trong doanh nghiệp.",
                "Bổ sung benchmark AI, kiểm thử tải và dashboard giám sát vận hành.",
            ],
        ),
        "Về tổng thể, hệ thống đã đạt mức prototype doanh nghiệp khá hoàn chỉnh; bước tiếp theo là chuẩn hóa hạ tầng, tăng kiểm thử và tối ưu hiệu năng để tiến gần production.",
        "11_danh_gia_he_thong_va_huong_phat_trien.png",
    )


def slide_compare_cloud() -> Path:
    image, draw, theme = new_slide("compare")
    draw_kicker(draw, "TECH CHOICE 05")
    draw_title(
        draw,
        "Điểm mạnh so với các kiến trúc tương đồng",
        "Hệ thống hiện đang dùng cloud LLM cho lớp suy luận. Vì vậy ưu thế chính không nằm ở local AI tuyệt đối, mà ở cách kiến trúc vẫn giữ được dữ liệu mạnh, nghiệp vụ rõ ràng và khả năng đổi nguồn model khi cần.",
    )
    draw_pills(
        draw,
        90,
        392,
        [
            "Flutter + Django + PostgreSQL/PGVector + AI layer linh hoạt",
            "Cân bằng nghiệp vụ",
            "Không khóa cứng model",
        ],
        theme["accent2"],
        1620,
    )

    hero = Card(
        90,
        520,
        2380,
        240,
        "Kiến trúc hiện tại mạnh ở đâu?",
        [
            "Flutter Web phù hợp cho giao diện ứng dụng nhiều màn hình; Django giữ vai trò điều phối nghiệp vụ, phân quyền và quy trình văn bản; PostgreSQL + PGVector đảm nhiệm lõi dữ liệu và truy hồi ngữ nghĩa.",
            "LLM hiện được dùng theo hướng cloud để tận dụng chất lượng mô hình, nhưng kiến trúc backend vẫn đủ mở để chuyển sang local hoặc hybrid sau này nếu yêu cầu chi phí, hiệu năng hoặc bảo mật thay đổi.",
        ],
        theme["accent2"],
    )
    draw_card(draw, hero)

    cards = [
        Card(
            90,
            820,
            740,
            330,
            "So với React + Node + Mongo + Cloud LLM",
            [
                "Mạnh hơn ở dữ liệu quan hệ, workflow văn bản và phân quyền doanh nghiệp.",
                "PGVector giúp gắn semantic retrieval sát dữ liệu nghiệp vụ thay vì tách riêng vector database quá sớm.",
                "Cloud model vẫn dùng được, nhưng điều phối tool, tài liệu và quyền truy cập vẫn nằm tập trung ở backend.",
            ],
            theme["accent"],
        ),
        Card(
            910,
            820,
            740,
            330,
            "So với Django template thuần",
            [
                "Trải nghiệm người dùng tốt hơn nhờ Flutter Web và kiến trúc SPA.",
                "Dễ xây dựng dashboard, AI chat, form nhiều bước và điều hướng hiện đại hơn.",
                "Các luồng AI, preview tài liệu và thao tác thời gian thực vì thế cũng thuyết phục hơn khi demo.",
            ],
            "#475569",
        ),
        Card(
            1730,
            820,
            740,
            330,
            "So với microservice quá sớm",
            [
                "Triển khai nhanh hơn, ít service hơn và dễ debug hơn.",
                "Phù hợp với pilot hoặc đồ án khi ưu tiên hoàn thiện nghiệp vụ trước, chưa cần chia nhỏ hệ thống quá sớm.",
                "Vẫn còn không gian để đổi nhà cung cấp LLM, hoặc scale riêng DB, AI và storage khi cần.",
            ],
            "#7C3AED",
        ),
    ]
    for card in cards:
        draw_card(draw, card)

    draw_takeaway(
        draw,
        "Điểm mạnh không nằm ở việc local hay cloud tuyệt đối, mà ở chỗ kiến trúc vẫn cân bằng giữa giao diện, dữ liệu, nghiệp vụ và AI; dùng cloud LLM hôm nay nhưng chưa tự khóa mình vào một hướng triển khai duy nhất.",
        theme["accent2"],
    )
    return save(image, "05_diem_manh_so_voi_kien_truc_tuong_dong.png")


def preview(paths: list[Path]) -> Path:
    image = Image.new("RGBA", (2560, 2160), "#F7F9FC")
    draw = ImageDraw.Draw(image)
    draw.text((70, 54), "Bộ slide công nghệ - bản dễ nhìn hơn", font=TITLE_FONT, fill=TEXT)
    draw.text((70, 124), "6 slide PNG đã rút gọn nội dung, tăng cỡ chữ và bổ sung phần giới thiệu từng công nghệ.", font=SUBTITLE_FONT, fill=MUTED)
    draw.line((70, 170, 2490, 170), fill="#D7E0EA", width=3)

    slots = []
    x_positions = [70, 1315]
    y_positions = [220, 875, 1530]
    idx = 0
    for y in y_positions:
        for x in x_positions:
            if idx < len(paths):
                slots.append((x, y))
            idx += 1

    for i, (path, (x, y)) in enumerate(zip(paths, slots), start=1):
        img = Image.open(path).convert("RGBA")
        img.thumbnail((1160, 600))
        draw_shadow_card(draw, x, y, 1190, 620, WHITE, "#CBD5E1")
        image.alpha_composite(img, (x + (1190 - img.width) // 2, y + 16))
        draw.text((x + 26, y + 570), f"{i:02d}. {path.stem}", font=font(22, True), fill=TEXT)
    return save(image, "00_preview_bo_slide_cong_nghe.png")


def preview_extra(paths: list[Path]) -> Path:
    image = Image.new("RGBA", (2560, 2160), "#F7F9FC")
    draw = ImageDraw.Draw(image)
    draw.text((70, 54), "Bo slide mo rong - domain, ky so, kiem thu", font=TITLE_FONT, fill=TEXT)
    draw.text((70, 124), "5 slide PNG bo sung cho phan trien khai thuc te, ky so va danh gia he thong.", font=SUBTITLE_FONT, fill=MUTED)
    draw.line((70, 170, 2490, 170), fill="#D7E0EA", width=3)

    slots = []
    x_positions = [70, 1315]
    y_positions = [220, 875, 1530]
    idx = 0
    for y in y_positions:
        for x in x_positions:
            if idx < len(paths):
                slots.append((x, y))
            idx += 1

    for i, (path, (x, y)) in enumerate(zip(paths, slots), start=1):
        img = Image.open(path).convert("RGBA")
        img.thumbnail((1160, 600))
        draw_shadow_card(draw, x, y, 1190, 620, WHITE, "#CBD5E1")
        image.alpha_composite(img, (x + (1190 - img.width) // 2, y + 16))
        draw.text((x + 26, y + 570), f"{i + 6:02d}. {path.stem}", font=font(22, True), fill=TEXT)
    return save(image, "07_11_preview_bo_slide_mo_rong.png")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    paths = [
        slide_flutter(),
        slide_django(),
        slide_postgres(),
        slide_ollama(),
        slide_compare_cloud(),
        slide_deploy(),
        slide_domain_current(),
        slide_domain_future(),
        slide_signing(),
        slide_testing(),
        slide_evaluation(),
    ]
    preview(paths[:6])
    preview_extra(paths[6:])
    for path in paths:
        print(path)


if __name__ == "__main__":
    main()
