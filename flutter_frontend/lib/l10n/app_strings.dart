// Tệp này dùng để: quản lý chuỗi đa ngôn ngữ trong flutter_frontend/lib/l10n/app_strings.dart.
// Cách hoạt động: được gọi từ lớp phía trên, xử lý dữ liệu theo vai trò hiện có và trả kết quả về cho luồng gọi.
// Vai trò trong hệ thống: Đây là lớp ngôn ngữ hóa của Flutter.
// Tác dụng khi hệ thống vận hành: giúp app đổi ngôn ngữ mà vẫn giữ nội dung nhất quán trên toàn web.

import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';

// Mục đích: Lớp `AppStrings` triển khai phần việc `App Strings` trong flutter_frontend/lib/l10n/app_strings.dart.
// Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
// Vai trò trong hệ thống: Đây là lớp thuộc lớp ngôn ngữ hóa của Flutter.
// Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

class AppStrings {
  const AppStrings(this.locale);

  final Locale locale;

  static const supportedLocales = [
    Locale('vi'),
    Locale('en'),
  ];

  static const delegate = _AppStringsDelegate();

  static AppStrings of(BuildContext context) {
    final strings = Localizations.of<AppStrings>(context, AppStrings);
    assert(strings != null, 'AppStrings not found in widget tree.');
    return strings!;
  }

  bool get isEnglish => locale.languageCode == 'en';

  // Mục đích: Phương thức `pick` triển khai phần việc `pick` trong flutter_frontend/lib/l10n/app_strings.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc lớp ngôn ngữ hóa của Flutter.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  String pick(String vi, String en) =>
      isEnglish ? en : _normalizeVietnamese(vi);

  // === BEGIN R2 ===
  String get r2_summaryDownloadDocx =>
      pick('Tải .docx', 'Download .docx');

  String get r2_summaryDownloadMd =>
      pick('Tải .md', 'Download .md');

  String get r2_summaryChoosePrompt =>
      pick('Chọn prompt tóm tắt', 'Choose summary prompt');

  String r2_summarySelectedPrompt(String title) =>
      pick('Prompt: $title', 'Prompt: $title');

  String get r2_summaryClearPrompt =>
      pick('Bỏ prompt', 'Clear prompt');

  String get r2_complianceTitle =>
      pick('Kiểm tra văn bản theo quy trình', 'Compliance checker');

  String get r2_complianceChooseTarget =>
      pick('Bước 1: Chọn đối tượng', 'Step 1: Choose target');

  String get r2_complianceChoosePrompt =>
      pick('Bước 2: Chọn prompt quy trình', 'Step 2: Choose process prompt');

  String get r2_complianceRunStep =>
      pick('Bước 3: Chạy kiểm tra', 'Step 3: Run check');

  String get r2_complianceDocumentLabel =>
      pick('Văn bản', 'Document');

  String get r2_complianceTemplateLabel =>
      pick('Mẫu văn bản', 'Template');

  String get r2_complianceSearchTargetHint =>
      pick('Tìm văn bản hoặc mẫu văn bản...', 'Search documents or templates...');

  String get r2_complianceChooseProcessPrompt =>
      pick('Chọn prompt quy trình', 'Choose process prompt');

  String r2_complianceSelectedPrompt(String title) =>
      pick('Đã chọn: $title', 'Selected: $title');

  String get r2_complianceNoTargetResults =>
      pick('Chưa có kết quả phù hợp.', 'No matching targets yet.');

  String get r2_complianceNoPromptResults =>
      pick('Chưa tìm thấy prompt phù hợp.', 'No matching prompt found.');

  String get r2_compliancePromptSearchHint =>
      pick('Tìm prompt theo tên hoặc nội dung...', 'Search prompts by title or content...');

  String get r2_complianceRun =>
      pick('Kiểm tra', 'Run compliance check');

  String get r2_complianceRerun =>
      pick('Kiểm tra lại', 'Run again');

  String get r2_complianceDownloadMd =>
      pick('Tải kết quả (.md)', 'Download result (.md)');

  String get r2_complianceLoading =>
      pick('Đang phân tích văn bản…', 'Analyzing document…');

  String get r2_complianceHistoryTitle =>
      pick('Lịch sử 10 lần kiểm tra gần nhất', 'Latest 10 compliance checks');

  String get r2_complianceOpen =>
      pick('Mở', 'Open');

  String get r2_compliancePassMessage =>
      pick(
        'Văn bản/mẫu văn bản đã đáp ứng được những yêu cầu mà bạn đưa ra',
        'The document/template satisfies the requirements you provided',
      );

  String get r2_complianceFailHeading =>
      pick(
        'Văn bản chưa đáp ứng các yêu cầu sau:',
        'The document does not satisfy these requirements:',
      );

  String get r2_complianceOpenChecker =>
      pick('Mở kiểm tra tuân thủ', 'Open compliance checker');
  // === END R2 ===

