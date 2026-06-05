class Prompt {
  final int id;
  final String title;
  final String? systemContent;
  final String? rulesContent;
  final String status;
  final String visibility;
  final int? ownerId;
  final String ownerName;
  final String? categoryName;
  final int? groupId;
  final String? groupName;
  final String? tags;
  final String? source;
  final int usageCount;
  final String? approverNote;
  final bool isMine;
  final bool canApprove;
  final bool canEdit;
  final String peerShareStatus;
  final int peerAudienceCount;
  final bool isPeerSharedToMe;
  final String createdAt;
  final String updatedAt;

  const Prompt({
    required this.id,
    required this.title,
    this.systemContent,
    this.rulesContent,
    required this.status,
    required this.visibility,
    this.ownerId,
    required this.ownerName,
    this.categoryName,
    this.groupId,
    this.groupName,
    this.tags,
    this.source,
    this.usageCount = 0,
    this.approverNote,
    this.isMine = false,
    this.canApprove = false,
    this.canEdit = false,
    this.peerShareStatus = 'none',
    this.peerAudienceCount = 0,
    this.isPeerSharedToMe = false,
    required this.createdAt,
    this.updatedAt = '',
  });

  factory Prompt.fromJson(Map<String, dynamic> json) => Prompt(
        id: json['id'] as int,
        title: (json['title'] ?? '') as String,
        systemContent: json['system_content'] as String?,
        rulesContent: json['rules_content'] as String?,
        status: (json['status'] ?? 'approved') as String,
        visibility: (json['visibility'] ?? 'private') as String,
        ownerId: json['owner'] as int? ?? json['owner_id'] as int?,
        ownerName: (json['owner_name'] ?? '') as String,
        categoryName: json['category_name'] as String?,
        groupId: json['group'] as int?,
        groupName: json['group_name'] as String?,
        tags: json['tags'] as String?,
        source: json['source'] as String?,
        usageCount: (json['usage_count'] ?? 0) as int,
        approverNote: json['approver_note'] as String?,
        isMine: json['is_mine'] == true,
        canApprove: json['can_approve'] == true,
        canEdit: json['can_edit'] == true,
        peerShareStatus: (json['peer_share_status'] ?? 'none') as String,
        peerAudienceCount: (json['peer_audience_count'] ?? 0) as int,
        isPeerSharedToMe: json['is_peer_shared_to_me'] == true,
        createdAt: (json['created_at'] ?? '') as String,
        updatedAt: (json['updated_at'] ?? '') as String,
      );

  String get statusLabel => switch (status) {
        'approved' => 'Đã duyệt',
        'pending' => 'Chờ admin duyệt',
        'pending_leader' => 'Chờ trưởng nhóm duyệt',
        'rejected' => 'Bị từ chối',
        _ => status,
      };

  String get visibilityLabel => switch (visibility) {
        'public' => 'Công khai',
        'group' => 'Phòng ban',
        _ => 'Riêng tư',
      };
}
