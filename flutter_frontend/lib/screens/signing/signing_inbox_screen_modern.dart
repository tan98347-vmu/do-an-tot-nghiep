// === MÀN HÌNH HỘP THƯ KÝ (nhiệm vụ ký của tôi) ===
// Liệt kê SigningTask cần ký ('signing/tasks/', signingSummaryProvider), lọc/tìm theo trạng thái (_matches/_count), mở chi tiết nhiệm vụ (/signing/tasks/<id>); link trang quyền (/signing/access).

// Tệp này dùng để: dựng giao diện và orchestration UI trong flutter_frontend/lib/screens/signing/signing_inbox_screen_modern.dart.
import 'dart:async';

import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/api_client.dart';
import '../../l10n/app_strings.dart';
import '../../models/signing.dart';
import '../../providers/signing_summary_provider.dart';
import '../../widgets/common/collapsible_filter_panel.dart';
import '../../widgets/common/list_filter_extras.dart';

// Widget màn HỘP THƯ KÝ (nhiệm vụ ký của tôi) — ConsumerStatefulWidget.

class SigningInboxScreen extends ConsumerStatefulWidget {
  // Widget màn HỘP THƯ KÝ (nhiệm vụ ký của tôi).
  const SigningInboxScreen({super.key});

  @override
  ConsumerState<SigningInboxScreen> createState() => _SigningInboxScreenState();
}

// State màn hộp thư ký: tải nhiệm vụ, lọc/tìm, nhóm theo trạng thái.

class _SigningInboxScreenState extends ConsumerState<SigningInboxScreen> {
  static const _refreshInterval = Duration(seconds: 8);

  AppStrings get _strings => AppStrings.of(context);
  // Chọn chuỗi hiển thị VI/EN (i18n).
  String _pick(String vi, String en) => _strings.pick(vi, en);

  final _searchController = TextEditingController();
  Timer? _refreshTimer;
  Timer? _debounce;
  bool _loading = true;
  String? _error;
  List<SigningTaskItem> _tasks = const [];
  String _query = '';
  String _statusFilter = 'all';
  DateTime? _dateFrom;
  DateTime? _dateTo;
  String _personFilter = ''; // lọc theo người ký/xử lý

  List<String> get _signerOptions {
    final set = _tasks
        .map((t) => t.signerName.trim())
        .where((e) => e.isNotEmpty)
        .toSet()
        .toList()
      ..sort();
    return set;
  }

  @override
  // Mở màn: nạp danh sách nhiệm vụ ký (_load 'signing/tasks/').
  void initState() {
    super.initState();
    _load();
    _refreshTimer = Timer.periodic(_refreshInterval, (_) {
      if (mounted) {
        _load(silent: true);
      }
    });
  }

  @override
  // Rời màn: dọn controller tìm kiếm.
  void dispose() {
    _refreshTimer?.cancel();
    _debounce?.cancel();
    _searchController.dispose();
    super.dispose();
  }

  // Tải danh sách nhiệm vụ ký từ server ('signing/tasks/'); silent=true để làm mới ngầm.

  Future<void> _load({bool silent = false}) async {
    if (!silent) {
      // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

      setState(() {
        _loading = true;
        _error = null;
      });
    }
    try {
      // Gọi API hoặc tác vụ bất đồng bộ rồi chờ kết quả trước khi cập nhật giao diện.

      final response = await ApiClient().dio.get('signing/tasks/');
      final tasks = (response.data as List)
          .map((item) =>
              SigningTaskItem.fromJson(Map<String, dynamic>.from(item as Map)))
          .toList();
      if (!mounted) return;
      // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

      setState(() {
        _tasks = tasks;
        _error = null;
        _loading = false;
      });
    } on DioException catch (error) {
      if (!mounted) return;
      // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

      setState(() {
        _error = error.response?.data?['detail']?.toString() ??
            error.message ??
            _pick('Không tải được yêu cầu ký.',
                'Could not load signing requests.');
        if (!silent) _loading = false;
      });
    } catch (error) {
      if (!mounted) return;
      // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

      setState(() {
        _error = '$error';
        if (!silent) _loading = false;
      });
    } finally {
      ref.invalidate(signingSummaryProvider);
    }
  }

  // Lọc nhiệm vụ theo từ khóa tìm kiếm.
  void _onSearchChanged(String value) {
    _debounce?.cancel();
    _debounce = Timer(const Duration(milliseconds: 250), () {
      if (!mounted) return;
      // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

      setState(() => _query = value.trim().toLowerCase());
    });
  }

