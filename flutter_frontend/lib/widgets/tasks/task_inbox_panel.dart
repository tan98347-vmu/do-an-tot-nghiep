import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../l10n/app_strings.dart';
import '../../models/ai_task.dart';
import '../../providers/ai_task_progress_provider.dart';
import 'task_progress_tile.dart';

Future<void> showTaskInboxPanel(BuildContext context) async {
  if (MediaQuery.sizeOf(context).width < 720) {
    await showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      showDragHandle: true,
      builder: (_) => const TaskInboxPanel(),
    );
    return;
  }

  await showGeneralDialog<void>(
    context: context,
    barrierDismissible: true,
    barrierLabel: 'task-inbox',
    barrierColor: Colors.black.withOpacity(0.24),
    transitionDuration: const Duration(milliseconds: 220),
    pageBuilder: (_, __, ___) => const Align(
      alignment: Alignment.centerRight,
      child: TaskInboxPanel(),
    ),
    transitionBuilder: (_, animation, __, child) {
      final offset = Tween<Offset>(
        begin: const Offset(1, 0),
        end: Offset.zero,
      ).animate(CurvedAnimation(parent: animation, curve: Curves.easeOutCubic));
      return SlideTransition(position: offset, child: child);
    },
  );
}

class TaskInboxPanel extends ConsumerWidget {
  const TaskInboxPanel({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final strings = AppStrings.of(context);
    final inboxAsync = ref.watch(taskInboxProvider);
    final maxWidth = MediaQuery.sizeOf(context).width < 720 ? double.infinity : 420.0;

    return SafeArea(
      child: Material(
        color: Colors.white,
        child: SizedBox(
          width: maxWidth,
          child: Column(
            children: [
              Padding(
                padding: const EdgeInsets.fromLTRB(18, 18, 18, 12),
                child: Row(
                  children: [
                    Expanded(
                      child: Text(
                        strings.r3TaskInboxTitle,
                        style: const TextStyle(
                          fontSize: 20,
                          fontWeight: FontWeight.w800,
                        ),
                      ),
                    ),
                    IconButton(
                      onPressed: () => ref.invalidate(taskInboxProvider),
                      icon: const Icon(Icons.refresh),
                    ),
                    IconButton(
                      onPressed: () => Navigator.of(context).pop(),
                      icon: const Icon(Icons.close),
                    ),
                  ],
                ),
              ),
              const Divider(height: 1),
              Expanded(
                child: inboxAsync.when(
                  loading: () => const Center(child: CircularProgressIndicator()),
                  error: (error, _) => Center(
                    child: Padding(
                      padding: const EdgeInsets.all(24),
                      child: Text(
                        'Không tải được danh sách tác vụ: $error',
                        textAlign: TextAlign.center,
                      ),
                    ),
                  ),
                  data: (inbox) {
                    if (inbox.running.isEmpty && inbox.recentCompleted.isEmpty) {
                      return Center(
                        child: Padding(
                          padding: const EdgeInsets.all(24),
                          child: Text(
                            strings.r3TaskNoItems,
                            textAlign: TextAlign.center,
                            style: const TextStyle(color: Color(0xFF64748B)),
                          ),
                        ),
                      );
                    }
                    return ListView(
                      padding: const EdgeInsets.all(16),
                      children: [
                        _TaskSection(
                          title: strings.r3TaskRunningSection,
                          tasks: inbox.running,
                        ),
                        const SizedBox(height: 18),
                        _TaskSection(
                          title: strings.r3TaskRecentSection,
                          tasks: inbox.recentCompleted,
                        ),
                      ],
                    );
                  },
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _TaskSection extends StatelessWidget {
  final String title;
  final List<AiTask> tasks;

  const _TaskSection({
    required this.title,
    required this.tasks,
  });

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          title,
          style: const TextStyle(
            fontSize: 15,
            fontWeight: FontWeight.w800,
          ),
        ),
        const SizedBox(height: 12),
        if (tasks.isEmpty)
          const Text(
            'Trống.',
            style: TextStyle(color: Color(0xFF94A3B8)),
          )
        else
          ...tasks.map(
            (task) => Padding(
              padding: const EdgeInsets.only(bottom: 10),
              child: TaskProgressTile(task: task),
            ),
          ),
      ],
    );
  }
}
