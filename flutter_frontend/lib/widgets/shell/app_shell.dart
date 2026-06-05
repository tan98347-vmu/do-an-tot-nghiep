// Tệp này dùng để: đóng gói khối giao diện hoặc hành vi lặp lại trong flutter_frontend/lib/widgets/shell/app_shell.dart.
// Cách hoạt động: được gọi từ lớp phía trên, xử lý dữ liệu theo vai trò hiện có và trả kết quả về cho luồng gọi.
// Vai trò trong hệ thống: Đây là widget tái sử dụng của Flutter.
// Tác dụng khi hệ thống vận hành: giúp các màn hình dùng lại cùng một cách hiển thị hoặc tương tác.

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../l10n/app_strings.dart';
import '../../providers/auth_provider.dart';
import '../../providers/sharing_provider.dart';
import '../../providers/signing_summary_provider.dart';
import '../tasks/task_inbox_button.dart';
import '../../providers/notification_center_provider.dart';
import 'aggregate_notification_button.dart';
import 'global_search_bar.dart';

// Mục đích: Widget `AppShell` triển khai phần việc `App Shell` trong flutter_frontend/lib/widgets/shell/app_shell.dart.
// Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
// Vai trò trong hệ thống: Đây là widget thuộc widget tái sử dụng của Flutter.
// Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

class AppShell extends ConsumerWidget {
  final Widget child;
  const AppShell({super.key, required this.child});

  @override
  // Mục đích: Phương thức `build` triển khai phần việc `build` trong flutter_frontend/lib/widgets/shell/app_shell.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc widget tái sử dụng của Flutter.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  Widget build(BuildContext context, WidgetRef ref) {
    // Lắng nghe provider để widget tự động dựng lại khi dữ liệu hoặc trạng thái thay đổi.

    final user = ref.watch(currentUserProvider);
    final AsyncValue<dynamic> signingSummaryAsync =
        ref.watch(signingSummaryProvider);
    final AsyncValue<int> sharingPendingAsync = user?.canApprovePending == true
        ? ref.watch(sharingPendingCountProvider)
        : const AsyncData(0);
    final isWide = MediaQuery.of(context).size.width >= 1000;
    final isCompact = MediaQuery.of(context).size.width < 600;
    final nav = _AppNav(
      user: user,
      signingSummaryAsync: signingSummaryAsync,
      sharingPendingAsync: sharingPendingAsync,
    );
    final appBar = AppBar(
      actions: [
        // Tren mobile (compact + drawer): van bay GlobalSearchBar trong app bar
        // vi sidebar dang drawer. Tren wide screen: search + icon nam o sidebar.
        if (isCompact) ...[
          const GlobalSearchBar(),
          const TaskInboxButton(),
          const AggregateNotificationButton(),
          IconButton(
            icon: const Icon(Icons.person_outline),
            onPressed: () => context.go('/profile'),
          ),
        ],
      ],
    );

    if (isWide) {
      // Dựng khung màn hình chính để chứa app bar, body, action và các vùng giao diện khác.

      return Scaffold(
        backgroundColor: const Color(0xFFF8FAFC),
        body: Row(
          children: [
            // Sidebar nav with subtle drop shadow on the right edge.
            Container(
              width: 280,
              decoration: const BoxDecoration(
                boxShadow: [
                  BoxShadow(
                    color: Color(0x1A0F172A),
                    blurRadius: 18,
                    offset: Offset(2, 0),
                  ),
                ],
              ),
              child: nav,
            ),
            Expanded(child: child),
          ],
        ),
      );
    }
    // Dựng khung màn hình chính để chứa app bar, body, action và các vùng giao diện khác.

    return Scaffold(
      drawer: Drawer(child: nav),
      appBar: appBar,
      body: child,
    );
  }
}

// Mục đích: Lớp `_PendingCountBadge` triển khai phần việc `Pending Count Badge` trong flutter_frontend/lib/widgets/shell/app_shell.dart.
// Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
// Vai trò trong hệ thống: Đây là lớp thuộc widget tái sử dụng của Flutter.
// Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

class _PendingCountBadge extends StatelessWidget {
  final int count;
  final int templates;
  final int documents;
  final bool loading;
  final String? tooltipMessage;

  const _PendingCountBadge({
    required this.count,
    required this.templates,
    required this.documents,
    required this.loading,
    this.tooltipMessage,
  });