  String _normalizeVietnamese(String value) {
    final repaired = _repairMojibake(value);
    final exactOverrides = <String, String>{
      'Bo chon': 'B\u1ecf ch\u1ecdn',
      'Bo chon tat ca': 'B\u1ecf ch\u1ecdn t\u1ea5t c\u1ea3',
      'Chon tat ca': 'Ch\u1ecdn t\u1ea5t c\u1ea3',
      'Chua chon mau nao': 'Ch\u01b0a ch\u1ecdn m\u1eabu n\u00e0o',
      'Chua chon van ban nao': 'Ch\u01b0a ch\u1ecdn v\u0103n b\u1ea3n n\u00e0o',
      'B? ch?n': 'B\u1ecf ch\u1ecdn',
      'B? ch?n t?t c?': 'B\u1ecf ch\u1ecdn t\u1ea5t c\u1ea3',
      'Ch?n t?t c?': 'Ch\u1ecdn t\u1ea5t c\u1ea3',
      'Ch?a ch?n m?u n?o': 'Ch\u01b0a ch\u1ecdn m\u1eabu n\u00e0o',
      'Ch?a ch?n v?n b?n n?o': 'Ch\u01b0a ch\u1ecdn v\u0103n b\u1ea3n n\u00e0o',
      'Dang xoa...': '\u0110ang x\u00f3a...',
      '?ang x?a...': '\u0110ang x\u00f3a...',
      'Xoa hang loat': 'X\u00f3a h\u00e0ng lo\u1ea1t',
      'X?a h?ng lo?t': 'X\u00f3a h\u00e0ng lo\u1ea1t',
      'Dang tai xem truoc...': '\u0110ang t\u1ea3i xem tr\u01b0\u1edbc...',
      'Mo PDF': 'M\u1edf PDF',
      'Thao tac': 'Thao t\u00e1c',
      'Xem truoc': 'Xem tr\u01b0\u1edbc',
      'Chinh sua': 'Ch\u1ec9nh s\u1eeda',
      'Xoa mau': 'X\u00f3a m\u1eabu',
      'Tai lai': 'T\u1ea3i l\u1ea1i',
      'Nguon Internet': 'Ngu\u1ed3n Internet',
      'So ket qua Internet': 'S\u1ed1 k\u1ebft qu\u1ea3 Internet',
      '0 = tat goi y Internet': '0 = t\u1eaft g\u1ee3i \u00fd Internet',
      'Nhap ten model thu cong': 'Nh\u1eadp t\u00ean model th\u1ee7 c\u00f4ng',
      'Khong co noi dung.': 'Kh\u00f4ng c\u00f3 n\u1ed9i dung.',
      'Khong co du lieu': 'Kh\u00f4ng c\u00f3 d\u1eef li\u1ec7u',
      'L?i': 'L\u1ed7i',
      'Cau hinh AI': 'C\u1ea5u h\u00ecnh AI',
      'Ho so ca nhan': 'H\u1ed3 s\u01a1 c\u00e1 nh\u00e2n',
      'Thung rac': 'Th\u00f9ng r\u00e1c',
      'Hom thu': 'H\u00f2m th\u01b0',
      'Yeu cau ky': 'Y\u00eau c\u1ea7u k\u00fd',
      'PDF da ky': 'PDF \u0111\u00e3 k\u00fd',
      'Uy quyen ky so': '\u1ee6y quy\u1ec1n k\u00fd s\u1ed1',
      'Kiem tra': 'Ki\u1ec3m tra',
      'Dong': '\u0110\u00f3ng',
      'Huy': 'H\u1ee7y',
      'Luu cau hinh': 'L\u01b0u c\u1ea5u h\u00ecnh',
      'Luu ngu canh': 'L\u01b0u ng\u1eef c\u1ea3nh',
      'Luu': 'L\u01b0u',
      'Tim': 'T\u00ecm',
      'Tim thay': 'T\u00ecm th\u1ea5y',
      'Xoa bo loc de xem tat ca':
          'X\u00f3a b\u1ed9 l\u1ecdc \u0111\u1ec3 xem t\u1ea5t c\u1ea3',
      'Khong tim thay van ban nao.':
          'Kh\u00f4ng t\u00ecm th\u1ea5y v\u0103n b\u1ea3n n\u00e0o.',
      'Khong tim thay mau nao.':
          'Kh\u00f4ng t\u00ecm th\u1ea5y m\u1eabu n\u00e0o.',
      'Trang thai': 'Tr\u1ea1ng th\u00e1i',
      'Dang forward': '\u0110ang forward',
      'Ket thuc': 'K\u1ebft th\u00fac',
      'Tu choi': 'T\u1eeb ch\u1ed1i',
      'Da xem': '\u0110\u00e3 xem',
      'Khong ro': 'Kh\u00f4ng r\u00f5',
      'Chua co thoi gian': 'Ch\u01b0a c\u00f3 th\u1eddi gian',
      'Tai len Word': 'T\u1ea3i l\u00ean Word',
      'Thong tin tai khoan': 'Th\u00f4ng tin t\u00e0i kho\u1ea3n',
      'Thong tin nhan su': 'Th\u00f4ng tin nh\u00e2n s\u1ef1',
      'Ten': 'T\u00ean',
      'Ho': 'H\u1ecd',
      'Ngay sinh': 'Ng\u00e0y sinh',
      'Chon ngay': 'Ch\u1ecdn ng\u00e0y',
      'Xoa ngay sinh': 'X\u00f3a ng\u00e0y sinh',
      'Alias nguoi nhan': 'Alias ng\u01b0\u1eddi nh\u1eadn',
      'Khoa ky so': 'Kh\u00f3a k\u00fd s\u1ed1',
      'Bo loc': 'B\u1ed9 l\u1ecdc',
      'Bo loc nang cao': 'B\u1ed9 l\u1ecdc n\u00e2ng cao',
      'Muc chia se': 'M\u1ee9c chia s\u1ebb',
      'Cong khai': 'C\u00f4ng khai',
      'Phong ban': 'Ph\u00f2ng ban',
      'Rieng tu': 'Ri\u00eang t\u01b0',
      'Da duyet': '\u0110\u00e3 duy\u1ec7t',
      'Cho duyet': 'Ch\u1edd duy\u1ec7t',
      'Ban nhap': 'B\u1ea3n nh\u00e1p',
      'Ngay tao': 'Ng\u00e0y t\u1ea1o',
      'Hieu luc tu': 'Hi\u1ec7u l\u1ef1c t\u1eeb',
      'Het hieu luc': 'H\u1ebft hi\u1ec7u l\u1ef1c',
      'Loi': 'L\u1ed7i',
      'Xac nhan': 'X\u00e1c nh\u1eadn',
      'Tat ca': 'T\u1ea5t c\u1ea3',
      'Ky so': 'K\u00fd s\u1ed1',
      'Can ky': 'C\u1ea7n k\u00fd',
      'Can ky ngay': 'C\u1ea7n k\u00fd ngay',
      'Cho buoc truoc': 'Ch\u1edd b\u01b0\u1edbc tr\u01b0\u1edbc',
      'Da ky': '\u0110\u00e3 k\u00fd',
      'Chua ky': 'Ch\u01b0a k\u00fd',
      'Da tu choi': '\u0110\u00e3 t\u1eeb ch\u1ed1i',
      'Khac': 'Kh\u00e1c',
      'An toan': 'An to\u00e0n',
      'Khong tin cay': 'Kh\u00f4ng tin c\u1eady',
      'Khong hop le': 'Kh\u00f4ng h\u1ee3p l\u1ec7',
      'Bi chinh sua': 'B\u1ecb ch\u1ec9nh s\u1eeda',
      'Noi bo': 'N\u1ed9i b\u1ed9',
      'Xac nhan noi bo': 'X\u00e1c nh\u1eadn n\u1ed9i b\u1ed9',
      'Ket qua': 'K\u1ebft qu\u1ea3',
      'Da forward': '\u0110\u00e3 forward',
      'Chua forward': 'Ch\u01b0a forward',
      'Nguoi ky': 'Ng\u01b0\u1eddi k\u00fd',
      'nguoi ky': 'ng\u01b0\u1eddi k\u00fd',
      'chu ky': 'ch\u1eef k\u00fd',
      'Chu so huu': 'Ch\u1ee7 s\u1edf h\u1eefu',
      'Hoan tat': 'Ho\u00e0n t\u1ea5t',
      'Kiem tra tinh toan ven': 'Ki\u1ec3m tra t\u00ednh to\u00e0n v\u1eb9n',
      'Kiem tra PDF mailbox': 'Ki\u1ec3m tra PDF mailbox',
      'PDF mailbox an toan': 'PDF mailbox an to\u00e0n',
      'PDF mailbox co dau hieu bi thay doi':
          'PDF mailbox c\u00f3 d\u1ea5u hi\u1ec7u b\u1ecb thay \u0111\u1ed5i',
      'Tong thread': 'T\u1ed5ng thread',
      'Tong muc': 'T\u1ed5ng m\u1ee5c',
      'Mo chi tiet': 'M\u1edf chi ti\u1ebft',
      'Mo van ban': 'M\u1edf v\u0103n b\u1ea3n',
      'Kho PDF da ky': 'Kho PDF \u0111\u00e3 k\u00fd',
      'Ban xem PDF mailbox': 'B\u1ea3n xem PDF mailbox',
      'Preview chua kha dung.': 'Preview ch\u01b0a kh\u1ea3 d\u1ee5ng.',
      'Tac vu ky da san sang.':
          'T\u00e1c v\u1ee5 k\u00fd \u0111\u00e3 s\u1eb5n s\u00e0ng.',
      'Khong tao duoc tac vu ky.':
          'Kh\u00f4ng t\u1ea1o \u0111\u01b0\u1ee3c t\u00e1c v\u1ee5 k\u00fd.',
      'Hoan thanh': 'Ho\u00e0n th\u00e0nh',
      'Hoan thanh xu ly': 'Ho\u00e0n th\u00e0nh x\u1eed l\u00fd',
      'Tu choi xu ly': 'T\u1eeb ch\u1ed1i x\u1eed l\u00fd',
      'Ly do hoan thanh': 'L\u00fd do ho\u00e0n th\u00e0nh',
      'Ly do tu choi': 'L\u00fd do t\u1eeb ch\u1ed1i',
      'Ly do': 'L\u00fd do',
      'Ly do gan nhat': 'L\u00fd do g\u1ea7n nh\u1ea5t',
      'Nguoi tao': 'Ng\u01b0\u1eddi t\u1ea1o',
      'Nguoi gui gan nhat': 'Ng\u01b0\u1eddi g\u1eedi g\u1ea7n nh\u1ea5t',
      'Nguoi xu ly': 'Ng\u01b0\u1eddi x\u1eed l\u00fd',
      'Nguoi xu ly cuoi': 'Ng\u01b0\u1eddi x\u1eed l\u00fd cu\u1ed1i',
      'So nhanh': 'S\u1ed1 nh\u00e1nh',
      'Cap nhat': 'C\u1eadp nh\u1eadt',
      'Tao luc': 'T\u1ea1o l\u00fac',
      'Xu ly luc': 'X\u1eed l\u00fd l\u00fac',
      'Ghi chu': 'Ghi ch\u00fa',
      'Ghi chu forward': 'Ghi ch\u00fa forward',
      'Tom tat': 'T\u00f3m t\u1eaft',
      'Tom tat van ban': 'T\u00f3m t\u1eaft v\u0103n b\u1ea3n',
      'Mo workspace tom tat': 'M\u1edf workspace t\u00f3m t\u1eaft',
      'TÃƒÂ³m tÃ¡ÂºÂ¯t vÃ„Æ’n bÃ¡ÂºÂ£n': 'T\u00f3m t\u1eaft v\u0103n b\u1ea3n',
      'MÃ¡Â»Å¸ workspace tÃƒÂ³m tÃ¡ÂºÂ¯t':
          'M\u1edf workspace t\u00f3m t\u1eaft',
      'Timeline': 'Timeline',
      'Tim nguoi nhan': 'T\u00ecm ng\u01b0\u1eddi nh\u1eadn',
      'Can chon it nhat mot nguoi nhan.':
          'C\u1ea7n ch\u1ecdn \u00edt nh\u1ea5t m\u1ed9t ng\u01b0\u1eddi nh\u1eadn.',
      'Chi tiet Hom thu': 'Chi ti\u1ebft H\u00f2m th\u01b0',
      'Chua co cap nhat mo ta gan nhat.':
          'Ch\u01b0a c\u00f3 c\u1eadp nh\u1eadt m\u00f4 t\u1ea3 g\u1ea7n nh\u1ea5t.',
      'Khong tai duoc yeu cau ky.':
          'Kh\u00f4ng t\u1ea3i \u0111\u01b0\u1ee3c y\u00eau c\u1ea7u k\u00fd.',
      'Khong tai duoc PDF da ky.':
          'Kh\u00f4ng t\u1ea3i \u0111\u01b0\u1ee3c PDF \u0111\u00e3 k\u00fd.',
      'Khong tai duoc Hom thu.':
          'Kh\u00f4ng t\u1ea3i \u0111\u01b0\u1ee3c H\u00f2m th\u01b0.',
      'Khong tai duoc mailbox thread.':
          'Kh\u00f4ng t\u1ea3i \u0111\u01b0\u1ee3c mailbox thread.',
      'Khong tai duoc PDF mailbox.':
          'Kh\u00f4ng t\u1ea3i \u0111\u01b0\u1ee3c PDF mailbox.',
      'Khong kiem tra duoc file mailbox.':
          'Kh\u00f4ng ki\u1ec3m tra \u0111\u01b0\u1ee3c file mailbox.',
      'Khong kiem tra duoc PDF mailbox.':
          'Kh\u00f4ng ki\u1ec3m tra \u0111\u01b0\u1ee3c PDF mailbox.',
      'Khong mo duoc PDF trong Hom thu.':
          'Kh\u00f4ng m\u1edf \u0111\u01b0\u1ee3c PDF trong H\u00f2m th\u01b0.',
      'Khong tai duoc danh sach nguoi nhan.':
          'Kh\u00f4ng t\u1ea3i \u0111\u01b0\u1ee3c danh s\u00e1ch ng\u01b0\u1eddi nh\u1eadn.',
      'Khong xu ly duoc entry.':
          'Kh\u00f4ng x\u1eed l\u00fd \u0111\u01b0\u1ee3c entry.',
      'Khong co entry nao khop bo loc timeline hien tai.':
          'Kh\u00f4ng c\u00f3 entry n\u00e0o kh\u1edbp b\u1ed9 l\u1ecdc timeline hi\u1ec7n t\u1ea1i.',
      'Khong co yeu cau nao dang cho buoc truoc.':
          'Kh\u00f4ng c\u00f3 y\u00eau c\u1ea7u n\u00e0o \u0111ang ch\u1edd b\u01b0\u1edbc tr\u01b0\u1edbc.',
      'Khong co yeu cau nao da bi tu choi.':
          'Kh\u00f4ng c\u00f3 y\u00eau c\u1ea7u n\u00e0o \u0111\u00e3 b\u1ecb t\u1eeb ch\u1ed1i.',
      'Khong co yeu cau nao san sang de ky.':
          'Kh\u00f4ng c\u00f3 y\u00eau c\u1ea7u n\u00e0o s\u1eb5n s\u00e0ng \u0111\u1ec3 k\u00fd.',
      'Ban chua hoan tat yeu cau ky nao.':
          'B\u1ea1n ch\u01b0a ho\u00e0n t\u1ea5t y\u00eau c\u1ea7u k\u00fd n\u00e0o.',
      'Bang yeu cau ky': 'B\u1ea3ng y\u00eau c\u1ea7u k\u00fd',
      'Dang cho mo buoc': '\u0110ang ch\u1edd m\u1edf b\u01b0\u1edbc',
      'Chua co van ban nao trong Hom thu.':
          'Ch\u01b0a c\u00f3 v\u0103n b\u1ea3n n\u00e0o trong H\u00f2m th\u01b0.',
      'Cai dat model AI va tham so cho toan he thong.':
          'C\u00e0i \u0111\u1eb7t model AI v\u00e0 tham s\u1ed1 cho to\u00e0n h\u1ec7 th\u1ed1ng.',
      'Ngu canh cong ty': 'Ng\u1eef c\u1ea3nh c\u00f4ng ty',
      'Chua co ngu canh cong ty.':
          'Ch\u01b0a c\u00f3 ng\u1eef c\u1ea3nh c\u00f4ng ty.',
      'Nhan "Chinh sua" de them thong tin.':
          'Nh\u1ea5n "Ch\u1ec9nh s\u1eeda" \u0111\u1ec3 th\u00eam th\u00f4ng tin.',
      'So ket qua RAG toi da': 'S\u1ed1 k\u1ebft qu\u1ea3 RAG t\u1ed1i \u0111a',
      'Da luu cau hinh AI.': '\u0110\u00e3 l\u01b0u c\u1ea5u h\u00ecnh AI.',
      'Da khoi phuc 1 muc.': '\u0110\u00e3 kh\u00f4i ph\u1ee5c 1 m\u1ee5c.',
      'Da xoa vinh vien 1 muc.':
          '\u0110\u00e3 x\u00f3a v\u0129nh vi\u1ec5n 1 m\u1ee5c.',
      'Khoi phuc': 'Kh\u00f4i ph\u1ee5c',
      'Khoi phuc da chon': 'Kh\u00f4i ph\u1ee5c \u0111\u00e3 ch\u1ecdn',
      'Dang khoi phuc...': '\u0110ang kh\u00f4i ph\u1ee5c...',
      'Xoa vinh vien': 'X\u00f3a v\u0129nh vi\u1ec5n',
      'Xoa tu khoa': 'X\u00f3a t\u1eeb kh\u00f3a',
      'Chua chon muc nao': 'Ch\u01b0a ch\u1ecdn m\u1ee5c n\u00e0o',
      'Khong co tieu de': 'Kh\u00f4ng c\u00f3 ti\u00eau \u0111\u1ec1',
      'Xoa luc': 'X\u00f3a l\u00fac',
      'Tu dong xoa vinh vien luc':
          'T\u1ef1 \u0111\u1ed9ng x\u00f3a v\u0129nh vi\u1ec5n l\u00fac',
      'Thung rac hien dang trong.':
          'Th\u00f9ng r\u00e1c hi\u1ec7n \u0111ang tr\u1ed1ng.',
      'Mau van ban': 'M\u1eabu v\u0103n b\u1ea3n',
      'Van ban': 'V\u0103n b\u1ea3n',
      'ChatAI chu': 'ChatAI ch\u1eef',
      'ChatAI giong noi': 'ChatAI gi\u1ecdng n\u00f3i',
      'Hoi dap mau': 'H\u1ecfi \u0111\u00e1p m\u1eabu',
      'Hoi dap van ban': 'H\u1ecfi \u0111\u00e1p v\u0103n b\u1ea3n',
    };
    final exact = exactOverrides[repaired] ?? exactOverrides[value];
    if (exact != null) {
      return exact;
    }
    if (repaired.startsWith('Da chon ') && repaired.endsWith(' mau')) {
      final count = repaired.substring(8, repaired.length - 4);
      return '\u0110\u00e3 ch\u1ecdn $count m\u1eabu';
    }
    if (repaired.startsWith('?? ch?n ') && repaired.endsWith(' m?u')) {
      final count = repaired.substring(8, repaired.length - 4);
      return '\u0110\u00e3 ch\u1ecdn $count m\u1eabu';
    }
    if (repaired.startsWith('Da chon ') && repaired.endsWith(' van ban')) {
      final count = repaired.substring(8, repaired.length - 8);
      return '\u0110\u00e3 ch\u1ecdn $count v\u0103n b\u1ea3n';
    }
    if (repaired.startsWith('Da chon ') && repaired.endsWith(' muc')) {
      final count = repaired.substring(8, repaired.length - 4);
      return '\u0110\u00e3 ch\u1ecdn $count m\u1ee5c';
    }
    if (repaired.startsWith('?? ch?n ') && repaired.endsWith(' v?n b?n')) {
      final count = repaired.substring(8, repaired.length - 8);
      return '\u0110\u00e3 ch\u1ecdn $count v\u0103n b\u1ea3n';
    }
    if (repaired.startsWith('Da khoi phuc ') && repaired.endsWith(' muc.')) {
      final count = repaired.substring(12, repaired.length - 5);
      return '\u0110\u00e3 kh\u00f4i ph\u1ee5c $count m\u1ee5c.';
    }
    if (repaired.startsWith('Da xoa vinh vien ') &&
        repaired.endsWith(' muc.')) {
      final count = repaired.substring(18, repaired.length - 5);
      return '\u0110\u00e3 x\u00f3a v\u0129nh vi\u1ec5n $count m\u1ee5c.';
    }
    if (repaired.startsWith('T?m th?y ')) {
      final suffix = repaired.substring('T?m th?y '.length);
      return 'T\u00ecm th\u1ea5y $suffix';
    }
    if (repaired.startsWith('Kh?p: ')) {
      final suffix = repaired.substring('Kh?p: '.length);
      return 'Kh\u1edbp: $suffix';
    }
    if (repaired.startsWith('Kh?ng t?m th?y ')) {
      final suffix = repaired.substring('Kh?ng t?m th?y '.length);
      return 'Kh\u00f4ng t\u00ecm th\u1ea5y $suffix';
    }
    if (repaired.startsWith('X?a b? l?c')) {
      return 'X\u00f3a b\u1ed9 l\u1ecdc \u0111\u1ec3 xem t\u1ea5t c\u1ea3';
    }
    if (repaired.startsWith('Buoc ')) {
      return repaired.replaceFirst('Buoc ', 'B\u01b0\u1edbc ');
    }
    if (repaired.startsWith('L?i')) {
      return repaired.replaceFirst('L?i', 'L\u1ed7i');
    }
    return repaired;
  }

