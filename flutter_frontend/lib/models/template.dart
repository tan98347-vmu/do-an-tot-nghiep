// Tệp này dùng để: mô tả cấu trúc dữ liệu client dùng để đọc và ghi API trong flutter_frontend/lib/models/template.dart.
// Cách hoạt động: được gọi từ lớp phía trên, xử lý dữ liệu theo vai trò hiện có và trả kết quả về cho luồng gọi.
// Vai trò trong hệ thống: Đây là lớp model dữ liệu phía Flutter.
// Tác dụng khi hệ thống vận hành: giúp frontend ánh xạ dữ liệu server thành đối tượng rõ nghĩa để render và xử lý.

// Mục đích: Lớp `TemplateAudienceUser` triển khai phần việc `Template Audience User` trong flutter_frontend/lib/models/template.dart.
// Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
// Vai trò trong hệ thống: Đây là lớp thuộc lớp model dữ liệu phía Flutter.
// Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

class TemplateAudienceUser {
  final int id;
  final String username;
  final String fullName;

  const TemplateAudienceUser({
    required this.id,
    required this.username,
    required this.fullName,
  });

  factory TemplateAudienceUser.fromJson(Map<String, dynamic> json) =>
      TemplateAudienceUser(
        id: json['id'],
        username: json['username'] ?? '',
        fullName: json['full_name'] ?? json['username'] ?? '',
      );
}

// Mục đích: Lớp `DocumentTemplate` triển khai phần việc `Document Template` trong flutter_frontend/lib/models/template.dart.
// Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
// Vai trò trong hệ thống: Đây là lớp thuộc lớp model dữ liệu phía Flutter.
// Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

class DocumentTemplate {
  final int id;
  final String? _recordCode;
  final String title;
  final String description;
  final String? content;
  final String status;
  final String visibility;
  final String version;
  final int? ownerId;
  final String ownerName;
  final int? groupId;
  final int variableCount;
  final List<String> variables;
  final String? categoryName;
  final bool isFavorite;
  final bool canUse;
  final bool canEdit;
  final bool canDelete;
  final bool isLimitedGroupShare;
  final int audienceCount;
  final List<int> audienceUserIds;
  final List<TemplateAudienceUser> audienceUsers;
  final String? effectiveDate;
  final String? endDate;
  final String createdAt;
  final String updatedAt;
  final String? approvedBy;
  final String? approvedAt;
  final String? approverNote;
  final String? sourceType; // 'manual' or 'docx'
  final bool hasDocxSource;
  final List<String> tags;
  final String? lastReviewAction;
  final String? lastReviewAt;
  final String? lastReviewActorName;

  const DocumentTemplate({
    required this.id,
    String? recordCode,
    required this.title,
    required this.description,
    this.content,
    required this.status,
    required this.visibility,
    required this.version,
    this.ownerId,
    required this.ownerName,
    this.groupId,
    required this.variableCount,
    this.variables = const [],
    this.categoryName,
    required this.isFavorite,
    required this.canUse,
    required this.canEdit,
    required this.canDelete,
    this.isLimitedGroupShare = false,
    this.audienceCount = 0,
    this.audienceUserIds = const [],
    this.audienceUsers = const [],
    this.effectiveDate,
    this.endDate,
    required this.createdAt,
    required this.updatedAt,
    this.approvedBy,
    this.approvedAt,
    this.approverNote,
    this.sourceType,
    this.hasDocxSource = false,
    this.tags = const [],
    this.lastReviewAction,
    this.lastReviewAt,
    this.lastReviewActorName,
  }) : _recordCode = recordCode;

  factory DocumentTemplate.fromJson(Map<String, dynamic> json) =>
      DocumentTemplate(
        id: json['id'],
        recordCode: json['record_code'],
        title: json['title'],
        description: json['description'] ?? '',
        content: json['content'],
        status: json['status'],
        visibility: json['visibility'],
        version: json['version'] ?? '1.0',
        ownerId: json['owner_id'] ?? json['owner'],
        ownerName: json['owner_name'] ?? '',
        groupId: json['group_id'] ?? json['group'],
        variableCount: json['variable_count'] ?? 0,
        variables: List<String>.from(json['variables'] ?? []),
        categoryName: json['category_name'],
        isFavorite: json['is_favorite'] ?? false,
        canUse: json['can_use'] ?? false,
        canEdit: json['can_edit'] ?? false,
        canDelete: json['can_delete'] ?? false,
        isLimitedGroupShare: json['is_limited_group_share'] ?? false,
        audienceCount: json['audience_count'] ?? 0,
        audienceUserIds: List<int>.from(json['audience_user_ids'] ?? const []),
        audienceUsers: (json['audience_users'] as List<dynamic>? ?? const [])
            .map((item) =>
                TemplateAudienceUser.fromJson(item as Map<String, dynamic>))
            .toList(),
        effectiveDate: json['effective_date'],
        endDate: json['end_date'],
        createdAt: json['created_at'] ?? '',
        updatedAt: json['updated_at'] ?? '',
        approvedBy: json['approved_by_name'] ?? '',
        approvedAt: json['approved_at'],
        approverNote: json['approver_note'],
        sourceType: json['source_type'],
        hasDocxSource: json['has_docx_source'] ?? false,
        tags: List<String>.from(json['tags'] ?? []),
        lastReviewAction: json['last_review_action'],
        lastReviewAt: json['last_review_at'],
        lastReviewActorName: json['last_review_actor_name'],
      );

  String get recordCode {
    final value = _recordCode?.trim() ?? '';
    if (value.isNotEmpty) return value;
    return 'MVB-${id.toString().padLeft(6, '0')}';
  }

  String get visibilityLabel => switch (visibility) {
        'public' => 'Công khai',
        'group' => 'Phòng ban',
        _ => 'Riêng tư',
      };

  String get statusLabel => switch (status) {
        'approved' => 'Đã duyệt',
        'pending_leader' => 'Chờ trưởng nhóm duyệt',
        'pending' => 'Chờ duyệt',
        'rejected' => 'Bị từ chối',
        _ => 'Nháp',
      };
}
