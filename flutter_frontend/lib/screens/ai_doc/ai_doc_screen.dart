// === MÀN HÌNH CHỌN MẪU ĐỂ SINH VĂN BẢN ===
// Liệt kê mẫu (templatesProvider) có tìm kiếm/lọc (theo danh mục, khoảng ngày — _matchDate, _resetFilters).
// Chọn 1 mẫu -> mở /ai-doc/<id> (hoặc kèm ?prefill=1 qua _showPrefillDialog để điền sẵn từ hồ sơ).

// Tệp này dùng để: dựng giao diện và orchestration UI trong flutter_frontend/lib/screens/ai_doc/ai_doc_screen.dart.
import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../l10n/app_strings.dart';
import '../../models/template.dart';
import '../../providers/templates_provider.dart';

// Widget màn SINH VĂN BẢN TỪ MẪU (chọn mẫu để điền) — ConsumerStatefulWidget.

class AiDocScreen extends ConsumerStatefulWidget {
  final int? preselectedTemplateId;

  const AiDocScreen({super.key, this.preselectedTemplateId});

  @override
  ConsumerState<AiDocScreen> createState() => _AiDocScreenState();
}

// State màn chọn mẫu: tìm kiếm, lọc, chọn mẫu để mở luồng điền.

class _AiDocScreenState extends ConsumerState<AiDocScreen> {
  final _searchCtrl = TextEditingController();
  Timer? _debounce;
  String _search = '';
  String _visFilter = '';
  String _statusFilter = '';
  DateTime? _dateFrom;
  DateTime? _dateTo;
  DateTime? _effectiveFrom;
  DateTime? _effectiveTo;
  DateTime? _endDateFrom;
  DateTime? _endDateTo;
  bool _showFilters = false;

  @override
  // Rời màn: dọn controller tìm kiếm.

  void dispose() {
    _searchCtrl.dispose();
    _debounce?.cancel();
    super.dispose();
  }

  // Lọc danh sách mẫu theo từ khóa (debounce).

  void _onSearchChanged(String v) {
    _debounce?.cancel();
    _debounce = Timer(const Duration(milliseconds: 300), () {
      // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

      setState(() => _search = v.toLowerCase().trim());
    });
  }

  // Xóa toàn bộ bộ lọc.

  void _resetFilters() {
    // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

    setState(() {
      _searchCtrl.clear();
      _search = '';
      _visFilter = '';
      _statusFilter = '';
      _dateFrom = null;
      _dateTo = null;
      _effectiveFrom = null;
      _effectiveTo = null;
      _endDateFrom = null;
      _endDateTo = null;
    });
  }

  // Đang có bộ lọc nào bật không.

  bool _hasActiveFilter() =>
      _search.isNotEmpty ||
      _visFilter.isNotEmpty ||
      _statusFilter.isNotEmpty ||
      _dateFrom != null ||
      _dateTo != null ||
      _effectiveFrom != null ||
      _effectiveTo != null ||
      _endDateFrom != null ||
      _endDateTo != null;

  // Kiểm 1 ngày có nằm trong khoảng lọc không.

  bool _matchDate(String? dateStr, DateTime? from, DateTime? to) {
    if (from == null && to == null) return true;
    if (dateStr == null || dateStr.isEmpty) return false;
    try {
      final d = DateTime.parse(dateStr.substring(0, 10));
      if (from != null && d.isBefore(from)) return false;
      if (to != null && d.isAfter(to)) return false;
      return true;
    } catch (_) {
      return true;
    }
  }

  List<DocumentTemplate> _filter(List<DocumentTemplate> all) {
    return all.where((t) {
      if (_search.isNotEmpty) {
        final q = _search;
        if (!t.title.toLowerCase().contains(q) &&
            !t.description.toLowerCase().contains(q) &&
            !(t.categoryName?.toLowerCase().contains(q) ?? false)) {
          return false;
        }
      }
      if (_visFilter.isNotEmpty && t.visibility != _visFilter) return false;
      if (_statusFilter.isNotEmpty && t.status != _statusFilter) return false;
      if (!_matchDate(t.createdAt, _dateFrom, _dateTo)) return false;
      if (!_matchDate(t.effectiveDate, _effectiveFrom, _effectiveTo))
        return false;
      if (!_matchDate(t.endDate, _endDateFrom, _endDateTo)) return false;
      return true;
    }).toList();
  }