  String _repairMojibake(String value) {
    if (value.isEmpty || !RegExp(r'[ÃÂÄÆâ]').hasMatch(value)) {
      return value;
    }
    try {
      final repaired = utf8.decode(latin1.encode(value));
      if (_mojibakeScore(repaired) < _mojibakeScore(value)) {
        return repaired;
      }
    } catch (_) {
      // Keep the original string when the byte sequence cannot be repaired safely.
    }
    return value;
  }

  int _mojibakeScore(String value) {
    const markers = ['Ã', 'Â', 'Ä', 'Æ', 'â', '�'];
    var score = 0;
    for (final marker in markers) {
      score += marker.allMatches(value).length;
    }
    return score;
  }

  String ui(String value) {
    const overrides = <String, ({String vi, String en})>{
      'Thông tin cá nhân': (
        vi: 'Thông tin cá nhân',
        en: 'Personal information'
      ),
      'Email': (vi: 'Email', en: 'Email'),
      'Số điện thoại': (vi: 'Số điện thoại', en: 'Phone number'),
      'Địa chỉ': (vi: 'Địa chỉ', en: 'Address'),
      'Mã nhân viên': (vi: 'Mã nhân viên', en: 'Employee code'),
      'Chức danh': (vi: 'Chức danh', en: 'Job title'),
      'Xác nhận mật khẩu mới': (
        vi: 'Xác nhận mật khẩu mới',
        en: 'Confirm new password'
      ),
      'Đã ký': (vi: 'Đã ký', en: 'Signed'),
      'Chưa ký': (vi: 'Chưa ký', en: 'Unsigned'),
      'Tạo từ AI': (vi: 'Tạo từ AI', en: 'Created by AI'),
      'Upload': (vi: 'Upload', en: 'Upload'),
      'Forward văn bản': (vi: 'Forward văn bản', en: 'Forward document'),
      'Người nhận': (vi: 'Người nhận', en: 'Recipient'),
      'Hòm thư': (vi: 'Hòm thư', en: 'Mailbox'),
      'Yêu cầu ký': (vi: 'Yêu cầu ký', en: 'Signing requests'),
      'PDF đã ký': (vi: 'PDF đã ký', en: 'Signed PDFs'),
      'Thùng rác': (vi: 'Thùng rác', en: 'Trash'),
      'Cấu hình AI': (vi: 'Cấu hình AI', en: 'AI configuration'),
      'Ngữ cảnh công ty': (vi: 'Ngữ cảnh công ty', en: 'Company context'),
      'Thông tin tài khoản': (
        vi: 'Thông tin tài khoản',
        en: 'Account information'
      ),
      'Thông tin nhân sự': (
        vi: 'Thông tin nhân sự',
        en: 'Employee information'
      ),
      'Sơ yếu lý lịch': (vi: 'Sơ yếu lý lịch', en: 'Profile summary'),
      'Chỉnh sửa hồ sơ': (vi: 'Chỉnh sửa hồ sơ', en: 'Edit profile'),
      'Lưu thay đổi': (vi: 'Lưu thay đổi', en: 'Save changes'),
      'Quay lại xem hồ sơ': (vi: 'Quay lại xem hồ sơ', en: 'Back to profile'),
      'Ngày sinh': (vi: 'Ngày sinh', en: 'Birth date'),
      'Tải lại': (vi: 'Tải lại', en: 'Reload'),
      'Khôi phục': (vi: 'Khôi phục', en: 'Restore'),
      'Xóa vĩnh viễn': (vi: 'Xóa vĩnh viễn', en: 'Delete permanently'),
      'Không có tiêu đề': (vi: 'Không có tiêu đề', en: 'Untitled'),
      'Ký số': (vi: 'Ký số', en: 'Digital signing'),
      'Kết quả': (vi: 'Kết quả', en: 'Results'),
      'An toàn': (vi: 'An toàn', en: 'Safe'),
      'Không rõ': (vi: 'Không rõ', en: 'Unknown'),
      'Đã forward': (vi: 'Đã forward', en: 'Forwarded'),
      'Chưa forward': (vi: 'Chưa forward', en: 'Not forwarded'),
      'Nguồn Internet': (vi: 'Nguồn Internet', en: 'Internet source'),
      'Số kết quả RAG tối đa': (
        vi: 'Số kết quả RAG tối đa',
        en: 'Maximum RAG results'
      ),
      'Số kết quả Internet': (
        vi: 'Số kết quả Internet',
        en: 'Internet result count'
      ),
      'Tìm người ký': (vi: 'Tìm người ký', en: 'Find signer'),
      'Bộ lọc thông minh': (vi: 'Bộ lọc thông minh', en: 'Smart filters'),
      'Hiện bộ lọc': (vi: 'Hiện bộ lọc', en: 'Show filters'),
      'Ẩn bộ lọc': (vi: 'Ẩn bộ lọc', en: 'Hide filters'),
      'Bộ lọc thêm': (vi: 'Bộ lọc thêm', en: 'More filters'),
      'Đặt lại': (vi: 'Đặt lại', en: 'Reset'),
      'Xóa bộ lọc': (vi: 'Xóa bộ lọc', en: 'Clear filters'),
      'Trạng thái': (vi: 'Trạng thái', en: 'Status'),
      'Nguồn gốc': (vi: 'Nguồn gốc', en: 'Source'),
      'Mức chia sẻ': (vi: 'Mức chia sẻ', en: 'Visibility'),
      'Kiểu hiển thị': (vi: 'Kiểu hiển thị', en: 'View mode'),
      'Tất cả': (vi: 'Tất cả', en: 'All'),
      'Đã duyệt': (vi: 'Đã duyệt', en: 'Approved'),
      'Chờ trưởng nhóm duyệt': (
        vi: 'Chờ trưởng nhóm duyệt',
        en: 'Waiting for team lead approval'
      ),
      'Chờ duyệt': (vi: 'Chờ duyệt', en: 'Pending'),
      'Bị từ chối': (vi: 'Bị từ chối', en: 'Rejected'),
      'Nháp': (vi: 'Nháp', en: 'Draft'),
      'Bản nháp': (vi: 'Bản nháp', en: 'Draft'),
      'Chính thức': (vi: 'Chính thức', en: 'Final'),
      'Lưu trữ': (vi: 'Lưu trữ', en: 'Archived'),
      'Công khai': (vi: 'Công khai', en: 'Public'),
      'Phòng ban': (vi: 'Phòng ban', en: 'Department'),
      'Riêng tư': (vi: 'Riêng tư', en: 'Private'),
      'Dạng thẻ': (vi: 'Dạng thẻ', en: 'Card view'),
      'Dạng danh sách': (vi: 'Dạng danh sách', en: 'List view'),
      'Ngày tạo': (vi: 'Ngày tạo', en: 'Created date'),
      'Hiệu lực từ ngày': (vi: 'Hiệu lực từ ngày', en: 'Effective from'),
      'Hết hiệu lực': (vi: 'Hết hiệu lực', en: 'Expiry date'),
      'Cập nhật': (vi: 'Cập nhật', en: 'Updated'),
      'Từ ngày': (vi: 'Từ ngày', en: 'From date'),
      'Đến ngày': (vi: 'Đến ngày', en: 'To date'),
      'Xóa khoảng ngày này': (
        vi: 'Xóa khoảng ngày này',
        en: 'Clear this date range'
      ),
      'Người dùng': (vi: 'Người dùng', en: 'Users'),
      'Nhóm': (vi: 'Nhóm', en: 'Groups'),
      'Chức vụ': (vi: 'Chức vụ', en: 'Positions'),
      'Import Excel': (vi: 'Import Excel', en: 'Excel import'),
      'Tìm kiếm người dùng...': (
        vi: 'Tìm kiếm người dùng...',
        en: 'Search users...'
      ),
      'Tìm kiếm nhóm...': (vi: 'Tìm kiếm nhóm...', en: 'Search groups...'),
      'Thêm': (vi: 'Thêm', en: 'Add'),
      'Chỉnh sửa': (vi: 'Chỉnh sửa', en: 'Edit'),
      'Xóa': (vi: 'Xóa', en: 'Delete'),
      'Hủy': (vi: 'Hủy', en: 'Cancel'),
      'Lưu': (vi: 'Lưu', en: 'Save'),
      'Tạo': (vi: 'Tạo', en: 'Create'),
      'Đóng': (vi: 'Đóng', en: 'Close'),
      'Thử lại': (vi: 'Thử lại', en: 'Retry'),
      'Xem tất cả': (vi: 'Xem tất cả', en: 'View all'),
      'Không có người dùng nào.': (
        vi: 'Không có người dùng nào.',
        en: 'No users found.'
      ),
      'Không có nhóm nào.': (vi: 'Không có nhóm nào.', en: 'No groups found.'),
      'Admin công ty': (vi: 'Admin công ty', en: 'Company admin'),
      'Trưởng nhóm': (vi: 'Trưởng nhóm', en: 'Team lead'),
      'Mẫu Văn Bản': (vi: 'Mẫu văn bản', en: 'Templates'),
      'Văn Bản': (vi: 'Văn bản', en: 'Documents'),
      'Phiên AI': (vi: 'Phiên AI', en: 'AI sessions'),
      'VB Tháng Này': (vi: 'VB tháng này', en: 'Documents this month'),
      'Mẫu Theo Tầng Tổ Chức': (
        vi: 'Mẫu theo tầng tổ chức',
        en: 'Templates by org layer'
      ),
      'Văn Bản Theo Tầng Tổ Chức': (
        vi: 'Văn bản theo tầng tổ chức',
        en: 'Documents by org layer'
      ),
      'Mẫu Văn Bản Mới Cập Nhật': (
        vi: 'Mẫu văn bản mới cập nhật',
        en: 'Recently updated templates'
      ),
      'Văn Bản Mới Cập Nhật': (
        vi: 'Văn bản mới cập nhật',
        en: 'Recently updated documents'
      ),
      'Bản đồ hệ thống': (vi: 'Bản đồ hệ thống', en: 'System map'),
      'Bản đồ cấu trúc doanh nghiệp': (
        vi: 'Bản đồ cấu trúc doanh nghiệp',
        en: 'Organization structure map'
      ),
      'Giao diện': (vi: 'Giao diện', en: 'Frontend'),
      'Quản trị viên': (vi: 'Quản trị viên', en: 'Administrators'),
      'Nhân viên': (vi: 'Nhân viên', en: 'Employees'),
      'Đặt lại góc nhìn': (vi: 'Đặt lại góc nhìn', en: 'Reset view'),
      'Phong ban': (vi: 'Phòng ban', en: 'Department'),
      'Chuc vu': (vi: 'Chức vụ', en: 'Position'),
      'Them': (vi: 'Thêm', en: 'Add'),
      'Chinh sua': (vi: 'Chỉnh sửa', en: 'Edit'),
      'Xoa': (vi: 'Xóa', en: 'Delete'),
      'Huy': (vi: 'Hủy', en: 'Cancel'),
      'Luu': (vi: 'Lưu', en: 'Save'),
      'Dong': (vi: 'Đóng', en: 'Close'),
      'Tim phong ban...': (vi: 'Tìm phòng ban...', en: 'Search departments...'),
      'Tim chuc vu...': (vi: 'Tìm chức vụ...', en: 'Search positions...'),
      'Khong co phong ban nao.': (
        vi: 'Không có phòng ban nào.',
        en: 'No departments found.'
      ),
      'Khong co chuc vu nao.': (
        vi: 'Không có chức vụ nào.',
        en: 'No positions found.'
      ),
      'Không có mô tả': (vi: 'Không có mô tả', en: 'No description'),
      'Nhân sự': (vi: 'Nhân sự', en: 'Employees'),
      'Đang dùng': (vi: 'Đang dùng', en: 'Active'),
      'Vô hiệu': (vi: 'Vô hiệu', en: 'Inactive'),
      'Quản trị': (vi: 'Quản trị', en: 'Admins'),
      'Thành viên': (vi: 'Thành viên', en: 'Members'),
      'Thành viên nhóm': (vi: 'Thành viên nhóm', en: 'Group member'),
      'Góc nhìn quản trị: bạn bao quát toàn bộ tài nguyên cá nhân, nhóm và tài nguyên công khai trong hệ thống.':
          (
        vi: 'Góc nhìn quản trị: bạn bao quát toàn bộ tài nguyên cá nhân, nhóm và tài nguyên công khai trong hệ thống.',
        en: 'Admin view: you can oversee personal, group, and public resources across the system.'
      ),
      'Góc nhìn trưởng nhóm: bạn thấy tài nguyên cá nhân, không gian nhóm phụ trách và tài nguyên toàn tổ chức.':
          (
        vi: 'Góc nhìn trưởng nhóm: bạn thấy tài nguyên cá nhân, không gian nhóm phụ trách và tài nguyên toàn tổ chức.',
        en: 'Team lead view: you can see personal resources, the groups you lead, and organization-wide resources.'
      ),
      'Góc nhìn đơn vị: bạn theo dõi tài nguyên của bạn, tài nguyên nhóm tham gia và các thành phần công khai của tổ chức.':
          (
        vi: 'Góc nhìn đơn vị: bạn theo dõi tài nguyên của bạn, tài nguyên nhóm tham gia và các thành phần công khai của tổ chức.',
        en: 'Unit view: you can follow your own resources, joined-group resources, and public organization resources.'
      ),
      'Góc nhìn cá nhân: dashboard nhấn mạnh tài nguyên của bạn và những gì tổ chức chia sẻ cho bạn.':
          (
        vi: 'Góc nhìn cá nhân: dashboard nhấn mạnh tài nguyên của bạn và những gì tổ chức chia sẻ cho bạn.',
        en: 'Personal view: the dashboard emphasizes your own resources and what the organization shares with you.'
      ),
      'Tổng số mẫu văn bản bạn có thể khai thác theo cấu trúc của tổ chức.': (
        vi: 'Tổng số mẫu văn bản bạn có thể khai thác theo cấu trúc của tổ chức.',
        en: 'The total number of templates you can use across the organization structure.'
      ),
      'Tổng số văn bản bạn đang nhìn thấy theo từng tầng tài nguyên trong hệ thống.':
          (
        vi: 'Tổng số văn bản bạn đang nhìn thấy theo từng tầng tài nguyên trong hệ thống.',
        en: 'The total number of documents you can currently see across the resource layers of the system.'
      ),
      'Văn bản phát sinh trong tháng hiện tại, tách theo các tầng của tổ chức.':
          (
        vi: 'Văn bản phát sinh trong tháng hiện tại, tách theo các tầng của tổ chức.',
        en: 'Documents created in the current month, broken down by organization layer.'
      ),
      'Phiên AI là dữ liệu cá nhân của tài khoản hiện tại, nhưng đang sử dụng cấu hình mô hình chung của tổ chức.':
          (
        vi: 'Phiên AI là dữ liệu cá nhân của tài khoản hiện tại, nhưng đang sử dụng cấu hình mô hình chung của tổ chức.',
        en: 'AI sessions belong to the current account, while still using the shared model configuration of the organization.'
      ),
      'Cá nhân sở hữu': (vi: 'Cá nhân sở hữu', en: 'Personally owned'),
      'Riêng tư / cấp phát': (
        vi: 'Riêng tư / cấp phát',
        en: 'Private / assigned'
      ),
      'Không gian nhóm': (vi: 'Không gian nhóm', en: 'Group space'),
      'Toàn tổ chức': (vi: 'Toàn tổ chức', en: 'Organization-wide'),
      'Cá nhân trong tháng': (
        vi: 'Cá nhân trong tháng',
        en: 'Personal this month'
      ),
      'Private trong tháng': (
        vi: 'Private trong tháng',
        en: 'Private this month'
      ),
      'Nhóm trong tháng': (vi: 'Nhóm trong tháng', en: 'Groups this month'),
      'Tổ chức trong tháng': (
        vi: 'Tổ chức trong tháng',
        en: 'Organization this month'
      ),
      'Mẫu do bạn tạo, chỉnh sửa hoặc đang phụ trách.': (
        vi: 'Mẫu do bạn tạo, chỉnh sửa hoặc đang phụ trách.',
        en: 'Templates you created, edited, or currently own.'
      ),
      'Mẫu private được cấp riêng cho bạn hoặc nằm ngoài phạm vi sở hữu của bạn.':
          (
        vi: 'Mẫu private được cấp riêng cho bạn hoặc nằm ngoài phạm vi sở hữu của bạn.',
        en: 'Private templates assigned specifically to you or outside your ownership scope.'
      ),
      'Mẫu chia sẻ theo nhóm, phòng ban mà bạn đang tham gia.': (
        vi: 'Mẫu chia sẻ theo nhóm, phòng ban mà bạn đang tham gia.',
        en: 'Templates shared with the groups or departments you belong to.'
      ),
      'Mẫu công khai, đã được duyệt và sẵn sàng cho tổ chức sử dụng.': (
        vi: 'Mẫu công khai, đã được duyệt và sẵn sàng cho tổ chức sử dụng.',
        en: 'Public templates that are approved and ready for organization-wide use.'
      ),
      'Văn bản do bạn tạo hoặc đang quản lý trực tiếp.': (
        vi: 'Văn bản do bạn tạo hoặc đang quản lý trực tiếp.',
        en: 'Documents you created or manage directly.'
      ),
      'Văn bản private ngoài sở hữu của bạn chỉ hiển thị nếu tài khoản có quyền quản trị.':
          (
        vi: 'Văn bản private ngoài sở hữu của bạn chỉ hiển thị nếu tài khoản có quyền quản trị.',
        en: 'Private documents outside your ownership are visible only when your account has admin privileges.'
      ),
      'Văn bản chia sẻ trong nhóm, đơn vị và đã được kích hoạt.': (
        vi: 'Văn bản chia sẻ trong nhóm, đơn vị và đã được kích hoạt.',
        en: 'Documents shared in groups or units and already activated.'
      ),
      'Văn bản công khai mà tài khoản hiện có thể tra cứu.': (
        vi: 'Văn bản công khai mà tài khoản hiện có thể tra cứu.',
        en: 'Public documents the current account can access.'
      ),
      'Văn bản bạn tạo từ ngày đầu tháng đến hiện tại.': (
        vi: 'Văn bản bạn tạo từ ngày đầu tháng đến hiện tại.',
        en: 'Documents you created from the start of the month until now.'
      ),
      'Văn bản private phát sinh trong tháng, chỉ có ý nghĩa với góc nhìn quản trị.':
          (
        vi: 'Văn bản private phát sinh trong tháng, chỉ có ý nghĩa với góc nhìn quản trị.',
        en: 'Private documents created this month, mainly relevant for the admin view.'
      ),
      'Văn bản nhóm/phòng ban có phát sinh trong tháng và bạn có thể truy cập.':
          (
        vi: 'Văn bản nhóm/phòng ban có phát sinh trong tháng và bạn có thể truy cập.',
        en: 'Group or department documents created this month that you can access.'
      ),
      'Văn bản công khai của tổ chức được tạo trong tháng hiện tại.': (
        vi: 'Văn bản công khai của tổ chức được tạo trong tháng hiện tại.',
        en: 'Public organization documents created in the current month.'
      ),
    };
    final translated = overrides[value];
    if (translated != null) {
      return isEnglish ? translated.en : _normalizeVietnamese(translated.vi);
    }
    if (value.startsWith('Số: ')) {
      final suffix = value.substring(4);
      return pick('Số: $suffix', 'No: $suffix');
    }
    if (value.startsWith('Số: ')) {
      final suffix = value.substring(4);
      return pick('Số: $suffix', 'No: $suffix');
    }
    if (value.startsWith('Người nhận ')) {
      final suffix = value.substring('Người nhận '.length);
      return pick('Người nhận $suffix', 'Recipient $suffix');
    }
    if (value.startsWith('Người nhận ')) {
      final suffix = value.substring('Người nhận '.length);
      return pick('Người nhận $suffix', 'Recipient $suffix');
    }
    if (value.startsWith('Mẫu: ')) {
      final suffix = value.substring('Mẫu: '.length);
      return pick('Mẫu: $suffix', 'Template: $suffix');
    }
    if (value.startsWith('Tìm thấy ')) {
      final suffix = value.substring('Tìm thấy '.length);
      return pick('Tìm thấy $suffix', 'Found $suffix');
    }
    if (value.startsWith('Khớp: "')) {
      final suffix = value.substring('Khớp: '.length);
      return pick('Khớp: $suffix', 'Match: $suffix');
    }
    if (value.startsWith('Có ') && value.endsWith(' phiên cũ')) {
      final count = value.substring(3, value.length - ' phiên cũ'.length);
      return pick('Có $count phiên cũ', '$count previous sessions');
    }
    return isEnglish ? value : _normalizeVietnamese(value);
  }

