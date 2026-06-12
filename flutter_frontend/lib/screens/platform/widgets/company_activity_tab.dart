// === TAB HOẠT ĐỘNG CÔNG TY (trong chi tiết công ty) ===
// Hiển thị nhật ký hoạt động gần đây của công ty (companyActivityProvider) dạng danh sách _ActivityTile.

// r5/M9 — Tab Hoat dong: timeline 20 entry gan nhat.

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../models/company_dashboard.dart';
import '../../../providers/company_dashboard_provider.dart';

class CompanyActivityTab extends ConsumerWidget {
  final int companyId;
  const CompanyActivityTab({super.key, required this.companyId});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final async = ref.watch(companyActivityProvider(companyId));
    return async.when(
      loading: () => const Center(child: CircularProgressIndicator()),
      error: (e, _) => Center(
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Icon(Icons.error_outline, color: Colors.red, size: 32),
              const SizedBox(height: 8),
              Text('Lỗi: $e'),
              const SizedBox(height: 12),
              FilledButton.icon(
                icon: const Icon(Icons.refresh),
                label: const Text('Thử lại'),
                onPressed: () => ref.invalidate(companyActivityProvider(companyId)),
              ),
            ],
          ),
        ),
      ),
      data: (items) {
        if (items.isEmpty) {
          return const Center(
            child: Padding(
              padding: EdgeInsets.all(32),
              child: Text(
                'Chưa có hoạt động nào được ghi lại.',
                style: TextStyle(color: Colors.grey),
              ),
            ),
          );
        }
        return ListView.separated(
          padding: const EdgeInsets.all(16),
          itemCount: items.length,
          separatorBuilder: (_, __) => const Divider(height: 1),
          itemBuilder: (_, i) => _ActivityTile(item: items[i]),
        );
      },
    );
  }
}

class _ActivityTile extends StatelessWidget {
  final CompanyActivity item;
  const _ActivityTile({required this.item});

  static const _icons = <String, IconData>{
    'backup_created': Icons.backup,
    'backup_restored': Icons.restore,
    'import_batch': Icons.upload_file,
    'user_added': Icons.person_add,
  };

  @override
  Widget build(BuildContext context) {
    final icon = _icons[item.action] ?? Icons.fiber_manual_record;
    return ListTile(
      leading: CircleAvatar(
        backgroundColor: Theme.of(context).colorScheme.primary,
        child: Icon(icon, color: Colors.white, size: 18),
      ),
      title: Text(item.detail),
      subtitle: Text('${_formatDate(item.at)} • ${item.actor.isEmpty ? "(hệ thống)" : item.actor}'),
      dense: true,
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
