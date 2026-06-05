import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../core/api_client.dart';
import '../models/company_backup.dart';

final companyBackupsProvider = FutureProvider<List<CompanyBackup>>((ref) async {
  final resp = await ApiClient().dio.get('admin/backups/');
  return (resp.data as List)
      .map((e) => CompanyBackup.fromJson(e as Map<String, dynamic>))
      .toList();
});

/// r5/M10: goi endpoint verify-only. Tra {ok, details, signature_status}.
final backupVerifyProvider = FutureProvider.family<Map<String, dynamic>, int>((ref, id) async {
  final resp = await ApiClient().dio.post('admin/backups/$id/verify/');
  return Map<String, dynamic>.from(resp.data as Map);
});

final companyBackupSettingsProvider = FutureProvider<CompanyBackupSettings>((ref) async {
  final resp = await ApiClient().dio.get('admin/backups/settings/');
  return CompanyBackupSettings.fromJson(
      Map<String, dynamic>.from(resp.data as Map));
});

final backupComponentsProvider = FutureProvider<List<BackupComponent>>((ref) async {
  final resp = await ApiClient().dio.get('admin/backups/components/');
  final data = resp.data as Map;
  final list = (data['components'] as List?) ?? [];
  return list
      .map((e) => BackupComponent.fromJson(Map<String, dynamic>.from(e as Map)))
      .toList();
});
