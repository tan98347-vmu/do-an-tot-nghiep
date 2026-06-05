// Bộ lọc bổ sung dùng chung: khoảng ngày + lọc theo người (linh hoạt nhãn).
// Dùng cho các màn Ký số (Yêu cầu ký / PDF đã ký / Hòm thư) — lọc client-side
// trên danh sách đã tải. Nhãn "người" thay đổi theo màn (người ký / người gửi /
// người xử lý) qua tham số [personLabel].

import 'package:flutter/material.dart';

class ListFilterExtras extends StatelessWidget {
  final DateTime? dateFrom;
  final DateTime? dateTo;
  final ValueChanged<DateTime?> onDateFrom;
  final ValueChanged<DateTime?> onDateTo;

  /// Nhãn cột người: "Người ký", "Người gửi gần nhất", "Người xử lý"…
  final String personLabel;

  /// Danh sách tên người xuất hiện trong dữ liệu hiện tại (để chọn nhanh).
  final List<String> personOptions;

  /// '' = tất cả, hoặc một tên cụ thể.
  final String personValue;
  final ValueChanged<String> onPerson;

  const ListFilterExtras({
    super.key,
    required this.dateFrom,
    required this.dateTo,
    required this.onDateFrom,
    required this.onDateTo,
    required this.personLabel,
    required this.personOptions,
    required this.personValue,
    required this.onPerson,
  });

  String _fmt(DateTime d) =>
      '${d.day.toString().padLeft(2, '0')}/${d.month.toString().padLeft(2, '0')}/${d.year}';

  Future<void> _pick(
    BuildContext context,
    DateTime? current,
    ValueChanged<DateTime?> onPicked,
  ) async {
    final picked = await showDatePicker(
      context: context,
      initialDate: current ?? DateTime.now(),
      firstDate: DateTime(2020),
      lastDate: DateTime(2100),
    );
    if (picked != null) onPicked(picked);
  }

  Widget _dateField(
    BuildContext context,
    String label,
    DateTime? value,
    ValueChanged<DateTime?> onPicked,
  ) {
    return OutlinedButton.icon(
      onPressed: () => _pick(context, value, onPicked),
      icon: const Icon(Icons.event_outlined, size: 16),
      label: Text(value == null ? label : '$label: ${_fmt(value)}'),
      style: OutlinedButton.styleFrom(
        visualDensity: VisualDensity.compact,
        foregroundColor: value == null ? Colors.blueGrey : Colors.teal.shade800,
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final hasDate = dateFrom != null || dateTo != null;
    return Wrap(
      spacing: 8,
      runSpacing: 8,
      crossAxisAlignment: WrapCrossAlignment.center,
      children: [
        _dateField(context, 'Từ ngày', dateFrom, onDateFrom),
        _dateField(context, 'Đến ngày', dateTo, onDateTo),
        if (hasDate)
          IconButton(
            tooltip: 'Xóa lọc ngày',
            visualDensity: VisualDensity.compact,
            icon: const Icon(Icons.clear, size: 16),
            onPressed: () {
              onDateFrom(null);
              onDateTo(null);
            },
          ),
        if (personOptions.isNotEmpty)
          SizedBox(
            width: 240,
            child: DropdownButtonFormField<String>(
              value: personValue.isEmpty ? '' : personValue,
              isDense: true,
              isExpanded: true,
              decoration: InputDecoration(
                labelText: personLabel,
                border: const OutlineInputBorder(),
                isDense: true,
                contentPadding:
                    const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
              ),
              items: [
                const DropdownMenuItem(value: '', child: Text('Tất cả')),
                ...personOptions.map(
                  (name) => DropdownMenuItem(
                    value: name,
                    child: Text(name, overflow: TextOverflow.ellipsis),
                  ),
                ),
              ],
              onChanged: (v) => onPerson(v ?? ''),
            ),
          ),
      ],
    );
  }
}

/// Tiện ích: kiểm tra một mốc ISO có nằm trong [from, to] (theo ngày, bao gồm 2 đầu).
bool dateInRange(String iso, DateTime? from, DateTime? to) {
  if (from == null && to == null) return true;
  if (iso.isEmpty) return false;
  final dt = DateTime.tryParse(iso);
  if (dt == null) return false;
  final d = DateTime(dt.year, dt.month, dt.day);
  if (from != null) {
    final f = DateTime(from.year, from.month, from.day);
    if (d.isBefore(f)) return false;
  }
  if (to != null) {
    final t = DateTime(to.year, to.month, to.day);
    if (d.isAfter(t)) return false;
  }
  return true;
}
