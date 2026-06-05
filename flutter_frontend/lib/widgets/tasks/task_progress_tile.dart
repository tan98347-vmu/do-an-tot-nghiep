import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/api_client.dart';
import '../../l10n/app_strings.dart';
import '../../models/ai_task.dart';
import '../../providers/ai_task_progress_provider.dart';

class TaskProgressTile extends ConsumerWidget {
  final AiTask task;

  const TaskProgressTile({
    super.key,
    required this.task,
  });

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final strings = AppStrings.of(context);
    final accent = _accentForTask(task);
    final icon = _iconForTask(task.taskType);

    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: const Color(0xFFE2E8F0)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Container(
                width: 40,
                height: 40,
                decoration: BoxDecoration(
                  color: accent.withOpacity(0.12),
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Icon(icon, color: accent),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      task.titleSummary,
                      style: const TextStyle(
                        fontWeight: FontWeight.w700,
                        fontSize: 15,
                      ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      task.statusLabel,
                      style: TextStyle(
                        color: accent,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
          if (task.progressStage.isNotEmpty) ...[
            const SizedBox(height: 12),
            Text(
              task.progressStage,
              style: const TextStyle(fontWeight: FontWeight.w600),
            ),
          ],
          if (task.progressDetail.isNotEmpty) ...[
            const SizedBox(height: 4),
            Text(
              task.progressDetail,
              style: const TextStyle(
                color: Color(0xFF64748B),
                height: 1.4,
              ),
            ),
          ],
          if (task.isRunning) ...[
            const SizedBox(height: 12),
            LinearProgressIndicator(
              value: (task.progressPercent.clamp(0, 100)) / 100,
              minHeight: 8,
              borderRadius: BorderRadius.circular(999),
            ),
          ] else if (task.isFailed && task.errorMessage.isNotEmpty) ...[
            const SizedBox(height: 12),
            Text(
              task.errorMessage,
              style: const TextStyle(
                color: Color(0xFFB91C1C),
                height: 1.4,
              ),
            ),
          ],
          const SizedBox(height: 12),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              if (task.canNavigate)
                FilledButton.tonal(
                  onPressed: () => context.go(task.deeplink),
                  child: Text(strings.r3TaskGoBack),
                ),
              if (task.isRunning)
                OutlinedButton(
                  onPressed: () => _cancelTask(context, ref),
                  child: Text(strings.r3TaskCancel),
                ),
              if (task.isTerminal && !task.isDismissed)
                TextButton(
                  onPressed: () => _dismissTask(context, ref),
                  child: Text(strings.r3TaskDismiss),
                ),
            ],
          ),
        ],
      ),
    );
  }

  Future<void> _cancelTask(BuildContext context, WidgetRef ref) async {
    try {
      await ApiClient().dio.post('ai-tasks/${task.taskId}/cancel/');
      ref.invalidate(taskInboxProvider);
    } catch (error) {
      if (!context.mounted) {
        return;
      }
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Không hủy được tác vụ: $error')),
      );
    }
  }

  Future<void> _dismissTask(BuildContext context, WidgetRef ref) async {
    try {
      await ApiClient().dio.post('ai-tasks/${task.taskId}/dismiss/');
      ref.invalidate(taskInboxProvider);
    } catch (error) {
      if (!context.mounted) {
        return;
      }
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Không đóng được tác vụ: $error')),
      );
    }
  }

  IconData _iconForTask(String taskType) {
    switch (taskType) {
      case 'voice':
      case 'voice_chat':
        return Icons.mic_none_outlined;
      case 'chat':
        return Icons.chat_bubble_outline;
      case 'bulk_template_upload':
        return Icons.upload_file_outlined;
      case 'document_summary':
        return Icons.summarize_outlined;
      case 'compliance_check':
        return Icons.fact_check_outlined;
      case 'word_ai_edit':
        return Icons.edit_note_outlined;
      case 'company_backup_export':
        return Icons.archive_outlined;
      default:
        return Icons.auto_awesome_outlined;
    }
  }

  Color _accentForTask(AiTask item) {
    if (item.isFailed) {
      return const Color(0xFFDC2626);
    }
    if (item.isCancelled) {
      return const Color(0xFF64748B);
    }
    if (item.isRunning) {
      return const Color(0xFF2563EB);
    }
    return const Color(0xFF16A34A);
  }
}
