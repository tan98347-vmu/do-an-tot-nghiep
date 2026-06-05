// Tệp này dùng để: mô tả cấu trúc dữ liệu client dùng để đọc và ghi API trong flutter_frontend/lib/models/signing.dart.
// Cách hoạt động: được gọi từ lớp phía trên, xử lý dữ liệu theo vai trò hiện có và trả kết quả về cho luồng gọi.
// Vai trò trong hệ thống: Đây là lớp model dữ liệu phía Flutter.
// Tác dụng khi hệ thống vận hành: giúp frontend ánh xạ dữ liệu server thành đối tượng rõ nghĩa để render và xử lý.

// Mục đích: Lớp `SigningSummary` triển khai phần việc `Signing Summary` trong flutter_frontend/lib/models/signing.dart.
// Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
// Vai trò trong hệ thống: Đây là lớp thuộc lớp model dữ liệu phía Flutter.
// Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

class SigningSummary {
  final int tasksAvailable;
  final int tasksBlocked;
  final int tasksSigned;
  final int tasksTotal;
  final int hrPendingProposals;
  final int actionableTotal;
  final int mailboxPendingEntries;
  final int mailboxPendingThreads;
  final bool canReviewProposals;
  final bool canManageHrDelegations;
  final bool canManageAccountingDelegations;
  final bool canViewSignedPdfsSpecial;
  final String? hrDepartmentName;
  final String? accountingDepartmentName;

  const SigningSummary({
    required this.tasksAvailable,
    required this.tasksBlocked,
    required this.tasksSigned,
    required this.tasksTotal,
    required this.hrPendingProposals,
    required this.actionableTotal,
    required this.mailboxPendingEntries,
    required this.mailboxPendingThreads,
    required this.canReviewProposals,
    required this.canManageHrDelegations,
    required this.canManageAccountingDelegations,
    required this.canViewSignedPdfsSpecial,
    this.hrDepartmentName,
    this.accountingDepartmentName,
  });

  const SigningSummary.zero()
      : tasksAvailable = 0,
        tasksBlocked = 0,
        tasksSigned = 0,
        tasksTotal = 0,
        hrPendingProposals = 0,
        actionableTotal = 0,
        mailboxPendingEntries = 0,
        mailboxPendingThreads = 0,
        canReviewProposals = false,
        canManageHrDelegations = false,
        canManageAccountingDelegations = false,
        canViewSignedPdfsSpecial = false,
        hrDepartmentName = null,
        accountingDepartmentName = null;

  factory SigningSummary.fromJson(Map<String, dynamic> json) {
    return SigningSummary(
      tasksAvailable: json['tasks_available'] ?? 0,
      tasksBlocked: json['tasks_blocked'] ?? 0,
      tasksSigned: json['tasks_signed'] ?? 0,
      tasksTotal: json['tasks_total'] ?? 0,
      hrPendingProposals: json['hr_pending_proposals'] ?? 0,
      actionableTotal: json['actionable_total'] ?? 0,
      mailboxPendingEntries: json['mailbox_pending_entries'] ?? 0,
      mailboxPendingThreads: json['mailbox_pending_threads'] ?? 0,
      canReviewProposals: json['can_review_proposals'] ?? false,
      canManageHrDelegations: json['can_manage_hr_delegations'] ?? false,
      canManageAccountingDelegations: json['can_manage_accounting_delegations'] ?? false,
      canViewSignedPdfsSpecial: json['can_view_signed_pdfs_special'] ?? false,
      hrDepartmentName: json['hr_department_name'],
      accountingDepartmentName: json['accounting_department_name'],
    );
  }

  int get navBadgeCount =>
      tasksAvailable + hrPendingProposals + mailboxPendingThreads;
}

// Mục đích: Lớp `SigningCandidate` triển khai phần việc `Signing Candidate` trong flutter_frontend/lib/models/signing.dart.
// Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
// Vai trò trong hệ thống: Đây là lớp thuộc lớp model dữ liệu phía Flutter.
// Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

class SigningCandidate {
  final int id;
  final String username;
  final String fullName;
  final String title;

  const SigningCandidate({
    required this.id,
    required this.username,
    required this.fullName,
    required this.title,
  });

