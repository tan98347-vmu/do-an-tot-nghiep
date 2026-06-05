// r2/M4 — DTO ket qua compliance check.

class ComplianceMissingItem {
  final String requirement;
  final String explanation;
  const ComplianceMissingItem({required this.requirement, required this.explanation});
  factory ComplianceMissingItem.fromJson(Map<String, dynamic> j) => ComplianceMissingItem(
        requirement: (j['requirement'] ?? '') as String,
        explanation: (j['explanation'] ?? '') as String,
      );
}

class ComplianceResult {
  final int id;
  final bool passed;
  final List<ComplianceMissingItem> itemsMissing;
  final String? message;
  final int? promptId;
  final String? promptTitle;
  final String targetType;
  final int targetId;
  final String checkedAt;

  const ComplianceResult({
    required this.id,
    required this.passed,
    required this.itemsMissing,
    required this.message,
    required this.promptId,
    required this.promptTitle,
    required this.targetType,
    required this.targetId,
    required this.checkedAt,
  });

  factory ComplianceResult.fromJson(Map<String, dynamic> j) {
    final rawItems = (j['items_missing'] ?? j['items_missing_json'] ?? []) as List;
    return ComplianceResult(
      id: (j['id'] ?? 0) as int,
      passed: j['passed'] == true,
      itemsMissing: rawItems
          .map((e) => ComplianceMissingItem.fromJson(Map<String, dynamic>.from(e as Map)))
          .toList(),
      message: j['message'] as String?,
      promptId: j['prompt_id'] as int?,
      promptTitle: j['prompt_title'] as String?,
      targetType: (j['target_type'] ?? 'document') as String,
      targetId: (j['target_id'] ?? 0) as int,
      checkedAt: (j['checked_at'] ?? '') as String,
    );
  }

  /// Message chinh xac theo yeu cau goc khi pass.
  static const String passMessage =
      'Văn bản/mẫu văn bản đã đáp ứng được những yêu cầu mà bạn đưa ra';
}
