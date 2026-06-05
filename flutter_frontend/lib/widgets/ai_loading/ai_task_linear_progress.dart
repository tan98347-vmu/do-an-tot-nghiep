import 'dart:async';

import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../core/api_client.dart';
import '../../models/ai_task_state.dart';
import '../../providers/ai_task_progress_provider.dart';
import 'stop_confirm_dialog.dart';

class AITaskLinearProgress extends ConsumerStatefulWidget {
  final String taskId;
  final bool compact;
  final void Function(AITaskState state)? onComplete;
  final void Function(AITaskState state)? onCancelled;
  final void Function(String message)? onFailed;

  const AITaskLinearProgress({
    super.key,
    required this.taskId,
    this.compact = false,
    this.onComplete,
    this.onCancelled,
    this.onFailed,
  });

  @override
  ConsumerState<AITaskLinearProgress> createState() => _AITaskLinearProgressState();
}

class _AITaskLinearProgressState extends ConsumerState<AITaskLinearProgress> {
  final DateTime _startedAt = DateTime.now();
  bool _finalized = false;
  bool _stopping = false;
  Timer? _ticker;
  Duration _elapsed = Duration.zero;
  double _displayedPercent = 0;

  @override
  void initState() {
    super.initState();
    _ticker = Timer.periodic(const Duration(seconds: 1), (_) {
      if (!mounted) return;
      setState(() => _elapsed = DateTime.now().difference(_startedAt));
    });
  }

  @override
  void dispose() {
    _ticker?.cancel();
    super.dispose();
  }

