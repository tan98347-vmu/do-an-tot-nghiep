// === MÀN HÌNH YÊU CẦU PHÊ DUYỆT (đang chờ) ===
// Dành cho trưởng nhóm/admin: liệt kê các mẫu/văn bản/prompt chia sẻ nhóm/công khai đang CHỜ DUYỆT.
// - Dữ liệu lấy qua pendingApprovalsListProvider; lọc theo loại đối tượng (_buildFilterBar, _entityLabel).
// - Mỗi thẻ _PendingCard cho Duyệt/Từ chối: _act() -> _update() gọi API duyệt tương ứng.

// Inbox "Yeu cau chia se cho duyet" - gop tat ca grant pending cho duyet
// tu ca 3 entity (template / document / prompt).

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../models/share_grant.dart';
import '../../providers/sharing_provider.dart';
import '../../widgets/sharing/grant_status_badge.dart';

String _fmtTime(DateTime dt) {
  final l = dt.toLocal();
  // Helper format số về 2 chữ số (dùng hiển thị thời gian).
  String two(int n) => n.toString().padLeft(2, '0');
  return '${two(l.day)}/${two(l.month)}/${l.year} ${two(l.hour)}:${two(l.minute)}';
}

String _entityLabel(String entityType) => switch (entityType) {
      'templates' => 'Mẫu văn bản',
      'documents' => 'Văn bản',
      'prompts' => 'Prompt',
      _ => entityType,
    };

class PendingShareApprovalsScreen extends ConsumerStatefulWidget {
  // Widget màn YÊU CẦU PHÊ DUYỆT đang chờ (mẫu/văn bản/prompt chia sẻ).
  const PendingShareApprovalsScreen({super.key});

  @override
  ConsumerState<PendingShareApprovalsScreen> createState() =>
      _PendingShareApprovalsScreenState();
}

