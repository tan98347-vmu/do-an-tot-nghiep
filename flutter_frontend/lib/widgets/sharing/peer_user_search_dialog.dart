import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../core/iframe_blocker.dart';
import '../../models/company_user_search.dart';
import '../../providers/company_users_search_provider.dart';

class PeerUserSearchDialog extends ConsumerStatefulWidget {
  final Set<int> alreadyInAudience;
  final int? excludeUserId;

  const PeerUserSearchDialog({
    super.key,
    this.alreadyInAudience = const {},
    this.excludeUserId,
  });

  static Future<List<int>?> show(BuildContext context,
      {Set<int> alreadyInAudience = const {}, int? excludeUserId}) {
    return showDialog<List<int>>(
      context: context,
      builder: (_) => PeerUserSearchDialog(
        alreadyInAudience: alreadyInAudience,
        excludeUserId: excludeUserId,
      ),
    );
  }

  @override
  ConsumerState<PeerUserSearchDialog> createState() => _PeerUserSearchDialogState();
}

class _PeerUserSearchDialogState extends ConsumerState<PeerUserSearchDialog> {
  final _searchCtrl = TextEditingController();
  Timer? _debounce;
  String _q = '';
  int? _departmentId;
  String? _position;
  final Set<int> _selected = {};

  @override
  void initState() {
    super.initState();
    pushIframeBlocker();
  }

  @override
  void dispose() {
    popIframeBlocker();
    _searchCtrl.dispose();
    _debounce?.cancel();
    super.dispose();
  }

  void _onSearchChanged(String v) {
    _debounce?.cancel();
    _debounce = Timer(const Duration(milliseconds: 250), () {
      if (mounted) setState(() => _q = v);
    });
  }

  @override
  Widget build(BuildContext context) {
    final filtersAsync = ref.watch(peerSearchFiltersProvider);
    final query = PeerSearchQuery(
      q: _q,
      departmentId: _departmentId,
      position: _position,
    );
    final resultsAsync = ref.watch(companyUsersSearchProvider(query));

    return AlertDialog(
      title: const Row(children: [
        Icon(Icons.person_search, size: 20),
        SizedBox(width: 8),
        Expanded(child: Text('Tìm đồng nghiệp để chia sẻ')),
      ]),
      content: SizedBox(
        width: 580,
        height: 520,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            TextField(
              controller: _searchCtrl,
              decoration: const InputDecoration(
                hintText: 'Tìm theo tên, username, email, chức danh...',
                prefixIcon: Icon(Icons.search, size: 18),
                isDense: true,
                contentPadding: EdgeInsets.symmetric(horizontal: 8, vertical: 10),
                border: OutlineInputBorder(),
              ),
              onChanged: _onSearchChanged,
            ),
            const SizedBox(height: 8),
            filtersAsync.when(
              loading: () => const SizedBox(
                  height: 36, child: Center(child: CircularProgressIndicator(strokeWidth: 2))),
              error: (e, _) => const SizedBox.shrink(),
              data: (filters) => Row(children: [
                Expanded(
                  child: DropdownButtonFormField<int?>(
                    value: _departmentId,
                    isDense: true,
                    isExpanded: true,
                    decoration: const InputDecoration(
                      labelText: 'Phòng ban',
                      border: OutlineInputBorder(),
                      isDense: true,
                      contentPadding: EdgeInsets.symmetric(horizontal: 8, vertical: 6),
                    ),
                    style: const TextStyle(fontSize: 12, color: Colors.black87),
                    items: [
                      const DropdownMenuItem<int?>(
                          value: null, child: Text('Tất cả', style: TextStyle(fontSize: 12))),
                      ...filters.departments.map((d) => DropdownMenuItem<int?>(
                            value: d.id,
                            child: Text(d.name, style: const TextStyle(fontSize: 12)),
                          )),
                    ],
                    onChanged: (v) => setState(() => _departmentId = v),
                  ),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: DropdownButtonFormField<String?>(
                    value: _position,
                    isDense: true,
                    isExpanded: true,
                    decoration: const InputDecoration(
                      labelText: 'Chức danh',
                      border: OutlineInputBorder(),
                      isDense: true,
                      contentPadding: EdgeInsets.symmetric(horizontal: 8, vertical: 6),
                    ),
                    style: const TextStyle(fontSize: 12, color: Colors.black87),
                    items: [
                      const DropdownMenuItem<String?>(
                          value: null, child: Text('Tất cả', style: TextStyle(fontSize: 12))),
                      ...filters.positions.map((p) => DropdownMenuItem<String?>(
                            value: p,
                            child: Text(p, style: const TextStyle(fontSize: 12)),
                          )),
                    ],
                    onChanged: (v) => setState(() => _position = v),
                  ),
                ),
              ]),
            ),
            const SizedBox(height: 8),
            Expanded(
              child: resultsAsync.when(
                loading: () => const Center(child: CircularProgressIndicator()),
                error: (e, _) => Center(
                    child: Text('Lỗi: $e', style: const TextStyle(color: Colors.red))),
                data: (users) {
                  if (users.isEmpty) {
                    return const Center(
                      child: Text('Không tìm thấy người dùng phù hợp.',
                          style: TextStyle(color: Colors.grey)),
                    );
                  }
                  return ListView.separated(
                    itemCount: users.length,
                    separatorBuilder: (_, __) => const Divider(height: 1),
                    itemBuilder: (_, i) {
                      final u = users[i];
                      final isAlready = widget.alreadyInAudience.contains(u.id);
                      final isExcluded = widget.excludeUserId == u.id;
                      final isSelected = _selected.contains(u.id);
                      return CheckboxListTile(
                        value: isSelected,
                        dense: true,
                        controlAffinity: ListTileControlAffinity.leading,
                        title: Row(children: [
                          Expanded(
                            child: Text(
                              u.fullName.isNotEmpty ? u.fullName : u.username,
                              style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 13),
                              overflow: TextOverflow.ellipsis,
                            ),
                          ),
                          if (isAlready)
                            Container(
                              padding: const EdgeInsets.symmetric(horizontal: 5, vertical: 1),
                              decoration: BoxDecoration(
                                color: Colors.green.shade50,
                                borderRadius: BorderRadius.circular(3),
                              ),
                              child: const Text('Đã trong danh sách',
                                  style: TextStyle(fontSize: 9, color: Colors.green)),
                            ),
                        ]),
                        subtitle: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(u.username, style: const TextStyle(fontSize: 11)),
                            if (u.position.isNotEmpty || u.departmentNames.isNotEmpty)
                              Text(
                                [u.position, u.departmentNames].where((s) => s.isNotEmpty).join(' • '),
                                style: const TextStyle(fontSize: 11, color: Colors.grey),
                              ),
                          ],
                        ),
                        onChanged: isExcluded
                            ? null
                            : (v) {
                                setState(() {
                                  if (v == true) {
                                    _selected.add(u.id);
                                  } else {
                                    _selected.remove(u.id);
                                  }
                                });
                              },
                      );
                    },
                  );
                },
              ),
            ),
          ],
        ),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.of(context).pop(),
          child: const Text('Huỷ'),
        ),
        FilledButton.icon(
          icon: const Icon(Icons.check, size: 16),
          label: Text(_selected.isEmpty
              ? 'Chọn người'
              : 'Thêm ${_selected.length} người'),
          onPressed: _selected.isEmpty
              ? null
              : () => Navigator.of(context).pop(_selected.toList()),
        ),
      ],
    );
  }
}
