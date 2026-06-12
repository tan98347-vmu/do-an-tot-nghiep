// === MÀN HÌNH CHI TIẾT NHIỆM VỤ KÝ ===
// Xem PDF cần ký (preview auto-reload), ngữ cảnh chữ ký ('signature-context/' — chứng thư của tôi).
// - _signNow: KÝ ('sign/'); _rejectTask: từ chối ('reject/'). Ký xong -> xem PDF đã ký (/signed-pdfs/<id>).

// Tệp này dùng để: dựng giao diện và orchestration UI trong flutter_frontend/lib/screens/signing/signing_task_detail_screen_pki.dart.
import 'dart:async';
import 'dart:html' as html;

import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/api_client.dart';
import '../../l10n/app_strings.dart';
import '../../models/signing.dart';
import '../../providers/signing_summary_provider.dart';
import '../../widgets/pdf/web_pdf_frame.dart';

// Widget màn CHI TIẾT NHIỆM VỤ KÝ; nhận taskId.

class SigningTaskDetailScreen extends ConsumerStatefulWidget {
  final int taskId;

  // Widget màn CHI TIẾT NHIỆM VỤ KÝ; nhận taskId.
  const SigningTaskDetailScreen({super.key, required this.taskId});

  @override
  ConsumerState<SigningTaskDetailScreen> createState() =>
      _SigningTaskDetailScreenState();
}

// State màn chi tiết nhiệm vụ ký: xem trước PDF, ngữ cảnh chữ ký, ký/từ chối.

