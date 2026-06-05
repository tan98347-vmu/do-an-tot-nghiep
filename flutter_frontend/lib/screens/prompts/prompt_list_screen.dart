import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/api_client.dart';
import '../../core/debouncer.dart';
import '../../providers/prompts_provider.dart';
import '../../providers/recent_prompts_provider.dart';
import '../../widgets/common/collapsible_filter_panel.dart';
import '../../widgets/common/view_mode_toggle.dart';

class PromptListScreen extends ConsumerStatefulWidget {
  final String? groupParam;

  const PromptListScreen({super.key, this.groupParam});

  @override
  ConsumerState<PromptListScreen> createState() => _PromptListScreenState();
}

class _PromptListScreenState extends ConsumerState<PromptListScreen> {
  final _searchCtrl = TextEditingController();
  final _searchDebouncer = Debouncer();

  String _searchQuery = '';
  String _statusFilter = '';
  String _visibilityFilter = '';
  String _ownerFilter = 'all';
  String _sourceFilter = '';
  String _scopeFilter = '';
  String _sortFilter = 'updated_desc';
  DateTime? _createdFrom;
  DateTime? _createdTo;
  bool _reviewMode = false;
  bool _peerSharedMode = false;
  String? _lastGroupParam;

  // Dong bo voi man Mau/Van ban: che do xem (the/danh sach) + chon & xoa hang loat.
  String _viewMode = 'list';
  final Set<int> _selectedPromptIds = {};
  bool _bulkDeleting = false;

  @override
  void initState() {
    super.initState();
    _applyGroupParam(widget.groupParam);
  }

  @override
  void didUpdateWidget(covariant PromptListScreen oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (widget.groupParam != _lastGroupParam) {
      _applyGroupParam(widget.groupParam);
    }
  }

  void _applyGroupParam(String? param) {
    _lastGroupParam = param;
    _searchDebouncer.cancel();
    _searchCtrl.clear();
    setState(() {
      _searchQuery = '';
      _statusFilter = '';
      _visibilityFilter = '';
      _ownerFilter = 'all';
      _sourceFilter = '';
      _scopeFilter = '';
      _sortFilter = 'updated_desc';
      _createdFrom = null;
      _createdTo = null;
      _reviewMode = false;
      _peerSharedMode = false;
      switch (param) {
        case 'private':
          _visibilityFilter = 'private';
          _ownerFilter = 'mine';
          break;
        case 'group':
          _visibilityFilter = 'group';
          break;
        case 'public':
          _visibilityFilter = 'public';
          break;
        case 'review':
          _reviewMode = true;
          break;
        case 'peer':
          _peerSharedMode = true;
          _ownerFilter = 'shared';
          break;
        case 'admin':
          break;
        default:
          break;
      }
    });
  }

  String _headerLabel() {
    switch (widget.groupParam) {
      case 'private':
        return 'Prompt riêng của tôi';
      case 'group':
        return 'Prompt phòng ban';
      case 'public':
        return 'Prompt dùng chung';
      case 'review':
        return 'Prompt cần duyệt';
      case 'peer':
        return 'Prompt chia sẻ cho đồng nghiệp';
      case 'admin':
        return 'Tất cả prompt (Admin)';
      default:
        return 'Quản lý Prompt';
    }
  }

  @override
  void dispose() {
    _searchDebouncer.cancel();
    _searchCtrl.dispose();
    super.dispose();
  }

  PromptListQuery _buildQuery() {
    return PromptListQuery(
      scopes: _scopeFilter.isEmpty ? const [] : [_scopeFilter],
      owner: _ownerFilter,
      status: _statusFilter,
      q: _searchQuery,
      visibility: _visibilityFilter,
      source: _sourceFilter,
      createdFrom: _createdFrom,
      createdTo: _createdTo,
      sort: _sortFilter,
      reviewMode: _reviewMode,
      sharedWithMe: _peerSharedMode,
    );
  }

  Color _statusColor(String s) => switch (s) {
        'approved' => Colors.green,
        'pending' => Colors.orange,
        'pending_leader' => Colors.deepOrange,
        'rejected' => Colors.red,
        _ => Colors.grey,
      };

  Color _visColor(String v) => switch (v) {
        'public' => Colors.green,
        'group' => Colors.blue,
        _ => Colors.grey,
      };

  Future<void> _approve(PromptRecord prompt) async {
    try {
      await ApiClient().dio.post('prompts/${prompt.id}/approve/');
      _invalidateLists();
      _snack('Đã duyệt prompt.');
    } on DioException catch (error) {
      _snack('Lỗi: ${error.response?.data?['detail'] ?? error.message}');
    }
  }

