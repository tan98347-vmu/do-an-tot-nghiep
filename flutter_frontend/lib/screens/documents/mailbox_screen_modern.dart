// Tệp này dùng để: dựng giao diện và orchestration UI trong flutter_frontend/lib/screens/documents/mailbox_screen_modern.dart.
// Cách hoạt động: nhận state từ provider, dựng widget, phản ứng sự kiện và gửi thao tác ngược về backend khi người dùng tương tác.
// Vai trò trong hệ thống: Đây là màn hình Flutter mà người dùng tương tác trực tiếp.
// Tác dụng khi hệ thống vận hành: biến nghiệp vụ backend thành trải nghiệm thao tác cụ thể trên web.

import 'dart:async';

import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/api_client.dart';
import '../../l10n/app_strings.dart';
import '../../models/signing.dart';
import '../../providers/auth_provider.dart';
import '../../widgets/common/collapsible_filter_panel.dart';
import '../../widgets/common/list_filter_extras.dart';

// Mục đích: Widget `MailboxScreen` triển khai phần việc `Mailbox Screen` trong flutter_frontend/lib/screens/documents/mailbox_screen_modern.dart.
// Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
// Vai trò trong hệ thống: Đây là widget thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
// Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

class MailboxScreen extends ConsumerStatefulWidget {
  const MailboxScreen({super.key});

  @override
  ConsumerState<MailboxScreen> createState() => _MailboxScreenState();
}

// Mục đích: Widget `_MailboxScreenState` triển khai phần việc `Mailbox Screen State` trong flutter_frontend/lib/screens/documents/mailbox_screen_modern.dart.
// Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
// Vai trò trong hệ thống: Đây là widget thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
// Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

class _MailboxScreenState extends ConsumerState<MailboxScreen> {
  AppStrings get _strings => AppStrings.of(context);
  String _pick(String vi, String en) => _strings.pick(vi, en);

  final _searchController = TextEditingController();
  Timer? _debounce;
  bool _loading = true;
  String? _error;
  String _query = '';
  String _statusFilter = 'all';
  DateTime? _dateFrom;
  DateTime? _dateTo;
  String _personFilter = ''; // lọc theo người gửi gần nhất
  List<MailboxThreadItem> _threads = const [];

  List<MailboxThreadItem> get _visibleThreads => _threads.where((t) {
        if (!dateInRange(t.updatedAt, _dateFrom, _dateTo)) return false;
        if (_personFilter.isNotEmpty &&
            t.latestSenderName.trim() != _personFilter) {
          return false;
        }
        return true;
      }).toList();

  List<String> get _senderOptions {
    final set = _threads
        .map((t) => t.latestSenderName.trim())
        .where((e) => e.isNotEmpty)
        .toSet()
        .toList()
      ..sort();
    return set;
  }

