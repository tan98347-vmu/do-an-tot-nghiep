enum PeerPermission { view, edit, delete, owner }

PeerPermission peerPermissionFromApi(String? value) => switch (value) {
      'owner' => PeerPermission.owner,
      'delete' => PeerPermission.delete,
      'edit' => PeerPermission.edit,
      _ => PeerPermission.view,
    };

String peerPermissionToApi(PeerPermission value) => switch (value) {
      PeerPermission.owner => 'owner',
      PeerPermission.delete => 'delete',
      PeerPermission.edit => 'edit',
      PeerPermission.view => 'view',
    };

String peerPermissionLabel(PeerPermission value) => switch (value) {
      PeerPermission.view => 'Chi xem',
      PeerPermission.edit => 'Xem va sua',
      PeerPermission.delete => 'Toan quyen',
      PeerPermission.owner => 'Owner',
    };

class PeerAudienceEntry {
  final int userId;
  final PeerPermission permissionLevel;
  final String? userName;
  final String? userEmail;
  final String? userUsername;
  final String? userPosition;
  final int? addedById;
  final String? createdAt;

  const PeerAudienceEntry({
    required this.userId,
    required this.permissionLevel,
    this.userName,
    this.userEmail,
    this.userUsername,
    this.userPosition,
    this.addedById,
    this.createdAt,
  });

  factory PeerAudienceEntry.fromJson(Map<String, dynamic> json) {
    final user = json['user'] is Map<String, dynamic>
        ? json['user'] as Map<String, dynamic>
        : (json['user'] is Map ? Map<String, dynamic>.from(json['user'] as Map) : <String, dynamic>{});
    return PeerAudienceEntry(
      userId: (json['user_id'] ?? user['id'] ?? 0) as int,
      permissionLevel: peerPermissionFromApi(
        (json['permission_level'] ?? user['permission_level'])?.toString(),
      ),
      userName: (user['full_name'] ?? json['full_name']) as String?,
      userEmail: (user['email'] ?? json['email']) as String?,
      userUsername: (user['username'] ?? json['username']) as String?,
      userPosition: (user['position'] ?? json['position']) as String?,
      addedById: json['added_by_id'] as int?,
      createdAt: json['created_at'] as String?,
    );
  }

  PeerAudienceEntry copyWith({
    PeerPermission? permissionLevel,
  }) {
    return PeerAudienceEntry(
      userId: userId,
      permissionLevel: permissionLevel ?? this.permissionLevel,
      userName: userName,
      userEmail: userEmail,
      userUsername: userUsername,
      userPosition: userPosition,
      addedById: addedById,
      createdAt: createdAt,
    );
  }

  Map<String, dynamic> toAudiencePayload() => {
        'user_id': userId,
        'permission_level': peerPermissionToApi(permissionLevel),
      };

  String get displayName {
    final name = (userName ?? '').trim();
    if (name.isNotEmpty) return name;
    final username = (userUsername ?? '').trim();
    if (username.isNotEmpty) return username;
    return 'User #$userId';
  }
}

class PeerAudienceState {
  final String status;
  final String approverNote;
  final String? submittedAt;
  final String? approvedAt;
  final List<PeerAudienceEntry> audiences;

  const PeerAudienceState({
    required this.status,
    required this.approverNote,
    required this.submittedAt,
    required this.approvedAt,
    required this.audiences,
  });

  factory PeerAudienceState.fromJson(Map<String, dynamic> json) {
    final audienceList = (json['audiences'] as List?) ??
        (json['members'] as List?) ??
        const [];
    return PeerAudienceState(
      status: (json['peer_share_status'] ?? 'none') as String,
      approverNote: (json['peer_share_approver_note'] ?? '') as String,
      submittedAt: json['peer_share_submitted_at'] as String?,
      approvedAt: json['peer_share_approved_at'] as String?,
      audiences: audienceList
          .map((item) => PeerAudienceEntry.fromJson(Map<String, dynamic>.from(item as Map)))
          .toList(),
    );
  }

  String get statusLabel => switch (status) {
        'none' => 'Chua chia se',
        'pending_leader' => 'Cho truong nhom duyet',
        'active' => 'Da kich hoat',
        'rejected' => 'Bi tu choi',
        _ => status,
      };
}