  Future<void> _onStop(AITaskState state) async {
    if (_stopping) return;
    final ok = await StopConfirmDialog.show(
      context,
      stage: state.stage.isNotEmpty ? state.stage : 'Khởi tạo',
      percent: state.percent,
      isHardMode: state.isHardCancel,
    );
    if (ok != true) return;
    setState(() => _stopping = true);
    try {
      await ApiClient().dio.post('ai-tasks/${widget.taskId}/cancel/');
    } on DioException catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(
        content: Text('Lỗi dừng: ${e.message}'),
      ));
    } finally {
      if (mounted) setState(() => _stopping = false);
    }
  }

  ({Color base, Color tint, Color soft}) _palette(String status) {
    switch (status) {
      case 'completed':
        return (
          base: const Color(0xFF16A34A),
          tint: const Color(0xFF22C55E),
          soft: const Color(0xFFDCFCE7),
        );
      case 'failed':
        return (
          base: const Color(0xFFDC2626),
          tint: const Color(0xFFEF4444),
          soft: const Color(0xFFFEE2E2),
        );
      case 'cancelled':
        return (
          base: const Color(0xFFD97706),
          tint: const Color(0xFFF59E0B),
          soft: const Color(0xFFFEF3C7),
        );
      default:
        return (
          base: const Color(0xFF1D4ED8),
          tint: const Color(0xFF3B82F6),
          soft: const Color(0xFFDBEAFE),
        );
    }
  }

  String _formatElapsed() {
    final s = _elapsed.inSeconds;
    if (s < 60) return '${s}s';
    return '${s ~/ 60}m ${(s % 60).toString().padLeft(2, '0')}s';
  }

  @override
  Widget build(BuildContext context) {
    final asyncState = ref.watch(aiTaskProgressProvider(
      AITaskPollConfig(taskId: widget.taskId),
    ));

    return LayoutBuilder(builder: (context, c) {
      final isMobile = c.maxWidth < 700;
      final hPad = widget.compact ? 10.0 : (isMobile ? 14.0 : 18.0);
      final barHeight = widget.compact ? 5.0 : (isMobile ? 7.0 : 9.0);

      return asyncState.when(
        loading: () => Padding(
          padding: EdgeInsets.all(hPad),
          child: ClipRRect(
            borderRadius: BorderRadius.circular(barHeight),
            child: LinearProgressIndicator(minHeight: barHeight),
          ),
        ),
        error: (e, _) => Padding(
          padding: EdgeInsets.all(hPad),
          child: Text('Lỗi: $e',
              style: const TextStyle(color: Colors.red, fontSize: 12)),
        ),
        data: (state) {
          if (state.isTerminal && !_finalized) {
            _finalized = true;
            _ticker?.cancel();
            WidgetsBinding.instance.addPostFrameCallback((_) {
              if (state.status == 'completed') {
                widget.onComplete?.call(state);
              } else if (state.status == 'cancelled') {
                widget.onCancelled?.call(state);
              } else if (state.status == 'failed') {
                widget.onFailed?.call(state.errorMessage ?? 'Thất bại');
              }
            });
          }
          final pct = state.percent.clamp(0, 100).toDouble();
          final palette = _palette(state.status);
          final stageText =
              state.stage.isNotEmpty ? state.stage : state.statusLabel;

          return Container(
            padding: EdgeInsets.symmetric(
                horizontal: hPad, vertical: hPad - 2),
            decoration: BoxDecoration(
              color: palette.soft.withOpacity(0.45),
              borderRadius: BorderRadius.circular(isMobile ? 14 : 18),
              border: Border.all(color: palette.tint.withOpacity(0.25)),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  crossAxisAlignment: CrossAxisAlignment.center,
                  children: [
                    AnimatedSwitcher(
                      duration: const Duration(milliseconds: 200),
                      transitionBuilder: (child, anim) => FadeTransition(
                        opacity: anim,
                        child: SizeTransition(
                          sizeFactor: anim,
                          axis: Axis.horizontal,
                          child: child,
                        ),
                      ),
                      child: Text(
                        '${pct.toInt()}%',
                        key: ValueKey<int>(pct.toInt()),
                        style: TextStyle(
                          fontSize: isMobile ? 18 : 22,
                          fontWeight: FontWeight.w800,
                          color: palette.base,
                          height: 1.1,
                        ),
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Text(
                            stageText,
                            style: TextStyle(
                              fontSize: isMobile ? 12.5 : 14,
                              fontWeight: FontWeight.w700,
                              color: const Color(0xFF0F172A),
                              height: 1.2,
                            ),
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                          ),
                          if (state.detail.isNotEmpty)
                            Padding(
                              padding: const EdgeInsets.only(top: 2),
                              child: Text(
                                state.detail,
                                style: const TextStyle(
                                  fontSize: 11,
                                  color: Color(0xFF64748B),
                                  height: 1.25,
                                ),
                                maxLines: 1,
                                overflow: TextOverflow.ellipsis,
                              ),
                            ),
                        ],
                      ),
                    ),
                    const SizedBox(width: 8),
                    Container(
                      padding: const EdgeInsets.symmetric(
                          horizontal: 6, vertical: 2),
                      decoration: BoxDecoration(
                        color: Colors.white.withOpacity(0.8),
                        borderRadius: BorderRadius.circular(10),
                      ),
                      child: Row(mainAxisSize: MainAxisSize.min, children: [
                        const Icon(Icons.timer_outlined,
                            size: 11, color: Color(0xFF64748B)),
                        const SizedBox(width: 3),
                        Text(
                          _formatElapsed(),
                          style: const TextStyle(
                            fontSize: 11,
                            color: Color(0xFF475569),
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                      ]),
                    ),
                    if (state.isRunning) ...[
                      const SizedBox(width: 4),
                      Tooltip(
                        message: 'Dừng tiến trình',
                        child: Material(
                          color: Colors.transparent,
                          child: InkWell(
                            onTap: _stopping ? null : () => _onStop(state),
                            customBorder: const CircleBorder(),
                            child: Padding(
                              padding: const EdgeInsets.all(6),
                              child: _stopping
                                  ? const SizedBox(
                                      width: 16,
                                      height: 16,
                                      child: CircularProgressIndicator(
                                          strokeWidth: 2),
                                    )
                                  : const Icon(
                                      Icons.stop_circle_rounded,
                                      color: Color(0xFFDC2626),
                                      size: 22,
                                    ),
                            ),
                          ),
                        ),
                      ),
                    ],
                  ],
                ),
                SizedBox(height: hPad - 2),
                TweenAnimationBuilder<double>(
                  tween: Tween<double>(begin: _displayedPercent, end: pct),
                  duration: const Duration(milliseconds: 320),
                  curve: Curves.easeOutCubic,
                  onEnd: () {
                    _displayedPercent = pct;
                  },
                  builder: (context, value, _) {
                    return ClipRRect(
                      borderRadius: BorderRadius.circular(barHeight),
                      child: Stack(children: [
                        Container(
                          height: barHeight,
                          color: Colors.white.withOpacity(0.8),
                        ),
                        FractionallySizedBox(
                          widthFactor: (value / 100).clamp(0.0, 1.0),
                          child: Container(
                            height: barHeight,
                            decoration: BoxDecoration(
                              gradient: LinearGradient(
                                colors: [palette.tint, palette.base],
                              ),
                              borderRadius: BorderRadius.circular(barHeight),
                            ),
                          ),
                        ),
                      ]),
                    );
                  },
                ),
                if (state.status == 'failed' &&
                    (state.errorMessage ?? '').isNotEmpty) ...[
                  const SizedBox(height: 6),
                  Container(
                    padding: const EdgeInsets.symmetric(
                        horizontal: 8, vertical: 4),
                    decoration: BoxDecoration(
                      color: Colors.red.shade50,
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: Row(children: [
                      const Icon(Icons.error_outline,
                          size: 14, color: Colors.red),
                      const SizedBox(width: 6),
                      Expanded(
                        child: Text(
                          state.errorMessage!,
                          style: const TextStyle(
                              fontSize: 11, color: Colors.red),
                          maxLines: 2,
                          overflow: TextOverflow.ellipsis,
                        ),
                      ),
                    ]),
                  ),
                ],
              ],
            ),
          );
        },
      );
    });
  }
}
