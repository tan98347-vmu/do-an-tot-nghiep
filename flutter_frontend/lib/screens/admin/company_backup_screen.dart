// === MÀN HÌNH SAO LƯU CÔNG TY (R5: mã hóa + chữ ký) ===
// - _CreateBackupTab: tạo backup theo thành phần (backupComponentsProvider) + đặt mật khẩu mã hóa (_SetPasswordWizard -> 'settings/set-password/').
// - _BackupListTab (companyBackupsProvider): tải (download có xác nhận mật khẩu), xác minh chữ ký (_verifySignature 'verify/'), khôi phục (_restore '.../restore/'), xóa (_delete).
// - Cấu hình auto-backup qua companyBackupSettingsProvider.

import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../core/api_client.dart';
import '../../core/download_helper.dart';
import '../../models/company_backup.dart';
import '../../providers/company_backups_provider.dart';
import 'widgets/password_confirm_dialog.dart';
import 'widgets/backup_progress_dialog.dart';
// === BEGIN R5: import ===
import 'widgets/backup_security_badge.dart';
// === END R5 ===

class CompanyBackupScreen extends ConsumerStatefulWidget {
  // Widget màn SAO LƯU CÔNG TY (mã hóa AES-GCM + chữ ký).
  const CompanyBackupScreen({super.key});

  @override
  ConsumerState<CompanyBackupScreen> createState() => _CompanyBackupScreenState();
}

class _CompanyBackupScreenState extends ConsumerState<CompanyBackupScreen>
    with SingleTickerProviderStateMixin {
  late final TabController _tabs = TabController(length: 3, vsync: this);

  // Rời màn: dọn tài nguyên.
  @override
  void dispose() {
    _tabs.dispose();
    super.dispose();
  }

  // Hiện snackbar thông báo (kèm màu).
  void _snack(String m, {Color? color}) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(m), backgroundColor: color),
    );
  }

  // Dựng màn: cấu hình lịch/mật khẩu backup + danh sách bản backup (mỗi bản là _buildCard).
  @override
  Widget build(BuildContext context) {
    final settingsAsync = ref.watch(companyBackupSettingsProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Sao lưu dữ liệu doanh nghiệp'),
        bottom: TabBar(
          controller: _tabs,
          tabs: const [
            Tab(icon: Icon(Icons.list_alt), text: 'Danh sách'),
            Tab(icon: Icon(Icons.add_box_outlined), text: 'Tạo backup'),
            Tab(icon: Icon(Icons.settings_outlined), text: 'Cài đặt'),
          ],
        ),
      ),
      body: settingsAsync.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => Center(child: Text('Lỗi: $e')),
        data: (settings) {
          if (!settings.hasPassword) {
            return _SetPasswordWizard(onDone: () {
              ref.invalidate(companyBackupSettingsProvider);
            });
          }
          return TabBarView(
            controller: _tabs,
            children: [
              _BackupListTab(onSnack: _snack),
              _CreateBackupTab(onSnack: _snack, onCreated: () => _tabs.animateTo(0)),
              _BackupSettingsTab(onSnack: _snack),
            ],
          );
        },
      ),
    );
  }
}


class _SetPasswordWizard extends ConsumerStatefulWidget {
  final VoidCallback onDone;
  const _SetPasswordWizard({required this.onDone});

  @override
  ConsumerState<_SetPasswordWizard> createState() => _SetPasswordWizardState();
}

class _SetPasswordWizardState extends ConsumerState<_SetPasswordWizard> {
  final _pw1 = TextEditingController();
  final _pw2 = TextEditingController();
  bool _saving = false;
  String? _error;

  @override
  void dispose() {
    _pw1.dispose();
    _pw2.dispose();
    super.dispose();
  }

