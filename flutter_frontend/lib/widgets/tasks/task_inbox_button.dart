import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../l10n/app_strings.dart';
import '../../providers/ai_task_progress_provider.dart';
import 'task_inbox_panel.dart';

// r4 imports this standalone widget into app_shell.dart.
class TaskInboxButton extends ConsumerWidget {
  final Color? iconColor;
  const TaskInboxButton({super.key, this.iconColor});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final strings = AppStrings.of(context);
    final inboxAsync = ref.watch(taskInboxProvider);
    final runningCount = inboxAsync.maybeWhen(
      data: (inbox) => inbox.running.length,
      orElse: () => 0,
    );

    return Stack(
      clipBehavior: Clip.none,
      children: [
        IconButton(
          tooltip: strings.r3TaskInboxOpen,
          onPressed: () => showTaskInboxPanel(context),
          icon: Icon(Icons.task_alt_outlined, color: iconColor),
        ),
        if (runningCount > 0)
          Positioned(
            right: 6,
            top: 6,
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 5, vertical: 2),
              decoration: BoxDecoration(
                color: const Color(0xFFDC2626),
                borderRadius: BorderRadius.circular(999),
              ),
              child: Text(
                '$runningCount',
                style: const TextStyle(
                  color: Colors.white,
                  fontSize: 11,
                  fontWeight: FontWeight.w700,
                ),
              ),
            ),
          ),
      ],
    );
  }
}