  @override
  // Mục đích: Phương thức `build` triển khai phần việc `build` trong flutter_frontend/lib/widgets/shell/app_shell.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc widget tái sử dụng của Flutter.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  Widget build(BuildContext context) {
    final strings = AppStrings.of(context);
    if (loading) {
      return const SizedBox(
        width: 16,
        height: 16,
        child: CircularProgressIndicator(
          strokeWidth: 2,
          valueColor: AlwaysStoppedAnimation<Color>(Color(0xFF60A5FA)),
        ),
      );
    }

    final hasItems = count > 0;
    final label = count > 99 ? '99+' : '$count';

    return Tooltip(
      message: tooltipMessage ??
          strings.pick(
            'Chờ duyệt: $templates mẫu văn bản, $documents văn bản',
            'Pending approvals: $templates templates, $documents documents',
          ),
      waitDuration: const Duration(milliseconds: 250),
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 180),
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
        decoration: BoxDecoration(
          color: hasItems ? const Color(0xFFDC2626) : Colors.white10,
          borderRadius: BorderRadius.circular(999),
          border: Border.all(
            color: hasItems ? const Color(0xFFEF4444) : Colors.white12,
          ),
        ),
        child: Text(
          label,
          style: TextStyle(
            fontSize: 11,
            fontWeight: FontWeight.w800,
            color: hasItems ? Colors.white : Colors.white54,
          ),
        ),
      ),
    );
  }
}

// Mục đích: Lớp `_AppNav` triển khai phần việc `App Nav` trong flutter_frontend/lib/widgets/shell/app_shell.dart.
// Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
// Vai trò trong hệ thống: Đây là lớp thuộc widget tái sử dụng của Flutter.
// Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

class _AppNav extends ConsumerWidget {
  final dynamic user;
  final AsyncValue<dynamic> signingSummaryAsync;
  final AsyncValue<int> sharingPendingAsync;

  const _AppNav({
    this.user,
    required this.signingSummaryAsync,
    required this.sharingPendingAsync,
  });

  @override
  // Mục đích: Phương thức `build` triển khai phần việc `build` trong flutter_frontend/lib/widgets/shell/app_shell.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc widget tái sử dụng của Flutter.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  Widget build(BuildContext context, WidgetRef ref) {
    final strings = AppStrings.of(context);
    final loc = GoRouterState.of(context).matchedLocation;
    final groupParam =
        GoRouterState.of(context).uri.queryParameters['group'] ?? '';
    final canAccessCompanyAdminArea = user?.canAccessAdminArea == true;

    final templateActive = loc.startsWith('/templates');
    final docActive = loc.startsWith('/documents');
    final promptActive = loc.startsWith('/prompts');
    final digitalSignActive = loc.startsWith('/signing') ||
        loc.startsWith('/signing/proposals') ||
        loc.startsWith('/signed-pdfs') ||
        loc.startsWith('/mailbox');
    final signingSummary = signingSummaryAsync.asData?.value;
    // Số CHƯA ĐỌC mỗi mục (đã trừ mốc "đã đọc"); badge nav hiển thị theo đây.
    final notifUnreadMap = ref.watch(notificationUnreadByCategoryProvider);
    final notifCurrentMap = ref.watch(notificationCurrentCountsProvider);

    // ── Nav item thông thường ──────────────────────────────────────────────
    // Mục đích: Phương thức `navTile` triển khai phần việc `nav Tile` trong flutter_frontend/lib/widgets/shell/app_shell.dart.
    // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
    // Vai trò trong hệ thống: Đây là phương thức thuộc widget tái sử dụng của Flutter.
    // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

