// Tệp này dùng để: mô tả cấu trúc dữ liệu client dùng để đọc và ghi API trong flutter_frontend/lib/models/chat.dart.
// Cách hoạt động: được gọi từ lớp phía trên, xử lý dữ liệu theo vai trò hiện có và trả kết quả về cho luồng gọi.
// Vai trò trong hệ thống: Đây là lớp model dữ liệu phía Flutter.
// Tác dụng khi hệ thống vận hành: giúp frontend ánh xạ dữ liệu server thành đối tượng rõ nghĩa để render và xử lý.

// Mục đích: Lớp `ChatSession` triển khai phần việc `Chat Session` trong flutter_frontend/lib/models/chat.dart.
// Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
// Vai trò trong hệ thống: Đây là lớp thuộc lớp model dữ liệu phía Flutter.
// Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

class ChatSession {
  final int id;
  final String title;
  final String sessionType;
  final String? ragMode;
  final int messageCount;
  final int audioCount;
  final String createdAt;
  final String updatedAt;

  const ChatSession({
    required this.id, required this.title, required this.sessionType,
    this.ragMode, required this.messageCount, this.audioCount = 0, required this.createdAt,
    this.updatedAt = '',
  });

  factory ChatSession.fromJson(Map<String, dynamic> json) => ChatSession(
    id: json['id'],
    title: json['title'],
    sessionType: json['session_type'] ?? 'chat',
    ragMode: json['rag_mode'],
    messageCount: json['message_count'] ?? 0,
    audioCount: json['audio_count'] ?? 0,
    createdAt: json['created_at'] ?? '',
    updatedAt: json['updated_at'] ?? json['created_at'] ?? '',
  );
}

// Mục đích: Lớp `ChatAudioAttachment` triển khai phần việc `Chat Audio Attachment` trong flutter_frontend/lib/models/chat.dart.
// Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
// Vai trò trong hệ thống: Đây là lớp thuộc lớp model dữ liệu phía Flutter.
// Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

class ChatAudioAttachment {
  final int id;
  final int sessionId;
  final String sessionTitle;
  final int? messageId;
  final String title;
  final String transcript;
  final String mimeType;
  final double durationSeconds;
  final String downloadUrl;
  final String createdAt;

  const ChatAudioAttachment({
    required this.id,
    required this.sessionId,
    required this.sessionTitle,
    required this.messageId,
    required this.title,
    required this.transcript,
    required this.mimeType,
    required this.durationSeconds,
    required this.downloadUrl,
    required this.createdAt,
  });

  factory ChatAudioAttachment.fromJson(Map<String, dynamic> json) => ChatAudioAttachment(
    id: json['id'] ?? 0,
    sessionId: json['session_id'] ?? 0,
    sessionTitle: json['session_title'] ?? '',
    messageId: json['message_id'],
    title: json['title'] ?? '',
    transcript: json['transcript'] ?? '',
    mimeType: json['mime_type'] ?? '',
    durationSeconds: (json['duration_seconds'] as num?)?.toDouble() ?? 0,
    downloadUrl: json['download_url'] ?? '',
    createdAt: json['created_at'] ?? '',
  );
}

// Mục đích: Lớp `ChatMessage` triển khai phần việc `Chat Message` trong flutter_frontend/lib/models/chat.dart.
// Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
// Vai trò trong hệ thống: Đây là lớp thuộc lớp model dữ liệu phía Flutter.
// Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

class ChatMessage {
  final int id;
  final String role;
  final String content;
  final List<dynamic> citations;
  final String createdAt;
  final Map<String, dynamic>? payload;
  final List<ChatAudioAttachment> audioAttachments;

  const ChatMessage({
    required this.id, required this.role, required this.content,
    required this.citations, required this.createdAt, this.payload,
    this.audioAttachments = const [],
  });

  factory ChatMessage.fromJson(Map<String, dynamic> json) => ChatMessage(
    id: json['id'],
    role: json['role'],
    content: json['content'],
    citations: json['citations'] ?? [],
    createdAt: json['created_at'] ?? '',
    payload: json['payload'] is Map<String, dynamic>
        ? json['payload'] as Map<String, dynamic>
        : (json['payload'] is Map ? Map<String, dynamic>.from(json['payload']) : null),
    audioAttachments: (json['audio_attachments'] as List<dynamic>? ?? [])
        .map((item) => ChatAudioAttachment.fromJson(Map<String, dynamic>.from(item as Map)))
        .toList(),
  );
}