  @override
  // Mục đích: Phương thức `initState` triển khai phần việc `init State` trong flutter_frontend/lib/screens/documents/mailbox_screen_modern.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  void initState() {
    super.initState();
    _load();
  }

  @override
  // Mục đích: Phương thức `dispose` triển khai phần việc `dispose` trong flutter_frontend/lib/screens/documents/mailbox_screen_modern.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  void dispose() {
    _debounce?.cancel();
    _searchController.dispose();
    super.dispose();
  }

  // Mục đích: Phương thức `_load` triển khai phần việc `load` trong flutter_frontend/lib/screens/documents/mailbox_screen_modern.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  Future<void> _load() async {
    // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final queryParameters = <String, dynamic>{};
      if (_query.trim().isNotEmpty) {
        queryParameters['q'] = _query.trim();
      }
      if (_statusFilter != 'all') {
        queryParameters['status'] = _statusFilter;
      }
      // Gọi API hoặc tác vụ bất đồng bộ rồi chờ kết quả trước khi cập nhật giao diện.

      final resp = await ApiClient()
          .dio
          .get('mailbox/', queryParameters: queryParameters);
      final items = (resp.data as List<dynamic>)
          .map((item) => MailboxThreadItem.fromJson(
              Map<String, dynamic>.from(item as Map)))
          .toList();
      if (!mounted) return;
      // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

      setState(() {
        _threads = items;
        _loading = false;
      });
    } on DioException catch (error) {
      if (!mounted) return;
      // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

      setState(() {
        _error = error.response?.data?['detail']?.toString() ??
            error.message ??
            _pick('Khong tai duoc Hom thu.', 'Could not load mailbox.');
        _loading = false;
      });
    } catch (error) {
      if (!mounted) return;
      // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

      setState(() {
        _error = '$error';
        _loading = false;
      });
    }
  }

  // Mục đích: Phương thức `_scheduleSearch` triển khai phần việc `schedule Search` trong flutter_frontend/lib/screens/documents/mailbox_screen_modern.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  void _scheduleSearch(String value) {
    _debounce?.cancel();
    _debounce = Timer(const Duration(milliseconds: 280), () {
      if (!mounted) return;
      // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

      setState(() => _query = value.trim());
      _load();
    });
  }

  MailboxEntryItem? _entryForCurrentUser(MailboxThreadItem thread) {
    // Đọc provider theo nhu cầu hành động mà không buộc widget đăng ký rebuild liên tục.

    final userId = ref.read(currentUserProvider)?.id;
    if (userId == null) return null;
    final mine = thread.entries
        .where((entry) => entry.forwardedTo == userId)
        .toList()
      ..sort((a, b) => b.createdAt.compareTo(a.createdAt));
    if (mine.isEmpty) return null;
    for (final entry in mine) {
      if (entry.status == 'view') return entry;
    }
    return mine.first;
  }

  // Mục đích: Phương thức `_statusLabel` triển khai phần việc `status Label` trong flutter_frontend/lib/screens/documents/mailbox_screen_modern.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  String _statusLabel(String status) {
    switch (status) {
      case 'forward':
        return _pick('Đang forward', 'Forwarding');
      case 'completed':
        return _pick('Kết thúc', 'Completed');
      case 'rejected':
        return _pick('Tu choi', 'Rejected');
      case 'view':
        return _pick('Da xem', 'Viewed');
      default:
        return _pick('Khong ro', 'Unknown');
    }
  }

  Color _statusColor(String status) {
    switch (status) {
      case 'forward':
        return const Color(0xFF0F766E);
      case 'completed':
        return const Color(0xFF166534);
      case 'rejected':
        return const Color(0xFF991B1B);
      case 'view':
        return const Color(0xFF1D4ED8);
      default:
        return const Color(0xFF475569);
    }
  }

  // Mục đích: Phương thức `_formatDate` triển khai phần việc `format Date` trong flutter_frontend/lib/screens/documents/mailbox_screen_modern.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  String _formatDate(String value) {
    if (value.trim().isEmpty) return _pick('Chua co thoi gian', 'No timestamp');
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

  // Mục đích: Phương thức `_verifyEntry` triển khai phần việc `verify Entry` trong flutter_frontend/lib/screens/documents/mailbox_screen_modern.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  Future<void> _verifyEntry(MailboxEntryItem entry) async {
    try {
      // Gọi API hoặc tác vụ bất đồng bộ rồi chờ kết quả trước khi cập nhật giao diện.

      final resp =
          await ApiClient().dio.get('mailbox/entries/${entry.id}/verify/');
      final data = Map<String, dynamic>.from(resp.data as Map);
      if (!mounted) return;
      await showDialog<void>(
        context: context,
        builder: (ctx) => AlertDialog(
          title: Text(_pick('Kiem tra tinh toan ven', 'Integrity check')),
          content: SizedBox(
            width: 520,
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  data['is_safe'] == true
                      ? _pick('PDF mailbox an toan', 'Mailbox PDF is safe')
                      : _pick('PDF mailbox co dau hieu bi thay doi',
                          'Mailbox PDF appears modified'),
                  style: TextStyle(
                    fontWeight: FontWeight.w700,
                    color: data['is_safe'] == true
                        ? const Color(0xFF166534)
                        : const Color(0xFF991B1B),
                  ),
                ),
                const SizedBox(height: 10),
                Text('${data['summary'] ?? ''}'),
              ],
            ),
          ),
          actions: [
            FilledButton(
                onPressed: () => Navigator.pop(ctx),
                child: Text(_pick('Dong', 'Close'))),
          ],
        ),
      );
    } on DioException catch (error) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            error.response?.data?['detail']?.toString() ??
                _pick('Khong kiem tra duoc file mailbox.',
                    'Could not verify the mailbox file.'),
          ),
        ),
      );
    }
  }

  @override
  // Mục đích: Phương thức `build` triển khai phần việc `build` trong flutter_frontend/lib/screens/documents/mailbox_screen_modern.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  Widget build(BuildContext context) {
    final forwardCount =
        _threads.where((item) => item.status == 'forward').length;
    final completedCount =
        _threads.where((item) => item.status == 'completed').length;
    final rejectedCount =
        _threads.where((item) => item.status == 'rejected').length;

    // Mục đích: Phương thức `filterChip` triển khai phần việc `filter Chip` trong flutter_frontend/lib/screens/documents/mailbox_screen_modern.dart.
    // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
    // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
    // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

    Widget filterChip(String label, String value, int count) {
      final active = _statusFilter == value;
      return InkWell(
        onTap: () {
          // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

          setState(() => _statusFilter = value);
          _load();
        },
        borderRadius: BorderRadius.circular(999),
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
          decoration: BoxDecoration(
            color: active ? const Color(0xFFDBEAFE) : const Color(0xFFF8FAFC),
            borderRadius: BorderRadius.circular(999),
            border: Border.all(
              color: active ? const Color(0xFF60A5FA) : const Color(0xFFE2E8F0),
            ),
          ),
          child: Text(
            '$label ($count)',
            style: TextStyle(
              color: active ? const Color(0xFF1D4ED8) : const Color(0xFF334155),
              fontWeight: FontWeight.w700,
            ),
          ),
        ),
      );
    }

    // Dựng khung màn hình chính để chứa app bar, body, action và các vùng giao diện khác.

    return Scaffold(
      appBar: AppBar(
        title: Text(_pick('Hom thu', 'Mailbox')),
        actions: [
          IconButton(
            onPressed: _load,
            tooltip: _pick('Tai lai', 'Reload'),
            icon: const Icon(Icons.refresh),
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
                        colors: [Color(0xFF0F172A), Color(0xFF0F766E)],
                        begin: Alignment.topLeft,
                        end: Alignment.bottomRight,
                      ),
                      borderRadius: BorderRadius.circular(24),
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          _pick('Ky so', 'Digital signing'),
                          style: TextStyle(
                            color: Color(0xFFCCFBF1),
                            fontWeight: FontWeight.w700,
                          ),
                        ),
                        const SizedBox(height: 8),
                        Text(
                          _pick('Hom thu forward van ban',
                              'Document forwarding mailbox'),
                          style: TextStyle(
                            color: Colors.white,
                            fontSize: 24,
                            fontWeight: FontWeight.w800,
                          ),
                        ),
                        const SizedBox(height: 8),
                        Text(
                          _pick(
                              'Theo doi toan bo thread forward, nguoi gui gan nhat, nguoi xu ly cuoi, ly do va trang thai ket thuc o mot noi.',
                              'Track every forwarding thread, latest sender, latest processor, reasons, and terminal status in one place.'),
                          style: TextStyle(
                            color: Color(0xFFF0FDFA),
                            height: 1.5,
                          ),
                        ),
                        const SizedBox(height: 16),
                        Wrap(
                          spacing: 10,
                          runSpacing: 10,
                          children: [
                            _MetricChip(
                                label: _pick('Tong thread', 'Total threads'),
                                value: '${_threads.length}'),
                            _MetricChip(
                                label: _pick('Đang forward', 'Forwarding'),
                                value: '$forwardCount'),
                            _MetricChip(
                                label: _pick('Kết thúc', 'Completed'),
                                value: '$completedCount'),
                            _MetricChip(
                                label: _pick('Tu choi', 'Rejected'),
                                value: '$rejectedCount'),
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
                          onChanged: _scheduleSearch,
                          decoration: InputDecoration(
                            hintText: _pick(
                                'Tìm theo văn bản, người gửi, người nhận, lý do hoặc tóm tắt xử lý...',
                                'Search by document, sender, recipient, reason, or processing summary...'),
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
                                      _load();
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
                            filterChip(
                                _pick('Tất cả', 'All'), 'all', _threads.length),
                            filterChip(_pick('Đang forward', 'Forwarding'),
                                'forward', forwardCount),
                            filterChip(_pick('Kết thúc', 'Completed'),
                                'completed', completedCount),
                            filterChip(_pick('Từ chối', 'Rejected'), 'rejected',
                                rejectedCount),
                          ],
                        ),
                        const SizedBox(height: 14),
                        ListFilterExtras(
                          dateFrom: _dateFrom,
                          dateTo: _dateTo,
                          onDateFrom: (d) => setState(() => _dateFrom = d),
                          onDateTo: (d) => setState(() => _dateTo = d),
                          personLabel:
                              _pick('Người gửi gần nhất', 'Latest sender'),
                          personOptions: _senderOptions,
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
                        borderRadius: BorderRadius.circular(18),
                      ),
                      child: Text(
                        _error!,
                        style: const TextStyle(color: Color(0xFF991B1B)),
                      ),
                    )
                  else if (_visibleThreads.isEmpty)
                    Container(
                      margin: const EdgeInsets.only(top: 16),
                      padding: const EdgeInsets.all(18),
                      decoration: BoxDecoration(
                        color: Colors.white,
                        borderRadius: BorderRadius.circular(22),
                        border: Border.all(color: const Color(0xFFE2E8F0)),
                      ),
                      child: Text(
                        _query.isEmpty
                            ? _pick('Chưa có văn bản nào trong Hòm thư.',
                                'There are no documents in the mailbox yet.')
                            : _pick(
                                'Không tìm thấy thread nào khớp từ khóa "$_query".',
                                'No threads matched "$_query".'),
                        style: const TextStyle(
                          color: Color(0xFF64748B),
                          height: 1.5,
                        ),
                      ),
                    )
                  else
                    ..._visibleThreads.map((thread) {
                      final entry = _entryForCurrentUser(thread);
                      final statusColor = _statusColor(thread.status);
                      final entryStatus = entry?.status;
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
                            Wrap(
                              spacing: 8,
                              runSpacing: 8,
                              children: [
                                Container(
                                  padding: const EdgeInsets.symmetric(
                                      horizontal: 10, vertical: 6),
                                  decoration: BoxDecoration(
                                    color: statusColor.withOpacity(0.12),
                                    borderRadius: BorderRadius.circular(999),
                                  ),
                                  child: Text(
                                    _statusLabel(thread.status),
                                    style: TextStyle(
                                      color: statusColor,
                                      fontWeight: FontWeight.w700,
                                    ),
                                  ),
                                ),
                                if (entryStatus != null)
                                  Container(
                                    padding: const EdgeInsets.symmetric(
                                        horizontal: 10, vertical: 6),
                                    decoration: BoxDecoration(
                                      color: const Color(0xFFF8FAFC),
                                      borderRadius: BorderRadius.circular(999),
                                      border: Border.all(
                                          color: const Color(0xFFE2E8F0)),
                                    ),
                                    child: Text(
                                      _pick(
                                          'Entry cua toi: ${_statusLabel(entryStatus)}',
                                          'My entry: ${_statusLabel(entryStatus)}'),
                                      style: const TextStyle(
                                        color: Color(0xFF334155),
                                        fontWeight: FontWeight.w700,
                                      ),
                                    ),
                                  ),
                              ],
                            ),
                            const SizedBox(height: 12),
                            Text(
                              thread.documentTitle,
                              style: const TextStyle(
                                fontSize: 18,
                                fontWeight: FontWeight.w800,
                                color: Color(0xFF0F172A),
                              ),
                            ),
                            const SizedBox(height: 10),
                            Text(
                              thread.lastActionSummary.isEmpty
                                  ? _pick(
                                      'Chua co cap nhat moi cho thread nay.',
                                      'No recent updates for this thread.')
                                  : thread.lastActionSummary,
                              style: const TextStyle(
                                color: Color(0xFF334155),
                                height: 1.5,
                              ),
                            ),
                            const SizedBox(height: 10),
                            Wrap(
                              spacing: 16,
                              runSpacing: 8,
                              children: [
                                _MetaLine(
                                  icon: Icons.person_outline,
                                  label: _pick(
                                      'Nguoi gui gan nhat: ${thread.latestSenderName.isEmpty ? '—' : thread.latestSenderName}',
                                      'Latest sender: ${thread.latestSenderName.isEmpty ? '—' : thread.latestSenderName}'),
                                ),
                                _MetaLine(
                                  icon: Icons.account_tree_outlined,
                                  label: _pick(
                                      'So nhanh: ${thread.branchCount}',
                                      'Branches: ${thread.branchCount}'),
                                ),
                                _MetaLine(
                                  icon: Icons.schedule_outlined,
                                  label: _pick(
                                      'Cap nhat: ${_formatDate(thread.updatedAt)}',
                                      'Updated: ${_formatDate(thread.updatedAt)}'),
                                ),
                                if (thread.latestTerminalActorName.isNotEmpty)
                                  _MetaLine(
                                    icon: Icons.task_alt_outlined,
                                    label: _pick(
                                        'Nguoi xu ly cuoi: ${thread.latestTerminalActorName}',
                                        'Latest processor: ${thread.latestTerminalActorName}'),
                                  ),
                              ],
                            ),
                            if (thread.lastActionReason.isNotEmpty) ...[
                              const SizedBox(height: 8),
                              Text(
                                _pick(
                                    'Ly do gan nhat: ${thread.lastActionReason}',
                                    'Latest reason: ${thread.lastActionReason}'),
                                style: const TextStyle(
                                  color: Color(0xFF64748B),
                                  height: 1.45,
                                ),
                              ),
                            ],
                            const SizedBox(height: 14),
                            Wrap(
                              spacing: 10,
                              runSpacing: 10,
                              children: [
                                FilledButton.icon(
                                  // Điều hướng người dùng sang màn phù hợp theo kết quả thao tác hiện tại.

                                  onPressed: () =>
                                      context.go('/mailbox/${thread.id}'),
                                  icon: const Icon(Icons.open_in_new_outlined),
                                  label: Text(
                                      _pick('Mo chi tiet', 'Open details')),
                                ),
                                OutlinedButton.icon(
                                  // Điều hướng người dùng sang màn phù hợp theo kết quả thao tác hiện tại.

                                  onPressed: () => context
                                      .go('/documents/${thread.documentId}'),
                                  icon: const Icon(Icons.description_outlined),
                                  label: Text(
                                      _pick('Mo van ban', 'Open document')),
                                ),
                                OutlinedButton.icon(
                                  onPressed: entry == null
                                      ? null
                                      : () => _verifyEntry(entry),
                                  icon: const Icon(Icons.verified_outlined),
                                  label: Text(_pick('Kiem tra', 'Verify')),
                                ),
                              ],
                            ),
                          ],
                        ),
                      );
                    }),
                ],
              ),
      ),
    );
  }
}

