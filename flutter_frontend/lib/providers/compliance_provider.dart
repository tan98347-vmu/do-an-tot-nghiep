// r2/M4 — Provider goi /api/compliance-check/{run,history,<id>}/

import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../core/api_client.dart';
import '../models/compliance_result.dart';

class ComplianceApi {
  final ApiClient _client;
  ComplianceApi(this._client);

  Future<ComplianceResult> run({
    required String targetType,
    required int targetId,
    required int promptId,
    bool force = false,
  }) async {
    final resp = await _client.dio.post(
      'compliance-check/run/',
      data: {
        'target_type': targetType,
        'target_id': targetId,
        'prompt_id': promptId,
        if (force) 'force': true,
      },
    );
    return ComplianceResult.fromJson(Map<String, dynamic>.from(resp.data as Map));
  }

  Future<List<ComplianceResult>> history({
    required String targetType,
    required int targetId,
    int limit = 10,
  }) async {
    final resp = await _client.dio.get(
      'compliance-check/history/',
      queryParameters: {
        'target_type': targetType,
        'target_id': targetId,
        'limit': limit,
      },
    );
    final data = resp.data;
    final list = data is Map ? (data['results'] ?? []) as List : data as List;
    return list
        .map((e) => ComplianceResult.fromJson(Map<String, dynamic>.from(e as Map)))
        .toList();
  }

  Future<ComplianceResult> detail(int id) async {
    final resp = await _client.dio.get('compliance-check/$id/');
    return ComplianceResult.fromJson(Map<String, dynamic>.from(resp.data as Map));
  }
}

final complianceApiProvider = Provider<ComplianceApi>((ref) => ComplianceApi(ApiClient()));

final complianceHistoryProvider = FutureProvider.family
    .autoDispose<List<ComplianceResult>, ({String type, int id})>((ref, args) async {
  return ref.read(complianceApiProvider).history(
        targetType: args.type,
        targetId: args.id,
        limit: 10,
      );
});
