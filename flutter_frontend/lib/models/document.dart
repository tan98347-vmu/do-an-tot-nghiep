import 'assistant_quick_sign.dart';

class Document {
  final int id;
  final String? _recordCode;
  final String title;
  final String? content;
  final String? docNumber;
  final String status;
  final String visibility;
  final String shareStatus;
  final int? ownerId;
  final String ownerName;
  final int? groupId;
  final String? templateTitle;
  final bool isArchived;
  final bool hasFile;
  final String createdAt;
  final String updatedAt;
  final String? sourceType;
  final String? notes;
  final List<String> tags;
  final String? departmentName;
  final String? categoryName;
  final String? groupName;
  final int versionNumber;
  final int versionCount;
  final bool isFavorite;
  final bool canEdit;
  final bool canDelete;
  final String signingStatus;
  final bool canForwardNow;
  final AssistantQuickSignPlanAction? assistantAction;
  final bool canManualEdit;
  final bool canResumeManualEdit;
  final bool manualEditActive;
  final int? manualEditSessionId;
  final String? manualEditSessionStatus;
  final String? manualEditLockMessage;
  final String? manualEditLockedByName;
  final int? promptId;
  final String? promptTitle;
  final String? appliedUserRules;
  final String peerShareStatus;
  final int peerAudienceCount;
  final bool isPeerSharedToMe;

  const Document({
    required this.id,
    String? recordCode,
    required this.title,
    this.content,
    this.docNumber,
    required this.status,
    required this.visibility,
    required this.shareStatus,
    this.ownerId,
    required this.ownerName,
    this.groupId,
    this.templateTitle,
    required this.isArchived,
    required this.hasFile,
    required this.createdAt,
    required this.updatedAt,
    this.sourceType,
    this.notes,
    this.tags = const [],
    this.departmentName,
    this.categoryName,
    this.groupName,
    this.versionNumber = 1,
    this.versionCount = 0,
    required this.isFavorite,
    required this.canEdit,
    required this.canDelete,
    this.signingStatus = 'unsigned',
    this.canForwardNow = false,
    this.assistantAction,
    this.canManualEdit = false,
    this.canResumeManualEdit = false,
    this.manualEditActive = false,
    this.manualEditSessionId,
    this.manualEditSessionStatus,
    this.manualEditLockMessage,
    this.manualEditLockedByName,
    this.promptId,
    this.promptTitle,
    this.appliedUserRules,
    this.peerShareStatus = 'none',
    this.peerAudienceCount = 0,
    this.isPeerSharedToMe = false,
  }) : _recordCode = recordCode;

  factory Document.fromJson(Map<String, dynamic> json) => Document(
        id: json['id'] as int? ?? 0,
        recordCode: json['record_code'] as String?,
        title: json['title'] as String? ?? '',
        content: json['content'] as String?,
        docNumber: json['doc_number'] as String?,
        status: json['status'] as String? ?? 'draft',
        visibility: json['visibility'] as String? ?? 'private',
        shareStatus: json['share_status'] as String? ?? 'private',
        ownerId: json['owner_id'] as int? ?? json['owner'] as int?,
        ownerName: json['owner_name'] as String? ?? '',
        groupId: json['group_id'] as int? ?? json['group'] as int?,
        templateTitle: json['template_title'] as String?,
        isArchived: json['is_archived'] as bool? ?? false,
        hasFile: json['has_file'] as bool? ?? false,
        createdAt: json['created_at'] as String? ?? '',
        updatedAt: json['updated_at'] as String? ?? '',
        sourceType: json['source_type'] as String?,
        notes: json['notes'] as String?,
        tags: ((json['tags'] as List?) ?? const [])
            .map((item) => item.toString().trim())
            .where((item) => item.isNotEmpty)
            .toList(),
        departmentName: json['department_name'] as String?,
        categoryName: json['category_name'] as String?,
        groupName: json['group_name'] as String?,
        versionNumber: json['version_number'] as int? ?? 1,
        versionCount: json['version_count'] as int? ?? 0,
        isFavorite: json['is_favorite'] as bool? ?? false,
        canEdit: json['can_edit'] as bool? ?? false,
        canDelete: json['can_delete'] as bool? ?? false,
        signingStatus: json['signing_status'] as String? ?? 'unsigned',
        canForwardNow: json['can_forward_now'] as bool? ?? false,
        assistantAction: json['assistant_action'] is Map
            ? AssistantQuickSignPlanAction.fromJson(
                Map<String, dynamic>.from(json['assistant_action'] as Map),
              )
            : null,
        canManualEdit: json['can_manual_edit'] as bool? ?? false,
        canResumeManualEdit: json['can_resume_manual_edit'] as bool? ?? false,
        manualEditActive: json['manual_edit_active'] as bool? ?? false,
        manualEditSessionId: json['manual_edit_session_id'] as int?,
        manualEditSessionStatus: json['manual_edit_session_status'] as String?,
        manualEditLockMessage: json['manual_edit_lock_message'] as String?,
        manualEditLockedByName: json['manual_edit_locked_by_name'] as String?,
        promptId: json['prompt_id'] as int?,
        promptTitle: json['prompt_title'] as String?,
        appliedUserRules: json['applied_user_rules'] as String?,
        peerShareStatus: (json['peer_share_status'] ?? 'none') as String,
        peerAudienceCount: (json['peer_audience_count'] ?? 0) as int,
        isPeerSharedToMe: json['is_peer_shared_to_me'] == true,
      );

  String get recordCode {
    final value = _recordCode?.trim() ?? '';
    if (value.isNotEmpty) return value;
    return 'VB-${id.toString().padLeft(6, '0')}';
  }

  String get statusLabel => switch (status) {
        'final' => 'Chính thức',
        'archived' => 'Lưu trữ',
        _ => 'Nháp',
      };

  String get signingStatusLabel =>
      signingStatus == 'signed' ? 'Đã ký' : 'Chưa ký';
}
