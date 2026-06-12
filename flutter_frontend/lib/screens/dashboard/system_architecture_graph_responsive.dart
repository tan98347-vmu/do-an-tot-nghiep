// === BIỂU ĐỒ KIẾN TRÚC HỆ THỐNG (dashboard) ===
// Vẽ sơ đồ các tầng (Flutter / Django / nginx / Ollama...) bằng CustomPainter (_SysPainter, _SysNodeCard) — minh họa kiến trúc, không gọi API.

// Tệp này dùng để: dựng giao diện và orchestration UI trong flutter_frontend/lib/screens/dashboard/system_architecture_graph_responsive.dart.
import 'package:flutter/material.dart';

import '../../l10n/app_strings.dart';

// Widget SƠ ĐỒ KIẾN TRÚC HỆ THỐNG (StatefulWidget).

class SystemArchitectureGraphResponsive extends StatefulWidget {
  final String currentModel;

  const SystemArchitectureGraphResponsive({
    super.key,
    required this.currentModel,
  });

  @override
  State<SystemArchitectureGraphResponsive> createState() =>
      _SystemArchitectureGraphResponsiveState();
}

// State sơ đồ kiến trúc: bố trí node thành phần + vẽ liên kết.

class _SystemArchitectureGraphResponsiveState
    extends State<SystemArchitectureGraphResponsive> {
  final TransformationController _controller = TransformationController();
  String _selectedNodeId = 'django_api';

  List<_GraphNode> _nodes(AppStrings strings) => [
        _GraphNode(
          'flutter_web',
          'Flutter Web',
          strings.pick('Giao diện chính', 'Primary frontend'),
          const Offset(60, 140),
          const Color(0xFF0F766E),
        ),
        _GraphNode(
          'guest',
          'Guest Portal',
          strings.pick('Luồng khách', 'Guest flow'),
          const Offset(60, 380),
          const Color(0xFF0891B2),
        ),
        _GraphNode(
          'auth',
          'Auth & Permission',
          strings.pick('JWT và phân quyền', 'JWT and authorization'),
          const Offset(380, 90),
          const Color(0xFF2563EB),
        ),
        _GraphNode(
          'django_api',
          'Django API',
          strings.pick('Trục điều phối', 'Orchestration core'),
          const Offset(380, 270),
          const Color(0xFF1D4ED8),
        ),
        _GraphNode(
          'admin',
          'Admin & Import',
          strings.pick('Vận hành và sao lưu', 'Operations and backup'),
          const Offset(380, 560),
          const Color(0xFF7C3AED),
        ),
        _GraphNode(
          'business',
          'Templates & Documents',
          strings.pick('Nghiệp vụ tài liệu', 'Document business layer'),
          const Offset(740, 150),
          const Color(0xFFB45309),
        ),
        _GraphNode(
          'ai',
          'AI Orchestrator',
          widget.currentModel.isEmpty
              ? 'Chat / RAG / AI doc'
              : 'Chat / RAG / AI doc | ${widget.currentModel}',
          const Offset(740, 400),
          const Color(0xFFBE123C),
        ),
        _GraphNode(
          'pipeline',
          'DOCX / PDF',
          strings.pick('Đọc và xuất file', 'Read and export files'),
          const Offset(1080, 150),
          const Color(0xFF0F766E),
        ),
        _GraphNode(
          'postgres',
          'PostgreSQL',
          strings.pick('Dữ liệu giao dịch', 'Transactional data'),
          const Offset(1080, 430),
          const Color(0xFF475569),
        ),
        _GraphNode(
          'models',
          'Ollama / Models',
          strings.pick('LLM và embedding', 'LLM and embeddings'),
          const Offset(1410, 120),
          const Color(0xFFEA580C),
        ),
        _GraphNode(
          'vector',
          'PGVector',
          strings.pick('Kho tri thức', 'Knowledge base'),
          const Offset(1410, 320),
          const Color(0xFFDC2626),
        ),
      ];

  List<_GraphEdge> get _edges => const [
        _GraphEdge('flutter_web', 'auth'),
        _GraphEdge('flutter_web', 'django_api'),
        _GraphEdge('guest', 'django_api'),
        _GraphEdge('auth', 'django_api'),
        _GraphEdge('django_api', 'business'),
        _GraphEdge('django_api', 'admin'),
        _GraphEdge('django_api', 'ai'),
        _GraphEdge('django_api', 'pipeline'),
        _GraphEdge('business', 'postgres'),
        _GraphEdge('admin', 'postgres'),
        _GraphEdge('pipeline', 'postgres'),
        _GraphEdge('ai', 'models'),
        _GraphEdge('ai', 'vector'),
        _GraphEdge('ai', 'postgres'),
        _GraphEdge('vector', 'postgres'),
      ];

  @override
  // Rời màn: dọn tài nguyên.

  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  // Dựng sơ đồ kiến trúc: node thành phần + cạnh liên kết + chú thích.

  Widget build(BuildContext context) {
    final strings = AppStrings.of(context);
    final nodes = _nodes(strings);
    final isCompact = MediaQuery.sizeOf(context).width < 900;
    final selected = nodes.firstWhere((node) => node.id == _selectedNodeId);
    final related = _edges
        .where((edge) =>
            edge.from == _selectedNodeId || edge.to == _selectedNodeId)
        .expand((edge) => [edge.from, edge.to])
        .where((id) => id != _selectedNodeId)
        .toSet();

    return Card(
      child: Padding(
        padding: EdgeInsets.all(isCompact ? 14 : 20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              strings.ui('Bản đồ hệ thống'),
              style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                    fontWeight: FontWeight.w800,
                  ),
            ),
            const SizedBox(height: 8),
            Text(
              strings.pick(
                'Pan, zoom và chạm vào node để xem thành phần chính, mối nối và công nghệ đang dùng.',
                'Pan, zoom, and tap a node to inspect the main components, links, and technologies in use.',
              ),
            ),
            const SizedBox(height: 12),
            Wrap(
              spacing: 10,
              runSpacing: 10,
              children: [
                _SysLegend(strings.ui('Giao diện'), const Color(0xFF0F766E)),
                const _SysLegend('Backend', Color(0xFF1D4ED8)),
                const _SysLegend('AI', Color(0xFFBE123C)),
                _SysLegend(strings.pick('Lưu trữ', 'Storage'),
                    const Color(0xFF475569)),
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
              height: isCompact ? 420 : 580,
              decoration: BoxDecoration(
                color: const Color(0xFF0F172A),
                borderRadius: BorderRadius.circular(24),
              ),
              child: ClipRRect(
                borderRadius: BorderRadius.circular(24),
                child: InteractiveViewer(
                  constrained: false,
                  minScale: 0.5,
                  maxScale: 1.9,
                  boundaryMargin: const EdgeInsets.all(180),
                  transformationController: _controller,
                  child: SizedBox(
                    width: 1680,
                    height: 980,
                    child: Stack(
                      children: [
                        CustomPaint(
                          size: const Size(1680, 980),
                          painter: _SysPainter(
                            nodes: nodes,
                            edges: _edges,
                            selectedNodeId: _selectedNodeId,
                          ),
                        ),
                        for (final node in nodes)
                          Positioned(
                            left: node.position.dx,
                            top: node.position.dy,
                            child: _SysNodeCard(
                              node: node,
                              selected: node.id == _selectedNodeId,
                              related: related.contains(node.id),
                              // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

                              onTap: () =>
                                  setState(() => _selectedNodeId = node.id),
                            ),
                          ),
                      ],
                    ),
                  ),
                ),
              ),
            ),
            const SizedBox(height: 14),
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: const Color(0xFFF8FAFC),
                borderRadius: BorderRadius.circular(18),
                border: Border.all(color: const Color(0xFFE2E8F0)),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    selected.title,
                    style: const TextStyle(
                        fontSize: 18, fontWeight: FontWeight.w800),
                  ),
                  const SizedBox(height: 6),
                  Text(selected.subtitle),
                  const SizedBox(height: 10),
                  Wrap(
                    spacing: 10,
                    runSpacing: 10,
                    children: related
                        .map((id) =>
                            nodes.firstWhere((node) => node.id == id).title)
                        .map((title) => Chip(label: Text(title)))
                        .toList(),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

// Mô hình 1 node thành phần trong sơ đồ kiến trúc.

class _GraphNode {
  final String id;
  final String title;
  final String subtitle;
  final Offset position;
  final Color color;

  const _GraphNode(
      this.id, this.title, this.subtitle, this.position, this.color);
}

// Mô hình 1 cạnh liên kết giữa hai thành phần.

class _GraphEdge {
  final String from;
  final String to;

  const _GraphEdge(this.from, this.to);
}

// Thẻ 1 node thành phần hệ thống.

class _SysNodeCard extends StatelessWidget {
  final _GraphNode node;
  final bool selected;
  final bool related;
  final VoidCallback onTap;

  const _SysNodeCard({
    required this.node,
    required this.selected,
    required this.related,
    required this.onTap,
  });

  @override
  // Dựng thẻ node thành phần.

  Widget build(BuildContext context) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(22),
      child: Container(
        width: 240,
        height: 118,
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          color:
              node.color.withOpacity(selected ? 0.30 : (related ? 0.22 : 0.16)),
          borderRadius: BorderRadius.circular(22),
          border: Border.all(
            color: selected ? node.color : Colors.white.withOpacity(0.12),
            width: selected ? 2 : 1,
          ),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              node.title,
              style: const TextStyle(
                  fontSize: 18,
                  fontWeight: FontWeight.w800,
                  color: Colors.white),
            ),
            const SizedBox(height: 8),
            Text(node.subtitle,
                style: const TextStyle(color: Colors.white70, height: 1.4)),
          ],
        ),
      ),
    );
  }
}