  factory SigningCandidate.fromJson(Map<String, dynamic> json) {
    return SigningCandidate(
      id: json['id'],
      username: json['username'] ?? '',
      fullName: json['full_name'] ?? json['username'] ?? '',
      title: json['title'] ?? '',
    );
  }

  String get label => title.trim().isEmpty ? fullName : '$fullName • $title';
}

// Mục đích: Lớp `ProposalSigner` triển khai phần việc `Proposal Signer` trong flutter_frontend/lib/models/signing.dart.
// Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
// Vai trò trong hệ thống: Đây là lớp thuộc lớp model dữ liệu phía Flutter.
// Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

class ProposalSigner {
  final int id;
  final int signerUserId;
  final String signerName;
  final String signerUsername;
  final String displayRole;
  final String groupContext;
  final int stepNo;
  final bool required;
  final int sortOrder;

  const ProposalSigner({
    required this.id,
    required this.signerUserId,
    required this.signerName,
    required this.signerUsername,
    required this.displayRole,
    required this.groupContext,
    required this.stepNo,
    required this.required,
    required this.sortOrder,
  });

  factory ProposalSigner.fromJson(Map<String, dynamic> json) {
    return ProposalSigner(
      id: json['id'],
      signerUserId: json['signer_user_id'],
      signerName: json['signer_name'] ?? '',
      signerUsername: json['signer_username'] ?? '',
      displayRole: json['display_role'] ?? '',
      groupContext: json['group_context'] ?? '',
      stepNo: json['step_no'] ?? 1,
      required: json['required'] ?? true,
      sortOrder: json['sort_order'] ?? 0,
    );
  }
}

// Mục đích: Lớp `SigningProposal` triển khai phần việc `Signing Proposal` trong flutter_frontend/lib/models/signing.dart.
// Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
// Vai trò trong hệ thống: Đây là lớp thuộc lớp model dữ liệu phía Flutter.
// Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

class SigningProposal {
  final int id;
  final int documentId;
  final String documentTitle;
  final String documentOwnerName;
  final int sourceVersionNumber;
  final String status;
  final String proposalNote;
  final String reviewNote;
  final String proposedByName;
  final String hrReviewedByName;
  final String invalidatedReason;
  final int? packetId;
  final int? currentUserTaskId;
  final List<ProposalSigner> signers;
  final String createdAt;

  const SigningProposal({
    required this.id,
    required this.documentId,
    required this.documentTitle,
    required this.documentOwnerName,
    required this.sourceVersionNumber,
    required this.status,
    required this.proposalNote,
    required this.reviewNote,
    required this.proposedByName,
    required this.hrReviewedByName,
    required this.invalidatedReason,
    required this.packetId,
    required this.currentUserTaskId,
    required this.signers,
    required this.createdAt,
  });

  factory SigningProposal.fromJson(Map<String, dynamic> json) {
    return SigningProposal(
      id: json['id'],
      documentId: json['document_id'],
      documentTitle: json['document_title'] ?? '',
      documentOwnerName: json['document_owner_name'] ?? '',
      sourceVersionNumber: json['source_version_number'] ?? 1,
      status: json['status'] ?? '',
      proposalNote: json['proposal_note'] ?? '',
      reviewNote: json['review_note'] ?? '',
      proposedByName: json['proposed_by_name'] ?? '',
      hrReviewedByName: json['hr_reviewed_by_name'] ?? '',
      invalidatedReason: json['invalidated_reason'] ?? '',
      packetId: json['packet_id'],
      currentUserTaskId: json['current_user_task_id'],
      signers: (json['signers'] as List<dynamic>? ?? [])
          .map((item) => ProposalSigner.fromJson(Map<String, dynamic>.from(item as Map)))
          .toList(),
      createdAt: json['created_at'] ?? '',
    );
  }
}

// Mục đích: Lớp `SigningTaskItem` triển khai phần việc `Signing Task Item` trong flutter_frontend/lib/models/signing.dart.
// Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
// Vai trò trong hệ thống: Đây là lớp thuộc lớp model dữ liệu phía Flutter.
// Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

class SigningTaskItem {
  final int id;
  final int packetId;
  final int documentId;
  final String documentTitle;
  final String packetStatus;
  final String signatureMode;
  final String displayRole;
  final String groupContext;
  final int stepNo;
  final bool required;
  final String signatureFieldName;
  final String status;
  final String signerName;
  final bool availableNow;
  final String rejectionReason;
  final String createdAt;

