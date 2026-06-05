import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../core/api_client.dart';

const promptScopeLabels = <String, String>{
  'template_fill': 'Sinh van ban tu mau',
  'summary': 'Tom tat van ban',
  'word_ai_edit': 'Sua van ban voi AI',
  'chat': 'Tro ly AI / Hoi thoai',
  'compliance_check': 'Kiem tra theo prompt',
};

const promptSourceLabels = <String, String>{
  'curated': 'Curated',
  'user_inline': 'Nguoi dung tao',
  'imported': 'Import',
};

class PromptRecord {
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
  final List<String> usageScopes;
  final String? approverNote;
  final bool isMine;
  final bool canApprove;
  final bool canEdit;
  final bool canDelete;
  final String? myPermission;
  final String peerShareStatus;
  final int peerAudienceCount;
  final bool isPeerSharedToMe;
  final String createdAt;
  final String updatedAt;

  const PromptRecord({
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
    this.usageScopes = const ['template_fill'],
    this.approverNote,
    this.isMine = false,
    this.canApprove = false,
    this.canEdit = false,
    this.canDelete = false,
    this.myPermission,
    this.peerShareStatus = 'none',
    this.peerAudienceCount = 0,
    this.isPeerSharedToMe = false,
    required this.createdAt,
    this.updatedAt = '',
  });

  factory PromptRecord.fromJson(Map<String, dynamic> json) {
    final rawScopes = (json['usage_scope'] as List?) ?? const [];
    return PromptRecord(
      id: json['id'] as int,
      title: (json['title'] ?? '') as String,
      systemContent: json['system_content'] as String?,
      rulesContent: json['rules_content'] as String?,
      status: (json['status'] ?? 'approved') as String,
      visibility: (json['visibility'] ?? 'private') as String,
      ownerId: json['owner'] as int? ?? json['owner_id'] as int?,
      ownerName: (json['owner_name'] ?? '') as String,
      categoryName: json['category_name'] as String?,
      groupId: json['group'] as int? ?? json['group_id'] as int?,
      groupName: json['group_name'] as String?,
      tags: json['tags'] as String?,
      source: json['source'] as String?,
      usageCount: (json['usage_count'] ?? 0) as int,
      usageScopes: rawScopes.map((item) => item.toString()).toList(),
      approverNote: json['approver_note'] as String?,
      isMine: json['is_mine'] == true,
      canApprove: json['can_approve'] == true,
      canEdit: json['can_edit'] == true,
      canDelete: json['can_delete'] == true,
      myPermission: json['my_permission'] as String?,
      peerShareStatus: (json['peer_share_status'] ?? 'none') as String,
      peerAudienceCount: (json['peer_audience_count'] ?? 0) as int,
      isPeerSharedToMe: json['is_peer_shared_to_me'] == true,
      createdAt: (json['created_at'] ?? '') as String,
      updatedAt: (json['updated_at'] ?? '') as String,
    );
  }

  String get statusLabel => switch (status) {
        'approved' => 'Da duyet',
        'pending' => 'Cho admin duyet',
        'pending_leader' => 'Cho truong nhom duyet',
        'rejected' => 'Bi tu choi',
        _ => status,
      };

  String get visibilityLabel => switch (visibility) {
        'public' => 'Cong khai',
        'group' => 'Phong ban',
        _ => 'Rieng tu',
      };

  String get sourceLabel => promptSourceLabels[source] ?? (source ?? 'Khac');
}

String _formatQueryDate(DateTime value) {
  final yyyy = value.year.toString().padLeft(4, '0');
  final mm = value.month.toString().padLeft(2, '0');
  final dd = value.day.toString().padLeft(2, '0');
  return '$yyyy-$mm-$dd';
}

class PromptListQuery {
  final List<String> scopes;
  final String owner;
  final String status;
  final String q;
  final String visibility;
  final String source;
  final String category;
  final String groupFilter;
  final DateTime? createdFrom;
  final DateTime? createdTo;
  final DateTime? updatedFrom;
  final DateTime? updatedTo;
  final String sort;
  final bool reviewMode;
  final bool sharedWithMe;

