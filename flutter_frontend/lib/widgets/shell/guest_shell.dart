// Tệp này dùng để: đóng gói khối giao diện hoặc hành vi lặp lại trong flutter_frontend/lib/widgets/shell/guest_shell.dart.
// Cách hoạt động: được gọi từ lớp phía trên, xử lý dữ liệu theo vai trò hiện có và trả kết quả về cho luồng gọi.
// Vai trò trong hệ thống: Đây là widget tái sử dụng của Flutter.
// Tác dụng khi hệ thống vận hành: giúp các màn hình dùng lại cùng một cách hiển thị hoặc tương tác.
// ignore_for_file: avoid_web_libraries_in_flutter, uri_does_not_exist

import 'dart:async';
import 'dart:html' as html;
import 'dart:js_util' as js_util;

import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../core/api_client.dart';
import '../../l10n/app_strings.dart';

// Mục đích: Widget `GuestShell` triển khai phần việc `Guest Shell` trong flutter_frontend/lib/widgets/shell/guest_shell.dart.
// Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
// Vai trò trong hệ thống: Đây là widget thuộc widget tái sử dụng của Flutter.
// Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

class GuestShell extends StatefulWidget {
  final Widget child;

  const GuestShell({super.key, required this.child});

  @override
  State<GuestShell> createState() => _GuestShellState();
}

// Mục đích: Widget `_GuestShellState` triển khai phần việc `Guest Shell State` trong flutter_frontend/lib/widgets/shell/guest_shell.dart.
// Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
// Vai trò trong hệ thống: Đây là widget thuộc widget tái sử dụng của Flutter.
// Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

class _GuestShellState extends State<GuestShell> {
  String? _username;
  bool _hasDocument = false;
  bool _cleanedUp = false;
  bool _loadingSession = false;
  String _lastRoute = '';
  StreamSubscription<html.Event>? _unloadSub;

  @override
  // Mục đích: Phương thức `initState` triển khai phần việc `init State` trong flutter_frontend/lib/widgets/shell/guest_shell.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc widget tái sử dụng của Flutter.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  void initState() {
    super.initState();
    _loadSessionInfo();
    _unloadSub = html.window.onUnload.listen((_) => _cleanupWithBeacon());
  }

  @override
  // Mục đích: Phương thức `dispose` triển khai phần việc `dispose` trong flutter_frontend/lib/widgets/shell/guest_shell.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc widget tái sử dụng của Flutter.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  void dispose() {
    _unloadSub?.cancel();
    _cleanupSession();
    super.dispose();
  }

  // Mục đích: Phương thức `_loadSessionInfo` triển khai phần việc `load Session Info` trong flutter_frontend/lib/widgets/shell/guest_shell.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc widget tái sử dụng của Flutter.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  Future<void> _loadSessionInfo() async {
    if (_loadingSession) return;
    _loadingSession = true;
    try {
      // Gọi API hoặc tác vụ bất đồng bộ rồi chờ kết quả trước khi cập nhật giao diện.

      final resp = await ApiClient().dio.get('guest/session/');
      if (!mounted) return;
      // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

      setState(() {
        _username = resp.data['username'] as String?;
        _hasDocument = resp.data['has_document'] == true;
      });
    } catch (_) {
      if (!mounted) return;
      // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

      setState(() {
        _username ??= 'temp_guest';
        _hasDocument = false;
      });
    } finally {
      _loadingSession = false;
    }
  }

  // Mục đích: Phương thức `_cleanupSession` triển khai phần việc `cleanup Session` trong flutter_frontend/lib/widgets/shell/guest_shell.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc widget tái sử dụng của Flutter.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  Future<void> _cleanupSession() async {
    if (_cleanedUp) return;
    _cleanedUp = true;
    try {
      // Gọi API hoặc tác vụ bất đồng bộ rồi chờ kết quả trước khi cập nhật giao diện.

      await ApiClient().dio.post('guest/session/cleanup/');
    } catch (_) {}
  }

  // Mục đích: Phương thức `_cleanupWithBeacon` triển khai phần việc `cleanup With Beacon` trong flutter_frontend/lib/widgets/shell/guest_shell.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc widget tái sử dụng của Flutter.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  void _cleanupWithBeacon() {
    if (_cleanedUp) return;
    _cleanedUp = true;
    final url = '${Uri.base.origin}/api/guest/session/cleanup/';
    try {
      if (js_util.hasProperty(html.window.navigator, 'sendBeacon')) {
        js_util.callMethod(html.window.navigator, 'sendBeacon', [url, '1']);
      }
    } catch (_) {}
  }

  // Mục đích: Phương thức `_showLockedMessage` triển khai phần việc `show Locked Message` trong flutter_frontend/lib/widgets/shell/guest_shell.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc widget tái sử dụng của Flutter.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  void _showLockedMessage() {
    final strings = AppStrings.of(context);
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(
          strings.pick('Cần đăng nhập mới sử dụng được', 'Sign in to use this feature'),
        ),
        backgroundColor: Colors.orange,
      ),
    );
  }

  // Mục đích: Phương thức `_goLogin` triển khai phần việc `go Login` trong flutter_frontend/lib/widgets/shell/guest_shell.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc widget tái sử dụng của Flutter.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  Future<void> _goLogin() async {
    await _cleanupSession();
    if (!mounted) return;
    // Điều hướng người dùng sang màn phù hợp theo kết quả thao tác hiện tại.

    context.go('/login');
  }

  @override
  // Mục đích: Phương thức `build` triển khai phần việc `build` trong flutter_frontend/lib/widgets/shell/guest_shell.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc widget tái sử dụng của Flutter.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  Widget build(BuildContext context) {
    final strings = AppStrings.of(context);
    final loc = GoRouterState.of(context).matchedLocation;
    if (_lastRoute != loc) {
      _lastRoute = loc;
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (mounted) _loadSessionInfo();
      });
    }

    final isWide = MediaQuery.of(context).size.width >= 1000;
    final nav = _GuestNav(
      username: _username ?? 'temp_guest',
      hasDocument: _hasDocument,
      onLockedTap: _showLockedMessage,
      onLoginTap: _goLogin,
    );

    if (isWide) {
      // Dựng khung màn hình chính để chứa app bar, body, action và các vùng giao diện khác.

      return Scaffold(
        body: Row(
          children: [
            SizedBox(width: 268, child: nav),
            Expanded(child: widget.child),
          ],
        ),
      );
    }

    // Dựng khung màn hình chính để chứa app bar, body, action và các vùng giao diện khác.

    return Scaffold(
      drawer: Drawer(child: nav),
      appBar: AppBar(
        actions: [
          TextButton.icon(
            onPressed: _goLogin,
            icon: const Icon(Icons.login, size: 18),
            label: Text(strings.pick('Đăng nhập', 'Sign in')),
          ),
        ],
      ),
      body: widget.child,
    );
  }
}

