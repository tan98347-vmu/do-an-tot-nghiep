import 'dart:html' as html;

import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/api_client.dart';
import '../../l10n/app_strings.dart';

class BackupScreen extends ConsumerStatefulWidget {
  const BackupScreen({super.key});

  @override
  ConsumerState<BackupScreen> createState() => _BackupScreenState();
}

class _BackupScreenState extends ConsumerState<BackupScreen> {
  static const Map<String, ({String vi, String en})> _appLabels = {
    'accounts': (vi: 'Tài khoản & cấu hình', en: 'Accounts & settings'),
    'document_templates': (vi: 'Mẫu văn bản', en: 'Templates'),
    'documents': (vi: 'Văn bản', en: 'Documents'),
    'ai_engine': (vi: 'AI engine', en: 'AI engine'),
    'prompts': (vi: 'Prompts', en: 'Prompts'),
    'auth': (vi: 'Phân quyền người dùng', en: 'User authorization'),
  };

  List<dynamic> _files = const [];
  List<dynamic> _dbInfo = const [];
  List<String> _appKeys = const [];
  bool _loading = true;
  bool _creating = false;
  String _backupType = 'full';
  String? _selectedApp;

  AppStrings get _strings => AppStrings.of(context);

  @override
  void initState() {
    super.initState();
    _loadData();
  }

  String _appLabel(String key) {
    final label = _appLabels[key];
    if (label == null) return key;
    return _strings.pick(label.vi, label.en);
  }

  Future<void> _loadData() async {
    setState(() => _loading = true);
    try {
      final resp = await ApiClient().dio.get('admin/backup/');
      if (!mounted) return;
      setState(() {
        _files = List.from(resp.data['files'] ?? const []);
        _dbInfo = List.from(resp.data['db_info'] ?? const []);
        _appKeys = List<String>.from(resp.data['app_keys'] ?? const []);
        _selectedApp ??= _appKeys.isNotEmpty ? _appKeys.first : null;
        _loading = false;
      });
    } catch (_) {
      if (!mounted) return;
      setState(() => _loading = false);
    }
  }