  const PromptListQuery({
    this.scopes = const [],
    this.owner = 'all',
    this.status = '',
    this.q = '',
    this.visibility = '',
    this.source = '',
    this.category = '',
    this.groupFilter = '',
    this.createdFrom,
    this.createdTo,
    this.updatedFrom,
    this.updatedTo,
    this.sort = 'updated_desc',
    this.reviewMode = false,
    this.sharedWithMe = false,
  });

  Map<String, dynamic> toQueryParameters() {
    final params = <String, dynamic>{};
    if (scopes.isNotEmpty) params['scope'] = scopes;
    if (owner.isNotEmpty && owner != 'all') params['owner'] = owner;
    if (status.isNotEmpty) params['status'] = status;
    if (q.trim().isNotEmpty) params['q'] = q.trim();
    if (visibility.isNotEmpty) params['visibility'] = visibility;
    if (source.isNotEmpty) params['source'] = source;
    if (category.trim().isNotEmpty) params['category'] = category.trim();
    if (groupFilter.trim().isNotEmpty) {
      params['group_filter'] = groupFilter.trim();
    }
    if (createdFrom != null) params['created_from'] = _formatQueryDate(createdFrom!);
    if (createdTo != null) params['created_to'] = _formatQueryDate(createdTo!);
    if (updatedFrom != null) params['updated_from'] = _formatQueryDate(updatedFrom!);
    if (updatedTo != null) params['updated_to'] = _formatQueryDate(updatedTo!);
    if (sort.isNotEmpty && sort != 'updated_desc') params['sort'] = sort;
    if (reviewMode) params['review_mode'] = '1';
    if (sharedWithMe) params['shared_with_me'] = '1';
    return params;
  }

  @override
  bool operator ==(Object other) {
    return other is PromptListQuery &&
        other.owner == owner &&
        other.status == status &&
        other.q == q &&
        other.visibility == visibility &&
        other.source == source &&
        other.category == category &&
        other.groupFilter == groupFilter &&
        other.createdFrom == createdFrom &&
        other.createdTo == createdTo &&
        other.updatedFrom == updatedFrom &&
        other.updatedTo == updatedTo &&
        other.sort == sort &&
        other.reviewMode == reviewMode &&
        other.sharedWithMe == sharedWithMe &&
        _sameScopes(other.scopes, scopes);
  }

  @override
  int get hashCode => Object.hash(
        owner,
        status,
        q,
        visibility,
        source,
        category,
        groupFilter,
        createdFrom,
        createdTo,
        updatedFrom,
        updatedTo,
        sort,
        reviewMode,
        sharedWithMe,
        Object.hashAll(scopes),
      );

  static bool _sameScopes(List<String> a, List<String> b) {
    if (a.length != b.length) return false;
    for (var i = 0; i < a.length; i++) {
      if (a[i] != b[i]) return false;
    }
    return true;
  }
}

Future<List<PromptRecord>> _fetchPrompts({
  PromptListQuery query = const PromptListQuery(),
}) async {
  final resp = await ApiClient().dio.get(
    'prompts/',
    queryParameters: query.toQueryParameters(),
  );
  final data = resp.data;
  final list = data is Map<String, dynamic>
      ? ((data['results'] as List?) ?? const [])
      : ((data as List?) ?? const []);
  return list
      .map(
        (item) => PromptRecord.fromJson(
          Map<String, dynamic>.from(item as Map),
        ),
      )
      .toList();
}

final promptsProvider = FutureProvider<List<PromptRecord>>((ref) async {
  return _fetchPrompts();
});

final promptQueryProvider = FutureProvider.autoDispose
    .family<List<PromptRecord>, PromptListQuery>((ref, query) async {
  return _fetchPrompts(query: query);
});

final promptsPendingReviewProvider = FutureProvider<List<PromptRecord>>((ref) async {
  return _fetchPrompts(
    query: const PromptListQuery(reviewMode: true),
  );
});
