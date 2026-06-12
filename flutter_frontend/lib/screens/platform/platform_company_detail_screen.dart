// === MÀN HÌNH CHI TIẾT CÔNG TY (platform-admin) ===
// Dashboard của 1 công ty (companyDashboardProvider): tổng quan + thống kê mở rộng (_ExtendedStatsGrid), hoạt động, sao lưu, lưu trữ qua các tab widget. _refreshAll làm mới toàn bộ.

// r5/M9 — Dashboard chi tiet cho 1 cong ty (platform admin only).
//
// Route: /platform/companies/:id
// 5 tab:
//   - Tong quan: info card + counts grid + storage chart
//   - Nguoi dung: link sang trang quan tri user
//   - Phong ban: link sang trang quan tri phong ban
//   - Backup: 10 backup gan nhat + badge ma hoa/ky so + nut tao
//   - Hoat dong: timeline 20 entry

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../models/company_dashboard.dart';
import '../../providers/company_dashboard_provider.dart';
import 'widgets/company_overview_card.dart';
import 'widgets/company_storage_chart.dart';
import 'widgets/company_backups_tab.dart';
import 'widgets/company_activity_tab.dart';

class PlatformCompanyDetailScreen extends ConsumerStatefulWidget {
  final int companyId;
  const PlatformCompanyDetailScreen({super.key, required this.companyId});

  @override
  ConsumerState<PlatformCompanyDetailScreen> createState() => _State();
}

class _State extends ConsumerState<PlatformCompanyDetailScreen>
    with SingleTickerProviderStateMixin {
  late final TabController _tab = TabController(length: 5, vsync: this);

  @override
  void dispose() {
    _tab.dispose();
    super.dispose();
  }

  void _refreshAll() {
    ref.invalidate(companyDashboardProvider(widget.companyId));
    ref.invalidate(companyActivityProvider(widget.companyId));
  }

  @override
  Widget build(BuildContext context) {
    final async = ref.watch(companyDashboardProvider(widget.companyId));
    return Scaffold(
      appBar: AppBar(
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => context.go('/platform/companies'),
          tooltip: 'Quay lại danh sách công ty',
        ),
        title: async.when(
          data: (d) => Text('Quản trị công ty: ${d.company.name}'),
          loading: () => const Text('Quản trị công ty'),
          error: (_, __) => const Text('Quản trị công ty'),
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            tooltip: 'Làm mới',
            onPressed: _refreshAll,
          ),
        ],
        bottom: TabBar(
          controller: _tab,
          isScrollable: true,
          tabs: const [
            Tab(icon: Icon(Icons.dashboard), text: 'Tổng quan'),
            Tab(icon: Icon(Icons.people), text: 'Người dùng'),
            Tab(icon: Icon(Icons.account_tree), text: 'Phòng ban'),
            Tab(icon: Icon(Icons.backup), text: 'Backup'),
            Tab(icon: Icon(Icons.history), text: 'Hoạt động'),
          ],
        ),
      ),
      body: async.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => _ErrorView(error: e.toString(), onRetry: _refreshAll),
        data: (dashboard) => TabBarView(
          controller: _tab,
          children: [
            _OverviewTab(dashboard: dashboard),
            _LinkToManagementTab(
              icon: Icons.people,
              title: 'Quản trị người dùng',
              description: 'Người dùng của công ty này được quản trị tại trang Admin (cùng company).',
              actionLabel: 'Mở trang admin',
              onAction: () => context.go('/admin'),
            ),
            _LinkToManagementTab(
              icon: Icons.account_tree,
              title: 'Quản trị phòng ban',
              description: 'Phòng ban thuộc company được quản lý từ trang Admin tương ứng.',
              actionLabel: 'Mở trang admin',
              onAction: () => context.go('/admin'),
            ),
            CompanyBackupsTab(companyId: widget.companyId, dashboard: dashboard),
            CompanyActivityTab(companyId: widget.companyId),
          ],
        ),
      ),
    );
  }
}

