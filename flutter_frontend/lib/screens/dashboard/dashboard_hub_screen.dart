// Tệp này dùng để: dựng giao diện và orchestration UI trong flutter_frontend/lib/screens/dashboard/dashboard_hub_screen.dart.
// Cách hoạt động: nhận state từ provider, dựng widget, phản ứng sự kiện và gửi thao tác ngược về backend khi người dùng tương tác.
// Vai trò trong hệ thống: Đây là màn hình Flutter mà người dùng tương tác trực tiếp.
// Tác dụng khi hệ thống vận hành: biến nghiệp vụ backend thành trải nghiệm thao tác cụ thể trên web.

import 'dart:async';

import 'package:fl_chart/fl_chart.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:intl/intl.dart';

import '../../core/app_locale.dart';
import '../../l10n/app_strings.dart';
import '../../models/dashboard_stats.dart';
import '../../models/user.dart';
import '../../providers/auth_provider.dart';
import '../../providers/dashboard_provider.dart';
import 'organization_structure_graph_responsive.dart';
import 'system_architecture_graph_responsive.dart';

// Mục đích: Widget `DashboardScreen` triển khai phần việc `Dashboard Screen` trong flutter_frontend/lib/screens/dashboard/dashboard_hub_screen.dart.
// Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
// Vai trò trong hệ thống: Đây là widget thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
// Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

class DashboardScreen extends ConsumerStatefulWidget {
  const DashboardScreen({super.key});

  @override
  ConsumerState<DashboardScreen> createState() => _DashboardScreenState();
}

// Mục đích: Widget `_DashboardScreenState` triển khai phần việc `Dashboard Screen State` trong flutter_frontend/lib/screens/dashboard/dashboard_hub_screen.dart.
// Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
// Vai trò trong hệ thống: Đây là widget thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
// Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

class _DashboardScreenState extends ConsumerState<DashboardScreen> {
  Timer? _refreshTimer;

  @override
  // Mục đích: Phương thức `initState` triển khai phần việc `init State` trong flutter_frontend/lib/screens/dashboard/dashboard_hub_screen.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  void initState() {
    super.initState();
    _refreshTimer = Timer.periodic(const Duration(seconds: 30), (_) {
      ref.invalidate(dashboardStatsProvider);
    });
  }

  @override
  // Mục đích: Phương thức `dispose` triển khai phần việc `dispose` trong flutter_frontend/lib/screens/dashboard/dashboard_hub_screen.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  void dispose() {
    _refreshTimer?.cancel();
    super.dispose();
  }

  @override
  // Mục đích: Phương thức `build` triển khai phần việc `build` trong flutter_frontend/lib/screens/dashboard/dashboard_hub_screen.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  Widget build(BuildContext context) {
    // Lắng nghe provider để widget tự động dựng lại khi dữ liệu hoặc trạng thái thay đổi.

    final user = ref.watch(currentUserProvider);
    // Lắng nghe provider để widget tự động dựng lại khi dữ liệu hoặc trạng thái thay đổi.

    final statsAsync = ref.watch(dashboardStatsProvider);
    final isCompact = MediaQuery.sizeOf(context).width < 960;

    return RefreshIndicator(
      onRefresh: () => ref.refresh(dashboardStatsProvider.future),
      child: SingleChildScrollView(
        physics: const AlwaysScrollableScrollPhysics(),
        padding: EdgeInsets.fromLTRB(
            isCompact ? 16 : 28, 18, isCompact ? 16 : 28, 28),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            _DashboardToolbar(isCompact: isCompact),
            const SizedBox(height: 18),
            statsAsync.when(
              loading: () => const Padding(
                padding: EdgeInsets.symmetric(vertical: 120),
                child: Center(child: CircularProgressIndicator()),
              ),
              error: (error, _) => _DashboardError(
                error: error,
                onRetry: () => ref.refresh(dashboardStatsProvider),
              ),
              data: (stats) => _DashboardLoadedView(
                user: user,
                stats: stats,
                isCompact: isCompact,
              ),
            ),
            const SizedBox(height: 28),
            const _QuickActions(),
          ],
        ),
      ),
    );
  }
}

// Mục đích: Lớp `_DashboardToolbar` triển khai phần việc `Dashboard Toolbar` trong flutter_frontend/lib/screens/dashboard/dashboard_hub_screen.dart.
// Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
// Vai trò trong hệ thống: Đây là lớp thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
// Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

class _DashboardToolbar extends StatelessWidget {
  final bool isCompact;

  const _DashboardToolbar({required this.isCompact});

  @override
  // Mục đích: Phương thức `build` triển khai phần việc `build` trong flutter_frontend/lib/screens/dashboard/dashboard_hub_screen.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  Widget build(BuildContext context) {
    final strings = AppStrings.of(context);
    if (isCompact) {
      return Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            strings.pick('Bảng điều khiển', 'Dashboard'),
            style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                  fontWeight: FontWeight.w700,
                ),
          ),
          const SizedBox(height: 4),
          Text(
            strings.pick('Tổng quan hệ thống', 'System overview'),
            style: TextStyle(color: Colors.blueGrey.shade700),
          ),
          const SizedBox(height: 12),
          const _LocaleSwitcher(),
        ],
      );
    }

    return Row(
      children: [
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                strings.pick('Bảng điều khiển', 'Dashboard'),
                style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                      fontWeight: FontWeight.w700,
                    ),
              ),
              const SizedBox(height: 4),
              Text(
                strings.pick('Tổng quan hệ thống', 'System overview'),
                style: TextStyle(color: Colors.blueGrey.shade700),
              ),
            ],
          ),
        ),
        const SizedBox(width: 16),
        const _LocaleSwitcher(),
      ],
    );
  }
}