  // Lưu cấu hình tự động sao lưu (lịch, bật/tắt).
  Future<void> _save() async {
    final p1 = _pw1.text.trim();
    final p2 = _pw2.text.trim();
    if (p1.length < 6) {
      setState(() => _error = 'Mật khẩu phải ít nhất 6 ký tự.');
      return;
    }
    if (p1 != p2) {
      setState(() => _error = 'Hai lần nhập không khớp.');
      return;
    }
    setState(() {
      _saving = true;
      _error = null;
    });
    try {
      await ApiClient().dio.post(
        'admin/backups/settings/set-password/',
        data: {'new_password': p1},
      );
      widget.onDone();
    } on DioException catch (e) {
      final d = e.response?.data;
      setState(() => _error = (d is Map ? d['detail']?.toString() : null) ?? e.message);
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Center(
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 480),
        child: Card(
          margin: const EdgeInsets.all(20),
          child: Padding(
            padding: const EdgeInsets.all(20),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Row(children: [
                  Icon(Icons.security, size: 28, color: Colors.blue),
                  SizedBox(width: 10),
                  Expanded(
                    child: Text(
                      'Thiết lập mật khẩu backup',
                      style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
                    ),
                  ),
                ]),
                const SizedBox(height: 8),
                const Text(
                  'Mọi hành động tạo/khôi phục/xoá backup đều yêu cầu mật khẩu này. '
                  'Vui lòng ghi nhớ — không thể khôi phục nếu quên.',
                  style: TextStyle(fontSize: 13, color: Colors.grey),
                ),
                const SizedBox(height: 16),
                TextField(
                  controller: _pw1,
                  obscureText: true,
                  decoration: const InputDecoration(
                    labelText: 'Mật khẩu mới (≥ 6 ký tự)',
                    border: OutlineInputBorder(),
                  ),
                ),
                const SizedBox(height: 10),
                TextField(
                  controller: _pw2,
                  obscureText: true,
                  decoration: InputDecoration(
                    labelText: 'Nhập lại mật khẩu',
                    border: const OutlineInputBorder(),
                    errorText: _error,
                  ),
                ),
                const SizedBox(height: 16),
                Align(
                  alignment: Alignment.centerRight,
                  child: FilledButton.icon(
                    icon: _saving
                        ? const SizedBox(width: 14, height: 14, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                        : const Icon(Icons.save),
                    label: const Text('Lưu mật khẩu'),
                    onPressed: _saving ? null : _save,
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}


class _BackupListTab extends ConsumerWidget {
  final void Function(String, {Color? color}) onSnack;
  const _BackupListTab({required this.onSnack});

  // Màu badge theo trạng thái bản backup.
  Color _statusColor(String s) => switch (s) {
        'ready' => Colors.green,
        'creating' => Colors.blue,
        'restoring' => Colors.orange,
        'restored' => Colors.teal,
        'failed' => Colors.red,
        _ => Colors.grey,
      };

  // Màu theo loại backup (tự động/thủ công).
  Color _kindColor(String k) => k == 'auto' ? Colors.indigo : Colors.deepPurple;

  // Tải bản backup về máy (có xác nhận _confirmDownload).
  Future<void> _download(BuildContext context, CompanyBackup b) async {
    final pw = await PasswordConfirmDialog.show(
      context,
      title: 'Tải về bản backup',
      description: 'Tệp .zip này có thể chứa dữ liệu nhạy cảm. Hãy bảo quản cẩn thận.',
      actionLabel: 'Tải về',
    );
    if (pw == null) return;
    try {
      onSnack('Đang tải ${b.name}...');
      final resp = await ApiClient().dio.get<List<int>>(
        'admin/backups/${b.id}/download/',
        options: Options(
          responseType: ResponseType.bytes,
          headers: {'X-Backup-Password': pw},
        ),
      );
      final bytes = resp.data;
      if (bytes == null || bytes.isEmpty) {
        onSnack('Server không trả về dữ liệu file.', color: Colors.red);
        return;
      }
      downloadBlob(bytes, b.name, 'application/zip');
      onSnack('Đã tải ${b.name}', color: Colors.green);
    } on DioException catch (e) {
      final d = e.response?.data;
      String msg = e.message ?? 'Lỗi tải file';
      if (d is Map && d['detail'] != null) msg = '${d['detail']}';
      onSnack(msg, color: Colors.red);
    } catch (e) {
      onSnack('Lỗi tải file: $e', color: Colors.red);
    }
  }

  // === BEGIN R5: confirm download + verify signature ===
  Future<void> _confirmDownload(BuildContext context, CompanyBackup b) async {
    final ok = await showDialog<bool>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        icon: const Icon(Icons.security, color: Colors.orange),
        title: const Text('Tải bản backup'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'File giải mã chứa dữ liệu nhạy cảm của công ty. Không chia sẻ ra ngoài.',
            ),
            const SizedBox(height: 8),
            if (b.isEncrypted)
              const Text(
                'File trên đĩa được mã hóa AES-256-GCM. Server sẽ giải mã streaming khi tải.',
                style: TextStyle(color: Colors.grey, fontSize: 12),
              ),
            if (b.signatureStatus == 'signed')
              const Text(
                'Server sẽ verify chữ ký số trước khi giải mã.',
                style: TextStyle(color: Colors.grey, fontSize: 12),
              ),
            if (b.signatureStatus == 'invalid')
              const Text(
                'CẢNH BÁO: Chữ ký không hợp lệ — backup có thể bị thay đổi.',
                style: TextStyle(color: Colors.red, fontWeight: FontWeight.bold, fontSize: 12),
              ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(dialogContext).pop(false),
            child: const Text('Hủy'),
          ),
          FilledButton(
            onPressed: () => Navigator.of(dialogContext).pop(true),
            child: const Text('Tiếp tục'),
          ),
        ],
      ),
    );
    if (!context.mounted || ok != true) return;
    await _download(context, b);
  }

  // Xác minh chữ ký số của bản backup (đảm bảo toàn vẹn).
  Future<void> _verifySignature(BuildContext context, WidgetRef ref, CompanyBackup b) async {
    // Yeu cau password admin de decrypt + verify chu ky.
    final pw = await PasswordConfirmDialog.show(
      context,
      title: 'Kiểm tra chữ ký',
      description:
          'Nhập mật khẩu backup để giải mã + verify chữ ký bằng public key của bạn.',
      actionLabel: 'Kiểm tra',
    );
    if (pw == null) return;
    onSnack('Đang kiểm tra chữ ký...');
    try {
      final resp = await ApiClient().dio.post(
        'admin/backups/${b.id}/verify/',
        data: {'password': pw},
      );
      final data = Map<String, dynamic>.from(resp.data as Map);
      final ok = data['ok'] == true;
      final details = (data['details'] ?? '').toString();
      if (!context.mounted) return;
      await showDialog<void>(
        context: context,
        builder: (dialogContext) => AlertDialog(
          icon: Icon(ok ? Icons.verified_user : Icons.gpp_bad,
              color: ok ? Colors.green : Colors.red, size: 32),
          title: Text(ok ? 'Chữ ký hợp lệ' : 'Chữ ký KHÔNG hợp lệ'),
          content: Text(details.isEmpty ? '—' : details),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(dialogContext).pop(),
              child: const Text('Đóng'),
            ),
          ],
        ),
      );
      ref.invalidate(companyBackupsProvider);
    } on DioException catch (e) {
      final d = e.response?.data;
      onSnack((d is Map ? d['detail']?.toString() : null) ?? 'Lỗi: ${e.message}', color: Colors.red);
    }
  }
  // === END R5 ===

  Future<void> _restore(BuildContext context, WidgetRef ref, CompanyBackup b) async {
    final ok = await showDialog<bool>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: const Text('Khôi phục dữ liệu?'),
        content: Text(
          'Khôi phục từ "${b.name}" sẽ XOÁ toàn bộ dữ liệu hiện tại của công ty trong scope các thành phần backup, rồi tải lại từ file. Hành động này KHÔNG thể hoàn tác.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(dialogContext).pop(false),
            child: const Text('Huỷ'),
          ),
          FilledButton(
            style: FilledButton.styleFrom(backgroundColor: Colors.red),
            onPressed: () => Navigator.of(dialogContext).pop(true),
            child: const Text('Tôi hiểu, tiếp tục'),
          ),
        ],
      ),
    );
    if (!context.mounted || ok != true) return;
    final pw = await PasswordConfirmDialog.show(
      context,
      title: 'Xác nhận khôi phục',
      description: 'Nhập mật khẩu backup để xác nhận lần cuối.',
      actionLabel: 'Khôi phục',
      actionColor: Colors.red,
    );
    if (pw == null) return;
    try {
      await ApiClient().dio.post('admin/backups/${b.id}/restore/', data: {'password': pw});
      ref.invalidate(companyBackupsProvider);
      onSnack('Đã khôi phục.', color: Colors.green);
    } on DioException catch (e) {
      final d = e.response?.data;
      onSnack((d is Map ? d['detail']?.toString() : null) ?? 'Lỗi: ${e.message}', color: Colors.red);
    }
  }

  // Xóa 1 bản backup (có xác nhận).
  Future<void> _delete(BuildContext context, WidgetRef ref, CompanyBackup b) async {
    final pw = await PasswordConfirmDialog.show(
      context,
      title: 'Xoá bản backup?',
      description: 'Hành động này xoá file .zip vĩnh viễn.',
      actionLabel: 'Xoá',
      actionColor: Colors.red,
    );
    if (pw == null) return;
    try {
      await ApiClient().dio.delete('admin/backups/${b.id}/', data: {'password': pw});
      ref.invalidate(companyBackupsProvider);
      onSnack('Đã xoá.', color: Colors.orange);
    } on DioException catch (e) {
      final d = e.response?.data;
      onSnack((d is Map ? d['detail']?.toString() : null) ?? 'Lỗi: ${e.message}', color: Colors.red);
    }
  }

  // Thẻ 1 bản backup: thời điểm, loại, trạng thái + nút Tải/Xác minh/Khôi phục/Xóa.
  Widget _buildCard(BuildContext context, WidgetRef ref, CompanyBackup b, bool compact) {
    final titleSize = compact ? 13.0 : 14.0;
    return Card(
      margin: const EdgeInsets.only(bottom: 8),
      child: Padding(
        padding: EdgeInsets.symmetric(horizontal: compact ? 10 : 14, vertical: compact ? 8 : 12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
              const Icon(Icons.archive_outlined, color: Colors.blueGrey, size: 20),
              const SizedBox(width: 8),
              Expanded(
                child: Text(b.name,
                    style: TextStyle(fontWeight: FontWeight.bold, fontSize: titleSize, fontFamily: 'monospace'),
                    overflow: TextOverflow.ellipsis),
              ),
            ]),
            const SizedBox(height: 6),
            Wrap(spacing: 6, runSpacing: 4, children: [
              _badge(b.kindLabel, _kindColor(b.kind)),
              _badge(b.statusLabel, _statusColor(b.status)),
              _badge(b.sizeDisplay, Colors.grey),
            ]),
            const SizedBox(height: 6),
            // === BEGIN R5: security badges ===
            BackupSecurityBadge(
              isEncrypted: b.isEncrypted,
              signatureStatus: b.signatureStatus,
              algorithm: b.encryptionAlgorithm,
              compact: compact,
            ),
            const SizedBox(height: 6),
            // === END R5 ===
            DefaultTextStyle(
              style: const TextStyle(fontSize: 11, color: Colors.grey),
              child: Wrap(spacing: 12, runSpacing: 2, children: [
                Text('Tạo: ${_fmt(b.createdAt)}'),
                if (b.createdByName.isNotEmpty) Text('Bởi: ${b.createdByName}'),
                if (b.restoredAt != null) Text('Khôi phục: ${_fmt(b.restoredAt!)}'),
                if (b.components.isNotEmpty) Text('Components: ${b.components.length}'),
              ]),
            ),
            if (b.errorMessage.isNotEmpty)
              Container(
                margin: const EdgeInsets.only(top: 6),
                padding: const EdgeInsets.all(6),
                color: Colors.red.shade50,
                child: Text(b.errorMessage,
                    style: const TextStyle(fontSize: 11, color: Colors.red)),
              ),
            const SizedBox(height: 8),
            Wrap(spacing: 6, runSpacing: 4, children: [
              OutlinedButton.icon(
                icon: const Icon(Icons.download, size: 16),
                label: const Text('Tải về'),
                onPressed: b.status == 'ready' ? () => _confirmDownload(context, b) : null,
              ),
              OutlinedButton.icon(
                icon: const Icon(Icons.restore, size: 16),
                label: const Text('Khôi phục'),
                style: OutlinedButton.styleFrom(foregroundColor: Colors.red),
                onPressed: (b.status == 'ready' || b.status == 'restored')
                    ? () => _restore(context, ref, b)
                    : null,
              ),
              // === BEGIN R5: verify button ===
              if (b.hasSignature)
                OutlinedButton.icon(
                  icon: const Icon(Icons.fact_check, size: 16),
                  label: const Text('Kiểm tra chữ ký'),
                  onPressed: () => _verifySignature(context, ref, b),
                ),
              // === END R5 ===
              OutlinedButton.icon(
                icon: const Icon(Icons.delete_outline, size: 16),
                label: const Text('Xoá'),
                style: OutlinedButton.styleFrom(foregroundColor: Colors.red),
                onPressed: () => _delete(context, ref, b),
              ),
            ]),
          ],
        ),
      ),
    );
  }

  Widget _badge(String label, Color color) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
        decoration: BoxDecoration(
          color: color.withOpacity(0.15),
          borderRadius: BorderRadius.circular(4),
        ),
        child: Text(label,
            style: TextStyle(fontSize: 10.5, color: color, fontWeight: FontWeight.w600)),
      );

  // Định dạng thời điểm bản backup để hiển thị.
  String _fmt(String iso) {
    if (iso.isEmpty) return '';
    try {
      final dt = DateTime.parse(iso).toLocal();
      final d = dt.day.toString().padLeft(2, '0');
      final m = dt.month.toString().padLeft(2, '0');
      final h = dt.hour.toString().padLeft(2, '0');
      final mi = dt.minute.toString().padLeft(2, '0');
      return '$d/$m/${dt.year} $h:$mi';
    } catch (_) {
      return iso;
    }
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final asyncList = ref.watch(companyBackupsProvider);
    return LayoutBuilder(builder: (context, c) {
      final compact = c.maxWidth < 700;
      return RefreshIndicator(
        onRefresh: () async {
          ref.invalidate(companyBackupsProvider);
          await Future<void>.delayed(const Duration(milliseconds: 200));
        },
        child: asyncList.when(
          loading: () => const Center(child: CircularProgressIndicator()),
          error: (e, _) => Center(child: Text('Lỗi: $e')),
          data: (list) {
            if (list.isEmpty) {
              return ListView(children: [
                Padding(
                  padding: const EdgeInsets.all(40),
                  child: Center(
                    child: Column(children: [
                      Icon(Icons.archive_outlined, size: 56, color: Colors.grey.shade400),
                      const SizedBox(height: 8),
                      const Text('Chưa có bản backup nào. Vào tab "Tạo backup" để tạo bản đầu tiên.',
                          style: TextStyle(color: Colors.grey), textAlign: TextAlign.center),
                    ]),
                  ),
                ),
              ]);
            }
            return ListView.builder(
              padding: EdgeInsets.all(compact ? 12 : 20),
              itemCount: list.length,
              itemBuilder: (_, i) => _buildCard(context, ref, list[i], compact),
            );
          },
        ),
      );
    });
  }
}


