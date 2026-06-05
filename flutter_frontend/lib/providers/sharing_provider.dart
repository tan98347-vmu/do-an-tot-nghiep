// Provider Riverpod 3.x cho viec quan ly ShareGrant.
//
// Pattern: dung FutureProvider.autoDispose.family cho doc va helper SharingActions
// cho mutation (style giong documents_provider trong codebase).

import 'dart:async';

import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../core/api_client.dart';
import '../models/share_grant.dart';

@immutable
class SharingKey {
  final String entityType; // 'templates' | 'documents' | 'prompts'
  final int entityId;
  const SharingKey(this.entityType, this.entityId);

  String get baseUrl => '$entityType/$entityId/shares/';

  @override
  bool operator ==(Object other) =>
      other is SharingKey &&
      other.entityType == entityType &&
      other.entityId == entityId;

  @override
  int get hashCode => Object.hash(entityType, entityId);
}


/// Provider tra ve danh sach ShareGrant cua mot resource cu the.
final sharingGrantsProvider =
    FutureProvider.autoDispose.family<List<ShareGrant>, SharingKey>(
  (ref, key) async {
    final resp = await ApiClient().dio.get(key.baseUrl);
    final data = Map<String, dynamic>.from(resp.data as Map);
    final list = (data['grants'] as List?)
            ?.map((e) =>
                ShareGrant.fromJson(Map<String, dynamic>.from(e as Map)))
            .toList() ??
        <ShareGrant>[];
    return list;
  },
);


/// Ket qua tao grant: loi (neu co) hoac grant vua tao (kem approval_status).
class CreateGrantResult {
  final String? error;
  final ShareGrant? grant;
  const CreateGrantResult({this.error, this.grant});
  bool get ok => error == null;
}


/// Helper static cho cac thao tac mutation.
class SharingActions {
  final WidgetRef ref;
  final SharingKey key;
  SharingActions(this.ref, this.key);

  String get _baseUrl => key.baseUrl;

  Future<void> _refresh() async {
    ref.invalidate(sharingGrantsProvider(key));
  }

  Future<CreateGrantResult> createGrant({
    required ShareScope scope,
    required SharePermission permission,
    int? targetUserId,
    int? targetGroupId,
    bool autoSubmit = true,
  }) async {
    try {
      final resp = await ApiClient().dio.post(_baseUrl, data: {
        'scope': shareScopeToApi(scope),
        'permission_level': sharePermissionToApi(permission),
        if (targetUserId != null) 'target_user': targetUserId,
        if (targetGroupId != null) 'target_group': targetGroupId,
        'auto_submit': autoSubmit,
      });
      await _refresh();
      ShareGrant? grant;
      if (resp.data is Map) {
        grant = ShareGrant.fromJson(Map<String, dynamic>.from(resp.data as Map));
      }
      return CreateGrantResult(grant: grant);
    } on DioException catch (e) {
      return CreateGrantResult(error: _err(e));
    }
  }

  Future<String?> updatePermission(int grantId, SharePermission permission) async {
    try {
      await ApiClient().dio.patch('$_baseUrl$grantId/', data: {
        'permission_level': sharePermissionToApi(permission),
      });
      await _refresh();
      return null;
    } on DioException catch (e) {
      return _err(e);
    }
  }

  Future<String?> revokeGrant(int grantId) async {
    try {
      await ApiClient().dio.delete('$_baseUrl$grantId/');
      await _refresh();
      return null;
    } on DioException catch (e) {
      return _err(e);
    }
  }

  Future<String?> submitGrant(int grantId) async {
    return _grantAction(grantId, 'submit');
  }

  Future<String?> approveGrant(int grantId, {String note = ''}) async {
    return _grantAction(grantId, 'approve', note: note);
  }

  Future<String?> rejectGrant(int grantId, {String note = ''}) async {
    return _grantAction(grantId, 'reject', note: note);
  }

  Future<String?> _grantAction(int grantId, String action,
      {String note = ''}) async {
    try {
      await ApiClient()
          .dio
          .post('$_baseUrl$grantId/$action/', data: {'note': note});
      await _refresh();
      return null;
    } on DioException catch (e) {
      return _err(e);
    }
  }

  String _err(DioException e) {
    final data = e.response?.data;
    if (data is Map && data['detail'] != null) return data['detail'].toString();
    return e.message ?? 'Loi khong xac dinh';
  }
}


// =============================================================================
// Cross-entity providers cho inbox va shared-with-me
// =============================================================================

class PendingItem {
  final String entityType;
  final int entityId;
  final String entityTitle;
  final String ownerName;
  final DateTime? submittedAt;
  final ShareGrant grant;
  const PendingItem({
    required this.entityType,
    required this.entityId,
    required this.entityTitle,
    required this.grant,
    this.ownerName = '',
    this.submittedAt,
  });
}

