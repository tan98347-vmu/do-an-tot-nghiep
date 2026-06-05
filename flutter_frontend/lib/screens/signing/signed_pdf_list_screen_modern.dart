// Tệp này dùng để: dựng giao diện và orchestration UI trong flutter_frontend/lib/screens/signing/signed_pdf_list_screen_modern.dart.
// Cách hoạt động: nhận state từ provider, dựng widget, phản ứng sự kiện và gửi thao tác ngược về backend khi người dùng tương tác.
// Vai trò trong hệ thống: Đây là màn hình Flutter mà người dùng tương tác trực tiếp.
// Tác dụng khi hệ thống vận hành: biến nghiệp vụ backend thành trải nghiệm thao tác cụ thể trên web.

import 'dart:async';

import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../core/api_client.dart';
import '../../l10n/app_strings.dart';
import '../../models/signing.dart';
import '../../widgets/common/collapsible_filter_panel.dart';
import '../../widgets/common/list_filter_extras.dart';

// Mục đích: Widget `SignedPdfListScreen` triển khai phần việc `Signed Pdf List Screen` trong flutter_frontend/lib/screens/signing/signed_pdf_list_screen_modern.dart.
// Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
// Vai trò trong hệ thống: Đây là widget thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
// Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

class SignedPdfListScreen extends StatefulWidget {
  const SignedPdfListScreen({super.key});

  @override
  State<SignedPdfListScreen> createState() => _SignedPdfListScreenState();
}

// Mục đích: Widget `_SignedPdfListScreenState` triển khai phần việc `Signed Pdf List Screen State` trong flutter_frontend/lib/screens/signing/signed_pdf_list_screen_modern.dart.
// Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
// Vai trò trong hệ thống: Đây là widget thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
// Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

class _SignedPdfListScreenState extends State<SignedPdfListScreen> {
  AppStrings get _strings => AppStrings.of(context);
  String _pick(String vi, String en) => _strings.pick(vi, en);

  final _searchController = TextEditingController();
  Timer? _debounce;
  bool _loading = true;
  String? _error;
  List<SignedPdfDocumentItem> _items = const [];
  String _query = '';
  String _statusFilter = 'all';
  String _modeFilter = 'all';
  String _forwardFilter = 'all';
  DateTime? _dateFrom;
  DateTime? _dateTo;
  String _personFilter = ''; // lọc theo người ký

  List<SignedPdfDocumentItem> get _visibleItems => _items.where((item) {
        if (!dateInRange(item.createdAt, _dateFrom, _dateTo)) return false;
        if (_personFilter.isNotEmpty &&
            !item.participantNames
                .map((e) => e.trim())
                .contains(_personFilter)) {
          return false;
        }
        return true;
      }).toList();

  List<String> get _signerOptions {
    final set = <String>{};
    for (final item in _items) {
      for (final name in item.participantNames) {
        final n = name.trim();
        if (n.isNotEmpty) set.add(n);
      }
    }
    final list = set.toList()..sort();
    return list;
  }

