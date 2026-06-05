from __future__ import annotations

import argparse
import ast
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from nav_feature_manifest import FEATURE_BY_ID, FEATURE_BY_SLUG, FEATURES, FeatureSpec, PythonSpec


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "BAO_CAO_NAV_WEB"
APP_SHELL = ROOT / "flutter_frontend/lib/widgets/shell/app_shell.dart"
GUEST_SHELL = ROOT / "flutter_frontend/lib/widgets/shell/guest_shell.dart"
ROUTER_FILE = ROOT / "flutter_frontend/lib/core/router.dart"
API_URLS = ROOT / "api/urls.py"


DISPLAY_TITLES: dict[str, str] = {
    "Dashboard": "Bảng điều khiển",
    "Sinh van ban tu mau": "Sinh văn bản từ mẫu",
    "Hoi dap tai lieu": "Hỏi đáp tài liệu",
    "Tro ly AI": "Trợ lý AI",
    "Yeu cau ky": "Yêu cầu ký",
    "PDF da ky": "PDF đã ký",
    "Hom thu": "Hòm thư",
    "Uy quyen ky so": "Ủy quyền ký số",
    "Tao mau van ban": "Tạo mẫu văn bản",
    "Mau dung chung": "Mẫu dùng chung",
    "Mau phong ban cua toi": "Mẫu phòng ban của tôi",
    "Mau rieng cua toi": "Mẫu riêng của tôi",
    "Mau yeu thich": "Mẫu yêu thích",
    "Tat ca mau (Admin)": "Tất cả mẫu (Admin)",
    "Van ban cua toi": "Văn bản của tôi",
    "Van ban chia se trong nhom": "Văn bản chia sẻ trong nhóm",
    "Van ban chia se cong khai": "Văn bản chia sẻ công khai",
    "Van ban yeu thich": "Văn bản yêu thích",
    "Van ban da luu tru": "Văn bản đã lưu trữ",
    "Tat ca van ban (Admin)": "Tất cả văn bản (Admin)",
    "Thung rac": "Thùng rác",
    "Ho so ca nhan": "Hồ sơ cá nhân",
    "Yeu cau phe duyet": "Yêu cầu phê duyệt",
    "Cau hinh AI": "Cấu hình AI",
    "Tai khoan, phong ban va nhom": "Tài khoản, phòng ban và nhóm",
    "Sao luu du lieu": "Sao lưu dữ liệu",
    "Guest tao van ban": "Guest tạo văn bản",
    "Guest xem van ban vua tao": "Guest xem văn bản vừa tạo",
}


