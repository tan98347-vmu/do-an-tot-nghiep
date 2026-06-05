import 'package:flutter/material.dart';

class StopConfirmDialog extends StatelessWidget {
  final String stage;
  final int percent;
  final bool isHardMode;

  const StopConfirmDialog({
    super.key,
    required this.stage,
    required this.percent,
    required this.isHardMode,
  });

  static Future<bool?> show(
    BuildContext context, {
    required String stage,
    required int percent,
    required bool isHardMode,
  }) {
    return showDialog<bool>(
      context: context,
      barrierColor: Colors.black.withOpacity(0.42),
      builder: (_) => StopConfirmDialog(
        stage: stage,
        percent: percent,
        isHardMode: isHardMode,
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final width = MediaQuery.sizeOf(context).width;
    final isMobile = width < 500;
    final accent = isHardMode
        ? const Color(0xFFDC2626)
        : const Color(0xFFD97706);
    final accentSoft = isHardMode
        ? const Color(0xFFFEE2E2)
        : const Color(0xFFFEF3C7);

    return Dialog(
      backgroundColor: Colors.transparent,
      insetPadding: EdgeInsets.symmetric(
          horizontal: isMobile ? 18 : 32, vertical: 24),
      child: ConstrainedBox(
        constraints: BoxConstraints(maxWidth: isMobile ? width : 420),
        child: Material(
          color: Colors.white,
          borderRadius: BorderRadius.circular(22),
          elevation: 16,
          child: Padding(
            padding: EdgeInsets.fromLTRB(
                isMobile ? 18 : 22, 22, isMobile ? 18 : 22, 18),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(children: [
                  Container(
                    padding: const EdgeInsets.all(10),
                    decoration: BoxDecoration(
                      color: accentSoft,
                      shape: BoxShape.circle,
                    ),
                    child: Icon(
                      isHardMode
                          ? Icons.warning_amber_rounded
                          : Icons.pause_circle_outline,
                      color: accent,
                      size: 26,
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Text(
                      isHardMode
                          ? 'Dừng tiến trình ngay?'
                          : 'Dừng tiến trình AI?',
                      style: const TextStyle(
                        fontSize: 18,
                        fontWeight: FontWeight.w800,
                        color: Color(0xFF0F172A),
                      ),
                    ),
                  ),
                ]),
                const SizedBox(height: 14),
                Container(
                  padding: const EdgeInsets.symmetric(
                      horizontal: 12, vertical: 10),
                  decoration: BoxDecoration(
                    color: const Color(0xFFF1F5F9),
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: Row(children: [
                    Container(
                      padding: const EdgeInsets.symmetric(
                          horizontal: 8, vertical: 3),
                      decoration: BoxDecoration(
                        color: accent,
                        borderRadius: BorderRadius.circular(8),
                      ),
                      child: Text(
                        '$percent%',
                        style: const TextStyle(
                          color: Colors.white,
                          fontSize: 13,
                          fontWeight: FontWeight.w800,
                        ),
                      ),
                    ),
                    const SizedBox(width: 10),
                    Expanded(
                      child: Text(
                        stage,
                        style: const TextStyle(
                          fontSize: 13,
                          fontWeight: FontWeight.w700,
                          color: Color(0xFF0F172A),
                        ),
                        maxLines: 2,
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                  ]),
                ),
                const SizedBox(height: 12),
                Container(
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: accentSoft,
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(color: accent.withOpacity(0.3)),
                  ),
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Icon(
                        isHardMode
                            ? Icons.flash_on_rounded
                            : Icons.info_outline,
                        color: accent,
                        size: 18,
                      ),
                      const SizedBox(width: 8),
                      Expanded(
                        child: Text(
                          isHardMode
                              ? 'Chế độ dừng cứng — sẽ ngắt kết nối ngay lập tức. Dữ liệu đang upload hoặc OCR sẽ bị mất.'
                              : 'Chế độ dừng mềm — AI sẽ kết thúc bước hiện tại trong vài giây rồi mới dừng. Phần đã sinh sẽ được lưu lại.',
                          style: TextStyle(
                            fontSize: 12,
                            color: accent,
                            height: 1.45,
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 18),
                Row(
                  mainAxisAlignment: MainAxisAlignment.end,
                  children: [
                    TextButton(
                      onPressed: () => Navigator.pop(context, false),
                      style: TextButton.styleFrom(
                        foregroundColor: const Color(0xFF475569),
                        padding: const EdgeInsets.symmetric(
                            horizontal: 16, vertical: 10),
                      ),
                      child: const Text('Tiếp tục chạy'),
                    ),
                    const SizedBox(width: 8),
                    FilledButton.icon(
                      icon: Icon(
                        isHardMode
                            ? Icons.flash_on_rounded
                            : Icons.stop_rounded,
                        size: 18,
                      ),
                      label: Text(
                        isHardMode ? 'Dừng ngay' : 'Dừng',
                        style:
                            const TextStyle(fontWeight: FontWeight.w700),
                      ),
                      style: FilledButton.styleFrom(
                        backgroundColor: accent,
                        padding: const EdgeInsets.symmetric(
                            horizontal: 18, vertical: 12),
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(14),
                        ),
                      ),
                      onPressed: () => Navigator.pop(context, true),
                    ),
                  ],
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