    Widget navTile(
      String label,
      IconData icon,
      String route, {
      String? query,
      double indent = 0,
      Widget? trailing,
    }) {
      if (route == '/chat/voice') {
        return const SizedBox.shrink();
      }
      final autoTrailing = route == '/signing/tasks'
              ? _PendingCountBadge(
                  count: notifUnreadMap[kNotifSigningTasks] ?? 0,
                  templates: signingSummary?.tasksAvailable ?? 0,
                  documents: signingSummary?.tasksBlocked ?? 0,
                  loading:
                      signingSummaryAsync.isLoading && signingSummary == null,
                  tooltipMessage: strings.pick(
                    'Yêu cầu ký: ${signingSummary?.tasksAvailable ?? 0} cần ký, ${signingSummary?.tasksBlocked ?? 0} đang chờ bước trước',
                    'Signing requests: ${signingSummary?.tasksAvailable ?? 0} ready, ${signingSummary?.tasksBlocked ?? 0} waiting for previous steps',
                  ),
                )
              : route == '/signing/proposals/review'
                  ? _PendingCountBadge(
                      count: notifUnreadMap[kNotifSigningProposals] ?? 0,
                      templates: signingSummary?.hrPendingProposals ?? 0,
                      documents: 0,
                      loading: signingSummaryAsync.isLoading &&
                          signingSummary == null,
                      tooltipMessage: strings.pick(
                        'Đề xuất ký: ${signingSummary?.hrPendingProposals ?? 0} mục đang chờ duyệt',
                        'Signing proposals: ${signingSummary?.hrPendingProposals ?? 0} items are waiting for review',
                      ),
                    )
                  : route == '/mailbox'
                      ? _PendingCountBadge(
                          count: notifUnreadMap[kNotifMailbox] ?? 0,
                          templates: signingSummary?.mailboxPendingThreads ?? 0,
                          documents: signingSummary?.mailboxPendingEntries ?? 0,
                          loading: signingSummaryAsync.isLoading &&
                              signingSummary == null,
                          tooltipMessage: strings.pick(
                            'Hòm thư: ${signingSummary?.mailboxPendingThreads ?? 0} thread cần xử lý, ${signingSummary?.mailboxPendingEntries ?? 0} entry của bạn đang chờ',
                            'Mailbox: ${signingSummary?.mailboxPendingThreads ?? 0} threads need attention, ${signingSummary?.mailboxPendingEntries ?? 0} of your entries are waiting',
                          ),
                        )
                      : route == '/sharing/pending'
                          ? _PendingCountBadge(
                              count: notifUnreadMap[kNotifShareApprovals] ?? 0,
                              templates:
                                  sharingPendingAsync.asData?.value ?? 0,
                              documents: 0,
                              loading: sharingPendingAsync.isLoading &&
                                  sharingPendingAsync.asData == null,
                              tooltipMessage: strings.pick(
                                'Chia sẻ chờ duyệt: ${sharingPendingAsync.asData?.value ?? 0} yêu cầu đang chờ bạn duyệt',
                                'Share approvals: ${sharingPendingAsync.asData?.value ?? 0} requests waiting for your review',
                              ),
                            )
                          : null;
      final trailingWidget = trailing ?? autoTrailing;
      final target = query != null ? '$route?group=$query' : route;
      final resolvedLabel = route == '/chat' ? 'Chat AI' : label;
      final bool active;
      if (query != null) {
        active = loc.startsWith(route) && groupParam == query;
      } else if (route == '/chat') {
        active = loc == route || loc.startsWith('/chat/');
      } else {
        // Highlight khi đang ở route con (vd /ai-doc/123 → highlight /ai-doc)
        active = loc == route ||
            (route.length > 1 &&
                loc.startsWith('$route/') &&
                route != '/templates' &&
                route != '/documents' &&
                route != '/prompts');
      }

      return Padding(
        padding: EdgeInsets.only(left: 6 + indent, right: 6, top: 1, bottom: 1),
        child: Material(
          color: active
              ? Colors.white.withValues(alpha: 0.15)
              : Colors.transparent,
          borderRadius: BorderRadius.circular(8),
          child: InkWell(
            borderRadius: BorderRadius.circular(8),
            // Điều hướng người dùng sang màn phù hợp theo kết quả thao tác hiện tại.

            onTap: () {
              // Mở màn của một mục thông báo = đánh dấu mục đó "đã đọc".
              final cat = notifCategoryForRoute(route);
              if (cat != null) {
                ref
                    .read(notificationAckProvider.notifier)
                    .markRead(cat, notifCurrentMap[cat] ?? 0);
              }
              context.go(target);
            },
            hoverColor: Colors.white.withValues(alpha: 0.08),
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
              child: Row(
                children: [
                  Icon(icon,
                      size: 17, color: active ? Colors.white : Colors.white54),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Text(
                      resolvedLabel,
                      style: TextStyle(
                        fontSize: 13,
                        fontWeight:
                            active ? FontWeight.w700 : FontWeight.normal,
                        color: active ? Colors.white : Colors.white70,
                      ),
                    ),
                  ),
                  if (trailingWidget != null) ...[
                    trailingWidget,
                    const SizedBox(width: 8),
                  ],
                  if (active)
                    Container(
                      width: 4,
                      height: 4,
                      decoration: const BoxDecoration(
                        color: Color(0xFF60A5FA),
                        shape: BoxShape.circle,
                      ),
                    ),
                ],
              ),
            ),
          ),
        ),
      );
    }

    // ── Nhãn phân vùng ─────────────────────────────────────────────────────
    // Mục đích: Phương thức `sectionLabel` triển khai phần việc `section Label` trong flutter_frontend/lib/widgets/shell/app_shell.dart.
    // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
    // Vai trò trong hệ thống: Đây là phương thức thuộc widget tái sử dụng của Flutter.
    // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

    Widget sectionLabel(String text) => Padding(
          padding: const EdgeInsets.only(left: 16, top: 14, bottom: 2),
          child: Text(text.toUpperCase(),
              style: const TextStyle(
                  color: Colors.white30,
                  fontSize: 9.5,
                  letterSpacing: 1.3,
                  fontWeight: FontWeight.w700)),
        );

    Widget userFooter({required bool showNotifications}) => Container(
          padding: const EdgeInsets.fromLTRB(12, 10, 8, 10),
          decoration: const BoxDecoration(
            border: Border(top: BorderSide(color: Colors.white12)),
            color: Color(0xFF0A0F1E),
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Row(
                children: [
                  CircleAvatar(
                    radius: 17,
                    backgroundColor: const Color(0xFF3B82F6),
                    child: Text(
                      (user.fullName.isNotEmpty
                              ? user.fullName[0]
                              : user.username[0])
                          .toUpperCase(),
                      style: const TextStyle(
                          color: Colors.white,
                          fontSize: 14,
                          fontWeight: FontWeight.bold),
                    ),
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Text(user.fullName,
                            style: const TextStyle(
                                color: Colors.white,
                                fontSize: 12,
                                fontWeight: FontWeight.w600),
                            overflow: TextOverflow.ellipsis),
                        Text(user.roleLabel,
                            style: const TextStyle(
                                color: Colors.white38, fontSize: 11)),
                      ],
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 8),
              // ── Action icons row (tasks · notifications · profile · logout)
              Theme(
                data: Theme.of(context).copyWith(
                  iconTheme: const IconThemeData(color: Colors.white70),
                ),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.spaceAround,
                  children: [
                    const TaskInboxButton(iconColor: Colors.white70),
                    const AggregateNotificationButton(
                      iconColor: Colors.white70,
                    ),
                    IconButton(
                      icon: const Icon(Icons.person_outline,
                          color: Colors.white70, size: 20),
                      tooltip: strings.pick('Hồ sơ cá nhân', 'Profile'),
                      onPressed: () => context.go('/profile'),
                      splashRadius: 18,
                    ),
                    IconButton(
                      icon: const Icon(Icons.logout,
                          color: Colors.white70, size: 20),
                      onPressed: () async {
                        final ok = await showDialog<bool>(
                          context: context,
                          builder: (ctx) => AlertDialog(
                            title: Text(strings.pick('Đăng xuất', 'Sign out')),
                            content: Text(strings.pick(
                              'Bạn có muốn đăng xuất khỏi hệ thống không?',
                              'Do you want to sign out of the system?',
                            )),
                            actions: [
                              TextButton(
                                onPressed: () => Navigator.pop(ctx, false),
                                child: Text(strings.pick('Hủy', 'Cancel')),
                              ),
                              FilledButton(
                                onPressed: () => Navigator.pop(ctx, true),
                                child:
                                    Text(strings.pick('Đăng xuất', 'Sign out')),
                              ),
                            ],
                          ),
                        );
                        if (ok == true) {
                          await ref.read(authProvider.notifier).logout();
                        }
                      },
                      tooltip: strings.pick('Đăng xuất', 'Sign out'),
                      splashRadius: 18,
                    ),
                  ],
                ),
              ),
            ],
          ),
        );

    // ── ExpansionTile nhóm ──────────────────────────────────────────────────
    // Mục đích: Phương thức `navGroup` triển khai phần việc `nav Group` trong flutter_frontend/lib/widgets/shell/app_shell.dart.
    // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
    // Vai trò trong hệ thống: Đây là phương thức thuộc widget tái sử dụng của Flutter.
    // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

    Widget navGroup({
      required String label,
      required IconData icon,
      required bool isExpanded,
      required String groupKey,
      required List<Widget> children,
      Widget? badge,
    }) {
      return Theme(
        data: Theme.of(context).copyWith(
          expansionTileTheme: ExpansionTileThemeData(
            iconColor: isExpanded ? Colors.white70 : Colors.white38,
            collapsedIconColor: Colors.white38,
            backgroundColor: Colors.transparent,
            collapsedBackgroundColor: Colors.transparent,
            tilePadding:
                const EdgeInsets.symmetric(horizontal: 12, vertical: 0),
            childrenPadding: EdgeInsets.zero,
            shape: const Border(),
            collapsedShape: const Border(),
          ),
        ),
        child: ExpansionTile(
          key: ValueKey('$groupKey-$isExpanded'),
          initiallyExpanded: isExpanded,
          leading: Icon(icon,
              size: 18, color: isExpanded ? Colors.white : Colors.white54),
          title: Row(
            children: [
              Expanded(
                child: Text(
                  label,
                  style: TextStyle(
                    fontSize: 13.5,
                    fontWeight:
                        isExpanded ? FontWeight.w700 : FontWeight.normal,
                    color: isExpanded ? Colors.white : Colors.white70,
                  ),
                ),
              ),
              if (badge != null) ...[
                badge,
                const SizedBox(width: 8),
              ],
            ],
          ),
          trailing: Icon(
            isExpanded ? Icons.expand_less : Icons.expand_more,
            size: 18,
            color: Colors.white38,
          ),
          children: children,
        ),
      );
    }

    // Badge nhóm "Ký số" = tổng số CHƯA ĐỌC của các mục con (đã trừ mốc đã đọc),
    // để khi đánh dấu đã đọc một mục con thì badge nhóm cũng giảm theo.
    final signingGroupBadge = _PendingCountBadge(
      count: (notifUnreadMap[kNotifSigningTasks] ?? 0) +
          (notifUnreadMap[kNotifSigningProposals] ?? 0) +
          (notifUnreadMap[kNotifMailbox] ?? 0),
      templates: signingSummary?.tasksAvailable ?? 0,
      documents: signingSummary?.mailboxPendingThreads ?? 0,
      loading: signingSummaryAsync.isLoading && signingSummary == null,
      tooltipMessage: strings.pick(
        'Ký số: ${signingSummary?.tasksAvailable ?? 0} cần ký, ${signingSummary?.hrPendingProposals ?? 0} đề xuất chờ duyệt, ${signingSummary?.mailboxPendingThreads ?? 0} thread hòm thư đang chờ',
        'Digital signing: ${signingSummary?.tasksAvailable ?? 0} tasks ready, ${signingSummary?.hrPendingProposals ?? 0} proposals to review, ${signingSummary?.mailboxPendingThreads ?? 0} mailbox threads pending',
      ),
    );

    return Material(
      color: const Color(0xFF0F172A),
      child: Column(
        children: [
          // ── Header ─────────────────────────────────────────────────────
          Container(
            padding: const EdgeInsets.fromLTRB(18, 20, 14, 14),
            decoration: const BoxDecoration(
              gradient: LinearGradient(
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
                colors: [Color(0xFF0F172A), Color(0xFF1E293B)],
              ),
              border: Border(bottom: BorderSide(color: Colors.white12)),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                // Global search bar — always shown in sidebar nav
                Theme(
                  data: Theme.of(context).copyWith(
                    iconTheme: const IconThemeData(color: Colors.white70),
                  ),
                  child: const GlobalSearchBar(),
                ),
              ],
            ),
          ),

          // ── Danh sách điều hướng ────────────────────────────────────────
          Expanded(
            child: ListView(
              padding: const EdgeInsets.symmetric(vertical: 8),
              children: [
                navTile(strings.pick('Bảng điều khiển', 'Dashboard'),
                    Icons.dashboard_outlined, '/dashboard'),

                sectionLabel(strings.pick('Văn bản', 'Documents')),
                navTile(
                    strings.pick(
                        'Sinh văn bản từ mẫu', 'Generate from templates'),
                    Icons.auto_awesome,
                    '/ai-doc'),
                navTile(strings.pick('Tom tat van ban', 'Document summaries'),
                    Icons.summarize_outlined, '/summaries'),
                navTile(strings.pick('Hỏi đáp văn bản', 'Document Q&A'),
                    Icons.chat_bubble_outline, '/rag'),
                navTile(strings.pick('Trợ lý AI', 'AI Assistant'),
                    Icons.smart_toy_outlined, '/chat'),
                navTile(strings.pick('Giọng nói AI', 'AI Voice'),
                    Icons.mic_none_outlined, '/chat/voice'),

                sectionLabel(strings.pick('Ký số', 'Digital signing')),
                navGroup(
                  label: strings.pick('Ký số', 'Digital signing'),
                  icon: Icons.workspace_premium_outlined,
                  isExpanded: digitalSignActive,
                  groupKey: 'digital-sign',
                  badge: signingGroupBadge,
                  children: [
                    navTile(strings.pick('Yêu cầu ký', 'Signing requests'),
                        Icons.draw_outlined, '/signing/tasks',
                        indent: 12),
                    if (signingSummary?.canReviewProposals ?? false)
                      navTile(
                          strings.pick('Duyá»‡t Ä‘á» xuáº¥t kÃ½',
                              'Review signing proposals'),
                          Icons.rule_folder_outlined,
                          '/signing/proposals/review',
                          indent: 12),
                    navTile(strings.pick('PDF đã ký', 'Signed PDFs'),
                        Icons.picture_as_pdf_outlined, '/signed-pdfs',
                        indent: 12),
                    navTile(strings.pick('Hòm thư', 'Mailbox'),
                        Icons.forward_to_inbox_outlined, '/mailbox',
                        indent: 12),
                    if ((signingSummaryAsync
                                .asData?.value?.canManageHrDelegations ??
                            false) ||
                        (signingSummaryAsync.asData?.value
                                ?.canManageAccountingDelegations ??
                            false))
                      navTile(
                          strings.pick('Ủy quyền ký số', 'Signing delegation'),
                          Icons.how_to_reg_outlined,
                          '/signing/access',
                          indent: 12),
                    const SizedBox(height: 4),
                  ],
                ),

                const SizedBox(height: 6),

                // ── Mẫu văn bản (ExpansionTile) ──────────────────────────
                navGroup(
                  label: strings.pick('Mẫu văn bản', 'Templates'),
                  icon: Icons.description_outlined,
                  isExpanded: templateActive,
                  groupKey: 'templates',
                  children: [
                    navTile(strings.pick('Tạo mẫu văn bản', 'Create template'),
                        Icons.add_circle_outline, '/templates/create',
                        indent: 12),
                    navTile(strings.pick('Mẫu dùng chung', 'Shared templates'),
                        Icons.public_outlined, '/templates',
                        query: 'system', indent: 12),
                    navTile(
                        strings.pick(
                            'Mẫu phòng ban của tôi', 'My department templates'),
                        Icons.group_outlined,
                        '/templates',
                        query: 'team',
                        indent: 12),
                    navTile(
                        strings.pick('Riêng của tôi', 'My private templates'),
                        Icons.lock_outline,
                        '/templates',
                        query: 'private',
                        indent: 12),
                    navTile(strings.pick('Yêu thích', 'Favorites'),
                        Icons.star_outline, '/templates',
                        query: 'favorite', indent: 12),
                    navTile(
                        strings.pick('Mẫu chia sẻ cho đồng nghiệp',
                            'Templates shared with me'),
                        Icons.people_alt_outlined,
                        '/templates',
                        query: 'peer',
                        indent: 12),
                    if (canAccessCompanyAdminArea)
                      navTile(strings.pick('Tất cả (Admin)', 'All (Admin)'),
                          Icons.admin_panel_settings_outlined, '/templates',
                          query: 'admin', indent: 12),
                    const SizedBox(height: 4),
                  ],
                ),

                const SizedBox(height: 2),

                // ── Quản lý văn bản (ExpansionTile) ──────────────────────
                navGroup(
                  label: strings.pick('Quản lý văn bản', 'Document management'),
                  icon: Icons.folder_outlined,
                  isExpanded: docActive,
                  groupKey: 'documents',
                  children: [
                    navTile(strings.pick('Văn bản của tôi', 'My documents'),
                        Icons.person_outline, '/documents',
                        query: 'private', indent: 12),
                    navTile(
                        strings.pick(
                            'Đã chia sẻ trong nhóm', 'Shared in my groups'),
                        Icons.group_outlined,
                        '/documents',
                        query: 'group',
                        indent: 12),
                    navTile(
                        strings.pick('Đã chia sẻ công khai', 'Publicly shared'),
                        Icons.public_outlined,
                        '/documents',
                        query: 'public',
                        indent: 12),
                    navTile(strings.pick('Yêu thích', 'Favorites'),
                        Icons.star_outline, '/documents',
                        query: 'favorite', indent: 12),
                    navTile(
                        strings.pick('Văn bản chia sẻ cho đồng nghiệp',
                            'Documents shared with me'),
                        Icons.people_alt_outlined,
                        '/documents',
                        query: 'peer',
                        indent: 12),
                    navTile(strings.pick('Đã lưu trữ', 'Archived'),
                        Icons.archive_outlined, '/documents',
                        query: 'archived', indent: 12),
                    if (canAccessCompanyAdminArea)
                      navTile(strings.pick('Tất cả (Admin)', 'All (Admin)'),
                          Icons.admin_panel_settings_outlined, '/documents',
                          query: 'admin', indent: 12),
                    const SizedBox(height: 4),
                  ],
                ),

                const SizedBox(height: 2),

                // ── Quản lý Prompt (ExpansionTile) ────────────────────────
                navGroup(
                  label: strings.pick('Quản lý Prompt', 'Prompt management'),
                  icon: Icons.bolt_outlined,
                  isExpanded: promptActive,
                  groupKey: 'prompts',
                  children: [
                    navTile(strings.pick('Tạo prompt mới', 'Create prompt'),
                        Icons.add_circle_outline, '/prompts/new',
                        indent: 12),
                    navTile(strings.pick('Tất cả của tôi', 'All accessible'),
                        Icons.list_alt_outlined, '/prompts',
                        indent: 12),
                    navTile(strings.pick('Prompt riêng tư', 'My private'),
                        Icons.lock_outline, '/prompts',
                        query: 'private', indent: 12),
                    navTile(
                        strings.pick('Prompt phòng ban', 'Department prompts'),
                        Icons.group_outlined,
                        '/prompts',
                        query: 'group',
                        indent: 12),
                    navTile(strings.pick('Prompt dùng chung', 'Public prompts'),
                        Icons.public_outlined, '/prompts',
                        query: 'public', indent: 12),
                    navTile(
                        strings.pick('Prompt chia sẻ cho đồng nghiệp',
                            'Prompts shared with me'),
                        Icons.people_alt_outlined,
                        '/prompts',
                        query: 'peer',
                        indent: 12),
                    if (canAccessCompanyAdminArea)
                      navTile(strings.pick('Tất cả (Admin)', 'All (Admin)'),
                          Icons.admin_panel_settings_outlined, '/prompts',
                          query: 'admin', indent: 12),
                    const SizedBox(height: 4),
                  ],
                ),

                sectionLabel(strings.pick('Hệ thống', 'System')),
                navTile(strings.pick('Thùng rác', 'Trash'),
                    Icons.delete_outline, '/trash'),
                navTile(strings.pick('Hồ sơ cá nhân', 'Profile'),
                    Icons.manage_accounts_outlined, '/profile'),

                if (user?.canApprovePending == true) ...[
                  sectionLabel(strings.pick('Phê duyệt', 'Approvals')),
                  navTile(
                    strings.pick('Chia sẻ chờ duyệt', 'Share approvals'),
                    Icons.share_outlined,
                    '/sharing/pending',
                  ),
                ],

                if (canAccessCompanyAdminArea) ...[
                  sectionLabel(strings.pick('Quản trị', 'Administration')),
                  navTile(strings.pick('Cấu hình AI', 'AI settings'),
                      Icons.psychology_outlined, '/admin/ai-config'),
                  navTile(strings.accountsAndDepartments,
                      Icons.admin_panel_settings_outlined, '/admin'),
                  navTile(strings.pick('Sao lưu dữ liệu', 'Data backup'),
                      Icons.cloud_download_outlined, '/admin/backups'),
                ],
              ],
            ),
          ),

          // ── Thông tin người dùng ────────────────────────────────────────
          if (user != null) userFooter(showNotifications: false),
        ],
      ),
    );
  }
}