  // Một nhiệm vụ có khớp bộ lọc/tìm kiếm hiện tại không.
  bool _matches(SigningTaskItem task) {
    if (_query.isEmpty) return true;
    final haystack = <String>[
      task.documentTitle,
      task.signerName,
      task.displayRole,
      task.groupContext,
      task.signatureMode,
      _pick('Bước ${task.stepNo}', 'Step ${task.stepNo}'),
    ].join(' ').toLowerCase();
    return haystack.contains(_query);
  }

  // Lọc nhiệm vụ theo trạng thái cho từng nhóm (cần ký / đã ký / ...).
  List<SigningTaskItem> _sectionTasks(String status) {
    return _tasks.where((task) {
      if (!_matches(task)) return false;
      if (_statusFilter != 'all' && _statusFilter != status) return false;
      if (!dateInRange(task.createdAt, _dateFrom, _dateTo)) return false;
      if (_personFilter.isNotEmpty && task.signerName.trim() != _personFilter) {
        return false;
      }
      return task.status == status;
    }).toList();
  }

  // Đếm số nhiệm vụ theo trạng thái (cho chip thống kê).
  int _count(String status) =>
      _tasks.where((task) => task.status == status).length;

  // Màu badge theo trạng thái nhiệm vụ.
  Color _statusColor(String status) {
    switch (status) {
      case 'available':
        return const Color(0xFF0F766E);
      case 'blocked':
        return const Color(0xFFB45309);
      case 'signed':
        return const Color(0xFF166534);
      case 'rejected':
        return const Color(0xFFB91C1C);
      default:
        return const Color(0xFF475569);
    }
  }

  // Định dạng ngày để hiển thị.
  String _formatDate(String value) {
    if (value.isEmpty) return _pick('Chưa có thời gian', 'No timestamp');
    try {
      final dt = DateTime.parse(value).toLocal();
      final day = dt.day.toString().padLeft(2, '0');
      final month = dt.month.toString().padLeft(2, '0');
      final hour = dt.hour.toString().padLeft(2, '0');
      final minute = dt.minute.toString().padLeft(2, '0');
      return '$day/$month/${dt.year} • $hour:$minute';
    } catch (_) {
      return value;
    }
  }

