import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../core/api_client.dart';
import '../models/company_user_search.dart';

class PeerSearchQuery {
  final String q;
  final int? departmentId;
  final String? position;
  const PeerSearchQuery({this.q = '', this.departmentId, this.position});

  @override
  bool operator ==(Object other) =>
      other is PeerSearchQuery &&
      other.q == q &&
      other.departmentId == departmentId &&
      other.position == position;

  @override
  int get hashCode => Object.hash(q, departmentId, position);
}

final companyUsersSearchProvider =
    FutureProvider.family.autoDispose<List<CompanyUserSearchItem>, PeerSearchQuery>(
  (ref, query) async {
    final params = <String, dynamic>{};
    if (query.q.trim().isNotEmpty) params['q'] = query.q.trim();
    if (query.departmentId != null) params['department'] = query.departmentId;
    if (query.position != null && query.position!.isNotEmpty) {
      params['position'] = query.position;
    }
    final resp = await ApiClient().dio.get(
      'users/peer-search/',
      queryParameters: params,
    );
    final data = resp.data as Map;
    final list = (data['results'] as List?) ?? [];
    return list
        .map((e) => CompanyUserSearchItem.fromJson(Map<String, dynamic>.from(e as Map)))
        .toList();
  },
);

final peerSearchFiltersProvider = FutureProvider<PeerSearchFilters>((ref) async {
  final resp = await ApiClient().dio.get('users/peer-search/filters/');
  return PeerSearchFilters.fromJson(Map<String, dynamic>.from(resp.data as Map));
});


class PeerEntityRef {
  final String entityType;
  final int entityId;
  const PeerEntityRef({required this.entityType, required this.entityId});

  String get listUrl => '$entityType/$entityId/peer-audience/';
  String get updateUrl => '$entityType/$entityId/peer-audience/update/';
  String get submitUrl => '$entityType/$entityId/peer-submit/';

  @override
  bool operator ==(Object other) =>
      other is PeerEntityRef && other.entityType == entityType && other.entityId == entityId;
  @override
  int get hashCode => Object.hash(entityType, entityId);
}

final peerAudienceProvider =
    FutureProvider.family.autoDispose<PeerAudienceState, PeerEntityRef>(
  (ref, key) async {
    final resp = await ApiClient().dio.get(key.listUrl);
    return PeerAudienceState.fromJson(Map<String, dynamic>.from(resp.data as Map));
  },
);
