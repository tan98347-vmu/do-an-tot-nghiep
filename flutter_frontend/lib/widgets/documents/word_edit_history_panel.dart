import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/word_ai_user_messages.dart';
import '../../providers/documents_provider.dart';
import '../../providers/word_ai_provider.dart';
import '../../models/word_ai_job.dart';
import 'word_edit_job_status_card.dart';

class WordEditHistoryPanel extends ConsumerStatefulWidget {
  final int documentId;
  final VoidCallback? onDocumentChanged;

  const WordEditHistoryPanel({
    super.key,
    required this.documentId,
    this.onDocumentChanged,
  });

  @override
  ConsumerState<WordEditHistoryPanel> createState() => _WordEditHistoryPanelState();
}

class _WordEditHistoryPanelState extends ConsumerState<WordEditHistoryPanel> {
  static const Duration _activePollInterval = Duration(seconds: 4);

  Timer? _pollTimer;
  Map<int, String> _lastKnownStatuses = <int, String>{};
  bool _statusCachePrimed = false;

  @override
  void dispose() {
    _pollTimer?.cancel();
    super.dispose();
  }

  void _ensurePolling(bool enabled) {
    if (!enabled) {
      _pollTimer?.cancel();
      _pollTimer = null;
      return;
    }
    _pollTimer ??= Timer.periodic(_activePollInterval, (_) {
      if (!mounted) {
        return;
      }
      refreshWordAiJobs(ref);
    });
  }

  void _handleStatusSnapshot(List<WordAiJob> jobs) {
    final snapshot = <int, String>{
      for (final job in jobs) job.id: job.status,
    };
    final hasActiveJob = jobs.any((job) => job.isActive);
    _ensurePolling(hasActiveJob);
    if (!_statusCachePrimed) {
      _lastKnownStatuses = snapshot;
      _statusCachePrimed = true;
      return;
    }
    for (final job in jobs) {
      final previousStatus = _lastKnownStatuses[job.id];
      if (previousStatus == job.status) {
        continue;
      }
      if (previousStatus == null) {
        if (_isTerminalStatus(job.status)) {
          _handleStatusTransition(job, '');
        }
        continue;
      }
      _handleStatusTransition(job, previousStatus);
    }
    _lastKnownStatuses = snapshot;
  }

  bool _isTerminalStatus(String status) {
    return status == 'completed' || status == 'failed' || status == 'needs_review' || status == 'cancelled';
  }

  void _handleStatusTransition(WordAiJob job, String previousStatus) {
    final messenger = ScaffoldMessenger.maybeOf(context);
    if (messenger == null) {
      return;
    }
    if (job.status == 'completed' && previousStatus != 'completed') {
      refreshDocumentCollections(ref);
      widget.onDocumentChanged?.call();
      messenger.showSnackBar(
        const SnackBar(
          content: Text(
            'Word AI đã tạo xong phiên bản mới. Màn hình đang cập nhật để hiển thị nội dung mới nhất.',
          ),
          backgroundColor: Color(0xFF166534),
        ),
      );
      return;
    }
    if (job.status == 'failed' || job.status == 'needs_review') {
      messenger.showSnackBar(
        SnackBar(
          content: Text(wordAiFailureForUser(job)),
          backgroundColor: const Color(0xFF991B1B),
        ),
      );
      return;
    }
    if (job.status == 'cancelled' && previousStatus != 'cancelled') {
      messenger.showSnackBar(
        const SnackBar(
          content: Text('Yêu cầu Word AI đã được hủy. Văn bản hiện tại không bị thay đổi.'),
        ),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final jobsAsync = ref.watch(wordAiJobHistoryProvider(widget.documentId));
    return Card(
      clipBehavior: Clip.antiAlias,
      child: ExpansionTile(
        leading: const Icon(Icons.auto_awesome, size: 20),
        title: Text(
          'Lịch sử Word AI',
          style: Theme.of(context).textTheme.titleSmall?.copyWith(fontWeight: FontWeight.bold),
        ),
        subtitle: const Text('Tiến độ xử lý, kiểm tra và các phiên bản đã tạo', style: TextStyle(fontSize: 11)),
        childrenPadding: const EdgeInsets.fromLTRB(16, 0, 16, 16),
        children: [
          jobsAsync.when(
            data: (jobs) {
              WidgetsBinding.instance.addPostFrameCallback((_) {
                if (!mounted) {
                  return;
                }
                _handleStatusSnapshot(jobs);
              });
              if (jobs.isEmpty) {
                return const Padding(
                  padding: EdgeInsets.only(bottom: 8),
                  child: Align(
                    alignment: Alignment.centerLeft,
                    child: Text(
                      'Chưa có lần chỉnh sửa Word AI nào cho văn bản này.',
                      style: TextStyle(color: Color(0xFF64748B)),
                    ),
                  ),
                );
              }
              return Column(
                children: [
                  for (final job in jobs) ...[
                    WordEditJobStatusCard(
                      job: job,
                      onCancel: job.canCancel
                          ? () async {
                              await cancelWordAiJob(job.id);
                              refreshWordAiJobs(ref);
                            }
                          : null,
                    ),
                    if (job != jobs.last) const SizedBox(height: 12),
                  ],
                ],
              );
            },
            error: (error, _) => Align(
              alignment: Alignment.centerLeft,
              child: Text(
                'Không tải được lịch sử Word AI: $error',
                style: const TextStyle(color: Color(0xFF991B1B)),
              ),
            ),
            loading: () => const Padding(
              padding: EdgeInsets.all(12),
              child: CircularProgressIndicator(),
            ),
          ),
        ],
      ),
    );
  }
}
