// Tệp này dùng để: dựng giao diện và orchestration UI trong flutter_frontend/lib/screens/documents/mailbox_detail_screen_modern.dart.
// Cách hoạt động: nhận state từ provider, dựng widget, phản ứng sự kiện và gửi thao tác ngược về backend khi người dùng tương tác.
// Vai trò trong hệ thống: Đây là màn hình Flutter mà người dùng tương tác trực tiếp.
// Tác dụng khi hệ thống vận hành: biến nghiệp vụ backend thành trải nghiệm thao tác cụ thể trên web.

import 'dart:async';
import 'dart:html' as html;

import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/api_client.dart';
import '../../l10n/app_strings.dart';
import '../../models/signing.dart';
import '../../providers/auth_provider.dart';
import '../../providers/signing_summary_provider.dart';
import '../../widgets/pdf/web_pdf_frame.dart';

// Mục đích: Widget `MailboxDetailScreen` triển khai phần việc `Mailbox Detail Screen` trong flutter_frontend/lib/screens/documents/mailbox_detail_screen_modern.dart.
// Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
// Vai trò trong hệ thống: Đây là widget thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
// Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

class MailboxDetailScreen extends ConsumerStatefulWidget {
  final int threadId;
  const MailboxDetailScreen({super.key, required this.threadId});

  @override
  ConsumerState<MailboxDetailScreen> createState() =>
      _MailboxDetailScreenState();
}

// Mục đích: Widget `_MailboxDetailScreenState` triển khai phần việc `Mailbox Detail Screen State` trong flutter_frontend/lib/screens/documents/mailbox_detail_screen_modern.dart.
// Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
// Vai trò trong hệ thống: Đây là widget thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
// Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

class _MailboxDetailScreenState extends ConsumerState<MailboxDetailScreen> {
  AppStrings get _strings => AppStrings.of(context);
  String _pick(String vi, String en) => _strings.pick(vi, en);

  final _timelineSearchController = TextEditingController();
  MailboxThreadItem? _thread;
  String? _pdfUrl;
  String? _previewError;
  bool _loading = true;
  bool _actionLoading = false;
  String? _error;
  String _timelineQuery = '';
  String _timelineStatusFilter = 'all';
  Timer? _pdfAutoReloadTimer;