  @override
  // Dựng màn: chip thống kê + danh sách nhiệm vụ ký theo nhóm; mở chi tiết (/signing/tasks/<id>).
  Widget build(BuildContext context) {
    // Lắng nghe provider để widget tự động dựng lại khi dữ liệu hoặc trạng thái thay đổi.

    final summary = ref.watch(signingSummaryProvider).asData?.value ??
        const SigningSummary.zero();
    final available = _sectionTasks('available');
    final blocked = _sectionTasks('blocked');
    final signed = _sectionTasks('signed');
    final rejected = _sectionTasks('rejected');
    final visibleCount =
        available.length + blocked.length + signed.length + rejected.length;
    final showAllSections = _query.isEmpty && _statusFilter == 'all';

    // Dựng 1 nhóm nhiệm vụ ký (tiêu đề + danh sách theo trạng thái).

    Widget section(String title, String status, List<SigningTaskItem> tasks,
        String emptyText) {
      if (tasks.isEmpty && !showAllSections) return const SizedBox.shrink();
      final color = _statusColor(status);
      return Container(
        margin: const EdgeInsets.only(top: 16),
        padding: const EdgeInsets.all(18),
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(22),
          border: Border.all(color: const Color(0xFFE2E8F0)),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Container(
                    width: 10,
                    height: 10,
                    decoration:
                        BoxDecoration(color: color, shape: BoxShape.circle)),
                const SizedBox(width: 10),
                Expanded(
                    child: Text(title,
                        style: const TextStyle(
                            fontSize: 18, fontWeight: FontWeight.w800))),
                Text('${tasks.length}',
                    style:
                        TextStyle(color: color, fontWeight: FontWeight.w800)),
              ],
            ),
            const SizedBox(height: 12),
            if (tasks.isEmpty)
              Text(emptyText,
                  style: const TextStyle(color: Color(0xFF64748B), height: 1.5))
            else
              ...tasks.map((task) => _TaskCard(
                  task: task,
                  color: _statusColor(task.status),
                  dateText: _formatDate(task.createdAt))),
          ],
        ),
      );
    }

    // Dựng khung màn hình chính để chứa app bar, body, action và các vùng giao diện khác.

    return Scaffold(
      appBar: AppBar(
        title: Text(_pick('Yeu cau ky', 'Signing requests')),
        actions: [
          IconButton(
              icon: const Icon(Icons.refresh),
              tooltip: _pick('Tai lai', 'Reload'),
              onPressed: _load),
          if (summary.canManageHrDelegations ||
              summary.canManageAccountingDelegations)
            IconButton(
              icon: const Icon(Icons.admin_panel_settings_outlined),
              tooltip: _pick('Uy quyen ky so', 'Signing delegation'),
              // Điều hướng người dùng sang màn phù hợp theo kết quả thao tác hiện tại.

              onPressed: () => context.go('/signing/access'),
            ),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: _load,
        child: _loading
            ? const Center(child: CircularProgressIndicator())
            : ListView(
                padding: const EdgeInsets.fromLTRB(16, 16, 16, 28),
                children: [
                  Container(
                    padding: const EdgeInsets.all(20),
                    decoration: BoxDecoration(
                      gradient: const LinearGradient(
                          colors: [Color(0xFF0F172A), Color(0xFF1D4ED8)]),
                      borderRadius: BorderRadius.circular(24),
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(_pick('Ky so', 'Digital signing'),
                            style: const TextStyle(
                                color: Color(0xFFBFDBFE),
                                fontWeight: FontWeight.w700)),
                        const SizedBox(height: 8),
                        Text(_pick('Bang yeu cau ky', 'Signing request board'),
                            style: const TextStyle(
                                color: Colors.white,
                                fontSize: 24,
                                fontWeight: FontWeight.w800)),
                        const SizedBox(height: 8),
                        Text(
                          _pick(
                            'Tim nhanh cac yeu cau can ky, dang cho buoc truoc, da ky hoac da tu choi trong mot noi.',
                            'Quickly find requests that need signing, are blocked, were signed, or were rejected in one place.',
                          ),
                          style: const TextStyle(
                              color: Color(0xFFE2E8F0), height: 1.5),
                        ),
                        const SizedBox(height: 16),
                        Wrap(
                          spacing: 10,
                          runSpacing: 10,
                          children: [
                            _MetricChip(
                                label: _pick('Cần ký', 'Needs signature'),
                                value: '${summary.tasksAvailable}'),
                            _MetricChip(
                                label: _pick('Chờ bước trước', 'Blocked'),
                                value: '${summary.tasksBlocked}'),
                            _MetricChip(
                                label: _pick('Đã ký', 'Signed'),
                                value: '${summary.tasksSigned}'),
                            _MetricChip(
                                label: _pick('Tong muc', 'Total items'),
                                value: '${_tasks.length}'),
                          ],
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: 16),
                  CollapsibleFilterPanel(
                    title: _pick('Bộ lọc / Tìm kiếm', 'Filter / Search'),
                    icon: Icons.filter_alt_outlined,
                    badgeCount: (_query.isNotEmpty ? 1 : 0) +
                        (_statusFilter != 'all' ? 1 : 0) +
                        ((_dateFrom != null || _dateTo != null) ? 1 : 0) +
                        (_personFilter.isNotEmpty ? 1 : 0),
                    padding: const EdgeInsets.fromLTRB(18, 0, 18, 18),
                    headerPadding:
                        const EdgeInsets.symmetric(horizontal: 18, vertical: 14),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        TextField(
                          controller: _searchController,
                          onChanged: _onSearchChanged,
                          decoration: InputDecoration(
                            hintText: _pick(
                              'Tìm theo văn bản, vai trò ký, bước ký hoặc chế độ ký...',
                              'Search by document, role, step, or signature mode...',
                            ),
                            prefixIcon: const Icon(Icons.search),
                            suffixIcon: _query.isEmpty
                                ? null
                                : IconButton(
                                    icon: const Icon(Icons.close),
                                    tooltip:
                                        _pick('Xóa từ khóa', 'Clear keyword'),
                                    onPressed: () {
                                      _searchController.clear();
                                      // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

                                      setState(() => _query = '');
                                    },
                                  ),
                            filled: true,
                            fillColor: const Color(0xFFF8FAFC),
                            border: OutlineInputBorder(
                              borderRadius: BorderRadius.circular(16),
                              borderSide: BorderSide.none,
                            ),
                          ),
                        ),
                        const SizedBox(height: 14),
                        Wrap(
                          spacing: 8,
                          runSpacing: 8,
                          children: [
                            // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

                            _FilterChip(
                                label: _pick('Tất cả', 'All'),
                                count: visibleCount,
                                active: _statusFilter == 'all',
                                onTap: () =>
                                    setState(() => _statusFilter = 'all')),
                            // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

                            _FilterChip(
                                label: _pick('Cần ký', 'Needs signature'),
                                count: _count('available'),
                                active: _statusFilter == 'available',
                                onTap: () => setState(
                                    () => _statusFilter = 'available')),
                            // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

                            _FilterChip(
                                label: _pick('Chờ bước trước', 'Blocked'),
                                count: _count('blocked'),
                                active: _statusFilter == 'blocked',
                                onTap: () =>
                                    setState(() => _statusFilter = 'blocked')),
                            // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

                            _FilterChip(
                                label: _pick('Đã ký', 'Signed'),
                                count: _count('signed'),
                                active: _statusFilter == 'signed',
                                onTap: () =>
                                    setState(() => _statusFilter = 'signed')),
                            // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

                            _FilterChip(
                                label: _pick('Đã từ chối', 'Rejected'),
                                count: _count('rejected'),
                                active: _statusFilter == 'rejected',
                                onTap: () =>
                                    setState(() => _statusFilter = 'rejected')),
                          ],
                        ),
                        const SizedBox(height: 14),
                        ListFilterExtras(
                          dateFrom: _dateFrom,
                          dateTo: _dateTo,
                          onDateFrom: (d) => setState(() => _dateFrom = d),
                          onDateTo: (d) => setState(() => _dateTo = d),
                          personLabel: _pick('Người ký / xử lý', 'Signer'),
                          personOptions: _signerOptions,
                          personValue: _personFilter,
                          onPerson: (v) => setState(() => _personFilter = v),
                        ),
                      ],
                    ),
                  ),
                  if (_error != null)
                    Container(
                      margin: const EdgeInsets.only(top: 16),
                      padding: const EdgeInsets.all(18),
                      decoration: BoxDecoration(
                          color: const Color(0xFFFEF2F2),
                          borderRadius: BorderRadius.circular(18)),
                      child: Text(_error!,
                          style: const TextStyle(color: Color(0xFF991B1B))),
                    )
                  else if (visibleCount == 0)
                    Container(
                      margin: const EdgeInsets.only(top: 16),
                      padding: const EdgeInsets.all(18),
                      decoration: BoxDecoration(
                          color: Colors.white,
                          borderRadius: BorderRadius.circular(22),
                          border: Border.all(color: const Color(0xFFE2E8F0))),
                      child: Text(
                        _query.isEmpty
                            ? _pick(
                                'Khong co yeu cau nao khop bo loc hien tai.',
                                'No requests matched the current filters.',
                              )
                            : _pick(
                                'Khong tim thay ket qua cho "$_query".',
                                'No results matched "$_query".',
                              ),
                        style: const TextStyle(
                            color: Color(0xFF64748B), height: 1.5),
                      ),
                    )
                  else ...[
                    section(
                      _pick('Can ky ngay', 'Ready to sign'),
                      'available',
                      available,
                      _pick('Chua co yeu cau nao san sang de ky.',
                          'No requests are ready for signing.'),
                    ),
                    section(
                      _pick('Dang cho mo buoc', 'Blocked requests'),
                      'blocked',
                      blocked,
                      _pick('Khong co yeu cau nao dang cho buoc truoc.',
                          'No requests are waiting on a previous step.'),
                    ),
                    section(
                      _pick('Đã ký', 'Signed'),
                      'signed',
                      signed,
                      _pick('Ban chua hoan tat yeu cau ky nao.',
                          'You have not completed any signing requests yet.'),
                    ),
                    section(
                      _pick('Da tu choi', 'Rejected'),
                      'rejected',
                      rejected,
                      _pick('Khong co yeu cau nao da bi tu choi.',
                          'No requests were rejected.'),
                    ),
                  ],
                ],
              ),
      ),
    );
  }
}

