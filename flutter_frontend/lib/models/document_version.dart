// Tệp này dùng để: mô tả cấu trúc dữ liệu client dùng để đọc và ghi API trong flutter_frontend/lib/models/document_version.dart.
// Cách hoạt động: được gọi từ lớp phía trên, xử lý dữ liệu theo vai trò hiện có và trả kết quả về cho luồng gọi.
// Vai trò trong hệ thống: Đây là lớp model dữ liệu phía Flutter.
// Tác dụng khi hệ thống vận hành: giúp frontend ánh xạ dữ liệu server thành đối tượng rõ nghĩa để render và xử lý.

// Mục đích: Lớp `DocumentVersion` triển khai phần việc `Document Version` trong flutter_frontend/lib/models/document_version.dart.
// Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
// Vai trò trong hệ thống: Đây là lớp thuộc lớp model dữ liệu phía Flutter.
// Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

class DocumentVersion {
  final int id;
  final int versionNumber;
  final String content;
  final String? changeNote;
  final Map<String, dynamic> variablesUsed;
  final String createdByName;
  final String createdAt;
  final bool isHidden;
  final String? outputFile;

  const DocumentVersion({
    required this.id, required this.versionNumber, required this.content,
    this.changeNote, required this.variablesUsed, required this.createdByName,
    required this.createdAt, required this.isHidden, this.outputFile,
  });

  factory DocumentVersion.fromJson(Map<String, dynamic> json) => DocumentVersion(
    id: json['id'],
    versionNumber: json['version_number'] ?? 1,
    content: json['content'] ?? '',
    changeNote: json['change_note'],
    variablesUsed: Map<String, dynamic>.from(json['variables_used'] ?? {}),
    createdByName: json['created_by_name'] ?? '',
    createdAt: json['created_at'] ?? '',
    isHidden: json['is_hidden'] ?? false,
    outputFile: json['output_file'],
  );
}