class _OverviewTab extends StatelessWidget {
  final CompanyDashboard dashboard;
  const _OverviewTab({required this.dashboard});

  @override
  Widget build(BuildContext context) {
    final isWide = MediaQuery.of(context).size.width > 1200;
    final overview = CompanyOverviewCard(dashboard: dashboard);
    final right = Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        _CountsGrid(counts: dashboard.counts),
        const SizedBox(height: 16),
        _ExtendedStatsGrid(extended: dashboard.extended),
        const SizedBox(height: 16),
        _StatusBreakdownCard(extended: dashboard.extended),
        const SizedBox(height: 16),
        CompanyStorageChart(
          totalBytes: dashboard.storageTotalBytes,
          bySubdir: dashboard.storageBySubdir,
        ),
      ],
    );
    final orgTree = _OrgTreeCard(
      root: dashboard.orgTreeRoot,
      totals: dashboard.orgTreeTotals,
    );
    if (isWide) {
      return SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Expanded(flex: 5, child: overview),
                const SizedBox(width: 16),
                Expanded(flex: 7, child: right),
              ],
            ),
            const SizedBox(height: 16),
            orgTree,
          ],
        ),
      );
    }
    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          overview,
          const SizedBox(height: 16),
          right,
          const SizedBox(height: 16),
          orgTree,
        ],
      ),
    );
  }
}

class _ExtendedStatsGrid extends StatelessWidget {
  final CompanyExtendedStats extended;
  const _ExtendedStatsGrid({required this.extended});

  @override
  Widget build(BuildContext context) {
    final items = <_StatTile>[
      _StatTile(
        icon: Icons.person_search,
        label: 'Người dùng hoạt động (30 ngày)',
        value: '${extended.usersActive30d}',
        color: const Color(0xFF22C55E),
      ),
      _StatTile(
        icon: Icons.article_outlined,
        label: 'Văn bản mới (30 ngày)',
        value: '${extended.documents30d}',
        color: const Color(0xFF3B82F6),
      ),
      _StatTile(
        icon: Icons.description_outlined,
        label: 'Mẫu mới (30 ngày)',
        value: '${extended.templates30d}',
        color: const Color(0xFF8B5CF6),
      ),
      _StatTile(
        icon: Icons.smart_toy_outlined,
        label: 'Lượt gọi AI (30 ngày)',
        value: '${extended.aiCalls30d}',
        sub: 'Tổng: ${extended.aiCallsTotal}',
        color: const Color(0xFFF97316),
      ),
      _StatTile(
        icon: Icons.account_tree_outlined,
        label: 'Thành viên có phòng ban',
        value: '${extended.membersWithDepartment}',
        sub: 'Chưa phân: ${extended.membersWithoutDepartment}',
        color: const Color(0xFF0EA5E9),
      ),
      _StatTile(
        icon: Icons.pending_actions,
        label: 'Chia sẻ chờ duyệt',
        value: '${extended.pendingDocShares + extended.pendingTemplateShares}',
        sub: 'Văn bản: ${extended.pendingDocShares} · Mẫu: ${extended.pendingTemplateShares}',
        color: const Color(0xFFEAB308),
      ),
    ];
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text('Hoạt động & vận hành',
                style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
            const SizedBox(height: 12),
            LayoutBuilder(builder: (context, c) {
              final cols = c.maxWidth > 800 ? 3 : (c.maxWidth > 480 ? 2 : 1);
              return GridView.count(
                crossAxisCount: cols,
                shrinkWrap: true,
                physics: const NeverScrollableScrollPhysics(),
                childAspectRatio: cols == 1 ? 4.5 : 2.4,
                crossAxisSpacing: 10,
                mainAxisSpacing: 10,
                children: items
                    .map((it) => _StatTileWidget(tile: it))
                    .toList(),
              );
            }),
          ],
        ),
      ),
    );
  }
}

