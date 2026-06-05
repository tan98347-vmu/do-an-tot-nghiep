// r5/M9 — DTO ket qua tu /api/platform/companies/<id>/dashboard/
//
// Schema:
//   {
//     'company': {id, code, name, status, address, email, phone, website, ...},
//     'counts': {users, departments, positions, templates, documents, prompts, backups},
//     'storage': {total_bytes, by_subdir: {dirName: bytes}},
//     'last_backup': {id, name, status, kind, size_bytes, is_encrypted, signature_status} | null
//   }

class CompanyDashboard {
  final CompanyInfo company;
  final Map<String, int> counts;
  final CompanyExtendedStats extended;
  final int storageTotalBytes;
  final Map<String, int> storageBySubdir;
  final LastBackupInfo? lastBackup;
  final OrgTreeNode? orgTreeRoot;
  final Map<String, int> orgTreeTotals;

  const CompanyDashboard({
    required this.company,
    required this.counts,
    required this.extended,
    required this.storageTotalBytes,
    required this.storageBySubdir,
    required this.lastBackup,
    required this.orgTreeRoot,
    required this.orgTreeTotals,
  });

  factory CompanyDashboard.fromJson(Map<String, dynamic> json) {
    final storage = (json['storage'] as Map?)?.cast<String, dynamic>() ?? {};
    final bySubdirRaw =
        (storage['by_subdir'] as Map?)?.cast<String, dynamic>() ?? {};
    final bySubdir =
        bySubdirRaw.map((k, v) => MapEntry(k, (v as num).toInt()));
    final countsRaw = (json['counts'] as Map?)?.cast<String, dynamic>() ?? {};
    final counts = countsRaw.map((k, v) => MapEntry(k, (v as num).toInt()));
    final lastBackupJson = json['last_backup'];

    final extJson = (json['extended'] as Map?)?.cast<String, dynamic>() ?? {};
    final treeJson = (json['org_tree'] as Map?)?.cast<String, dynamic>() ?? {};
    final rootJson = (treeJson['root'] as Map?)?.cast<String, dynamic>();
    final totalsJson =
        (treeJson['totals'] as Map?)?.cast<String, dynamic>() ?? {};
    final totals =
        totalsJson.map((k, v) => MapEntry(k, ((v as num?) ?? 0).toInt()));
    return CompanyDashboard(
      company: CompanyInfo.fromJson(
          Map<String, dynamic>.from((json['company'] ?? {}) as Map)),
      counts: counts,
      extended: CompanyExtendedStats.fromJson(extJson),
      storageTotalBytes: ((storage['total_bytes'] as num?) ?? 0).toInt(),
      storageBySubdir: bySubdir,
      lastBackup: lastBackupJson == null
          ? null
          : LastBackupInfo.fromJson(
              Map<String, dynamic>.from(lastBackupJson as Map)),
      orgTreeRoot: rootJson == null ? null : OrgTreeNode.fromJson(rootJson),
      orgTreeTotals: totals,
    );
  }
}

class CompanyExtendedStats {
  final int documents30d;
  final int templates30d;
  final int usersActive30d;
  final int membersWithDepartment;
  final int membersWithoutDepartment;
  final int aiCalls30d;
  final int aiCallsTotal;
  final int pendingDocShares;
  final int pendingTemplateShares;
  final Map<String, int> templatesByStatus;
  final Map<String, int> documentsByStatus;

  const CompanyExtendedStats({
    required this.documents30d,
    required this.templates30d,
    required this.usersActive30d,
    required this.membersWithDepartment,
    required this.membersWithoutDepartment,
    required this.aiCalls30d,
    required this.aiCallsTotal,
    required this.pendingDocShares,
    required this.pendingTemplateShares,
    required this.templatesByStatus,
    required this.documentsByStatus,
  });

  factory CompanyExtendedStats.fromJson(Map<String, dynamic> j) {
    Map<String, int> _m(dynamic raw) {
      if (raw is Map) {
        return raw.map((k, v) =>
            MapEntry(k.toString(), ((v as num?) ?? 0).toInt()));
      }
      return <String, int>{};
    }

    int _i(dynamic raw) => ((raw as num?) ?? 0).toInt();
    return CompanyExtendedStats(
      documents30d: _i(j['documents_30d']),
      templates30d: _i(j['templates_30d']),
      usersActive30d: _i(j['users_active_30d']),
      membersWithDepartment: _i(j['members_with_department']),
      membersWithoutDepartment: _i(j['members_without_department']),
      aiCalls30d: _i(j['ai_calls_30d']),
      aiCallsTotal: _i(j['ai_calls_total']),
      pendingDocShares: _i(j['pending_doc_shares']),
      pendingTemplateShares: _i(j['pending_template_shares']),
      templatesByStatus: _m(j['templates_by_status']),
      documentsByStatus: _m(j['documents_by_status']),
    );
  }
}

class OrgTreeNode {
  final String type; // 'company' | 'department' | 'member'
  final int? id;
  final String name;
  final String? code;
  final String subtitle;
  final String? role; // for members: 'leader' | 'member'
  final Map<String, dynamic>? manager;
  final List<OrgTreeNode> children;

