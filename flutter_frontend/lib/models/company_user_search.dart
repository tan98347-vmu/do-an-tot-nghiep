class CompanyUserSearchItem {
  final int id;
  final String username;
  final String fullName;
  final String email;
  final String position;
  final String? avatarUrl;
  final List<DepartmentRef> departments;
  final List<GroupRef> groups;

  const CompanyUserSearchItem({
    required this.id,
    required this.username,
    required this.fullName,
    required this.email,
    required this.position,
    this.avatarUrl,
    this.departments = const [],
    this.groups = const [],
  });

  factory CompanyUserSearchItem.fromJson(Map<String, dynamic> json) =>
      CompanyUserSearchItem(
        id: json['id'] as int,
        username: (json['username'] ?? '') as String,
        fullName: (json['full_name'] ?? '') as String,
        email: (json['email'] ?? '') as String,
        position: (json['position'] ?? '') as String,
        avatarUrl: json['avatar_url'] as String?,
        departments: ((json['departments'] as List?) ?? const [])
            .map((e) => DepartmentRef.fromJson(Map<String, dynamic>.from(e as Map)))
            .toList(),
        groups: ((json['groups'] as List?) ?? const [])
            .map((e) => GroupRef.fromJson(Map<String, dynamic>.from(e as Map)))
            .toList(),
      );

  String get departmentNames =>
      departments.map((d) => d.name).where((n) => n.isNotEmpty).join(', ');
}

class DepartmentRef {
  final int id;
  final String name;
  const DepartmentRef({required this.id, required this.name});
  factory DepartmentRef.fromJson(Map<String, dynamic> json) =>
      DepartmentRef(id: json['id'] as int, name: (json['name'] ?? '') as String);
}

class GroupRef {
  final String name;
  final String role;
  const GroupRef({required this.name, required this.role});
  factory GroupRef.fromJson(Map<String, dynamic> json) =>
      GroupRef(name: (json['name'] ?? '') as String, role: (json['role'] ?? '') as String);
}

class PeerSearchFilters {
  final List<DepartmentRef> departments;
  final List<String> positions;
  const PeerSearchFilters({required this.departments, required this.positions});
  factory PeerSearchFilters.fromJson(Map<String, dynamic> json) => PeerSearchFilters(
        departments: ((json['departments'] as List?) ?? const [])
            .map((e) => DepartmentRef.fromJson(Map<String, dynamic>.from(e as Map)))
            .toList(),
        positions: ((json['positions'] as List?) ?? const [])
            .map((e) => e.toString())
            .toList(),
      );
}

class PeerAudienceMemberRef {
  final int id;
  final String username;
  final String fullName;
  final String email;
  final String position;
  final int? addedById;
  final String? createdAt;

  const PeerAudienceMemberRef({
    required this.id,
    required this.username,
    required this.fullName,
    required this.email,
    required this.position,
    this.addedById,
    this.createdAt,
  });

  factory PeerAudienceMemberRef.fromJson(Map<String, dynamic> json) =>
      PeerAudienceMemberRef(
        id: json['id'] as int,
        username: (json['username'] ?? '') as String,
        fullName: (json['full_name'] ?? '') as String,
        email: (json['email'] ?? '') as String,
        position: (json['position'] ?? '') as String,
        addedById: json['added_by_id'] as int?,
        createdAt: json['created_at'] as String?,
      );
}

class PeerAudienceState {
  final String status;
  final String approverNote;
  final String? submittedAt;
  final String? approvedAt;
  final List<PeerAudienceMemberRef> members;

  const PeerAudienceState({
    required this.status,
    required this.approverNote,
    required this.submittedAt,
    required this.approvedAt,
    required this.members,
  });

  factory PeerAudienceState.fromJson(Map<String, dynamic> json) => PeerAudienceState(
        status: (json['peer_share_status'] ?? 'none') as String,
        approverNote: (json['peer_share_approver_note'] ?? '') as String,
        submittedAt: json['peer_share_submitted_at'] as String?,
        approvedAt: json['peer_share_approved_at'] as String?,
        members: ((json['members'] as List?) ?? const [])
            .map((e) => PeerAudienceMemberRef.fromJson(Map<String, dynamic>.from(e as Map)))
            .toList(),
      );

  String get statusLabel => switch (status) {
        'none' => 'Chưa chia sẻ',
        'pending_leader' => 'Chờ trưởng nhóm duyệt',
        'active' => 'Đã kích hoạt',
        'rejected' => 'Bị từ chối',
        _ => status,
      };
}
