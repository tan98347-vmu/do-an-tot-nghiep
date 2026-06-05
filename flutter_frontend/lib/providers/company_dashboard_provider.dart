// r5/M9 — Provider lay dashboard + activity timeline cho 1 company.

import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../core/api_client.dart';
import '../models/company_dashboard.dart';

final companyDashboardProvider =
    FutureProvider.family.autoDispose<CompanyDashboard, int>((ref, companyId) async {
  final resp = await ApiClient().dio.get('platform/companies/$companyId/dashboard/');
  return CompanyDashboard.fromJson(Map<String, dynamic>.from(resp.data as Map));
});

final companyActivityProvider =
    FutureProvider.family.autoDispose<List<CompanyActivity>, int>((ref, companyId) async {
  final resp = await ApiClient().dio.get(
    'platform/companies/$companyId/activity/',
    queryParameters: {'limit': 20},
  );
  final data = Map<String, dynamic>.from(resp.data as Map);
  final list = (data['activities'] as List?) ?? [];
  return list
      .map((e) => CompanyActivity.fromJson(Map<String, dynamic>.from(e as Map)))
      .toList();
});