  const OrgTreeNode({
    required this.type,
    required this.id,
    required this.name,
    required this.code,
    required this.subtitle,
    required this.role,
    required this.manager,
    required this.children,
  });

  factory OrgTreeNode.fromJson(Map<String, dynamic> j) {
    final rawChildren = (j['children'] as List?) ?? const [];
    return OrgTreeNode(
      type: (j['type'] ?? 'member') as String,
      id: j['id'] is num ? (j['id'] as num).toInt() : null,
      name: (j['name'] ?? '') as String,
      code: j['code']?.toString(),
      subtitle: (j['subtitle'] ?? '') as String,
      role: j['role']?.toString(),
      manager: (j['manager'] as Map?)?.cast<String, dynamic>(),
      children: rawChildren
          .map((c) => OrgTreeNode.fromJson(
              Map<String, dynamic>.from(c as Map)))
          .toList(growable: false),
    );
  }
}

class CompanyInfo {
  final int id;
  final String code;
  final String slug;
  final String name;
  final String status;
  final String description;
  final String industry;
  final String address;
  final String email;
  final String phone;
  final String website;
  final String companyContext;
  final String? createdAt;
  final String? updatedAt;

  const CompanyInfo({
    required this.id,
    required this.code,
    required this.slug,
    required this.name,
    required this.status,
    required this.description,
    required this.industry,
    required this.address,
    required this.email,
    required this.phone,
    required this.website,
    required this.companyContext,
    required this.createdAt,
    required this.updatedAt,
  });

  factory CompanyInfo.fromJson(Map<String, dynamic> j) => CompanyInfo(
        id: (j['id'] ?? 0) as int,
        code: (j['code'] ?? '') as String,
        slug: (j['slug'] ?? '') as String,
        name: (j['name'] ?? '') as String,
        status: (j['status'] ?? '') as String,
        description: (j['description'] ?? '') as String,
        industry: (j['industry'] ?? '') as String,
        address: (j['address'] ?? '') as String,
        email: (j['email'] ?? '') as String,
        phone: (j['phone'] ?? '') as String,
        website: (j['website'] ?? '') as String,
        companyContext: (j['company_context'] ?? '') as String,
        createdAt: j['created_at'] as String?,
        updatedAt: j['updated_at'] as String?,
      );

  String get statusLabel => switch (status) {
        'draft' => 'Nháp',
        'active' => 'Hoạt động',
        'locked' => 'Bị khóa',
        'archived' => 'Lưu trữ',
        'deleted' => 'Đã xóa',
        _ => status,
      };
}

class LastBackupInfo {
  final int id;
  final String name;
  final String status;
  final String kind;
  final int sizeBytes;
  final String? createdAt;
  final String? completedAt;
  final bool isEncrypted;
  final String signatureStatus;
  final bool hasSignature;

  const LastBackupInfo({
    required this.id,
    required this.name,
    required this.status,
    required this.kind,
    required this.sizeBytes,
    required this.createdAt,
    required this.completedAt,
    required this.isEncrypted,
    required this.signatureStatus,
    required this.hasSignature,
  });

  factory LastBackupInfo.fromJson(Map<String, dynamic> j) => LastBackupInfo(
        id: (j['id'] ?? 0) as int,
        name: (j['name'] ?? '') as String,
        status: (j['status'] ?? '') as String,
        kind: (j['kind'] ?? '') as String,
        sizeBytes: ((j['size_bytes'] as num?) ?? 0).toInt(),
        createdAt: j['created_at'] as String?,
        completedAt: j['completed_at'] as String?,
        isEncrypted: j['is_encrypted'] == true,
        signatureStatus: (j['signature_status'] ?? 'unsigned') as String,
        hasSignature: j['has_signature'] == true,
      );
}

class CompanyActivity {
  final String at;
  final String actor;
  final String action;
  final String detail;
  final String targetType;
  final int targetId;

  const CompanyActivity({
    required this.at,
    required this.actor,
    required this.action,
    required this.detail,
    required this.targetType,
    required this.targetId,
  });

  factory CompanyActivity.fromJson(Map<String, dynamic> j) => CompanyActivity(
        at: (j['at'] ?? '') as String,
        actor: (j['actor'] ?? '') as String,
        action: (j['action'] ?? '') as String,
        detail: (j['detail'] ?? '') as String,
        targetType: (j['target_type'] ?? '') as String,
        targetId: ((j['target_id'] as num?) ?? 0).toInt(),
      );
}

String formatBytes(int bytes) {
  if (bytes < 1024) return '$bytes B';
  if (bytes < 1024 * 1024) return '${(bytes / 1024).toStringAsFixed(1)} KB';
  if (bytes < 1024 * 1024 * 1024) return '${(bytes / (1024 * 1024)).toStringAsFixed(1)} MB';
  return '${(bytes / (1024 * 1024 * 1024)).toStringAsFixed(2)} GB';
}