class _StatTile {
  final IconData icon;
  final String label;
  final String value;
  final String? sub;
  final Color color;
  const _StatTile({
    required this.icon,
    required this.label,
    required this.value,
    this.sub,
    required this.color,
  });
}

class _StatTileWidget extends StatelessWidget {
  final _StatTile tile;
  const _StatTileWidget({required this.tile});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: tile.color.withOpacity(0.08),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: tile.color.withOpacity(0.25)),
      ),
      child: Row(children: [
        Container(
          padding: const EdgeInsets.all(8),
          decoration: BoxDecoration(
            color: tile.color.withOpacity(0.18),
            borderRadius: BorderRadius.circular(8),
          ),
          child: Icon(tile.icon, color: tile.color, size: 22),
        ),
        const SizedBox(width: 10),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(tile.label,
                  style: const TextStyle(
                      fontSize: 11, color: Color(0xFF64748B)),
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis),
              const SizedBox(height: 2),
              Text(tile.value,
                  style: TextStyle(
                      fontSize: 22,
                      fontWeight: FontWeight.w800,
                      color: tile.color)),
              if (tile.sub != null && tile.sub!.isNotEmpty)
                Text(tile.sub!,
                    style: const TextStyle(
                        fontSize: 10, color: Color(0xFF94A3B8))),
            ],
          ),
        ),
      ]),
    );
  }
}

class _StatusBreakdownCard extends StatelessWidget {
  final CompanyExtendedStats extended;
  const _StatusBreakdownCard({required this.extended});

  Widget _statusRow(String title, Map<String, int> data, Color base) {
    final total = data.values.fold<int>(0, (a, b) => a + b);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Padding(
          padding: const EdgeInsets.only(bottom: 6),
          child: Text(title,
              style: const TextStyle(
                  fontSize: 13, fontWeight: FontWeight.w700)),
        ),
        if (total == 0)
          const Text('Chưa có dữ liệu',
              style: TextStyle(fontSize: 11, color: Colors.grey))
        else
          Wrap(
            spacing: 6,
            runSpacing: 6,
            children: data.entries.map((e) {
              final pct = total == 0 ? 0 : ((e.value / total) * 100).round();
              return Container(
                padding: const EdgeInsets.symmetric(
                    horizontal: 10, vertical: 5),
                decoration: BoxDecoration(
                  color: base.withOpacity(0.1),
                  borderRadius: BorderRadius.circular(20),
                  border: Border.all(color: base.withOpacity(0.3)),
                ),
                child: Text(
                  '${_statusLabel(e.key)} · ${e.value} ($pct%)',
                  style: TextStyle(
                      fontSize: 11,
                      color: base,
                      fontWeight: FontWeight.w600),
                ),
              );
            }).toList(),
          ),
      ],
    );
  }

  String _statusLabel(String key) => switch (key.toLowerCase()) {
        'approved' => 'Đã duyệt',
        'pending' => 'Chờ duyệt',
        'rejected' => 'Bị từ chối',
        'draft' => 'Nháp',
        'archived' => 'Lưu trữ',
        'deleted' => 'Đã xoá',
        'active' => 'Hoạt động',
        _ => key,
      };

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text('Phân loại trạng thái',
                style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
            const SizedBox(height: 12),
            _statusRow('Mẫu văn bản', extended.templatesByStatus,
                const Color(0xFF8B5CF6)),
            const SizedBox(height: 12),
            _statusRow('Văn bản', extended.documentsByStatus,
                const Color(0xFF3B82F6)),
          ],
        ),
      ),
    );
  }
}

class _OrgTreeCard extends StatelessWidget {
  final OrgTreeNode? root;
  final Map<String, int> totals;
  const _OrgTreeCard({required this.root, required this.totals});

