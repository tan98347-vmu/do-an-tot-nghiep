// ignore_for_file: avoid_web_libraries_in_flutter

import 'dart:async';
import 'dart:html' as html;

import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../core/api_client.dart';
import '../models/ai_task.dart';
import '../models/ai_task_state.dart';

class AITaskPollConfig {
  final String taskId;
  final Duration pollInterval;
  const AITaskPollConfig({
    required this.taskId,
    this.pollInterval = const Duration(milliseconds: 600),
  });

  @override
  bool operator ==(Object other) =>
      other is AITaskPollConfig &&
      other.taskId == taskId &&
      other.pollInterval == pollInterval;

  @override
  int get hashCode => Object.hash(taskId, pollInterval);
}

final aiTaskProgressProvider =
    StreamProvider.family.autoDispose<AITaskState, AITaskPollConfig>(
  (ref, config) async* {
    int retry = 0;
    while (true) {
      var nextDelay = config.pollInterval;
      try {
        final resp = await ApiClient().dio.get('ai-tasks/${config.taskId}/');
        final state = AITaskState.fromJson(
          Map<String, dynamic>.from(resp.data as Map),
        );
        yield state;
        retry = 0;
        if (state.isTerminal) break;
      } catch (e) {
        retry++;
        if (retry > 3) rethrow;
        final baseMs = config.pollInterval.inMilliseconds;
        nextDelay = Duration(milliseconds: baseMs * (1 << (retry - 1)));
      }
      await Future<void>.delayed(nextDelay);
    }
  },
);

class TaskInbox {
  final List<AiTask> running;
  final List<AiTask> recentCompleted;

  const TaskInbox({
    required this.running,
    required this.recentCompleted,
  });

  const TaskInbox.empty()
      : running = const [],
        recentCompleted = const [];

  factory TaskInbox.fromJson(Map<String, dynamic> json) {
    return TaskInbox(
      running: ((json['running'] as List?) ?? const [])
          .whereType<Map>()
          .map((item) => AiTask.fromJson(Map<String, dynamic>.from(item)))
          .toList(),
      recentCompleted: ((json['recent_completed'] as List?) ?? const [])
          .whereType<Map>()
          .map((item) => AiTask.fromJson(Map<String, dynamic>.from(item)))
          .toList(),
    );
  }
}

final taskInboxProvider = StreamProvider.autoDispose<TaskInbox>((ref) async* {
  var disposed = false;
  var errorBackoffSeconds = 5;
  ref.onDispose(() => disposed = true);

  while (!disposed) {
    if (_isBrowserTabHidden()) {
      await _sleepWithDispose(
        disposed: () => disposed,
        duration: const Duration(seconds: 5),
      );
      continue;
    }

    try {
      final response = await ApiClient().dio.get('ai-tasks/inbox/');
      if (disposed) {
        break;
      }
      final inbox = TaskInbox.fromJson(
        Map<String, dynamic>.from(response.data as Map),
      );
      yield inbox;
      errorBackoffSeconds = 5;
      await _sleepWithDispose(
        disposed: () => disposed,
        duration: inbox.running.isNotEmpty
            ? const Duration(seconds: 5)
            : const Duration(seconds: 30),
      );
    } catch (_) {
      await _sleepWithDispose(
        disposed: () => disposed,
        duration: Duration(seconds: errorBackoffSeconds),
      );
      errorBackoffSeconds = switch (errorBackoffSeconds) {
        5 => 10,
        10 => 20,
        _ => 60,
      };
    }
  }
});

bool _isBrowserTabHidden() {
  try {
    return html.document.hidden ?? false;
  } catch (_) {
    return false;
  }
}

Future<void> _sleepWithDispose({
  required bool Function() disposed,
  required Duration duration,
}) async {
  final deadline = DateTime.now().add(duration);
  while (!disposed() && DateTime.now().isBefore(deadline)) {
    await Future<void>.delayed(const Duration(milliseconds: 250));
  }
}
