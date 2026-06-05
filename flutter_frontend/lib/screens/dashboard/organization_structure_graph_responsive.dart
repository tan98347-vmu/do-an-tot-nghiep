// Tệp này dùng để: dựng giao diện và orchestration UI trong flutter_frontend/lib/screens/dashboard/organization_structure_graph_responsive.dart.
// Cách hoạt động: nhận state từ provider, dựng widget, phản ứng sự kiện và gửi thao tác ngược về backend khi người dùng tương tác.
// Vai trò trong hệ thống: Đây là màn hình Flutter mà người dùng tương tác trực tiếp.
// Tác dụng khi hệ thống vận hành: biến nghiệp vụ backend thành trải nghiệm thao tác cụ thể trên web.

import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../l10n/app_strings.dart';
import '../../models/dashboard_stats.dart';
import '../../models/user.dart';
import '../../providers/dashboard_provider.dart';

// Mục đích: Lớp `OrganizationStructureGraphResponsive` triển khai phần việc `Organization Structure Graph Responsive` trong flutter_frontend/lib/screens/dashboard/organization_structure_graph_responsive.dart.
// Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
// Vai trò trong hệ thống: Đây là lớp thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
// Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

class OrganizationStructureGraphResponsive extends ConsumerStatefulWidget {
  final OrgStructure structure;
  final AppUser? viewer;

  const OrganizationStructureGraphResponsive({
    super.key,
    required this.structure,
    required this.viewer,
  });

  @override
  ConsumerState<OrganizationStructureGraphResponsive> createState() =>
      _OrganizationStructureGraphResponsiveState();
}

// Mục đích: Lớp `_OrganizationStructureGraphResponsiveState` triển khai phần việc `Organization Structure Graph Responsive State` trong flutter_frontend/lib/screens/dashboard/organization_structure_graph_responsive.dart.
// Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
// Vai trò trong hệ thống: Đây là lớp thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
// Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