  @override
  // Dựng màn: tìm/lọc + lưới mẫu (mỗi mẫu là _TmplPickCard); chọn mẫu -> mở /ai-doc/<id>.

  Widget build(BuildContext context) {
    final strings = AppStrings.of(context);
    final isMobile = MediaQuery.sizeOf(context).width < 760;
    // Lắng nghe provider để widget tự động dựng lại khi dữ liệu hoặc trạng thái thay đổi.

    final async = ref.watch(templatesProvider(''));
    final activeCount = _hasActiveFilter() ? 1 : 0;

    return Padding(
      padding:
          EdgeInsets.fromLTRB(isMobile ? 12 : 20, 12, isMobile ? 12 : 20, 16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      strings.pick(
                          'Sinh văn bản từ mẫu', 'Generate from templates'),
                      style:
                          Theme.of(context).textTheme.headlineSmall?.copyWith(
                                fontWeight: FontWeight.bold,
                              ),
                    ),
                    Text(
                      strings.pick(
                        'Chọn mẫu văn bản, điền thông tin, AI sẽ tạo văn bản hoàn chỉnh',
                        'Choose a template, fill the details, and AI will generate the final document',
                      ),
                      style:
                          TextStyle(color: Colors.grey.shade600, fontSize: 13),
                    ),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 16),
          Row(
            children: [
              Expanded(
                child: TextField(
                  controller: _searchCtrl,
                  decoration: InputDecoration(
                    hintText: strings.templateSearchHint(''),
                    prefixIcon: const Icon(Icons.search),
                    suffixIcon: _search.isNotEmpty
                        ? IconButton(
                            icon: const Icon(Icons.clear, size: 18),
                            onPressed: () {
                              _searchCtrl.clear();
                              // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

                              setState(() => _search = '');
                            },
                          )
                        : null,
                    border: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(10)),
                    filled: true,
                    fillColor: Colors.white,
                    isDense: true,
                    contentPadding: const EdgeInsets.symmetric(
                        vertical: 12, horizontal: 14),
                  ),
                  onChanged: _onSearchChanged,
                ),
              ),
              const SizedBox(width: 8),
              Badge(
                isLabelVisible: activeCount > 0,
                label: const Text('!'),
                child: OutlinedButton.icon(
                  // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

                  onPressed: () => setState(() => _showFilters = !_showFilters),
                  icon: Icon(
                      _showFilters ? Icons.filter_list_off : Icons.filter_list,
                      size: 18),
                  label: Text(strings.ui('Bộ lọc')),
                  style: OutlinedButton.styleFrom(
                    padding: const EdgeInsets.symmetric(
                        horizontal: 14, vertical: 12),
                  ),
                ),
              ),
              if (_hasActiveFilter()) ...[
                const SizedBox(width: 6),
                TextButton.icon(
                  onPressed: _resetFilters,
                  icon: const Icon(Icons.refresh, size: 16),
                  label: Text(strings.ui('Xóa bộ lọc')),
                  style: TextButton.styleFrom(foregroundColor: Colors.red),
                ),
              ],
            ],
          ),
          if (_showFilters) ...[
            const SizedBox(height: 10),
            Card(
              margin: EdgeInsets.zero,
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      strings.ui('Bộ lọc nâng cao'),
                      style: Theme.of(context).textTheme.titleSmall?.copyWith(
                            fontWeight: FontWeight.bold,
                          ),
                    ),
                    const SizedBox(height: 12),
                    Wrap(
                      spacing: 12,
                      runSpacing: 12,
                      children: [
                        SizedBox(
                          width: isMobile ? double.infinity : 180,
                          child: DropdownButtonFormField<String>(
                            value: _visFilter.isEmpty ? null : _visFilter,
                            decoration: InputDecoration(
                              labelText: strings.ui('Mức chia sẻ'),
                              isDense: true,
                              border: const OutlineInputBorder(),
                            ),
                            items: [
                              DropdownMenuItem(
                                  value: null,
                                  child: Text(strings.ui('Tất cả'))),
                              DropdownMenuItem(
                                  value: 'public',
                                  child: Text(
                                      strings.pick('Thông thường', 'Shared'))),
                              DropdownMenuItem(
                                  value: 'group',
                                  child: Text(strings.ui('Phòng ban'))),
                              DropdownMenuItem(
                                  value: 'private',
                                  child: Text(strings.ui('Riêng tư'))),
                            ],
                            // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

                            onChanged: (v) =>
                                setState(() => _visFilter = v ?? ''),
                          ),
                        ),
                        SizedBox(
                          width: isMobile ? double.infinity : 180,
                          child: DropdownButtonFormField<String>(
                            value: _statusFilter.isEmpty ? null : _statusFilter,
                            decoration: InputDecoration(
                              labelText: strings.ui('Trạng thái'),
                              isDense: true,
                              border: const OutlineInputBorder(),
                            ),
                            items: [
                              DropdownMenuItem(
                                  value: null,
                                  child: Text(strings.ui('Tất cả'))),
                              DropdownMenuItem(
                                  value: 'approved',
                                  child: Text(strings.ui('Đã duyệt'))),
                              DropdownMenuItem(
                                  value: 'pending',
                                  child: Text(strings.ui('Chờ duyệt'))),
                              DropdownMenuItem(
                                  value: 'draft',
                                  child: Text(strings.ui('Bản nháp'))),
                            ],
                            // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

                            onChanged: (v) =>
                                setState(() => _statusFilter = v ?? ''),
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 12),
                    _DateRangeRow(
                      label: strings.ui('Ngày tạo'),
                      from: _dateFrom,
                      to: _dateTo,
                      // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

                      onFromPick: (d) => setState(() => _dateFrom = d),
                      // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

                      onToPick: (d) => setState(() => _dateTo = d),
                    ),
                    const SizedBox(height: 8),
                    _DateRangeRow(
                      label: strings.pick('Hiệu lực từ', 'Effective from'),
                      from: _effectiveFrom,
                      to: _effectiveTo,
                      // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

                      onFromPick: (d) => setState(() => _effectiveFrom = d),
                      // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

                      onToPick: (d) => setState(() => _effectiveTo = d),
                    ),
                    const SizedBox(height: 8),
                    _DateRangeRow(
                      label: strings.ui('Hết hiệu lực'),
                      from: _endDateFrom,
                      to: _endDateTo,
                      // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

                      onFromPick: (d) => setState(() => _endDateFrom = d),
                      // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

                      onToPick: (d) => setState(() => _endDateTo = d),
                    ),
                  ],
                ),
              ),
            ),
          ],
          if (_showFilters) ...[
            const SizedBox(height: 14),
            SingleChildScrollView(
              scrollDirection: Axis.horizontal,
              child: Row(
                children: [
                  _FilterChip(
                    label: strings.ui('Tất cả'),
                    active: _visFilter.isEmpty && _statusFilter.isEmpty,
                    onTap: () => setState(() {
                      _visFilter = '';
                      _statusFilter = '';
                    }),
                  ),
                  const SizedBox(width: 6),
                  _FilterChip(
                    label: strings.ui('Công khai'),
                    active: _visFilter == 'public',
                    onTap: () => setState(
                      () => _visFilter = _visFilter == 'public' ? '' : 'public',
                    ),
                    color: Colors.green,
                  ),
                  const SizedBox(width: 6),
                  _FilterChip(
                    label: strings.ui('Phòng ban'),
                    active: _visFilter == 'group',
                    onTap: () => setState(
                      () => _visFilter = _visFilter == 'group' ? '' : 'group',
                    ),
                    color: Colors.blue,
                  ),
                  const SizedBox(width: 6),
                  _FilterChip(
                    label: strings.ui('Riêng tư'),
                    active: _visFilter == 'private',
                    onTap: () => setState(
                      () => _visFilter = _visFilter == 'private' ? '' : 'private',
                    ),
                    color: Colors.grey,
                  ),
                  const SizedBox(width: 6),
                  _FilterChip(
                    label: strings.ui('Đã duyệt'),
                    active: _statusFilter == 'approved',
                    onTap: () => setState(
                      () => _statusFilter =
                          _statusFilter == 'approved' ? '' : 'approved',
                    ),
                    color: Colors.teal,
                  ),
                ],
              ),
            ),
            const SizedBox(height: 12),
          ] else
            const SizedBox(height: 14),
          Expanded(
            child: async.when(
              loading: () => const Center(child: CircularProgressIndicator()),
              error: (e, _) => Center(
                  child: Text(strings.pick(
                      'Lỗi tải mẫu: $e', 'Template loading error: $e'))),
              data: (templates) {
                final filtered = _filter(templates);
                if (filtered.isEmpty) {
                  return Center(
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Icon(Icons.search_off,
                            size: 64, color: Colors.grey.shade300),
                        const SizedBox(height: 12),
                        Text(
                            strings.pick('Không tìm thấy mẫu nào.',
                                'No templates found.'),
                            style: TextStyle(color: Colors.grey.shade500)),
                        if (_hasActiveFilter()) ...[
                          const SizedBox(height: 8),
                          TextButton(
                              onPressed: _resetFilters,
                              child: Text(strings.pick(
                                  'Xóa bộ lọc để xem tất cả',
                                  'Clear filters to view everything'))),
                        ],
                      ],
                    ),
                  );
                }
                return Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                        strings.pick('Tìm thấy ${filtered.length} mẫu',
                            'Found ${filtered.length} templates'),
                        style: TextStyle(
                            color: Colors.grey.shade600, fontSize: 13)),
                    const SizedBox(height: 10),
                    Expanded(
                      child: isMobile
                          ? ListView.separated(
                              itemCount: filtered.length,
                              separatorBuilder: (_, __) =>
                                  const SizedBox(height: 10),
                              itemBuilder: (_, i) => _TmplPickCard(
                                template: filtered[i],
                                searchQuery: _search,
                                compact: true,
                              ),
                            )
                          : GridView.builder(
                              gridDelegate:
                                  const SliverGridDelegateWithMaxCrossAxisExtent(
                                maxCrossAxisExtent: 340,
                                childAspectRatio: 1.35,
                                crossAxisSpacing: 12,
                                mainAxisSpacing: 12,
                              ),
                              itemCount: filtered.length,
                              itemBuilder: (_, i) => _TmplPickCard(
                                  template: filtered[i], searchQuery: _search),
                            ),
                    ),
                  ],
                );
              },
            ),
          ),
        ],
      ),
    );
  }
}