/// Bo loc/sap xep cho man "Chia se cho duyet".
@immutable
class PendingApprovalsFilter {
  final String q; // tim theo ten resource / chu so huu
  final String entityType; // '' | templates | documents | prompts
  final String scope; // '' | group | colleagues | everyone
  final String sort; // newest | oldest

  const PendingApprovalsFilter({
    this.q = '',
    this.entityType = '',
    this.scope = '',
    this.sort = 'newest',
  });

  PendingApprovalsFilter copyWith({
    String? q,
    String? entityType,
    String? scope,
    String? sort,
  }) =>
      PendingApprovalsFilter(
        q: q ?? this.q,
        entityType: entityType ?? this.entityType,
        scope: scope ?? this.scope,
        sort: sort ?? this.sort,
      );

  Map<String, dynamic> toQueryParameters() => {
        if (q.trim().isNotEmpty) 'q': q.trim(),
        if (entityType.isNotEmpty) 'entity_type': entityType,
        if (scope.isNotEmpty) 'scope': scope,
        'sort': sort,
      };

  @override
  bool operator ==(Object other) =>
      other is PendingApprovalsFilter &&
      other.q == q &&
      other.entityType == entityType &&
      other.scope == scope &&
      other.sort == sort;

  @override
  int get hashCode => Object.hash(q, entityType, scope, sort);
}

final pendingApprovalsListProvider = FutureProvider.autoDispose
    .family<List<PendingItem>, PendingApprovalsFilter>((ref, filter) async {
  final resp = await ApiClient().dio.get(
    'shares/pending/',
    queryParameters: filter.toQueryParameters(),
  );
  final data = Map<String, dynamic>.from(resp.data as Map);
  final list = (data['pending'] as List?) ?? [];
  return list.map((e) {
    final m = Map<String, dynamic>.from(e as Map);
    return PendingItem(
      entityType: (m['entity_type'] ?? '') as String,
      entityId: (m['entity_id'] ?? 0) as int,
      entityTitle: (m['entity_title'] ?? '') as String,
      ownerName: (m['owner_name'] ?? '') as String,
      submittedAt: DateTime.tryParse((m['submitted_at'] ?? '').toString()),
      grant: ShareGrant.fromJson(Map<String, dynamic>.from(m['grant'] as Map)),
    );
  }).toList();
});


/// Dem so yeu cau chia se dang cho user nay duyet (badge tren nav "Chia se cho duyet").
/// Lam moi dinh ky 5s giong cac badge khac. Sau nay co the doi sang endpoint
/// "chua doc" (last_seen) khi co co che danh dau da doc.
final sharingPendingCountProvider = StreamProvider.autoDispose<int>((ref) {
  final controller = StreamController<int>();
  const refreshInterval = Duration(seconds: 5);

  Timer? timer;
  var disposed = false;
  var inFlight = false;
  int? latest;

  Future<void> refresh() async {
    if (disposed || inFlight) return;
    inFlight = true;
    try {
      final resp = await ApiClient().dio.get(
        'shares/pending/',
        queryParameters: const {'sort': 'newest'},
      );
      final data = Map<String, dynamic>.from(resp.data as Map);
      latest = (data['count'] as int?) ??
          (data['pending'] as List?)?.length ??
          0;
      if (!disposed) controller.add(latest!);
    } catch (error, stackTrace) {
      if (disposed) return;
      if (latest != null) {
        controller.add(latest!);
      } else {
        controller.addError(error, stackTrace);
      }
    } finally {
      inFlight = false;
    }
  }

  Future.microtask(refresh);
  timer = Timer.periodic(refreshInterval, (_) => refresh());

  ref.onDispose(() {
    disposed = true;
    timer?.cancel();
    controller.close();
  });

  return controller.stream;
});


class SharedWithMeItem {
  final String entityType;
  final int entityId;
  final String entityTitle;
  final SharePermission permission;
  const SharedWithMeItem({
    required this.entityType,
    required this.entityId,
    required this.entityTitle,
    required this.permission,
  });
}

final sharedWithMeProvider =
    FutureProvider.autoDispose<List<SharedWithMeItem>>((ref) async {
  final resp = await ApiClient().dio.get('shares/shared-with-me/');
  final data = Map<String, dynamic>.from(resp.data as Map);
  final list = (data['items'] as List?) ?? [];
  return list.map((e) {
    final m = Map<String, dynamic>.from(e as Map);
    return SharedWithMeItem(
      entityType: (m['entity_type'] ?? '') as String,
      entityId: (m['entity_id'] ?? 0) as int,
      entityTitle: (m['entity_title'] ?? '') as String,
      permission: sharePermissionFromApi(m['my_permission']?.toString()),
    );
  }).toList();
});