// Mục đích: Lớp `_LocaleSwitcher` triển khai phần việc `Locale Switcher` trong flutter_frontend/lib/screens/dashboard/dashboard_hub_screen.dart.
// Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
// Vai trò trong hệ thống: Đây là lớp thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
// Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

class _LocaleSwitcher extends ConsumerWidget {
  const _LocaleSwitcher();

  @override
  // Mục đích: Phương thức `build` triển khai phần việc `build` trong flutter_frontend/lib/screens/dashboard/dashboard_hub_screen.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  Widget build(BuildContext context, WidgetRef ref) {
    final strings = AppStrings.of(context);
    // Lắng nghe provider để widget tự động dựng lại khi dữ liệu hoặc trạng thái thay đổi.

    final locale = ref.watch(appLocaleProvider);

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: const Color(0xFFD9E2EC)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          const Icon(Icons.translate, size: 18, color: Color(0xFF1D4ED8)),
          const SizedBox(width: 8),
          Text(
            strings.language,
            style: const TextStyle(fontWeight: FontWeight.w600),
          ),
          const SizedBox(width: 10),
          SegmentedButton<String>(
            showSelectedIcon: false,
            segments: const [
              ButtonSegment<String>(value: 'vi', label: Text('VI')),
              ButtonSegment<String>(value: 'en', label: Text('EN')),
            ],
            selected: {locale.languageCode == 'en' ? 'en' : 'vi'},
            onSelectionChanged: (selection) {
              if (selection.isEmpty) return;
              // Đọc provider theo nhu cầu hành động mà không buộc widget đăng ký rebuild liên tục.

              ref
                  .read(appLocaleProvider.notifier)
                  .setLanguageCode(selection.first);
            },
          ),
        ],
      ),
    );
  }
}

// Mục đích: Lớp `_DashboardLoadedView` triển khai phần việc `Dashboard Loaded View` trong flutter_frontend/lib/screens/dashboard/dashboard_hub_screen.dart.
// Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
// Vai trò trong hệ thống: Đây là lớp thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
// Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

class _DashboardLoadedView extends StatelessWidget {
  final AppUser? user;
  final DashboardStats stats;
  final bool isCompact;

  const _DashboardLoadedView({
    required this.user,
    required this.stats,
    required this.isCompact,
  });

  @override
  // Mục đích: Phương thức `build` triển khai phần việc `build` trong flutter_frontend/lib/screens/dashboard/dashboard_hub_screen.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  Widget build(BuildContext context) {
    final strings = AppStrings.of(context);
    final metricCards = [
      _ScopeMetricCard(
        title: strings.ui('Mẫu Văn Bản'),
        total: stats.templateStructure.total,
        summary: stats.templateStructure.summary,
        icon: Icons.account_tree_outlined,
        accent: const Color(0xFF1D4ED8),
        items: stats.templateStructure.items,
      ),
      _ScopeMetricCard(
        title: strings.ui('Văn Bản'),
        total: stats.documentStructure.total,
        summary: stats.documentStructure.summary,
        icon: Icons.description_outlined,
        accent: const Color(0xFF0F766E),
        items: stats.documentStructure.items,
      ),
      _AiMetricCard(
        title: strings.ui('Phiên AI'),
        overview: stats.aiOverview,
        accent: const Color(0xFFBE123C),
      ),
      _ScopeMetricCard(
        title: strings.ui('VB Tháng Này'),
        total: stats.monthlyDocumentStructure.total,
        summary: stats.monthlyDocumentStructure.summary,
        icon: Icons.calendar_month_outlined,
        accent: const Color(0xFFB45309),
        items: stats.monthlyDocumentStructure.items,
      ),
    ];

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _DashboardHero(
          user: user,
          contextInfo: stats.orgContext,
        ),
        const SizedBox(height: 22),
        LayoutBuilder(
          builder: (context, constraints) {
            final cardWidth = isCompact
                ? constraints.maxWidth
                : (constraints.maxWidth - 18) / 2;
            return Wrap(
              spacing: 18,
              runSpacing: 18,
              children: metricCards
                  .map((card) => SizedBox(width: cardWidth, child: card))
                  .toList(),
            );
          },
        ),
        const SizedBox(height: 22),
        if (isCompact) ...[
          _ActivityBarCard(stats: stats),
          const SizedBox(height: 18),
          _ScopePieChartCard(
            title: strings.ui('Mẫu Theo Tầng Tổ Chức'),
            summary: stats.templateStructure.summary,
            items: stats.templateStructure.items,
          ),
          const SizedBox(height: 18),
          _ScopePieChartCard(
            title: strings.ui('Văn Bản Theo Tầng Tổ Chức'),
            summary: stats.documentStructure.summary,
            items: stats.documentStructure.items,
          ),
        ] else
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Expanded(
                flex: 6,
                child: _ActivityBarCard(stats: stats),
              ),
              const SizedBox(width: 18),
              Expanded(
                flex: 5,
                child: Column(
                  children: [
                    _ScopePieChartCard(
                      title: strings.ui('Mẫu Theo Tầng Tổ Chức'),
                      summary: stats.templateStructure.summary,
                      items: stats.templateStructure.items,
                    ),
                    const SizedBox(height: 18),
                    _ScopePieChartCard(
                      title: strings.ui('Văn Bản Theo Tầng Tổ Chức'),
                      summary: stats.documentStructure.summary,
                      items: stats.documentStructure.items,
                    ),
                  ],
                ),
              ),
            ],
          ),
        const SizedBox(height: 22),
        SystemArchitectureGraphResponsive(
            currentModel: stats.aiOverview.currentModel),
        const SizedBox(height: 22),
        OrganizationStructureGraphResponsive(
          structure: stats.orgStructure,
          viewer: user,
        ),
        const SizedBox(height: 22),
        if (isCompact) ...[
          _RecentCard(
            title: strings.ui('Mẫu Văn Bản Mới Cập Nhật'),
            route: '/templates',
            items: stats.recentTemplates,
          ),
          const SizedBox(height: 18),
          _RecentCard(
            title: strings.ui('Văn Bản Mới Cập Nhật'),
            route: '/documents',
            items: stats.recentDocuments,
          ),
        ] else
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Expanded(
                child: _RecentCard(
                  title: strings.ui('Mẫu Văn Bản Mới Cập Nhật'),
                  route: '/templates',
                  items: stats.recentTemplates,
                ),
              ),
              const SizedBox(width: 18),
              Expanded(
                child: _RecentCard(
                  title: strings.ui('Văn Bản Mới Cập Nhật'),
                  route: '/documents',
                  items: stats.recentDocuments,
                ),
              ),
            ],
          ),
      ],
    );
  }
}