  @override
  // Mục đích: Phương thức `initState` triển khai phần việc `init State` trong flutter_frontend/lib/screens/documents/mailbox_detail_screen_modern.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  void initState() {
    super.initState();
    _load();
  }

  @override
  // Mục đích: Phương thức `dispose` triển khai phần việc `dispose` trong flutter_frontend/lib/screens/documents/mailbox_detail_screen_modern.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  void dispose() {
    _stopPdfAutoReload();
    _timelineSearchController.dispose();
    final current = _pdfUrl;
    if (current != null && current.isNotEmpty)
      html.Url.revokeObjectUrl(current);
    super.dispose();
  }

  void _stopPdfAutoReload() {
    _pdfAutoReloadTimer?.cancel();
    _pdfAutoReloadTimer = null;
  }

  void _restartPdfAutoReload() {
    _stopPdfAutoReload();
    _pdfAutoReloadTimer = Timer.periodic(const Duration(seconds: 10), (_) {
      if (!mounted || _loading) return;
      if (_pdfUrl == null || _pdfUrl!.isEmpty) return;
      _load(silent: true);
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

  // Mục đích: Phương thức `_previewPath` triển khai phần việc `preview Path` trong flutter_frontend/lib/screens/documents/mailbox_detail_screen_modern.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  String _previewPath(MailboxThreadItem thread, MailboxEntryItem? entry) =>
      entry != null
          ? 'mailbox/entries/${entry.id}/preview-pdf/'
          : 'mailbox/${thread.id}/preview-pdf/';

  // Mục đích: Phương thức `_verifyPath` triển khai phần việc `verify Path` trong flutter_frontend/lib/screens/documents/mailbox_detail_screen_modern.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  String _verifyPath(MailboxThreadItem thread, MailboxEntryItem? entry) =>
      entry != null
          ? 'mailbox/entries/${entry.id}/verify/'
          : 'mailbox/${thread.id}/verify/';

  // Mục đích: Phương thức `_load` triển khai phần việc `load` trong flutter_frontend/lib/screens/documents/mailbox_detail_screen_modern.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  Future<void> _load({bool silent = false}) async {
    // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

    if (!silent) {
      setState(() {
        _loading = true;
        _error = null;
        _previewError = null;
      });
    }
    try {
      // Gọi API hoặc tác vụ bất đồng bộ rồi chờ kết quả trước khi cập nhật giao diện.

      final detailResp =
          await ApiClient().dio.get('mailbox/${widget.threadId}/');
      final thread = MailboxThreadItem.fromJson(
          Map<String, dynamic>.from(detailResp.data as Map));
      final entry = _entryForCurrentUser(thread);
      String? nextUrl;
      String? nextPreviewError;
      try {
        // Gọi API hoặc tác vụ bất đồng bộ rồi chờ kết quả trước khi cập nhật giao diện.

        final pdfResp = await ApiClient().dio.get(
              _previewPath(thread, entry),
              queryParameters: {
                'ts': DateTime.now().millisecondsSinceEpoch.toString(),
              },
              options: Options(
                  responseType: ResponseType.bytes,
                  validateStatus: (status) => status != null && status < 500),
            );
        if ((pdfResp.statusCode ?? 500) >= 400) {
          final data = pdfResp.data;
          nextPreviewError = data is Map && data['detail'] != null
              ? data['detail'].toString()
              : _pick('Khong mo duoc PDF trong Hom thu.',
                  'Could not open the mailbox PDF.');
        } else {
          final blob =
              html.Blob([pdfResp.data as List<int>], 'application/pdf');
          nextUrl = html.Url.createObjectUrlFromBlob(blob);
        }
      } on DioException catch (error) {
        nextPreviewError =
            error.response?.data?['detail']?.toString() ?? error.message;
      }
      if (!mounted) {
        if (nextUrl != null && nextUrl.isNotEmpty)
          html.Url.revokeObjectUrl(nextUrl);
        return;
      }
      final current = _pdfUrl;
      if (current != null && current.isNotEmpty)
        html.Url.revokeObjectUrl(current);
      // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

      setState(() {
        _thread = thread;
        _pdfUrl = nextUrl;
        _previewError = nextPreviewError;
        _loading = false;
      });
      if (nextUrl != null && nextUrl.isNotEmpty) {
        _restartPdfAutoReload();
      } else {
        _stopPdfAutoReload();
      }
    } on DioException catch (error) {
      if (!mounted) return;
      _stopPdfAutoReload();
      if (silent) return;
      // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

      setState(() {
        _error = error.response?.data?['detail']?.toString() ?? error.message;
        _loading = false;
      });
    } catch (error) {
      if (!mounted) return;
      _stopPdfAutoReload();
      if (silent) return;
      // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

      setState(() {
        _error = '$error';
        _loading = false;
      });
    }
  }

  // Mục đích: Phương thức `_showSnack` triển khai phần việc `show Snack` trong flutter_frontend/lib/screens/documents/mailbox_detail_screen_modern.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  void _showSnack(String message, {bool error = false}) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
          content: Text(message),
          backgroundColor: error ? const Color(0xFF991B1B) : null),
    );
  }

  // Mục đích: Phương thức `_verify` triển khai phần việc `verify` trong flutter_frontend/lib/screens/documents/mailbox_detail_screen_modern.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  Future<void> _verify() async {
    final thread = _thread;
    if (thread == null) return;
    try {
      // Gọi API hoặc tác vụ bất đồng bộ rồi chờ kết quả trước khi cập nhật giao diện.

      final resp = await ApiClient().dio.get(
            _verifyPath(thread, _entryForCurrentUser(thread)),
            options: Options(
                validateStatus: (status) => status != null && status < 500),
          );
      final data = Map<String, dynamic>.from(resp.data as Map);
      if (!mounted) return;
      await showDialog<void>(
        context: context,
        builder: (ctx) => AlertDialog(
          title: Text(_pick('Kiem tra PDF mailbox', 'Verify mailbox PDF')),
          content: SizedBox(
            width: 520,
            child: Text('${data['summary'] ?? ''}'),
          ),
          actions: [
            FilledButton(
                onPressed: () => Navigator.pop(ctx),
                child: Text(_pick('Dong', 'Close'))),
          ],
        ),
      );
    } on DioException catch (error) {
      _showSnack(
          error.response?.data?['detail']?.toString() ??
              _pick('Khong kiem tra duoc PDF mailbox.',
                  'Could not verify the mailbox PDF.'),
          error: true);
    }
  }

  // Mục đích: Phương thức `_downloadPreview` triển khai phần việc `download Preview` trong flutter_frontend/lib/screens/documents/mailbox_detail_screen_modern.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  Future<void> _downloadPreview() async {
    final thread = _thread;
    if (thread == null) return;
    try {
      // Gọi API hoặc tác vụ bất đồng bộ rồi chờ kết quả trước khi cập nhật giao diện.

      final resp = await ApiClient().dio.get(
          _previewPath(thread, _entryForCurrentUser(thread)),
          options: Options(responseType: ResponseType.bytes));
      final blob = html.Blob([resp.data as List<int>], 'application/pdf');
      final url = html.Url.createObjectUrlFromBlob(blob);
      html.AnchorElement(href: url)
        ..setAttribute('download', '${thread.documentTitle}_mailbox.pdf')
        ..click();
      html.Url.revokeObjectUrl(url);
    } on DioException catch (error) {
      _showSnack(
          error.response?.data?['detail']?.toString() ??
              _pick('Khong tai duoc PDF mailbox.',
                  'Could not download the mailbox PDF.'),
          error: true);
    }
  }

  // Mục đích: Phương thức `_signCurrentEntry` triển khai phần việc `sign Current Entry` trong flutter_frontend/lib/screens/documents/mailbox_detail_screen_modern.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  Future<void> _signCurrentEntry() async {
    final thread = _thread;
    final entry = thread == null ? null : _entryForCurrentUser(thread);
    if (entry == null) return;
    // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

    setState(() => _actionLoading = true);
    try {
      // Gọi API hoặc tác vụ bất đồng bộ rồi chờ kết quả trước khi cập nhật giao diện.

      final resp =
          await ApiClient().dio.post('mailbox/entries/${entry.id}/sign/');
      final data = Map<String, dynamic>.from(resp.data as Map);
      _showSnack(data['detail']?.toString() ??
          _pick('Tac vu ky da san sang.', 'The signing task is ready.'));
      final task = data['task'];
      final taskId = task is Map ? task['id'] as int? : null;
      if (taskId != null && data['already_signed'] != true && mounted) {
        // Điều hướng người dùng sang màn phù hợp theo kết quả thao tác hiện tại.

        context.go('/signing/tasks/$taskId');
        return;
      }
      await _load();
    } on DioException catch (error) {
      _showSnack(
          error.response?.data?['detail']?.toString() ??
              _pick('Khong tao duoc tac vu ky.',
                  'Could not create the signing task.'),
          error: true);
    } finally {
      // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

      if (mounted) setState(() => _actionLoading = false);
    }
  }

  // Mục đích: Phương thức `_actEntry` triển khai phần việc `act Entry` trong flutter_frontend/lib/screens/documents/mailbox_detail_screen_modern.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  Future<void> _actEntry(String action) async {
    final thread = _thread;
    final entry = thread == null ? null : _entryForCurrentUser(thread);
    if (entry == null) return;
    final controller = TextEditingController();
    final reason = await showDialog<String>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text(action == 'complete'
            ? _pick('Hoan thanh xu ly', 'Complete processing')
            : _pick('Tu choi xu ly', 'Reject processing')),
        content: TextField(
          controller: controller,
          minLines: 2,
          maxLines: 4,
          decoration: InputDecoration(
            labelText: action == 'complete'
                ? _pick('Ly do hoan thanh', 'Completion reason')
                : _pick('Ly do tu choi', 'Rejection reason'),
            border: const OutlineInputBorder(),
          ),
        ),
        actions: [
          TextButton(
              onPressed: () => Navigator.pop(ctx),
              child: Text(_pick('Huy', 'Cancel'))),
          FilledButton(
              onPressed: () => Navigator.pop(ctx, controller.text.trim()),
              child: Text(_pick('Xac nhan', 'Confirm'))),
        ],
      ),
    );
    controller.dispose();
    if (reason == null || reason.trim().isEmpty) return;
    // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

    setState(() => _actionLoading = true);
    try {
      // Gọi API hoặc tác vụ bất đồng bộ rồi chờ kết quả trước khi cập nhật giao diện.

      await ApiClient().dio.post(
          'mailbox/entries/${entry.id}/${action == 'complete' ? 'complete' : 'reject'}/',
          data: {'reason': reason.trim()});
      ref.invalidate(signingSummaryProvider);
      _showSnack(action == 'complete'
          ? _pick('Da hoan thanh xu ly.', 'Processing completed.')
          : _pick('Da tu choi xu ly.', 'Processing rejected.'));
      await _load();
    } on DioException catch (error) {
      _showSnack(
          error.response?.data?['detail']?.toString() ??
              _pick('Khong xu ly duoc entry.', 'Could not process the entry.'),
          error: true);
    } finally {
      // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

      if (mounted) setState(() => _actionLoading = false);
    }
  }

  // Mục đích: Phương thức `_forwardEntry` triển khai phần việc `forward Entry` trong flutter_frontend/lib/screens/documents/mailbox_detail_screen_modern.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  Future<void> _forwardEntry() async {
    final thread = _thread;
    final entry = thread == null ? null : _entryForCurrentUser(thread);
    if (entry == null) return;
    List<SigningCandidate> candidates = const [];
    try {
      // Gọi API hoặc tác vụ bất đồng bộ rồi chờ kết quả trước khi cập nhật giao diện.

      final resp = await ApiClient().dio.get('signing/candidates/');
      candidates = (resp.data as List<dynamic>)
          .map((item) =>
              SigningCandidate.fromJson(Map<String, dynamic>.from(item as Map)))
          .where((item) => item.id != entry.forwardedTo)
          .toList();
    } on DioException catch (error) {
      _showSnack(
          error.response?.data?['detail']?.toString() ??
              _pick('Khong tai duoc danh sach nguoi nhan.',
                  'Could not load the recipient list.'),
          error: true);
      return;
    }

    final selectedIds = <int>{};
    final noteController = TextEditingController();
    String query = '';
    final payload = await showDialog<Map<String, dynamic>>(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, setDialogState) {
          final visible = candidates.where((candidate) {
            final q = query.trim().toLowerCase();
            if (q.isEmpty) return true;
            return [
              candidate.fullName,
              candidate.username,
              candidate.title,
              candidate.label
            ].join(' ').toLowerCase().contains(q);
          }).toList();
          return AlertDialog(
            title:
                Text(_pick('Forward trong Hom thu', 'Forward within mailbox')),
            content: SizedBox(
              width: 640,
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  TextField(
                    decoration: InputDecoration(
                      prefixIcon: Icon(Icons.search),
                      hintText: _pick('Tim nguoi nhan', 'Find recipient'),
                      border: const OutlineInputBorder(),
                    ),
                    onChanged: (value) => setDialogState(() => query = value),
                  ),
                  const SizedBox(height: 12),
                  SizedBox(
                    height: 260,
                    child: visible.isEmpty
                        ? Center(
                            child: Text(_pick(
                                'Khong tim thay nguoi nhan phu hop.',
                                'No matching recipients found.')))
                        : ListView(
                            shrinkWrap: true,
                            children: visible.map((candidate) {
                              final selected =
                                  selectedIds.contains(candidate.id);
                              return CheckboxListTile(
                                value: selected,
                                title: Text(candidate.fullName),
                                subtitle: Text(candidate.label),
                                onChanged: (value) {
                                  setDialogState(() {
                                    if (value == true) {
                                      selectedIds.add(candidate.id);
                                    } else {
                                      selectedIds.remove(candidate.id);
                                    }
                                  });
                                },
                              );
                            }).toList(),
                          ),
                  ),
                  const SizedBox(height: 12),
                  TextField(
                    controller: noteController,
                    minLines: 2,
                    maxLines: 4,
                    decoration: InputDecoration(
                      labelText: _pick('Ghi chu forward', 'Forward note'),
                      border: const OutlineInputBorder(),
                    ),
                  ),
                ],
              ),
            ),
            actions: [
              TextButton(
                  onPressed: () => Navigator.pop(ctx),
                  child: Text(_pick('Huy', 'Cancel'))),
              FilledButton(
                onPressed: () => Navigator.pop(ctx, {
                  'user_ids': selectedIds.toList(),
                  'note': noteController.text.trim(),
                }),
                child: Text(_pick('Chuyển tiếp', 'Forward')),
              ),
            ],
          );
        },
      ),
    );
    noteController.dispose();
    if (payload == null) return;
    final userIds = (payload['user_ids'] as List<dynamic>).cast<int>();
    if (userIds.isEmpty) {
      _showSnack(
          _pick('Can chon it nhat mot nguoi nhan.',
              'Select at least one recipient.'),
          error: true);
      return;
    }

    // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

    setState(() => _actionLoading = true);
    try {
      // Gọi API hoặc tác vụ bất đồng bộ rồi chờ kết quả trước khi cập nhật giao diện.

      await ApiClient().dio.post('mailbox/entries/${entry.id}/forward/', data: {
        'user_ids': userIds,
        'note': payload['note'],
      });
      ref.invalidate(signingSummaryProvider);
      _showSnack('Đã forward trong Hòm thư.');
      await _load();
    } on DioException catch (error) {
      _showSnack(
          error.response?.data?['detail']?.toString() ??
              'Không forward được entry.',
          error: true);
    } finally {
      // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

      if (mounted) setState(() => _actionLoading = false);
    }
  }

  // Mục đích: Phương thức `_formatDateTime` triển khai phần việc `format Date Time` trong flutter_frontend/lib/screens/documents/mailbox_detail_screen_modern.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  String _formatDateTime(String value) {
    if (value.trim().isEmpty) return '—';
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

  // Mục đích: Phương thức `_statusLabel` triển khai phần việc `status Label` trong flutter_frontend/lib/screens/documents/mailbox_detail_screen_modern.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  String _statusLabel(String status) {
    switch (status) {
      case 'completed':
        return _pick('Ket thuc', 'Completed');
      case 'rejected':
        return _pick('Tu choi', 'Rejected');
      case 'forward':
        return _pick('Dang forward', 'Forwarding');
      case 'view':
        return _pick('Da xem', 'Viewed');
      default:
        return 'Không rõ';
    }
  }

  Color _statusColor(String status) {
    switch (status) {
      case 'completed':
        return const Color(0xFF166534);
      case 'rejected':
        return const Color(0xFF991B1B);
      case 'forward':
        return const Color(0xFF0F766E);
      case 'view':
        return const Color(0xFF1D4ED8);
      default:
        return const Color(0xFF475569);
    }
  }

  List<MailboxEntryItem> _filteredTimeline(List<MailboxEntryItem> entries) {
    return entries.where((entry) {
      if (_timelineStatusFilter != 'all' &&
          entry.status != _timelineStatusFilter) return false;
      final q = _timelineQuery.trim().toLowerCase();
      if (q.isEmpty) return true;
      final haystack = [
        entry.forwardedByName,
        entry.forwardedToName,
        entry.note,
        entry.actionReason,
        entry.actionedByName,
      ].join(' ').toLowerCase();
      return haystack.contains(q);
    }).toList();
  }

  @override
  // Mục đích: Phương thức `build` triển khai phần việc `build` trong flutter_frontend/lib/screens/documents/mailbox_detail_screen_modern.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  Widget build(BuildContext context) {
    final thread = _thread;
    final currentEntry = thread == null ? null : _entryForCurrentUser(thread);
    final canAct = currentEntry != null && currentEntry.status == 'view';
    final entries = thread == null
        ? const <MailboxEntryItem>[]
        : ([...thread.entries]
          ..sort((a, b) => a.createdAt.compareTo(b.createdAt)));
    final filteredEntries = _filteredTimeline(entries);

    if (_loading) {
      // Dựng khung màn hình chính để chứa app bar, body, action và các vùng giao diện khác.

      return const Scaffold(body: Center(child: CircularProgressIndicator()));
    }
    if (_error != null) {
      // Dựng khung màn hình chính để chứa app bar, body, action và các vùng giao diện khác.

      return Scaffold(
          appBar:
              AppBar(title: Text(_pick('Chi tiet Hom thu', 'Mailbox details'))),
          body: Center(
              child: Padding(
                  padding: const EdgeInsets.all(24),
                  child: Text('${_pick('Loi', 'Error')}: $_error'))));
    }
    if (thread == null) {
      // Dựng khung màn hình chính để chứa app bar, body, action và các vùng giao diện khác.

      return Scaffold(
          body: Center(
              child: Text(_pick('Khong tai duoc mailbox thread.',
                  'Could not load the mailbox thread.'))));
    }

    // Mục đích: Phương thức `chip` triển khai phần việc `chip` trong flutter_frontend/lib/screens/documents/mailbox_detail_screen_modern.dart.
    // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
    // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
    // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

    Widget chip(String label, String value) {
      final active = _timelineStatusFilter == value;
      return InkWell(
        // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

        onTap: () => setState(() => _timelineStatusFilter = value),
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

    final summary = ListView(
      padding: const EdgeInsets.fromLTRB(16, 16, 16, 24),
      children: [
        Container(
          padding: const EdgeInsets.all(20),
          decoration: BoxDecoration(
            gradient: const LinearGradient(
                colors: [Color(0xFF0F172A), Color(0xFF0F766E)]),
            borderRadius: BorderRadius.circular(24),
          ),
          child:
              Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text(thread.documentTitle,
                style: const TextStyle(
                    color: Colors.white,
                    fontSize: 24,
                    fontWeight: FontWeight.w800)),
            const SizedBox(height: 10),
            Text(
                thread.lastActionSummary.isEmpty
                    ? _pick('Chua co cap nhat mo ta gan nhat.',
                        'No recent update summary yet.')
                    : thread.lastActionSummary,
                style: const TextStyle(color: Color(0xFFE2E8F0), height: 1.5)),
            const SizedBox(height: 14),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: [
                Container(
                    padding:
                        const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                    decoration: BoxDecoration(
                        color: Colors.white.withOpacity(0.12),
                        borderRadius: BorderRadius.circular(999)),
                    child: Text(_statusLabel(thread.status),
                        style: const TextStyle(
                            color: Colors.white, fontWeight: FontWeight.w700))),
                if (currentEntry != null)
                  Container(
                      padding: const EdgeInsets.symmetric(
                          horizontal: 10, vertical: 6),
                      decoration: BoxDecoration(
                          color: Colors.white.withOpacity(0.12),
                          borderRadius: BorderRadius.circular(999)),
                      child: Text(
                          _pick(
                              'Entry cua toi: ${_statusLabel(currentEntry.status)}',
                              'My entry: ${_statusLabel(currentEntry.status)}'),
                          style: const TextStyle(
                              color: Colors.white,
                              fontWeight: FontWeight.w700))),
              ],
            ),
          ]),
        ),
        const SizedBox(height: 16),
        Container(
          padding: const EdgeInsets.all(18),
          decoration: BoxDecoration(
              color: Colors.white,
              borderRadius: BorderRadius.circular(22),
              border: Border.all(color: const Color(0xFFE2E8F0))),
          child:
              Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text(_pick('Tom tat', 'Summary'),
                style:
                    const TextStyle(fontSize: 18, fontWeight: FontWeight.w800)),
            const SizedBox(height: 12),
            Text('${_pick('Người tạo', 'Created by')}: ${thread.createdByName}',
                style: const TextStyle(color: Color(0xFF334155))),
            Text(
                '${_pick('Nguoi gui gan nhat', 'Latest sender')}: ${thread.latestSenderName.isEmpty ? '—' : thread.latestSenderName}',
                style: const TextStyle(color: Color(0xFF334155))),
            Text(
                '${_pick('Nguoi xu ly cuoi', 'Latest processor')}: ${thread.latestTerminalActorName.isEmpty ? '—' : thread.latestTerminalActorName}',
                style: const TextStyle(color: Color(0xFF334155))),
            Text('${_pick('So nhanh', 'Branches')}: ${thread.branchCount}',
                style: const TextStyle(color: Color(0xFF334155))),
            Text(
                '${_pick('Cap nhat', 'Updated')}: ${_formatDateTime(thread.updatedAt)}',
                style: const TextStyle(color: Color(0xFF334155))),
            if (thread.lastActionReason.isNotEmpty)
              Text(
                  '${_pick('Ly do gan nhat', 'Latest reason')}: ${thread.lastActionReason}',
                  style:
                      const TextStyle(color: Color(0xFF334155), height: 1.45)),
            const SizedBox(height: 14),
            Wrap(
              spacing: 10,
              runSpacing: 10,
              children: [
                OutlinedButton.icon(
                    onPressed: _verify,
                    icon: const Icon(Icons.verified_outlined),
                    label: Text(_pick('Kiem tra', 'Verify'))),
                OutlinedButton.icon(
                    onPressed: _downloadPreview,
                    icon: const Icon(Icons.download_outlined),
                    label:
                        Text(_pick('Tai PDF mailbox', 'Download mailbox PDF'))),
                // Điều hướng người dùng sang màn phù hợp theo kết quả thao tác hiện tại.

                OutlinedButton.icon(
                    onPressed: () =>
                        context.go('/documents/${thread.documentId}'),
                    icon: const Icon(Icons.description_outlined),
                    label: Text(_pick('Mo van ban', 'Open document'))),
                if (canAct)
                  FilledButton.icon(
                      onPressed: _actionLoading ? null : _signCurrentEntry,
                      icon: const Icon(Icons.edit_document),
                      label: Text(_pick('Ky', 'Sign'))),
                if (canAct)
                  OutlinedButton.icon(
                      onPressed: _actionLoading ? null : _forwardEntry,
                      icon: const Icon(Icons.forward_to_inbox_outlined),
                      label: Text(_pick('Chuyển tiếp', 'Forward'))),
                if (canAct)
                  FilledButton.icon(
                      onPressed:
                          _actionLoading ? null : () => _actEntry('complete'),
                      icon: const Icon(Icons.task_alt_outlined),
                      label: Text(_pick('Hoan thanh', 'Complete'))),
                if (canAct)
                  OutlinedButton.icon(
                      onPressed:
                          _actionLoading ? null : () => _actEntry('reject'),
                      icon: const Icon(Icons.reply_outlined),
                      label: Text(_pick('Tu choi', 'Reject'))),
              ],
            ),
          ]),
        ),
        const SizedBox(height: 16),
        Container(
          padding: const EdgeInsets.all(18),
          decoration: BoxDecoration(
              color: Colors.white,
              borderRadius: BorderRadius.circular(22),
              border: Border.all(color: const Color(0xFFE2E8F0))),
          child:
              Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text(_pick('Timeline', 'Timeline'),
                style:
                    const TextStyle(fontSize: 18, fontWeight: FontWeight.w800)),
            const SizedBox(height: 12),
            TextField(
              controller: _timelineSearchController,
              // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

              onChanged: (value) => setState(() => _timelineQuery = value),
              decoration: InputDecoration(
                hintText: _pick(
                    'Tim theo nguoi gui, nguoi nhan, ghi chu, ly do...',
                    'Search by sender, recipient, note, or reason...'),
                prefixIcon: const Icon(Icons.search),
                // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

                suffixIcon: _timelineQuery.isEmpty
                    ? null
                    : IconButton(
                        icon: const Icon(Icons.close),
                        onPressed: () {
                          _timelineSearchController.clear();
                          setState(() => _timelineQuery = '');
                        }),
                filled: true,
                fillColor: const Color(0xFFF8FAFC),
                border: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(16),
                    borderSide: BorderSide.none),
              ),
            ),
            const SizedBox(height: 14),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: [
                chip(_pick('Tat ca', 'All'), 'all'),
                chip(_pick('Da xem', 'Viewed'), 'view'),
                chip(_pick('Dang forward', 'Forwarding'), 'forward'),
                chip(_pick('Ket thuc', 'Completed'), 'completed'),
                chip(_pick('Tu choi', 'Rejected'), 'rejected')
              ],
            ),
            const SizedBox(height: 14),
            if (filteredEntries.isEmpty)
              Text(
                  _pick('Khong co entry nao khop bo loc timeline hien tai.',
                      'No entries matched the current timeline filters.'),
                  style: const TextStyle(color: Color(0xFF64748B), height: 1.5))
            else
              ...filteredEntries.map((entry) {
                final color = _statusColor(entry.status);
                return Container(
                  margin: const EdgeInsets.only(bottom: 12),
                  padding: const EdgeInsets.all(16),
                  decoration: BoxDecoration(
                      color: const Color(0xFFF8FAFC),
                      borderRadius: BorderRadius.circular(18),
                      border: Border.all(color: const Color(0xFFE2E8F0))),
                  child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Container(
                          padding: const EdgeInsets.symmetric(
                              horizontal: 10, vertical: 6),
                          decoration: BoxDecoration(
                              color: color.withOpacity(0.12),
                              borderRadius: BorderRadius.circular(999)),
                          child: Text(_statusLabel(entry.status),
                              style: TextStyle(
                                  color: color, fontWeight: FontWeight.w700)),
                        ),
                        const SizedBox(height: 12),
                        Text(
                            '${entry.forwardedByName} → ${entry.forwardedToName}',
                            style: const TextStyle(
                                fontSize: 16, fontWeight: FontWeight.w800)),
                        const SizedBox(height: 8),
                        Text(
                            '${_pick('Tao luc', 'Created at')}: ${_formatDateTime(entry.createdAt)}',
                            style: const TextStyle(color: Color(0xFF475569))),
                        if (entry.note.isNotEmpty)
                          Text('${_pick('Ghi chu', 'Note')}: ${entry.note}',
                              style: const TextStyle(
                                  color: Color(0xFF475569), height: 1.45)),
                        if (entry.actionedByName.isNotEmpty)
                          Text(
                              '${_pick('Nguoi xu ly', 'Processed by')}: ${entry.actionedByName}',
                              style: const TextStyle(color: Color(0xFF475569))),
                        if (entry.actionReason.isNotEmpty)
                          Text(
                              '${_pick('Ly do', 'Reason')}: ${entry.actionReason}',
                              style: const TextStyle(
                                  color: Color(0xFF475569), height: 1.45)),
                        if (entry.actionedAt.isNotEmpty)
                          Text(
                              '${_pick('Xu ly luc', 'Processed at')}: ${_formatDateTime(entry.actionedAt)}',
                              style: const TextStyle(color: Color(0xFF475569))),
                      ]),
                );
              }),
          ]),
        ),
      ],
    );

    final preview = Padding(
      padding: const EdgeInsets.fromLTRB(0, 16, 16, 24),
      child: _pdfUrl != null
          ? Container(
              decoration: BoxDecoration(
                  color: Colors.white,
                  borderRadius: BorderRadius.circular(24),
                  border: Border.all(color: const Color(0xFFE2E8F0))),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Padding(
                    padding: const EdgeInsets.fromLTRB(16, 16, 16, 4),
                    child: Wrap(
                      spacing: 10,
                      runSpacing: 10,
                      crossAxisAlignment: WrapCrossAlignment.center,
                      children: [
                        Text(
                          _pick('Ban xem PDF mailbox', 'Mailbox PDF preview'),
                          style: const TextStyle(
                              fontSize: 16, fontWeight: FontWeight.w700),
                        ),
                        OutlinedButton.icon(
                          onPressed: () => _load(silent: true),
                          icon: const Icon(Icons.refresh, size: 16),
                          label: Text(_pick('Tai lai', 'Reload')),
                        ),
                      ],
                    ),
                  ),
                  Padding(
                    padding: EdgeInsets.fromLTRB(16, 0, 16, 8),
                    child: Text(
                      _pick(
                        'He thong tu dong tai lai moi 10 giay sau khi PDF da hien thi.',
                        'The preview refreshes automatically every 10 seconds after the PDF is available.',
                      ),
                      style: const TextStyle(
                          color: Color(0xFF64748B), height: 1.45),
                    ),
                  ),
                  Expanded(
                    child: Padding(
                      padding: const EdgeInsets.all(12),
                      // Keep the embedded PDF read-only on web so the iframe does not
                      // steal pointer events from mailbox action buttons and dialogs.
                      child: WebPdfFrame(
                        viewKey: 'mailbox-thread-${widget.threadId}',
                        pdfUrl: _pdfUrl!,
                        interactive: false,
                      ),
                    ),
                  ),
                ],
              ),
            )
          : Container(
              padding: const EdgeInsets.all(24),
              decoration: BoxDecoration(
                  color: const Color(0xFFFFF7ED),
                  borderRadius: BorderRadius.circular(24),
                  border: Border.all(color: const Color(0xFFFED7AA))),
              child: Text(
                  _previewError ??
                      _pick('Preview chua kha dung.',
                          'Preview is not available yet.'),
                  style: const TextStyle(color: Color(0xFF7C2D12))),
            ),
    );

    // Dựng khung màn hình chính để chứa app bar, body, action và các vùng giao diện khác.

    return Scaffold(
      appBar: AppBar(
        title: Text(thread.documentTitle),
        // Điều hướng người dùng sang màn phù hợp theo kết quả thao tác hiện tại.

        leading: IconButton(
            icon: const Icon(Icons.arrow_back),
            onPressed: () =>
                context.canPop() ? context.pop() : context.go('/mailbox')),
        actions: [
          IconButton(icon: const Icon(Icons.refresh), onPressed: _load)
        ],
      ),
      body: LayoutBuilder(
        builder: (context, constraints) {
          if (constraints.maxWidth >= 1120) {
            return Row(children: [
              SizedBox(width: 520, child: summary),
              Expanded(child: preview)
            ]);
          }
          return Column(
            children: [
              Expanded(flex: 3, child: summary),
              Expanded(
                flex: 2,
                child: Padding(
                  padding: const EdgeInsets.fromLTRB(16, 0, 16, 16),
                  child: preview,
                ),
              ),
            ],
          );
        },
      ),
    );
  }
}
