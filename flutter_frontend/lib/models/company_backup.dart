class CompanyBackup {
  final int id;
  final String name;
  final String kind;
  final List<String> components;
  final int sizeBytes;
  final String status;
  final Map<String, dynamic> manifest;
  final int? createdBy;
  final String createdByName;
  final String createdAt;
  final String? completedAt;
  final String? downloadedAt;
  final String? restoredAt;
  final int? restoredBy;
  final String restoredByName;
  final String errorMessage;
  final String downloadUrl;
  // === BEGIN R5: encryption + signature fields ===
  final bool isEncrypted;
  final String encryptionAlgorithm;
  final String signatureStatus; // 'unsigned' | 'signed' | 'invalid'
  final bool hasSignature;
  // === END R5 ===

  const CompanyBackup({
    required this.id,
    required this.name,
    required this.kind,
    required this.components,
    required this.sizeBytes,
    required this.status,
    required this.manifest,
    required this.createdBy,
    required this.createdByName,
    required this.createdAt,
    required this.completedAt,
    required this.downloadedAt,
    required this.restoredAt,
    required this.restoredBy,
    required this.restoredByName,
    required this.errorMessage,
    required this.downloadUrl,
    this.isEncrypted = false,
    this.encryptionAlgorithm = '',
    this.signatureStatus = 'unsigned',
    this.hasSignature = false,
  });

  factory CompanyBackup.fromJson(Map<String, dynamic> json) => CompanyBackup(
        id: json['id'] as int,
        name: (json['name'] ?? '') as String,
        kind: (json['kind'] ?? 'manual') as String,
        components: ((json['components'] ?? []) as List).map((e) => e.toString()).toList(),
        sizeBytes: (json['size_bytes'] ?? 0) as int,
        status: (json['status'] ?? 'creating') as String,
        manifest: (json['manifest'] as Map?)?.cast<String, dynamic>() ?? {},
        createdBy: json['created_by'] as int?,
        createdByName: (json['created_by_name'] ?? '') as String,
        createdAt: (json['created_at'] ?? '') as String,
        completedAt: json['completed_at'] as String?,
        downloadedAt: json['downloaded_at'] as String?,
        restoredAt: json['restored_at'] as String?,
        restoredBy: json['restored_by'] as int?,
        restoredByName: (json['restored_by_name'] ?? '') as String,
        errorMessage: (json['error_message'] ?? '') as String,
        downloadUrl: (json['download_url'] ?? '') as String,
        isEncrypted: json['is_encrypted'] == true,
        encryptionAlgorithm: (json['encryption_algorithm'] ?? '') as String,
        signatureStatus: (json['signature_status'] ?? 'unsigned') as String,
        hasSignature: json['has_signature'] == true,
      );

  String get kindLabel => kind == 'auto' ? 'Tự động' : 'Thủ công';

  String get statusLabel => switch (status) {
        'creating' => 'Đang tạo',
        'ready' => 'Sẵn sàng',
        'failed' => 'Thất bại',
        'restoring' => 'Đang khôi phục',
        'restored' => 'Đã khôi phục',
        'deleted' => 'Đã xoá',
        _ => status,
      };

  String get sizeDisplay {
    if (sizeBytes < 1024) return '$sizeBytes B';
    if (sizeBytes < 1024 * 1024) return '${(sizeBytes / 1024).toStringAsFixed(1)} KB';
    if (sizeBytes < 1024 * 1024 * 1024) return '${(sizeBytes / (1024 * 1024)).toStringAsFixed(1)} MB';
    return '${(sizeBytes / (1024 * 1024 * 1024)).toStringAsFixed(2)} GB';
  }
}

class CompanyBackupSettings {
  final bool autoEnabled;
  final int autoIntervalDays;
  final int retentionCount;
  final bool notifyAdminEmail;
  final String? lastAutoRunAt;
  final bool hasPassword;

  const CompanyBackupSettings({
    required this.autoEnabled,
    required this.autoIntervalDays,
    required this.retentionCount,
    required this.notifyAdminEmail,
    required this.lastAutoRunAt,
    required this.hasPassword,
  });

  factory CompanyBackupSettings.fromJson(Map<String, dynamic> json) => CompanyBackupSettings(
        autoEnabled: json['auto_enabled'] == true,
        autoIntervalDays: (json['auto_interval_days'] ?? 30) as int,
        retentionCount: (json['retention_count'] ?? 12) as int,
        notifyAdminEmail: json['notify_admin_email'] == true,
        lastAutoRunAt: json['last_auto_run_at'] as String?,
        hasPassword: json['has_password'] == true,
      );
}

class BackupComponent {
  final String key;
  final String label;

  const BackupComponent({required this.key, required this.label});

  factory BackupComponent.fromJson(Map<String, dynamic> json) => BackupComponent(
        key: (json['key'] ?? '') as String,
        label: (json['label'] ?? '') as String,
      );
}