  String get language => pick('Ngôn ngữ', 'Language');
  String get vietnamese => pick('Tiếng Việt', 'Vietnamese');
  String get english => pick('Tiếng Anh', 'English');

  String get appTitle => pick('Quản lý văn bản AI', 'AI Document Manager');
  String get dashboardTitle => pick('Bảng điều khiển', 'Dashboard');
  String get dashboardSummary => pick('Tổng quan hệ thống', 'System overview');
  String get fromTemplate =>
      pick('Sinh văn bản từ mẫu', 'Generate from templates');
  String get documentQa => pick('Hỏi đáp văn bản', 'Document Q&A');
  String get bulkUploadTemplates =>
      pick('Tải lên nhiều mẫu', 'Bulk upload templates');
  String get approvalRequests => pick('Yêu cầu phê duyệt', 'Approval requests');
  String get accountsAndDepartments =>
      pick('Tài khoản & Nhóm', 'Accounts & Groups');
  String get createTemplateTitle => pick('Tạo mẫu văn bản', 'Create template');
  String get createTemplateSubtitle => pick(
        'Chọn một cách bắt đầu phù hợp để tạo một mẫu mới hoặc tải lên nhiều mẫu cùng lúc.',
        'Choose the right starting point to create one template or upload many templates at once.',
      );
  String get quickCreateTemplate => pick('Tạo nhanh một mẫu', 'Quick create');
  String get quickCreateTemplateDescription => pick(
        'Mở form tạo mẫu đầy đủ để soạn và cấu hình một mẫu mới ngay lập tức.',
        'Open the full template form to draft and configure a new template right away.',
      );
  String get bulkUploadTemplateDescription => pick(
        'Tải lên một thư mục DOCX kèm metadata để tạo nhiều mẫu trong một đợt.',
        'Upload a DOCX folder with metadata to create many templates in one batch.',
      );
  String get sharedTemplates => pick('Mẫu dùng chung', 'Shared templates');