// Mục đích: Lớp `_DashboardHero` triển khai phần việc `Dashboard Hero` trong flutter_frontend/lib/screens/dashboard/dashboard_hub_screen.dart.
// Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
// Vai trò trong hệ thống: Đây là lớp thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
// Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

class _DashboardHero extends StatelessWidget {
  final AppUser? user;
  final OrgContext contextInfo;

  const _DashboardHero({
    required this.user,
    required this.contextInfo,
  });

  @override
  // Mục đích: Phương thức `build` triển khai phần việc `build` trong flutter_frontend/lib/screens/dashboard/dashboard_hub_screen.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  Widget build(BuildContext context) {
    final strings = AppStrings.of(context);
    final groupNames = contextInfo.groupNames;
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(26),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(30),
        gradient: const LinearGradient(
          colors: [
            Color(0xFF0F172A),
            Color(0xFF1D4ED8),
            Color(0xFF0F766E),
          ],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        boxShadow: [
          BoxShadow(
            color: const Color(0xFF1D4ED8).withOpacity(0.24),
            blurRadius: 28,
            offset: const Offset(0, 14),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            strings.pick(
              'Dashboard theo cấu trúc tổ chức',
              'Dashboard by organization structure',
            ),
            style: GoogleFonts.spaceGrotesk(
              fontSize: 30,
              height: 1.1,
              fontWeight: FontWeight.w700,
              color: Colors.white,
            ),
          ),
          const SizedBox(height: 10),
          Text(
            strings.pick(
              'Xin chào ${user?.fullName ?? user?.username ?? ''}. Màn hình này tách rõ dữ liệu cá nhân, nhóm, riêng tư và toàn tổ chức để bạn đọc hệ thống theo đúng bối cảnh vận hành.',
              'Hello ${user?.fullName ?? user?.username ?? ''}. This screen separates personal, group, private, and organization-wide data so you can read the system in the right operating context.',
            ),
            style: TextStyle(
              color: Colors.white.withOpacity(0.78),
              height: 1.55,
            ),
          ),
          const SizedBox(height: 18),
          Wrap(
            spacing: 10,
            runSpacing: 10,
            children: [
              _HeroChip(
                icon: Icons.badge_outlined,
                label: contextInfo.roleLabel.isEmpty
                    ? strings.ui('Người dùng')
                    : strings.ui(contextInfo.roleLabel),
              ),
              if (contextInfo.groupCount > 0)
                _HeroChip(
                  icon: Icons.account_tree_outlined,
                  label: strings.pick(
                    '${contextInfo.groupCount} nhóm tham gia',
                    '${contextInfo.groupCount} joined groups',
                  ),
                ),
              if (contextInfo.leaderGroupCount > 0)
                _HeroChip(
                  icon: Icons.workspace_premium_outlined,
                  label: strings.pick(
                    'Dẫn dắt ${contextInfo.leaderGroupCount} nhóm',
                    'Leading ${contextInfo.leaderGroupCount} groups',
                  ),
                ),
              if (contextInfo.canApprovePending)
                _HeroChip(
                  icon: Icons.rule_folder_outlined,
                  label: strings.pick('Có quyền phê duyệt', 'Can approve'),
                ),
              ...groupNames.map((group) => _HeroChip(
                    icon: Icons.groups_2_outlined,
                    label: group,
                  )),
            ],
          ),
          const SizedBox(height: 14),
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(20),
              color: Colors.white.withOpacity(0.10),
              border: Border.all(color: Colors.white.withOpacity(0.10)),
            ),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Container(
                  width: 42,
                  height: 42,
                  decoration: BoxDecoration(
                    color: Colors.white.withOpacity(0.14),
                    borderRadius: BorderRadius.circular(14),
                  ),
                  child: const Icon(Icons.route_outlined, color: Colors.white),
                ),
                const SizedBox(width: 14),
                Expanded(
                  child: Text(
                    strings.ui(contextInfo.summary),
                    style: TextStyle(
                      color: Colors.white.withOpacity(0.84),
                      height: 1.5,
                    ),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

// Mục đích: Lớp `_HeroChip` triển khai phần việc `Hero Chip` trong flutter_frontend/lib/screens/dashboard/dashboard_hub_screen.dart.
// Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
// Vai trò trong hệ thống: Đây là lớp thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
// Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

class _HeroChip extends StatelessWidget {
  final IconData icon;
  final String label;

  const _HeroChip({
    required this.icon,
    required this.label,
  });

  @override
  // Mục đích: Phương thức `build` triển khai phần việc `build` trong flutter_frontend/lib/screens/dashboard/dashboard_hub_screen.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 9),
      decoration: BoxDecoration(
        color: Colors.white.withOpacity(0.12),
        borderRadius: BorderRadius.circular(999),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 16, color: Colors.white),
          const SizedBox(width: 8),
          Text(
            label,
            style: const TextStyle(
              color: Colors.white,
              fontWeight: FontWeight.w700,
            ),
          ),
        ],
      ),
    );
  }
}

