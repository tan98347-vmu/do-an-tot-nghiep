import 'dart:ui';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'ai_task_circular_progress.dart';
import 'ai_task_linear_progress.dart';

enum AITaskDialogStyle { linear, circularCompact, circularExpanded }

class AITaskDialog extends ConsumerWidget {
  final String taskId;
  final AITaskDialogStyle style;
  final String? title;
  final String? subtitle;
  final bool showStreamingText;

  const AITaskDialog({
    super.key,
    required this.taskId,
    required this.style,
    this.title,
    this.subtitle,
    this.showStreamingText = false,
  });

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final size = MediaQuery.sizeOf(context);
    final isMobile = size.width < 700;
    final isExpanded = style == AITaskDialogStyle.circularExpanded;

    final linearProgress = AITaskLinearProgress(
      taskId: taskId,
      onComplete: (s) =>
          Navigator.of(context).pop({'status': 'completed', 'result': s.result}),
      onCancelled: (s) => Navigator.of(context).pop({'status': 'cancelled'}),
      onFailed: (msg) =>
          Navigator.of(context).pop({'status': 'failed', 'error': msg}),
    );
    final circularProgress = AITaskCircularProgress(
      taskId: taskId,
      size: style == AITaskDialogStyle.circularCompact
          ? CircularSize.compact
          : CircularSize.expanded,
      showStreamingText: showStreamingText,
      onComplete: (s) =>
          Navigator.of(context).pop({'status': 'completed', 'result': s.result}),
      onCancelled: (s) => Navigator.of(context).pop({'status': 'cancelled'}),
      onFailed: (msg) =>
          Navigator.of(context).pop({'status': 'failed', 'error': msg}),
    );

    if (isExpanded) {
      final panel = Container(
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(isMobile ? 24 : 28),
          boxShadow: [
            BoxShadow(
              color: Colors.black.withOpacity(isMobile ? 0.0 : 0.18),
              blurRadius: 32,
              offset: const Offset(0, 12),
            ),
          ],
        ),
        constraints: BoxConstraints(
          maxWidth: isMobile ? size.width : 560,
          maxHeight: isMobile ? size.height : 600,
        ),
        child: Padding(
          padding: EdgeInsets.fromLTRB(
            isMobile ? 22 : 30,
            isMobile ? 26 : 32,
            isMobile ? 22 : 30,
            isMobile ? 22 : 28,
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              if (title != null) ...[
                Row(
                  crossAxisAlignment: CrossAxisAlignment.center,
                  children: [
                    Container(
                      padding: const EdgeInsets.all(8),
                      decoration: BoxDecoration(
                        gradient: const LinearGradient(
                          colors: [Color(0xFF1D4ED8), Color(0xFF3B82F6)],
                        ),
                        borderRadius: BorderRadius.circular(10),
                      ),
                      child: const Icon(
                        Icons.auto_awesome,
                        color: Colors.white,
                        size: 20,
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Text(
                        title!,
                        style: const TextStyle(
                          fontSize: 18,
                          fontWeight: FontWeight.w800,
                          color: Color(0xFF0F172A),
                        ),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 10),
              ],
              if (subtitle != null) ...[
                Text(
                  subtitle!,
                  textAlign: TextAlign.center,
                  style: const TextStyle(
                    fontSize: 13,
                    color: Color(0xFF64748B),
                    height: 1.5,
                  ),
                ),
                const SizedBox(height: 22),
              ],
              Flexible(
                child: SingleChildScrollView(
                  child: Center(child: circularProgress),
                ),
              ),
            ],
          ),
        ),
      );

      return PopScope(
        canPop: false,
        child: isMobile
            ? Dialog.fullscreen(
                backgroundColor: Colors.transparent,
                child: Container(
                  color: Colors.black.withOpacity(0.45),
                  padding: const EdgeInsets.all(14),
                  child: SafeArea(child: Center(child: panel)),
                ),
              )
            : Dialog(
                backgroundColor: Colors.transparent,
                elevation: 0,
                insetPadding: const EdgeInsets.all(24),
                child: ClipRRect(
                  borderRadius: BorderRadius.circular(28),
                  child: BackdropFilter(
                    filter: ImageFilter.blur(sigmaX: 14, sigmaY: 14),
                    child: panel,
                  ),
                ),
              ),
      );
    }

    return PopScope(
      canPop: false,
      child: Dialog(
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(18),
        ),
        insetPadding: EdgeInsets.symmetric(
            horizontal: isMobile ? 18 : 32, vertical: 24),
        child: ConstrainedBox(
          constraints: BoxConstraints(
            maxWidth: isMobile ? size.width : 520,
          ),
          child: Padding(
            padding: const EdgeInsets.fromLTRB(20, 18, 20, 18),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                if (title != null) ...[
                  Row(children: [
                    Container(
                      padding: const EdgeInsets.all(6),
                      decoration: BoxDecoration(
                        gradient: const LinearGradient(
                          colors: [Color(0xFF1D4ED8), Color(0xFF3B82F6)],
                        ),
                        borderRadius: BorderRadius.circular(8),
                      ),
                      child: const Icon(Icons.auto_awesome,
                          color: Colors.white, size: 16),
                    ),
                    const SizedBox(width: 10),
                    Expanded(
                      child: Text(
                        title!,
                        style: const TextStyle(
                          fontSize: 15,
                          fontWeight: FontWeight.w800,
                          color: Color(0xFF0F172A),
                        ),
                      ),
                    ),
                  ]),
                  const SizedBox(height: 10),
                ],
                if (subtitle != null) ...[
                  Text(
                    subtitle!,
                    style: const TextStyle(
                      fontSize: 12,
                      color: Color(0xFF64748B),
                      height: 1.45,
                    ),
                  ),
                  const SizedBox(height: 14),
                ],
                if (style == AITaskDialogStyle.linear)
                  linearProgress
                else
                  Center(child: circularProgress),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