class _OrganizationStructureGraphResponsiveState
    extends ConsumerState<OrganizationStructureGraphResponsive> {
  final TransformationController _controller = TransformationController();
  String? _selectedNodeId;

  @override
  // Mục đích: Phương thức `initState` triển khai phần việc `init State` trong flutter_frontend/lib/screens/dashboard/organization_structure_graph_responsive.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  void initState() {
    super.initState();
    final all = [
      ...widget.structure.admins,
      ...widget.structure.leaders,
      ...widget.structure.employees,
    ];
    _selectedNodeId = all.isEmpty ? null : all.first.id;
  }

  @override
  // Mục đích: Phương thức `dispose` triển khai phần việc `dispose` trong flutter_frontend/lib/screens/dashboard/organization_structure_graph_responsive.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  // Mục đích: Phương thức `build` triển khai phần việc `build` trong flutter_frontend/lib/screens/dashboard/organization_structure_graph_responsive.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  Widget build(BuildContext context) {
    final strings = AppStrings.of(context);
    final isCompact = MediaQuery.sizeOf(context).width < 900;
    final people = [
      ...widget.structure.admins,
      ...widget.structure.leaders,
      ...widget.structure.employees,
    ];
    final peopleById = {for (final person in people) person.id: person};
    final layout = _buildLayout();

    return Card(
      child: Padding(
        padding: EdgeInsets.all(isCompact ? 14 : 20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              strings.ui('Bản đồ cấu trúc doanh nghiệp'),
              style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                    fontWeight: FontWeight.w800,
                  ),
            ),
            const SizedBox(height: 8),
            Text(strings.ui(widget.structure.summary)),
            const SizedBox(height: 12),
            Wrap(
              spacing: 10,
              runSpacing: 10,
              children: [
                _Legend(
                    label: strings.pick('Quản trị viên', 'Administrators'),
                    color: const Color(0xFF1D4ED8)),
                _Legend(
                    label: strings.ui('Trưởng nhóm'),
                    color: const Color(0xFF7C3AED)),
                _Legend(
                    label: strings.ui('Nhân viên'),
                    color: const Color(0xFF0F766E)),
                OutlinedButton.icon(
                  onPressed: () => _controller.value = Matrix4.identity(),
                  icon:
                      const Icon(Icons.center_focus_strong_outlined, size: 18),
                  label: Text(strings.ui('Đặt lại góc nhìn')),
                ),
              ],
            ),
            const SizedBox(height: 14),
            Container(
              height: isCompact ? 420 : 620,
              decoration: BoxDecoration(
                color: const Color(0xFF0F172A),
                borderRadius: BorderRadius.circular(24),
              ),
              child: ClipRRect(
                borderRadius: BorderRadius.circular(24),
                child: InteractiveViewer(
                  constrained: false,
                  minScale: 0.52,
                  maxScale: 1.9,
                  boundaryMargin: const EdgeInsets.all(180),
                  transformationController: _controller,
                  child: SizedBox(
                    width: layout.canvasWidth,
                    height: layout.canvasHeight,
                    child: Stack(
                      children: [
                        CustomPaint(
                          size: Size(layout.canvasWidth, layout.canvasHeight),
                          painter: _EdgePainter(
                            positions: layout.positions,
                            reportingEdges: widget.structure.reportingEdges,
                            teamEdges: widget.structure.teamEdges,
                            selectedNodeId: _selectedNodeId,
                          ),
                        ),
                        for (final marker in layout.markers)
                          Positioned(
                            left: 18,
                            top: marker.$2,
                            child: _Marker(label: marker.$1),
                          ),
                        for (final entry in layout.positions.entries)
                          Positioned(
                            left: entry.value.dx,
                            top: entry.value.dy,
                            child: _NodeCard(
                              person: peopleById[entry.key]!,
                              selected: entry.key == _selectedNodeId,
                              onTap: () => _handleTap(
                                context,
                                peopleById[entry.key]!,
                                isCompact,
                              ),
                            ),
                          ),
                      ],
                    ),
                  ),
                ),
              ),
            ),
            const SizedBox(height: 12),
            Text(
              _viewerCanInspectAny
                  ? strings.pick(
                      'Chạm vào user để xem thông tin. Quản trị viên xem được tất cả; trưởng nhóm chỉ xem được nhân viên mình quản lý.',
                      'Tap a user to inspect details. Administrators can inspect everyone; team leads can inspect only the employees they manage.',
                    )
                  : strings.pick(
                      'Bạn đang ở chế độ xem bản đồ. Có thể chạm để highlight và pan/zoom để đọc cấu trúc.',
                      'You are in map view. Tap to highlight and use pan/zoom to read the structure.',
                    ),
              style: TextStyle(color: Colors.blueGrey.shade700, height: 1.45),
            ),
          ],
        ),
      ),
    );
  }

  bool get _viewerCanInspectAny {
    final viewer = widget.viewer;
    return viewer != null &&
        (viewer.isSuperuser || viewer.isStaff || viewer.isLeaderOfAny);
  }

  // Mục đích: Phương thức `_canInspectPerson` triển khai phần việc `can Inspect Person` trong flutter_frontend/lib/screens/dashboard/organization_structure_graph_responsive.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  bool _canInspectPerson(OrgPerson person) {
    final viewer = widget.viewer;
    if (viewer == null) return false;
    if (viewer.isSuperuser || viewer.isStaff) return true;
    if (!viewer.isLeaderOfAny) return false;
    return person.role == 'employee';
  }

  // Mục đích: Phương thức `_handleTap` triển khai phần việc `handle Tap` trong flutter_frontend/lib/screens/dashboard/organization_structure_graph_responsive.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  void _handleTap(BuildContext context, OrgPerson person, bool isCompact) {
    // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

    setState(() => _selectedNodeId = person.id);
    if (!_canInspectPerson(person)) return;
    final content = _Inspector(person: person);
    if (isCompact) {
      showModalBottomSheet<void>(
        context: context,
        showDragHandle: true,
        isScrollControlled: true,
        builder: (_) => SafeArea(
          child: Padding(
            padding: const EdgeInsets.fromLTRB(16, 8, 16, 18),
            child: content,
          ),
        ),
      );
      return;
    }
    showDialog<void>(
      context: context,
      builder: (_) => Dialog(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 720),
          child: Padding(
            padding: const EdgeInsets.all(20),
            child: content,
          ),
        ),
      ),
    );
  }

  _Layout _buildLayout() {
    const nodeWidth = 220.0;
    const nodeHeight = 108.0;
    const gapX = 34.0;
    const marginX = 110.0;
    const marginY = 80.0;
    const gapY = 180.0;

    Map<String, Offset> place(List<OrgPerson> layer, double y, double width) {
      final result = <String, Offset>{};
      if (layer.isEmpty) return result;
      final totalWidth = layer.length * nodeWidth + (layer.length - 1) * gapX;
      final startX = math.max(marginX, (width - totalWidth) / 2);
      for (var index = 0; index < layer.length; index++) {
        result[layer[index].id] =
            Offset(startX + index * (nodeWidth + gapX), y);
      }
      return result;
    }

    final maxCount = math.max(
      1,
      math.max(
        widget.structure.admins.length,
        math.max(
            widget.structure.leaders.length, widget.structure.employees.length),
      ),
    );
    final width = math.max(1480, marginX * 2 + maxCount * (nodeWidth + gapX));
    final positions = <String, Offset>{}
      ..addAll(place(widget.structure.admins, marginY, width.toDouble()))
      ..addAll(
          place(widget.structure.leaders, marginY + gapY, width.toDouble()))
      ..addAll(place(
          widget.structure.employees, marginY + gapY * 2, width.toDouble()));
    return _Layout(
      canvasWidth: width.toDouble(),
      canvasHeight: marginY * 2 + nodeHeight * 3 + gapY * 2,
      positions: positions,
      markers: [
        (AppStrings.of(context).pick('Quản trị', 'Admins'), 92),
        (AppStrings.of(context).pick('Trưởng nhóm', 'Team leads'), 272),
        (AppStrings.of(context).pick('Nhân viên', 'Employees'), 452),
      ],
    );
  }
}