class _SigningTaskDetailScreenState
    extends ConsumerState<SigningTaskDetailScreen> {
  SigningTaskItem? _task;
  SigningTaskSignatureContext? _signatureContext;
  String? _pdfUrl;
  bool _loading = true;
  String? _error;
  bool _submitting = false;
  html.IFrameElement? _pdfFrame;
  Timer? _pdfAutoReloadTimer;

  AppStrings get _strings => AppStrings.of(context);

  @override
  // Mở màn: nạp nhiệm vụ ký (_load) và bật auto-reload khung xem trước PDF.
  void initState() {
    super.initState();
    _load();
  }

  @override
  // Rời màn: dừng auto-reload PDF và dọn tài nguyên.
  void dispose() {
    _stopPdfAutoReload();
    final current = _pdfUrl;
    if (current != null && current.isNotEmpty) {
      html.Url.revokeObjectUrl(current);
    }
    super.dispose();
  }

  void _stopPdfAutoReload() {
    _pdfAutoReloadTimer?.cancel();
    _pdfAutoReloadTimer = null;
  }

  // Khởi động lại vòng tự tải lại PDF xem trước (cập nhật khi file đổi).
  void _restartPdfAutoReload() {
    _stopPdfAutoReload();
    _pdfAutoReloadTimer = Timer.periodic(const Duration(seconds: 10), (_) {
      if (!mounted || _loading) return;
      if (_pdfUrl == null || _pdfUrl!.isEmpty) return;
      _load(silent: true);
    });
  }

  // Bật/tắt tương tác với khung PDF (chặn thao tác khi đang xử lý).
  void _setPdfInteractivity(bool enabled) {
    final frame = _pdfFrame;
    if (frame == null) return;
    frame.style.pointerEvents = enabled ? 'auto' : 'none';
  }

  // Tải chi tiết nhiệm vụ ký từ server (preview + ngữ cảnh chữ ký).

  Future<void> _load({bool silent = false}) async {
    // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

    if (!silent) {
      setState(() {
        _loading = true;
        _error = null;
      });
    }

    try {
      // Gọi API hoặc tác vụ bất đồng bộ rồi chờ kết quả trước khi cập nhật giao diện.

      final detailResp =
          await ApiClient().dio.get('signing/tasks/${widget.taskId}/');
      // Gọi API hoặc tác vụ bất đồng bộ rồi chờ kết quả trước khi cập nhật giao diện.

      final contextResp = await ApiClient()
          .dio
          .get('signing/tasks/${widget.taskId}/signature-context/');
      // Gọi API hoặc tác vụ bất đồng bộ rồi chờ kết quả trước khi cập nhật giao diện.

      final pdfResp = await ApiClient().dio.get(
            'signing/tasks/${widget.taskId}/preview-pdf/',
            queryParameters: {
              'ts': DateTime.now().millisecondsSinceEpoch.toString(),
            },
            options: Options(responseType: ResponseType.bytes),
          );

      final task = SigningTaskItem.fromJson(
          Map<String, dynamic>.from(detailResp.data as Map));
      final signatureContext = SigningTaskSignatureContext.fromJson(
        Map<String, dynamic>.from(contextResp.data as Map),
      );
      final blob = html.Blob([pdfResp.data as List<int>], 'application/pdf');
      final nextUrl = html.Url.createObjectUrlFromBlob(blob);

      if (!mounted) {
        html.Url.revokeObjectUrl(nextUrl);
        return;
      }

      final current = _pdfUrl;
      if (current != null && current.isNotEmpty) {
        html.Url.revokeObjectUrl(current);
      }

      // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

      setState(() {
        _task = task;
        _signatureContext = signatureContext;
        _pdfUrl = nextUrl;
        _loading = false;
      });
      _restartPdfAutoReload();
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
        _error = error.toString();
        _loading = false;
      });
    }
  }

  // Nút KÝ NGAY: gọi 'sign/' ký tài liệu bằng chứng thư của mình; xong chuyển sang xem PDF đã ký.
  Future<void> _signNow() async {
    final task = _task;
    final contextData = _signatureContext;
    if (task == null) return;

    if (task.signatureMode == 'pdf_pkcs7' &&
        (contextData == null || !contextData.canSign)) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            contextData != null && contextData.reason.isNotEmpty
                ? contextData.reason
                : _strings.pick(
                    'Người ký này chưa có chứng thư PKI sẵn sàng.',
                    'This signer does not have a ready PKI credential.',
                  ),
          ),
        ),
      );
      return;
    }

    final passwordCtrl = TextEditingController();
    _setPdfInteractivity(false);
    final password = await showDialog<String>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text(_strings.pick('Xác nhận ký', 'Confirm signing')),
        content: TextField(
          controller: passwordCtrl,
          autofocus: true,
          obscureText: true,
          decoration: InputDecoration(
            labelText: _strings.pick('Mật khẩu hiện tại', 'Current password'),
            border: OutlineInputBorder(),
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: Text(_strings.pick('Hủy', 'Cancel')),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(ctx, passwordCtrl.text),
            child: Text(_strings.pick('Ký ngay', 'Sign now')),
          ),
        ],
      ),
    ).whenComplete(() => _setPdfInteractivity(true));
    passwordCtrl.dispose();

    if (password == null || password.isEmpty) return;

    // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

    setState(() => _submitting = true);
    try {
      // Gọi API hoặc tác vụ bất đồng bộ rồi chờ kết quả trước khi cập nhật giao diện.

      final resp = await ApiClient().dio.post(
        'signing/tasks/${widget.taskId}/sign/',
        data: {'reauth_password': password},
      );
      ref.invalidate(signingSummaryProvider);

      if (!mounted) return;
      final signedPdf = resp.data['signed_pdf'];
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            signedPdf is Map
                ? _strings.pick(
                    'Ký thành công. PDF cuối cùng đã sẵn sàng.',
                    'Signed successfully. Final PDF is ready.',
                  )
                : _strings.pick(
                    'Ký thành công. Quy trình đã chuyển sang bước tiếp theo.',
                    'Signed successfully. The workflow moved to the next step.',
                  ),
          ),
        ),
      );

      if (signedPdf is Map && signedPdf['id'] != null) {
        // Điều hướng người dùng sang màn phù hợp theo kết quả thao tác hiện tại.

        context.go('/signed-pdfs/${signedPdf['id']}');
        return;
      }
      await _load();
    } on DioException catch (error) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            error.response?.data?['detail']?.toString() ??
                error.message ??
                _strings.pick('Ký thất bại', 'Signing failed'),
          ),
        ),
      );
    } finally {
      if (mounted) {
        // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

        setState(() => _submitting = false);
      }
    }
  }

  // Nút TỪ CHỐI: hỏi lý do rồi gọi 'reject/' để từ chối nhiệm vụ ký.
  Future<void> _rejectTask() async {
    final reasonCtrl = TextEditingController();
    _setPdfInteractivity(false);
    final reason = await showDialog<String>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text(
          _strings.pick('Từ chối yêu cầu ký', 'Reject signing request'),
        ),
        content: TextField(
          controller: reasonCtrl,
          autofocus: true,
          minLines: 2,
          maxLines: 4,
          decoration: InputDecoration(
            labelText: _strings.pick('Lý do', 'Reason'),
            border: OutlineInputBorder(),
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: Text(_strings.pick('Hủy', 'Cancel')),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(ctx, reasonCtrl.text.trim()),
            child: Text(_strings.pick('Từ chối', 'Reject')),
          ),
        ],
      ),
    ).whenComplete(() => _setPdfInteractivity(true));
    reasonCtrl.dispose();

    if (reason == null) return;

    // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

    setState(() => _submitting = true);
    try {
      // Gọi API hoặc tác vụ bất đồng bộ rồi chờ kết quả trước khi cập nhật giao diện.

      await ApiClient().dio.post(
        'signing/tasks/${widget.taskId}/reject/',
        data: {'reason': reason},
      );
      ref.invalidate(signingSummaryProvider);
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            _strings.pick(
              'Đã từ chối yêu cầu ký.',
              'Signing request rejected.',
            ),
          ),
        ),
      );
      await _load();
    } on DioException catch (error) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            error.response?.data?['detail']?.toString() ??
                error.message ??
                _strings.pick('Từ chối thất bại', 'Reject failed'),
          ),
        ),
      );
    } finally {
      if (mounted) {
        // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

        setState(() => _submitting = false);
      }
    }
  }

  // Dựng panel ngữ cảnh chữ ký: thông tin chứng thư/người ký lấy từ 'signature-context/'.
  Widget _buildSignatureContextPanel() {
    final task = _task;
    final contextData = _signatureContext;
    if (task == null || contextData == null) {
      return const SizedBox.shrink();
    }

    if (task.signatureMode != 'pdf_pkcs7') {
      return Container(
        width: double.infinity,
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: const Color(0xFFF8FAFC),
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: const Color(0xFFE2E8F0)),
        ),
        child: Text(
          _strings.pick(
            'Tác vụ này dùng chế độ phê duyệt nội bộ. Không cần chứng thư PKI.',
            'This task is using internal approval mode. No PKI credential is required.',
          ),
          style: TextStyle(color: Color(0xFF475569)),
        ),
      );
    }

    final certificate = contextData.certificate;
    final ready = contextData.canSign;
    final panelColor =
        ready ? const Color(0xFFDCFCE7) : const Color(0xFFFFF7ED);
    final accentColor =
        ready ? const Color(0xFF166534) : const Color(0xFFB45309);

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: panelColor,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: accentColor.withOpacity(0.25)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            ready
                ? _strings.pick(
                    'Chứng thư PKI đã sẵn sàng',
                    'PKI credential is ready',
                  )
                : _strings.pick(
                    'Chứng thư PKI chưa sẵn sàng',
                    'PKI credential is not ready',
                  ),
            style: TextStyle(
              color: accentColor,
              fontWeight: FontWeight.w700,
            ),
          ),
          const SizedBox(height: 8),
          if (certificate != null) ...[
            Text(
                '${_strings.pick('Nhà cung cấp', 'Provider')}: ${certificate.provider}'),
            if (certificate.subjectDn.isNotEmpty)
              Text(
                  '${_strings.pick('Subject', 'Subject')}: ${certificate.subjectDn}'),
            if (certificate.serialNumber.isNotEmpty)
              Text(
                  '${_strings.pick('Serial', 'Serial')}: ${certificate.serialNumber}'),
            if (certificate.issuerDn.isNotEmpty)
              Text(
                  '${_strings.pick('Issuer', 'Issuer')}: ${certificate.issuerDn}'),
            if (certificate.validTo.isNotEmpty)
              Text(
                  '${_strings.pick('Hết hạn', 'Expires')}: ${certificate.validTo}'),
          ] else
            Text(
              _strings.pick(
                'Không có chứng thư đang hoạt động cho người ký này.',
                'No active credential is bound to this signer.',
              ),
            ),
          if (contextData.providerMessage.isNotEmpty) ...[
            const SizedBox(height: 8),
            Text(
              contextData.providerMessage,
              style: const TextStyle(color: Color(0xFF475569)),
            ),
          ],
          if (contextData.reason.isNotEmpty && !ready) ...[
            const SizedBox(height: 8),
            Text(
              contextData.reason,
              style: const TextStyle(color: Color(0xFF9A3412)),
            ),
          ],
        ],
      ),
    );
  }

  @override
  // Dựng màn: AppBar + khung xem trước PDF + panel ngữ cảnh chữ ký + nút Ký/Từ chối; xử lý loading/lỗi.
  Widget build(BuildContext context) {
    final strings = AppStrings.of(context);
    final task = _task;

    // Dựng khung màn hình chính để chứa app bar, body, action và các vùng giao diện khác.

    return Scaffold(
      appBar: AppBar(
        title: Text(strings.pick('Tác vụ ký', 'Signing task')),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          // Điều hướng người dùng sang màn phù hợp theo kết quả thao tác hiện tại.

          onPressed: () =>
              context.canPop() ? context.pop() : context.go('/signing/tasks'),
        ),
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : _error != null
              ? Center(
                  child: Padding(
                    padding: const EdgeInsets.all(24),
                    child: Text('${strings.pick('Lỗi', 'Error')}: $_error'),
                  ),
                )
              : task == null || _pdfUrl == null
                  ? Center(
                      child: Text(
                        strings.pick(
                          'Không tải được tác vụ ký.',
                          'Cannot load signing task.',
                        ),
                      ),
                    )
                  : Column(
                      children: [
                        Container(
                          width: double.infinity,
                          padding: const EdgeInsets.all(16),
                          decoration: const BoxDecoration(
                            border: Border(
                                bottom: BorderSide(color: Color(0xFFE2E8F0))),
                          ),
                          child: Wrap(
                            spacing: 12,
                            runSpacing: 12,
                            crossAxisAlignment: WrapCrossAlignment.center,
                            children: [
                              Text(
                                task.documentTitle,
                                style: const TextStyle(
                                    fontSize: 18, fontWeight: FontWeight.w700),
                              ),
                              Chip(
                                label: Text(
                                  strings.pick(
                                    'Bước ${task.stepNo}',
                                    'Step ${task.stepNo}',
                                  ),
                                ),
                              ),
                              Chip(label: Text(task.displayRole)),
                              Chip(label: Text(task.signatureMode)),
                              if (task.availableNow) ...[
                                FilledButton.icon(
                                  onPressed: _submitting ||
                                          (task.signatureMode == 'pdf_pkcs7' &&
                                              !(_signatureContext?.canSign ??
                                                  false))
                                      ? null
                                      : _signNow,
                                  icon: const Icon(Icons.edit, size: 18),
                                  label:
                                      Text(strings.pick('Ký ngay', 'Sign now')),
                                ),
                                OutlinedButton.icon(
                                  onPressed: _submitting ? null : _rejectTask,
                                  icon: const Icon(Icons.close, size: 18),
                                  label:
                                      Text(strings.pick('Từ chối', 'Reject')),
                                ),
                              ] else
                                Text(
                                  task.status == 'signed'
                                      ? strings.pick(
                                          'Bạn đã ký tác vụ này.',
                                          'You already signed this task.',
                                        )
                                      : task.status == 'blocked'
                                          ? strings.pick(
                                              'Tác vụ này đang chờ bước trước hoàn tất.',
                                              'This task is waiting for a previous step.',
                                            )
                                          : strings.pick(
                                              'Tác vụ này không còn khả năng ký nữa.',
                                              'This task is not signable anymore.',
                                            ),
                                  style:
                                      const TextStyle(color: Color(0xFF475569)),
                                ),
                            ],
                          ),
                        ),
                        Padding(
                          padding: const EdgeInsets.fromLTRB(16, 16, 16, 0),
                          child: _buildSignatureContextPanel(),
                        ),
                        Expanded(
                          child: Padding(
                            padding: const EdgeInsets.all(12),
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Wrap(
                                  spacing: 10,
                                  runSpacing: 10,
                                  crossAxisAlignment: WrapCrossAlignment.center,
                                  children: [
                                    const Text(
                                      'Bản xem PDF ký số',
                                      style: TextStyle(
                                          fontSize: 16,
                                          fontWeight: FontWeight.w700),
                                    ),
                                    OutlinedButton.icon(
                                      onPressed: () => _load(silent: true),
                                      icon: const Icon(Icons.refresh, size: 16),
                                      label: Text(
                                          strings.pick('Tải lại', 'Reload')),
                                    ),
                                  ],
                                ),
                                const SizedBox(height: 6),
                                Text(
                                  strings.pick(
                                    'Hệ thống tự động tải lại mỗi 10 giây sau khi PDF đã hiển thị.',
                                    'The system automatically reloads every 10 seconds after the PDF is displayed.',
                                  ),
                                  style: TextStyle(
                                      color: Color(0xFF64748B), height: 1.45),
                                ),
                                const SizedBox(height: 12),
                                Expanded(
                                  child: WebPdfFrame(
                                    viewKey:
                                        'signing-task-${widget.taskId}-${task.status}',
                                    pdfUrl: _pdfUrl!,
                                    onFrameReady: (frame) {
                                      _pdfFrame = frame;
                                      _setPdfInteractivity(true);
                                    },
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