// Mục đích: Lớp `_GuestNav` triển khai phần việc `Guest Nav` trong flutter_frontend/lib/widgets/shell/guest_shell.dart.
// Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
// Vai trò trong hệ thống: Đây là lớp thuộc widget tái sử dụng của Flutter.
// Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

class _GuestNav extends StatelessWidget {
  final String username;
  final bool hasDocument;
  final VoidCallback onLockedTap;
  final VoidCallback onLoginTap;

  const _GuestNav({
    required this.username,
    required this.hasDocument,
    required this.onLockedTap,
    required this.onLoginTap,
  });

  @override
  // Mục đích: Phương thức `build` triển khai phần việc `build` trong flutter_frontend/lib/widgets/shell/guest_shell.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc widget tái sử dụng của Flutter.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  Widget build(BuildContext context) {
    final strings = AppStrings.of(context);
    final loc = GoRouterState.of(context).matchedLocation;

    // Mục đích: Phương thức `sectionLabel` triển khai phần việc `section Label` trong flutter_frontend/lib/widgets/shell/guest_shell.dart.
    // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
    // Vai trò trong hệ thống: Đây là phương thức thuộc widget tái sử dụng của Flutter.
    // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

    Widget sectionLabel(String text) => Padding(
          padding: const EdgeInsets.only(left: 16, top: 14, bottom: 2),
          child: Text(
            text.toUpperCase(),
            style: const TextStyle(
              color: Colors.white30,
              fontSize: 9.5,
              letterSpacing: 1.3,
              fontWeight: FontWeight.w700,
            ),
          ),
        );

    // Mục đích: Phương thức `navTile` triển khai phần việc `nav Tile` trong flutter_frontend/lib/widgets/shell/guest_shell.dart.
    // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
    // Vai trò trong hệ thống: Đây là phương thức thuộc widget tái sử dụng của Flutter.
    // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