// Mục đích: Lớp `_Layout` triển khai phần việc `Layout` trong flutter_frontend/lib/screens/dashboard/organization_structure_graph_responsive.dart.
// Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
// Vai trò trong hệ thống: Đây là lớp thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
// Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

class _Layout {
  final double canvasWidth;
  final double canvasHeight;
  final Map<String, Offset> positions;
  final List<(String, double)> markers;

  const _Layout({
    required this.canvasWidth,
    required this.canvasHeight,
    required this.positions,
    required this.markers,
  });
}

// Mục đích: Lớp `_EdgePainter` triển khai phần việc `Edge Painter` trong flutter_frontend/lib/screens/dashboard/organization_structure_graph_responsive.dart.
// Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
// Vai trò trong hệ thống: Đây là lớp thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
// Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

class _EdgePainter extends CustomPainter {
  final Map<String, Offset> positions;
  final List<OrgEdge> reportingEdges;
  final List<OrgEdge> teamEdges;
  final String? selectedNodeId;

  const _EdgePainter({
    required this.positions,
    required this.reportingEdges,
    required this.teamEdges,
    required this.selectedNodeId,
  });

  @override
  // Mục đích: Phương thức `paint` triển khai phần việc `paint` trong flutter_frontend/lib/screens/dashboard/organization_structure_graph_responsive.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  void paint(Canvas canvas, Size size) {
    for (final edge in reportingEdges) {
      _draw(canvas, edge, const Color(0xFF93C5FD), false);
    }
    for (final edge in teamEdges) {
      _draw(canvas, edge, const Color(0xFFF59E0B), true);
    }
  }

  // Mục đích: Phương thức `_draw` triển khai phần việc `draw` trong flutter_frontend/lib/screens/dashboard/organization_structure_graph_responsive.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  void _draw(Canvas canvas, OrgEdge edge, Color color, bool dashed) {
    final from = positions[edge.from];
    final to = positions[edge.to];
    if (from == null || to == null) return;
    final start = Offset(from.dx + 110, from.dy + 54);
    final end = Offset(to.dx + 110, to.dy + 54);
    final path = Path()
      ..moveTo(start.dx, start.dy)
      ..cubicTo(
        start.dx,
        start.dy + (end.dy - start.dy) * 0.42,
        end.dx,
        end.dy - (end.dy - start.dy) * 0.42,
        end.dx,
        end.dy,
      );
    final selected = selectedNodeId == edge.from || selectedNodeId == edge.to;
    final paint = Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = selected ? 2.2 : 1.2
      ..color = color.withOpacity(selected ? 0.92 : 0.56);
    if (!dashed) {
      canvas.drawPath(path, paint);
      return;
    }
    for (final metric in path.computeMetrics()) {
      double distance = 0;
      while (distance < metric.length) {
        final next = math.min(distance + 8, metric.length);
        canvas.drawPath(metric.extractPath(distance, next), paint);
        distance += 14;
      }
    }
  }

  @override
  // Mục đích: Phương thức `shouldRepaint` triển khai phần việc `should Repaint` trong flutter_frontend/lib/screens/dashboard/organization_structure_graph_responsive.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  bool shouldRepaint(covariant _EdgePainter oldDelegate) {
    return oldDelegate.selectedNodeId != selectedNodeId ||
        oldDelegate.positions != positions ||
        oldDelegate.reportingEdges.length != reportingEdges.length ||
        oldDelegate.teamEdges.length != teamEdges.length;
  }
}