// Mục đích: Lớp `_ScopeMetricCard` triển khai phần việc `Scope Metric Card` trong flutter_frontend/lib/screens/dashboard/dashboard_hub_screen.dart.
// Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
// Vai trò trong hệ thống: Đây là lớp thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
// Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

class _ScopeMetricCard extends StatelessWidget {
  final String title;
  final int total;
  final String summary;
  final IconData icon;
  final Color accent;
  final List<ScopeItem> items;

  const _ScopeMetricCard({
    required this.title,
    required this.total,
    required this.summary,
    required this.icon,
    required this.accent,
    required this.items,
  });

  @override
  // Mục đích: Phương thức `build` triển khai phần việc `build` trong flutter_frontend/lib/screens/dashboard/dashboard_hub_screen.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  Widget build(BuildContext context) {
    final strings = AppStrings.of(context);
    return Container(
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(28),
        color: Colors.white,
        border: Border.all(color: accent.withOpacity(0.18)),
        boxShadow: [
          BoxShadow(
            color: accent.withOpacity(0.08),
            blurRadius: 24,
            offset: const Offset(0, 10),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Container(
                width: 52,
                height: 52,
                decoration: BoxDecoration(
                  color: accent.withOpacity(0.10),
                  borderRadius: BorderRadius.circular(16),
                ),
                child: Icon(icon, color: accent),
              ),
              const SizedBox(width: 14),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      strings.ui(title),
                      style: GoogleFonts.spaceGrotesk(
                        fontSize: 24,
                        fontWeight: FontWeight.w700,
                        color: const Color(0xFF0F172A),
                      ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      '$total',
                      style: TextStyle(
                        fontSize: 34,
                        height: 1,
                        fontWeight: FontWeight.w800,
                        color: accent,
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          Text(
            strings.ui(summary),
            style: TextStyle(
              color: Colors.blueGrey.shade700,
              height: 1.5,
            ),
          ),
          const SizedBox(height: 16),
          ...items.map((item) => Padding(
                padding: const EdgeInsets.only(bottom: 10),
                child: _BreakdownRow(
                  accent: _scopeColor(item.key, accent),
                  label: strings.ui(item.label),
                  description: strings.ui(item.description),
                  count: item.count,
                ),
              )),
        ],
      ),
    );
  }
}

// Mục đích: Lớp `_AiMetricCard` triển khai phần việc `Ai Metric Card` trong flutter_frontend/lib/screens/dashboard/dashboard_hub_screen.dart.
// Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
// Vai trò trong hệ thống: Đây là lớp thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
// Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

class _AiMetricCard extends StatelessWidget {
  final String title;
  final AiOverview overview;
  final Color accent;

  const _AiMetricCard({
    required this.title,
    required this.overview,
    required this.accent,
  });

  @override
  // Mục đích: Phương thức `build` triển khai phần việc `build` trong flutter_frontend/lib/screens/dashboard/dashboard_hub_screen.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  Widget build(BuildContext context) {
    final strings = AppStrings.of(context);
    final rows = [
      (
        strings.pick('Phiên', 'Sessions'),
        strings.pick('Phiên AI của tài khoản', 'AI sessions for this account'),
        overview.sessions,
        Icons.chat_bubble_outline,
      ),
      (
        strings.pick('Tin nhắn', 'Messages'),
        strings.pick('Tổng tin nhắn đã lưu', 'Total stored messages'),
        overview.messages,
        Icons.forum_outlined,
      ),
      (
        strings.pick('Lượt gọi API', 'API calls'),
        strings.pick('Lần ghi log gọi model', 'Logged model call count'),
        overview.apiCalls,
        Icons.bolt_outlined,
      ),
    ];