class _CreateBackupTab extends ConsumerStatefulWidget {
  final void Function(String, {Color? color}) onSnack;
  final VoidCallback onCreated;
  const _CreateBackupTab({required this.onSnack, required this.onCreated});

  @override
  ConsumerState<_CreateBackupTab> createState() => _CreateBackupTabState();
}

class _CreateBackupTabState extends ConsumerState<_CreateBackupTab> {
  final Set<String> _selected = {};
  bool _creating = false;

  // Nút Tạo backup ngay: tạo bản sao lưu thủ công.
  Future<void> _create() async {
    if (_selected.isEmpty) {
      widget.onSnack('Vui lòng chọn ít nhất 1 thành phần.', color: Colors.orange);
      return;
    }
    final pw = await PasswordConfirmDialog.show(
      context,
      title: 'Xác nhận tạo backup',
      description: 'Tạo backup ${_selected.length} thành phần. Có thể mất 1-2 phút.',
      actionLabel: 'Tạo',
    );
    if (pw == null) return;
    setState(() => _creating = true);
    int? backupId;
    String? backupName;
    try {
      final resp = await ApiClient().dio.post(
        'admin/backups/',
        data: {'components': _selected.toList(), 'password': pw},
      );
      final data = Map<String, dynamic>.from(resp.data as Map);
      backupId = data['id'] as int?;
      backupName = (data['name'] ?? '') as String;
      ref.invalidate(companyBackupsProvider);
    } on DioException catch (e) {
      final d = e.response?.data;
      widget.onSnack((d is Map ? d['detail']?.toString() : null) ?? 'Lỗi: ${e.message}',
          color: Colors.red);
    } finally {
      if (mounted) setState(() => _creating = false);
    }

    if (!mounted || backupId == null) return;
    final result = await BackupProgressDialog.show(
      context,
      backupId: backupId,
      fileName: backupName ?? '',
    );
    if (!mounted) return;
    ref.invalidate(companyBackupsProvider);
    if (result?.success == true) {
      widget.onSnack('Đã tạo backup thành công.', color: Colors.green);
      setState(() => _selected.clear());
      widget.onCreated();
    } else if (result != null && !result.success) {
      widget.onSnack(
        result.message.isEmpty ? 'Backup đang chạy nền.' : result.message,
        color: result.message.contains('nền') ? Colors.blue : Colors.red,
      );
      widget.onCreated();
    }
  }