// Widget chip lọc.

class _FilterChip extends StatelessWidget {
  final String label;
  final bool active;
  final VoidCallback onTap;
  final Color? color;

  const _FilterChip(
      {required this.label,
      required this.active,
      required this.onTap,
      this.color});

  @override
  // Dựng chip lọc.

  Widget build(BuildContext context) {
    final c = color ?? Theme.of(context).colorScheme.primary;
    return GestureDetector(
      onTap: onTap,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 150),
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
        decoration: BoxDecoration(
          color: active ? c : Colors.grey.shade100,
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: active ? c : Colors.grey.shade300),
        ),
        child: Text(
          label,
          style: TextStyle(
            fontSize: 12.5,
            fontWeight: FontWeight.w600,
            color: active ? Colors.white : Colors.grey.shade700,
          ),
        ),
      ),
    );
  }
}

// Widget chọn khoảng ngày trong bộ lọc.

class _DateRangeRow extends StatelessWidget {
  final String label;
  final DateTime? from;
  final DateTime? to;
  final void Function(DateTime?) onFromPick;
  final void Function(DateTime?) onToPick;

  const _DateRangeRow({
    required this.label,
    required this.from,
    required this.to,
    required this.onFromPick,
    required this.onToPick,
  });

  // Định dạng ngày để hiển thị.

