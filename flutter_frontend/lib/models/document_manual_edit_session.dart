import 'document.dart';

class DocumentManualEditSession {
  final int id;
  final int documentId;
  final String documentTitle;
  final int? createdById;
  final String createdByName;
  final String status;
  final String provider;
  final int baseVersionNumber;
  final int? committedVersionId;
  final String? editorUrl;
  final bool providerReady;
  final String providerStatusCode;
  final String? providerStatusDetail;
  final bool isActive;
  final String? lockMessage;
  final String? workingCopyUpdatedAt;
  final String? expiresAt;
  final String? lastActivityAt;
  final String? finishedAt;
  final String? cancelledAt;

  const DocumentManualEditSession({
    required this.id,
    required this.documentId,
    required this.documentTitle,
    this.createdById,
    required this.createdByName,
    required this.status,
    required this.provider,
    required this.baseVersionNumber,
    this.committedVersionId,
    this.editorUrl,
    this.providerReady = false,
    this.providerStatusCode = '',
    this.providerStatusDetail,
    this.isActive = false,
    this.lockMessage,
    this.workingCopyUpdatedAt,
    this.expiresAt,
    this.lastActivityAt,
    this.finishedAt,
    this.cancelledAt,
  });

  factory DocumentManualEditSession.fromJson(Map<String, dynamic> json) {
    return DocumentManualEditSession(
      id: json['id'] as int,
      documentId: json['document'] as int,
      documentTitle: (json['document_title'] ?? '') as String,
      createdById: json['created_by'] as int?,
      createdByName: (json['created_by_name'] ?? '') as String,
      status: (json['status'] ?? '') as String,
      provider: (json['provider'] ?? 'collabora') as String,
      baseVersionNumber: (json['base_version_number'] ?? 1) as int,
      committedVersionId: json['committed_version'] as int?,
      editorUrl: json['editor_url'] as String?,
      providerReady: json['provider_ready'] ?? false,
      providerStatusCode: (json['provider_status_code'] ?? '') as String,
      providerStatusDetail: json['provider_status_detail'] as String?,
      isActive: json['is_active'] ?? false,
      lockMessage: json['lock_message'] as String?,
      workingCopyUpdatedAt: json['working_copy_updated_at'] as String?,
      expiresAt: json['expires_at'] as String?,
      lastActivityAt: json['last_activity_at'] as String?,
      finishedAt: json['finished_at'] as String?,
      cancelledAt: json['cancelled_at'] as String?,
    );
  }
}

class DocumentManualEditFinishResponse {
  final DocumentManualEditSession session;
  final Document document;

  const DocumentManualEditFinishResponse({
    required this.session,
    required this.document,
  });

  factory DocumentManualEditFinishResponse.fromJson(Map<String, dynamic> json) {
    return DocumentManualEditFinishResponse(
      session: DocumentManualEditSession.fromJson(
        json['session'] as Map<String, dynamic>,
      ),
      document: Document.fromJson(json['document'] as Map<String, dynamic>),
    );
  }
}