VI_REPLACEMENTS: tuple[tuple[str, str], ...] = (
    ("Chi hien khi user co quyen HR delegation hoac accounting delegation", "Chỉ hiện khi user có quyền HR delegation hoặc accounting delegation"),
    ("Muc nay chi duoc bao cao vi dang co tren nav va nguoi dung co the su dung o runtime hien tai.", "Mục này chỉ được báo cáo vì đang có trên nav và người dùng có thể sử dụng ở runtime hiện tại."),
    ("Luu y: so do duoc dung de doi chieu; line number va runtime file trong tai lieu nay uu tien source code nav/router hien tai.", "Lưu ý: sơ đồ được dùng để đối chiếu; line number và runtime file trong tài liệu này ưu tiên source code nav/router hiện tại."),
    ("Chi hien khi guest da co document vua tao", "Chỉ hiện khi guest đã có document vừa tạo"),
    ("Chi user co `canApprovePending == true`", "Chỉ user có `canApprovePending == true`"),
    ("Chi user co `isStaff == true`", "Chỉ user có `isStaff == true`"),
    ("Moi tai khoan da dang nhap", "Mọi tài khoản đã đăng nhập"),
    ("Moi guest truoc dang nhap", "Mọi guest trước đăng nhập"),
    ("Tat ca van ban (Admin)", "Tất cả văn bản (Admin)"),
    ("Tat ca mau (Admin)", "Tất cả mẫu (Admin)"),
    ("Tai khoan, phong ban va nhom", "Tài khoản, phòng ban và nhóm"),
    ("Guest xem van ban vua tao", "Guest xem văn bản vừa tạo"),
    ("Guest tao van ban", "Guest tạo văn bản"),
    ("Sao luu du lieu", "Sao lưu dữ liệu"),
    ("Yeu cau phe duyet", "Yêu cầu phê duyệt"),
    ("Ho so ca nhan", "Hồ sơ cá nhân"),
    ("Thung rac", "Thùng rác"),
    ("Van ban da luu tru", "Văn bản đã lưu trữ"),
    ("Van ban yeu thich", "Văn bản yêu thích"),
    ("Van ban chia se cong khai", "Văn bản chia sẻ công khai"),
    ("Van ban chia se trong nhom", "Văn bản chia sẻ trong nhóm"),
    ("Van ban cua toi", "Văn bản của tôi"),
    ("Mau phong ban cua toi", "Mẫu phòng ban của tôi"),
    ("Mau rieng cua toi", "Mẫu riêng của tôi"),
    ("Mau dung chung", "Mẫu dùng chung"),
    ("Mau yeu thich", "Mẫu yêu thích"),
    ("Tao mau van ban", "Tạo mẫu văn bản"),
    ("Uy quyen ky so", "Ủy quyền ký số"),
    ("Hom thu", "Hòm thư"),
    ("Yeu cau ky", "Yêu cầu ký"),
    ("Sinh van ban tu mau", "Sinh văn bản từ mẫu"),
    ("Hoi dap tai lieu", "Hỏi đáp tài liệu"),
    ("Tro ly AI", "Trợ lý AI"),
    ("Cau hinh AI", "Cấu hình AI"),
    ("Digital signing", "Ký số"),
    ("Document management", "Quản lý văn bản"),
    ("Guest documents", "Văn bản guest"),
    ("Administration", "Quản trị"),
    ("Approvals", "Phê duyệt"),
    ("Templates", "Mẫu văn bản"),
    ("Documents", "Văn bản"),
    ("System", "Hệ thống"),
    ("Top level", "Cấp điều hướng chính"),
    ("Nguoi dung", "Người dùng"),
    ("Nguon su that", "Nguồn sự thật"),
    ("Dieu kien xuat hien tren nav", "Điều kiện xuất hiện trên nav"),
    ("Route chinh va route con", "Route chính và route con"),
    ("Route chinh", "Route chính"),
    ("Route con cung flow", "Route con cùng flow"),
    ("Tep runtime chinh", "Tệp runtime chính"),
    ("Tep lien quan", "Tệp liên quan"),
    ("Danh sach ham / method / provider / endpoint phuc vu chuc nang", "Danh sách hàm / method / provider / endpoint phục vụ chức năng"),
    ("Luong tuan tu chi tiet", "Luồng tuần tự chi tiết"),
    ("So do tuan tu tham chieu", "Sơ đồ tuần tự tham chiếu"),
    ("Tong so chuc nang", "Tổng số chức năng"),
    ("Muc luc chuc nang nav web dang su dung", "Mục lục chức năng nav web đang sử dụng"),
    ("Hien cho", "Hiện cho"),
    ("Nhom nav", "Nhóm nav"),
    ("Chuc nang", "Chức năng"),
    ("Ten chuc nang", "Tên chức năng"),
    ("Ho so", "Hồ sơ"),
    ("So do", "Sơ đồ"),
    ("Pham vi", "Phạm vi"),
    ("Dang ", "Đang "),
    ("dang ", "đang "),
    ("mo nav", "mở nav"),
    ("mo route", "mở route"),
    ("vao nav", "vào nav"),
    ("de xem", "để xem"),
    ("de vao", "để vào"),
    ("de chon", "để chọn"),
    ("de quan ly", "để quản lý"),
    ("de tao", "để tạo"),
    ("de mo lai", "để mở lại"),
    ("de tiep tuc", "để tiếp tục"),
    ("de lay", "để lấy"),
    ("de user", "để user"),
    ("goi endpoint", "gọi endpoint"),
    (" goi ", " gọi "),
    ("chi tiet", "chi tiết"),
    ("danh sach", "danh sách"),
    ("van ban", "văn bản"),
    ("tai lieu", "tài liệu"),
    ("phong ban", "phòng ban"),
    ("nhom", "nhóm"),
    ("rieng", "riêng"),
    ("yeu thich", "yêu thích"),
    ("cong khai", "công khai"),
    ("luu tru", "lưu trữ"),
    ("luu chuyen", "lưu chuyển"),
    ("bo loc", "bộ lọc"),
    ("du lieu", "dữ liệu"),
    ("nghiep vu", "nghiệp vụ"),
    ("thao tac", "thao tác"),
    ("trang thai", "trạng thái"),
    ("hien thi", "hiển thị"),
    ("hien co", "hiện có"),
    ("hien tai", "hiện tại"),
    ("co the", "có thể"),
    ("duoc", "được"),
    ("quyen", "quyền"),
    ("moi nhat", "mới nhất"),
    ("tao moi", "tạo mới"),
    ("tao document", "tạo document"),
    ("tai danh sach", "tải danh sách"),
    ("tai du lieu", "tải dữ liệu"),
    ("tai summary", "tải summary"),
    ("tai metadata", "tải metadata"),
    ("tai session", "tải session"),
    ("tai lich su", "tải lịch sử"),
    ("tai context", "tải context"),
    ("tai profile", "tải profile"),
    ("tai thread", "tải thread"),
    ("tai config", "tải config"),
    ("tai KPI", "tải KPI"),
    ("tai payload", "tải payload"),
    ("tai bo loc", "tải bộ lọc"),
    ("xu ly", "xử lý"),
    ("tong quan", "tổng quan"),
    ("he thong", "hệ thống"),
    ("ho tro", "hỗ trợ"),
    ("doi tuong", "đối tượng"),
    ("xem truoc", "xem trước"),
    ("tai file", "tải file"),
    ("quay ve", "quay về"),
    ("vua tao", "vừa tạo"),
    ("Van ban vua tao", "Văn bản vừa tạo"),
    ("van ban vua tao", "văn bản vừa tạo"),
    ("dang cho", "đang chờ"),
    ("phu trach", "phụ trách"),
    ("dai dien", "đại diện"),
    ("dieu phoi", "điều phối"),
    ("giu state", "giữ state"),
    ("man hinh", "màn hình"),
    ("giao dien", "giao diện"),
    ("ket hop", "kết hợp"),
    ("bam", "bấm"),
    ("mo 1", "mở 1"),
    ("mo node", "mở node"),
    ("mo lai", "mở lại"),
    ("mo sang", "mở sang"),
    ("mo chi tiet", "mở chi tiết"),
    ("mo flow", "mở flow"),
    ("mo ra", "mở ra"),
    ("mo route", "mở route"),
    ("mo ", "mở "),
    ("goi ", "gọi "),
    ("goi.", "gọi."),
    ("lay ", "lấy "),
    ("loc ", "lọc "),
    ("mo ta", "mô tả"),
    ("danh sach", "danh sách"),
    ("vao ", "vào "),
    ("chon ", "chọn "),
    ("man ", "màn "),
    ("dien bien", "điền biến"),
    ("ho so", "hồ sơ"),
    ("cong ty", "công ty"),
    ("la trung tam", "là trung tâm"),
    ("la ", "là "),
    ("cung cap", "cung cấp"),
    ("sau do", "sau đó"),
    ("hoac", "hoặc"),
    ("doc/ghi", "đọc/ghi"),
    ("hop le", "hợp lệ"),
    ("phan ", "phần "),
    ("cau hinh", "cấu hình"),
    ("thong bao", "thông báo"),
    ("thong tin", "thông tin"),
    ("hien khong co", "hiện không có"),
    ("route do", "route đó"),
    ("hien muc", "hiện mục"),
    ("bao cao", "báo cáo"),
    ("bi khoa", "bị khóa"),
    ("cong tao", "cổng tạo"),
    ("dang nhap", "đăng nhập"),
    ("doc session", "đọc session"),
    ("pham vi", "phạm vi"),
    ("qua trinh", "quá trình"),
    ("ghi ", "ghi "),
    ("tra ", "trả "),
    ("hien ", "hiện "),
    ("moi ", "mới "),
    ("mau ", "mẫu "),
    ("noi dung", "nội dung"),
    ("bien", "biến"),
    ("ky ", "ký "),
    ("can ky", "cần ký"),
    (" de ", " để "),
    (" de.", " để."),
    (" de,", " để,"),
    (" de;", " để;"),
    ("De ", "Để "),
    (" do ", " đó "),
    (" do.", " đó."),
    (" do,", " đó,"),
    (" chi ", " chỉ "),
    ("Chi ", "Chỉ "),
    ("nay", "này"),
    ("phep", "phép"),
    ("nhin thay", "nhìn thấy"),
    ("cap nhat", "cập nhật"),
    ("thanh cong", "thành công"),
    ("that bai", "thất bại"),
    ("quan ly", "quản lý"),
    ("tam", "tạm"),
    ("dau vao", "đầu vào"),
    ("dau ra", "đầu ra"),
    ("tong hop", "tổng hợp"),
    ("tim kiem", "tìm kiếm"),
    ("nhu", "như"),
    ("PDF/anh", "PDF/ảnh"),
    ("document that", "document thật"),
    ("nhat", "nhất"),
    ("thuc hien", "thực hiện"),
    ("xac thuc", "xác thực"),
    ("nhung", "những"),
    ("muc can", "mục cần"),
    ("muc nay", "mục này"),
    ("co ", "có "),
    ("khi ", "khi "),
    (" va ", " và "),
    (" tu ", " từ "),
    (" vi route ", " vì route "),
    (" vi cac ", " vì các "),
    (" vi co ", " vì có "),
    (" ma ", " mà "),
    ("tren nav", "trên nav"),
    ("tren ", "trên "),
    ("bao gom", "bao gồm"),
    ("muc ", "mục "),
    ("cac ", "các "),
    ("tao ", "tạo "),
    ("luu ", "lưu "),
    ("tuong ung", "tương ứng"),
    ("thuc thi", "thực thi"),
    ("thay duoc", "thấy được"),
    ("Chi 2 muc", "Chỉ 2 mục"),
    ("Chi 2", "Chỉ 2"),
    ("Khi user", "Khi người dùng"),
    ("User ", "Người dùng "),
    (" user ", " người dùng "),
    ("Feature nay", "Chức năng này"),
    ("quan tri", "quản trị"),
    ("tai ve", "tải về"),
    ("thay doi", "thay đổi"),
    ("dang ky", "đăng ký"),
    ("nhan su", "nhân sự"),
    ("hang loat", "hàng loạt"),
    ("Chi man", "Chỉ màn"),
    ("Chi chuc nang", "Chỉ chức năng"),
    ("Khong", "Không"),
    ("khong", "không"),
    ("nguoi dung", "người dùng"),
    ("moi thao tac", "mọi thao tác"),
    ("Moi thao tac", "Mọi thao tác"),
    ("moi hanh dong", "mỗi hành động"),
    ("duoc tao", "được tạo"),
    ("duoc dung cho", "được dùng cho"),
    ("loc dung task", "lọc đúng task"),
    ("dung scope", "đúng scope"),
    ("can dung", "cần dùng"),
    ("can thiet", "cần thiết"),
    ("khong can", "không cần"),
    ("bo sung", "bổ sung"),
    ("ap dung", "áp dụng"),
    ("Toan bo", "Toàn bộ"),
    ("pham vi cookie/session", "phạm vi cookie/session"),
    ("biet", "biết"),
    ("Man ", "Màn "),
    ("tung ", "từng "),
    ("vai tro", "vai trò"),
    ("dac biet", "đặc biệt"),
    ("dac thu", "đặc thù"),
    ("dua vao", "đưa vào"),
    ("voi ", "với "),
    ("Neu ", "Nếu "),
    ("neu co", "nếu có"),
    ("hanh dong", "hành động"),
    ("khoi dong", "khởi động"),
    ("ghi nhan", "ghi nhận"),
    ("liet ke", "liệt kê"),
    ("cung mien", "cùng miền"),
    ("quy tac", "quy tắc"),
    ("ban sao luu moi", "bản sao lưu mới"),
    ("thong ke", "thống kê"),
    ("xoa ", "xóa "),
    ("nap lai", "nạp lại"),
    ("cho phep", "cho phép"),
    ("gui ", "gửi "),
    ("su dung", "sử dụng"),
    ("thanh vien", "thành viên"),
    ("len backend", "lên backend"),
)