  Future<void> _reject(PromptRecord prompt) async {
    final note = await _askReason(
      title: 'Từ chối prompt',
      label: 'Lý do từ chối *',
    );
    if (note == null) return;

    try {
      await ApiClient().dio.post(
        'prompts/${prompt.id}/reject/',
        data: {'note': note},
      );
      _invalidateLists();
      _snack('Đã từ chối prompt.');
    } on DioException catch (error) {
      _snack('Lỗi: ${error.response?.data?['detail'] ?? error.message}');
    }
  }

  Future<void> _submit(PromptRecord prompt) async {
    try {
      await ApiClient().dio.post('prompts/${prompt.id}/submit/');
      _invalidateLists();
      _snack('Đã gửi duyệt.');
    } on DioException catch (error) {
      _snack('Lỗi: ${error.response?.data?['detail'] ?? error.message}');
    }
  }

  Future<void> _delete(PromptRecord prompt) async {
    final ok = await showDialog<bool>(
      context: context,
      builder: (_) => AlertDialog(
        title: const Text('Xóa prompt?'),
        content: Text('Xóa "${prompt.title}"? Hành động này không thể hoàn tác.'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Hủy'),
          ),
          FilledButton(
            style: FilledButton.styleFrom(backgroundColor: Colors.red),
            onPressed: () => Navigator.pop(context, true),
            child: const Text('Xóa'),
          ),
        ],
      ),
    );
    if (ok != true) return;
    try {
      await ApiClient().dio.delete('prompts/${prompt.id}/');
      _invalidateLists();
      ref.invalidate(recentPromptsProvider);
      _snack('Đã xóa prompt.');
    } on DioException catch (error) {
      _snack('Lỗi: ${error.response?.data?['detail'] ?? error.message}');
    }
  }

  bool _canDeletePrompt(PromptRecord p) => p.canDelete;

  void _toggleSelectAllPrompts(List<PromptRecord> prompts) {
    final deletable = prompts.where(_canDeletePrompt).toList();
    final allSelected = deletable.isNotEmpty &&
        deletable.every((p) => _selectedPromptIds.contains(p.id));
    setState(() {
      if (allSelected) {
        _selectedPromptIds.clear();
      } else {
        _selectedPromptIds
          ..clear()
          ..addAll(deletable.map((p) => p.id));
      }
    });
  }

  Future<void> _bulkDeletePrompts() async {
    if (_selectedPromptIds.isEmpty) return;
    final count = _selectedPromptIds.length;
    final ok = await showDialog<bool>(
      context: context,
      builder: (_) => AlertDialog(
        title: const Text('Xác nhận xóa hàng loạt'),
        content: Text(
            'Xóa $count prompt đã chọn? Hành động này không thể hoàn tác.'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Hủy'),
          ),
          FilledButton(
            style: FilledButton.styleFrom(backgroundColor: Colors.red),
            onPressed: () => Navigator.pop(context, true),
            child: const Text('Xóa'),
          ),
        ],
      ),
    );
    if (ok != true) return;
    setState(() => _bulkDeleting = true);
    var success = 0;
    final failures = <String>[];
    for (final id in _selectedPromptIds.toList()) {
      try {
        await ApiClient().dio.delete('prompts/$id/');
        success++;
      } on DioException catch (e) {
        failures.add(
            e.response?.data?['detail']?.toString() ?? e.message ?? 'Loi');
      }
    }
    if (!mounted) return;
    setState(() {
      _selectedPromptIds.clear();
      _bulkDeleting = false;
    });
    _invalidateLists();
    ref.invalidate(recentPromptsProvider);
    _snack(failures.isEmpty
        ? 'Đã xóa $success prompt.'
        : 'Đã xóa $success prompt, ${failures.length} thất bại.');
  }

  Future<String?> _askReason({
    required String title,
    required String label,
  }) async {
    final noteCtrl = TextEditingController();
    final ok = await showDialog<bool>(
      context: context,
      builder: (_) => AlertDialog(
        title: Text(title),
        content: TextField(
          controller: noteCtrl,
          minLines: 2,
          maxLines: 5,
          decoration: InputDecoration(
            labelText: label,
            border: const OutlineInputBorder(),
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Hủy'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(context, true),
            child: const Text('Xác nhận'),
          ),
        ],
      ),
    );
    if (ok != true) return null;
    final note = noteCtrl.text.trim();
    if (note.isEmpty) {
      _snack('Phải nhập lý do.');
      return null;
    }
    return note;
  }

  void _invalidateLists() {
    ref.invalidate(promptsProvider);
    ref.invalidate(promptsPendingReviewProvider);
    ref.invalidate(promptQueryProvider(_buildQuery()));
  }

  void _snack(String message) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(message)),
    );
  }

  Widget _badge(String label, Color color) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(4),
      ),
      child: Text(
        label,
        style: TextStyle(
          fontSize: 10.5,
          color: color,
          fontWeight: FontWeight.w600,
        ),
      ),
    );
  }

  bool _hasActiveFilter() {
    return _searchQuery.isNotEmpty ||
        _statusFilter.isNotEmpty ||
        _visibilityFilter.isNotEmpty ||
        _ownerFilter != 'all' ||
        _sourceFilter.isNotEmpty ||
        _scopeFilter.isNotEmpty ||
        _createdFrom != null ||
        _createdTo != null ||
        _sortFilter != 'updated_desc';
  }

  void _resetFilters() {
    setState(() {
      _searchDebouncer.cancel();
      _searchCtrl.clear();
      _searchQuery = '';
      _statusFilter = '';
      _visibilityFilter = switch (widget.groupParam) {
        'private' => 'private',
        'group' => 'group',
        'public' => 'public',
        _ => '',
      };
      _ownerFilter = switch (widget.groupParam) {
        'private' => 'mine',
        'peer' => 'shared',
        _ => 'all',
      };
      _sourceFilter = '';
      _scopeFilter = '';
      _sortFilter = 'updated_desc';
      _createdFrom = null;
      _createdTo = null;
    });
  }

  String _formatDate(DateTime? value) {
    if (value == null) return 'Tất cả';
    final yyyy = value.year.toString().padLeft(4, '0');
    final mm = value.month.toString().padLeft(2, '0');
    final dd = value.day.toString().padLeft(2, '0');
    return '$dd/$mm/$yyyy';
  }

  Future<void> _pickDate({
    required bool isStart,
  }) async {
    final current = isStart ? _createdFrom : _createdTo;
    final selected = await showDatePicker(
      context: context,
      initialDate: current ?? DateTime.now(),
      firstDate: DateTime(2020),
      lastDate: DateTime(2100),
    );
    if (selected == null) return;
    setState(() {
      if (isStart) {
        _createdFrom = selected;
      } else {
        _createdTo = selected;
      }
    });
  }

  Widget _buildItem(
    PromptRecord prompt, {
    bool compact = false,
    bool selectable = false,
    bool selected = false,
    ValueChanged<bool>? onSelectedChanged,
  }) {
    final titleSize = compact ? 13.0 : 14.0;
    final bodySize = compact ? 11.5 : 12.0;
    final metaSize = compact ? 10.5 : 11.0;
    final createdLabel = prompt.createdAt.isNotEmpty
        ? prompt.createdAt.replaceFirst('T', ' ').substring(
              0,
              prompt.createdAt.length >= 16 ? 16 : prompt.createdAt.length,
            )
        : '';
    final updatedLabel = prompt.updatedAt.isNotEmpty
        ? prompt.updatedAt.replaceFirst('T', ' ').substring(
              0,
              prompt.updatedAt.length >= 16 ? 16 : prompt.updatedAt.length,
            )
        : '';
    return Card(
      margin: EdgeInsets.only(bottom: compact ? 6 : 8),
      child: InkWell(
        onTap: prompt.canEdit ? () => context.go('/prompts/${prompt.id}/edit') : null,
        child: Padding(
          padding: EdgeInsets.symmetric(
            horizontal: compact ? 10 : 14,
            vertical: compact ? 8 : 10,
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  if (selectable)
                    SizedBox(
                      width: 28,
                      child: Checkbox(
                        value: selected,
                        visualDensity: VisualDensity.compact,
                        materialTapTargetSize:
                            MaterialTapTargetSize.shrinkWrap,
                        onChanged: (v) => onSelectedChanged?.call(v ?? false),
                      ),
                    ),
                  Icon(Icons.bolt, color: Colors.orange, size: compact ? 18 : 20),
                  const SizedBox(width: 6),
                  Expanded(
                    child: Text(
                      prompt.title,
                      style: TextStyle(
                        fontWeight: FontWeight.bold,
                        fontSize: titleSize,
                      ),
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
                  PopupMenuButton<String>(
                    icon: const Icon(Icons.more_vert, size: 20),
                    padding: EdgeInsets.zero,
                    onSelected: (value) {
                      switch (value) {
                        case 'edit':
                          context.go('/prompts/${prompt.id}/edit');
                          break;
                        case 'submit':
                          _submit(prompt);
                          break;
                        case 'approve':
                          _approve(prompt);
                          break;
                        case 'reject':
                          _reject(prompt);
                          break;
                        case 'delete':
                          _delete(prompt);
                          break;
                      }
                    },
                    itemBuilder: (_) => [
                      if (prompt.canEdit)
                        const PopupMenuItem(
                          value: 'edit',
                          child: ListTile(
                            dense: true,
                            leading: Icon(Icons.edit),
                            title: Text('Sửa'),
                          ),
                        ),
                      if (prompt.canEdit &&
                          (prompt.status == 'rejected' ||
                              prompt.status == 'pending' ||
                              prompt.status == 'pending_leader'))
                        const PopupMenuItem(
                          value: 'submit',
                          child: ListTile(
                            dense: true,
                            leading: Icon(Icons.send),
                            title: Text('Gửi duyệt lại'),
                          ),
                        ),
                      if (prompt.canApprove &&
                          (prompt.status == 'pending' ||
                              prompt.status == 'pending_leader')) ...[
                        const PopupMenuItem(
                          value: 'approve',
                          child: ListTile(
                            dense: true,
                            leading: Icon(Icons.check, color: Colors.green),
                            title: Text('Duyệt'),
                          ),
                        ),
                        const PopupMenuItem(
                          value: 'reject',
                          child: ListTile(
                            dense: true,
                            leading: Icon(Icons.close, color: Colors.red),
                            title: Text('Từ chối'),
                          ),
                        ),
                      ],
                      if (prompt.canDelete)
                        const PopupMenuItem(
                          value: 'delete',
                          child: ListTile(
                            dense: true,
                            leading: Icon(Icons.delete, color: Colors.red),
                            title: Text('Xóa'),
                          ),
                        ),
                    ],
                  ),
                ],
              ),
              const SizedBox(height: 4),
              Wrap(
                spacing: 4,
                runSpacing: 4,
                children: [
                  _badge(prompt.visibilityLabel, _visColor(prompt.visibility)),
                  _badge(prompt.statusLabel, _statusColor(prompt.status)),
                  _badge(prompt.sourceLabel, Colors.indigo),
                  ...prompt.usageScopes
                      .take(3)
                      .map(
                        (scope) => _badge(
                          promptScopeLabels[scope] ?? scope,
                          Colors.teal,
                        ),
                      ),
                ],
              ),
              if ((prompt.rulesContent ?? '').isNotEmpty) ...[
                const SizedBox(height: 6),
                Text(
                  prompt.rulesContent!,
                  maxLines: compact ? 2 : 3,
                  overflow: TextOverflow.ellipsis,
                  style: TextStyle(fontSize: bodySize),
                ),
              ],
              const SizedBox(height: 8),
              DefaultTextStyle(
                style: TextStyle(fontSize: metaSize, color: Colors.grey),
                child: Wrap(
                  spacing: 10,
                  runSpacing: 3,
                  children: [
                    Text('Bởi: ${prompt.ownerName}'),
                    if (prompt.groupName != null) Text('Nhóm: ${prompt.groupName}'),
                    if (prompt.categoryName != null)
                      Text('Danh mục: ${prompt.categoryName}'),
                    Text('Nguồn: ${prompt.sourceLabel}'),
                    if (prompt.tags != null && prompt.tags!.isNotEmpty)
                      Text('Tag: ${prompt.tags}'),
                    Text('Tạo: $createdLabel'),
                    if (updatedLabel.isNotEmpty) Text('Cập nhật: $updatedLabel'),
                  ],
                ),
              ),
              if (prompt.status == 'rejected' &&
                  (prompt.approverNote ?? '').isNotEmpty)
                Container(
                  margin: const EdgeInsets.only(top: 6),
                  padding: const EdgeInsets.all(6),
                  decoration: BoxDecoration(
                    color: Colors.red.shade50,
                    borderRadius: BorderRadius.circular(4),
                  ),
                  child: Text(
                    'Lý do từ chối: ${prompt.approverNote}',
                    style: TextStyle(fontSize: metaSize, color: Colors.red),
                  ),
                ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _searchField({bool compact = false}) {
    return TextField(
      controller: _searchCtrl,
      decoration: InputDecoration(
        hintText: 'Tìm theo tên, phạm vi, nguồn, danh mục, người tạo...',
        prefixIcon: const Icon(Icons.search, size: 18),
        suffixIcon: _searchCtrl.text.isEmpty
            ? null
            : IconButton(
                icon: const Icon(Icons.clear, size: 16),
                onPressed: () {
                  _searchDebouncer.cancel();
                  setState(() {
                    _searchCtrl.clear();
                    _searchQuery = '';
                  });
                },
              ),
        isDense: true,
        contentPadding: EdgeInsets.symmetric(
          horizontal: 10,
          vertical: compact ? 10 : 12,
        ),
        border: const OutlineInputBorder(),
      ),
      onChanged: (value) {
        _searchDebouncer.run(const Duration(milliseconds: 300), () {
          if (!mounted) return;
          setState(() => _searchQuery = value.trim());
        });
      },
    );
  }

  Widget _statusDropdown() {
    return DropdownButtonFormField<String>(
      initialValue: _statusFilter.isEmpty ? 'all' : _statusFilter,
      isDense: true,
      isExpanded: true,
      decoration: const InputDecoration(
        labelText: 'Trạng thái',
        border: OutlineInputBorder(),
        isDense: true,
      ),
      items: const [
        DropdownMenuItem(value: 'all', child: Text('Tất cả')),
        DropdownMenuItem(value: 'approved', child: Text('Đã duyệt')),
        DropdownMenuItem(value: 'pending', child: Text('Chờ admin duyệt')),
        DropdownMenuItem(
          value: 'pending_leader',
          child: Text('Chờ trưởng nhóm duyệt'),
        ),
        DropdownMenuItem(value: 'rejected', child: Text('Bị từ chối')),
      ],
      onChanged: (value) {
        setState(() => _statusFilter = value == 'all' ? '' : (value ?? ''));
      },
    );
  }

  Widget _visibilityDropdown() {
    return DropdownButtonFormField<String>(
      initialValue: _visibilityFilter.isEmpty ? 'all' : _visibilityFilter,
      isDense: true,
      isExpanded: true,
      decoration: const InputDecoration(
        labelText: 'Phạm vi',
        border: OutlineInputBorder(),
        isDense: true,
      ),
      items: const [
        DropdownMenuItem(value: 'all', child: Text('Tất cả')),
        DropdownMenuItem(value: 'private', child: Text('Riêng tư')),
        DropdownMenuItem(value: 'group', child: Text('Phòng ban')),
        DropdownMenuItem(value: 'public', child: Text('Công khai')),
      ],
      onChanged: (value) {
        setState(() => _visibilityFilter = value == 'all' ? '' : (value ?? ''));
      },
    );
  }

  Widget _ownerDropdown() {
    return DropdownButtonFormField<String>(
      initialValue: _ownerFilter,
      isDense: true,
      isExpanded: true,
      decoration: const InputDecoration(
        labelText: 'Chủ sở hữu',
        border: OutlineInputBorder(),
        isDense: true,
      ),
      items: const [
        DropdownMenuItem(value: 'all', child: Text('Tất cả')),
        DropdownMenuItem(value: 'mine', child: Text('Của tôi')),
        DropdownMenuItem(value: 'shared', child: Text('Được chia sẻ')),
      ],
      onChanged: (value) {
        setState(() => _ownerFilter = value ?? 'all');
      },
    );
  }

  Widget _sourceDropdown() {
    return DropdownButtonFormField<String>(
      initialValue: _sourceFilter.isEmpty ? 'all' : _sourceFilter,
      isDense: true,
      isExpanded: true,
      decoration: const InputDecoration(
        labelText: 'Nguồn',
        border: OutlineInputBorder(),
        isDense: true,
      ),
      items: const [
        DropdownMenuItem(value: 'all', child: Text('Tất cả')),
        DropdownMenuItem(value: 'curated', child: Text('Curated')),
        DropdownMenuItem(value: 'user_inline', child: Text('Người dùng tạo')),
        DropdownMenuItem(value: 'imported', child: Text('Import')),
      ],
      onChanged: (value) {
        setState(() => _sourceFilter = value == 'all' ? '' : (value ?? ''));
      },
    );
  }

  Widget _scopeDropdown() {
    return DropdownButtonFormField<String>(
      initialValue: _scopeFilter.isEmpty ? 'all' : _scopeFilter,
      isDense: true,
      isExpanded: true,
      decoration: const InputDecoration(
        labelText: 'Thuộc phần nào',
        border: OutlineInputBorder(),
        isDense: true,
      ),
      items: [
        const DropdownMenuItem(value: 'all', child: Text('Tất cả')),
        ...promptScopeLabels.entries.map(
          (entry) => DropdownMenuItem(
            value: entry.key,
            child: Text(entry.value),
          ),
        ),
      ],
      onChanged: (value) {
        setState(() => _scopeFilter = value == 'all' ? '' : (value ?? ''));
      },
    );
  }

  Widget _sortDropdown() {
    return DropdownButtonFormField<String>(
      initialValue: _sortFilter,
      isDense: true,
      isExpanded: true,
      decoration: const InputDecoration(
        labelText: 'Sắp xếp',
        border: OutlineInputBorder(),
        isDense: true,
      ),
      items: const [
        DropdownMenuItem(
          value: 'updated_desc',
          child: Text('Mới cập nhật'),
        ),
        DropdownMenuItem(
          value: 'created_desc',
          child: Text('Mới tạo'),
        ),
        DropdownMenuItem(
          value: 'title_asc',
          child: Text('Ten A-Z'),
        ),
        DropdownMenuItem(
          value: 'usage_desc',
          child: Text('Dùng nhiều nhất'),
        ),
      ],
      onChanged: (value) {
        setState(() => _sortFilter = value ?? 'updated_desc');
      },
    );
  }

  Widget _dateField({
    required String label,
    required DateTime? value,
    required VoidCallback onPick,
    required VoidCallback onClear,
  }) {
    return InkWell(
      onTap: onPick,
      child: InputDecorator(
        decoration: InputDecoration(
          labelText: label,
          border: const OutlineInputBorder(),
          suffixIcon: value == null
              ? const Icon(Icons.event_outlined)
              : IconButton(
                  icon: const Icon(Icons.clear),
                  onPressed: onClear,
                ),
        ),
        child: Text(_formatDate(value)),
      ),
    );
  }

  Widget _mobileFilterBar() {
    return Card(
      margin: EdgeInsets.zero,
      child: ExpansionTile(
        tilePadding: const EdgeInsets.symmetric(horizontal: 10),
        leading: const Icon(Icons.filter_list, size: 18),
        title: Row(
          children: [
            const Text(
              'Bộ lọc',
              style: TextStyle(fontSize: 13, fontWeight: FontWeight.w600),
            ),
            const SizedBox(width: 8),
            if (_hasActiveFilter())
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 1),
                decoration: BoxDecoration(
                  color: Colors.blue,
                  borderRadius: BorderRadius.circular(8),
                ),
                child: const Text(
                  'Đang áp dụng',
                  style: TextStyle(fontSize: 10, color: Colors.white),
                ),
              ),
          ],
        ),
        childrenPadding: const EdgeInsets.fromLTRB(10, 0, 10, 10),
        children: [
          _searchField(compact: true),
          const SizedBox(height: 8),
          _statusDropdown(),
          const SizedBox(height: 8),
          _visibilityDropdown(),
          const SizedBox(height: 8),
          _ownerDropdown(),
          const SizedBox(height: 8),
          _sourceDropdown(),
          const SizedBox(height: 8),
          _scopeDropdown(),
          const SizedBox(height: 8),
          _sortDropdown(),
          const SizedBox(height: 8),
          _dateField(
            label: 'Tạo từ ngày',
            value: _createdFrom,
            onPick: () => _pickDate(isStart: true),
            onClear: () => setState(() => _createdFrom = null),
          ),
          const SizedBox(height: 8),
          _dateField(
            label: 'Tạo đến ngày',
            value: _createdTo,
            onPick: () => _pickDate(isStart: false),
            onClear: () => setState(() => _createdTo = null),
          ),
          if (_hasActiveFilter()) ...[
            const SizedBox(height: 4),
            Align(
              alignment: Alignment.centerRight,
              child: TextButton.icon(
                onPressed: _resetFilters,
                icon: const Icon(Icons.filter_alt_off, size: 14),
                label: const Text('Xóa bộ lọc'),
              ),
            ),
          ],
        ],
      ),
    );
  }

  Widget _desktopFilterBar() {
    return Column(
      children: [
        Row(
          children: [
            Expanded(flex: 3, child: _searchField()),
            const SizedBox(width: 8),
            Expanded(child: _statusDropdown()),
            const SizedBox(width: 8),
            Expanded(child: _visibilityDropdown()),
            const SizedBox(width: 8),
            Expanded(child: _ownerDropdown()),
          ],
        ),
        const SizedBox(height: 8),
        Row(
          children: [
            Expanded(child: _sourceDropdown()),
            const SizedBox(width: 8),
            Expanded(child: _scopeDropdown()),
            const SizedBox(width: 8),
            Expanded(child: _sortDropdown()),
            const SizedBox(width: 8),
            Expanded(
              child: _dateField(
                label: 'Tạo từ ngày',
                value: _createdFrom,
                onPick: () => _pickDate(isStart: true),
                onClear: () => setState(() => _createdFrom = null),
              ),
            ),
            const SizedBox(width: 8),
            Expanded(
              child: _dateField(
                label: 'Tạo đến ngày',
                value: _createdTo,
                onPick: () => _pickDate(isStart: false),
                onClear: () => setState(() => _createdTo = null),
              ),
            ),
            const SizedBox(width: 4),
            IconButton(
              icon: const Icon(Icons.refresh),
              tooltip: 'Tai lai',
              onPressed: () => _invalidateLists(),
            ),
          ],
        ),
      ],
    );
  }

  @override
  Widget build(BuildContext context) {
    final query = _buildQuery();
    final promptsAsync = ref.watch(promptQueryProvider(query));

    return LayoutBuilder(
      builder: (context, constraints) {
        final isMobile = constraints.maxWidth < 700;
        final padding = isMobile ? 12.0 : 20.0;
        return Scaffold(
          floatingActionButton: isMobile
              ? FloatingActionButton.extended(
                  icon: const Icon(Icons.add),
                  label: const Text('Tạo prompt'),
                  onPressed: () => context.go('/prompts/new'),
                )
              : null,
          body: Padding(
            padding: EdgeInsets.all(padding),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Expanded(
                      child: Text(
                        _headerLabel(),
                        style: Theme.of(context)
                            .textTheme
                            .titleLarge
                            ?.copyWith(fontWeight: FontWeight.bold),
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                    if (!isMobile)
                      FilledButton.icon(
                        icon: const Icon(Icons.add),
                        label: const Text('Tạo prompt mới'),
                        onPressed: () => context.go('/prompts/new'),
                      ),
                    if (isMobile)
                      IconButton(
                        icon: const Icon(Icons.refresh),
                        tooltip: 'Tải lại',
                        onPressed: _invalidateLists,
                      ),
                  ],
                ),
                SizedBox(height: isMobile ? 8 : 12),
                if (isMobile)
                  _mobileFilterBar()
                else
                  CollapsibleFilterPanel(
                    title: 'Bộ lọc / Tìm kiếm',
                    icon: Icons.filter_alt_outlined,
                    badgeCount: _hasActiveFilter() ? 1 : 0,
                    child: _desktopFilterBar(),
                  ),
                SizedBox(height: isMobile ? 8 : 12),
                Expanded(
                  child: promptsAsync.when(
                    loading: () => const Center(child: CircularProgressIndicator()),
                    error: (error, _) => Center(child: Text('Lỗi: $error')),
                    data: (prompts) {
                      if (prompts.isEmpty) {
                        return Center(
                          child: Padding(
                            padding: const EdgeInsets.all(20),
                            child: Column(
                              mainAxisSize: MainAxisSize.min,
                              children: [
                                Icon(
                                  Icons.search_off,
                                  size: 48,
                                  color: Colors.grey.shade400,
                                ),
                                const SizedBox(height: 8),
                                const Text(
                                  'Không có prompt nào khớp với bộ lọc hiện tại.',
                                  style: TextStyle(color: Colors.grey),
                                  textAlign: TextAlign.center,
                                ),
                                if (_hasActiveFilter()) ...[
                                  const SizedBox(height: 8),
                                  TextButton(
                                    onPressed: _resetFilters,
                                    child: const Text('Xóa bộ lọc'),
                                  ),
                                ],
                              ],
                            ),
                          ),
                        );
                      }
                      final deletable =
                          prompts.where(_canDeletePrompt).toList();
                      final allSelected = deletable.isNotEmpty &&
                          deletable
                              .every((p) => _selectedPromptIds.contains(p.id));
                      final effectiveViewMode = isMobile ? 'list' : _viewMode;

                      Widget refresh(Widget child) => RefreshIndicator(
                            onRefresh: () async {
                              _invalidateLists();
                              await Future<void>.delayed(
                                const Duration(milliseconds: 250),
                              );
                            },
                            child: child,
                          );

                      Widget itemFor(PromptRecord p, {required bool compact}) =>
                          _buildItem(
                            p,
                            compact: compact,
                            selectable: _canDeletePrompt(p),
                            selected: _selectedPromptIds.contains(p.id),
                            onSelectedChanged: (sel) => setState(() {
                              if (sel) {
                                _selectedPromptIds.add(p.id);
                              } else {
                                _selectedPromptIds.remove(p.id);
                              }
                            }),
                          );

                      // Cards: Wrap cac the rong co dinh, cao tu nhien -> khong tran.
                      final Widget body = effectiveViewMode == 'cards'
                          ? refresh(
                              SingleChildScrollView(
                                padding: const EdgeInsets.only(bottom: 12),
                                child: Wrap(
                                  spacing: 12,
                                  runSpacing: 12,
                                  children: [
                                    for (final p in prompts)
                                      SizedBox(
                                        width: 360,
                                        child: itemFor(p, compact: false),
                                      ),
                                  ],
                                ),
                              ),
                            )
                          : refresh(
                              ListView.builder(
                                padding: EdgeInsets.only(
                                    bottom: isMobile ? 80 : 12),
                                itemCount: prompts.length,
                                itemBuilder: (_, index) =>
                                    itemFor(prompts[index], compact: isMobile),
                              ),
                            );

                      final bulkDeleteBtn = FilledButton.icon(
                        onPressed: _bulkDeleting ? null : _bulkDeletePrompts,
                        style: FilledButton.styleFrom(
                            backgroundColor: Colors.red.shade600),
                        icon: _bulkDeleting
                            ? const SizedBox(
                                width: 14,
                                height: 14,
                                child: CircularProgressIndicator(
                                    strokeWidth: 2, color: Colors.white))
                            : const Icon(Icons.delete_sweep_outlined, size: 18),
                        label: Text(_bulkDeleting ? 'Đang xóa...' : 'Xóa hàng loạt'),
                      );
                      final selectAllBtn = OutlinedButton.icon(
                        onPressed: deletable.isEmpty
                            ? null
                            : () => _toggleSelectAllPrompts(prompts),
                        icon: Icon(
                          allSelected
                              ? Icons.check_box_rounded
                              : Icons.check_box_outline_blank_rounded,
                          size: 18,
                        ),
                        label: Text(allSelected ? 'Bỏ chọn tất cả' : 'Chọn tất cả'),
                      );

                      return Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          // Thanh cong cu 1 dong: dem + chon + toggle + xoa hang loat.
                          Row(
                            children: [
                              Expanded(
                                child: Text(
                                  'Tìm thấy ${prompts.length} prompt',
                                  style: TextStyle(
                                      color: Colors.grey.shade600,
                                      fontSize: 13),
                                ),
                              ),
                              if (!isMobile) ...[
                                const SizedBox(width: 8),
                                selectAllBtn,
                                if (_selectedPromptIds.isNotEmpty) ...[
                                  const SizedBox(width: 8),
                                  Text(
                                    'Đã chọn ${_selectedPromptIds.length}',
                                    style: TextStyle(
                                      fontSize: 13,
                                      fontWeight: FontWeight.w600,
                                      color: Colors.blueGrey.shade700,
                                    ),
                                  ),
                                  TextButton(
                                    onPressed: () => setState(
                                        () => _selectedPromptIds.clear()),
                                    child: const Text('Bỏ chọn'),
                                  ),
                                ],
                                const SizedBox(width: 8),
                                ViewModeToggle(
                                  value: _viewMode,
                                  onChanged: (v) =>
                                      setState(() => _viewMode = v),
                                  cardLabel: 'Dạng thẻ',
                                  listLabel: 'Dạng danh sách',
                                ),
                                if (_selectedPromptIds.isNotEmpty) ...[
                                  const SizedBox(width: 8),
                                  bulkDeleteBtn,
                                ],
                              ],
                            ],
                          ),
                          if (isMobile && _selectedPromptIds.isNotEmpty) ...[
                            const SizedBox(height: 8),
                            Wrap(
                              spacing: 8,
                              runSpacing: 8,
                              crossAxisAlignment: WrapCrossAlignment.center,
                              children: [
                                selectAllBtn,
                                Text(
                                  'Da chon ${_selectedPromptIds.length}',
                                  style: TextStyle(
                                    fontSize: 13,
                                    fontWeight: FontWeight.w600,
                                    color: Colors.blueGrey.shade700,
                                  ),
                                ),
                                bulkDeleteBtn,
                              ],
                            ),
                          ],
                          const SizedBox(height: 10),
                          Expanded(child: body),
                        ],
                      );
                    },
                  ),
                ),
              ],
            ),
          ),
        );
      },
    );
  }
}