    return Container(
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(28),
        color: const Color(0xFF111827),
        boxShadow: [
          BoxShadow(
            color: accent.withOpacity(0.18),
            blurRadius: 24,
            offset: const Offset(0, 12),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                width: 52,
                height: 52,
                decoration: BoxDecoration(
                  color: accent.withOpacity(0.14),
                  borderRadius: BorderRadius.circular(16),
                ),
                child: Icon(Icons.auto_awesome, color: accent),
              ),
              const SizedBox(width: 14),
              Expanded(
                child: Text(
                  strings.ui(title),
                  style: GoogleFonts.spaceGrotesk(
                    fontSize: 24,
                    fontWeight: FontWeight.w700,
                    color: Colors.white,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 14),
          Container(
            width: double.infinity,
            padding: const EdgeInsets.all(14),
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(20),
              color: Colors.white.withOpacity(0.05),
              border: Border.all(color: Colors.white.withOpacity(0.08)),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  strings.pick('Model hiện tại', 'Current model'),
                  style: TextStyle(
                    fontSize: 12,
                    fontWeight: FontWeight.w700,
                    color: Colors.white.withOpacity(0.66),
                  ),
                ),
                const SizedBox(height: 6),
                Text(
                  overview.currentModel.isEmpty
                      ? strings.pick('Chưa cấu hình', 'Not configured')
                      : overview.currentModel,
                  style: TextStyle(
                    fontSize: 20,
                    fontWeight: FontWeight.w800,
                    color: accent,
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 14),
          Text(
            strings.ui(overview.summary),
            style: TextStyle(
              color: Colors.white.withOpacity(0.72),
              height: 1.5,
            ),
          ),
          const SizedBox(height: 16),
          ...rows.map((row) => Padding(
                padding: const EdgeInsets.only(bottom: 12),
                child: Container(
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    borderRadius: BorderRadius.circular(18),
                    color: Colors.white.withOpacity(0.04),
                  ),
                  child: Row(
                    children: [
                      Icon(row.$4, color: accent, size: 20),
                      const SizedBox(width: 12),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              row.$1,
                              style: TextStyle(
                                fontSize: 12,
                                fontWeight: FontWeight.w700,
                                color: Colors.white.withOpacity(0.64),
                              ),
                            ),
                            const SizedBox(height: 2),
                            Text(
                              row.$2,
                              style: TextStyle(
                                color: Colors.white.withOpacity(0.84),
                              ),
                            ),
                          ],
                        ),
                      ),
                      Text(
                        '${row.$3}',
                        style: TextStyle(
                          fontSize: 24,
                          fontWeight: FontWeight.w800,
                          color: accent,
                        ),
                      ),
                    ],
                  ),
                ),
              )),
        ],
      ),
    );
  }
}

// Mục đích: Lớp `_BreakdownRow` triển khai phần việc `Breakdown Row` trong flutter_frontend/lib/screens/dashboard/dashboard_hub_screen.dart.
// Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
// Vai trò trong hệ thống: Đây là lớp thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
// Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

class _BreakdownRow extends StatelessWidget {
  final Color accent;
  final String label;
  final String description;
  final int count;

  const _BreakdownRow({
    required this.accent,
    required this.label,
    required this.description,
    required this.count,
  });