  String _fmt(DateTime? d) =>
      d == null ? 'Chọn ngày' : '${d.day}/${d.month}/${d.year}';

  // Mở lịch chọn 1 mốc ngày.

  Future<void> _pick(BuildContext context, DateTime? current,
      void Function(DateTime?) cb) async {
    final picked = await showDatePicker(
      context: context,
      initialDate: current ?? DateTime.now(),
      firstDate: DateTime(2020),
      lastDate: DateTime(2030),
    );
    cb(picked);
  }

  @override
  // Dựng hàng chọn khoảng ngày.

  Widget build(BuildContext context) {
    final strings = AppStrings.of(context);
    final isMobile = MediaQuery.sizeOf(context).width < 760;
    if (isMobile) {
      return Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(label,
              style:
                  const TextStyle(fontSize: 12.5, fontWeight: FontWeight.w600)),
          const SizedBox(height: 6),
          Row(
            children: [
              Expanded(
                child: OutlinedButton(
                  onPressed: () => _pick(context, from, onFromPick),
                  style: OutlinedButton.styleFrom(
                    padding:
                        const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
                    side: BorderSide(
                        color:
                            from != null ? Colors.blue : Colors.grey.shade300),
                  ),
                  child: Text(
                    strings.pick(_fmt(from),
                        _fmt(from) == 'Chọn ngày' ? 'Pick a date' : _fmt(from)),
                    style: TextStyle(
                        fontSize: 12,
                        color:
                            from != null ? Colors.blue : Colors.grey.shade500),
                  ),
                ),
              ),
              const Padding(
                padding: EdgeInsets.symmetric(horizontal: 6),
                child: Icon(Icons.arrow_forward, size: 14, color: Colors.grey),
              ),
              Expanded(
                child: OutlinedButton(
                  onPressed: () => _pick(context, to, onToPick),
                  style: OutlinedButton.styleFrom(
                    padding:
                        const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
                    side: BorderSide(
                        color: to != null ? Colors.blue : Colors.grey.shade300),
                  ),
                  child: Text(
                    strings.pick(_fmt(to),
                        _fmt(to) == 'Chọn ngày' ? 'Pick a date' : _fmt(to)),
                    style: TextStyle(
                        fontSize: 12,
                        color: to != null ? Colors.blue : Colors.grey.shade500),
                  ),
                ),
              ),
              if (from != null || to != null)
                IconButton(
                  icon: const Icon(Icons.clear, size: 16),
                  onPressed: () {
                    onFromPick(null);
                    onToPick(null);
                  },
                ),
            ],
          ),
        ],
      );
    }
    return Row(
      children: [
        SizedBox(
            width: 90,
            child: Text(label,
                style: const TextStyle(
                    fontSize: 12.5, fontWeight: FontWeight.w500))),
        Expanded(
          child: OutlinedButton(
            onPressed: () => _pick(context, from, onFromPick),
            style: OutlinedButton.styleFrom(
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
              side: BorderSide(
                  color: from != null ? Colors.blue : Colors.grey.shade300),
            ),
            child: Text(
                strings.pick(_fmt(from),
                    _fmt(from) == 'Chọn ngày' ? 'Pick a date' : _fmt(from)),
                style: TextStyle(
                    fontSize: 12,
                    color: from != null ? Colors.blue : Colors.grey.shade500)),
          ),
        ),
        const Padding(
            padding: EdgeInsets.symmetric(horizontal: 6),
            child: Text('→', style: TextStyle(color: Colors.grey))),
        Expanded(
          child: OutlinedButton(
            onPressed: () => _pick(context, to, onToPick),
            style: OutlinedButton.styleFrom(
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
              side: BorderSide(
                  color: to != null ? Colors.blue : Colors.grey.shade300),
            ),
            child: Text(
                strings.pick(_fmt(to),
                    _fmt(to) == 'Chọn ngày' ? 'Pick a date' : _fmt(to)),
                style: TextStyle(
                    fontSize: 12,
                    color: to != null ? Colors.blue : Colors.grey.shade500)),
          ),
        ),
        if (from != null || to != null)
          IconButton(
              icon: const Icon(Icons.clear, size: 16),
              onPressed: () {
                onFromPick(null);
                onToPick(null);
              }),
      ],
    );
  }
}

