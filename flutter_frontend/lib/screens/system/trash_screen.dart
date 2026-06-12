// === MÀN HÌNH THÙNG RÁC ===
// Liệt kê các bản ghi đã XÓA MỀM (mẫu/văn bản/...) để khôi phục hoặc xóa vĩnh viễn.
// - _loadTrash(): GET 'trash/entries/' (có tìm kiếm _onSearchChanged, lọc theo loại _labelForCategory).
// - Chọn nhiều rồi: _restoreSelected() POST 'trash/restore/'; _deleteSelected() POST 'trash/delete/' (xác nhận qua _confirmPermanentDelete).

// Tệp này dùng để: dựng giao diện và orchestration UI trong flutter_frontend/lib/screens/system/trash_screen.dart.
import 'dart:async';

import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/api_client.dart';
import '../../l10n/app_strings.dart';
import '../../models/trash.dart';
import '../../providers/documents_provider.dart';
import '../../providers/templates_provider.dart';

// Widget màn THÙNG RÁC — ConsumerStatefulWidget.

class TrashScreen extends ConsumerStatefulWidget {
  // Widget màn THÙNG RÁC (văn bản/mẫu/prompt đã xóa).
  const TrashScreen({super.key});

  @override
  ConsumerState<TrashScreen> createState() => _TrashScreenState();
}

// State màn thùng rác: tải mục đã xóa, tìm kiếm, chọn nhiều, khôi phục/xóa vĩnh viễn.

class _TrashScreenState extends ConsumerState<TrashScreen> {
  AppStrings get _strings => AppStrings.of(context);
  // Chọn chuỗi VI/EN (i18n).
  String _pick(String vi, String en) => _strings.pick(vi, en);

  static const _categories = <String, String>{
    'all': 'Tất cả',
    'template': 'Mẫu văn bản',
    'document': 'Văn bản',
    'chat_ai_text': 'ChatAI chữ',
    'chat_ai_voice': 'ChatAI giọng nói',
    'rag_template': 'Hỏi đáp mẫu',
    'rag_document': 'Hỏi đáp văn bản',
  };

  final _searchCtrl = TextEditingController();
  Timer? _debounce;
  List<TrashEntry> _entries = const [];
  Map<String, int> _counts = const {};
  final Set<String> _selectedKeys = <String>{};
  String _category = 'all';
  String _query = '';
  bool _loading = true;
  bool _restoring = false;
  bool _purging = false;
  String? _error;

  @override
  // Mở màn: nạp danh sách mục trong thùng rác.
  void initState() {
    super.initState();
    _loadTrash();
  }

  @override
  // Rời màn: dọn controller tìm kiếm.
  void dispose() {
    _debounce?.cancel();
    _searchCtrl.dispose();
    super.dispose();
  }

  // Tải danh sách mục trong thùng rác từ server.