  @override
  Widget build(BuildContext context) {
    final root = this.root;
    return Card(
      elevation: 0,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(18),
        side: const BorderSide(color: Color(0xFFE2E8F0)),
      ),
      child: Padding(
        padding: const EdgeInsets.fromLTRB(20, 18, 20, 22),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Row(children: [
              Container(
                padding: const EdgeInsets.all(8),
                decoration: BoxDecoration(
                  gradient: const LinearGradient(
                    colors: [Color(0xFF1E40AF), Color(0xFF3B82F6)],
                  ),
                  borderRadius: BorderRadius.circular(10),
                ),
                child: const Icon(Icons.account_tree,
                    color: Colors.white, size: 20),
              ),
              const SizedBox(width: 12),
              const Expanded(
                child: Text('Sơ đồ tổ chức',
                    style: TextStyle(
                        fontSize: 17,
                        fontWeight: FontWeight.w800,
                        color: Color(0xFF0F172A))),
              ),
              if (root != null) ...[
                _Chip('${totals['departments'] ?? 0} phòng ban',
                    const Color(0xFF1D4ED8)),
                const SizedBox(width: 6),
                _Chip('${totals['members'] ?? 0} thành viên',
                    const Color(0xFF15803D)),
              ],
            ]),
            const SizedBox(height: 6),
            const Text(
              'Hiển thị từ công ty (trên cùng) → các phòng ban → thành viên (dưới).',
              style: TextStyle(fontSize: 12, color: Color(0xFF64748B)),
            ),
            const SizedBox(height: 18),
            if (root == null)
              const Padding(
                padding: EdgeInsets.symmetric(vertical: 30),
                child: Center(
                  child: Text('Chưa có dữ liệu cơ cấu tổ chức.',
                      style: TextStyle(color: Color(0xFF94A3B8))),
                ),
              )
            else
              SingleChildScrollView(
                scrollDirection: Axis.horizontal,
                child: Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 8),
                  child: _OrgTreeVerticalChart(root: root),
                ),
              ),
          ],
        ),
      ),
    );
  }
}

/// Cay to chuc dang dung: Cong ty -> connector doc -> hang ngang departments
/// -> connector doc -> members.
class _OrgTreeVerticalChart extends StatelessWidget {
  final OrgTreeNode root;
  const _OrgTreeVerticalChart({required this.root});

  @override
  Widget build(BuildContext context) {
    final departments = root.children;
    return Column(
      mainAxisSize: MainAxisSize.min,
      crossAxisAlignment: CrossAxisAlignment.center,
      children: [
        _OrgNodeCard(node: root),
        if (departments.isNotEmpty) ...[
          const _Trunk(height: 18),
          _DepartmentRow(departments: departments),
        ],
      ],
    );
  }
}

class _Trunk extends StatelessWidget {
  final double height;
  final Color color;
  const _Trunk({this.height = 16, this.color = const Color(0xFFCBD5E1)});
  @override
  Widget build(BuildContext context) {
    return Container(
      width: 2,
      height: height,
      color: color,
    );
  }
}

class _DepartmentRow extends StatelessWidget {
  final List<OrgTreeNode> departments;
  const _DepartmentRow({required this.departments});

  @override
  Widget build(BuildContext context) {
    return Stack(
      children: [
        // Horizontal connector across all departments
        Positioned(
          top: 0,
          left: 80,
          right: 80,
          child: Container(height: 2, color: const Color(0xFFCBD5E1)),
        ),
        Padding(
          padding: const EdgeInsets.only(top: 0),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: departments
                .map((d) => Padding(
                      padding: const EdgeInsets.symmetric(horizontal: 8),
                      child: _DepartmentBranch(department: d),
                    ))
                .toList(),
          ),
        ),
      ],
    );
  }
}

class _DepartmentBranch extends StatelessWidget {
  final OrgTreeNode department;
  const _DepartmentBranch({required this.department});