  @override
  // Mục đích: Phương thức `build` triển khai phần việc `build` trong flutter_frontend/lib/screens/dashboard/dashboard_hub_screen.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  Widget build(BuildContext context) {
    final strings = AppStrings.of(context);
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Container(
          width: 12,
          height: 12,
          margin: const EdgeInsets.only(top: 6),
          decoration: BoxDecoration(
            color: accent,
            shape: BoxShape.circle,
          ),
        ),
        const SizedBox(width: 10),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Expanded(
                    child: Text(
                      strings.ui(label),
                      style: const TextStyle(
                        fontWeight: FontWeight.w700,
                        color: Color(0xFF0F172A),
                      ),
                    ),
                  ),
                  Text(
                    '$count',
                    style: TextStyle(
                      fontWeight: FontWeight.w800,
                      color: accent,
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 4),
              Text(
                strings.ui(description),
                style: TextStyle(
                  fontSize: 12,
                  color: Colors.blueGrey.shade600,
                  height: 1.4,
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }
}

// Mục đích: Lớp `_ActivityBarCard` triển khai phần việc `Activity Bar Card` trong flutter_frontend/lib/screens/dashboard/dashboard_hub_screen.dart.
// Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
// Vai trò trong hệ thống: Đây là lớp thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
// Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

class _ActivityBarCard extends StatelessWidget {
  final DashboardStats stats;

  const _ActivityBarCard({required this.stats});

  @override
  // Mục đích: Phương thức `build` triển khai phần việc `build` trong flutter_frontend/lib/screens/dashboard/dashboard_hub_screen.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  Widget build(BuildContext context) {
    final strings = AppStrings.of(context);
    final data = stats.docsLast7Days;
    final maxRaw = data.map((day) => day.count).fold(0, mathMax);
    final maxY = (maxRaw + 2).toDouble();

    return Container(
      padding: const EdgeInsets.fromLTRB(18, 18, 18, 8),
      decoration: _panelDecoration(),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            strings.pick('Nhịp Hoạt Động 7 Ngày', '7-Day Activity'),
            style: GoogleFonts.spaceGrotesk(
              fontSize: 23,
              fontWeight: FontWeight.w700,
              color: const Color(0xFF0F172A),
            ),
          ),
          const SizedBox(height: 6),
          Text(
            strings.pick(
              'Số văn bản mà tài khoản hiện có thể nhìn thấy trong 7 ngày gần nhất. Đây là góc nhìn theo tổ chức, không chỉ đóng trong tài nguyên cá nhân.',
              'The number of documents this account can currently see over the last 7 days. This is an organization-level view, not only personal resources.',
            ),
            style: TextStyle(color: Colors.blueGrey.shade700, height: 1.5),
          ),
          const SizedBox(height: 18),
          SizedBox(
            height: 220,
            child: BarChart(
              BarChartData(
                maxY: maxY < 3 ? 5 : maxY,
                gridData: FlGridData(
                  show: true,
                  drawVerticalLine: false,
                  horizontalInterval: 1,
                  getDrawingHorizontalLine: (_) => FlLine(
                    color: const Color(0xFFE2E8F0),
                    strokeWidth: 1,
                  ),
                ),
                borderData: FlBorderData(show: false),
                titlesData: FlTitlesData(
                  topTitles: const AxisTitles(
                      sideTitles: SideTitles(showTitles: false)),
                  rightTitles: const AxisTitles(
                      sideTitles: SideTitles(showTitles: false)),
                  leftTitles: AxisTitles(
                    sideTitles: SideTitles(
                      showTitles: true,
                      interval: 1,
                      reservedSize: 28,
                      getTitlesWidget: (value, _) => Text(
                        value.toInt().toString(),
                        style: TextStyle(
                          fontSize: 10,
                          color: Colors.blueGrey.shade400,
                        ),
                      ),
                    ),
                  ),
                  bottomTitles: AxisTitles(
                    sideTitles: SideTitles(
                      showTitles: true,
                      getTitlesWidget: (value, _) {
                        final index = value.toInt();
                        if (index < 0 || index >= data.length) {
                          return const SizedBox.shrink();
                        }
                        final day = DateTime.tryParse(data[index].date);
                        return Padding(
                          padding: const EdgeInsets.only(top: 8),
                          child: Text(
                            day == null ? '' : DateFormat('dd/MM').format(day),
                            style: TextStyle(
                              fontSize: 10,
                              color: Colors.blueGrey.shade500,
                            ),
                          ),
                        );
                      },
                    ),
                  ),
                ),
                barGroups: List.generate(
                  data.length,
                  (index) => BarChartGroupData(
                    x: index,
                    barRods: [
                      BarChartRodData(
                        toY: data[index].count.toDouble(),
                        width: 18,
                        borderRadius: const BorderRadius.vertical(
                            top: Radius.circular(6)),
                        gradient: const LinearGradient(
                          colors: [Color(0xFF1D4ED8), Color(0xFF0F766E)],
                          begin: Alignment.bottomCenter,
                          end: Alignment.topCenter,
                        ),
                        backDrawRodData: BackgroundBarChartRodData(
                          show: true,
                          toY: maxY < 3 ? 5 : maxY,
                          color: const Color(0xFFEFF6FF),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

// Mục đích: Lớp `_ScopePieChartCard` triển khai phần việc `Scope Pie Chart Card` trong flutter_frontend/lib/screens/dashboard/dashboard_hub_screen.dart.
// Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
// Vai trò trong hệ thống: Đây là lớp thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
// Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

class _ScopePieChartCard extends StatelessWidget {
  final String title;
  final String summary;
  final List<ScopeItem> items;

  const _ScopePieChartCard({
    required this.title,
    required this.summary,
    required this.items,
  });

  @override
  // Mục đích: Phương thức `build` triển khai phần việc `build` trong flutter_frontend/lib/screens/dashboard/dashboard_hub_screen.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  Widget build(BuildContext context) {
    final strings = AppStrings.of(context);
    final total = items.fold<int>(0, (sum, item) => sum + item.count);
    return Container(
      padding: const EdgeInsets.all(18),
      decoration: _panelDecoration(),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            strings.ui(title),
            style: GoogleFonts.spaceGrotesk(
              fontSize: 23,
              fontWeight: FontWeight.w700,
              color: const Color(0xFF0F172A),
            ),
          ),
          const SizedBox(height: 6),
          Text(
            strings.ui(summary),
            style: TextStyle(color: Colors.blueGrey.shade700, height: 1.5),
          ),
          const SizedBox(height: 18),
          SizedBox(
            height: 220,
            child: total == 0
                ? Center(
                    child: Text(
                      strings.pick('Chưa có dữ liệu', 'No data yet'),
                      style: TextStyle(color: Colors.blueGrey.shade400),
                    ),
                  )
                : PieChart(
                    PieChartData(
                      centerSpaceRadius: 42,
                      sectionsSpace: 3,
                      sections: items.map((item) {
                        final color =
                            _scopeColor(item.key, const Color(0xFF1D4ED8));
                        final percent = total == 0
                            ? 0
                            : ((item.count / total) * 100).round();
                        return PieChartSectionData(
                          color: color,
                          value: item.count.toDouble(),
                          title: item.count == 0 ? '' : '$percent%',
                          radius: 54,
                          titleStyle: const TextStyle(
                            fontSize: 11,
                            fontWeight: FontWeight.w800,
                            color: Colors.white,
                          ),
                        );
                      }).toList(),
                    ),
                  ),
          ),
          const SizedBox(height: 14),
          ...items.map((item) => Padding(
                padding: const EdgeInsets.only(bottom: 10),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Container(
                      width: 12,
                      height: 12,
                      margin: const EdgeInsets.only(top: 4),
                      decoration: BoxDecoration(
                        color: _scopeColor(item.key, const Color(0xFF1D4ED8)),
                        shape: BoxShape.circle,
                      ),
                    ),
                    const SizedBox(width: 10),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            '${strings.ui(item.label)}: ${item.count}',
                            style: const TextStyle(
                              fontWeight: FontWeight.w700,
                              color: Color(0xFF0F172A),
                            ),
                          ),
                          const SizedBox(height: 3),
                          Text(
                            strings.ui(item.description),
                            style: TextStyle(
                              fontSize: 12,
                              color: Colors.blueGrey.shade600,
                              height: 1.4,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
              )),
        ],
      ),
    );
  }
}

// Mục đích: Lớp `_RecentCard` triển khai phần việc `Recent Card` trong flutter_frontend/lib/screens/dashboard/dashboard_hub_screen.dart.
// Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
// Vai trò trong hệ thống: Đây là lớp thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
// Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

class _RecentCard extends StatelessWidget {
  final String title;
  final String route;
  final List<RecentItem> items;

  const _RecentCard({
    required this.title,
    required this.route,
    required this.items,
  });

  @override
  // Mục đích: Phương thức `build` triển khai phần việc `build` trong flutter_frontend/lib/screens/dashboard/dashboard_hub_screen.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  Widget build(BuildContext context) {
    final strings = AppStrings.of(context);
    return Container(
      padding: const EdgeInsets.all(18),
      decoration: _panelDecoration(),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(
                child: Text(
                  strings.ui(title),
                  style: GoogleFonts.spaceGrotesk(
                    fontSize: 23,
                    fontWeight: FontWeight.w700,
                    color: const Color(0xFF0F172A),
                  ),
                ),
              ),
              TextButton(
                // Điều hướng người dùng sang màn phù hợp theo kết quả thao tác hiện tại.

                onPressed: () => context.go(route),
                child: Text(strings.ui('Xem tất cả')),
              ),
            ],
          ),
          const SizedBox(height: 12),
          if (items.isEmpty)
            Text(
              strings.pick(
                  'Chưa có dữ liệu cập nhật.', 'No recent updates yet.'),
              style: TextStyle(color: Colors.blueGrey.shade400),
            )
          else
            ...items.map((item) => _RecentRow(item: item)),
        ],
      ),
    );
  }
}

// Mục đích: Lớp `_RecentRow` triển khai phần việc `Recent Row` trong flutter_frontend/lib/screens/dashboard/dashboard_hub_screen.dart.
// Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
// Vai trò trong hệ thống: Đây là lớp thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
// Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

class _RecentRow extends StatelessWidget {
  final RecentItem item;

  const _RecentRow({required this.item});

  @override
  // Mục đích: Phương thức `build` triển khai phần việc `build` trong flutter_frontend/lib/screens/dashboard/dashboard_hub_screen.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  Widget build(BuildContext context) {
    final statusColor = switch (item.status) {
      'approved' || 'final' => const Color(0xFF15803D),
      'pending' => const Color(0xFFD97706),
      'rejected' => const Color(0xFFDC2626),
      'archived' => const Color(0xFF64748B),
      _ => const Color(0xFF2563EB),
    };

    final date = DateTime.tryParse(item.createdAt);
    final dateText = date == null ? '' : DateFormat('dd/MM/yyyy').format(date);

    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 7),
      child: Row(
        children: [
          Container(
            width: 11,
            height: 11,
            decoration: BoxDecoration(
              color: statusColor,
              shape: BoxShape.circle,
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Text(
              item.title,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: const TextStyle(
                fontWeight: FontWeight.w600,
                color: Color(0xFF0F172A),
              ),
            ),
          ),
          const SizedBox(width: 12),
          Text(
            dateText,
            style: TextStyle(
              fontSize: 12,
              color: Colors.blueGrey.shade500,
            ),
          ),
        ],
      ),
    );
  }
}

// Mục đích: Lớp `_DashboardError` triển khai phần việc `Dashboard Error` trong flutter_frontend/lib/screens/dashboard/dashboard_hub_screen.dart.
// Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
// Vai trò trong hệ thống: Đây là lớp thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
// Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

class _DashboardError extends StatelessWidget {
  final Object error;
  final VoidCallback onRetry;