  const SigningTaskItem({
    required this.id,
    required this.packetId,
    required this.documentId,
    required this.documentTitle,
    required this.packetStatus,
    required this.signatureMode,
    required this.displayRole,
    required this.groupContext,
    required this.stepNo,
    required this.required,
    required this.signatureFieldName,
    required this.status,
    required this.signerName,
    required this.availableNow,
    required this.rejectionReason,
    required this.createdAt,
  });

  factory SigningTaskItem.fromJson(Map<String, dynamic> json) {
    return SigningTaskItem(
      id: json['id'],
      packetId: json['packet_id'],
      documentId: json['document_id'],
      documentTitle: json['document_title'] ?? '',
      packetStatus: json['packet_status'] ?? '',
      signatureMode: json['signature_mode'] ?? 'internal_approval',
      displayRole: json['display_role'] ?? '',
      groupContext: json['group_context'] ?? '',
      stepNo: json['step_no'] ?? 1,
      required: json['required'] ?? true,
      signatureFieldName: json['signature_field_name'] ?? '',
      status: json['status'] ?? '',
      signerName: json['signer_name'] ?? '',
      availableNow: json['available_now'] ?? false,
      rejectionReason: json['rejection_reason'] ?? '',
      createdAt: json['created_at'] ?? '',
    );
  }
}

// Mục đích: Lớp `SigningCertificateInfo` triển khai phần việc `Signing Certificate Info` trong flutter_frontend/lib/models/signing.dart.
// Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
// Vai trò trong hệ thống: Đây là lớp thuộc lớp model dữ liệu phía Flutter.
// Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

class SigningCertificateInfo {
  final int? id;
  final String provider;
  final String keyAlias;
  final String keyId;
  final String subjectDn;
  final String issuerDn;
  final String serialNumber;
  final String validFrom;
  final String validTo;
  final String status;
  final String fingerprintSha256;

  const SigningCertificateInfo({
    this.id,
    required this.provider,
    required this.keyAlias,
    required this.keyId,
    required this.subjectDn,
    required this.issuerDn,
    required this.serialNumber,
    required this.validFrom,
    required this.validTo,
    required this.status,
    required this.fingerprintSha256,
  });

  factory SigningCertificateInfo.fromJson(Map<String, dynamic> json) {
    return SigningCertificateInfo(
      id: json['id'],
      provider: json['provider'] ?? '',
      keyAlias: json['key_alias'] ?? '',
      keyId: json['key_id'] ?? '',
      subjectDn: json['subject_dn'] ?? '',
      issuerDn: json['issuer_dn'] ?? '',
      serialNumber: json['serial_number'] ?? '',
      validFrom: json['valid_from'] ?? '',
      validTo: json['valid_to'] ?? '',
      status: json['status'] ?? '',
      fingerprintSha256: json['fingerprint_sha256'] ?? '',
    );
  }
}

// Mục đích: Lớp `SigningTaskSignatureContext` triển khai phần việc `Signing Task Signature Context` trong flutter_frontend/lib/models/signing.dart.
// Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
// Vai trò trong hệ thống: Đây là lớp thuộc lớp model dữ liệu phía Flutter.
// Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

class SigningTaskSignatureContext {
  final int taskId;
  final int packetId;
  final String signatureMode;
  final bool availableNow;
  final bool credentialRequired;
  final bool providerReady;
  final String providerMessage;
  final bool credentialBound;
  final bool canSign;
  final String reason;
  final SigningCertificateInfo? certificate;

  const SigningTaskSignatureContext({
    required this.taskId,
    required this.packetId,
    required this.signatureMode,
    required this.availableNow,
    required this.credentialRequired,
    required this.providerReady,
    required this.providerMessage,
    required this.credentialBound,
    required this.canSign,
    required this.reason,
    required this.certificate,
  });