  @override
  Widget build(BuildContext context) {
    final members = department.children;
    return Column(
      mainAxisSize: MainAxisSize.min,
      crossAxisAlignment: CrossAxisAlignment.center,
      children: [
        const _Trunk(height: 14),
        _OrgNodeCard(node: department),
        if (members.isNotEmpty) ...[
          const _Trunk(height: 14),
          ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 240),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: members
                  .map((m) => Padding(
                        padding: const EdgeInsets.only(bottom: 6),
                        child: _OrgNodeCard(node: m, compact: true),
                      ))
                  .toList(),
            ),
          ),
        ],
      ],
    );
  }
}

class _OrgNodeCard extends StatelessWidget {
  final OrgTreeNode node;
  final bool compact;
  const _OrgNodeCard({required this.node, this.compact = false});

  ({Color bg, Color border, Color accent, IconData icon, String headerLabel})
      _palette() {
    switch (node.type) {
      case 'company':
        return (
          bg: const Color(0xFFEFF6FF),
          border: const Color(0xFF3B82F6),
          accent: const Color(0xFF1E3A8A),
          icon: Icons.business,
          headerLabel: 'CÔNG TY',
        );
      case 'department':
        return (
          bg: const Color(0xFFEEF2FF),
          border: const Color(0xFF818CF8),
          accent: const Color(0xFF3730A3),
          icon: Icons.account_tree,
          headerLabel: 'PHÒNG BAN',
        );
      default:
        return (
          bg: const Color(0xFFF8FAFC),
          border: const Color(0xFFCBD5E1),
          accent: const Color(0xFF1F2937),
          icon: Icons.person,
          headerLabel: 'THÀNH VIÊN',
        );
    }
  }

  @override
  Widget build(BuildContext context) {
    final palette = _palette();
    final isLeader = node.role == 'leader';
    final isMember = node.type == 'member';
    final width = node.type == 'company'
        ? 280.0
        : (node.type == 'department' ? 220.0 : (compact ? 220.0 : 200.0));
    return Container(
      width: width,
      padding: EdgeInsets.symmetric(
        horizontal: isMember && compact ? 10 : 12,
        vertical: isMember && compact ? 8 : 12,
      ),
      decoration: BoxDecoration(
        color: palette.bg,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: palette.border, width: 1.3),
        boxShadow: [
          BoxShadow(
            color: palette.border.withOpacity(0.18),
            blurRadius: 10,
            offset: const Offset(0, 4),
          ),
        ],
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          if (!compact)
            Padding(
              padding: const EdgeInsets.only(bottom: 4),
              child: Text(
                palette.headerLabel,
                style: TextStyle(
                  fontSize: 9.5,
                  letterSpacing: 1.2,
                  fontWeight: FontWeight.w800,
                  color: palette.accent.withOpacity(0.7),
                ),
              ),
            ),
          Row(
            crossAxisAlignment: CrossAxisAlignment.center,
            children: [
              Container(
                padding: const EdgeInsets.all(6),
                decoration: BoxDecoration(
                  color: palette.border.withOpacity(0.22),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Icon(palette.icon,
                    color: palette.accent, size: compact ? 14 : 18),
              ),
              const SizedBox(width: 8),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Text(
                      node.name,
                      style: TextStyle(
                        fontSize: compact
                            ? 12.5
                            : (node.type == 'company' ? 15 : 13.5),
                        fontWeight: FontWeight.w800,
                        color: palette.accent,
                        height: 1.2,
                      ),
                      overflow: TextOverflow.ellipsis,
                      maxLines: 2,
                    ),
                    if (node.subtitle.isNotEmpty)
                      Padding(
                        padding: const EdgeInsets.only(top: 2),
                        child: Text(
                          node.subtitle,
                          style: TextStyle(
                            fontSize: compact ? 10.5 : 11.5,
                            color: const Color(0xFF64748B),
                            fontWeight: FontWeight.w500,
                          ),
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                        ),
                      ),
                  ],
                ),
              ),
              if (isLeader)
                Container(
                  padding: const EdgeInsets.symmetric(
                      horizontal: 6, vertical: 2),
                  decoration: BoxDecoration(
                    color: const Color(0xFFFEF3C7),
                    borderRadius: BorderRadius.circular(8),
                    border: Border.all(color: const Color(0xFFFCD34D)),
                  ),
                  child: const Text(
                    'Trưởng',
                    style: TextStyle(
                      fontSize: 9.5,
                      color: Color(0xFF92400E),
                      fontWeight: FontWeight.w800,
                    ),
                  ),
                ),
            ],
          ),
        ],
      ),
    );
  }
}

