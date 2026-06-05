from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

from render_technology_slides import (
    MUTED,
    OUT_DIR,
    SUBTITLE_FONT,
    TEXT,
    TITLE_FONT,
    WHITE,
    Card,
    arrow,
    draw_band_panel,
    draw_bullet_block,
    draw_card,
    draw_kicker,
    draw_metric_tile,
    draw_paragraph_block,
    draw_pills,
    draw_shadow_card,
    draw_step_box,
    draw_takeaway,
    draw_title,
    font,
    new_slide,
    save,
)


def slide_domain_current() -> Path:
    image, draw, theme = new_slide("domain")
    draw_kicker(draw, "TECH CHOICE 07")
    draw_title(
        draw,
        "Cấu hình domain hiện tại với ngrok",
        "Hệ thống đang dùng ngrok để đưa server local ra Internet phục vụ demo, social login và kiểm thử từ ngoài mạng nội bộ. Đây là cách triển khai nhanh cho giai đoạn phát triển, nhưng chưa phải mô hình production lâu dài.",
    )
    draw_pills(draw, 90, 392, ["Ngrok tunnel", "Demo từ Internet", "Same-origin /api/", "Phù hợp dev"], theme["accent"], 1250)

    steps = [
        ("1", "Mở URL public", ["Người dùng truy cập địa chỉ ngrok trên trình duyệt."]),
        ("2", "Tunnel về máy dev", ["Ngrok chuyển request từ Internet về server local đang chạy."]),
        ("3", "Django phục vụ hệ thống", ["Backend serve cả Flutter Web build lẫn REST API."]),
        ("4", "Frontend gọi cùng origin", ["Flutter Web dùng `Uri.base.origin/api/` để gọi cùng domain."]),
    ]
    sx, sy, sw, sh, gap = 90, 520, 680, 145, 12
    for idx, (num, title, bullets) in enumerate(steps):
        y = sy + idx * (sh + gap)
        draw_step_box(draw, sx, y, sw, sh, number=num, title=title, bullets=bullets, accent=theme["accent"])
        if idx < len(steps) - 1:
            arrow(draw, sx + sw // 2, y + sh, sx + sw // 2, y + sh + gap, theme["accent2"])

    config_card = Card(
        830,
        520,
        1640,
        300,
        "Các cấu hình thật đang bật trong codebase",
        [
            "ALLOWED_HOSTS đã cho phép `.ngrok-free.app` để request từ tunnel không bị chặn.",
            "CSRF_TRUSTED_ORIGINS đã trust `https://*.ngrok-free.app` cho form và API.",
            "USE_X_FORWARDED_HOST và SECURE_PROXY_SSL_HEADER đã sẵn sàng cho mô hình proxy/HTTPS.",
            "Flutter Web dùng `Uri.base.origin/api/`, nên khi Django serve frontend thì API vẫn same-origin.",
        ],
        theme["accent2"],
    )
    demo_card = Card(
        830,
        860,
        790,
        280,
        "Điểm mạnh cho giai đoạn demo",
        [
            "Dựng nhanh, rẻ và rất tiện để chia sẻ bản demo đang phát triển.",
            "Thuận lợi khi cần test callback, social login hoặc luồng dùng từ xa.",
            "Phù hợp cho giai đoạn làm đồ án và trình bày tiến độ.",
        ],
        theme["accent"],
    )
    limit_card = Card(
        1680,
        860,
        790,
        280,
        "Giới hạn nếu dùng lâu dài",
        [
            "URL thường thay đổi nên khó xem là địa chỉ truy cập chính thức.",
            "Độ ổn định phụ thuộc tunnel, không tối ưu cho vận hành doanh nghiệp.",
            "Khó chuẩn hóa backup, monitoring và chính sách truy cập dài hạn.",
        ],
        theme["accent"],
    )
    for card in (config_card, demo_card, limit_card):
        draw_card(draw, card)

    draw_takeaway(
        draw,
        "Ngrok phù hợp để phát triển và demo nhanh; nhưng khi hệ thống cần ổn định và chính thức hơn, hạ tầng phải chuyển sang VPS và domain riêng.",
        theme["accent"],
    )
    return save(image, "07_cau_hinh_domain_hien_tai_ngrok.png")


def slide_domain_future() -> Path:
    image, draw, theme = new_slide("roadmap")
    draw_kicker(draw, "TECH CHOICE 08")
    draw_title(
        draw,
        "Lộ trình VPS và domain production",
        "Khi đi từ bản demo sang môi trường dùng thật, hệ thống cần một địa chỉ ổn định và một server chạy 24/7. Vì vậy nhóm dự kiến chuyển từ ngrok sang VPS và domain riêng để tiến gần mô hình production.",
    )
    draw_pills(draw, 90, 392, ["VPS riêng", "Domain cố định", "HTTPS", "Sẵn sàng mở rộng"], theme["accent"], 1200)

    steps = [
        ("1", "Mua VPS", ["Chuẩn bị server chạy 24/7.", "Cài môi trường hệ thống và database."]),
        ("2", "Mua domain", ["Trỏ DNS về VPS.", "Chuẩn hóa địa chỉ truy cập cố định."]),
        ("3", "Deploy ứng dụng", ["Nginx reverse proxy tới Django.", "Giữ Flutter Web và API cùng origin."]),
        ("4", "Bật vận hành", ["HTTPS, backup, monitoring.", "Tách AI hoặc storage khi tải tăng."]),
    ]
    start_x, step_y, step_w, step_h, gap = 120, 540, 530, 210, 20
    for idx, (num, title, bullets) in enumerate(steps):
        x = start_x + idx * (step_w + gap)
        draw_step_box(draw, x, step_y, step_w, step_h, number=num, title=title, bullets=bullets, accent=theme["accent"])
        if idx < len(steps) - 1:
            arrow(draw, x + step_w, step_y + step_h // 2, x + step_w + gap, step_y + step_h // 2, theme["accent2"])

    target_card = Card(
        90,
        820,
        1140,
        350,
        "Kiến trúc mục tiêu sau khi lên VPS",
        [
            "Domain trỏ vào Nginx, sau đó Nginx route request vào Django.",
            "Django tiếp tục serve cả Flutter Web build lẫn REST API theo mô hình same-origin.",
            "PostgreSQL, PGVector, Ollama và media có thể đặt cùng VPS ở giai đoạn đầu rồi tách dần khi cần scale.",
        ],
        theme["accent2"],
    )
    benefit_card = Card(
        1330,
        820,
        1140,
        350,
        "Lợi ích đối với môi trường doanh nghiệp",
        [
            "URL ổn định hơn cho người dùng nội bộ và cho buổi demo chính thức.",
            "Dễ cấu hình SSL, social login, backup, logging và chính sách truy cập.",
            "Tạo nền để có staging, production và khả năng tách server AI riêng trong tương lai.",
        ],
        theme["accent"],
    )
    draw_card(draw, target_card)
    draw_card(draw, benefit_card)

    draw_takeaway(
        draw,
        "Lộ trình hợp lý là dùng ngrok để phát triển nhanh, sau đó chuyển sang VPS và domain riêng khi hệ thống cần tính ổn định, bảo mật và khả năng vận hành thật.",
        theme["accent"],
    )
    return save(image, "08_lo_trinh_vps_va_domain_production.png")


def slide_signing() -> Path:
    image, draw, theme = new_slide("signing")
    draw_kicker(draw, "TECH CHOICE 09")
    draw_title(
        draw,
        "Deploy và setup hệ thống ký số",
        "Phần ký số không chỉ là một module nghiệp vụ, mà còn là một cụm triển khai riêng với dependency PDF signing, cấu hình PKI/HSM, credential người ký và bước kiểm thử verify sau khi setup. Với codebase này, deploy ký số nên trình bày như một quy trình cấu hình từng lớp.",
    )
    draw_pills(draw, 90, 392, ["pyHanko", "pdf_pkcs7", "Internal PKI / HSM", "Verify after setup"], theme["accent"], 1280)

    intro_card = Card(
        90,
        510,
        760,
        240,
        "Thành phần cần cài trước",
        [
            "Máy chạy backend cần có `pyHanko`, `pyhanko-certvalidator` và `cryptography` để ký PDF và verify chain.",
            "Luồng ký vẫn dựa trên lớp PDF hiện có của hệ thống, vì tài liệu được ký sau khi convert từ DOCX sang PDF.",
        ],
        theme["accent"],
    )
    config_card = Card(
        900,
        510,
        1570,
        240,
        "Biến môi trường và cấu hình cần chuẩn bị",
        [
            "`SIGNING_DEFAULT_SIGNATURE_MODE` hiện dùng `pdf_pkcs7` làm mặc định.",
            "Nếu dùng remote HSM thì phải cấu hình `SIGNING_REMOTE_HSM_*`: base URL, healthcheck, sign URL, API key, SSL verify.",
            "Nếu dùng internal PKI thì phải chuẩn bị trust CA, intermediate CA và dữ liệu credential qua `UserSigningCredential` và `InternalPkiConfig`.",
        ],
        theme["accent2"],
    )
    draw_card(draw, intro_card)
    draw_card(draw, config_card)

    process_steps = [
        ("1", "Cài dependency", ["Cài pyHanko, certvalidator và cryptography trên máy backend."]),
        ("2", "Cấu hình .env", ["Chọn `pdf_pkcs7` và khai báo HSM hoặc trust CA."]),
        ("3", "Cấp credential", ["Khởi tạo internal PKI hoặc gắn chứng thư cho user ký."]),
        ("4", "Chạy và kiểm tra", ["Khởi động Django, test health HSM và API signing."]),
        ("5", "Ký thử + verify", ["Tạo document mẫu, ký thử và verify PDF trước khi dùng."]),
    ]
    px, py, pw, ph, pgap = 135, 790, 420, 185, 18
    for idx, (num, title, bullets) in enumerate(process_steps):
        x = px + idx * (pw + pgap)
        draw_step_box(draw, x, py, pw, ph, number=num, title=title, bullets=bullets, accent=theme["accent"])
        if idx < len(process_steps) - 1:
            arrow(draw, x + pw, py + ph // 2, x + pw + pgap, py + ph // 2, theme["accent2"])

    draw_band_panel(
        draw,
        90,
        1000,
        2380,
        195,
        title="Lưu ý khi deploy production cho ký số",
        bullets=[
            "Nên xem `legacy_internal` chỉ là cơ chế xác nhận nội bộ; production nên ưu tiên `pdf_pkcs7` để có ký số PDF đúng nghĩa.",
            "Sau khi setup xong phải ký thử, verify thử và kiểm tra quyền truy cập signed PDF trước khi trình diễn hoặc đưa vào dùng thật.",
        ],
        accent=theme["accent2"],
    )

    draw_takeaway(
        draw,
        "Khi thuyết trình phần deploy, ký số nên được xem là một subsystem riêng: cài dependency, cấu hình PKI/HSM, cấp credential và verify PDF sau setup.",
        theme["accent"],
    )
    return save(image, "09_co_che_ky_so_trong_he_thong.png")


def slide_testing() -> Path:
    image, draw, theme = new_slide("testing")
    draw_kicker(draw, "TECH CHOICE 10")
    draw_title(
        draw,
        "Kiểm thử hệ thống",
        "Codebase đã có lớp kiểm thử backend tự động cho nhiều vùng nghiệp vụ quan trọng. Đây là cơ sở để giảm regression khi chỉnh sửa các phần nhạy như AI, mailbox, tài liệu và ký số.",
    )
    draw_pills(draw, 90, 392, ["Unit + integration", "Django TestCase", "Regression control", "Luồng rủi ro cao"], theme["accent"], 1350)

    draw_metric_tile(
        draw,
        90,
        520,
        320,
        170,
        value="06",
        title="Nhóm test chính",
        subtitle="Auth, template, RAG, mailbox, signing và PKI.",
        accent=theme["accent"],
    )
    draw_metric_tile(
        draw,
        90,
        715,
        320,
        170,
        value="03",
        title="Vùng rủi ro cao",
        subtitle="AI retrieval, mailbox văn bản và ký số PDF.",
        accent=theme["accent2"],
    )
    draw_metric_tile(
        draw,
        90,
        910,
        320,
        170,
        value="01",
        title="Mục tiêu chính",
        subtitle="Phát hiện regression sớm khi sửa nghiệp vụ cốt lõi.",
        accent="#475569",
    )

    draw_shadow_card(draw, 470, 520, 2000, 260, WHITE, theme["accent2"])
    draw.text((500, 545), "Các file test tiêu biểu trong codebase", font=font(30, True), fill=theme["accent2"])
    draw.line((494, 595, 2438, 595), fill=theme["accent2"], width=2)
    draw_bullet_block(
        draw,
        500,
        620,
        [
            "api/tests_auth_profile.py: login và cập nhật hồ sơ người dùng.",
            "api/tests_templates.py: upload DOCX, render, export và duyệt template.",
            "ai_engine/tests_rag.py: search, sync signal và lệnh rebuild_rag_index.",
        ],
        900,
        accent=theme["accent2"],
        size=24,
        line_gap=5,
        item_gap=8,
    )
    draw.line((1460, 620, 1460, 744), fill="#D5DEE8", width=2)
    draw_bullet_block(
        draw,
        1510,
        620,
        [
            "documents/tests_mailbox.py: forward, preview và signed PDF trong mailbox.",
            "signing/tests.py: flow ký nhiều bước và quyền truy cập tài liệu đã ký.",
            "signing/tests_pki.py: PKCS#7, credential PKI và verify chữ ký số.",
        ],
        900,
        accent=theme["accent"],
        size=24,
        line_gap=5,
        item_gap=8,
    )

    cover_card = Card(
        470,
        840,
        960,
        300,
        "Những luồng đã được cover",
        [
            "Không chỉ test CRUD mà còn test quyền truy cập, integrity file và trạng thái quy trình.",
            "Các test đang bám vào đúng các vùng dễ hỏng khi thay đổi nghiệp vụ.",
        ],
        theme["accent2"],
    )
    value_card = Card(
        1510,
        840,
        960,
        300,
        "Giá trị đối với bảo trì hệ thống",
        [
            "Nhóm có thể sửa API, signing hoặc RAG tự tin hơn vì đã có điểm chặn regression.",
            "Đây là nền tảng để tiếp tục mở rộng CI, test tải hoặc UAT về sau.",
        ],
        theme["accent"],
    )
    draw_card(draw, cover_card)
    draw_card(draw, value_card)

    draw_takeaway(
        draw,
        "Điểm mạnh của phần kiểm thử là nó bám vào các luồng rủi ro cao, nên giá trị thực tế lớn hơn nhiều so với việc chỉ test giao diện bên ngoài.",
        theme["accent"],
    )
    return save(image, "10_kiem_thu_he_thong.png")


def slide_evaluation() -> Path:
    image, draw, theme = new_slide("evaluation")
    draw_kicker(draw, "TECH CHOICE 11")
    draw_title(
        draw,
        "Đánh giá hệ thống và hướng phát triển",
        "Sau khi hoàn thiện phiên bản hiện tại, có thể đánh giá hệ thống theo ba góc độ chính: mức đáp ứng nghiệp vụ, giá trị mà AI mang lại và khả năng đưa hệ thống tiến gần môi trường production.",
    )
    draw_pills(draw, 90, 392, ["Nghiệp vụ", "AI usefulness", "Triển khai thực tế", "Cần mở rộng thêm"], theme["accent"], 1300)

    draw_shadow_card(draw, 90, 510, 2380, 205, WHITE, theme["accent2"])
    draw.text((120, 540), "Ba trục đánh giá chính của hệ thống", font=font(30, True), fill=theme["accent2"])
    draw.line((120, 592, 2440, 592), fill=theme["accent2"], width=2)

    columns = [
        ("Nghiệp vụ", "Quản lý mẫu, văn bản, mailbox, ký số và admin đã về cùng một hệ thống."),
        ("AI", "RAG, AI Doc và Ollama đã tạo giá trị thực trong tra cứu và soạn thảo."),
        ("Triển khai", "Kiến trúc đã rõ, nhưng hạ tầng hiện vẫn ở mức demo."),
    ]
    positions = [130, 900, 1670]
    for idx, (title, body) in enumerate(columns):
        if idx > 0:
            draw.line((positions[idx] - 45, 620, positions[idx] - 45, 660), fill="#D7E0EA", width=3)
        draw.text((positions[idx], 615), title, font=font(26, True), fill=theme["accent"])
        draw_paragraph_block(draw, positions[idx], 642, body, 610, size=16, fill=TEXT, line_gap=1)

    cards = [
        Card(
            90,
            745,
            1140,
            210,
            "Kết quả đạt được",
            [
                "Đã kết nối quản lý mẫu, sinh văn bản, hỏi đáp RAG, ký số và admin trong một quy trình end-to-end.",
                "Mô hình đủ rõ để minh họa giá trị của AI agent trong quản lý văn bản doanh nghiệp.",
            ],
            theme["accent"],
        ),
        Card(
            1330,
            745,
            1140,
            210,
            "Giới hạn hiện tại",
            [
                "Hạ tầng truy cập vẫn dựa vào ngrok nên chưa là môi trường production chính thức.",
                "Hiệu năng AI còn phụ thuộc cấu hình máy chạy Ollama và chưa có kiểm thử tải lớn.",
            ],
            theme["accent2"],
        ),
        Card(
            90,
            990,
            1140,
            210,
            "Ưu tiên ngắn hạn",
            [
                "Chuyển sang VPS và domain riêng để ổn định lớp truy cập.",
                "Bổ sung monitoring, backup chuẩn hóa và kiểm thử bảo mật cơ bản.",
            ],
            theme["accent2"],
        ),
        Card(
            1330,
            990,
            1140,
            210,
            "Hướng phát triển tiếp",
            [
                "Mở rộng đánh giá bằng UAT với người dùng thật trong doanh nghiệp.",
                "Bổ sung benchmark AI, test tải và dashboard giám sát vận hành.",
            ],
            theme["accent"],
        ),
    ]
    for card in cards:
        draw_card(draw, card)

    draw_takeaway(
        draw,
        "Tổng thể, hệ thống đã đạt mức prototype doanh nghiệp khá hoàn chỉnh; bước tiếp theo là chuẩn hóa hạ tầng, tăng kiểm thử và tối ưu hiệu năng để tiến gần production.",
        theme["accent"],
    )
    return save(image, "11_danh_gia_he_thong_va_huong_phat_trien.png")


def slide_security() -> Path:
    image, draw, theme = new_slide("security")
    draw_kicker(draw, "TECH CHOICE 12")
    draw_title(
        draw,
        "Đánh giá kiểm thử bảo mật",
        "Ở mức rà soát và kiểm thử cơ bản, hệ thống chưa cho thấy dấu hiệu lỗi nghiêm trọng ở các lỗ hổng phổ biến. Tuy vậy, đây chưa phải pentest chuyên sâu cho toàn bộ nghiệp vụ; vì thế phần bảo mật nên được trình bày như một đánh giá tạm thời và có định hướng kiểm thử tiếp theo.",
    )
    draw_pills(draw, 90, 392, ["XSS", "SQL injection", "Business logic", "Cần pentest sâu"], theme["accent"], 1250)

    hero = Card(
        90,
        510,
        2380,
        180,
        "Nhận định hiện tại ở mức rà soát cơ bản",
        [
            "Chưa thấy dấu hiệu lỗi nghiêm trọng ở các lỗ hổng phổ biến như XSS hay SQL injection trong kiểm tra ban đầu.",
            "Tuy nhiên kết luận này mới dừng ở mức sơ bộ; hệ thống chưa được pentest sâu theo từng nghiệp vụ đặc thù.",
        ],
        theme["accent2"],
    )
    draw_card(draw, hero)

    risk_cards = [
        Card(
            90,
            735,
            740,
            300,
            "XSS / HTML injection",
            [
                "UI chính bằng Flutter Web làm giảm bề mặt chèn HTML trực tiếp ở phần lớn màn hình mới.",
                "Tuy vậy repo vẫn còn một số màn HTML/JS legacy dùng `innerHTML`, nên vẫn cần test stored/reflected XSS kỹ hơn.",
            ],
            theme["accent"],
        ),
        Card(
            910,
            735,
            740,
            300,
            "SQL injection",
            [
                "Phần lớn API dựa trên Django ORM nên rủi ro SQL injection phổ biến tạm thời không nổi bật.",
                "Dù vậy vẫn có một số truy vấn SQL kỹ thuật ở lớp vector index, nên cần review thêm đường đi dữ liệu và input.",
            ],
            theme["accent2"],
        ),
        Card(
            1730,
            735,
            740,
            300,
            "Nghiệp vụ chuyên sâu",
            [
                "Chưa test sâu các luồng như ký số, guest portal, upload tài liệu, AI prompt flow, mailbox và permission theo trạng thái.",
                "Đây mới là nhóm rủi ro cần kiểm thử chuyên sâu hơn trong giai đoạn tiếp theo.",
            ],
            theme["accent"],
        ),
    ]
    for card in risk_cards:
        draw_card(draw, card)

    next_card = Card(
        90,
        1070,
        2380,
        130,
        "Đề xuất kiểm thử tiếp theo",
        [
            "Thực hiện pentest chuyên sâu hơn cho XSS, upload file, permission bypass, IDOR, luồng ký số và các nghiệp vụ có AI hoặc guest access.",
        ],
        theme["accent2"],
    )
    draw_card(draw, next_card)

    draw_takeaway(
        draw,
        "Cách trình bày phù hợp là: hệ thống tạm thời chưa thấy lỗi phổ biến ở mức kiểm tra cơ bản, nhưng vẫn cần một vòng kiểm thử bảo mật chuyên sâu hơn trước khi kết luận chắc chắn.",
        theme["accent"],
    )
    return save(image, "12_danh_gia_kiem_thu_bao_mat.png")


def preview_extra(paths: list[Path]) -> Path:
    image = Image.new("RGBA", (2560, 2160), "#F7F9FC")
    draw = ImageDraw.Draw(image)
    draw.text((70, 54), "Bo slide mo rong - 6 slide layout khac nhau", font=TITLE_FONT, fill=TEXT)
    draw.text((70, 124), "Bo nay gom domain, VPS, ky so, test, danh gia va kiem thu bao mat.", font=SUBTITLE_FONT, fill=MUTED)
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
    return save(image, "07_12_preview_bo_slide_mo_rong.png")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    paths = [
        slide_domain_current(),
        slide_domain_future(),
        slide_signing(),
        slide_testing(),
        slide_evaluation(),
        slide_security(),
    ]
    preview_extra(paths)
    for path in paths:
        print(path)


if __name__ == "__main__":
    main()