  factory SigningTaskSignatureContext.fromJson(Map<String, dynamic> json) {
    return SigningTaskSignatureContext(
      taskId: json['task_id'] ?? 0,
      packetId: json['packet_id'] ?? 0,
      signatureMode: json['signature_mode'] ?? 'internal_approval',
      availableNow: json['available_now'] ?? false,
      credentialRequired: json['credential_required'] ?? false,
      providerReady: json['provider_ready'] ?? false,
      providerMessage: json['provider_message'] ?? '',
      credentialBound: json['credential_bound'] ?? false,
      canSign: json['can_sign'] ?? false,
      reason: json['reason'] ?? '',
      certificate: json['certificate'] is Map<String, dynamic>
          ? SigningCertificateInfo.fromJson(json['certificate'] as Map<String, dynamic>)
          : (json['certificate'] is Map
              ? SigningCertificateInfo.fromJson(Map<String, dynamic>.from(json['certificate'] as Map))
              : null),
    );
  }
}

// Mục đích: Lớp `SignedPdfDocumentItem` triển khai phần việc `Signed Pdf Document Item` trong flutter_frontend/lib/models/signing.dart.
// Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
// Vai trò trong hệ thống: Đây là lớp thuộc lớp model dữ liệu phía Flutter.
// Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

class SignedPdfDocumentItem {
  final int id;
  final String title;
  final String ownerName;
  final int sourceDocumentId;
  final int sourceVersionNumber;
  final String fileHash;
  final String signatureMode;
  final String verificationStatus;
  final String verificationCheckedAt;
  final int signatureCount;
  final List<String> participantNames;
  final int participantCount;
  final int mailboxThreadCount;
  final String mailboxLastStatus;
  final String mailboxLastSummary;
  final int? mailboxLatestThreadId;
  final List<SignedPdfSigningEvent> signingEvents;
  final String createdAt;

  const SignedPdfDocumentItem({
    required this.id,
    required this.title,
    required this.ownerName,
    required this.sourceDocumentId,
    required this.sourceVersionNumber,
    required this.fileHash,
    required this.signatureMode,
    required this.verificationStatus,
    required this.verificationCheckedAt,
    required this.signatureCount,
    required this.participantNames,
    required this.participantCount,
    required this.mailboxThreadCount,
    required this.mailboxLastStatus,
    required this.mailboxLastSummary,
    required this.mailboxLatestThreadId,
    required this.signingEvents,
    required this.createdAt,
  });

  factory SignedPdfDocumentItem.fromJson(Map<String, dynamic> json) {
    return SignedPdfDocumentItem(
      id: json['id'],
      title: json['title'] ?? '',
      ownerName: json['owner_name'] ?? '',
      sourceDocumentId: json['source_document_id'],
      sourceVersionNumber: json['source_version_number'] ?? 1,
      fileHash: json['file_hash'] ?? '',
      signatureMode: json['signature_mode'] ?? 'internal_approval',
      verificationStatus: json['verification_status'] ?? '',
      verificationCheckedAt: json['verification_checked_at'] ?? '',
      signatureCount: json['signature_count'] ?? 0,
      participantNames: (json['participant_names'] as List<dynamic>? ?? [])
          .map((item) => item.toString())
          .toList(),
      participantCount: json['participant_count'] ?? 0,
      mailboxThreadCount: json['mailbox_thread_count'] ?? 0,
      mailboxLastStatus: json['mailbox_last_status'] ?? '',
      mailboxLastSummary: json['mailbox_last_summary'] ?? '',
      mailboxLatestThreadId: json['mailbox_latest_thread_id'],
      signingEvents: (json['signing_events'] as List<dynamic>? ?? [])
          .map((item) => SignedPdfSigningEvent.fromJson(Map<String, dynamic>.from(item as Map)))
          .toList(),
      createdAt: json['created_at'] ?? '',
    );
  }
}

// Mục đích: Lớp `MailboxEntryItem` triển khai phần việc `Mailbox Entry Item` trong flutter_frontend/lib/models/signing.dart.
// Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
// Vai trò trong hệ thống: Đây là lớp thuộc lớp model dữ liệu phía Flutter.
// Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

class MailboxEntryItem {
  final int id;
  final int? parentEntry;
  final int forwardedBy;
  final String forwardedByName;
  final int forwardedTo;
  final String forwardedToName;
  final int? signedPdfId;
  final String status;
  final String note;
  final String actionReason;
  final int? actionedBy;
  final String actionedByName;
  final String actionedAt;
  final String createdAt;
  final String updatedAt;

