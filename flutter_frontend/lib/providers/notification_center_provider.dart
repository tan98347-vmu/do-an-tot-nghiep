// Trung tâm thông báo (client-side) cho các badge "cần xử lý":
//   - Chia sẻ chờ duyệt, Yêu cầu ký, Đề xuất ký, Hòm thư ký số.
//
// Cơ chế "đã đọc" theo MỐC ĐÃ XEM (last-seen): lưu một mốc số lượng (ack) cho
// mỗi mục trong SharedPreferences. Badge hiển thị = max(0, số hiện tại - ack).
// Bấm "đã đọc" (hoặc mở đúng màn của mục đó) -> ack = số hiện tại -> badge về 0.
// Khi có mục MỚI (số hiện tại tăng vượt ack) -> badge lại hiện phần chênh lệch.

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'sharing_provider.dart';
import 'signing_summary_provider.dart';

const String kNotifShareApprovals = 'share_approvals';
const String kNotifSigningTasks = 'signing_tasks';
const String kNotifSigningProposals = 'signing_proposals';
const String kNotifMailbox = 'mailbox';

const List<String> kNotifCategories = [
  kNotifShareApprovals,
  kNotifSigningTasks,
  kNotifSigningProposals,
  kNotifMailbox,
];

String notifCategoryLabel(String key) => switch (key) {
      kNotifShareApprovals => 'Chia sẻ chờ duyệt',
      kNotifSigningTasks => 'Yêu cầu ký',
      kNotifSigningProposals => 'Đề xuất ký',
      kNotifMailbox => 'Hòm thư ký số',
      _ => key,
    };

String notifCategoryRoute(String key) => switch (key) {
      kNotifShareApprovals => '/sharing/pending',
      kNotifSigningTasks => '/signing/tasks',
      kNotifSigningProposals => '/signing/proposals/review',
      kNotifMailbox => '/mailbox',
      _ => '/',
    };

/// Map route -> category (để app_shell tự đánh dấu đã đọc khi mở màn).
String? notifCategoryForRoute(String route) {
  for (final key in kNotifCategories) {
    if (notifCategoryRoute(key) == route) return key;
  }
  return null;
}

int notifUnread(int current, int ack) {
  final u = current - ack;
  return u < 0 ? 0 : u;
}

/// Số lượng hiện tại (raw) mỗi mục, lấy từ các provider đếm sẵn có.
final notificationCurrentCountsProvider = Provider<Map<String, int>>((ref) {
  final share = ref.watch(sharingPendingCountProvider).asData?.value ?? 0;
  final signing = ref.watch(signingSummaryProvider).asData?.value;
  int sv(dynamic v) => (v is int) ? v : 0;
  return {
    kNotifShareApprovals: share,
    kNotifSigningTasks: sv(signing?.tasksAvailable),
    kNotifSigningProposals: sv(signing?.hrPendingProposals),
    kNotifMailbox: sv(signing?.mailboxPendingThreads),
  };
});

/// Mốc đã xem (ack) mỗi mục, lưu bền trong SharedPreferences.
class NotificationAckNotifier extends Notifier<Map<String, int>> {
  static const _prefix = 'notif_ack_';
  SharedPreferences? _prefs;

  @override
  Map<String, int> build() {
    _load();
    return {for (final k in kNotifCategories) k: 0};
  }

  Future<void> _load() async {
    _prefs = await SharedPreferences.getInstance();
    state = {
      for (final k in kNotifCategories) k: _prefs!.getInt('$_prefix$k') ?? 0,
    };
  }

  Future<void> markRead(String category, int currentCount) async {
    _prefs ??= await SharedPreferences.getInstance();
    await _prefs!.setInt('$_prefix$category', currentCount);
    state = {...state, category: currentCount};
  }

  Future<void> markAllRead(Map<String, int> currentCounts) async {
    _prefs ??= await SharedPreferences.getInstance();
    final Map<String, int> next = {...state};
    for (final entry in currentCounts.entries) {
      await _prefs!.setInt('$_prefix${entry.key}', entry.value);
      next[entry.key] = entry.value;
    }
    state = next;
  }
}

final notificationAckProvider =
    NotifierProvider<NotificationAckNotifier, Map<String, int>>(
  NotificationAckNotifier.new,
);

/// Số "chưa đọc" mỗi mục = max(0, hiện tại - ack).
final notificationUnreadByCategoryProvider = Provider<Map<String, int>>((ref) {
  final current = ref.watch(notificationCurrentCountsProvider);
  final ack = ref.watch(notificationAckProvider);
  return {
    for (final k in kNotifCategories)
      k: notifUnread(current[k] ?? 0, ack[k] ?? 0),
  };
});

/// Tổng số chưa đọc của tất cả mục cần xử lý.
final notificationTotalUnreadProvider = Provider<int>((ref) {
  final unread = ref.watch(notificationUnreadByCategoryProvider);
  return unread.values.fold<int>(0, (sum, v) => sum + v);
});
