import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'api_client.dart';
import '../widgets/ai_loading/ai_task_dialog.dart';

export '../widgets/ai_loading/ai_task_dialog.dart' show AITaskDialogStyle;

class AITaskCancelledException implements Exception {
  final String message;
  const AITaskCancelledException([this.message = 'Task cancelled']);
  @override String toString() => message;
}

class AITaskFailedException implements Exception {
  final String message;
  const AITaskFailedException(this.message);
  @override String toString() => message;
}

/// Start an AI task by POSTing to the async endpoint, open a dialog showing
/// progress with the chosen style, and return the task result when completed.
///
/// Throws [AITaskCancelledException] or [AITaskFailedException].
Future<Map<String, dynamic>> runAITask({
  required BuildContext context,
  required String endpoint,
  Map<String, dynamic>? jsonPayload,
  FormData? formPayload,
  required AITaskDialogStyle style,
  String? dialogTitle,
  String? dialogSubtitle,
  bool showStreamingText = false,
}) async {
  final resp = await ApiClient().dio.post(
    endpoint,
    data: formPayload ?? jsonPayload,
  );
  final body = (resp.data as Map).cast<String, dynamic>();
  final taskId = body['task_id'] as String?;
  if (taskId == null || taskId.isEmpty) {
    throw const AITaskFailedException('Server không trả về task_id.');
  }

  if (!context.mounted) {
    throw const AITaskFailedException('Context unmounted');
  }
  final dialogResult = await showDialog<Map<String, dynamic>>(
    context: context,
    barrierDismissible: false,
    builder: (_) => AITaskDialog(
      taskId: taskId,
      style: style,
      title: dialogTitle,
      subtitle: dialogSubtitle,
      showStreamingText: showStreamingText,
    ),
  );

  if (dialogResult == null) {
    throw const AITaskCancelledException();
  }
  final status = dialogResult['status'] as String?;
  if (status == 'completed') {
    final result = dialogResult['result'];
    return (result is Map) ? Map<String, dynamic>.from(result) : <String, dynamic>{};
  }
  if (status == 'cancelled') {
    throw const AITaskCancelledException();
  }
  throw AITaskFailedException(
    (dialogResult['error'] as String?) ?? 'AI task thất bại',
  );
}