  Future<void> _loadTrash() async {
    if (!mounted) return;
    // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      // Gọi API hoặc tác vụ bất đồng bộ rồi chờ kết quả trước khi cập nhật giao diện.

      final resp = await ApiClient().dio.get(
        'trash/entries/',
        queryParameters: {
          'category': _category,
          if (_query.trim().isNotEmpty) 'q': _query.trim(),
        },
      );
      final countsRaw = Map<String, dynamic>.from(
        (resp.data['counts'] as Map?)?.cast<String, dynamic>() ?? const {},
      );
      final entries = (resp.data['results'] as List<dynamic>? ?? const [])
          .map((item) =>
              TrashEntry.fromJson(Map<String, dynamic>.from(item as Map)))
          .toList();
      if (!mounted) return;
      // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

      setState(() {
        _counts = countsRaw
            .map((key, value) => MapEntry(key, (value as num?)?.toInt() ?? 0));
        _entries = entries;
        _selectedKeys
            .removeWhere((key) => !entries.any((item) => item.trashKey == key));
        _loading = false;
      });
    } catch (error) {
      if (!mounted) return;
      // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

      setState(() {
        _loading = false;
        _error = _readableError(error);
      });
    }
  }

  // Đổi lỗi API thành thông điệp dễ đọc.
  String _readableError(Object error) {
    if (error is DioException) {
      final data = error.response?.data;
      if (data is Map && data['detail'] != null) {
        return '${data['detail']}';
      }
      return _pick(
        'Khong tai duoc thung rac (${error.response?.statusCode ?? 'network'}).',
        'Could not load trash (${error.response?.statusCode ?? 'network'}).',
      );
    }
    return _pick(
        'Khong tai duoc thung rac: $error', 'Could not load trash: $error');
  }

  // Lọc mục thùng rác theo từ khóa.
  void _onSearchChanged(String value) {
    _debounce?.cancel();
    _debounce = Timer(const Duration(milliseconds: 300), () {
      if (!mounted) return;
      // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

      setState(() => _query = value);
      _loadTrash();
    });
  }

  // Nút Khôi phục: khôi phục các mục đã chọn về danh sách gốc.
  Future<void> _restoreSelected({List<TrashEntry>? entries}) async {
    final selected = entries ??
        _entries
            .where((entry) => _selectedKeys.contains(entry.trashKey))
            .toList();
    if (selected.isEmpty || _restoring) return;
    // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

    setState(() => _restoring = true);
    try {
      // Gọi API hoặc tác vụ bất đồng bộ rồi chờ kết quả trước khi cập nhật giao diện.

      await ApiClient().dio.post(
        'trash/restore/',
        data: {
          'items': selected
              .map((entry) => {
                    'category': entry.category,
                    'id': entry.id,
                  })
              .toList(),
        },
      );
      if (!mounted) return;
      // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

      setState(() => _selectedKeys.clear());
      ref.invalidate(templatesProvider(''));
      ref.invalidate(templatesProvider('private'));
      ref.invalidate(templatesProvider('team'));
      ref.invalidate(templatesProvider('system'));
      ref.invalidate(templatesProvider('favorite'));
      ref.invalidate(adminTemplatesProvider(const AdminTemplateParams()));
      refreshDocumentCollections(ref);
      _showSnack(
        selected.length == 1
            ? _pick('Da khoi phuc 1 muc.', 'Restored 1 item.')
            : _pick('Da khoi phuc ${selected.length} muc.',
                'Restored ${selected.length} items.'),
      );
      await _loadTrash();
    } catch (error) {
      if (!mounted) return;
      _showSnack(_readableError(error), error: true);
    } finally {
      // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

      if (mounted) setState(() => _restoring = false);
    }
  }

  // Hỏi xác nhận trước khi xóa vĩnh viễn.
  Future<bool> _confirmPermanentDelete(int count) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: Text(_pick('Xoa vinh vien', 'Delete permanently')),
        content: Text(
          count == 1
              ? _pick(
                  'Muc da chon se bi xoa vinh vien va khong the khoi phuc lai. Ban co chac chan khong?',
                  'The selected item will be deleted permanently and cannot be restored. Continue?',
                )
              : _pick(
                  '$count muc da chon se bi xoa vinh vien va khong the khoi phuc lai. Ban co chac chan khong?',
                  '$count selected items will be deleted permanently and cannot be restored. Continue?',
                ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(false),
            child: Text(_pick('Huy', 'Cancel')),
          ),
          FilledButton(
            onPressed: () => Navigator.of(context).pop(true),
            style: FilledButton.styleFrom(backgroundColor: Colors.red.shade600),
            child: Text(_pick('Xoa vinh vien', 'Delete permanently')),
          ),
        ],
      ),
    );
    return confirmed == true;
  }

  // Nút Xóa vĩnh viễn: xóa hẳn các mục đã chọn (không khôi phục được).
  Future<void> _deleteSelected({List<TrashEntry>? entries}) async {
    final selected = entries ??
        _entries
            .where((entry) => _selectedKeys.contains(entry.trashKey))
            .toList();
    if (selected.isEmpty || _purging) return;

    final confirmed = await _confirmPermanentDelete(selected.length);
    if (!confirmed || !mounted) return;

    // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

    setState(() => _purging = true);
    try {
      // Gọi API hoặc tác vụ bất đồng bộ rồi chờ kết quả trước khi cập nhật giao diện.

      await ApiClient().dio.post(
        'trash/delete/',
        data: {
          'items': selected
              .map((entry) => {
                    'category': entry.category,
                    'id': entry.id,
                  })
              .toList(),
        },
      );
      if (!mounted) return;
      // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

      setState(() => _selectedKeys.clear());
      _showSnack(
        selected.length == 1
            ? _pick('Da xoa vinh vien 1 muc.', 'Deleted 1 item permanently.')
            : _pick('Da xoa vinh vien ${selected.length} muc.',
                'Deleted ${selected.length} items permanently.'),
      );
      await _loadTrash();
    } catch (error) {
      if (!mounted) return;
      _showSnack(_readableError(error), error: true);
    } finally {
      // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

      if (mounted) setState(() => _purging = false);
    }
  }

  // Hiện snackbar thông báo (thường/lỗi).

  void _showSnack(String message, {bool error = false}) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(message),
        backgroundColor: error ? Colors.red : Colors.green,
      ),
    );
  }

  // Nhãn loại đối tượng (văn bản/mẫu/prompt) trong thùng rác.
  String _labelForCategory(String category) => switch (category) {
        'all' => _pick('Tat ca', 'All'),
        'template' => _pick('Mau van ban', 'Templates'),
        'document' => _pick('Van ban', 'Documents'),
        'chat_ai_text' => _pick('ChatAI chu', 'ChatAI text'),
        'chat_ai_voice' => _pick('ChatAI giong noi', 'ChatAI voice'),
        'rag_template' => _pick('Hoi dap mau', 'Template Q&A'),
        'rag_document' => _pick('Hoi dap van ban', 'Document Q&A'),
        _ => _categories[category] ?? category,
      };

  // Định dạng thời điểm xóa để hiển thị.
  String _formatStamp(String value) {
    if (value.isEmpty) return '';
    return value
        .replaceFirst('T', ' ')
        .substring(0, value.length >= 16 ? 16 : value.length);
  }

  @override
  // Dựng màn: tìm kiếm + danh sách mục đã xóa + nút Khôi phục/Xóa vĩnh viễn (chọn nhiều).
  Widget build(BuildContext context) {
    final isCompact = MediaQuery.sizeOf(context).width < 820;
    return Padding(
      padding: EdgeInsets.all(isCompact ? 12 : 20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            _pick('Thung rac', 'Trash'),
            style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                  fontWeight: FontWeight.w800,
                ),
          ),
          const SizedBox(height: 6),
          Text(
            _pick(
              'Cac muc da xoa se duoc giu tam trong 30 ngay de ban khoi phuc khi can.',
              'Deleted items stay here for 30 days so you can restore them if needed.',
            ),
            style: const TextStyle(color: Color(0xFF475569), height: 1.5),
          ),
          const SizedBox(height: 16),
          Flex(
            direction: isCompact ? Axis.vertical : Axis.horizontal,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Expanded(
                child: TextField(
                  controller: _searchCtrl,
                  onChanged: _onSearchChanged,
                  decoration: InputDecoration(
                    hintText: _pick(
                      'Tim theo ten, noi dung, tin nhan...',
                      'Search by title, content, or message...',
                    ),
                    prefixIcon: const Icon(Icons.search),
                    suffixIcon: _query.isEmpty
                        ? null
                        : IconButton(
                            onPressed: () {
                              _searchCtrl.clear();
                              // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

                              setState(() => _query = '');
                              _loadTrash();
                            },
                            icon: const Icon(Icons.close),
                          ),
                    border: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(14),
                    ),
                    filled: true,
                    fillColor: Colors.white,
                  ),
                ),
              ),
              SizedBox(width: isCompact ? 0 : 10, height: isCompact ? 10 : 0),
              OutlinedButton.icon(
                onPressed: _loading ? null : _loadTrash,
                icon: const Icon(Icons.refresh),
                label: Text(_pick('Tai lai', 'Reload')),
              ),
            ],
          ),
          const SizedBox(height: 14),
          SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            child: Row(
              children: _categories.entries.map((entry) {
                final count = _counts[entry.key] ?? 0;
                return Padding(
                  padding: const EdgeInsets.only(right: 8),
                  child: ChoiceChip(
                    label: Text('${_labelForCategory(entry.key)} ($count)'),
                    selected: _category == entry.key,
                    onSelected: (_) {
                      // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

                      setState(() {
                        _category = entry.key;
                        _selectedKeys.clear();
                      });
                      _loadTrash();
                    },
                  ),
                );
              }).toList(),
            ),
          ),
          const SizedBox(height: 14),
          if (!isCompact || _selectedKeys.isNotEmpty)
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
              decoration: BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: const Color(0xFFE2E8F0)),
              ),
              child: Row(
                children: [
                  Expanded(
                    child: Text(
                      _selectedKeys.isEmpty
                          ? _pick('Chua chon muc nao', 'No items selected')
                          : _pick('Da chon ${_selectedKeys.length} muc',
                              '${_selectedKeys.length} items selected'),
                      style: const TextStyle(fontWeight: FontWeight.w600),
                    ),
                  ),
                  if (_selectedKeys.isNotEmpty)
                    TextButton(
                      // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

                      onPressed: () => setState(() => _selectedKeys.clear()),
                      child: Text(_pick('Bo chon', 'Clear selection')),
                    ),
                  const SizedBox(width: 8),
                  FilledButton.tonalIcon(
                    onPressed: _selectedKeys.isEmpty || _purging || _restoring
                        ? null
                        : _deleteSelected,
                    icon: _purging
                        ? const SizedBox(
                            width: 16,
                            height: 16,
                            child: CircularProgressIndicator(strokeWidth: 2),
                          )
                        : const Icon(Icons.delete_forever_outlined),
                    style: FilledButton.styleFrom(
                      foregroundColor: Colors.red.shade700,
                    ),
                    label: Text(_purging
                        ? _pick('Dang xoa...', 'Deleting...')
                        : _pick('Xoa vinh vien', 'Delete permanently')),
                  ),
                  const SizedBox(width: 8),
                  FilledButton.icon(
                    onPressed: _selectedKeys.isEmpty || _restoring || _purging
                        ? null
                        : _restoreSelected,
                    icon: _restoring
                        ? const SizedBox(
                            width: 16,
                            height: 16,
                            child: CircularProgressIndicator(
                                strokeWidth: 2, color: Colors.white),
                          )
                        : const Icon(Icons.restore_outlined),
                    label: Text(_restoring
                        ? _pick('Dang khoi phuc...', 'Restoring...')
                        : _pick('Khoi phuc da chon', 'Restore selected')),
                  ),
                ],
              ),
            ),
          const SizedBox(height: 12),
          Expanded(
            child: _loading
                ? const Center(child: CircularProgressIndicator())
                : _error != null
                    ? Center(child: Text(_error!))
                    : _entries.isEmpty
                        ? Center(
                            child: Text(
                              _pick('Thung rac hien dang trong.',
                                  'Trash is currently empty.'),
                              style: const TextStyle(color: Color(0xFF64748B)),
                            ),
                          )
                        : ListView.separated(
                            itemCount: _entries.length,
                            separatorBuilder: (_, __) =>
                                const SizedBox(height: 10),
                            itemBuilder: (context, index) {
                              final entry = _entries[index];
                              final selected =
                                  _selectedKeys.contains(entry.trashKey);
                              return Container(
                                decoration: BoxDecoration(
                                  color: Colors.white,
                                  borderRadius: BorderRadius.circular(16),
                                  border: Border.all(
                                    color: selected
                                        ? const Color(0xFF2563EB)
                                        : const Color(0xFFE2E8F0),
                                  ),
                                ),
                                child: CheckboxListTile(
                                  value: selected,
                                  onChanged: (value) {
                                    // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

                                    setState(() {
                                      if (value == true) {
                                        _selectedKeys.add(entry.trashKey);
                                      } else {
                                        _selectedKeys.remove(entry.trashKey);
                                      }
                                    });
                                  },
                                  controlAffinity:
                                      ListTileControlAffinity.leading,
                                  contentPadding: const EdgeInsets.symmetric(
                                      horizontal: 12, vertical: 8),
                                  title: Row(
                                    children: [
                                      Expanded(
                                        child: Text(
                                          entry.title.isEmpty
                                              ? '(${_pick('Khong co tieu de', 'Untitled')})'
                                              : entry.title,
                                          style: const TextStyle(
                                              fontWeight: FontWeight.w700),
                                        ),
                                      ),
                                      FilledButton.tonalIcon(
                                        onPressed: _restoring || _purging
                                            ? null
                                            : () => _restoreSelected(
                                                entries: [entry]),
                                        icon: const Icon(Icons.restore_outlined,
                                            size: 18),
                                        label:
                                            Text(_pick('Khoi phuc', 'Restore')),
                                      ),
                                      const SizedBox(width: 8),
                                      FilledButton.tonalIcon(
                                        onPressed: _restoring || _purging
                                            ? null
                                            : () => _deleteSelected(
                                                entries: [entry]),
                                        icon: const Icon(
                                            Icons.delete_forever_outlined,
                                            size: 18),
                                        style: FilledButton.styleFrom(
                                          foregroundColor: Colors.red.shade700,
                                        ),
                                        label: Text(_pick('Xoa vinh vien',
                                            'Delete permanently')),
                                      ),
                                    ],
                                  ),
                                  subtitle: Padding(
                                    padding: const EdgeInsets.only(top: 8),
                                    child: Column(
                                      crossAxisAlignment:
                                          CrossAxisAlignment.start,
                                      children: [
                                        Wrap(
                                          spacing: 8,
                                          runSpacing: 8,
                                          children: [
                                            _TrashMetaChip(
                                                label: _labelForCategory(
                                                    entry.category)),
                                            if (entry.messageCount > 0)
                                              _TrashMetaChip(
                                                  label: _pick(
                                                      '${entry.messageCount} tin nhan',
                                                      '${entry.messageCount} messages')),
                                            if (entry.audioCount > 0)
                                              _TrashMetaChip(
                                                  label: _pick(
                                                      '${entry.audioCount} audio',
                                                      '${entry.audioCount} audio files')),
                                          ],
                                        ),
                                        if (entry.preview.isNotEmpty) ...[
                                          const SizedBox(height: 8),
                                          Text(
                                            entry.preview,
                                            style: const TextStyle(
                                                color: Color(0xFF475569),
                                                height: 1.5),
                                          ),
                                        ],
                                        const SizedBox(height: 10),
                                        Text(
                                          '${_pick('Xoa luc', 'Deleted at')}: ${_formatStamp(entry.deletedAt)}',
                                          style: const TextStyle(
                                              fontSize: 12,
                                              color: Color(0xFF64748B)),
                                        ),
                                        if (entry.expiresAt.isNotEmpty)
                                          Text(
                                            '${_pick('Tu dong xoa vinh vien luc', 'Auto-delete permanently at')}: ${_formatStamp(entry.expiresAt)}',
                                            style: const TextStyle(
                                                fontSize: 12,
                                                color: Color(0xFF64748B)),
                                          ),
                                      ],
                                    ),
                                  ),
                                ),
                              );
                            },
                          ),
          ),
        ],
      ),
    );
  }
}

// Widget chip metadata mục thùng rác (loại/ngày xóa).

class _TrashMetaChip extends StatelessWidget {
  final String label;

  const _TrashMetaChip({required this.label});

  @override
  // Dựng chip metadata.

  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: const Color(0xFFF1F5F9),
        borderRadius: BorderRadius.circular(999),
        border: Border.all(color: const Color(0xFFE2E8F0)),
      ),
      child: Text(
        label,
        style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w600),
      ),
    );
  }
}