def beautify_text(text: str) -> str:
    segments = text.split("`")
    replacements = sorted(VI_REPLACEMENTS, key=lambda item: len(item[0]), reverse=True)
    for index in range(0, len(segments), 2):
        segment = segments[index]
        for source, target in replacements:
            segment = segment.replace(source, target)
        segments[index] = segment
    return "`".join(segments)


def display_title(feature: FeatureSpec) -> str:
    return DISPLAY_TITLES.get(feature.title, beautify_text(feature.title))


def display_sequence_step(feature: FeatureSpec, step: str) -> str:
    normalized = step.replace("`%s`" % feature.title, "`%s`" % display_title(feature))
    return beautify_text(normalized)


@dataclass(frozen=True)
class BasicLineRef:
    label: str
    path: str
    line: int
    kind: str
    layer: str
    role: str
    flow_step: str


@dataclass(frozen=True)
class PythonSymbol:
    name: str
    qualname: str
    kind: str
    lineno: int
    end_lineno: int
    calls: tuple[str, ...]


@dataclass
class PythonIndex:
    path: str
    by_name: dict[str, list[PythonSymbol]]
    by_qualname: dict[str, list[PythonSymbol]]

    def resolve(self, name: str) -> PythonSymbol | None:
        if "." in name:
            candidates = self.by_qualname.get(name, [])
            return candidates[-1] if candidates else None
        candidates = self.by_name.get(name, [])
        return candidates[-1] if candidates else None

    def closure(self, roots: Iterable[str], helpers: Iterable[str], follow_calls: bool) -> list[PythonSymbol]:
        queue: list[PythonSymbol] = []
        seen: set[str] = set()
        for item in list(roots) + list(helpers):
            symbol = self.resolve(item)
            if symbol is not None and symbol.qualname not in seen:
                seen.add(symbol.qualname)
                queue.append(symbol)
        ordered = list(queue)
        if not follow_calls:
            return sorted(ordered, key=lambda item: (item.lineno, item.qualname))
        cursor = 0
        while cursor < len(ordered):
            current = ordered[cursor]
            cursor += 1
            for called_name in current.calls:
                target = self.resolve(called_name)
                if target is None:
                    continue
                if target.qualname in seen:
                    continue
                seen.add(target.qualname)
                ordered.append(target)
        return sorted(ordered, key=lambda item: (item.lineno, item.qualname))


