import 'dart:math' as math;

import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../core/api_client.dart';
import '../../models/ai_task_state.dart';
import '../../providers/ai_task_progress_provider.dart';
import 'stop_confirm_dialog.dart';

enum CircularSize { compact, expanded }

class AITaskCircularProgress extends ConsumerStatefulWidget {
  final String taskId;
  final CircularSize size;
  final bool showStreamingText;
  final void Function(AITaskState state)? onComplete;
  final void Function(AITaskState state)? onCancelled;
  final void Function(String message)? onFailed;
  final void Function(List<String> chunks)? onStreamingUpdate;

  const AITaskCircularProgress({
    super.key,
    required this.taskId,
    this.size = CircularSize.compact,
    this.showStreamingText = false,
    this.onComplete,
    this.onCancelled,
    this.onFailed,
    this.onStreamingUpdate,
  });

  @override
  ConsumerState<AITaskCircularProgress> createState() =>
      _AITaskCircularProgressState();
}

class _AITaskCircularProgressState
    extends ConsumerState<AITaskCircularProgress>
    with SingleTickerProviderStateMixin {
  bool _finalized = false;
  bool _stopping = false;
  int _lastChunkCount = 0;
  double _displayedValue = 0;
  late final AnimationController _pulse;
  final ScrollController _streamScrollCtrl = ScrollController();

  @override
  void initState() {
    super.initState();
    _pulse = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1400),
    )..repeat(reverse: true);
  }

  @override
  void dispose() {
    _pulse.dispose();
    _streamScrollCtrl.dispose();
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
      ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Lỗi dừng: ${e.message}')));
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

  @override
  Widget build(BuildContext context) {
    final asyncState = ref.watch(aiTaskProgressProvider(
      AITaskPollConfig(
        taskId: widget.taskId,
        pollInterval: const Duration(milliseconds: 400),
      ),
    ));
    final compact = widget.size == CircularSize.compact;
    final dim = compact ? 56.0 : 128.0;

    return asyncState.when(
      loading: () => SizedBox(
        width: dim,
        height: dim,
        child: const Center(child: CircularProgressIndicator()),
      ),
      error: (e, _) => Text('Lỗi: $e',
          style: const TextStyle(color: Colors.red, fontSize: 11)),
      data: (state) {
        if (state.streamingChunks.length != _lastChunkCount) {
          _lastChunkCount = state.streamingChunks.length;
          WidgetsBinding.instance.addPostFrameCallback((_) {
            widget.onStreamingUpdate?.call(state.streamingChunks);
            if (_streamScrollCtrl.hasClients) {
              _streamScrollCtrl.animateTo(
                _streamScrollCtrl.position.maxScrollExtent,
                duration: const Duration(milliseconds: 200),
                curve: Curves.easeOut,
              );
            }
          });
        }
        if (state.isTerminal && !_finalized) {
          _finalized = true;
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
        return compact ? _buildCompact(state) : _buildExpanded(state);
      },
    );
  }

  Widget _animatedRing({
    required double size,
    required double strokeWidth,
    required double targetValue,
    required Color base,
    required Color tint,
    required bool spin,
  }) {
    return TweenAnimationBuilder<double>(
      tween: Tween<double>(begin: _displayedValue, end: targetValue),
      duration: const Duration(milliseconds: 320),
      curve: Curves.easeOutCubic,
      onEnd: () => _displayedValue = targetValue,
      builder: (context, value, _) {
        return AnimatedBuilder(
          animation: _pulse,
          builder: (context, __) {
            final pulseValue = spin
                ? (math.sin(_pulse.value * math.pi * 2) * 0.05)
                : 0.0;
            return CustomPaint(
              size: Size(size, size),
              painter: _RingPainter(
                value: value.clamp(0.0, 100.0) / 100.0,
                pulseExtra: pulseValue.abs(),
                strokeWidth: strokeWidth,
                base: base,
                tint: tint,
                trackColor: Colors.grey.shade200,
              ),
            );
          },
        );
      },
    );
  }

  Widget _buildCompact(AITaskState state) {
    final pct = state.percent.clamp(0, 100);
    final palette = _palette(state.status);
    return SizedBox(
      width: 56,
      height: 56,
      child: Stack(alignment: Alignment.center, children: [
        _animatedRing(
          size: 56,
          strokeWidth: 4.5,
          targetValue: pct.toDouble(),
          base: palette.base,
          tint: palette.tint,
          spin: state.isRunning,
        ),
        Column(mainAxisSize: MainAxisSize.min, children: [
          Text(
            '$pct%',
            style: TextStyle(
              fontSize: 13,
              fontWeight: FontWeight.w800,
              color: palette.base,
              height: 1.05,
            ),
          ),
        ]),
        if (state.isRunning)
          Positioned(
            top: -6,
            right: -6,
            child: Semantics(
              button: true,
              label: 'Dừng tiến trình',
              child: Material(
                color: Colors.white,
                shape: const CircleBorder(),
                elevation: 2,
                child: InkWell(
                  onTap: _stopping ? null : () => _onStop(state),
                  customBorder: const CircleBorder(),
                  child: Padding(
                    padding: const EdgeInsets.all(3),
                    child: Icon(
                      Icons.close_rounded,
                      size: 12,
                      color: _stopping
                          ? Colors.grey
                          : const Color(0xFFDC2626),
                    ),
                  ),
                ),
              ),
            ),
          ),
      ]),
    );
  }

  Widget _buildExpanded(AITaskState state) {
    final pct = state.percent.clamp(0, 100);
    final palette = _palette(state.status);
    final stageText =
        state.stage.isNotEmpty ? state.stage : state.statusLabel;
    return Column(mainAxisSize: MainAxisSize.min, children: [
      SizedBox(
        width: 144,
        height: 144,
        child: Stack(alignment: Alignment.center, children: [
          _animatedRing(
            size: 144,
            strokeWidth: 10,
            targetValue: pct.toDouble(),
            base: palette.base,
            tint: palette.tint,
            spin: state.isRunning,
          ),
          Column(mainAxisSize: MainAxisSize.min, children: [
            Text(
              '$pct%',
              style: TextStyle(
                fontSize: 28,
                fontWeight: FontWeight.w900,
                color: palette.base,
                height: 1.05,
              ),
            ),
            const SizedBox(height: 2),
            Text(
              state.statusLabel,
              style: const TextStyle(
                  fontSize: 11,
                  color: Color(0xFF64748B),
                  fontWeight: FontWeight.w600),
            ),
          ]),
        ]),
      ),
      const SizedBox(height: 14),
      AnimatedSwitcher(
        duration: const Duration(milliseconds: 240),
        child: Text(
          stageText,
          key: ValueKey<String>(stageText),
          style: const TextStyle(
            fontSize: 16,
            fontWeight: FontWeight.w700,
            color: Color(0xFF0F172A),
            height: 1.25,
          ),
          textAlign: TextAlign.center,
        ),
      ),
      if (state.detail.isNotEmpty) ...[
        const SizedBox(height: 4),
        Text(
          state.detail,
          style: const TextStyle(
              fontSize: 12, color: Color(0xFF64748B), height: 1.35),
          textAlign: TextAlign.center,
          maxLines: 2,
          overflow: TextOverflow.ellipsis,
        ),
      ],
      if (widget.showStreamingText &&
          state.streamingChunks.isNotEmpty) ...[
        const SizedBox(height: 12),
        Container(
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(
            color: palette.soft.withOpacity(0.6),
            borderRadius: BorderRadius.circular(12),
            border: Border.all(color: palette.tint.withOpacity(0.3)),
          ),
          constraints: const BoxConstraints(maxHeight: 110),
          child: Scrollbar(
            controller: _streamScrollCtrl,
            child: SingleChildScrollView(
              controller: _streamScrollCtrl,
              child: Text(
                state.streamingText,
                style: const TextStyle(
                  fontSize: 12.5,
                  height: 1.45,
                  color: Color(0xFF0F172A),
                ),
              ),
            ),
          ),
        ),
      ],
      if (state.isRunning) ...[
        const SizedBox(height: 16),
        Semantics(
          button: true,
          label: 'Dừng tiến trình',
          child: OutlinedButton.icon(
            icon: _stopping
                ? const SizedBox(
                    width: 14,
                    height: 14,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  )
                : const Icon(Icons.stop_circle_outlined,
                    color: Colors.red, size: 20),
            label: const Text(
              'Dừng',
              style: TextStyle(
                color: Colors.red,
                fontWeight: FontWeight.w700,
              ),
            ),
            style: OutlinedButton.styleFrom(
              padding: const EdgeInsets.symmetric(
                  horizontal: 22, vertical: 10),
              side: const BorderSide(color: Colors.red, width: 1.2),
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(24),
              ),
            ),
            onPressed: _stopping ? null : () => _onStop(state),
          ),
        ),
      ],
      if (state.status == 'failed' &&
          (state.errorMessage ?? '').isNotEmpty) ...[
        const SizedBox(height: 12),
        Container(
          padding: const EdgeInsets.symmetric(
              horizontal: 12, vertical: 8),
          decoration: BoxDecoration(
            color: Colors.red.shade50,
            borderRadius: BorderRadius.circular(10),
            border: Border.all(color: Colors.red.shade200),
          ),
          child: Row(mainAxisSize: MainAxisSize.min, children: [
            const Icon(Icons.error_outline,
                color: Colors.red, size: 16),
            const SizedBox(width: 6),
            Flexible(
              child: Text(
                state.errorMessage!,
                style: const TextStyle(
                    color: Colors.red, fontSize: 12),
                textAlign: TextAlign.center,
              ),
            ),
          ]),
        ),
      ],
    ]);
  }
}

