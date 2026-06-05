import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../l10n/app_strings.dart';
import '../../models/notification_item.dart';
import '../../providers/auth_provider.dart';
import '../../providers/notification_center_provider.dart';
import '../../providers/notifications_provider.dart';
import '../../providers/signing_summary_provider.dart';

class AggregateNotificationButton extends ConsumerWidget {
  final Color? iconColor;

  const AggregateNotificationButton({super.key, this.iconColor});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final strings = AppStrings.of(context);
    final user = ref.watch(currentUserProvider);
    if (user == null) {
      return IconButton(
        icon: Icon(Icons.notifications_none_outlined, color: iconColor),
        onPressed: null,
      );
    }

    final unreadCountAsync = ref.watch(unreadNotificationCountProvider);
    // Tổng = thông báo sự kiện (backend) + việc cần xử lý đang chờ (4 hàng đợi).
    final queueUnread = ref.watch(notificationTotalUnreadProvider);
    final count = (unreadCountAsync.asData?.value ?? 0) + queueUnread;
    return Stack(
      clipBehavior: Clip.none,
      children: [
        IconButton(
          tooltip: strings.pick('Thong bao tong', 'All notifications'),
          icon: Icon(Icons.notifications_none_outlined, color: iconColor),
          onPressed: () => _openNotificationsDialog(context, ref),
        ),
        if (count > 0)
          Positioned(
            right: 7,
            top: 7,
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 5, vertical: 2),
              decoration: BoxDecoration(
                color: Colors.red,
                borderRadius: BorderRadius.circular(999),
              ),
              child: Text(
                count > 99 ? '99+' : '$count',
                style: const TextStyle(
                  color: Colors.white,
                  fontSize: 10,
                  fontWeight: FontWeight.w700,
                ),
              ),
            ),
          ),
      ],
    );
  }

  IconData _queueIcon(String key) => switch (key) {
        kNotifShareApprovals => Icons.share_outlined,
        kNotifSigningTasks => Icons.edit_document,
        kNotifSigningProposals => Icons.how_to_reg_outlined,
        kNotifMailbox => Icons.mail_outline,
        _ => Icons.notifications_none,
      };

  /// Mục "Việc cần xử lý" (4 hàng đợi) hiển thị phía trên danh sách thông báo sự kiện.
  /// Chỉ hiện các mục đang có việc mới; có nút "đã đọc" và bấm để mở màn tương ứng.
  Widget _buildQueueSection(
    BuildContext context,
    WidgetRef ref,
    BuildContext dialogCtx,
  ) {
    final current = ref.watch(notificationCurrentCountsProvider);
    final unread = ref.watch(notificationUnreadByCategoryProvider);
    final visible =
        kNotifCategories.where((k) => (unread[k] ?? 0) > 0).toList();
    if (visible.isEmpty) return const SizedBox.shrink();
    return Container(
      color: const Color(0xFFFFFBEB),
      padding: const EdgeInsets.only(bottom: 4),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Padding(
            padding: EdgeInsets.fromLTRB(16, 8, 12, 2),
            child: Text(
              'Việc cần xử lý',
              style: TextStyle(fontWeight: FontWeight.w700, fontSize: 13),
            ),
          ),
          for (final key in visible)
            ListTile(
              dense: true,
              visualDensity: VisualDensity.compact,
              leading: Icon(_queueIcon(key), size: 20, color: Colors.deepOrange),
              title: Text(notifCategoryLabel(key)),
              subtitle: Text('${unread[key]} mục mới cần xử lý'),
              trailing: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Container(
                    padding:
                        const EdgeInsets.symmetric(horizontal: 7, vertical: 2),
                    decoration: BoxDecoration(
                      color: Colors.red,
                      borderRadius: BorderRadius.circular(10),
                    ),
                    child: Text(
                      '${unread[key]}',
                      style: const TextStyle(
                          color: Colors.white,
                          fontSize: 11,
                          fontWeight: FontWeight.bold),
                    ),
                  ),
                  IconButton(
                    tooltip: 'Đánh dấu đã đọc',
                    icon: const Icon(Icons.done_all, size: 18),
                    onPressed: () => ref
                        .read(notificationAckProvider.notifier)
                        .markRead(key, current[key] ?? 0),
                  ),
                ],
              ),
              onTap: () {
                ref
                    .read(notificationAckProvider.notifier)
                    .markRead(key, current[key] ?? 0);
                Navigator.pop(dialogCtx);
                context.go(notifCategoryRoute(key));
              },
            ),
          const Divider(height: 1),
        ],
      ),
    );
  }

  Future<void> _openNotificationsDialog(
    BuildContext context,
    WidgetRef ref,
  ) async {
    ref.invalidate(notificationsProvider);
    await showDialog<void>(
      context: context,
      builder: (ctx) => Dialog(
        child: SizedBox(
          width: 560,
          height: MediaQuery.of(ctx).size.height * 0.76,
          child: Consumer(
            builder: (context, ref, _) {
              final strings = AppStrings.of(context);
              final notificationsAsync = ref.watch(notificationsProvider);
              return Column(
                children: [
                  Padding(
                    padding: const EdgeInsets.fromLTRB(18, 16, 12, 8),
                    child: Row(
                      children: [
                        Expanded(
                          child: Text(
                            strings.pick(
                              'Thong bao tong',
                              'All notifications',
                            ),
                            style: const TextStyle(
                              fontSize: 18,
                              fontWeight: FontWeight.w700,
                            ),
                          ),
                        ),
                        TextButton.icon(
                          onPressed: () async {
                            // Đánh dấu đã đọc cả thông báo sự kiện (backend) lẫn
                            // các hàng đợi việc cần xử lý (mốc last-seen client).
                            ref
                                .read(notificationAckProvider.notifier)
                                .markAllRead(
                                    ref.read(notificationCurrentCountsProvider));
                            await markAllAggregateNotificationsRead();
                            ref.invalidate(notificationsProvider);
                            ref.invalidate(unreadNotificationCountProvider);
                            ref.invalidate(signingSummaryProvider);
                          },
                          icon: const Icon(Icons.done_all, size: 18),
                          label: Text(
                            strings.pick('Da xem tat ca', 'Mark all read'),
                          ),
                        ),
                        IconButton(
                          onPressed: () => Navigator.pop(ctx),
                          icon: const Icon(Icons.close),
                        ),
                      ],
                    ),
                  ),
                  const Divider(height: 1),
                  _buildQueueSection(context, ref, ctx),
                  Expanded(
                    child: notificationsAsync.when(
                      loading: () =>
                          const Center(child: CircularProgressIndicator()),
                      error: (error, _) => Center(
                        child: Text(
                          strings.pick(
                            'Khong tai duoc thong bao: $error',
                            'Could not load notifications: $error',
                          ),
                        ),
                      ),
                      data: (items) {
                        if (items.isEmpty) {
                          return Center(
                            child: Text(
                              strings.pick(
                                'Chua co thong bao nao.',
                                'There are no notifications yet.',
                              ),
                            ),
                          );
                        }
                        return ListView.separated(
                          padding: const EdgeInsets.all(12),
                          itemCount: items.length,
                          separatorBuilder: (_, __) =>
                              const SizedBox(height: 8),
                          itemBuilder: (context, index) {
                            final item = items[index];
                            return _NotificationCard(
                              item: item,
                              onMarkRead:
                                  item.supportsRead && item.countsAsUnread
                                      ? () async {
                                          await markAggregateNotificationRead(
                                            item.sourceType,
                                            item.sourceId,
                                          );
                                          ref.invalidate(notificationsProvider);
                                          ref.invalidate(
                                              unreadNotificationCountProvider);
                                          ref.invalidate(signingSummaryProvider);
                                        }
                                      : null,
                              onPressed: () async {
                                if (item.supportsRead) {
                                  await markAggregateNotificationRead(
                                    item.sourceType,
                                    item.sourceId,
                                  );
                                }
                                ref.invalidate(notificationsProvider);
                                ref.invalidate(unreadNotificationCountProvider);
                                ref.invalidate(signingSummaryProvider);
                                if (context.mounted) {
                                  Navigator.pop(ctx);
                                  context.go(item.deeplink);
                                }
                              },
                            );
                          },
                        );
                      },
                    ),
                  ),
                ],
              );
            },
          ),
        ),
      ),
    );
  }
}