@dataclass(frozen=True)
class DartSymbol:
    name: str
    kind: str
    line: int
    container: str | None = None


@dataclass
class DartIndex:
    path: str
    classes: list[DartSymbol]
    methods: list[DartSymbol]
    functions: list[DartSymbol]
    providers: list[DartSymbol]

    def screen_symbols(self) -> list[DartSymbol]:
        selected_class_names = {
            symbol.name
            for symbol in self.classes
            if "Screen" in symbol.name or "Dialog" in symbol.name
        }
        symbols: list[DartSymbol] = []
        symbols.extend(sorted((item for item in self.functions), key=lambda item: item.line))
        symbols.extend(sorted((item for item in self.classes if item.name in selected_class_names), key=lambda item: item.line))
        symbols.extend(
            sorted(
                (
                    item
                    for item in self.methods
                    if item.container in selected_class_names
                ),
                key=lambda item: item.line,
            )
        )
        return symbols

    def provider_symbols(self) -> list[DartSymbol]:
        class_names = {item.name for item in self.classes}
        symbols: list[DartSymbol] = []
        symbols.extend(sorted(self.providers, key=lambda item: item.line))
        symbols.extend(sorted(self.functions, key=lambda item: item.line))
        symbols.extend(sorted(self.classes, key=lambda item: item.line))
        symbols.extend(sorted((item for item in self.methods if item.container in class_names), key=lambda item: item.line))
        return symbols