class _RingPainter extends CustomPainter {
  final double value;
  final double pulseExtra;
  final double strokeWidth;
  final Color base;
  final Color tint;
  final Color trackColor;

  _RingPainter({
    required this.value,
    required this.pulseExtra,
    required this.strokeWidth,
    required this.base,
    required this.tint,
    required this.trackColor,
  });

  @override
  void paint(Canvas canvas, Size size) {
    final center = Offset(size.width / 2, size.height / 2);
    final radius = (math.min(size.width, size.height) - strokeWidth) / 2;
    final rect = Rect.fromCircle(center: center, radius: radius);

    final trackPaint = Paint()
      ..color = trackColor
      ..style = PaintingStyle.stroke
      ..strokeWidth = strokeWidth
      ..strokeCap = StrokeCap.round;
    canvas.drawArc(rect, 0, math.pi * 2, false, trackPaint);

    if (value > 0) {
      final sweep = math.pi * 2 * value;
      final start = -math.pi / 2;
      final gradient = SweepGradient(
        startAngle: start,
        endAngle: start + sweep,
        tileMode: TileMode.clamp,
        colors: [tint, base],
      );
      final progressPaint = Paint()
        ..shader = gradient.createShader(rect)
        ..style = PaintingStyle.stroke
        ..strokeWidth = strokeWidth + pulseExtra * strokeWidth
        ..strokeCap = StrokeCap.round;
      canvas.drawArc(rect, start, sweep, false, progressPaint);
    }
  }

  @override
  bool shouldRepaint(_RingPainter old) =>
      old.value != value ||
      old.pulseExtra != pulseExtra ||
      old.base != base ||
      old.tint != tint;
}