// Mục đích: Lớp `_NodeCard` triển khai phần việc `Node Card` trong flutter_frontend/lib/screens/dashboard/organization_structure_graph_responsive.dart.
// Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
// Vai trò trong hệ thống: Đây là lớp thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
// Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

class _NodeCard extends StatelessWidget {
  final OrgPerson person;
  final bool selected;
  final VoidCallback onTap;

  const _NodeCard({
    required this.person,
    required this.selected,
    required this.onTap,
  });

  @override
  // Mục đích: Phương thức `build` triển khai phần việc `build` trong flutter_frontend/lib/screens/dashboard/organization_structure_graph_responsive.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  Widget build(BuildContext context) {
    final strings = AppStrings.of(context);
    final color = _roleColor(person.role);
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(22),
      child: Container(
        width: 220,
        height: 108,
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(22),
          color: color.withOpacity(selected ? 0.30 : 0.18),
          border: Border.all(
            color: selected ? color : Colors.white.withOpacity(0.12),
            width: selected ? 2 : 1,
          ),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              _roleLabel(person.role, strings).toUpperCase(),
              style: const TextStyle(
                  fontSize: 10,
                  color: Colors.white70,
                  fontWeight: FontWeight.w700),
            ),
            const SizedBox(height: 8),
            Text(
              person.name,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: const TextStyle(
                  fontSize: 18,
                  fontWeight: FontWeight.w800,
                  color: Colors.white),
            ),
            const SizedBox(height: 4),
            Text(
              person.title.isEmpty ? person.username : person.title,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: const TextStyle(color: Colors.white70),
            ),
          ],
        ),
      ),
    );
  }
}

// Mục đích: Lớp `_Legend` triển khai phần việc `Legend` trong flutter_frontend/lib/screens/dashboard/organization_structure_graph_responsive.dart.
// Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
// Vai trò trong hệ thống: Đây là lớp thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
// Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

class _Legend extends StatelessWidget {
  final String label;
  final Color color;

  const _Legend({required this.label, required this.color});

  @override
  // Mục đích: Phương thức `build` triển khai phần việc `build` trong flutter_frontend/lib/screens/dashboard/organization_structure_graph_responsive.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      decoration: BoxDecoration(
        color: color.withOpacity(0.10),
        borderRadius: BorderRadius.circular(999),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Container(
              width: 10,
              height: 10,
              decoration: BoxDecoration(color: color, shape: BoxShape.circle)),
          const SizedBox(width: 8),
          Text(label),
        ],
      ),
    );
  }
}

// Mục đích: Lớp `_Marker` triển khai phần việc `Marker` trong flutter_frontend/lib/screens/dashboard/organization_structure_graph_responsive.dart.
// Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
// Vai trò trong hệ thống: Đây là lớp thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
// Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

class _Marker extends StatelessWidget {
  final String label;

  const _Marker({required this.label});

  @override
  // Mục đích: Phương thức `build` triển khai phần việc `build` trong flutter_frontend/lib/screens/dashboard/organization_structure_graph_responsive.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
      decoration: BoxDecoration(
        color: Colors.white.withOpacity(0.08),
        borderRadius: BorderRadius.circular(999),
      ),
      child: Text(label,
          style: const TextStyle(
              color: Colors.white70, fontWeight: FontWeight.w700)),
    );
  }
}

// Mục đích: Lớp `_Inspector` triển khai phần việc `Inspector` trong flutter_frontend/lib/screens/dashboard/organization_structure_graph_responsive.dart.
// Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
// Vai trò trong hệ thống: Đây là lớp thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
// Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

class _Inspector extends ConsumerWidget {
  final OrgPerson person;

  const _Inspector({required this.person});

  @override
  // Mục đích: Phương thức `build` triển khai phần việc `build` trong flutter_frontend/lib/screens/dashboard/organization_structure_graph_responsive.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  Widget build(BuildContext context, WidgetRef ref) {
    final strings = AppStrings.of(context);
    // Lắng nghe provider để widget tự động dựng lại khi dữ liệu hoặc trạng thái thay đổi.