  @override
  Widget build(BuildContext context) {
    final compsAsync = ref.watch(backupComponentsProvider);
    return SingleChildScrollView(
      padding: const EdgeInsets.all(20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text('Chọn các thành phần cần sao lưu',
              style: TextStyle(fontWeight: FontWeight.bold, fontSize: 15)),
          const SizedBox(height: 8),
          compsAsync.when(
            loading: () => const LinearProgressIndicator(),
            error: (e, _) => Text('Lỗi: $e', style: const TextStyle(color: Colors.red)),
            data: (list) {
              return Column(children: [
                Row(children: [
                  TextButton.icon(
                    icon: const Icon(Icons.select_all, size: 16),
                    label: const Text('Chọn tất cả'),
                    onPressed: () => setState(() {
                      _selected
                        ..clear()
                        ..addAll(list.map((c) => c.key));
                    }),
                  ),
                  const SizedBox(width: 8),
                  TextButton.icon(
                    icon: const Icon(Icons.deselect, size: 16),
                    label: const Text('Bỏ chọn'),
                    onPressed: () => setState(() => _selected.clear()),
                  ),
                  const Spacer(),
                  Text('${_selected.length}/${list.length}',
                      style: const TextStyle(color: Colors.grey, fontSize: 12)),
                ]),
                const SizedBox(height: 8),
                ...list.map((c) {
                  final isChecked = _selected.contains(c.key);
                  return Card(
                    margin: const EdgeInsets.only(bottom: 6),
                    child: CheckboxListTile(
                      value: isChecked,
                      onChanged: (v) {
                        setState(() {
                          if (v == true) {
                            _selected.add(c.key);
                          } else {
                            _selected.remove(c.key);
                          }
                        });
                      },
                      title: Text(c.label, style: const TextStyle(fontWeight: FontWeight.w600)),
                      subtitle: Text(c.key, style: const TextStyle(fontSize: 11, color: Colors.grey)),
                      dense: true,
                    ),
                  );
                }),
              ]);
            },
          ),
          const SizedBox(height: 20),
          Align(
            alignment: Alignment.centerRight,
            child: FilledButton.icon(
              icon: _creating
                  ? const SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                  : const Icon(Icons.archive_outlined),
              label: Text(_creating ? 'Đang tạo...' : 'Tạo backup'),
              onPressed: _creating ? null : _create,
            ),
          ),
        ],
      ),
    );
  }
}