// Bộ vẽ các cạnh liên kết của sơ đồ kiến trúc (CustomPainter).

class _SysPainter extends CustomPainter {
  final List<_GraphNode> nodes;
  final List<_GraphEdge> edges;
  final String selectedNodeId;

  const _SysPainter({
    required this.nodes,
    required this.edges,
    required this.selectedNodeId,
  });

  @override
  // Vẽ toàn bộ cạnh liên kết.

  void paint(Canvas canvas, Size size) {
    final map = {for (final node in nodes) node.id: node};
    for (final edge in edges) {
      final from = map[edge.from];
      final to = map[edge.to];
      if (from == null || to == null) continue;
      final start = Offset(from.position.dx + 120, from.position.dy + 59);
      final end = Offset(to.position.dx + 120, to.position.dy + 59);
      final path = Path()
        ..moveTo(start.dx, start.dy)
        ..cubicTo(start.dx + (end.dx - start.dx) * 0.28, start.dy,
            end.dx - (end.dx - start.dx) * 0.28, end.dy, end.dx, end.dy);
      final selected = edge.from == selectedNodeId || edge.to == selectedNodeId;
      final paint = Paint()
        ..style = PaintingStyle.stroke
        ..strokeWidth = selected ? 2.2 : 1.2
        ..color = Colors.white.withOpacity(selected ? 0.76 : 0.26);
      canvas.drawPath(path, paint);
    }
  }

  @override
  // Có cần vẽ lại sơ đồ không.

  bool shouldRepaint(covariant _SysPainter oldDelegate) =>
      oldDelegate.selectedNodeId != selectedNodeId;
}

// Chú thích sơ đồ kiến trúc.

class _SysLegend extends StatelessWidget {
  final String label;
  final Color color;

  const _SysLegend(this.label, this.color);

  @override
  // Dựng chú thích.

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
