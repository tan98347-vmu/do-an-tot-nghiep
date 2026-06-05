class AiTask {
  final String taskId;
  final String taskType;
  final String status;
  final int progressPercent;
  final String progressStage;
  final String progressDetail;
  final String titleSummary;
  final String deeplink;
  final String relatedEntityType;
  final int? relatedEntityId;
  final String createdAt;
  final String updatedAt;
  final String? completedAt;
  final String errorMessage;
  final bool cancelRequested;
  final bool isDismissed;
  final Map<String, dynamic> result;
  final List<String> streamingChunks;

  const AiTask({
    required this.taskId,
    required this.taskType,
    required this.status,
    required this.progressPercent,
    required this.progressStage,
    required this.progressDetail,
    required this.titleSummary,
    required this.deeplink,
    required this.relatedEntityType,
    required this.relatedEntityId,
    required this.createdAt,
    required this.updatedAt,
    required this.completedAt,
    required this.errorMessage,
    required this.cancelRequested,
    required this.isDismissed,
    required this.result,
    required this.streamingChunks,
  });

  factory AiTask.fromJson(Map<String, dynamic> json) {
    final taskType = '${json['task_type'] ?? ''}'.trim();
    final relatedEntityType = '${json['related_entity_type'] ?? ''}'.trim();
    final relatedEntityId = (json['related_entity_id'] as num?)?.toInt();
    final rawDeeplink = '${json['deeplink'] ?? ''}'.trim();
    final fallbackDeeplink = _fallbackDeeplink(
      taskType: taskType,
      relatedEntityType: relatedEntityType,
      relatedEntityId: relatedEntityId,
    );
    final safeDeeplink = isSafeDeeplink(rawDeeplink)
        ? rawDeeplink
        : (isSafeDeeplink(fallbackDeeplink) ? fallbackDeeplink : '');

    return AiTask(
      taskId: '${json['task_id'] ?? ''}',
      taskType: taskType,
      status: '${json['status'] ?? 'queued'}'.trim(),
      progressPercent: (json['progress_percent'] as num?)?.toInt() ?? 0,
      progressStage: '${json['progress_stage'] ?? ''}',
      progressDetail: '${json['progress_detail'] ?? ''}',
      titleSummary: _fallbackTitle(
        '${json['title_summary'] ?? ''}'.trim(),
        taskType,
      ),
      deeplink: safeDeeplink,
      relatedEntityType: relatedEntityType,
      relatedEntityId: relatedEntityId,
      createdAt: '${json['created_at'] ?? ''}',
      updatedAt: '${json['updated_at'] ?? ''}',
      completedAt: json['completed_at']?.toString(),
      errorMessage: '${json['error_message'] ?? ''}',
      cancelRequested: json['cancel_requested'] == true,
      isDismissed: json['is_dismissed'] == true,
      result: json['result'] is Map
          ? Map<String, dynamic>.from(json['result'] as Map)
          : const <String, dynamic>{},
      streamingChunks: ((json['streaming_chunks'] as List?) ?? const [])
          .map((item) => '$item')
          .toList(),
    );
  }

  static bool isTerminalStatus(String status) {
    return status == 'completed' || status == 'failed' || status == 'cancelled';
  }

  static bool isSafeDeeplink(String value) {
    if (value.isEmpty || !value.startsWith('/')) {
      return false;
    }
    final uri = Uri.tryParse(value);
    if (uri == null || uri.hasScheme || value.startsWith('//')) {
      return false;
    }
    return !value.contains('\\') && !value.contains('..');
  }

  bool get isTerminal => isTerminalStatus(status);
  bool get isRunning => status == 'queued' || status == 'running';
  bool get isFailed => status == 'failed';
  bool get isCancelled => status == 'cancelled';
  bool get canNavigate => deeplink.isNotEmpty && !isCancelled;

  String get statusLabel {
    switch (status) {
      case 'queued':
        return 'Đang chờ';
      case 'running':
        return 'Đang chạy';
      case 'completed':
        return 'Hoàn tất';
      case 'failed':
        return 'Đã thất bại';
      case 'cancelled':
        return 'Đã hủy';
      default:
        return status;
    }
  }

  String get streamingText => streamingChunks.join();

  static String _fallbackTitle(String titleSummary, String taskType) {
    if (titleSummary.isNotEmpty) {
      return titleSummary;
    }
    switch (taskType) {
      case 'voice':
      case 'voice_chat':
        return 'Phiên voice chat';
      case 'chat':
        return 'Phiên chat AI';
      case 'bulk_template_upload':
        return 'Tải nhiều mẫu';
      case 'document_summary':
        return 'Tóm tắt văn bản';
      case 'compliance_check':
        return 'Kiểm tra tuân thủ';
      case 'word_ai_edit':
        return 'Word AI edit';
      case 'company_backup_export':
        return 'Xuất backup công ty';
      default:
        return 'Tác vụ AI';
    }
  }

  static String _fallbackDeeplink({
    required String taskType,
    required String relatedEntityType,
    required int? relatedEntityId,
  }) {
    if (relatedEntityId == null) {
      return '';
    }
    if (relatedEntityType == 'chat_session') {
      if (taskType == 'voice' || taskType == 'voice_chat') {
        return Uri(
          path: '/assistant/voice',
          queryParameters: {'conversation_id': '$relatedEntityId'},
        ).toString();
      }
      return Uri(
        path: '/chat/text',
        queryParameters: {'conversation_id': '$relatedEntityId'},
      ).toString();
    }
    if (taskType == 'document_summary') {
      return '/summaries/$relatedEntityId';
    }
    if (taskType == 'word_ai_edit') {
      return '/word-ai/jobs/$relatedEntityId';
    }
    return '';
  }
}