class PythonCollector(ast.NodeVisitor):
    def __init__(self) -> None:
        self.stack: list[str] = []
        self.by_name: dict[str, list[PythonSymbol]] = {}
        self.by_qualname: dict[str, list[PythonSymbol]] = {}

    def _add(self, symbol: PythonSymbol) -> None:
        self.by_name.setdefault(symbol.name, []).append(symbol)
        self.by_qualname.setdefault(symbol.qualname, []).append(symbol)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:  # noqa: N802
        qualname = ".".join(self.stack + [node.name]) if self.stack else node.name
        self._add(
            PythonSymbol(
                name=node.name,
                qualname=qualname,
                kind="class",
                lineno=node.lineno,
                end_lineno=node.end_lineno or node.lineno,
                calls=(),
            )
        )
        self.stack.append(node.name)
        self.generic_visit(node)
        self.stack.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:  # noqa: N802
        self._visit_function(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:  # noqa: N802
        self._visit_function(node)

    def _visit_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        qualname = ".".join(self.stack + [node.name]) if self.stack else node.name
        kind = "method" if self.stack and self.stack[-1] and self.stack[-1][0].isupper() else "function"
        calls = tuple(sorted(_collect_calls(node)))
        self._add(
            PythonSymbol(
                name=node.name,
                qualname=qualname,
                kind=kind,
                lineno=node.lineno,
                end_lineno=node.end_lineno or node.lineno,
                calls=calls,
            )
        )
        self.stack.append(node.name)
        self.generic_visit(node)
        self.stack.pop()


def _collect_calls(node: ast.AST) -> set[str]:
    names: set[str] = set()

    class _CallVisitor(ast.NodeVisitor):
        def visit_Call(self, call_node: ast.Call) -> None:  # noqa: N802
            func = call_node.func
            if isinstance(func, ast.Name):
                names.add(func.id)
            elif isinstance(func, ast.Attribute):
                names.add(func.attr)
            self.generic_visit(call_node)

        def visit_FunctionDef(self, inner_node: ast.FunctionDef) -> None:  # noqa: N802
            if inner_node is node:
                self.generic_visit(inner_node)

        def visit_AsyncFunctionDef(self, inner_node: ast.AsyncFunctionDef) -> None:  # noqa: N802
            if inner_node is node:
                self.generic_visit(inner_node)

        def visit_ClassDef(self, _: ast.ClassDef) -> None:  # noqa: N802
            return

    _CallVisitor().visit(node)
    return names


def parse_python_file(path: str) -> PythonIndex:
    source_path = ROOT / path
    tree = ast.parse(source_path.read_text(encoding="utf-8"))
    collector = PythonCollector()
    collector.visit(tree)
    return PythonIndex(path=path, by_name=collector.by_name, by_qualname=collector.by_qualname)


CLASS_RE = re.compile(r"^class\s+([A-Za-z_]\w*)")
PROVIDER_RE = re.compile(r"^final\s+([A-Za-z_]\w*Provider)\s*=")
TOP_LEVEL_FUNCTION_RE = re.compile(
    r"^(?:Future<[^>]+>|Future<void>|Future|void|Widget|String|int|double|bool|num|Map<[^>]+>|List<[^>]+>|Uint8List\??|State<[^>]+>|[A-Z_][\w<>, ?]+)\s+([A-Za-z_]\w*)\s*\("
)
METHOD_RE = re.compile(
    r"^\s{2}(?:static\s+)?(?:Future<[^>]+>|Future<void>|Future|void|Widget|String|int|double|bool|num|Map<[^>]+>|List<[^>]+>|Uint8List\??|State<[^>]+>|[A-Z_][\w<>, ?]+)\s+([A-Za-z_]\w*)\s*\("
)


def parse_dart_file(path: str) -> DartIndex:
    source_path = ROOT / path
    lines = source_path.read_text(encoding="utf-8").splitlines()
    classes: list[DartSymbol] = []
    methods: list[DartSymbol] = []
    functions: list[DartSymbol] = []
    providers: list[DartSymbol] = []

    brace_depth = 0
    current_class: str | None = None
    current_class_depth = 0

    for lineno, line in enumerate(lines, start=1):
        stripped = line.strip()
        if current_class is not None and brace_depth < current_class_depth:
            current_class = None
            current_class_depth = 0

        class_match = CLASS_RE.match(stripped)
        if class_match:
            current_class = class_match.group(1)
            classes.append(DartSymbol(name=current_class, kind="class", line=lineno))

        provider_match = PROVIDER_RE.match(stripped)
        if provider_match and line == stripped:
            providers.append(DartSymbol(name=provider_match.group(1), kind="provider", line=lineno))

        function_match = TOP_LEVEL_FUNCTION_RE.match(stripped)
        if function_match and line == stripped:
            functions.append(DartSymbol(name=function_match.group(1), kind="function", line=lineno))

        if current_class is not None:
            method_match = METHOD_RE.match(line)
            if method_match:
                methods.append(
                    DartSymbol(
                        name=method_match.group(1),
                        kind="method",
                        line=lineno,
                        container=current_class,
                    )
                )

        depth_delta = line.count("{") - line.count("}")
        brace_depth += depth_delta
        if class_match:
            current_class_depth = brace_depth
        if current_class is not None and brace_depth < current_class_depth:
            current_class = None
            current_class_depth = 0

    return DartIndex(
        path=path,
        classes=classes,
        methods=methods,
        functions=functions,
        providers=providers,
    )


def capture_call_blocks(path: Path, token: str) -> list[tuple[int, str]]:
    lines = path.read_text(encoding="utf-8").splitlines()
    blocks: list[tuple[int, str]] = []
    index = 0
    while index < len(lines):
        line = lines[index]
        if token not in line:
            index += 1
            continue
        start = index
        balance = line.count("(") - line.count(")")
        cursor = index
        while balance > 0 and cursor + 1 < len(lines):
            cursor += 1
            next_line = lines[cursor]
            balance += next_line.count("(") - next_line.count(")")
        blocks.append((start + 1, "\n".join(lines[start:cursor + 1])))
        index = cursor + 1
    return blocks


def extract_nav_items(path: Path, shell: str) -> list[tuple[str, str | None, int]]:
    items: list[tuple[str, str | None, int]] = []
    for line_no, block in capture_call_blocks(path, "navTile("):
        if "locked: true" in block:
            continue
        route_match = re.search(r"route:\s*'([^']+)'", block)
        route = route_match.group(1) if route_match else None
        if route is None:
            literals = re.findall(r"'(/[^']*)'", block)
            route = literals[-1] if literals else None
        if route is None:
            continue
        if shell == "app" and route == "/chat/voice":
            continue
        query_match = re.search(r"query:\s*'([^']+)'", block)
        items.append((route, query_match.group(1) if query_match else None, line_no))
    return items


def discover_nav_inventory() -> dict[tuple[str, str | None, str], int]:
    inventory: dict[tuple[str, str | None, str], int] = {}
    for route, query, line_no in extract_nav_items(APP_SHELL, "app"):
        inventory[(route, query, "app")] = line_no
    for route, query, line_no in extract_nav_items(GUEST_SHELL, "guest"):
        inventory[(route, query, "guest")] = line_no
    return inventory


def find_line_with_snippets(path: str, snippets: Iterable[str]) -> int:
    lines = (ROOT / path).read_text(encoding="utf-8").splitlines()
    snippet_list = list(snippets)
    for lineno, line in enumerate(lines, start=1):
        if all(snippet in line for snippet in snippet_list):
            return lineno
    raise ValueError("Could not find line in %s with snippets %s" % (path, snippet_list))


def humanize_symbol(name: str) -> str:
    parts = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", name).replace("_", " ").split()
    if not parts:
        return name
    return " ".join(part.lower() for part in parts)


def flow_step_for_symbol(layer: str, name: str, kind: str) -> str:
    lower_name = name.lower()
    if layer == "Nav":
        return "Bước mở chức năng từ thanh nav"
    if layer == "Router":
        return "Bước chọn route và tải màn hình"
    if layer == "API URL":
        return "Bước map request frontend sang backend"
    if kind == "class":
        return "Bước tổ chức state và vùng giao diện"
    if name == "createState":
        return "Bước tạo state cho màn hình"
    if lower_name == "initstate":
        return "Bước khởi động và nạp dữ liệu ban đầu"
    if lower_name == "dispose":
        return "Bước dọn dẹp tài nguyên khi rời màn"
    if any(token in lower_name for token in ("initstate", "load", "refresh", "provider", "sessions", "summary", "list")):
        return "Bước nạp dữ liệu ban đầu"
    if any(token in lower_name for token in ("build", "panel", "layout", "card", "chip", "badge")):
        return "Bước dựng giao diện và hiển thị kết quả"
    if any(token in lower_name for token in ("send", "query", "turn", "message", "chat", "prefill", "parse", "extract")):
        return "Bước gửi yêu cầu và xử lý nội dung"
    if any(token in lower_name for token in ("create", "save", "patch", "submit", "import", "generate", "replace")):
        return "Bước tạo mới hoặc lưu thay đổi"
    if any(token in lower_name for token in ("approve", "reject", "sign", "verify", "complete", "forward")):
        return "Bước thao tác nghiệp vụ trên đối tượng đang xử lý"
    if any(token in lower_name for token in ("download", "preview", "export")):
        return "Bước xem trước hoặc tải file"
    if any(token in lower_name for token in ("archive", "unarchive", "favorite", "restore", "delete")):
        return "Bước đổi trạng thái đối tượng"
    return "Bước phụ trợ luồng chính"


def role_for_dart_symbol(feature: FeatureSpec, symbol: DartSymbol, source_path: str) -> str:
    name = symbol.name
    title = display_title(feature)
    if symbol.kind == "provider":
        return "Provider `%s` cấp dữ liệu, trigger HTTP call hoặc invalidate state cho chức năng `%s`." % (name, title)
    if symbol.kind == "class":
        if "/providers/" in source_path and name.endswith("Params"):
            return "Lớp `%s` đóng vai trò payload tham số để provider gọi đúng API cho chức năng `%s`." % (name, title)
        if "/providers/" in source_path and "Version" in name:
            return "Lớp `%s` mô tả shape dữ liệu/version mà provider dùng để hiển thị chức năng `%s`." % (name, title)
        if "State" in name:
            return "Lớp state `%s` giữ state runtime và điều phối hành động trên màn `%s`." % (name, title)
        if "Dialog" in name:
            return "Lớp `%s` dùng dialog/phụ trợ thao tác chi tiết trong chức năng `%s`." % (name, title)
        return "Lớp `%s` đại diện màn hình/chiều giao diện chính của chức năng `%s`." % (name, title)
    if symbol.kind == "function":
        return "Hàm top-level `%s` hỗ trợ thao tác đặc thù của file `%s` cho chức năng `%s`." % (name, source_path, title)
    action = humanize_symbol(name)
    return "Phương thức `%s` phụ trách `%s` trong flow `%s`." % (name, action, title)


def role_for_python_symbol(feature: FeatureSpec, symbol: PythonSymbol, source_path: str, layer: str) -> str:
    name = symbol.name
    action = humanize_symbol(name)
    title = display_title(feature)
    if symbol.kind == "class":
        return "Lớp `%s` trong `%s` đóng vai trò container lỗi nghiệp vụ/phát sinh lỗi cho flow `%s`." % (name, source_path, title)
    if layer == "Backend View":
        if name.startswith("_"):
            return "Hàm phụ backend `%s` hỗ trợ xử lý `%s` để endpoint của chức năng `%s` trả kết quả đúng cho web." % (name, action, title)
        return "Endpoint `%s` là điểm vào backend cho chức năng `%s`, phụ trách `%s` và trả response cho frontend." % (name, title, action)
    if layer == "Service/Domain":
        if name.startswith("_"):
            return "Hàm phụ service `%s` thực thi bước `%s` để flow `%s` hoàn tất đúng quy tắc nghiệp vụ." % (name, action, title)
        return "Hàm service `%s` thực thi nghiệp vụ `%s` ở tầng service/domain để hoàn tất flow `%s`." % (name, action, title)
    return "Ký hiệu `%s` trong `%s` phụ trợ `%s` cho chức năng `%s`." % (name, source_path, action, title)


def role_for_nav(feature: FeatureSpec) -> str:
    return "Dòng nav này render mục `%s` và cho phép người dùng mở đúng flow đang được sử dụng hiện tại." % display_title(feature)


def role_for_route(feature: FeatureSpec) -> str:
    return "Khai báo GoRoute này ánh xạ URL `%s` sang màn hình runtime của chức năng `%s`." % (feature.route, display_title(feature))


def role_for_api_url(feature: FeatureSpec, path_fragment: str, view_name: str) -> str:
    return "Dòng URL này map request `%s` sang view `%s` để phục vụ chức năng `%s`." % (path_fragment, view_name, display_title(feature))


def collect_screen_refs(feature: FeatureSpec) -> list[BasicLineRef]:
    refs: list[BasicLineRef] = []
    for path in feature.screen_files:
        index = parse_dart_file(path)
        for symbol in index.screen_symbols():
            label = symbol.name if symbol.container is None else "%s.%s" % (symbol.container, symbol.name)
            refs.append(
                BasicLineRef(
                    label=label,
                    path=path,
                    line=symbol.line,
                    kind=symbol.kind,
                    layer="UI Screen",
                    role=role_for_dart_symbol(feature, symbol, path),
                    flow_step=flow_step_for_symbol("UI Screen", symbol.name, symbol.kind),
                )
            )
    return refs


def collect_provider_refs(feature: FeatureSpec) -> list[BasicLineRef]:
    refs: list[BasicLineRef] = []
    for path in feature.provider_files:
        index = parse_dart_file(path)
        for symbol in index.provider_symbols():
            label = symbol.name if symbol.container is None else "%s.%s" % (symbol.container, symbol.name)
            refs.append(
                BasicLineRef(
                    label=label,
                    path=path,
                    line=symbol.line,
                    kind=symbol.kind,
                    layer="Provider/Client",
                    role=role_for_dart_symbol(feature, symbol, path),
                    flow_step=flow_step_for_symbol("Provider/Client", symbol.name, symbol.kind),
                )
            )
    return refs


def collect_python_refs(feature: FeatureSpec) -> list[BasicLineRef]:
    refs: list[BasicLineRef] = []
    for spec in feature.python_specs:
        index = parse_python_file(spec.path)
        layer = "Backend View" if spec.path.startswith("api/views/") else "Service/Domain"
        for symbol in index.closure(spec.roots, spec.helpers, spec.follow_calls):
            label = symbol.qualname if "." in symbol.qualname else symbol.name
            refs.append(
                BasicLineRef(
                    label=label,
                    path=spec.path,
                    line=symbol.lineno,
                    kind=symbol.kind,
                    layer=layer,
                    role=role_for_python_symbol(feature, symbol, spec.path, layer),
                    flow_step=flow_step_for_symbol(layer, symbol.name, symbol.kind),
                )
            )
    return refs


def collect_nav_and_route_refs(feature: FeatureSpec, nav_inventory: dict[tuple[str, str | None, str], int]) -> list[BasicLineRef]:
    refs: list[BasicLineRef] = []
    nav_key = (feature.nav_route, feature.nav_query, feature.shell)
    if nav_key not in nav_inventory:
        raise ValueError("Nav item missing for feature %s" % feature.slug)
    refs.append(
        BasicLineRef(
            label="Mục nav `%s`" % display_title(feature),
            path=feature.nav_file,
            line=nav_inventory[nav_key],
            kind="nav",
            layer="Nav",
            role=role_for_nav(feature),
            flow_step="Buoc mo chuc nang tu thanh nav",
        )
    )
    route_line = find_line_with_snippets("flutter_frontend/lib/core/router.dart", feature.route_match_snippets)
    refs.append(
        BasicLineRef(
            label="GoRoute `%s`" % feature.route,
            path="flutter_frontend/lib/core/router.dart",
            line=route_line,
            kind="route",
            layer="Router",
            role=role_for_route(feature),
            flow_step="Buoc chon route va tai man hinh",
        )
    )
    return refs


def collect_api_url_refs(feature: FeatureSpec) -> list[BasicLineRef]:
    refs: list[BasicLineRef] = []
    for path_fragment, view_name in feature.api_routes:
        line = find_line_with_snippets("api/urls.py", ("'%s'" % path_fragment, view_name))
        refs.append(
            BasicLineRef(
                label="URL `%s` -> `%s`" % (path_fragment, view_name),
                path="api/urls.py",
                line=line,
                kind="api-url",
                layer="API URL",
                role=role_for_api_url(feature, path_fragment, view_name),
                flow_step="Buoc map request frontend sang backend",
            )
        )
    return refs


def relative_sort_key(ref: BasicLineRef) -> tuple[int, str, int, str]:
    order = {
        "Nav": 0,
        "Router": 1,
        "UI Screen": 2,
        "Provider/Client": 3,
        "API URL": 4,
        "Backend View": 5,
        "Service/Domain": 6,
    }
    return (order.get(ref.layer, 99), ref.path, ref.line, ref.label)


def dedupe_refs(refs: Iterable[BasicLineRef]) -> list[BasicLineRef]:
    seen: set[tuple[str, int, str, str]] = set()
    result: list[BasicLineRef] = []
    for ref in sorted(refs, key=relative_sort_key):
        key = (ref.path, ref.line, ref.label, ref.layer)
        if key in seen:
            continue
        seen.add(key)
        result.append(ref)
    return result


def collect_feature_refs(feature: FeatureSpec, nav_inventory: dict[tuple[str, str | None, str], int]) -> list[BasicLineRef]:
    refs: list[BasicLineRef] = []
    refs.extend(collect_nav_and_route_refs(feature, nav_inventory))
    refs.extend(collect_screen_refs(feature))
    refs.extend(collect_provider_refs(feature))
    refs.extend(collect_api_url_refs(feature))
    refs.extend(collect_python_refs(feature))
    return dedupe_refs(refs)


def render_feature_doc(feature: FeatureSpec, refs: list[BasicLineRef]) -> str:
    route_line = next(ref for ref in refs if ref.layer == "Router")
    nav_line = next(ref for ref in refs if ref.layer == "Nav")
    title = display_title(feature)
    runtime_sections: list[tuple[str, list[str]]] = [
        ("Nav và router", [feature.nav_file, "flutter_frontend/lib/core/router.dart"]),
        ("Màn hình Flutter", list(feature.screen_files)),
        ("Provider và client", list(feature.provider_files)),
        ("Backend trực tiếp", ["api/urls.py", *(spec.path for spec in feature.python_specs)]),
    ]
    related_files = list(dict.fromkeys(feature.related_files))

    lines: list[str] = []
    lines.append("# %02d. %s" % (feature.id, title))
    lines.append("")
    lines.append("## Chức năng")
    lines.append("- Tên chức năng: %s" % title)
    lines.append("- Route nav: `%s`" % feature.route)
    lines.append("- Shell: `%s`" % feature.shell)
    lines.append("- Nguồn sự thật nav: `%s:%s`" % (nav_line.path, nav_line.line))
    lines.append("- Nguồn sự thật route: `%s:%s`" % (route_line.path, route_line.line))
    lines.append("")
    lines.append("## Điều kiện xuất hiện trên nav")
    lines.append("- Hiện cho: %s" % beautify_text(feature.visibility))
    lines.append("- Nhóm nav: %s" % beautify_text(feature.nav_group))
    lines.append("- Mục này chỉ được báo cáo vì đang có trên nav và người dùng có thể sử dụng ở runtime hiện tại.")
    lines.append("")
    lines.append("## Route chính và route con")
    lines.append("- Route chính: `%s`" % feature.route)
    if feature.subroutes:
        for subroute in feature.subroutes:
            lines.append("- Route con cùng flow: `%s`" % subroute)
    else:
        lines.append("- Route con cùng flow: không có")
    lines.append("")
    lines.append("## Tệp runtime chính")
    for section_title, paths in runtime_sections:
        unique_paths = list(dict.fromkeys(paths))
        if not unique_paths:
            continue
        lines.append("### %s" % section_title)
        for path in unique_paths:
            lines.append("- `%s`" % path)
    lines.append("")
    lines.append("## Tệp liên quan")
    if related_files:
        for path in related_files:
            lines.append("- `%s`" % path)
    else:
        lines.append("- Không khai báo tệp bổ trợ riêng.")
    lines.append("")
    lines.append("## Danh sách hàm / method / provider / endpoint phục vụ chức năng")
    lines.append("| Tầng | Symbol | File và dòng | Vai trò trong chức năng | Được dùng ở bước nào |")
    lines.append("| --- | --- | --- | --- | --- |")
    for ref in refs:
        lines.append(
            "| %s | %s | `%s:%s` | %s | %s |"
            % (ref.layer, ref.label, ref.path, ref.line, ref.role, ref.flow_step)
        )
    lines.append("")
    lines.append("## Luồng tuần tự chi tiết")
    for index, step in enumerate(feature.sequence_steps, start=1):
        lines.append("%d. %s" % (index, display_sequence_step(feature, step)))
    lines.append("")
    lines.append("## Sơ đồ tuần tự tham chiếu")
    lines.append("- PlantUML: `%s`" % feature.diagram_path)
    lines.append("- Lưu ý: sơ đồ được dùng để đối chiếu; line number và runtime file trong tài liệu này ưu tiên source code nav/router hiện tại.")
    lines.append("")
    return beautify_text("\n".join(lines))


def render_index(features: list[FeatureSpec], docs_by_feature: dict[int, str], nav_inventory: dict[tuple[str, str | None, str], int]) -> str:
    lines: list[str] = []
    lines.append("# Mục lục chức năng nav web đang sử dụng")
    lines.append("")
    lines.append("- Phạm vi: chỉ các chức năng đang xuất hiện trên nav và có thể sử dụng ở runtime hiện tại.")
    lines.append("- Nguồn sự thật: `app_shell.dart`, `guest_shell.dart`, `router.dart`, `api/urls.py`.")
    lines.append("- Tổng số chức năng: `%d`" % len(features))
    lines.append("")
    lines.append("| ID | Chức năng | Route nav | Shell | Hiện cho ai | Nav source | Hồ sơ | Sơ đồ |")
    lines.append("| --- | --- | --- | --- | --- | --- | --- | --- |")
    for feature in features:
        nav_line = nav_inventory[(feature.nav_route, feature.nav_query, feature.shell)]
        doc_name = docs_by_feature[feature.id]
        lines.append(
            "| %02d | %s | `%s` | `%s` | %s | `%s:%s` | `%s` | `%s` |"
            % (
                feature.id,
                display_title(feature),
                feature.route,
                feature.shell,
                beautify_text(feature.visibility),
                feature.nav_file,
                nav_line,
                doc_name,
                feature.diagram_path,
            )
        )
    lines.append("")
    return beautify_text("\n".join(lines))


def selected_features(raw_items: list[str] | None) -> list[FeatureSpec]:
    if not raw_items:
        return list(FEATURES)
    picked: list[FeatureSpec] = []
    seen: set[int] = set()
    for raw_item in raw_items:
        feature: FeatureSpec | None = None
        if raw_item.isdigit():
            feature = FEATURE_BY_ID.get(int(raw_item))
        if feature is None:
            feature = FEATURE_BY_SLUG.get(raw_item)
        if feature is None:
            raise ValueError("Unknown feature selector: %s" % raw_item)
        if feature.id in seen:
            continue
        seen.add(feature.id)
        picked.append(feature)
    return picked


def verify_inventory(features: list[FeatureSpec], nav_inventory: dict[tuple[str, str | None, str], int]) -> None:
    feature_keys = {(feature.nav_route, feature.nav_query, feature.shell) for feature in FEATURES}
    if len(feature_keys) != 28:
        raise ValueError("Manifest must contain exactly 28 usable nav features, found %d" % len(feature_keys))
    discovered_keys = set(nav_inventory)
    if discovered_keys != feature_keys:
        missing = sorted(feature_keys - discovered_keys)
        extra = sorted(discovered_keys - feature_keys)
        raise ValueError("Nav inventory mismatch. missing=%s extra=%s" % (missing, extra))
    for feature in features:
        collect_feature_refs(feature, nav_inventory)


def write_docs(features: list[FeatureSpec], nav_inventory: dict[tuple[str, str | None, str], int]) -> None:
    OUT_DIR.mkdir(exist_ok=True)
    docs_by_feature: dict[int, str] = {}
    for feature in features:
        refs = collect_feature_refs(feature, nav_inventory)
        doc_name = "%02d_%s.md" % (feature.id, feature.slug)
        docs_by_feature[feature.id] = doc_name
        (OUT_DIR / doc_name).write_text(render_feature_doc(feature, refs), encoding="utf-8")
    index_doc = render_index(list(FEATURES), {feature.id: "%02d_%s.md" % (feature.id, feature.slug) for feature in FEATURES}, nav_inventory)
    (OUT_DIR / "00_MUC_LUC.md").write_text(index_doc, encoding="utf-8")
    (OUT_DIR / "README.md").write_text(index_doc, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate detailed nav web runtime reports.")
    parser.add_argument("--feature", nargs="*", help="Feature ids or slugs to generate/check.")
    parser.add_argument("--check", action="store_true", help="Validate manifest and source resolution without writing files.")
    args = parser.parse_args()

    features = selected_features(args.feature)
    nav_inventory = discover_nav_inventory()
    verify_inventory(features, nav_inventory)
    if args.check:
        print("Nav report manifest check passed for %d feature(s)." % len(features))
        return
    write_docs(features, nav_inventory)
    print("Generated nav report docs for %d feature(s) in %s" % (len(features), OUT_DIR))


if __name__ == "__main__":
    main()