  const _DashboardError({
    required this.error,
    required this.onRetry,
  });

  @override
  // Mục đích: Phương thức `build` triển khai phần việc `build` trong flutter_frontend/lib/screens/dashboard/dashboard_hub_screen.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  Widget build(BuildContext context) {
    final strings = AppStrings.of(context);
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(28),
      decoration: _panelDecoration(),
      child: Column(
        children: [
          const Icon(Icons.error_outline, size: 52, color: Color(0xFFDC2626)),
          const SizedBox(height: 14),
          Text(
            strings.pick(
                'Không tải được dashboard', 'Unable to load dashboard'),
            style: GoogleFonts.spaceGrotesk(
              fontSize: 24,
              fontWeight: FontWeight.w700,
            ),
          ),
          const SizedBox(height: 8),
          Text(
            '$error',
            textAlign: TextAlign.center,
            style: TextStyle(color: Colors.blueGrey.shade600),
          ),
          const SizedBox(height: 16),
          FilledButton.icon(
            onPressed: onRetry,
            icon: const Icon(Icons.refresh),
            label: Text(strings.ui('Thử lại')),
          ),
        ],
      ),
    );
  }
}

// Mục đích: Lớp `_QuickActions` triển khai phần việc `Quick Actions` trong flutter_frontend/lib/screens/dashboard/dashboard_hub_screen.dart.
// Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
// Vai trò trong hệ thống: Đây là lớp thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
// Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

class _QuickActions extends StatelessWidget {
  const _QuickActions();

