class AssistantRecipientCandidate {
  final int id;
  final String username;
  final String displayName;
  final String title;
  final String employeeCode;
  final String department;
  final List<String> aliases;
  final String matchReason;
  final int confidence;

  const AssistantRecipientCandidate({
    required this.id,
    required this.username,
    required this.displayName,
    required this.title,
    this.employeeCode = '',
    this.department = '',
    this.aliases = const [],
    this.matchReason = '',
    this.confidence = 0,
  });

  factory AssistantRecipientCandidate.fromJson(Map<String, dynamic> json) {
    return AssistantRecipientCandidate(
      id: json['id'] as int? ?? json['user_id'] as int? ?? 0,
      username: json['username'] as String? ?? '',
      displayName: json['display_name'] as String? ??
          json['full_name'] as String? ??
          json['username'] as String? ??
          '',
      title: json['title'] as String? ?? '',
      employeeCode: json['employee_code'] as String? ?? '',
      department: json['department'] as String? ?? '',
      aliases: (json['aliases'] as List<dynamic>? ?? const [])
          .map((item) => item.toString())
          .where((item) => item.trim().isNotEmpty)
          .toList(),
      matchReason: json['match_reason'] as String? ?? '',
      confidence: json['confidence'] as int? ?? 0,
    );
  }

  String get label =>
      title.trim().isEmpty ? displayName : '$displayName • $title';

  String get subtitle {
    final parts = <String>[
      if (username.trim().isNotEmpty) '@${username.trim()}',
      if (department.trim().isNotEmpty) department.trim(),
      if (employeeCode.trim().isNotEmpty) employeeCode.trim(),
    ];
    return parts.join(' • ');
  }

  String get aliasSummary => aliases.take(3).join(', ');
}

class QuickSignRecipientResolution {
  final String status;
  final AssistantRecipientCandidate? recipient;
  final List<AssistantRecipientCandidate> candidates;

  const QuickSignRecipientResolution({
    required this.status,
    required this.recipient,
    this.candidates = const [],
  });

  factory QuickSignRecipientResolution.fromJson(Map<String, dynamic> json) {
    return QuickSignRecipientResolution(
      status: json['status'] as String? ?? 'not_found',
      recipient: json['recipient'] is Map
          ? AssistantRecipientCandidate.fromJson(
              Map<String, dynamic>.from(json['recipient'] as Map),
            )
          : null,
      candidates: (json['candidates'] as List<dynamic>? ?? const [])
          .map(
            (item) => AssistantRecipientCandidate.fromJson(
              Map<String, dynamic>.from(item as Map),
            ),
          )
          .toList(),
    );
  }
}

class AssistantQuickSignPlanAction {
  final String kind;
  final String type;
  final String status;
  final String route;
  final int? documentId;
  final int documentVersionNumber;
  final String planToken;
  final QuickSignRecipientResolution recipientResolution;
  final AssistantRecipientCandidate? recipient;
  final String signatureMode;
  final bool requiresReauthPassword;
  final bool credentialRequired;
  final bool canSignNow;
  final bool alreadySigned;
  final String blockingCode;
  final String blockingReason;
  final String lastErrorCode;
  final String lastErrorMessage;
  final int? signedPdfId;
  final int? mailboxThreadId;
  final String forwardNote;
  final String message;
  final String cta;
  final String uiState;

  const AssistantQuickSignPlanAction({
    required this.kind,
    required this.type,
    required this.status,
    required this.route,
    required this.documentId,
    required this.documentVersionNumber,
    required this.planToken,
    required this.recipientResolution,
    required this.recipient,
    required this.signatureMode,
    required this.requiresReauthPassword,
    required this.credentialRequired,
    required this.canSignNow,
    required this.alreadySigned,
    required this.blockingCode,
    required this.blockingReason,
    required this.lastErrorCode,
    required this.lastErrorMessage,
    required this.signedPdfId,
    required this.mailboxThreadId,
    required this.forwardNote,
    required this.message,
    required this.cta,
    required this.uiState,
  });

  factory AssistantQuickSignPlanAction.fromJson(Map<String, dynamic> json) {
    final recipientResolution = json['recipient_resolution'] is Map
        ? QuickSignRecipientResolution.fromJson(
            Map<String, dynamic>.from(json['recipient_resolution'] as Map),
          )
        : const QuickSignRecipientResolution(
            status: 'not_found', recipient: null);
    return AssistantQuickSignPlanAction(
      kind: json['kind'] as String? ?? 'assistant_quick_sign_plan',
      type: json['type'] as String? ?? 'assistant_quick_sign',
      status: json['status'] as String? ?? 'assistant_message',
      route: json['route'] as String? ?? '',
      documentId: json['document_id'] as int?,
      documentVersionNumber: json['document_version_number'] as int? ?? 0,
      planToken: json['plan_token'] as String? ?? '',
      recipientResolution: recipientResolution,
      recipient: json['recipient'] is Map
          ? AssistantRecipientCandidate.fromJson(
              Map<String, dynamic>.from(json['recipient'] as Map),
            )
          : recipientResolution.recipient,
      signatureMode: json['signature_mode'] as String? ?? '',
      requiresReauthPassword:
          json['requires_reauth_password'] as bool? ?? false,
      credentialRequired: json['credential_required'] as bool? ?? false,
      canSignNow: json['can_sign_now'] as bool? ?? false,
      alreadySigned: json['already_signed'] as bool? ?? false,
      blockingCode: json['blocking_code'] as String? ?? '',
      blockingReason: json['blocking_reason'] as String? ?? '',
      lastErrorCode: json['last_error_code'] as String? ?? '',
      lastErrorMessage: json['last_error_message'] as String? ?? '',
      signedPdfId: json['signed_pdf_id'] as int?,
      mailboxThreadId: json['mailbox_thread_id'] as int?,
      forwardNote: json['forward_note'] as String? ?? '',
      message: json['message'] as String? ?? '',
      cta: json['ui_hint'] is Map
          ? (json['ui_hint']['cta'] as String? ?? '')
          : '',
      uiState: json['ui_hint'] is Map
          ? (json['ui_hint']['state'] as String? ?? '')
          : '',
    );
  }

  bool get isBlocked =>
      uiState == 'blocked' || (status == 'operation_failed' && uiState.isEmpty);
  bool get isFailed => uiState == 'failed';
  bool get hasErrorState => isBlocked || isFailed;
  bool get isPartial => uiState == 'partial';
  bool get isCompleted => uiState == 'completed';
  bool get isReady => status == 'quick_sign_plan_ready' || isPartial;
  bool get canExecute => canSignNow && !isCompleted && !hasErrorState;
  bool get canRetryForward => cta == 'retry_forward' || isPartial;
}