    Widget navTile({
      required String label,
      required IconData icon,
      String? route,
      bool locked = false,
      double indent = 0,
    }) {
      final active = route != null && (loc == route || loc.startsWith('$route/'));
      return Padding(
        padding: EdgeInsets.only(left: 6 + indent, right: 6, top: 1, bottom: 1),
        child: Material(
          color: active ? Colors.white.withOpacity(0.15) : Colors.transparent,
          borderRadius: BorderRadius.circular(8),
          child: InkWell(
            borderRadius: BorderRadius.circular(8),
            onTap: locked
                ? onLockedTap
                : route == null
                    ? null
                    // Điều hướng người dùng sang màn phù hợp theo kết quả thao tác hiện tại.

                    : () => context.go(route),
            hoverColor: Colors.white.withOpacity(0.08),
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
              child: Row(
                children: [
                  Icon(
                    icon,
                    size: 17,
                    color: active ? Colors.white : Colors.white70,
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Text(
                      label,
                      style: TextStyle(
                        fontSize: 13,
                        fontWeight: active ? FontWeight.w700 : FontWeight.normal,
                        color: active ? Colors.white : Colors.white70,
                      ),
                    ),
                  ),
                  if (locked)
                    const Icon(Icons.lock_outline, size: 15, color: Colors.white38)
                  else if (active)
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

    // Mục đích: Phương thức `navGroup` triển khai phần việc `nav Group` trong flutter_frontend/lib/widgets/shell/guest_shell.dart.
    // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
    // Vai trò trong hệ thống: Đây là phương thức thuộc widget tái sử dụng của Flutter.
    // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

    Widget navGroup({
      required String label,
      required IconData icon,
      required bool isExpanded,
      required String groupKey,
      required List<Widget> children,
    }) {
      return Theme(
        data: Theme.of(context).copyWith(
          expansionTileTheme: const ExpansionTileThemeData(
            iconColor: Colors.white38,
            collapsedIconColor: Colors.white38,
            backgroundColor: Colors.transparent,
            collapsedBackgroundColor: Colors.transparent,
            tilePadding: EdgeInsets.symmetric(horizontal: 12),
            childrenPadding: EdgeInsets.zero,
            shape: Border(),
            collapsedShape: Border(),
          ),
        ),
        child: ExpansionTile(
          key: ValueKey('$groupKey-$isExpanded'),
          initiallyExpanded: isExpanded,
          leading: Icon(
            icon,
            size: 18,
            color: isExpanded ? Colors.white : Colors.white54,
          ),
          title: Text(
            label,
            style: TextStyle(
              fontSize: 13.5,
              fontWeight: isExpanded ? FontWeight.w700 : FontWeight.normal,
              color: isExpanded ? Colors.white : Colors.white70,
            ),
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

    final templateActive = loc.startsWith('/guest/templates');
    final documentActive = loc.startsWith('/guest/document');

    return Material(
      color: const Color(0xFF0F172A),
      child: Column(
        children: [
          Container(
            padding: const EdgeInsets.fromLTRB(16, 20, 16, 16),
            decoration: const BoxDecoration(
              border: Border(bottom: BorderSide(color: Colors.white12)),
            ),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.end,
              children: [
                TextButton.icon(
                  onPressed: onLoginTap,
                  icon: const Icon(Icons.login, size: 16),
                  label: Text(strings.pick('Đăng nhập', 'Sign in')),
                  style: TextButton.styleFrom(
                    foregroundColor: const Color(0xFF93C5FD),
                  ),
                ),
              ],
            ),
          ),
          Expanded(
            child: ListView(
              padding: const EdgeInsets.symmetric(vertical: 8),
              children: [
                navTile(label: strings.dashboardTitle, icon: Icons.dashboard_outlined, locked: true),
                sectionLabel(strings.pick('Văn bản', 'Documents')),
                navTile(
                  label: strings.fromTemplate,
                  icon: Icons.auto_awesome,
                  route: '/guest',
                ),
                if (hasDocument)
                  navTile(
                    label: strings.pick('Văn bản vừa tạo', 'Latest generated document'),
                    icon: Icons.description_outlined,
                    route: '/guest/document',
                  ),
                navTile(
                  label: strings.documentQa,
                  icon: Icons.chat_bubble_outline,
                  locked: true,
                ),
                navTile(
                  label: strings.pick('Chat AI', 'AI Chat'),
                  icon: Icons.smart_toy_outlined,
                  locked: true,
                ),
                const SizedBox(height: 6),
                navGroup(
                  label: strings.pick('Quản lý mẫu văn bản', 'Template management'),
                  icon: Icons.description_outlined,
                  isExpanded: templateActive,
                  groupKey: 'guest-templates',
                  children: [
                    navTile(
                      label: strings.createTemplateTitle,
                      icon: Icons.add_circle_outline,
                      locked: true,
                      indent: 12,
                    ),
                    navTile(
                      label: strings.sharedTemplates,
                      icon: Icons.public_outlined,
                      locked: true,
                      indent: 12,
                    ),
                    navTile(
                      label: strings.pick('Mẫu phòng ban của tôi', 'My department templates'),
                      icon: Icons.group_outlined,
                      locked: true,
                      indent: 12,
                    ),
                    navTile(
                      label: strings.pick('Mẫu của tôi', 'My private templates'),
                      icon: Icons.lock_outline,
                      locked: true,
                      indent: 12,
                    ),
                    navTile(
                      label: strings.pick('Yêu thích', 'Favorites'),
                      icon: Icons.star_outline,
                      locked: true,
                      indent: 12,
                    ),
                  ],
                ),
                navGroup(
                  label: strings.pick('Quản lý văn bản', 'Document management'),
                  icon: Icons.folder_outlined,
                  isExpanded: documentActive,
                  groupKey: 'guest-documents',
                  children: [
                    navTile(
                      label: strings.pick('Văn bản của tôi', 'My documents'),
                      icon: Icons.person_outline,
                      locked: true,
                      indent: 12,
                    ),
                    navTile(
                      label: strings.pick('Đã chia sẻ trong nhóm', 'Shared in my groups'),
                      icon: Icons.group_outlined,
                      locked: true,
                      indent: 12,
                    ),
                    navTile(
                      label: strings.pick('Đã chia sẻ công khai', 'Publicly shared'),
                      icon: Icons.public_outlined,
                      locked: true,
                      indent: 12,
                    ),
                    navTile(
                      label: strings.pick('Yêu thích', 'Favorites'),
                      icon: Icons.star_outline,
                      locked: true,
                      indent: 12,
                    ),
                    navTile(
                      label: strings.pick('Đã lưu trữ', 'Archived'),
                      icon: Icons.archive_outlined,
                      locked: true,
                      indent: 12,
                    ),
                  ],
                ),
                sectionLabel(strings.pick('Hệ thống', 'System')),
                navTile(
                  label: strings.pick('Hồ sơ cá nhân', 'Profile'),
                  icon: Icons.manage_accounts_outlined,
                  locked: true,
                ),
                sectionLabel(strings.pick('Phê duyệt', 'Approvals')),
                navTile(
                  label: strings.approvalRequests,
                  icon: Icons.pending_actions_outlined,
                  locked: true,
                ),
                sectionLabel(strings.pick('Quản trị', 'Administration')),
                navTile(
                  label: strings.pick('Cấu hình AI', 'AI settings'),
                  icon: Icons.psychology_outlined,
                  locked: true,
                ),
                navTile(
                  label: strings.accountsAndDepartments,
                  icon: Icons.admin_panel_settings_outlined,
                  locked: true,
                ),
                navTile(
                  label: strings.pick('Sao lưu dữ liệu', 'Backups'),
                  icon: Icons.backup_outlined,
                  locked: true,
                ),
              ],
            ),
          ),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
            decoration: const BoxDecoration(
              border: Border(top: BorderSide(color: Colors.white12)),
              color: Color(0xFF0A0F1E),
            ),
            child: Row(
              children: [
                CircleAvatar(
                  radius: 17,
                  backgroundColor: const Color(0xFF3B82F6),
                  child: Text(
                    username.isNotEmpty ? username[0].toUpperCase() : 'T',
                    style: const TextStyle(
                      color: Colors.white,
                      fontSize: 14,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Text(
                        strings.pick('Khách tạm thời', 'Temporary guest'),
                        style: const TextStyle(
                          color: Colors.white,
                          fontSize: 12,
                          fontWeight: FontWeight.w600,
                        ),
                        overflow: TextOverflow.ellipsis,
                      ),
                      Text(
                        strings.pick('Chỉ lưu trong session hiện tại', 'Saved only for this session'),
                        style: const TextStyle(color: Colors.white38, fontSize: 11),
                      ),
                    ],
                  ),
                ),
                Text(
                  username,
                  style: const TextStyle(color: Colors.white54, fontSize: 11),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
