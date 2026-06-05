// Tệp này dùng để: mô tả cấu trúc dữ liệu client dùng để đọc và ghi API trong flutter_frontend/lib/models/trash.dart.
// Cách hoạt động: được gọi từ lớp phía trên, xử lý dữ liệu theo vai trò hiện có và trả kết quả về cho luồng gọi.
// Vai trò trong hệ thống: Đây là lớp model dữ liệu phía Flutter.
// Tác dụng khi hệ thống vận hành: giúp frontend ánh xạ dữ liệu server thành đối tượng rõ nghĩa để render và xử lý.

// Mục đích: Lớp `TrashEntry` triển khai phần việc `Trash Entry` trong flutter_frontend/lib/models/trash.dart.
// Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
// Vai trò trong hệ thống: Đây là lớp thuộc lớp model dữ liệu phía Flutter.
// Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

class TrashEntry {
  final String category;
  final int id;
  final String trashKey;
  final String title;
  final String subtitle;
  final String preview;
  final String deletedAt;
  final String expiresAt;
  final int messageCount;
  final int audioCount;

  const TrashEntry({
    required this.category,
    required this.id,
    required this.trashKey,
    required this.title,
    required this.subtitle,
    required this.preview,
    required this.deletedAt,
    required this.expiresAt,
    required this.messageCount,
    required this.audioCount,
  });

  factory TrashEntry.fromJson(Map<String, dynamic> json) => TrashEntry(
        category: json['category']?.toString() ?? '',
        id: (json['id'] as num?)?.toInt() ?? 0,
        trashKey: json['trash_key']?.toString() ?? '',
        title: json['title']?.toString() ?? '',
        subtitle: json['subtitle']?.toString() ?? '',
        preview: json['preview']?.toString() ?? '',
        deletedAt: json['deleted_at']?.toString() ?? '',
        expiresAt: json['expires_at']?.toString() ?? '',
        messageCount: (json['message_count'] as num?)?.toInt() ?? 0,
        audioCount: (json['audio_count'] as num?)?.toInt() ?? 0,
      );
}
