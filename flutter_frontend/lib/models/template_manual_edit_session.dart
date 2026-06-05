import 'template.dart';

class TemplateManualEditSession {
  final int id;
  final int templateId;
  final String templateTitle;
  final int? createdById;
  final String createdByName;
  final String status;
  final String provider;
  final String baseVersionLabel;
  final String? editorUrl;
  final bool providerReady;
  final String providerStatusCode;
  final String? providerStatusDetail;
  final bool isActive;
  final String? workingCopyUpdatedAt;
  final String? expiresAt;
  final String? lastActivityAt;
  final String? finishedAt;
  final String? cancelledAt;

  const TemplateManualEditSession({
    required this.id,
    required this.templateId,
    required this.templateTitle,
    this.createdById,
    required this.createdByName,
    required this.status,
    required this.provider,
    required this.baseVersionLabel,
    this.editorUrl,
    this.providerReady = false,
    this.providerStatusCode = '',
    this.providerStatusDetail,
    this.isActive = false,
    this.workingCopyUpdatedAt,
    this.expiresAt,
    this.lastActivityAt,
    this.finishedAt,
    this.cancelledAt,
  });

  factory TemplateManualEditSession.fromJson(Map<String, dynamic> json) {
    return TemplateManualEditSession(
      id: json['id'] as int,
      templateId: json['template'] as int,
      templateTitle: (json['template_title'] ?? '') as String,
      createdById: json['created_by'] as int?,
      createdByName: (json['created_by_name'] ?? '') as String,
      status: (json['status'] ?? '') as String,
      provider: (json['provider'] ?? 'collabora') as String,
      baseVersionLabel: (json['base_version_label'] ?? '1.0') as String,
      editorUrl: json['editor_url'] as String?,
      providerReady: json['provider_ready'] ?? false,
      providerStatusCode: (json['provider_status_code'] ?? '') as String,
      providerStatusDetail: json['provider_status_detail'] as String?,
      isActive: json['is_active'] ?? false,
      workingCopyUpdatedAt: json['working_copy_updated_at'] as String?,
      expiresAt: json['expires_at'] as String?,
      lastActivityAt: json['last_activity_at'] as String?,
      finishedAt: json['finished_at'] as String?,
      cancelledAt: json['cancelled_at'] as String?,
    );
  }
}

class TemplateManualEditFinishResponse {
  final TemplateManualEditSession session;
  final DocumentTemplate template;

  const TemplateManualEditFinishResponse({
    required this.session,
    required this.template,
  });

  factory TemplateManualEditFinishResponse.fromJson(Map<String, dynamic> json) {
    return TemplateManualEditFinishResponse(
      session: TemplateManualEditSession.fromJson(
        json['session'] as Map<String, dynamic>,
      ),
      template: DocumentTemplate.fromJson(
        json['template'] as Map<String, dynamic>,
      ),
    );
  }
}
