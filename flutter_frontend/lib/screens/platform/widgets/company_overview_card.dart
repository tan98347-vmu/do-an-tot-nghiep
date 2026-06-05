// r5/M9 — Info card hien thi tat ca metadata cua 1 cong ty.

import 'package:flutter/material.dart';
import '../../../models/company_dashboard.dart';

class CompanyOverviewCard extends StatelessWidget {
  final CompanyDashboard dashboard;
  const CompanyOverviewCard({super.key, required this.dashboard});

  @override
  Widget build(BuildContext context) {
    final c = dashboard.company;
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                _Avatar(name: c.name),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(c.name, style: Theme.of(context).textTheme.titleLarge),
                      const SizedBox(height: 4),
                      Row(
                        children: [
                          _StatusBadge(status: c.status, label: c.statusLabel),
                          const SizedBox(width: 8),
                          Text('Mã: ${c.code}', style: const TextStyle(color: Colors.grey)),
                        ],
                      ),
                    ],
                  ),
                ),
              ],
            ),
            const SizedBox(height: 16),
            const Divider(),
            _Row(label: 'Slug', value: c.slug.isEmpty ? '—' : c.slug),
            _Row(label: 'Lĩnh vực', value: c.industry.isEmpty ? '—' : c.industry),
            _Row(label: 'Địa chỉ', value: c.address.isEmpty ? '—' : c.address),
            _Row(label: 'Email', value: c.email.isEmpty ? '—' : c.email),
            _Row(label: 'Điện thoại', value: c.phone.isEmpty ? '—' : c.phone),
            _Row(label: 'Website', value: c.website.isEmpty ? '—' : c.website),
            _Row(label: 'Ngày tạo', value: _formatDate(c.createdAt)),
            _Row(label: 'Cập nhật', value: _formatDate(c.updatedAt)),
            if (c.companyContext.trim().isNotEmpty) ...[
              const SizedBox(height: 12),
              const Text('Ngữ cảnh:', style: TextStyle(fontWeight: FontWeight.bold)),
              const SizedBox(height: 4),
              Container(
                width: double.infinity,
                padding: const EdgeInsets.all(8),
                decoration: BoxDecoration(
                  color: Theme.of(context).colorScheme.surfaceContainerHighest,
                  borderRadius: BorderRadius.circular(6),
                ),
                child: Text(c.companyContext),
              ),
            ],
            if (c.description.trim().isNotEmpty) ...[
              const SizedBox(height: 12),
              const Text('Mô tả:', style: TextStyle(fontWeight: FontWeight.bold)),
              const SizedBox(height: 4),
              Text(c.description, style: const TextStyle(color: Colors.black87)),
            ],
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
        padding: const EdgeInsets.symmetric(vertical: 4),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            SizedBox(
              width: 110,
              child: Text(label, style: const TextStyle(color: Colors.grey, fontSize: 13)),
            ),
            Expanded(child: SelectableText(value)),
          ],
        ),
      );
}

class _Avatar extends StatelessWidget {
  final String name;
  const _Avatar({required this.name});

  @override
  Widget build(BuildContext context) {
    final initials = _initials(name);
    return CircleAvatar(
      radius: 28,
      backgroundColor: Theme.of(context).colorScheme.primary,
      child: Text(
        initials,
        style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 18),
      ),
    );
  }

  static String _initials(String s) {
    if (s.isEmpty) return '?';
    final parts = s.trim().split(RegExp(r'\s+'));
    if (parts.length == 1) return parts.first.substring(0, parts.first.length >= 2 ? 2 : 1).toUpperCase();
    return (parts.first.characters.first + parts.last.characters.first).toUpperCase();
  }
}

class _StatusBadge extends StatelessWidget {
  final String status;
  final String label;
  const _StatusBadge({required this.status, required this.label});

  @override
  Widget build(BuildContext context) {
    final color = switch (status) {
      'active' => Colors.green,
      'draft' => Colors.blue,
      'locked' => Colors.orange,
      'archived' => Colors.grey,
      'deleted' => Colors.red,
      _ => Colors.grey,
    };
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.15),
        border: Border.all(color: color),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Text(
        label,
        style: TextStyle(color: color, fontWeight: FontWeight.bold, fontSize: 12),
      ),
    );
  }
}