class _Chip extends StatelessWidget {
  final String label;
  final Color color;
  const _Chip(this.label, this.color);
  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
        decoration: BoxDecoration(
          color: color.withOpacity(0.12),
          borderRadius: BorderRadius.circular(20),
          border: Border.all(color: color.withOpacity(0.3)),
        ),
        child: Text(label,
            style: TextStyle(
                fontSize: 11, color: color, fontWeight: FontWeight.w700)),
      );
}

class _OrgTreeNodeView extends StatelessWidget {
  final OrgTreeNode node;
  final int depth;
  const _OrgTreeNodeView({required this.node, required this.depth});

  @override
  Widget build(BuildContext context) {
    final colors = _colorsForType(node.type);
    final indent = depth * 18.0;
    return Padding(
      padding: EdgeInsets.only(left: indent, bottom: 6, top: 2),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            crossAxisAlignment: CrossAxisAlignment.center,
            children: [
              if (depth > 0)
                Container(
                  width: 14,
                  height: 1.2,
                  margin: const EdgeInsets.only(right: 6),
                  color: const Color(0xFFCBD5E1),
                ),
              Container(
                padding: const EdgeInsets.symmetric(
                    horizontal: 10, vertical: 8),
                decoration: BoxDecoration(
                  color: colors.$1,
                  borderRadius: BorderRadius.circular(10),
                  border: Border.all(color: colors.$2),
                ),
                child: Row(mainAxisSize: MainAxisSize.min, children: [
                  Icon(_iconForType(node.type),
                      color: colors.$3, size: 18),
                  const SizedBox(width: 8),
                  Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Row(mainAxisSize: MainAxisSize.min, children: [
                        Text(node.name,
                            style: TextStyle(
                              fontWeight: FontWeight.w700,
                              fontSize: node.type == 'company' ? 15 : 13,
                              color: colors.$3,
                            )),
                        if (node.role == 'leader') ...[
                          const SizedBox(width: 6),
                          Container(
                            padding: const EdgeInsets.symmetric(
                                horizontal: 6, vertical: 1),
                            decoration: BoxDecoration(
                              color: const Color(0xFFFEF3C7),
                              borderRadius: BorderRadius.circular(8),
                              border: Border.all(
                                  color: const Color(0xFFFCD34D)),
                            ),
                            child: const Text('Trưởng phòng',
                                style: TextStyle(
                                    fontSize: 9.5,
                                    color: Color(0xFF92400E),
                                    fontWeight: FontWeight.w800)),
                          ),
                        ],
                      ]),
                      if (node.subtitle.isNotEmpty)
                        Text(node.subtitle,
                            style: const TextStyle(
                                fontSize: 11,
                                color: Color(0xFF64748B))),
                    ],
                  ),
                ]),
              ),
            ],
          ),
          ...node.children.map(
            (c) => _OrgTreeNodeView(node: c, depth: depth + 1),
          ),
        ],
      ),
    );
  }

  IconData _iconForType(String t) => switch (t) {
        'company' => Icons.business,
        'department' => Icons.account_tree,
        _ => Icons.person_outline,
      };

  // (background, border, text/icon)
  (Color, Color, Color) _colorsForType(String t) => switch (t) {
        'company' => (
            const Color(0xFFDBEAFE),
            const Color(0xFF60A5FA),
            const Color(0xFF1E3A8A)
          ),
        'department' => (
            const Color(0xFFE0E7FF),
            const Color(0xFFA5B4FC),
            const Color(0xFF3730A3)
          ),
        _ => (
            const Color(0xFFF1F5F9),
            const Color(0xFFCBD5E1),
            const Color(0xFF334155)
          ),
      };
}