  const MailboxEntryItem({
    required this.id,
    required this.parentEntry,
    required this.forwardedBy,
    required this.forwardedByName,
    required this.forwardedTo,
    required this.forwardedToName,
    required this.signedPdfId,
    required this.status,
    required this.note,
    required this.actionReason,
    required this.actionedBy,
    required this.actionedByName,
    required this.actionedAt,
    required this.createdAt,
    required this.updatedAt,
  });

  factory MailboxEntryItem.fromJson(Map<String, dynamic> json) => MailboxEntryItem(
    id: json['id'] ?? 0,
    parentEntry: json['parent_entry'],
    forwardedBy: json['forwarded_by'] ?? 0,
    forwardedByName: json['forwarded_by_name'] ?? '',
    forwardedTo: json['forwarded_to'] ?? 0,
    forwardedToName: json['forwarded_to_name'] ?? '',
    signedPdfId: json['signed_pdf_id'],
    status: json['status'] ?? '',
    note: json['note'] ?? '',
    actionReason: json['action_reason'] ?? '',
    actionedBy: json['actioned_by'],
    actionedByName: json['actioned_by_name'] ?? '',
    actionedAt: json['actioned_at'] ?? '',
    createdAt: json['created_at'] ?? '',
    updatedAt: json['updated_at'] ?? '',
  );
}

// Mục đích: Lớp `MailboxThreadItem` triển khai phần việc `Mailbox Thread Item` trong flutter_frontend/lib/models/signing.dart.
// Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
// Vai trò trong hệ thống: Đây là lớp thuộc lớp model dữ liệu phía Flutter.
// Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

class MailboxThreadItem {
  final int id;
  final int documentId;
  final String documentTitle;
  final int createdBy;
  final String createdByName;
  final int sourceVersionNumber;
  final int? sourceSignedPdfId;
  final String status;
  final int? lastActionBy;
  final String lastActionByName;
  final String lastActionAt;
  final String lastActionSummary;
  final String lastActionReason;
  final String latestSenderName;
  final String latestTerminalActorName;
  final int branchCount;
  final String createdAt;
  final String updatedAt;
  final List<MailboxEntryItem> entries;

  const MailboxThreadItem({
    required this.id,
    required this.documentId,
    required this.documentTitle,
    required this.createdBy,
    required this.createdByName,
    required this.sourceVersionNumber,
    required this.sourceSignedPdfId,
    required this.status,
    required this.lastActionBy,
    required this.lastActionByName,
    required this.lastActionAt,
    required this.lastActionSummary,
    required this.lastActionReason,
    required this.latestSenderName,
    required this.latestTerminalActorName,
    required this.branchCount,
    required this.createdAt,
    required this.updatedAt,
    required this.entries,
  });

  factory MailboxThreadItem.fromJson(Map<String, dynamic> json) => MailboxThreadItem(
    id: json['id'] ?? 0,
    documentId: json['document'] ?? 0,
    documentTitle: json['document_title'] ?? '',
    createdBy: json['created_by'] ?? 0,
    createdByName: json['created_by_name'] ?? '',
    sourceVersionNumber: json['source_version_number'] ?? 1,
    sourceSignedPdfId: json['source_signed_pdf_id'],
    status: json['status'] ?? '',
    lastActionBy: json['last_action_by'],
    lastActionByName: json['last_action_by_name'] ?? '',
    lastActionAt: json['last_action_at'] ?? '',
    lastActionSummary: json['last_action_summary'] ?? '',
    lastActionReason: json['last_action_reason'] ?? '',
    latestSenderName: json['latest_sender_name'] ?? '',
    latestTerminalActorName: json['latest_terminal_actor_name'] ?? '',
    branchCount: json['branch_count'] ?? 0,
    createdAt: json['created_at'] ?? '',
    updatedAt: json['updated_at'] ?? '',
    entries: (json['entries'] as List<dynamic>? ?? [])
        .map((item) => MailboxEntryItem.fromJson(Map<String, dynamic>.from(item as Map)))
        .toList(),
  );
}

// Mục đích: Lớp `SignedPdfSigningEvent` triển khai phần việc `Signed Pdf Signing Event` trong flutter_frontend/lib/models/signing.dart.
// Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
// Vai trò trong hệ thống: Đây là lớp thuộc lớp model dữ liệu phía Flutter.
// Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

