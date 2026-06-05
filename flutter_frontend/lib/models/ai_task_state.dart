class AITaskState {
  final String taskId;
  final String status;
  final String taskType;
  final int percent;
  final String stage;
  final String detail;
  final bool cancelRequested;
  final String cancelMode;
  final Map<String, dynamic>? result;
  final String? errorMessage;
  final List<String> streamingChunks;
  final String? relatedEntityType;
  final int? relatedEntityId;
  final String createdAt;
  final String updatedAt;
  final String? completedAt;

  const AITaskState({
    required this.taskId,
    required this.status,
    required this.taskType,
    required this.percent,
    required this.stage,
    required this.detail,
    required this.cancelRequested,
    required this.cancelMode,
    required this.result,
    required this.errorMessage,
    required this.streamingChunks,
    required this.relatedEntityType,
    required this.relatedEntityId,
    required this.createdAt,
    required this.updatedAt,
    required this.completedAt,
  });

  factory AITaskState.fromJson(Map<String, dynamic> json) => AITaskState(
        taskId: json['task_id'].toString(),
        status: (json['status'] ?? 'queued').toString(),
        taskType: (json['task_type'] ?? '').toString(),
        percent: (json['progress_percent'] ?? 0) as int,
        stage: (json['progress_stage'] ?? '').toString(),
        detail: (json['progress_detail'] ?? '').toString(),
        cancelRequested: json['cancel_requested'] == true,
        cancelMode: (json['cancel_mode'] ?? 'soft').toString(),
        result: (json['result'] as Map?)?.cast<String, dynamic>(),
        errorMessage: json['error_message'] as String?,
        streamingChunks: ((json['streaming_chunks'] as List?) ?? const [])
            .map((e) => e.toString()).toList(),
        relatedEntityType: json['related_entity_type'] as String?,
        relatedEntityId: json['related_entity_id'] as int?,
        createdAt: (json['created_at'] ?? '') as String,
        updatedAt: (json['updated_at'] ?? '') as String,
        completedAt: json['completed_at'] as String?,
      );

  bool get isTerminal =>
      status == 'completed' || status == 'failed' || status == 'cancelled';
  bool get isRunning => status == 'running' || status == 'queued';
  bool get isSoftCancel => cancelMode == 'soft';
  bool get isHardCancel => cancelMode == 'hard';

  String get statusLabel => switch (status) {
        'queued' => 'Đang chờ',
        'running' => 'Đang chạy',
        'completed' => 'Hoàn tất',
        'failed' => 'Thất bại',
        'cancelled' => 'Đã dừng',
        _ => status,
      };

  String get streamingText => streamingChunks.join('');
}