// Widget chip thống kê số liệu (nhãn + số).

class _MetricChip extends StatelessWidget {
  final String label;
  final String value;

  const _MetricChip({required this.label, required this.value});

  @override
  // Dựng chip thống kê.

  Widget build(BuildContext context) {
    return Container(
      width: 150,
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
      decoration: BoxDecoration(
        color: Colors.white.withOpacity(0.12),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: Colors.white.withOpacity(0.14)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(value,
              style: const TextStyle(
                  color: Colors.white,
                  fontSize: 20,
                  fontWeight: FontWeight.w800)),
          const SizedBox(height: 4),
          Text(label, style: const TextStyle(color: Color(0xFFDBEAFE))),
        ],
      ),
    );
  }
}

// Widget chip lọc theo trạng thái.

class _FilterChip extends StatelessWidget {
  final String label;
  final int count;
  final bool active;
  final VoidCallback onTap;

  const _FilterChip(
      {required this.label,
      required this.count,
      required this.active,
      required this.onTap});

  @override
  // Dựng chip lọc.

  Widget build(BuildContext context) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(999),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
        decoration: BoxDecoration(
          color: active ? const Color(0xFFDBEAFE) : const Color(0xFFF8FAFC),
          borderRadius: BorderRadius.circular(999),
          border: Border.all(
              color:
                  active ? const Color(0xFF60A5FA) : const Color(0xFFE2E8F0)),
        ),
        child: Text('$label ($count)',
            style: TextStyle(
                color:
                    active ? const Color(0xFF1D4ED8) : const Color(0xFF334155),
                fontWeight: FontWeight.w700)),
      ),
    );
  }
}