class SignedPdfSigningEvent {
  final int? taskId;
  final int? signerUserId;
  final String signerUsername;
  final String signerName;
  final String displayRole;
  final int stepNo;
  final String signatureFieldName;
  final String certificateFingerprint;
  final String certificateSubjectDn;
  final String certificateSerialNumber;
  final String certificateIssuerDn;
  final String signatureAlgorithm;
  final String digestAlgorithm;
  final String providerTransactionId;
  final String verificationStatus;
  final String signedAt;

  const SignedPdfSigningEvent({
    this.taskId,
    this.signerUserId,
    required this.signerUsername,
    required this.signerName,
    required this.displayRole,
    required this.stepNo,
    required this.signatureFieldName,
    required this.certificateFingerprint,
    required this.certificateSubjectDn,
    required this.certificateSerialNumber,
    required this.certificateIssuerDn,
    required this.signatureAlgorithm,
    required this.digestAlgorithm,
    required this.providerTransactionId,
    required this.verificationStatus,
    required this.signedAt,
  });

  factory SignedPdfSigningEvent.fromJson(Map<String, dynamic> json) {
    return SignedPdfSigningEvent(
      taskId: json['task_id'],
      signerUserId: json['signer_user_id'],
      signerUsername: json['signer_username'] ?? '',
      signerName: json['signer_name'] ?? '',
      displayRole: json['display_role'] ?? '',
      stepNo: json['step_no'] ?? 1,
      signatureFieldName: json['signature_field_name'] ?? '',
      certificateFingerprint: json['certificate_fingerprint'] ?? '',
      certificateSubjectDn: json['certificate_subject_dn'] ?? '',
      certificateSerialNumber: json['certificate_serial_number'] ?? '',
      certificateIssuerDn: json['certificate_issuer_dn'] ?? '',
      signatureAlgorithm: json['signature_algorithm'] ?? '',
      digestAlgorithm: json['digest_algorithm'] ?? '',
      providerTransactionId: json['provider_transaction_id'] ?? '',
      verificationStatus: json['verification_status'] ?? '',
      signedAt: json['signed_at'] ?? '',
    );
  }
}

// Mục đích: Lớp `SignedPdfSignerVerification` triển khai phần việc `Signed Pdf Signer Verification` trong flutter_frontend/lib/models/signing.dart.
// Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
// Vai trò trong hệ thống: Đây là lớp thuộc lớp model dữ liệu phía Flutter.
// Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

class SignedPdfSignerVerification {
  final String fieldName;
  final int? taskId;
  final int? signerUserId;
  final String signerName;
  final String displayRole;
  final int? stepNo;
  final String status;
  final bool isValid;
  final String detail;
  final String signedAt;
  final String subjectDn;
  final String issuerDn;
  final String serialNumber;
  final String certificateFingerprint;
  final String digestAlgorithm;
  final String signatureAlgorithm;
  final Map<String, dynamic> integrity;
  final List<Map<String, dynamic>> chain;

  const SignedPdfSignerVerification({
    required this.fieldName,
    required this.taskId,
    required this.signerUserId,
    required this.signerName,
    required this.displayRole,
    required this.stepNo,
    required this.status,
    required this.isValid,
    required this.detail,
    required this.signedAt,
    required this.subjectDn,
    required this.issuerDn,
    required this.serialNumber,
    required this.certificateFingerprint,
    required this.digestAlgorithm,
    required this.signatureAlgorithm,
    required this.integrity,
    required this.chain,
  });

  factory SignedPdfSignerVerification.fromJson(Map<String, dynamic> json) {
    return SignedPdfSignerVerification(
      fieldName: json['field_name'] ?? '',
      taskId: json['task_id'],
      signerUserId: json['signer_user_id'],
      signerName: json['signer_name'] ?? '',
      displayRole: json['display_role'] ?? '',
      stepNo: json['step_no'],
      status: json['status'] ?? '',
      isValid: json['is_valid'] ?? false,
      detail: json['detail'] ?? '',
      signedAt: json['signed_at'] ?? '',
      subjectDn: json['subject_dn'] ?? '',
      issuerDn: json['issuer_dn'] ?? '',
      serialNumber: json['serial_number'] ?? '',
      certificateFingerprint: json['certificate_fingerprint'] ?? '',
      digestAlgorithm: json['digest_algorithm'] ?? '',
      signatureAlgorithm: json['signature_algorithm'] ?? '',
      integrity: Map<String, dynamic>.from(json['integrity'] as Map? ?? const {}),
      chain: (json['chain'] as List<dynamic>? ?? [])
          .map((item) => Map<String, dynamic>.from(item as Map))
          .toList(),
    );
  }
}