  @override
  // Mục đích: Phương thức `initState` triển khai phần việc `init State` trong flutter_frontend/lib/screens/signing/signed_pdf_list_screen_modern.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  void initState() {
    super.initState();
    _load();
  }

  @override
  // Mục đích: Phương thức `dispose` triển khai phần việc `dispose` trong flutter_frontend/lib/screens/signing/signed_pdf_list_screen_modern.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  void dispose() {
    _debounce?.cancel();
    _searchController.dispose();
    super.dispose();
  }

  // Mục đích: Phương thức `_scheduleSearch` triển khai phần việc `schedule Search` trong flutter_frontend/lib/screens/signing/signed_pdf_list_screen_modern.dart.
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

  // Mục đích: Phương thức `_load` triển khai phần việc `load` trong flutter_frontend/lib/screens/signing/signed_pdf_list_screen_modern.dart.
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
      if (_query.trim().isNotEmpty) queryParameters['q'] = _query.trim();
      if (_statusFilter != 'all') queryParameters['status'] = _statusFilter;
      if (_modeFilter != 'all') queryParameters['mode'] = _modeFilter;
      if (_forwardFilter == 'forwarded') queryParameters['forwarded'] = '1';
      if (_forwardFilter == 'not_forwarded') queryParameters['forwarded'] = '0';

      // Gọi API hoặc tác vụ bất đồng bộ rồi chờ kết quả trước khi cập nhật giao diện.

      final response = await ApiClient()
          .dio
          .get('signed-pdfs/', queryParameters: queryParameters);
      final items = (response.data as List)
          .map((item) => SignedPdfDocumentItem.fromJson(
              Map<String, dynamic>.from(item as Map)))
          .toList();
      if (!mounted) return;
      // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

      setState(() {
        _items = items;
        _loading = false;
      });
    } on DioException catch (error) {
      if (!mounted) return;
      // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

      setState(() {
        _error = error.response?.data?['detail']?.toString() ??
            error.message ??
            _pick('Khong tai duoc PDF da ky.', 'Could not load signed PDFs.');
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

  // Mục đích: Phương thức `_formatDate` triển khai phần việc `format Date` trong flutter_frontend/lib/screens/signing/signed_pdf_list_screen_modern.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  String _formatDate(String value) {
    if (value.isEmpty) return _pick('Chua co thoi gian', 'No timestamp');
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

  // Mục đích: Phương thức `_statusLabel` triển khai phần việc `status Label` trong flutter_frontend/lib/screens/signing/signed_pdf_list_screen_modern.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  String _statusLabel(String status) {
    switch (status) {
      case 'safe':
        return _pick('An toan', 'Safe');
      case 'untrusted':
        return _pick('Khong tin cay', 'Untrusted');
      case 'invalid':
        return _pick('Khong hop le', 'Invalid');
      case 'tampered':
        return _pick('Bi chinh sua', 'Tampered');
      case 'internal_approval':
        return _pick('Noi bo', 'Internal');
      default:
        return _pick('Khong ro', 'Unknown');
    }
  }

  Color _statusColor(String status) {
    switch (status) {
      case 'safe':
        return const Color(0xFF166534);
      case 'untrusted':
        return const Color(0xFFB45309);
      case 'invalid':
      case 'tampered':
        return const Color(0xFFB91C1C);
      case 'internal_approval':
        return const Color(0xFF1D4ED8);
      default:
        return const Color(0xFF475569);
    }
  }

  // Mục đích: Phương thức `_modeLabel` triển khai phần việc `mode Label` trong flutter_frontend/lib/screens/signing/signed_pdf_list_screen_modern.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  String _modeLabel(String mode) => mode == 'pdf_pkcs7'
      ? 'PDF PKCS#7'
      : _pick('Xac nhan noi bo', 'Internal approval');

  @override
  // Mục đích: Phương thức `build` triển khai phần việc `build` trong flutter_frontend/lib/screens/signing/signed_pdf_list_screen_modern.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  Widget build(BuildContext context) {
    final safeCount =
        _items.where((item) => item.verificationStatus == 'safe').length;
    final forwardedCount =
        _items.where((item) => item.mailboxThreadCount > 0).length;

    // Mục đích: Phương thức `toggleChip` triển khai phần việc `toggle Chip` trong flutter_frontend/lib/screens/signing/signed_pdf_list_screen_modern.dart.
    // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
    // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
    // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

    Widget toggleChip(String label, bool active, VoidCallback onTap) {
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
          child: Text(label,
              style: TextStyle(
                  color: active
                      ? const Color(0xFF1D4ED8)
                      : const Color(0xFF334155),
                  fontWeight: FontWeight.w700)),
        ),
      );
    }

    // Dựng khung màn hình chính để chứa app bar, body, action và các vùng giao diện khác.

    return Scaffold(
      appBar: AppBar(
        title: Text(_pick('PDF da ky', 'Signed PDFs')),
        actions: [
          IconButton(
              icon: const Icon(Icons.refresh),
              tooltip: _pick('Tai lai', 'Reload'),
              onPressed: _load),
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
                          colors: [Color(0xFF082F49), Color(0xFF0F766E)]),
                      borderRadius: BorderRadius.circular(24),
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(_pick('Ky so', 'Digital signing'),
                            style: const TextStyle(
                                color: Color(0xFFCCFBF1),
                                fontWeight: FontWeight.w700)),
                        const SizedBox(height: 8),
                        Text(_pick('Kho PDF da ky', 'Signed PDF archive'),
                            style: const TextStyle(
                                color: Colors.white,
                                fontSize: 24,
                                fontWeight: FontWeight.w800)),
                        const SizedBox(height: 8),
                        Text(
                          _pick(
                            'Tim theo tieu de, nguoi ky, chu so huu, serial chung thu, certificate subject hoac hoat dong forward gan nhat.',
                            'Search by title, signer, owner, certificate serial, subject, or recent forwarding activity.',
                          ),
                          style: const TextStyle(
                              color: Color(0xFFF0FDFA), height: 1.5),
                        ),
                        const SizedBox(height: 16),
                        Wrap(
                          spacing: 10,
                          runSpacing: 10,
                          children: [
                            _TopMetric(
                                label: _pick('Ket qua', 'Results'),
                                value: '${_items.length}'),
                            _TopMetric(
                                label: _pick('An toan', 'Safe'),
                                value: '$safeCount'),
                            _TopMetric(
                                label: _pick('Da forward', 'Forwarded'),
                                value: '$forwardedCount'),
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
                        (_modeFilter != 'all' ? 1 : 0) +
                        (_forwardFilter != 'all' ? 1 : 0) +
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
                          onSubmitted: (_) => _load(),
                          decoration: InputDecoration(
                            hintText: _pick(
                              'Tim theo tieu de, signer, owner, serial, subject, forwarder...',
                              'Search by title, signer, owner, serial, subject, or forwarder...',
                            ),
                            prefixIcon: const Icon(Icons.search),
                            suffixIcon: _query.isEmpty
                                ? null
                                : IconButton(
                                    icon: const Icon(Icons.close),
                                    tooltip:
                                        _pick('Xoa tu khoa', 'Clear keyword'),
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
                            // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

                            toggleChip(
                                _pick('Tat ca', 'All'), _statusFilter == 'all',
                                () {
                              setState(() => _statusFilter = 'all');
                              _load();
                            }),
                            // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

                            toggleChip(_pick('An toan', 'Safe'),
                                _statusFilter == 'safe', () {
                              setState(() => _statusFilter = 'safe');
                              _load();
                            }),
                            // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

                            toggleChip(
                                'Untrusted', _statusFilter == 'untrusted', () {
                              setState(() => _statusFilter = 'untrusted');
                              _load();
                            }),
                            // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

                            toggleChip('Invalid', _statusFilter == 'invalid',
                                () {
                              setState(() => _statusFilter = 'invalid');
                              _load();
                            }),
                            // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

                            toggleChip('Tampered', _statusFilter == 'tampered',
                                () {
                              setState(() => _statusFilter = 'tampered');
                              _load();
                            }),
                            // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

                            toggleChip(_pick('Noi bo', 'Internal'),
                                _statusFilter == 'internal_approval', () {
                              setState(
                                  () => _statusFilter = 'internal_approval');
                              _load();
                            }),
                            // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

                            toggleChip('PDF PKCS#7', _modeFilter == 'pdf_pkcs7',
                                () {
                              setState(() => _modeFilter =
                                  _modeFilter == 'pdf_pkcs7'
                                      ? 'all'
                                      : 'pdf_pkcs7');
                              _load();
                            }),
                            // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

                            toggleChip(_pick('Noi bo', 'Internal'),
                                _modeFilter == 'internal_approval', () {
                              setState(() => _modeFilter =
                                  _modeFilter == 'internal_approval'
                                      ? 'all'
                                      : 'internal_approval');
                              _load();
                            }),
                            // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

                            toggleChip(_pick('Da forward', 'Forwarded'),
                                _forwardFilter == 'forwarded', () {
                              setState(() => _forwardFilter =
                                  _forwardFilter == 'forwarded'
                                      ? 'all'
                                      : 'forwarded');
                              _load();
                            }),
                            // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

                            toggleChip(_pick('Chua forward', 'Not forwarded'),
                                _forwardFilter == 'not_forwarded', () {
                              setState(() => _forwardFilter =
                                  _forwardFilter == 'not_forwarded'
                                      ? 'all'
                                      : 'not_forwarded');
                              _load();
                            }),
                          ],
                        ),
                        const SizedBox(height: 14),
                        ListFilterExtras(
                          dateFrom: _dateFrom,
                          dateTo: _dateTo,
                          onDateFrom: (d) => setState(() => _dateFrom = d),
                          onDateTo: (d) => setState(() => _dateTo = d),
                          personLabel: _pick('Người ký', 'Signer'),
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
                  else if (_visibleItems.isEmpty)
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
                                'Chua co PDF da ky nao phu hop voi quyen truy cap hien tai.',
                                'No signed PDFs are available with your current access.',
                              )
                            : _pick(
                                'Khong tim thay PDF da ky nao khop tu khoa "$_query".',
                                'No signed PDFs matched "$_query".',
                              ),
                        style: const TextStyle(
                            color: Color(0xFF64748B), height: 1.5),
                      ),
                    )
                  else
                    ..._visibleItems.map((item) {
                      final color = _statusColor(item.verificationStatus);
                      final signers = item.participantNames.isEmpty
                          ? _pick(
                              'Chua co danh sach signer', 'No signer list yet')
                          : item.participantNames.take(4).join(', ');
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
                                      color: color.withOpacity(0.12),
                                      borderRadius: BorderRadius.circular(999)),
                                  child: Text(
                                      _statusLabel(item.verificationStatus),
                                      style: TextStyle(
                                          color: color,
                                          fontWeight: FontWeight.w700)),
                                ),
                                Container(
                                  padding: const EdgeInsets.symmetric(
                                      horizontal: 10, vertical: 6),
                                  decoration: BoxDecoration(
                                      color: const Color(0xFFF8FAFC),
                                      borderRadius: BorderRadius.circular(999)),
                                  child: Text(_modeLabel(item.signatureMode),
                                      style: const TextStyle(
                                          fontWeight: FontWeight.w700)),
                                ),
                                if (item.mailboxThreadCount > 0)
                                  Container(
                                    padding: const EdgeInsets.symmetric(
                                        horizontal: 10, vertical: 6),
                                    decoration: BoxDecoration(
                                        color: const Color(0xFFE0F2FE),
                                        borderRadius:
                                            BorderRadius.circular(999)),
                                    child: Text(
                                        _pick('Da forward', 'Forwarded'),
                                        style: const TextStyle(
                                            color: Color(0xFF075985),
                                            fontWeight: FontWeight.w700)),
                                  ),
                              ],
                            ),
                            const SizedBox(height: 12),
                            Text(item.title,
                                style: const TextStyle(
                                    fontSize: 18, fontWeight: FontWeight.w800)),
                            const SizedBox(height: 10),
                            Text(
                                '${_pick('Version', 'Version')} ${item.sourceVersionNumber} • ${item.signatureCount} ${_pick('chu ky', 'signatures')} • ${item.participantCount} ${_pick('nguoi ky', 'signers')}',
                                style: const TextStyle(
                                    color: Color(0xFF334155), height: 1.5)),
                            const SizedBox(height: 4),
                            Text(
                                '${_pick('Chu so huu', 'Owner')}: ${item.ownerName.isEmpty ? _pick('Khong ro', 'Unknown') : item.ownerName}',
                                style:
                                    const TextStyle(color: Color(0xFF64748B))),
                            const SizedBox(height: 4),
                            Text('${_pick('Người ký', 'Signer')}: $signers',
                                style: const TextStyle(
                                    color: Color(0xFF64748B), height: 1.5)),
                            const SizedBox(height: 4),
                            Text(
                                '${_pick('Hoan tat', 'Completed')}: ${_formatDate(item.createdAt)}',
                                style:
                                    const TextStyle(color: Color(0xFF64748B))),
                            if (item.mailboxThreadCount > 0) ...[
                              const SizedBox(height: 8),
                              Text(
                                  '${_pick('Hom thu', 'Mailbox')}: ${item.mailboxLastSummary}',
                                  style: const TextStyle(
                                      color: Color(0xFF0F766E), height: 1.5)),
                            ],
                            const SizedBox(height: 14),
                            Wrap(
                              spacing: 10,
                              runSpacing: 10,
                              children: [
                                FilledButton.icon(
                                  // Điều hướng người dùng sang màn phù hợp theo kết quả thao tác hiện tại.

                                  onPressed: () =>
                                      context.go('/signed-pdfs/${item.id}'),
                                  icon: const Icon(Icons.visibility_outlined),
                                  label: Text(
                                      _pick('Xem chi tiet', 'View details')),
                                ),
                                if (item.mailboxLatestThreadId != null)
                                  OutlinedButton.icon(
                                    // Điều hướng người dùng sang màn phù hợp theo kết quả thao tác hiện tại.

                                    onPressed: () => context.go(
                                        '/mailbox/${item.mailboxLatestThreadId}'),
                                    icon: const Icon(
                                        Icons.forward_to_inbox_outlined),
                                    label: Text(
                                        _pick('Mo hom thu', 'Open mailbox')),
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

// Mục đích: Lớp `_TopMetric` triển khai phần việc `Top Metric` trong flutter_frontend/lib/screens/signing/signed_pdf_list_screen_modern.dart.
// Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
// Vai trò trong hệ thống: Đây là lớp thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
// Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

class _TopMetric extends StatelessWidget {
  final String label;
  final String value;

  const _TopMetric({required this.label, required this.value});

  @override
  // Mục đích: Phương thức `build` triển khai phần việc `build` trong flutter_frontend/lib/screens/signing/signed_pdf_list_screen_modern.dart.
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
          Text(value,
              style: const TextStyle(
                  color: Colors.white,
                  fontSize: 20,
                  fontWeight: FontWeight.w800)),
          const SizedBox(height: 4),
          Text(label, style: const TextStyle(color: Color(0xFFF0FDFA))),
        ],
      ),
    );
  }
}