// Mục đích: Lớp `_MetricChip` triển khai phần việc `Metric Chip` trong flutter_frontend/lib/screens/documents/mailbox_screen_modern.dart.
// Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
// Vai trò trong hệ thống: Đây là lớp thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
// Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

class _MetricChip extends StatelessWidget {
  final String label;
  final String value;

  const _MetricChip({
    required this.label,
    required this.value,
  });

  @override
  // Mục đích: Phương thức `build` triển khai phần việc `build` trong flutter_frontend/lib/screens/documents/mailbox_screen_modern.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

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
          Text(
            value,
            style: const TextStyle(
              color: Colors.white,
              fontSize: 20,
              fontWeight: FontWeight.w800,
            ),
          ),
          const SizedBox(height: 4),
          Text(
            label,
            style: const TextStyle(color: Color(0xFFF0FDFA)),
          ),
        ],
      ),
    );
  }
}

// Mục đích: Lớp `_MetaLine` triển khai phần việc `Meta Line` trong flutter_frontend/lib/screens/documents/mailbox_screen_modern.dart.
// Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
// Vai trò trong hệ thống: Đây là lớp thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
// Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

class _MetaLine extends StatelessWidget {
  final IconData icon;
  final String label;

  const _MetaLine({
    required this.icon,
    required this.label,
  });

  @override
  // Mục đích: Phương thức `build` triển khai phần việc `build` trong flutter_frontend/lib/screens/documents/mailbox_screen_modern.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  Widget build(BuildContext context) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Icon(icon, size: 15, color: const Color(0xFF64748B)),
        const SizedBox(width: 6),
        Text(
          label,
          style: const TextStyle(
            color: Color(0xFF334155),
            fontWeight: FontWeight.w600,
          ),
        ),
      ],
    );
  }
}