// Mục đích: Lớp `SignedPdfVerificationStep` triển khai phần việc `Signed Pdf Verification Step` trong flutter_frontend/lib/models/signing.dart.
// Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
// Vai trò trong hệ thống: Đây là lớp thuộc lớp model dữ liệu phía Flutter.
// Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

class SignedPdfVerificationStep {
  final String code;
  final String label;
  final String status;
  final String detail;

  const SignedPdfVerificationStep({
    required this.code,
    required this.label,
    required this.status,
    required this.detail,
  });

  factory SignedPdfVerificationStep.fromJson(Map<String, dynamic> json) {
    return SignedPdfVerificationStep(
      code: json['code'] ?? '',
      label: json['label'] ?? '',
      status: json['status'] ?? '',
      detail: json['detail'] ?? '',
    );
  }
}

// Mục đích: Lớp `SignedPdfVerificationItem` triển khai phần việc `Signed Pdf Verification Item` trong flutter_frontend/lib/models/signing.dart.
// Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
// Vai trò trong hệ thống: Đây là lớp thuộc lớp model dữ liệu phía Flutter.
// Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

class SignedPdfVerificationItem {
  final String status;
  final bool isSafe;
  final bool isAccessAllowed;
  final String summary;
  final String checkedAt;
  final String signatureMode;
  final int signatureCount;
  final String expectedHash;
  final String actualHash;
  final List<SignedPdfSignerVerification> signerReports;
  final List<SignedPdfVerificationStep> steps;

  const SignedPdfVerificationItem({
    required this.status,
    required this.isSafe,
    required this.isAccessAllowed,
    required this.summary,
    required this.checkedAt,
    required this.signatureMode,
    required this.signatureCount,
    required this.expectedHash,
    required this.actualHash,
    required this.signerReports,
    required this.steps,
  });

  factory SignedPdfVerificationItem.fromJson(Map<String, dynamic> json) {
    return SignedPdfVerificationItem(
      status: json['status'] ?? '',
      isSafe: json['is_safe'] ?? false,
      isAccessAllowed: json['is_access_allowed'] ?? (json['is_safe'] ?? false),
      summary: json['summary'] ?? '',
      checkedAt: json['checked_at'] ?? '',
      signatureMode: json['signature_mode'] ?? 'internal_approval',
      signatureCount: json['signature_count'] ?? 0,
      expectedHash: json['expected_hash'] ?? '',
      actualHash: json['actual_hash'] ?? '',
      signerReports: (json['signer_reports'] as List<dynamic>? ?? [])
          .map((item) => SignedPdfSignerVerification.fromJson(Map<String, dynamic>.from(item as Map)))
          .toList(),
      steps: (json['steps'] as List<dynamic>? ?? [])
          .map((item) => SignedPdfVerificationStep.fromJson(Map<String, dynamic>.from(item as Map)))
          .toList(),
    );
  }
}

// Mục đích: Lớp `DepartmentDelegationItem` triển khai phần việc `Department Delegation Item` trong flutter_frontend/lib/models/signing.dart.
// Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
// Vai trò trong hệ thống: Đây là lớp thuộc lớp model dữ liệu phía Flutter.
// Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

class DepartmentDelegationItem {
  final int id;
  final int department;
  final String departmentName;
  final int delegateUser;
  final String delegateUserName;
  final String permissionType;
  final bool isActive;
  final String createdAt;

  const DepartmentDelegationItem({
    required this.id,
    required this.department,
    required this.departmentName,
    required this.delegateUser,
    required this.delegateUserName,
    required this.permissionType,
    required this.isActive,
    required this.createdAt,
  });

  factory DepartmentDelegationItem.fromJson(Map<String, dynamic> json) {
    return DepartmentDelegationItem(
      id: json['id'],
      department: json['department'],
      departmentName: json['department_name'] ?? '',
      delegateUser: json['delegate_user'],
      delegateUserName: json['delegate_user_name'] ?? '',
      permissionType: json['permission_type'] ?? '',
      isActive: json['is_active'] ?? false,
      createdAt: json['created_at'] ?? '',
    );
  }
}