class _CountsGrid extends StatelessWidget {
  final Map<String, int> counts;
  const _CountsGrid({required this.counts});

  static const _items = <_CountItem>[
    _CountItem('users', 'Người dùng', Icons.people),
    _CountItem('departments', 'Phòng ban', Icons.account_tree),
    _CountItem('positions', 'Chức danh', Icons.badge),
    _CountItem('templates', 'Mẫu văn bản', Icons.description),
    _CountItem('documents', 'Văn bản', Icons.article),
    _CountItem('prompts', 'Prompts', Icons.psychology),
    _CountItem('backups', 'Bản backup', Icons.backup),
  ];

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Tổng quan số liệu',
              style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16),
            ),
            const SizedBox(height: 12),
            LayoutBuilder(builder: (context, constraints) {
              final w = constraints.maxWidth;
              final cols = w > 800 ? 4 : (w > 500 ? 3 : 2);
              return GridView.count(
                crossAxisCount: cols,
                shrinkWrap: true,
                physics: const NeverScrollableScrollPhysics(),
                childAspectRatio: 2.4,
                crossAxisSpacing: 8,
                mainAxisSpacing: 8,
                children: _items.map((it) {
                  final value = counts[it.key] ?? 0;
                  return Container(
                    padding: const EdgeInsets.all(8),
                    decoration: BoxDecoration(
                      color: Theme.of(context).colorScheme.surfaceContainerHighest,
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: Row(
                      children: [
                        Icon(it.icon, color: Theme.of(context).colorScheme.primary, size: 28),
                        const SizedBox(width: 8),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            mainAxisAlignment: MainAxisAlignment.center,
                            children: [
                              Text(it.label, style: const TextStyle(fontSize: 11, color: Colors.grey)),
                              Text('$value', style: const TextStyle(fontSize: 20, fontWeight: FontWeight.bold)),
                            ],
                          ),
                        ),
                      ],
                    ),
                  );
                }).toList(),
              );
            }),
          ],
        ),
      ),
    );
  }
}

class _CountItem {
  final String key;
  final String label;
  final IconData icon;
  const _CountItem(this.key, this.label, this.icon);
}

class _LinkToManagementTab extends StatelessWidget {
  final IconData icon;
  final String title;
  final String description;
  final String actionLabel;
  final VoidCallback onAction;

  const _LinkToManagementTab({
    required this.icon,
    required this.title,
    required this.description,
    required this.actionLabel,
    required this.onAction,
  });

  @override
  Widget build(BuildContext context) => Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(icon, size: 64, color: Theme.of(context).colorScheme.primary),
              const SizedBox(height: 16),
              Text(title, style: Theme.of(context).textTheme.titleLarge),
              const SizedBox(height: 8),
              Text(description, textAlign: TextAlign.center, style: const TextStyle(color: Colors.grey)),
              const SizedBox(height: 16),
              FilledButton.icon(
                icon: const Icon(Icons.open_in_new),
                label: Text(actionLabel),
                onPressed: onAction,
              ),
            ],
          ),
        ),
      );
}

class _ErrorView extends StatelessWidget {
  final String error;
  final VoidCallback onRetry;
  const _ErrorView({required this.error, required this.onRetry});

  @override
  Widget build(BuildContext context) => Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.error_outline, size: 48, color: Colors.red),
            const SizedBox(height: 12),
            Text('Lỗi tải dashboard: $error', textAlign: TextAlign.center),
            const SizedBox(height: 12),
            FilledButton.icon(
              icon: const Icon(Icons.refresh),
              label: const Text('Thử lại'),
              onPressed: onRetry,
            ),
          ],
        ),
      );
}