  Future<void> _createBackup() async {
    setState(() => _creating = true);
    try {
      final body = <String, dynamic>{'backup_type': _backupType};
      if (_backupType == 'app' && _selectedApp != null) {
        body['app_key'] = _selectedApp;
      }
      final resp =
          await ApiClient().dio.post('admin/backup/create/', data: body);
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            resp.data['detail']?.toString() ??
                _strings.pick(
                  'Đã tạo backup thành công.',
                  'Backup created successfully.',
                ),
          ),
          backgroundColor: Colors.green,
        ),
      );
      await _loadData();
    } catch (error) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            '${_strings.pick('Lỗi tạo backup', 'Backup creation error')}: $error',
          ),
          backgroundColor: Colors.red,
        ),
      );
    } finally {
      if (mounted) setState(() => _creating = false);
    }
  }

  Future<void> _downloadBackup(String filename) async {
    try {
      final resp = await ApiClient().dio.get(
            'admin/backup/$filename/download/',
            options: Options(responseType: ResponseType.bytes),
          );
      final bytes = resp.data as List<int>;
      final blob = html.Blob([bytes], 'application/json');
      final url = html.Url.createObjectUrlFromBlob(blob);
      html.AnchorElement(href: url)
        ..setAttribute('download', filename)
        ..click();
      html.Url.revokeObjectUrl(url);
    } catch (error) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            '${_strings.pick('Lỗi tải file', 'File download error')}: $error',
          ),
          backgroundColor: Colors.red,
        ),
      );
    }
  }

  Future<void> _deleteBackup(String filename) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text(_strings.pick('Xác nhận xóa', 'Confirm deletion')),
        content: Text(
          _strings.pick(
            'Xóa file backup "$filename"?',
            'Delete backup file "$filename"?',
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx, false),
            child: Text(_strings.pick('Hủy', 'Cancel')),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(ctx, true),
            style: FilledButton.styleFrom(backgroundColor: Colors.red),
            child: Text(_strings.pick('Xóa', 'Delete')),
          ),
        ],
      ),
    );
    if (confirmed != true) return;

    try {
      await ApiClient().dio.delete('admin/backup/$filename/');
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            _strings.pick('Đã xóa file backup.', 'Backup file deleted.'),
          ),
          backgroundColor: Colors.green,
        ),
      );
      await _loadData();
    } catch (error) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('${_strings.pick('Lỗi xóa', 'Delete error')}: $error'),
          backgroundColor: Colors.red,
        ),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(24),
      child: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 900),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  const Icon(
                    Icons.backup_outlined,
                    size: 24,
                    color: Color(0xFF1565C0),
                  ),
                  const SizedBox(width: 10),
                  Text(
                    _strings.pick('Sao lưu dữ liệu', 'Data backups'),
                    style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                          fontWeight: FontWeight.bold,
                        ),
                  ),
                  const Spacer(),
                  IconButton(
                    icon: const Icon(Icons.refresh_outlined),
                    tooltip: _strings.pick('Làm mới', 'Refresh'),
                    onPressed: _loading ? null : _loadData,
                  ),
                ],
              ),
              const SizedBox(height: 4),
              Text(
                _strings.pick(
                  'Tạo và quản lý các bản sao lưu dữ liệu hệ thống.',
                  'Create and manage system data backups.',
                ),
                style: TextStyle(color: Colors.grey.shade600),
              ),
              const SizedBox(height: 24),
              if (_loading)
                const Center(child: CircularProgressIndicator())
              else ...[
                LayoutBuilder(
                  builder: (context, constraints) {
                    final wide = constraints.maxWidth >= 700;
                    final createCard = _buildCreateCard();
                    final statsCard = _buildDbStatsCard();
                    if (wide) {
                      return Row(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Expanded(flex: 5, child: createCard),
                          const SizedBox(width: 16),
                          Expanded(flex: 4, child: statsCard),
                        ],
                      );
                    }
                    return Column(
                      children: [
                        createCard,
                        const SizedBox(height: 16),
                        statsCard,
                      ],
                    );
                  },
                ),
                const SizedBox(height: 24),
                _buildFilesCard(),
              ],
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildCreateCard() {
    return Card(
      elevation: 1,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Icon(
                  Icons.add_circle_outline,
                  size: 18,
                  color: Color(0xFF1565C0),
                ),
                const SizedBox(width: 8),
                Text(
                  _strings.pick('Tạo backup mới', 'Create new backup'),
                  style: Theme.of(context).textTheme.titleMedium?.copyWith(
                        fontWeight: FontWeight.bold,
                      ),
                ),
              ],
            ),
            const SizedBox(height: 16),
            RadioListTile<String>(
              value: 'full',
              groupValue: _backupType,
              onChanged: (value) => setState(() => _backupType = value!),
              title: Text(
                _strings.pick('Toàn bộ hệ thống', 'Entire system'),
              ),
              subtitle: Text(
                _strings.pick(
                  'Backup tất cả dữ liệu',
                  'Back up all data',
                ),
                style: const TextStyle(fontSize: 12),
              ),
              contentPadding: EdgeInsets.zero,
              dense: true,
            ),
            RadioListTile<String>(
              value: 'app',
              groupValue: _backupType,
              onChanged: (value) => setState(() => _backupType = value!),
              title: Text(_strings.pick('Theo module', 'By module')),
              subtitle: Text(
                _strings.pick(
                  'Chỉ backup một module cụ thể',
                  'Back up a specific module only',
                ),
                style: const TextStyle(fontSize: 12),
              ),
              contentPadding: EdgeInsets.zero,
              dense: true,
            ),
            if (_backupType == 'app' && _appKeys.isNotEmpty) ...[
              const SizedBox(height: 8),
              DropdownButtonFormField<String>(
                initialValue: _selectedApp,
                decoration: InputDecoration(
                  labelText: _strings.pick('Chọn module', 'Choose module'),
                  border: const OutlineInputBorder(),
                  isDense: true,
                  contentPadding: const EdgeInsets.symmetric(
                    horizontal: 12,
                    vertical: 10,
                  ),
                ),
                items: _appKeys
                    .map(
                      (key) => DropdownMenuItem<String>(
                        value: key,
                        child: Text(_appLabel(key)),
                      ),
                    )
                    .toList(),
                onChanged: (value) => setState(() => _selectedApp = value),
              ),
            ],
            const SizedBox(height: 16),
            SizedBox(
              width: double.infinity,
              child: FilledButton.icon(
                onPressed: _creating ? null : _createBackup,
                icon: _creating
                    ? const SizedBox(
                        width: 16,
                        height: 16,
                        child: CircularProgressIndicator(
                          strokeWidth: 2,
                          color: Colors.white,
                        ),
                      )
                    : const Icon(Icons.save_outlined, size: 16),
                label: Text(
                  _creating
                      ? _strings.pick(
                          'Đang tạo backup...',
                          'Creating backup...',
                        )
                      : _strings.pick(
                          'Tạo backup ngay',
                          'Create backup now',
                        ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildDbStatsCard() {
    return Card(
      elevation: 1,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Icon(
                  Icons.storage_outlined,
                  size: 18,
                  color: Color(0xFF1565C0),
                ),
                const SizedBox(width: 8),
                Text(
                  _strings.pick('Thống kê dữ liệu', 'Data statistics'),
                  style: Theme.of(context).textTheme.titleMedium?.copyWith(
                        fontWeight: FontWeight.bold,
                      ),
                ),
              ],
            ),
            const SizedBox(height: 12),
            if (_dbInfo.isEmpty)
              Text(
                _strings.pick('Không có dữ liệu', 'No data available'),
                style: TextStyle(color: Colors.grey.shade500),
              )
            else
              ..._dbInfo.map<Widget>((app) {
                final appKey = app['app'] as String? ?? '';
                final models = List.from(app['models'] ?? const []);
                return ExpansionTile(
                  dense: true,
                  tilePadding: EdgeInsets.zero,
                  title: Text(
                    _appLabel(appKey),
                    style: const TextStyle(
                      fontSize: 13,
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                  children: models.map<Widget>((model) {
                    final label = (model['label'] as String).split('.').last;
                    final count = model['count'];
                    return Padding(
                      padding: const EdgeInsets.symmetric(
                        horizontal: 12,
                        vertical: 3,
                      ),
                      child: Row(
                        children: [
                          Text(
                            label,
                            style: TextStyle(
                              fontSize: 12,
                              color: Colors.grey.shade700,
                            ),
                          ),
                          const Spacer(),
                          Container(
                            padding: const EdgeInsets.symmetric(
                              horizontal: 8,
                              vertical: 2,
                            ),
                            decoration: BoxDecoration(
                              color: Colors.blue.shade50,
                              borderRadius: BorderRadius.circular(8),
                            ),
                            child: Text(
                              _strings.pick(
                                '$count bản ghi',
                                '$count records',
                              ),
                              style: TextStyle(
                                fontSize: 11,
                                color: Colors.blue.shade700,
                              ),
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

  Widget _buildFilesCard() {
    return Card(
      elevation: 1,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Icon(
                  Icons.folder_outlined,
                  size: 18,
                  color: Color(0xFF1565C0),
                ),
                const SizedBox(width: 8),
                Text(
                  _strings.pick(
                    'Danh sách backup (${_files.length})',
                    'Backups (${_files.length})',
                  ),
                  style: Theme.of(context).textTheme.titleMedium?.copyWith(
                        fontWeight: FontWeight.bold,
                      ),
                ),
              ],
            ),
            const SizedBox(height: 12),
            if (_files.isEmpty)
              Container(
                width: double.infinity,
                padding: const EdgeInsets.all(24),
                decoration: BoxDecoration(
                  color: Colors.grey.shade50,
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(color: Colors.grey.shade200),
                ),
                child: Column(
                  children: [
                    Icon(
                      Icons.backup_outlined,
                      size: 36,
                      color: Colors.grey.shade300,
                    ),
                    const SizedBox(height: 8),
                    Text(
                      _strings.pick(
                        'Chưa có file backup nào.',
                        'No backup files yet.',
                      ),
                      style: TextStyle(color: Colors.grey.shade500),
                    ),
                  ],
                ),
              )
            else
              ListView.separated(
                shrinkWrap: true,
                physics: const NeverScrollableScrollPhysics(),
                itemCount: _files.length,
                separatorBuilder: (_, __) => const Divider(height: 1),
                itemBuilder: (_, index) {
                  final file = _files[index];
                  final name = file['name'] as String? ?? '';
                  final sizeKb = file['size_kb'] ?? 0;
                  final modified = file['modified'] ?? '';
                  final isFull = name.contains('_full_');
                  return ListTile(
                    dense: true,
                    leading: Container(
                      padding: const EdgeInsets.all(6),
                      decoration: BoxDecoration(
                        color:
                            isFull ? Colors.blue.shade50 : Colors.teal.shade50,
                        borderRadius: BorderRadius.circular(6),
                      ),
                      child: Icon(
                        isFull
                            ? Icons.backup_outlined
                            : Icons.folder_zip_outlined,
                        size: 18,
                        color: isFull
                            ? Colors.blue.shade600
                            : Colors.teal.shade600,
                      ),
                    ),
                    title: Text(name, style: const TextStyle(fontSize: 13)),
                    subtitle: Text(
                      '$sizeKb KB  •  $modified',
                      style: TextStyle(
                        fontSize: 11.5,
                        color: Colors.grey.shade500,
                      ),
                    ),
                    trailing: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        IconButton(
                          icon: Icon(
                            Icons.download_outlined,
                            size: 18,
                            color: Colors.blue.shade600,
                          ),
                          tooltip: _strings.pick('Tải xuống', 'Download'),
                          onPressed: () => _downloadBackup(name),
                        ),
                        IconButton(
                          icon: Icon(
                            Icons.delete_outline,
                            size: 18,
                            color: Colors.red.shade400,
                          ),
                          tooltip: _strings.pick('Xóa', 'Delete'),
                          onPressed: () => _deleteBackup(name),
                        ),
                      ],
                    ),
                  );
                },
              ),
          ],
        ),
      ),
    );
  }
}