// Thẻ 1 mẫu để chọn sinh văn bản (tiêu đề + mô tả + số biến).

class _TmplPickCard extends StatelessWidget {
  final DocumentTemplate template;
  final String searchQuery;
  final bool compact;

  const _TmplPickCard({
    required this.template,
    required this.searchQuery,
    this.compact = false,
  });

  @override
  // Dựng thẻ chọn mẫu; bấm mở luồng điền.

  Widget build(BuildContext context) {
    final strings = AppStrings.of(context);
    if (compact) {
      return Card(
        clipBehavior: Clip.antiAlias,
        elevation: 1,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
        child: InkWell(
          onTap: () => _showPrefillDialog(context),
          child: Padding(
            padding: const EdgeInsets.all(12),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Container(
                      padding: const EdgeInsets.all(8),
                      decoration: BoxDecoration(
                        color: Colors.blue.withOpacity(0.1),
                        borderRadius: BorderRadius.circular(10),
                      ),
                      child: const Icon(Icons.file_copy_outlined,
                          size: 18, color: Colors.blue),
                    ),
                    const SizedBox(width: 10),
                    Expanded(
                      child: _HighlightText(
                        text: template.title,
                        query: searchQuery,
                        style: const TextStyle(
                            fontWeight: FontWeight.bold,
                            fontSize: 14,
                            height: 1.25),
                        maxLines: 3,
                      ),
                    ),
                  ],
                ),
                if (template.description.isNotEmpty) ...[
                  const SizedBox(height: 8),
                  _HighlightText(
                    text: template.description,
                    query: searchQuery,
                    style: TextStyle(
                        color: Colors.grey.shade700,
                        fontSize: 12,
                        height: 1.35),
                    maxLines: 3,
                  ),
                ],
                if (template.categoryName != null &&
                    template.categoryName!.isNotEmpty) ...[
                  const SizedBox(height: 8),
                  Text(
                    template.categoryName!,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style:
                        TextStyle(fontSize: 11.5, color: Colors.grey.shade600),
                  ),
                ],
                const SizedBox(height: 10),
                Wrap(
                  spacing: 6,
                  runSpacing: 6,
                  children: [
                    _VisChip(visibility: template.visibility),
                    if (template.variableCount > 0)
                      Container(
                        padding: const EdgeInsets.symmetric(
                            horizontal: 8, vertical: 3),
                        decoration: BoxDecoration(
                          color: Colors.blueGrey.shade50,
                          borderRadius: BorderRadius.circular(999),
                        ),
                        child: Text(
                          strings.pick('${template.variableCount} bien',
                              '${template.variableCount} variables'),
                          style: TextStyle(
                              fontSize: 11, color: Colors.blueGrey.shade700),
                        ),
                      ),
                    if (template.isFavorite)
                      const Icon(Icons.star, color: Colors.amber, size: 16),
                  ],
                ),
                if (template.tags.isNotEmpty) ...[
                  const SizedBox(height: 8),
                  Wrap(
                    spacing: 4,
                    runSpacing: 4,
                    children: template.tags.take(2).map((tag) {
                      return Container(
                        padding: const EdgeInsets.symmetric(
                            horizontal: 6, vertical: 2),
                        decoration: BoxDecoration(
                          color: Colors.indigo.shade50,
                          borderRadius: BorderRadius.circular(999),
                        ),
                        child: Text(
                          '#$tag',
                          style: TextStyle(
                              fontSize: 10, color: Colors.indigo.shade700),
                        ),
                      );
                    }).toList(),
                  ),
                ],
                const SizedBox(height: 12),
                Container(
                  width: double.infinity,
                  padding:
                      const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
                  decoration: BoxDecoration(
                    gradient: const LinearGradient(
                        colors: [Color(0xFF2563EB), Color(0xFF1D4ED8)]),
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: Text(
                    strings.pick('Chon mau va dien thong tin',
                        'Select the template and fill details'),
                    textAlign: TextAlign.center,
                    style: const TextStyle(
                        color: Colors.white,
                        fontSize: 12,
                        fontWeight: FontWeight.w600),
                  ),
                ),
              ],
            ),
          ),
        ),
      );
    }
    return Card(
      clipBehavior: Clip.antiAlias,
      elevation: 1,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
      child: InkWell(
        onTap: () => _showPrefillDialog(context),
        hoverColor: Colors.blue.withOpacity(0.04),
        child: Padding(
          padding: const EdgeInsets.all(14),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Container(
                    padding: const EdgeInsets.all(7),
                    decoration: BoxDecoration(
                      color: Colors.blue.withOpacity(0.1),
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: const Icon(Icons.file_copy_outlined,
                        size: 16, color: Colors.blue),
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: _HighlightText(
                      text: template.title,
                      query: searchQuery,
                      style: const TextStyle(
                          fontWeight: FontWeight.bold, fontSize: 13),
                      maxLines: 2,
                    ),
                  ),
                ],
              ),
              if (template.description.isNotEmpty) ...[
                const SizedBox(height: 6),
                _HighlightText(
                  text: template.description,
                  query: searchQuery,
                  style: TextStyle(color: Colors.grey.shade600, fontSize: 11.5),
                  maxLines: 2,
                ),
              ],
              if (template.categoryName != null) ...[
                const SizedBox(height: 4),
                Row(
                  children: [
                    Icon(Icons.label_outline,
                        size: 11, color: Colors.grey.shade400),
                    const SizedBox(width: 3),
                    Text(template.categoryName!,
                        style: TextStyle(
                            fontSize: 11, color: Colors.grey.shade500)),
                  ],
                ),
              ],
              const Spacer(),
              Row(
                children: [
                  _VisChip(visibility: template.visibility),
                  const SizedBox(width: 4),
                  if (template.variableCount > 0)
                    Flexible(
                      child: Text(
                        '${template.variableCount} biến',
                        overflow: TextOverflow.ellipsis,
                        style: TextStyle(
                            fontSize: 10.5, color: Colors.grey.shade500),
                      ),
                    ),
                  const Spacer(),
                  if (template.isFavorite)
                    const Icon(Icons.star, color: Colors.amber, size: 14),
                  const SizedBox(width: 2),
                  Flexible(
                    child: Container(
                      padding: const EdgeInsets.symmetric(
                          horizontal: 8, vertical: 4),
                      decoration: BoxDecoration(
                        gradient: const LinearGradient(
                            colors: [Color(0xFF2563EB), Color(0xFF1D4ED8)]),
                        borderRadius: BorderRadius.circular(6),
                      ),
                      child: Text(
                        strings.pick('Chon mau', 'Select'),
                        overflow: TextOverflow.ellipsis,
                        style: const TextStyle(
                            color: Colors.white,
                            fontSize: 11,
                            fontWeight: FontWeight.w600),
                      ),
                    ),
                  ),
                ],
              ),
              if (template.tags.isNotEmpty) ...[
                const SizedBox(height: 4),
                Wrap(
                  spacing: 4,
                  runSpacing: 3,
                  children: template.tags.take(3).map((tag) {
                    return Container(
                      padding: const EdgeInsets.symmetric(
                          horizontal: 5, vertical: 1),
                      decoration: BoxDecoration(
                        color: Colors.indigo.shade50,
                        borderRadius: BorderRadius.circular(3),
                        border: Border.all(color: Colors.indigo.shade100),
                      ),
                      child: Text('#$tag',
                          style: TextStyle(
                              fontSize: 9.5, color: Colors.indigo.shade600)),
                    );
                  }).toList(),
                ),
              ],
              if (template.effectiveDate != null ||
                  template.endDate != null) ...[
                const SizedBox(height: 4),
                Row(
                  children: [
                    if (template.effectiveDate != null) ...[
                      Icon(Icons.calendar_today,
                          size: 10, color: Colors.grey.shade400),
                      const SizedBox(width: 3),
                      Text(
                        '${strings.pick('Tu', 'From')}: ${template.effectiveDate!.substring(0, 10)}',
                        style: TextStyle(
                            fontSize: 10, color: Colors.grey.shade500),
                      ),
                      const SizedBox(width: 8),
                    ],
                    if (template.endDate != null) ...[
                      Icon(Icons.event_busy,
                          size: 10, color: Colors.red.shade200),
                      const SizedBox(width: 3),
                      Text(
                        '${strings.pick('Den', 'To')}: ${template.endDate!.substring(0, 10)}',
                        style:
                            TextStyle(fontSize: 10, color: Colors.red.shade300),
                      ),
                    ],
                  ],
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }

  // Mở dialog chọn cách điền tự động (hồ sơ/công ty) trước khi vào màn điền.

  void _showPrefillDialog(BuildContext context) {
    final strings = AppStrings.of(context);
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Row(
          children: [
            const Icon(Icons.auto_awesome, color: Color(0xFF2563EB)),
            const SizedBox(width: 8),
            Expanded(
                child: Text(
                    strings.pick(
                        'Tự động điền từ hồ sơ?', 'Auto-fill from profile?'),
                    style: const TextStyle(fontSize: 16))),
          ],
        ),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('${strings.pick('Mau', 'Template')}: ${template.title}',
                style:
                    const TextStyle(fontWeight: FontWeight.bold, fontSize: 13)),
            const SizedBox(height: 8),
            if (template.variableCount > 0)
              Text(
                strings.pick(
                    'Can dien ${template.variableCount} truong thong tin.',
                    '${template.variableCount} fields need input.'),
                style: TextStyle(color: Colors.grey.shade600, fontSize: 13),
              ),
            const SizedBox(height: 12),
            Container(
              padding: const EdgeInsets.all(10),
              decoration: BoxDecoration(
                color: Colors.blue.shade50,
                borderRadius: BorderRadius.circular(8),
              ),
              child: Text(
                strings.pick(
                  'AI se doc ho so cua ban (ho ten, chuc danh, ma NV, CCCD, ngay sinh...) va tu dong dien vao cac truong phu hop. Chi dien nhung gi co du lieu ro rang.',
                  'AI reads your profile details and auto-fills matching fields. It only fills values with clear source data.',
                ),
                style: TextStyle(fontSize: 12.5),
              ),
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () {
              Navigator.pop(ctx);
              // Điều hướng người dùng sang màn phù hợp theo kết quả thao tác hiện tại.

              context.go('/ai-doc/${template.id}');
            },
            child: Text(
                strings.pick('Khong, tu dien', 'No, I will fill it manually')),
          ),
          FilledButton.icon(
            onPressed: () {
              Navigator.pop(ctx);
              // Điều hướng người dùng sang màn phù hợp theo kết quả thao tác hiện tại.

              context.go('/ai-doc/${template.id}?prefill=1');
            },
            icon: const Icon(Icons.auto_awesome, size: 16),
            label: Text(strings.pick('Co, tu dong dien', 'Yes, auto-fill')),
          ),
        ],
      ),
    );
  }
}

