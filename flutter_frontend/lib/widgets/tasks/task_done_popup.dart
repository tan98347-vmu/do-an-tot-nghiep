// ignore_for_file: avoid_web_libraries_in_flutter

import 'dart:html' as html;

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../l10n/app_strings.dart';
import '../../models/ai_task.dart';
import '../../providers/ai_task_progress_provider.dart';

class TaskDonePopup {
  static final List<_ActivePopup> _activePopups = <_ActivePopup>[];

  static OverlayEntry show(BuildContext ctx, AiTask task) {
    if (_activePopups.length >= 3) {
      final oldest = _activePopups.removeAt(0);
      if (oldest.entry.mounted) {
        oldest.entry.remove();
      }
    }

    late final OverlayEntry entry;
    entry = OverlayEntry(
      builder: (_) {
        final strings = AppStrings.of(ctx);
        final popupIndex = _activePopups.indexWhere((item) => item.entry == entry);
        final bottom = 24.0 + (popupIndex < 0 ? 0 : popupIndex * 118.0);
        final accent = _accentForTask(task);
        final icon = _iconForTask(task);
        final canGoBack = task.canNavigate && !task.isFailed;

        return Positioned(
          right: 16,
          bottom: bottom,
          width: 360,
          child: Material(
            color: Colors.transparent,
            child: Container(
              padding: const EdgeInsets.all(14),
              decoration: BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.circular(16),
                border: Border.all(color: accent.withOpacity(0.18)),
                boxShadow: [
                  BoxShadow(
                    color: accent.withOpacity(0.14),
                    blurRadius: 24,
                    offset: const Offset(0, 10),
                  ),
                ],
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisSize: MainAxisSize.min,
                children: [
                  Row(
                    children: [
                      Icon(icon, color: accent),
                      const SizedBox(width: 10),
                      Expanded(
                        child: Text(
                          task.titleSummary,
                          style: const TextStyle(fontWeight: FontWeight.w700),
                        ),
                      ),
                      IconButton(
                        onPressed: () => _remove(entry),
                        icon: const Icon(Icons.close, size: 18),
                        visualDensity: VisualDensity.compact,
                      ),
                    ],
                  ),
                  const SizedBox(height: 4),
                  Text(
                    _messageForTask(strings, task),
                    style: const TextStyle(
                      color: Color(0xFF475569),
                      height: 1.45,
                    ),
                  ),
                  const SizedBox(height: 12),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.end,
                    children: [
                      TextButton(
                        onPressed: () => _remove(entry),
                        child: Text(strings.r3TaskClose),
                      ),
                      if (canGoBack) ...[
                        const SizedBox(width: 8),
                        FilledButton(
                          onPressed: () {
                            _remove(entry);
                            ctx.go(task.deeplink);
                          },
                          child: Text(strings.r3TaskGoBack),
                        ),
                      ],
                    ],
                  ),
                ],
              ),
            ),
          ),
        );
      },
    );

    Overlay.of(ctx, rootOverlay: true).insert(entry);
    _activePopups.add(_ActivePopup(entry: entry));
    Future<void>.delayed(const Duration(seconds: 8), () => _remove(entry));
    return entry;
  }

  static void _remove(OverlayEntry entry) {
    final index = _activePopups.indexWhere((item) => item.entry == entry);
    if (index >= 0) {
      _activePopups.removeAt(index);
    }
    if (entry.mounted) {
      entry.remove();
    }
  }

  static Color _accentForTask(AiTask task) {
    if (task.isFailed) {
      return const Color(0xFFDC2626);
    }
    if (task.isCancelled) {
      return const Color(0xFF64748B);
    }
    return const Color(0xFF16A34A);
  }

  static IconData _iconForTask(AiTask task) {
    if (task.isFailed) {
      return Icons.error_outline;
    }
    if (task.isCancelled) {
      return Icons.remove_circle_outline;
    }
    return Icons.check_circle_outline;
  }

  static String _messageForTask(AppStrings strings, AiTask task) {
    if (task.isFailed) {
      return strings.pick('Tác vụ đã thất bại.', 'The task failed.');
    }
    if (task.isCancelled) {
      return strings.pick('Tác vụ đã bị hủy.', 'The task was cancelled.');
    }
    return strings.pick('Tác vụ đã hoàn tất.', 'The task has completed.');
  }
}

class TaskDonePopupHost extends ConsumerStatefulWidget {
  final Widget child;

  const TaskDonePopupHost({
    super.key,
    required this.child,
  });

  @override
  ConsumerState<TaskDonePopupHost> createState() => _TaskDonePopupHostState();
}

class _TaskDonePopupHostState extends ConsumerState<TaskDonePopupHost> {
  final Map<String, String> _knownStatuses = <String, String>{};
  bool _seeded = false;

  @override
  Widget build(BuildContext context) {
    ref.listen(taskInboxProvider, (_, next) {
      next.whenData(_handleInbox);
    });
    return widget.child;
  }

  void _handleInbox(TaskInbox inbox) {
    final tasks = <AiTask>[
      ...inbox.running,
      ...inbox.recentCompleted,
    ];
    if (!_seeded) {
      for (final task in tasks) {
        _knownStatuses[task.taskId] = task.status;
      }
      _seeded = true;
      return;
    }

    for (final task in inbox.recentCompleted) {
      final previousStatus = _knownStatuses[task.taskId];
      if (task.isDismissed || !_canShowPopup(task, previousStatus)) {
        continue;
      }
      if (!_isForegroundTab()) {
        continue;
      }
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (mounted) {
          TaskDonePopup.show(context, task);
        }
      });
    }

    _knownStatuses
      ..clear()
      ..addEntries(tasks.map((task) => MapEntry(task.taskId, task.status)));
  }

  bool _canShowPopup(AiTask task, String? previousStatus) {
    if (!task.isTerminal) {
      return false;
    }
    if (previousStatus == null) {
      return true;
    }
    return !AiTask.isTerminalStatus(previousStatus);
  }

  bool _isForegroundTab() {
    try {
      return !(html.document.hidden ?? false);
    } catch (_) {
      return true;
    }
  }
}

class _ActivePopup {
  final OverlayEntry entry;

  const _ActivePopup({
    required this.entry,
  });
}