class _BackupSettingsTab extends ConsumerStatefulWidget {
  final void Function(String, {Color? color}) onSnack;
  const _BackupSettingsTab({required this.onSnack});

  @override
  ConsumerState<_BackupSettingsTab> createState() => _BackupSettingsTabState();
}

class _BackupSettingsTabState extends ConsumerState<_BackupSettingsTab> {
  bool? _autoEnabled;
  int? _intervalDays;
  int? _retention;
  bool? _notify;
  bool _saving = false;

  Future<void> _save(CompanyBackupSettings current) async {
    final pw = await PasswordConfirmDialog.show(
      context,
      title: 'Xác nhận thay đổi cài đặt',
      description: 'Nhập mật khẩu backup để lưu thay đổi.',
      actionLabel: 'Lưu',
    );
    if (pw == null) return;
    setState(() => _saving = true);
    try {
      await ApiClient().dio.put(
        'admin/backups/settings/',
        data: {
          'auto_enabled': _autoEnabled ?? current.autoEnabled,
          'auto_interval_days': _intervalDays ?? current.autoIntervalDays,
          'retention_count': _retention ?? current.retentionCount,
          'notify_admin_email': _notify ?? current.notifyAdminEmail,
          'password': pw,
        },
      );
      ref.invalidate(companyBackupSettingsProvider);
      widget.onSnack('Đã lưu cài đặt.', color: Colors.green);
    } on DioException catch (e) {
      final d = e.response?.data;
      widget.onSnack((d is Map ? d['detail']?.toString() : null) ?? 'Lỗi: ${e.message}',
          color: Colors.red);
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  // Đổi mật khẩu mã hóa backup của công ty.
  Future<void> _changePassword() async {
    final ctrlOld = TextEditingController();
    final ctrlNew = TextEditingController();
    final ctrlNew2 = TextEditingController();
    final ok = await showDialog<bool>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: const Text('Đổi mật khẩu backup'),
        content: SizedBox(
          width: 400,
          child: Column(mainAxisSize: MainAxisSize.min, children: [
            TextField(controller: ctrlOld, obscureText: true, decoration: const InputDecoration(labelText: 'Mật khẩu hiện tại', border: OutlineInputBorder())),
            const SizedBox(height: 8),
            TextField(controller: ctrlNew, obscureText: true, decoration: const InputDecoration(labelText: 'Mật khẩu mới', border: OutlineInputBorder())),
            const SizedBox(height: 8),
            TextField(controller: ctrlNew2, obscureText: true, decoration: const InputDecoration(labelText: 'Nhập lại mật khẩu mới', border: OutlineInputBorder())),
          ]),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(dialogContext).pop(false),
            child: const Text('Huỷ'),
          ),
          FilledButton(
            onPressed: () => Navigator.of(dialogContext).pop(true),
            child: const Text('Đổi'),
          ),
        ],
      ),
    );
    if (!mounted || ok != true) return;
    if (ctrlNew.text != ctrlNew2.text) {
      widget.onSnack('Hai lần nhập mật khẩu mới không khớp.', color: Colors.red);
      return;
    }
    try {
      await ApiClient().dio.post(
        'admin/backups/settings/set-password/',
        data: {'current_password': ctrlOld.text, 'new_password': ctrlNew.text},
      );
      widget.onSnack('Đã đổi mật khẩu backup.', color: Colors.green);
    } on DioException catch (e) {
      final d = e.response?.data;
      widget.onSnack((d is Map ? d['detail']?.toString() : null) ?? 'Lỗi: ${e.message}',
          color: Colors.red);
    }
  }

  @override
  Widget build(BuildContext context) {
    final settingsAsync = ref.watch(companyBackupSettingsProvider);
    return settingsAsync.when(
      loading: () => const Center(child: CircularProgressIndicator()),
      error: (e, _) => Center(child: Text('Lỗi: $e')),
      data: (s) {
        _autoEnabled ??= s.autoEnabled;
        _intervalDays ??= s.autoIntervalDays;
        _retention ??= s.retentionCount;
        _notify ??= s.notifyAdminEmail;
        return SingleChildScrollView(
          padding: const EdgeInsets.all(20),
          child: Center(
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 720),
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                const Text('Backup tự động',
                    style: TextStyle(fontWeight: FontWeight.bold, fontSize: 15)),
                const SizedBox(height: 8),
                Card(
                  child: Column(children: [
                    SwitchListTile(
                      title: const Text('Bật backup tự động'),
                      subtitle: const Text('Hệ thống tự tạo backup TOÀN BỘ định kỳ.'),
                      value: _autoEnabled!,
                      onChanged: (v) => setState(() => _autoEnabled = v),
                    ),
                    const Divider(height: 1),
                    ListTile(
                      title: const Text('Chu kỳ backup'),
                      subtitle: DropdownButton<int>(
                        value: _intervalDays,
                        items: const [
                          DropdownMenuItem(value: 7, child: Text('Hàng tuần (7 ngày)')),
                          DropdownMenuItem(value: 14, child: Text('Mỗi 2 tuần (14 ngày)')),
                          DropdownMenuItem(value: 30, child: Text('Hàng tháng (30 ngày) — mặc định')),
                          DropdownMenuItem(value: 60, child: Text('Mỗi 2 tháng (60 ngày)')),
                          DropdownMenuItem(value: 90, child: Text('Quý (90 ngày)')),
                        ],
                        onChanged: (v) => setState(() => _intervalDays = v),
                      ),
                    ),
                    const Divider(height: 1),
                    ListTile(
                      title: const Text('Số bản giữ lại (retention)'),
                      subtitle: DropdownButton<int>(
                        value: _retention,
                        items: const [
                          DropdownMenuItem(value: 6, child: Text('6 bản gần nhất')),
                          DropdownMenuItem(value: 12, child: Text('12 bản gần nhất — mặc định')),
                          DropdownMenuItem(value: 24, child: Text('24 bản gần nhất')),
                          DropdownMenuItem(value: 60, child: Text('60 bản gần nhất')),
                        ],
                        onChanged: (v) => setState(() => _retention = v),
                      ),
                    ),
                    if (s.lastAutoRunAt != null)
                      ListTile(
                        leading: const Icon(Icons.access_time),
                        title: const Text('Lần auto backup gần nhất'),
                        subtitle: Text(s.lastAutoRunAt!),
                      ),
                  ]),
                ),
                const SizedBox(height: 20),
                Align(
                  alignment: Alignment.centerRight,
                  child: FilledButton.icon(
                    icon: _saving
                        ? const SizedBox(width: 14, height: 14, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                        : const Icon(Icons.save),
                    label: const Text('Lưu cài đặt'),
                    onPressed: _saving ? null : () => _save(s),
                  ),
                ),
                const SizedBox(height: 28),
                const Text('Bảo mật',
                    style: TextStyle(fontWeight: FontWeight.bold, fontSize: 15)),
                const SizedBox(height: 8),
                Card(
                  child: ListTile(
                    leading: const Icon(Icons.lock_outline),
                    title: const Text('Đổi mật khẩu backup'),
                    subtitle: const Text('Đổi mật khẩu xác nhận cho mọi hành động backup/restore/xoá.'),
                    trailing: const Icon(Icons.chevron_right),
                    onTap: _changePassword,
                  ),
                ),
              ]),
            ),
          ),
        );
      },
    );
  }
}