  @override
  // Mục đích: Phương thức `build` triển khai phần việc `build` trong flutter_frontend/lib/screens/dashboard/dashboard_hub_screen.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  Widget build(BuildContext context) {
    final strings = AppStrings.of(context);
    final width = MediaQuery.sizeOf(context).width;
    final cardWidth = width < 900
        ? (((width - 52) / 2).clamp(160.0, 280.0) as num).toDouble()
        : 212.0;
    final actions = [
      (
        icon: Icons.auto_awesome,
        color: const Color(0xFF1D4ED8),
        title: strings.pick('Sinh văn bản từ mẫu', 'Generate from templates'),
        subtitle: strings.pick('Tạo văn bản từ mẫu và dữ liệu điền',
            'Create documents from templates and input data'),
        route: '/ai-doc',
      ),
      (
        icon: Icons.search,
        color: const Color(0xFF0F766E),
        title: strings.pick('Hỏi đáp văn bản', 'Document Q&A'),
        subtitle: strings.pick('Tra cứu mẫu và văn bản theo ngữ cảnh',
            'Search templates and documents by context'),
        route: '/rag',
      ),
      (
        icon: Icons.file_copy_outlined,
        color: const Color(0xFF4338CA),
        title: strings.pick('Quản lý mẫu', 'Template management'),
        subtitle: strings.pick('Mẫu dùng chung, phiên bản và phê duyệt',
            'Shared templates, versions, and approvals'),
        route: '/templates?group=system',
      ),
      (
        icon: Icons.description_outlined,
        color: const Color(0xFF15803D),
        title: strings.pick('Quản lý văn bản', 'Document management'),
        subtitle: strings.pick('Văn bản cá nhân, nhóm và toàn tổ chức',
            'Personal, group, and organization documents'),
        route: '/documents?group=private',
      ),
      (
        icon: Icons.chat_outlined,
        color: const Color(0xFFEA580C),
        title: strings.pick('Trợ lý AI', 'AI Assistant'),
        subtitle: strings.pick('Điều phối tool AI bằng giao diện chat',
            'Coordinate AI tools through chat'),
        route: '/chat',
      ),
      (
        icon: Icons.mic_none_outlined,
        color: const Color(0xFF7C3AED),
        title: strings.pick('Giọng nói AI', 'AI Voice'),
        subtitle: strings.pick(
            'Tương tác realtime bằng giọng nói', 'Realtime voice interaction'),
        route: '/chat/voice',
      ),
      (
        icon: Icons.person_outline,
        color: const Color(0xFF0F766E),
        title: strings.pick('Hồ sơ cá nhân', 'Profile'),
        subtitle: strings.pick('Cập nhật thông tin để AI điền mẫu',
            'Keep profile data ready for template filling'),
        route: '/profile',
      ),
    ];

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          strings.pick('Truy cập nhanh', 'Quick access'),
          style: GoogleFonts.spaceGrotesk(
            fontSize: 24,
            fontWeight: FontWeight.w700,
            color: const Color(0xFF0F172A),
          ),
        ),
        const SizedBox(height: 12),
        Wrap(
          spacing: 14,
          runSpacing: 14,
          children: actions
              .map((action) => SizedBox(
                    width: cardWidth,
                    child: InkWell(
                      borderRadius: BorderRadius.circular(24),
                      // Điều hướng người dùng sang màn phù hợp theo kết quả thao tác hiện tại.

                      onTap: () => context.go(action.route),
                      child: Container(
                        padding: const EdgeInsets.all(16),
                        decoration: _panelDecoration().copyWith(
                          border:
                              Border.all(color: action.color.withOpacity(0.16)),
                        ),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Container(
                              width: 46,
                              height: 46,
                              decoration: BoxDecoration(
                                color: action.color.withOpacity(0.10),
                                borderRadius: BorderRadius.circular(14),
                              ),
                              child: Icon(action.icon, color: action.color),
                            ),
                            const SizedBox(height: 12),
                            Text(
                              action.title,
                              style: const TextStyle(
                                fontWeight: FontWeight.w800,
                                color: Color(0xFF0F172A),
                              ),
                            ),
                            const SizedBox(height: 4),
                            Text(
                              action.subtitle,
                              style: TextStyle(
                                color: Colors.blueGrey.shade600,
                                height: 1.45,
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                  ))
              .toList(),
        ),
      ],
    );
  }
}

BoxDecoration _panelDecoration() {
  return BoxDecoration(
    color: Colors.white,
    borderRadius: BorderRadius.circular(28),
    border: Border.all(color: const Color(0xFFE2E8F0)),
    boxShadow: [
      BoxShadow(
        color: const Color(0xFF0F172A).withOpacity(0.05),
        blurRadius: 24,
        offset: const Offset(0, 10),
      ),
    ],
  );
}

Color _scopeColor(String key, Color fallback) {
  switch (key) {
    case 'personal':
      return const Color(0xFF2563EB);
    case 'private_scope':
      return const Color(0xFF7C3AED);
    case 'team':
      return const Color(0xFF0F766E);
    case 'organization':
      return const Color(0xFFEA580C);
    default:
      return fallback;
  }
}

// Mục đích: Hàm `mathMax` triển khai phần việc `math Max` trong flutter_frontend/lib/screens/dashboard/dashboard_hub_screen.dart.
// Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
// Vai trò trong hệ thống: Đây là hàm thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
// Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

int mathMax(int left, int right) => left > right ? left : right;