    final statsAsync = ref.watch(orgNodeStatsProvider(person.userId));
    return SingleChildScrollView(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            person.name,
            style: Theme.of(context)
                .textTheme
                .headlineSmall
                ?.copyWith(fontWeight: FontWeight.w800),
          ),
          const SizedBox(height: 6),
          Text(
              '${_roleLabel(person.role, strings)} • ${person.title.isEmpty ? person.username : person.title}'),
          const SizedBox(height: 16),
          statsAsync.when(
            data: (stats) => Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Wrap(
                  spacing: 10,
                  runSpacing: 10,
                  children: [
                    _Metric(
                        label: strings.pick('Mẫu văn bản', 'Templates'),
                        value: '${stats.templateCount}'),
                    _Metric(
                        label: strings.pick('Văn bản', 'Documents'),
                        value: '${stats.documentCount}'),
                    _Metric(
                        label: strings.pick('VB tháng này', 'Docs this month'),
                        value: '${stats.documentsThisMonth}'),
                    _Metric(
                        label: strings.pick(
                            'Nhịp hoạt động 7 ngày', '7-day activity'),
                        value: '${stats.activityTotal}'),
                  ],
                ),
                const SizedBox(height: 14),
                Text(strings.pick('Nhịp hoạt động 7 ngày', '7-day activity'),
                    style: const TextStyle(fontWeight: FontWeight.w700)),
                const SizedBox(height: 8),
                ...stats.activityLast7Days.map(
                  (item) => Padding(
                    padding: const EdgeInsets.only(bottom: 8),
                    child: Row(
                      children: [
                        SizedBox(
                          width: 90,
                          child: Text(item.date.length >= 10
                              ? item.date.substring(5, 10)
                              : item.date),
                        ),
                        Expanded(
                          child: ClipRRect(
                            borderRadius: BorderRadius.circular(999),
                            child: LinearProgressIndicator(
                              minHeight: 10,
                              value: stats.activityTotal == 0
                                  ? 0
                                  : item.count /
                                      math.max(1, stats.activityTotal),
                              backgroundColor: const Color(0xFFE2E8F0),
                            ),
                          ),
                        ),
                        const SizedBox(width: 8),
                        Text('${item.count}'),
                      ],
                    ),
                  ),
                ),
              ],
            ),
            loading: () => const Center(
                child: Padding(
              padding: EdgeInsets.symmetric(vertical: 20),
              child: CircularProgressIndicator(),
            )),
            error: (_, __) => Text(
              strings.pick(
                'Không xem được thông tin chi tiết của user này trong phạm vi quyền hiện tại.',
                'You cannot inspect this user in the current permission scope.',
              ),
            ),
          ),
        ],
      ),
    );
  }
}

// Mục đích: Lớp `_Metric` triển khai phần việc `Metric` trong flutter_frontend/lib/screens/dashboard/organization_structure_graph_responsive.dart.
// Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
// Vai trò trong hệ thống: Đây là lớp thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
// Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

class _Metric extends StatelessWidget {
  final String label;
  final String value;

  const _Metric({required this.label, required this.value});

  @override
  // Mục đích: Phương thức `build` triển khai phần việc `build` trong flutter_frontend/lib/screens/dashboard/organization_structure_graph_responsive.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  Widget build(BuildContext context) {
    return Container(
      width: 150,
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: const Color(0xFFE2E8F0)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(value,
              style:
                  const TextStyle(fontSize: 22, fontWeight: FontWeight.w800)),
          const SizedBox(height: 4),
          Text(label, style: TextStyle(color: Colors.blueGrey.shade700)),
        ],
      ),
    );
  }
}

Color _roleColor(String role) {
  switch (role) {
    case 'admin':
      return const Color(0xFF1D4ED8);
    case 'leader':
      return const Color(0xFF7C3AED);
    case 'employee':
      return const Color(0xFF0F766E);
    default:
      return const Color(0xFF475569);
  }
}

// Mục đích: Hàm `_roleLabel` triển khai phần việc `role Label` trong flutter_frontend/lib/screens/dashboard/organization_structure_graph_responsive.dart.
// Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
// Vai trò trong hệ thống: Đây là hàm thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
// Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

String _roleLabel(String role, AppStrings strings) {
  switch (role) {
    case 'admin':
      return strings.pick('Quản trị viên', 'Administrator');
    case 'leader':
      return strings.pick('Trưởng nhóm', 'Team lead');
    case 'employee':
      return strings.pick('Nhân viên', 'Employee');
    default:
      return strings.pick('Người dùng', 'User');
  }
}