class _PendingShareApprovalsScreenState
    extends ConsumerState<PendingShareApprovalsScreen> {
  final _searchCtrl = TextEditingController();
  PendingApprovalsFilter _filter = const PendingApprovalsFilter();

  // Rời màn: dọn tài nguyên.
  @override
  void dispose() {
    _searchCtrl.dispose();
    super.dispose();
  }

  // Đổi bộ lọc loại đối tượng (mẫu/văn bản/prompt) đang xem.
  void _update(PendingApprovalsFilter next) => setState(() => _filter = next);

  // Dựng màn: thanh lọc + danh sách yêu cầu chờ duyệt (pendingApprovalsListProvider); mỗi mục là _PendingCard.
  @override
  Widget build(BuildContext context) {
    final asyncItems = ref.watch(pendingApprovalsListProvider(_filter));
    return Scaffold(
      appBar: AppBar(title: const Text('Yêu cầu chia sẻ chờ duyệt')),
      body: Column(
        children: [
          _buildFilterBar(),
          const Divider(height: 1),
          Expanded(
            child: asyncItems.when(
              loading: () => const Center(child: CircularProgressIndicator()),
              error: (e, _) => Center(child: Text('Lỗi: $e')),
              data: (items) {
                if (items.isEmpty) {
                  return const Center(
                    child: Text('Không có yêu cầu nào phù hợp.',
                        style: TextStyle(color: Colors.grey)),
                  );
                }
                return RefreshIndicator(
                  onRefresh: () async =>
                      ref.refresh(pendingApprovalsListProvider(_filter).future),
                  child: ListView.builder(
                    itemCount: items.length,
                    itemBuilder: (_, i) => _PendingCard(item: items[i]),
                  ),
                );
              },
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildFilterBar() {
    return Padding(
      padding: const EdgeInsets.fromLTRB(12, 10, 12, 6),
      child: Column(
        children: [
          TextField(
            controller: _searchCtrl,
            decoration: InputDecoration(
              isDense: true,
              hintText: 'Tìm theo tên văn bản / chủ sở hữu...',
              prefixIcon: const Icon(Icons.search, size: 20),
              suffixIcon: _filter.q.isEmpty
                  ? null
                  : IconButton(
                      icon: const Icon(Icons.clear, size: 18),
                      onPressed: () {
                        _searchCtrl.clear();
                        _update(_filter.copyWith(q: ''));
                      },
                    ),
              border: const OutlineInputBorder(),
            ),
            textInputAction: TextInputAction.search,
            onSubmitted: (v) => _update(_filter.copyWith(q: v)),
          ),
          const SizedBox(height: 8),
          Row(
            children: [
              Expanded(
                child: DropdownButtonFormField<String>(
                  value: _filter.entityType,
                  isDense: true,
                  decoration: const InputDecoration(
                    isDense: true,
                    labelText: 'Loại',
                    border: OutlineInputBorder(),
                  ),
                  items: const [
                    DropdownMenuItem(value: '', child: Text('Tất cả')),
                    DropdownMenuItem(value: 'documents', child: Text('Văn bản')),
                    DropdownMenuItem(
                        value: 'templates', child: Text('Mẫu văn bản')),
                    DropdownMenuItem(value: 'prompts', child: Text('Prompt')),
                  ],
                  onChanged: (v) =>
                      _update(_filter.copyWith(entityType: v ?? '')),
                ),
              ),
              const SizedBox(width: 8),
              Expanded(
                child: DropdownButtonFormField<String>(
                  value: _filter.scope,
                  isDense: true,
                  decoration: const InputDecoration(
                    isDense: true,
                    labelText: 'Phạm vi',
                    border: OutlineInputBorder(),
                  ),
                  items: const [
                    DropdownMenuItem(value: '', child: Text('Tất cả')),
                    DropdownMenuItem(value: 'group', child: Text('Nhóm')),
                    DropdownMenuItem(
                        value: 'colleagues', child: Text('Đồng nghiệp')),
                    DropdownMenuItem(value: 'everyone', child: Text('Mọi người')),
                  ],
                  onChanged: (v) => _update(_filter.copyWith(scope: v ?? '')),
                ),
              ),
              const SizedBox(width: 8),
              IconButton(
                tooltip: _filter.sort == 'newest'
                    ? 'Mới nhất trước (bấm để đổi)'
                    : 'Cũ nhất trước (bấm để đổi)',
                icon: Icon(_filter.sort == 'newest'
                    ? Icons.arrow_downward
                    : Icons.arrow_upward),
                onPressed: () => _update(_filter.copyWith(
                    sort: _filter.sort == 'newest' ? 'oldest' : 'newest')),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _PendingCard extends ConsumerStatefulWidget {
  final PendingItem item;
  // Thẻ 1 yêu cầu chờ duyệt: thông tin đối tượng + nút Duyệt / Từ chối.
  const _PendingCard({required this.item});

  @override
  ConsumerState<_PendingCard> createState() => _PendingCardState();
}

class _PendingCardState extends ConsumerState<_PendingCard> {
  final _noteCtrl = TextEditingController();
  bool _busy = false;

  // Duyệt (approve) hoặc Từ chối yêu cầu chia sẻ -> gọi API tương ứng rồi làm mới danh sách.
  Future<void> _act(bool approve) async {
    setState(() => _busy = true);
    final key = SharingKey(widget.item.entityType, widget.item.entityId);
    final actions = SharingActions(ref, key);
    final err = approve
        ? await actions.approveGrant(widget.item.grant.id,
            note: _noteCtrl.text.trim())
        : await actions.rejectGrant(widget.item.grant.id,
            note: _noteCtrl.text.trim());
    if (mounted) {
      setState(() => _busy = false);
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(
        content: Text(err == null
            ? (approve ? 'Đã duyệt' : 'Đã từ chối')
            : 'Thao tác thất bại: $err'),
      ));
      ref.invalidate(pendingApprovalsListProvider);
    }
  }

  @override
  Widget build(BuildContext context) {
    final g = widget.item.grant;
    final target = switch (g.scope) {
      ShareScope.group => g.targetGroup?.name ?? '(nhom)',
      ShareScope.colleagues => g.targetUser?.displayName ?? '(user)',
      ShareScope.everyone => 'Toan bo cong ty',
      ShareScope.private => 'Rieng tu',
    };
    return Card(
      margin: const EdgeInsets.all(8),
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Container(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                  decoration: BoxDecoration(
                    color: Colors.blue.shade50,
                    borderRadius: BorderRadius.circular(4),
                  ),
                  child: Text(
                    _entityLabel(widget.item.entityType),
                    style: TextStyle(
                        color: Colors.blue.shade700,
                        fontSize: 11,
                        fontWeight: FontWeight.bold),
                  ),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(widget.item.entityTitle,
                      style: const TextStyle(fontWeight: FontWeight.bold)),
                ),
                GrantStatusBadge(status: g.approvalStatus),
              ],
            ),
            const SizedBox(height: 8),
            Text('Phạm vi: ${shareScopeLabel(g.scope)} - $target'),
            Text('Quyền: ${sharePermissionLabel(g.permissionLevel)}'),
            if (widget.item.ownerName.isNotEmpty)
              Text('Chủ sở hữu: ${widget.item.ownerName}',
                  style: const TextStyle(fontSize: 12, color: Colors.grey)),
            if (g.submittedBy != null)
              Text('Người yêu cầu: ${g.submittedBy!.displayName}',
                  style: const TextStyle(fontSize: 12, color: Colors.grey)),
            if (widget.item.submittedAt != null)
              Text('Thời gian gửi: ${_fmtTime(widget.item.submittedAt!)}',
                  style: const TextStyle(fontSize: 12, color: Colors.grey)),
            const SizedBox(height: 8),
            TextField(
              controller: _noteCtrl,
              decoration: const InputDecoration(
                labelText: 'Ghi chú (tuỳ chọn)',
                border: OutlineInputBorder(),
                isDense: true,
              ),
              maxLines: 2,
            ),
            const SizedBox(height: 8),
            Row(
              mainAxisAlignment: MainAxisAlignment.end,
              children: [
                TextButton.icon(
                  icon: const Icon(Icons.close, color: Colors.red),
                  label: const Text('Từ chối',
                      style: TextStyle(color: Colors.red)),
                  onPressed: _busy ? null : () => _act(false),
                ),
                const SizedBox(width: 8),
                FilledButton.icon(
                  icon: const Icon(Icons.check),
                  label: const Text('Duyệt'),
                  onPressed: _busy ? null : () => _act(true),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}