  // === BEGIN R3 ===
  String get r3TaskInboxTitle => pick('Tác vụ AI', 'AI tasks');
  String get r3TaskInboxOpen => pick('Mở danh sách tác vụ', 'Open task inbox');
  String get r3TaskRunningSection => pick('Đang chạy', 'Running');
  String get r3TaskRecentSection => pick('Gần đây (50)', 'Recent (50)');
  String get r3TaskCancel => pick('Hủy', 'Cancel');
  String get r3TaskDismiss => pick('Đóng', 'Dismiss');
  String get r3TaskGoBack => pick('Quay lại', 'Go back');
  String get r3TaskClose => pick('Đóng', 'Close');
  String get r3TaskRetry => pick('Thử lại', 'Retry');
  String get r3TaskNoItems =>
      pick('Chưa có tác vụ nền nào gần đây.', 'There are no recent background tasks yet.');
  // === END R3 ===

  // Mục đích: Phương thức `templateGroupTitle` triển khai phần việc `template Group Title` trong flutter_frontend/lib/l10n/app_strings.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc lớp ngôn ngữ hóa của Flutter.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  String templateGroupTitle(String group) {
    switch (group) {
      case 'system':
        return pick('Mẫu dùng chung', 'Shared templates');
      case 'team':
        return pick('Mẫu phòng ban của tôi', 'My department templates');
      case 'private':
        return pick('Mẫu của tôi', 'My private templates');
      case 'favorite':
        return pick('Mẫu yêu thích', 'Favorite templates');
      case 'admin':
        return pick('Tất cả mẫu văn bản (Admin)', 'All templates (Admin)');
      default:
        return pick('Mẫu văn bản', 'Templates');
    }
  }

  // Mục đích: Phương thức `templateGroupSubtitle` triển khai phần việc `template Group Subtitle` trong flutter_frontend/lib/l10n/app_strings.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc lớp ngôn ngữ hóa của Flutter.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  String templateGroupSubtitle(String group) {
    switch (group) {
      case 'system':
        return pick(
          'Mẫu dùng chung cho toàn bộ nhân viên trong hệ thống',
          'Templates shared across the organization',
        );
      case 'team':
        return pick(
          'Các mẫu dùng chung trong phòng ban hoặc nhóm của bạn',
          'Templates shared within your department or group',
        );
      case 'private':
        return pick(
          'Tất cả mẫu bạn đã tạo, kể cả bản nháp hoặc đang chờ phê duyệt',
          'All templates you created, including drafts and pending approvals',
        );
      case 'favorite':
        return pick(
          'Các mẫu bạn đã đánh dấu yêu thích',
          'Templates you marked as favorite',
        );
      case 'admin':
        return pick(
          'Xem và quản lý toàn bộ mẫu văn bản của người dùng',
          'Browse and manage every template in the system',
        );
      default:
        return pick(
          'Tất cả mẫu văn bản bạn có quyền truy cập',
          'All templates you can access',
        );
    }
  }

  // Mục đích: Phương thức `documentGroupTitle` triển khai phần việc `document Group Title` trong flutter_frontend/lib/l10n/app_strings.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc lớp ngôn ngữ hóa của Flutter.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  String documentGroupTitle(String group) {
    switch (group) {
      case 'private':
        return pick('Văn bản của tôi', 'My documents');
      case 'group':
        return pick('Đã chia sẻ trong nhóm', 'Shared in my groups');
      case 'public':
        return pick('Đã chia sẻ công khai', 'Publicly shared documents');
      case 'favorite':
        return pick('Văn bản yêu thích', 'Favorite documents');
      case 'archived':
        return pick('Đã lưu trữ', 'Archived documents');
      case 'admin':
        return pick('Tất cả văn bản (Admin)', 'All documents (Admin)');
      default:
        return pick('Quản lý văn bản', 'Document management');
    }
  }

  // Mục đích: Phương thức `documentGroupSubtitle` triển khai phần việc `document Group Subtitle` trong flutter_frontend/lib/l10n/app_strings.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc lớp ngôn ngữ hóa của Flutter.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  String documentGroupSubtitle(String group) {
    switch (group) {
      case 'private':
        return pick(
          'Theo dõi các văn bản riêng của bạn và tải lên tài liệu Word mới',
          'Track your private documents and upload new Word files',
        );
      case 'group':
        return pick(
          'Những văn bản đang được chia sẻ trong các nhóm bạn tham gia',
          'Documents shared inside the groups you belong to',
        );
      case 'public':
        return pick(
          'Các văn bản được chia sẻ công khai trong hệ thống',
          'Documents publicly shared across the system',
        );
      case 'favorite':
        return pick(
          'Danh sách văn bản bạn đã đánh dấu yêu thích',
          'Documents you bookmarked as favorites',
        );
      case 'archived':
        return pick(
          'Các văn bản bạn đã lưu trữ',
          'Documents you archived',
        );
      case 'admin':
        return pick(
          'Xem và quản lý toàn bộ văn bản của người dùng',
          'Browse and manage every document in the system',
        );
      default:
        return pick(
          'Các văn bản bạn có quyền truy cập',
          'Documents you can access',
        );
    }
  }

  // Mục đích: Phương thức `templateSearchHint` triển khai phần việc `template Search Hint` trong flutter_frontend/lib/l10n/app_strings.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc lớp ngôn ngữ hóa của Flutter.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  String templateSearchHint(String group) {
    switch (group) {
      case 'system':
        return pick(
          'Tìm trong mẫu dùng chung theo tên, mô tả, tag, danh mục, phòng ban...',
          'Search shared templates by title, description, tags, category, department...',
        );
      case 'team':
        return pick(
          'Tìm trong mẫu phòng ban theo tên, mô tả, tag, nhóm, người tạo...',
          'Search department templates by title, description, tags, group, owner...',
        );
      case 'private':
        return pick(
          'Tìm trong mẫu của tôi theo tên, mô tả, tag, danh mục, trạng thái...',
          'Search your templates by title, description, tags, category, status...',
        );
      case 'favorite':
        return pick(
          'Tìm trong mẫu yêu thích theo tên, mô tả, tag, danh mục, người tạo...',
          'Search favorite templates by title, description, tags, category, owner...',
        );
      default:
        return pick(
          'Tìm mẫu văn bản theo tên, mô tả, tag, danh mục, phòng ban...',
          'Search templates by title, description, tags, category, department...',
        );
    }
  }

  // Mục đích: Phương thức `documentSearchHint` triển khai phần việc `document Search Hint` trong flutter_frontend/lib/l10n/app_strings.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc lớp ngôn ngữ hóa của Flutter.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  String documentSearchHint(String group) {
    switch (group) {
      case 'private':
        return pick(
          'Tìm văn bản của tôi theo tên, số hiệu, mẫu nguồn, ghi chú, danh mục...',
          'Search my documents by title, number, source template, notes, category...',
        );
      case 'group':
        return pick(
          'Tìm văn bản đã chia sẻ trong nhóm theo tên, số hiệu, người tạo, nhóm...',
          'Search group-shared documents by title, number, owner, group...',
        );
      case 'public':
        return pick(
          'Tìm văn bản công khai theo tên, số hiệu, mẫu nguồn, phòng ban...',
          'Search public documents by title, number, source template, department...',
        );
      case 'favorite':
        return pick(
          'Tìm trong văn bản yêu thích theo tên, số hiệu, người tạo, ghi chú...',
          'Search favorite documents by title, number, owner, notes...',
        );
      case 'archived':
        return pick(
          'Tìm trong văn bản lưu trữ theo tên, số hiệu, mẫu nguồn, trạng thái...',
          'Search archived documents by title, number, source template, status...',
        );
      default:
        return pick(
          'Tìm văn bản theo tên, số hiệu, mẫu nguồn, người tạo, ghi chú...',
          'Search documents by title, number, source template, owner, notes...',
        );
    }
  }

  // === BEGIN R4 ===
  String get r4_globalSearchTitle => pick('Tim kiem toan cuc', 'Global search');
  String get r4_globalSearchHint =>
      pick('Tim kiem moi thu (Ctrl+K)...', 'Search everything (Ctrl+K)...');
  String get r4_globalSearchRetry => pick('Thu lai', 'Retry');
  String get r4_globalSearchMinChars => pick(
        'Nhap it nhat 2 ky tu de tim kiem.',
        'Type at least 2 characters to search.',
      );
  String get r4_globalSearchTemplates => pick('Mau van ban', 'Templates');
  String get r4_globalSearchDocuments => pick('Van ban', 'Documents');
  String get r4_globalSearchPrompts => pick('Prompt', 'Prompts');
  String get r4_globalSearchSummaries => pick('Tom tat', 'Summaries');
  String get r4_globalSearchConversations =>
      pick('Cuoc tro chuyen', 'Conversations');
  String r4_globalSearchEmpty(String query) => pick(
        "Khong tim thay ket qua cho '$query'.",
        "No results found for '$query'.",
      );
  // === END R4 ===
}

