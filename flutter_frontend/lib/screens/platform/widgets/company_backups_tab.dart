// === TAB SAO LƯU CÔNG TY (trong chi tiết công ty, platform-admin) ===
// Hiển thị bản backup gần nhất (_LastBackupCard) + trạng thái (_StatusChip); dẫn tới trang quản trị (/admin).

// r5/M9 + M10 — Tab Backup: hien thi last_backup + badge ma hoa/ky so.

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../models/company_dashboard.dart';
import '../../admin/widgets/backup_security_badge.dart';

class CompanyBackupsTab extends ConsumerWidget {
  final int companyId;
  final CompanyDashboard dashboard;
  const CompanyBackupsTab({super.key, required this.companyId, required this.dashboard});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final last = dashboard.lastBackup;
    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          if (last == null)
            Card(
              child: Padding(
                padding: const EdgeInsets.all(24),
                child: Column(
                  children: [
                    const Icon(Icons.backup_outlined, size: 48, color: Colors.grey),
                    const SizedBox(height: 12),
                    const Text(
                      'Công ty này chưa có backup nào.',
                      style: TextStyle(fontWeight: FontWeight.bold),
                    ),
                    const SizedBox(height: 8),
                    const Text(
                      'Đăng nhập tài khoản admin của công ty để tạo backup đầu tiên.',
                      style: TextStyle(color: Colors.grey),
                      textAlign: TextAlign.center,
                    ),
                    const SizedBox(height: 12),
                    FilledButton.icon(
                      icon: const Icon(Icons.open_in_new),
                      label: const Text('Mở trang Admin'),
                      onPressed: () => context.go('/admin'),
                    ),
                  ],
                ),
              ),
            )
          else
            _LastBackupCard(backup: last),
          const SizedBox(height: 16),
          const Card(
            child: Padding(
              padding: EdgeInsets.all(12),
              child: Row(
                children: [
                  Icon(Icons.info_outline, color: Colors.blueGrey),
                  SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      'Để xem danh sách 10+ backup gần nhất, tải/khôi phục, '
                      'kiểm tra chữ ký số chi tiết — vui lòng mở trang Admin '
                      'với tài khoản admin của công ty.',
                    ),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _LastBackupCard extends StatelessWidget {
  final LastBackupInfo backup;
  const _LastBackupCard({required this.backup});

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Icon(Icons.backup, size: 24),
                const SizedBox(width: 8),
                const Text('Backup gần nhất',
                    style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
                const Spacer(),
                _StatusChip(status: backup.status),
              ],
            ),
            const SizedBox(height: 12),
            BackupSecurityBadge(
              isEncrypted: backup.isEncrypted,
              signatureStatus: backup.signatureStatus,
            ),
            const SizedBox(height: 16),
            _Row(label: 'Tên file', value: backup.name),
            _Row(label: 'Loại', value: backup.kind == 'auto' ? 'Tự động' : 'Thủ công'),
            _Row(label: 'Kích thước', value: formatBytes(backup.sizeBytes)),
            _Row(label: 'Tạo lúc', value: _formatDate(backup.createdAt)),
            if (backup.completedAt != null)
              _Row(label: 'Hoàn tất lúc', value: _formatDate(backup.completedAt)),
          ],
        ),
      ),
    );
  }

  static String _formatDate(String? raw) {
    if (raw == null || raw.isEmpty) return '—';
    try {
      final dt = DateTime.parse(raw).toLocal();
      return '${dt.day.toString().padLeft(2, '0')}/${dt.month.toString().padLeft(2, '0')}/${dt.year} '
          '${dt.hour.toString().padLeft(2, '0')}:${dt.minute.toString().padLeft(2, '0')}';
    } catch (_) {
      return raw;
    }
  }
}

class _Row extends StatelessWidget {
  final String label;
  final String value;
  const _Row({required this.label, required this.value});
  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 3),
        child: Row(
          children: [
            SizedBox(width: 110, child: Text(label, style: const TextStyle(color: Colors.grey, fontSize: 13))),
            Expanded(child: SelectableText(value)),
          ],
        ),
      );
}

class _StatusChip extends StatelessWidget {
  final String status;
  const _StatusChip({required this.status});
  @override
  Widget build(BuildContext context) {
    final (color, label) = switch (status) {
      'ready' => (Colors.green, 'Sẵn sàng'),
      'creating' => (Colors.blue, 'Đang tạo'),
      'failed' => (Colors.red, 'Thất bại'),
      'restoring' => (Colors.orange, 'Đang khôi phục'),
      'restored' => (Colors.green, 'Đã khôi phục'),
      'deleted' => (Colors.grey, 'Đã xoá'),
      _ => (Colors.grey, status),
    };
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.15),
        border: Border.all(color: color),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Text(label, style: TextStyle(color: color, fontWeight: FontWeight.bold, fontSize: 12)),
    );
  }
}