class _NotificationCard extends StatelessWidget {
  final AggregateNotificationItem item;
  final VoidCallback onPressed;
  final Future<void> Function()? onMarkRead;

  const _NotificationCard({
    required this.item,
    required this.onPressed,
    this.onMarkRead,
  });

  @override
  Widget build(BuildContext context) {
    final palette = _paletteFor(item);
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: item.highlight
            ? palette.background
            : Colors.grey.shade50,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(
          color: item.highlight ? palette.border : Colors.grey.shade300,
        ),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(palette.icon, color: palette.color, size: 20),
          const SizedBox(width: 10),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Expanded(
                      child: Text(
                        item.title,
                        style: const TextStyle(fontWeight: FontWeight.w700),
                        maxLines: 2,
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                    if (item.countsAsUnread)
                      Container(
                        margin: const EdgeInsets.only(left: 8),
                        padding: const EdgeInsets.symmetric(
                          horizontal: 8,
                          vertical: 3,
                        ),
                        decoration: BoxDecoration(
                          color: palette.color.withValues(alpha: 0.12),
                          borderRadius: BorderRadius.circular(999),
                        ),
                        child: Text(
                          'Moi',
                          style: TextStyle(
                            color: palette.color,
                            fontSize: 11,
                            fontWeight: FontWeight.w700,
                          ),
                        ),
                      ),
                  ],
                ),
                const SizedBox(height: 4),
                Text(
                  item.summary,
                  style: TextStyle(
                    color: palette.color,
                    fontWeight: FontWeight.w600,
                  ),
                ),
                if (item.reason.trim().isNotEmpty) ...[
                  const SizedBox(height: 6),
                  Container(
                    width: double.infinity,
                    padding: const EdgeInsets.all(8),
                    decoration: BoxDecoration(
                      color: Colors.white,
                      borderRadius: BorderRadius.circular(8),
                      border: Border.all(color: palette.border),
                    ),
                    child: Text(
                      item.reason,
                      style: const TextStyle(fontSize: 12.5),
                    ),
                  ),
                ],
                const SizedBox(height: 8),
                Row(
                  children: [
                    Expanded(
                      child: Text(
                        item.displayTime,
                        style: TextStyle(
                          fontSize: 12,
                          color: Colors.grey.shade600,
                        ),
                      ),
                    ),
                    if (onMarkRead != null)
                      TextButton.icon(
                        onPressed: () => onMarkRead!.call(),
                        icon: const Icon(Icons.check, size: 16),
                        label: const Text('Đã xem'),
                      ),
                    TextButton.icon(
                      onPressed: onPressed,
                      icon: const Icon(Icons.arrow_forward, size: 16),
                      label: Text(item.actionLabel),
                    ),
                  ],
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  _NotificationPalette _paletteFor(AggregateNotificationItem item) {
    if (item.status == 'reject' || item.status == 'rejected' || item.status == 'failed') {
      return const _NotificationPalette(
        color: Colors.red,
        background: Color(0xFFFFF1F2),
        border: Color(0xFFFDA4AF),
        icon: Icons.cancel_outlined,
      );
    }
    if (item.category.contains('signing') || item.category == 'mailbox') {
      return const _NotificationPalette(
        color: Colors.blue,
        background: Color(0xFFEFF6FF),
        border: Color(0xFF93C5FD),
        icon: Icons.workspace_premium_outlined,
      );
    }
    if (item.category == 'approval') {
      return const _NotificationPalette(
        color: Colors.deepOrange,
        background: Color(0xFFFFF7ED),
        border: Color(0xFFFDBA74),
        icon: Icons.pending_actions_outlined,
      );
    }
    if (item.category == 'ai_task') {
      return const _NotificationPalette(
        color: Colors.purple,
        background: Color(0xFFFAF5FF),
        border: Color(0xFFD8B4FE),
        icon: Icons.smart_toy_outlined,
      );
    }
    return const _NotificationPalette(
      color: Colors.green,
      background: Color(0xFFF0FDF4),
      border: Color(0xFF86EFAC),
      icon: Icons.notifications_active_outlined,
    );
  }
}

class _NotificationPalette {
  final Color color;
  final Color background;
  final Color border;
  final IconData icon;

  const _NotificationPalette({
    required this.color,
    required this.background,
    required this.border,
    required this.icon,
  });
}