// Mục đích: Lớp `_AppStringsDelegate` triển khai phần việc `App Strings Delegate` trong flutter_frontend/lib/l10n/app_strings.dart.
// Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
// Vai trò trong hệ thống: Đây là lớp thuộc lớp ngôn ngữ hóa của Flutter.
// Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

class _AppStringsDelegate extends LocalizationsDelegate<AppStrings> {
  const _AppStringsDelegate();

  @override
  // Mục đích: Phương thức `isSupported` triển khai phần việc `is Supported` trong flutter_frontend/lib/l10n/app_strings.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc lớp ngôn ngữ hóa của Flutter.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  bool isSupported(Locale locale) => {'vi', 'en'}.contains(locale.languageCode);

  @override
  // Mục đích: Phương thức `load` triển khai phần việc `load` trong flutter_frontend/lib/l10n/app_strings.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc lớp ngôn ngữ hóa của Flutter.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  Future<AppStrings> load(Locale locale) {
    return SynchronousFuture<AppStrings>(AppStrings(locale));
  }

  @override
  // Mục đích: Phương thức `shouldReload` triển khai phần việc `should Reload` trong flutter_frontend/lib/l10n/app_strings.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc lớp ngôn ngữ hóa của Flutter.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  bool shouldReload(_AppStringsDelegate old) => false;
}
