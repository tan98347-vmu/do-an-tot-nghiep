// Mo hinh ShareGrant - mirror cua sharing.models.ShareGrant tren backend.

enum ShareScope { private, group, colleagues, everyone }

ShareScope shareScopeFromApi(String? value) => switch (value) {
      'private' => ShareScope.private,
      'group' => ShareScope.group,
      'colleagues' => ShareScope.colleagues,
      'everyone' => ShareScope.everyone,
      _ => ShareScope.private,
    };

String shareScopeToApi(ShareScope value) => switch (value) {
      ShareScope.private => 'private',
      ShareScope.group => 'group',
      ShareScope.colleagues => 'colleagues',
      ShareScope.everyone => 'everyone',
    };

String shareScopeLabel(ShareScope value) => switch (value) {
      ShareScope.private => 'Riêng tư',
      ShareScope.group => 'Nhóm',
      ShareScope.colleagues => 'Đồng nghiệp',
      ShareScope.everyone => 'Mọi người',
    };

String shareScopeDescription(ShareScope value) => switch (value) {
      ShareScope.private => 'Chỉ mình bạn thấy',
      ShareScope.group => 'Chia sẻ cho cả nhóm (trưởng nhóm duyệt)',
      ShareScope.colleagues =>
        'Chia sẻ cho đồng nghiệp cụ thể (chung nhóm: trưởng nhóm duyệt; khác nhóm: admin duyệt)',
      ShareScope.everyone => 'Chia sẻ cho tất cả (admin duyệt)',
    };

enum SharePermission { view, edit, delete }

SharePermission sharePermissionFromApi(String? value) => switch (value) {
      'delete' => SharePermission.delete,
      'edit' => SharePermission.edit,
      _ => SharePermission.view,
    };

String sharePermissionToApi(SharePermission value) => switch (value) {
      SharePermission.delete => 'delete',
      SharePermission.edit => 'edit',
      SharePermission.view => 'view',
    };

String sharePermissionLabel(SharePermission value) => switch (value) {
      SharePermission.view => 'Chỉ xem',
      SharePermission.edit => 'Xem & Sửa',
      SharePermission.delete => 'Toàn quyền (xem, sửa, xóa)',
    };

int sharePermissionRank(SharePermission p) => switch (p) {
      SharePermission.view => 1,
      SharePermission.edit => 2,
      SharePermission.delete => 3,
    };

enum ShareApprovalStatus { draft, pendingLeader, pendingAdmin, active, rejected }

ShareApprovalStatus shareApprovalFromApi(String? value) => switch (value) {
      'draft' => ShareApprovalStatus.draft,
      'pending_leader' => ShareApprovalStatus.pendingLeader,
      'pending_admin' => ShareApprovalStatus.pendingAdmin,
      'active' => ShareApprovalStatus.active,
      'rejected' => ShareApprovalStatus.rejected,
      _ => ShareApprovalStatus.draft,
    };

String shareApprovalToApi(ShareApprovalStatus value) => switch (value) {
      ShareApprovalStatus.draft => 'draft',
      ShareApprovalStatus.pendingLeader => 'pending_leader',
      ShareApprovalStatus.pendingAdmin => 'pending_admin',
      ShareApprovalStatus.active => 'active',
      ShareApprovalStatus.rejected => 'rejected',
    };

String shareApprovalLabel(ShareApprovalStatus value) => switch (value) {
      ShareApprovalStatus.draft => 'Nháp',
      ShareApprovalStatus.pendingLeader => 'Chờ trưởng nhóm duyệt',
      ShareApprovalStatus.pendingAdmin => 'Chờ admin duyệt',
      ShareApprovalStatus.active => 'Đã kích hoạt',
      ShareApprovalStatus.rejected => 'Bị từ chối',
    };

class UserBrief {
  final int id;
  final String username;
  final String fullName;
  final String email;
  final String position;

  const UserBrief({
    required this.id,
    required this.username,
    required this.fullName,
    required this.email,
    required this.position,
  });

  factory UserBrief.fromJson(Map<String, dynamic> json) => UserBrief(
        id: (json['id'] ?? 0) as int,
        username: (json['username'] ?? '') as String,
        fullName: (json['full_name'] ?? '') as String,
        email: (json['email'] ?? '') as String,
        position: (json['position'] ?? '') as String,
      );

  String get displayName {
    if (fullName.trim().isNotEmpty) return fullName;
    if (username.trim().isNotEmpty) return username;
    return 'User #$id';
  }
}

class GroupBrief {
  final int id;
  final String name;

  const GroupBrief({required this.id, required this.name});

  factory GroupBrief.fromJson(Map<String, dynamic> json) => GroupBrief(
        id: (json['id'] ?? 0) as int,
        name: (json['name'] ?? '') as String,
      );
}

class ShareGrant {
  final int id;
  final ShareScope scope;
  final SharePermission permissionLevel;
  final int? targetUserId;
  final UserBrief? targetUser;
  final int? targetGroupId;
  final GroupBrief? targetGroup;
  final ShareApprovalStatus approvalStatus;
  final String? submittedAt;
  final UserBrief? submittedBy;
  final String? approvedAt;
  final UserBrief? approvedBy;
  final String approverNote;
  final String requiredApprover; // 'leader' | 'admin' | 'none'

  const ShareGrant({
    required this.id,
    required this.scope,
    required this.permissionLevel,
    required this.targetUserId,
    required this.targetUser,
    required this.targetGroupId,
    required this.targetGroup,
    required this.approvalStatus,
    required this.submittedAt,
    required this.submittedBy,
    required this.approvedAt,
    required this.approvedBy,
    required this.approverNote,
    required this.requiredApprover,
  });

  factory ShareGrant.fromJson(Map<String, dynamic> json) {
    UserBrief? _user(Object? raw) => raw is Map
        ? UserBrief.fromJson(Map<String, dynamic>.from(raw))
        : null;
    GroupBrief? _group(Object? raw) => raw is Map
        ? GroupBrief.fromJson(Map<String, dynamic>.from(raw))
        : null;
    return ShareGrant(
      id: (json['id'] ?? 0) as int,
      scope: shareScopeFromApi(json['scope']?.toString()),
      permissionLevel:
          sharePermissionFromApi(json['permission_level']?.toString()),
      targetUserId: json['target_user'] as int?,
      targetUser: _user(json['target_user_info']),
      targetGroupId: json['target_group'] as int?,
      targetGroup: _group(json['target_group_info']),
      approvalStatus: shareApprovalFromApi(json['approval_status']?.toString()),
      submittedAt: json['submitted_at'] as String?,
      submittedBy: _user(json['submitted_by_info']),
      approvedAt: json['approved_at'] as String?,
      approvedBy: _user(json['approved_by_info']),
      approverNote: (json['approver_note'] ?? '') as String,
      requiredApprover: (json['required_approver'] ?? 'none') as String,
    );
  }

  bool get isActive => approvalStatus == ShareApprovalStatus.active;
  bool get isPending =>
      approvalStatus == ShareApprovalStatus.pendingLeader ||
      approvalStatus == ShareApprovalStatus.pendingAdmin;
  bool get isRejected => approvalStatus == ShareApprovalStatus.rejected;
}