// Thẻ 1 nhiệm vụ ký (tiêu đề tài liệu, hạn, trạng thái).

class _TaskCard extends StatelessWidget {
  final SigningTaskItem task;
  final Color color;
  final String dateText;

  // Thẻ 1 nhiệm vụ ký: tiêu đề tài liệu, hạn, trạng thái; bấm để mở chi tiết.
  const _TaskCard(
      {required this.task, required this.color, required this.dateText});

  @override
  // Dựng thẻ nhiệm vụ ký; bấm mở chi tiết.

  Widget build(BuildContext context) {
    final strings = AppStrings.of(context);
    String pick(String vi, String en) => strings.pick(vi, en);
    return Container(
      margin: const EdgeInsets.only(top: 12),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: const Color(0xFFF8FAFC),
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: const Color(0xFFE2E8F0)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              Container(
                padding:
                    const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                decoration: BoxDecoration(
                    color: color.withOpacity(0.12),
                    borderRadius: BorderRadius.circular(999)),
                child: Text(
                    task.status == 'available'
                        ? pick('Co the xu ly', 'Actionable')
                        : task.status == 'blocked'
                            ? pick('Dang cho', 'Waiting')
                            : task.status == 'signed'
                                ? pick('Da hoan tat', 'Completed')
                                : pick('Da tu choi', 'Rejected'),
                    style:
                        TextStyle(color: color, fontWeight: FontWeight.w700)),
              ),
              Container(
                padding:
                    const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                decoration: BoxDecoration(
                    color: Colors.white,
                    borderRadius: BorderRadius.circular(999),
                    border: Border.all(color: const Color(0xFFE2E8F0))),
                child: Text(task.signatureMode == 'pdf_pkcs7'
                    ? 'PDF PKCS#7'
                    : pick('Xac nhan noi bo', 'Internal approval')),
              ),
            ],
          ),
          const SizedBox(height: 12),
          Text(task.documentTitle,
              style:
                  const TextStyle(fontSize: 17, fontWeight: FontWeight.w800)),
          const SizedBox(height: 8),
          Text(
            '${pick('Buoc', 'Step')} ${task.stepNo} • ${task.displayRole.isEmpty ? pick('Nguoi ky', 'Signer') : task.displayRole}'
            '${task.groupContext.isEmpty ? '' : ' • ${task.groupContext}'}',
            style: const TextStyle(color: Color(0xFF334155), height: 1.5),
          ),
          const SizedBox(height: 4),
          Text(
              '${pick('Nguoi xu ly', 'Signer')}: ${task.signerName.isEmpty ? pick('Ban', 'You') : task.signerName} • $dateText',
              style: const TextStyle(color: Color(0xFF64748B))),
          if (task.rejectionReason.trim().isNotEmpty) ...[
            const SizedBox(height: 10),
            Text(
                '${pick('Ly do tu choi', 'Rejection reason')}: ${task.rejectionReason}',
                style: const TextStyle(
                    color: Color(0xFF9F1239), fontWeight: FontWeight.w600)),
          ],
          const SizedBox(height: 14),
          Align(
            alignment: Alignment.centerRight,
            child: task.status == 'available'
                ? FilledButton.icon(
                    // Điều hướng người dùng sang màn phù hợp theo kết quả thao tác hiện tại.

                    onPressed: () => context.go('/signing/tasks/${task.id}'),
                    icon: const Icon(Icons.arrow_forward_outlined),
                    label: Text(pick('Mo yeu cau', 'Open request')),
                  )
                : OutlinedButton.icon(
                    // Điều hướng người dùng sang màn phù hợp theo kết quả thao tác hiện tại.

                    onPressed: () => context.go('/signing/tasks/${task.id}'),
                    icon: const Icon(Icons.visibility_outlined),
                    label: Text(pick('Xem', 'View')),
                  ),
          ),
        ],
      ),
    );
  }
}