// Widget tô sáng phần text khớp từ khóa.

class _HighlightText extends StatelessWidget {
  final String text;
  final String query;
  final TextStyle style;
  final int maxLines;

  const _HighlightText(
      {required this.text,
      required this.query,
      required this.style,
      this.maxLines = 1});

  @override
  // Dựng text tô sáng.

  Widget build(BuildContext context) {
    if (query.isEmpty) {
      return Text(text,
          style: style, maxLines: maxLines, overflow: TextOverflow.ellipsis);
    }
    final lower = text.toLowerCase();
    final spans = <TextSpan>[];
    var start = 0;
    while (start < text.length) {
      final idx = lower.indexOf(query, start);
      if (idx < 0) {
        spans.add(TextSpan(text: text.substring(start), style: style));
        break;
      }
      if (idx > start)
        spans.add(TextSpan(text: text.substring(start, idx), style: style));
      spans.add(
        TextSpan(
          text: text.substring(idx, idx + query.length),
          style: style.copyWith(
            backgroundColor: Colors.yellow.shade200,
            color: Colors.black87,
            fontWeight: FontWeight.bold,
          ),
        ),
      );
      start = idx + query.length;
    }
    return Text.rich(
      TextSpan(children: spans),
      maxLines: maxLines,
      overflow: TextOverflow.ellipsis,
    );
  }
}

// Widget chip phạm vi hiển thị của mẫu.

class _VisChip extends StatelessWidget {
  final String visibility;

  const _VisChip({required this.visibility});

  @override
  // Dựng chip phạm vi.

  Widget build(BuildContext context) {
    final strings = AppStrings.of(context);
    final (label, color) = switch (visibility) {
      'public' => (strings.ui('Công khai'), Colors.green),
      'group' => (strings.ui('Phòng ban'), Colors.blue),
      _ => (strings.ui('Riêng tư'), Colors.grey),
    };
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
      decoration: BoxDecoration(
        color: color.withOpacity(0.1),
        borderRadius: BorderRadius.circular(4),
        border: Border.all(color: color.withOpacity(0.3)),
      ),
      child: Text(label,
          style: TextStyle(
              fontSize: 10, color: color, fontWeight: FontWeight.w600)),
    );
  }
}
