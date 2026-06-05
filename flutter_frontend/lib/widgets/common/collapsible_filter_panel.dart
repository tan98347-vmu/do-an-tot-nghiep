import 'package:flutter/material.dart';

/// Panel bộ lọc luôn khởi tạo ở trạng thái ẩn (collapsed).
///
/// - Không lưu state vào SharedPreferences / disk: mỗi lần widget được mount
///   sẽ bắt đầu ở trạng thái ẩn theo yêu cầu UX (roadmap29-5 mục A).
/// - Khi `badgeCount > 0` hiển thị badge nhỏ kế bên tiêu đề để báo có filter
///   đang active dù panel đang ẩn.
class CollapsibleFilterPanel extends StatefulWidget {
  final String title;
  final IconData icon;
  final int badgeCount;
  final Widget child;
  final EdgeInsetsGeometry? padding;
  final EdgeInsetsGeometry? headerPadding;
  final bool dense;

  const CollapsibleFilterPanel({
    super.key,
    required this.child,
    this.title = 'Bộ lọc',
    this.icon = Icons.filter_alt_outlined,
    this.badgeCount = 0,
    this.padding,
    this.headerPadding,
    this.dense = false,
  });

  @override
  State<CollapsibleFilterPanel> createState() => _CollapsibleFilterPanelState();
}

class _CollapsibleFilterPanelState extends State<CollapsibleFilterPanel>
    with SingleTickerProviderStateMixin {
  bool _expanded = false;

  void _toggle() {
    setState(() => _expanded = !_expanded);
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final hasBadge = widget.badgeCount > 0;
    final isCompact = widget.dense;
    final headerPad = widget.headerPadding ??
        EdgeInsets.symmetric(horizontal: isCompact ? 10 : 14, vertical: isCompact ? 6 : 10);

    return Card(
      margin: EdgeInsets.zero,
      elevation: 0,
      shape: RoundedRectangleBorder(
        side: BorderSide(color: theme.dividerColor),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          InkWell(
            onTap: _toggle,
            borderRadius: BorderRadius.circular(8),
            child: Padding(
              padding: headerPad,
              child: Row(
                children: [
                  Icon(widget.icon, size: isCompact ? 18 : 20),
                  const SizedBox(width: 8),
                  Text(
                    widget.title,
                    style: TextStyle(
                      fontSize: isCompact ? 13 : 14,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                  if (hasBadge) ...[
                    const SizedBox(width: 8),
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 1),
                      decoration: BoxDecoration(
                        color: theme.colorScheme.primary,
                        borderRadius: BorderRadius.circular(8),
                      ),
                      child: Text(
                        '${widget.badgeCount}',
                        style: const TextStyle(fontSize: 10, color: Colors.white),
                      ),
                    ),
                  ],
                  const Spacer(),
                  AnimatedRotation(
                    turns: _expanded ? 0.5 : 0.0,
                    duration: const Duration(milliseconds: 200),
                    child: Icon(Icons.expand_more, size: isCompact ? 18 : 20),
                  ),
                ],
              ),
            ),
          ),
          AnimatedSize(
            duration: const Duration(milliseconds: 220),
            curve: Curves.easeInOut,
            child: _expanded
                ? Padding(
                    padding: widget.padding ??
                        EdgeInsets.fromLTRB(
                          isCompact ? 10 : 14,
                          0,
                          isCompact ? 10 : 14,
                          isCompact ? 10 : 14,
                        ),
                    child: widget.child,
                  )
                : const SizedBox.shrink(),
          ),
        ],
      ),
    );
  }
}
