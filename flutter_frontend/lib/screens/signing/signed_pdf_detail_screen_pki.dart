// === MÀN HÌNH CHI TIẾT PDF ĐÃ KÝ ===
// Xem PDF đã ký (preview auto-reload), tải ('download/'), và panel XÁC MINH chữ ký (_buildVerificationPanel 'verify/': trạng thái safe/tampered/untrusted..., hash _shortHash).
// - _load 'signed-pdfs/<id>/'. Có link sang hòm thư nếu PDF được forward.

// Tệp này dùng để: dựng giao diện và orchestration UI trong flutter_frontend/lib/screens/signing/signed_pdf_detail_screen_pki.dart.
import 'dart:async';
import 'dart:html' as html;

import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../core/api_client.dart';
import '../../l10n/app_strings.dart';
import '../../models/signing.dart';
import '../../widgets/pdf/web_pdf_frame.dart';

// Widget màn CHI TIẾT PDF ĐÃ KÝ; nhận id.

class SignedPdfDetailScreen extends StatefulWidget {
  final int id;

  // Widget màn CHI TIẾT PDF ĐÃ KÝ; nhận id.
  const SignedPdfDetailScreen({super.key, required this.id});

  @override
  State<SignedPdfDetailScreen> createState() => _SignedPdfDetailScreenState();
}

// State màn chi tiết PDF đã ký: xem trước, tải, panel xác minh chữ ký.

class _SignedPdfDetailScreenState extends State<SignedPdfDetailScreen> {
  SignedPdfDocumentItem? _item;
  SignedPdfVerificationItem? _verification;
  String? _pdfUrl;
  String? _previewError;
  bool _loading = true;
  String? _error;
  Timer? _pdfAutoReloadTimer;

  AppStrings get _strings => AppStrings.of(context);

  @override
  // Mở màn: nạp PDF đã ký (_load) và bật auto-reload preview.
  void initState() {
    super.initState();
    _load();
  }

  @override
  // Rời màn: dừng auto-reload PDF.
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

  // Khởi động lại tự tải lại PDF xem trước.
  void _restartPdfAutoReload() {
    _stopPdfAutoReload();
    _pdfAutoReloadTimer = Timer.periodic(const Duration(seconds: 10), (_) {
      if (!mounted || _loading) return;
      if (_pdfUrl == null || _pdfUrl!.isEmpty) return;
      _load(silent: true);
    });
  }

  // Tải chi tiết PDF đã ký + kết quả xác minh từ server.

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

      final detailResp = await ApiClient().dio.get('signed-pdfs/${widget.id}/');
      // Gọi API hoặc tác vụ bất đồng bộ rồi chờ kết quả trước khi cập nhật giao diện.

      final verifyResp = await ApiClient().dio.get(
            'signed-pdfs/${widget.id}/verify/',
            options: Options(
                validateStatus: (status) => status != null && status < 500),
          );

      final item = SignedPdfDocumentItem.fromJson(
          Map<String, dynamic>.from(detailResp.data as Map));
      final verification = SignedPdfVerificationItem.fromJson(
          Map<String, dynamic>.from(verifyResp.data as Map));

      String? nextUrl;
      String? previewError;
      if (verification.isAccessAllowed) {
        try {
          // Gọi API hoặc tác vụ bất đồng bộ rồi chờ kết quả trước khi cập nhật giao diện.

          final pdfResp = await ApiClient().dio.get(
                'signed-pdfs/${widget.id}/preview-pdf/',
                queryParameters: {
                  'ts': DateTime.now().millisecondsSinceEpoch.toString(),
                },
                options: Options(responseType: ResponseType.bytes),
              );
          final blob =
              html.Blob([pdfResp.data as List<int>], 'application/pdf');
          nextUrl = html.Url.createObjectUrlFromBlob(blob);
        } on DioException catch (error) {
          previewError =
              error.response?.data?['detail']?.toString() ?? error.message;
        }
      } else {
        previewError = verification.summary;
      }

      if (!mounted) {
        if (nextUrl != null && nextUrl.isNotEmpty) {
          html.Url.revokeObjectUrl(nextUrl);
        }
        return;
      }

      final current = _pdfUrl;
      if (current != null && current.isNotEmpty) {
        html.Url.revokeObjectUrl(current);
      }

      // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

      setState(() {
        _item = item;
        _verification = verification;
        _pdfUrl = nextUrl;
        _previewError = previewError;
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
        _error = error.toString();
        _loading = false;
      });
    }
  }

  // Tải PDF đã ký về máy ('download/').
  Future<void> _download() async {
    final verification = _verification;
    if (verification != null && !verification.isAccessAllowed) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            _strings.pick(
              'PDF này đang bị chặn vì xác minh thất bại sau khi ký.',
              'This PDF is blocked because verification failed after signing.',
            ),
          ),
        ),
      );
      return;
    }

    try {
      // Gọi API hoặc tác vụ bất đồng bộ rồi chờ kết quả trước khi cập nhật giao diện.

      final resp = await ApiClient().dio.get(
            'signed-pdfs/${widget.id}/download/',
            options: Options(responseType: ResponseType.bytes),
          );
      final bytes = resp.data as List<int>;
      final blob = html.Blob([bytes], 'application/pdf');
      final url = html.Url.createObjectUrlFromBlob(blob);
      html.AnchorElement(href: url)
        ..setAttribute('download', '${_item?.title ?? 'signed_pdf'}.pdf')
        ..click();
      html.Url.revokeObjectUrl(url);
    } catch (error) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            '${_strings.pick('Tải xuống thất bại', 'Download failed')}: $error',
          ),
        ),
      );
    }
  }

  // Định dạng thời điểm để hiển thị.
  String _formatDateTime(String value) {
    if (value.trim().isEmpty) return _strings.pick('Không rõ', 'Unknown');
    try {
      final dateTime = DateTime.parse(value).toLocal();
      final day = dateTime.day.toString().padLeft(2, '0');
      final month = dateTime.month.toString().padLeft(2, '0');
      final hour = dateTime.hour.toString().padLeft(2, '0');
      final minute = dateTime.minute.toString().padLeft(2, '0');
      final second = dateTime.second.toString().padLeft(2, '0');
      return '$day/$month/${dateTime.year} $hour:$minute:$second';
    } catch (_) {
      return value;
    }
  }

  // Rút gọn hash file để hiển thị (vd 8 ký tự đầu).
  String _shortHash(String value) {
    final trimmed = value.trim();
    if (trimmed.length <= 24) return trimmed;
    return '${trimmed.substring(0, 12)}...${trimmed.substring(trimmed.length - 12)}';
  }

  // Tiêu đề trạng thái xác minh.
  String _statusTitle(String status) {
    switch (status) {
      case 'safe':
        return 'Document is safe';
      case 'internal_approval':
        return 'Internal approval record';
      case 'untrusted':
        return 'Signature exists but CA is not trusted';
      case 'tampered':
        return 'File was changed after signing';
      case 'invalid':
        return 'Embedded signature is invalid';
      default:
        return 'Verification status is unknown';
    }
  }

  // Màu chữ theo trạng thái xác minh.
  Color _statusColor(String status) {
    switch (status) {
      case 'safe':
        return const Color(0xFF166534);
      case 'internal_approval':
        return const Color(0xFF1D4ED8);
      case 'untrusted':
        return const Color(0xFFB45309);
      case 'tampered':
      case 'invalid':
        return const Color(0xFFB91C1C);
      default:
        return const Color(0xFF475569);
    }
  }

  // Màu nền badge theo trạng thái xác minh.
  Color _statusBackground(String status) {
    switch (status) {
      case 'safe':
        return const Color(0xFFDCFCE7);
      case 'internal_approval':
        return const Color(0xFFDBEAFE);
      case 'untrusted':
        return const Color(0xFFFFF7ED);
      case 'tampered':
      case 'invalid':
        return const Color(0xFFFEE2E2);
      default:
        return const Color(0xFFF8FAFC);
    }
  }

  // Icon cho từng bước trong tiến trình xác minh.
  IconData _stepIcon(String status) {
    return status == 'passed' ? Icons.check_circle : Icons.error_outline;
  }

  // Màu cho từng bước xác minh.
  Color _stepColor(String status) {
    return status == 'passed'
        ? const Color(0xFF16A34A)
        : const Color(0xFFDC2626);
  }

  // Panel kết quả xác minh tổng thể (safe/tampered/untrusted..., hash) từ 'verify/'.
  Widget _buildVerificationPanel(SignedPdfVerificationItem verification) {
    final status = verification.status;
    final foreground = _statusColor(status);

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: _statusBackground(status),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: foreground.withOpacity(0.25)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Icon(
                verification.isSafe
                    ? Icons.verified_user_outlined
                    : Icons.gpp_bad_outlined,
                color: foreground,
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      _statusTitle(status),
                      style: TextStyle(
                        color: foreground,
                        fontWeight: FontWeight.w700,
                        fontSize: 16,
                      ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      verification.summary,
                      style: TextStyle(color: foreground),
                    ),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          Text(
            '${_strings.pick('Chế độ ký', 'Signature mode')}: ${verification.signatureMode}',
          ),
          Text(
            '${_strings.pick('Số chữ ký nhúng', 'Embedded signatures')}: ${verification.signatureCount}',
          ),
          if (verification.checkedAt.isNotEmpty)
            Text(
              '${_strings.pick('Thời điểm kiểm tra', 'Checked at')}: ${_formatDateTime(verification.checkedAt)}',
            ),
          if (verification.expectedHash.isNotEmpty ||
              verification.actualHash.isNotEmpty) ...[
            const SizedBox(height: 8),
            Text(
              '${_strings.pick('Hash kỳ vọng', 'Expected hash')}: ${_shortHash(verification.expectedHash)}',
            ),
            Text(
              '${_strings.pick('Hash thực tế', 'Actual hash')}: ${_shortHash(verification.actualHash)}',
            ),
          ],
          if (verification.steps.isNotEmpty) ...[
            const SizedBox(height: 14),
            ...verification.steps.map(
              (step) => Padding(
                padding: const EdgeInsets.only(bottom: 10),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Icon(_stepIcon(step.status),
                        size: 18, color: _stepColor(step.status)),
                    const SizedBox(width: 10),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            step.label,
                            style: const TextStyle(fontWeight: FontWeight.w600),
                          ),
                          const SizedBox(height: 2),
                          Text(
                            step.detail,
                            style: const TextStyle(color: Color(0xFF475569)),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ],
        ],
      ),
    );
  }

  // Panel dòng thời gian các chữ ký trên tài liệu.
  Widget _buildTimelinePanel(SignedPdfDocumentItem item) {
    if (item.signingEvents.isEmpty) {
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
            'Chưa có sự kiện ký nào.',
            'No signing event is available.',
          ),
          style: TextStyle(color: Color(0xFF475569)),
        ),
      );
    }

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: const Color(0xFFF8FAFC),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: const Color(0xFFE2E8F0)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            _strings.pick('Dòng thời gian ký', 'Signing timeline'),
            style: TextStyle(fontSize: 16, fontWeight: FontWeight.w700),
          ),
          const SizedBox(height: 12),
          ...item.signingEvents.map(
            (event) => Container(
              margin: const EdgeInsets.only(bottom: 10),
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: const Color(0xFFE2E8F0)),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    event.signerName,
                    style: const TextStyle(fontWeight: FontWeight.w700),
                  ),
                  const SizedBox(height: 4),
                  Text('${_strings.pick('Bước', 'Step')}: ${event.stepNo}'),
                  Text(
                      '${_strings.pick('Vai trò', 'Role')}: ${event.displayRole}'),
                  Text(
                    '${_strings.pick('Thời gian', 'Time')}: ${_formatDateTime(event.signedAt)}',
                  ),
                  if (event.certificateSubjectDn.isNotEmpty)
                    Text(
                      '${_strings.pick('Subject', 'Subject')}: ${event.certificateSubjectDn}',
                    ),
                  if (event.certificateSerialNumber.isNotEmpty)
                    Text(
                      '${_strings.pick('Serial', 'Serial')}: ${event.certificateSerialNumber}',
                    ),
                  if (event.signatureAlgorithm.isNotEmpty)
                    Text(
                      '${_strings.pick('Thuật toán chữ ký', 'Signature algorithm')}: ${event.signatureAlgorithm}',
                    ),
                  if (event.digestAlgorithm.isNotEmpty)
                    Text(
                      '${_strings.pick('Thuật toán băm', 'Digest algorithm')}: ${event.digestAlgorithm}',
                    ),
                  if (event.verificationStatus.isNotEmpty)
                    Text(
                      '${_strings.pick('Xác minh lưu trữ', 'Stored verification')}: ${event.verificationStatus}',
                    ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  // Panel chi tiết người ký + chứng thư đã xác minh.
  Widget _buildVerifySignerPanel(SignedPdfVerificationItem verification) {
    if (verification.signerReports.isEmpty) {
      return const SizedBox.shrink();
    }

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: const Color(0xFFF8FAFC),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: const Color(0xFFE2E8F0)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            _strings.pick(
              'Xác minh chữ ký nhúng',
              'Embedded signature verification',
            ),
            style: TextStyle(fontSize: 16, fontWeight: FontWeight.w700),
          ),
          const SizedBox(height: 12),
          ...verification.signerReports.map(
            (report) => Container(
              margin: const EdgeInsets.only(bottom: 10),
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: const Color(0xFFE2E8F0)),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    report.signerName.isNotEmpty
                        ? report.signerName
                        : report.fieldName,
                    style: const TextStyle(fontWeight: FontWeight.w700),
                  ),
                  const SizedBox(height: 4),
                  Text(
                      '${_strings.pick('Trạng thái', 'Status')}: ${report.status}'),
                  if (report.displayRole.isNotEmpty)
                    Text(
                        '${_strings.pick('Vai trò', 'Role')}: ${report.displayRole}'),
                  if (report.stepNo != null)
                    Text('${_strings.pick('Bước', 'Step')}: ${report.stepNo}'),
                  if (report.signedAt.isNotEmpty)
                    Text(
                      '${_strings.pick('Ký lúc', 'Signed at')}: ${_formatDateTime(report.signedAt)}',
                    ),
                  if (report.subjectDn.isNotEmpty)
                    Text(
                        '${_strings.pick('Subject', 'Subject')}: ${report.subjectDn}'),
                  if (report.serialNumber.isNotEmpty)
                    Text(
                        '${_strings.pick('Serial', 'Serial')}: ${report.serialNumber}'),
                  if (report.digestAlgorithm.isNotEmpty)
                    Text(
                        '${_strings.pick('Digest', 'Digest')}: ${report.digestAlgorithm}'),
                  if (report.signatureAlgorithm.isNotEmpty)
                    Text(
                      '${_strings.pick('Signature', 'Signature')}: ${report.signatureAlgorithm}',
                    ),
                  Text(report.detail),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  // Khung xem trước PDF (auto-reload).
  Widget _buildPreviewArea() {
    if (_pdfUrl != null) {
      return Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Wrap(
              spacing: 10,
              runSpacing: 10,
              crossAxisAlignment: WrapCrossAlignment.center,
              children: [
                Text(
                  _strings.pick('Bản xem PDF đã ký', 'Signed PDF preview'),
                  style: TextStyle(fontSize: 16, fontWeight: FontWeight.w700),
                ),
                OutlinedButton.icon(
                  onPressed: () => _load(silent: true),
                  icon: const Icon(Icons.refresh, size: 16),
                  label: Text(_strings.pick('Tải lại', 'Reload')),
                ),
              ],
            ),
            const SizedBox(height: 6),
            Text(
              _strings.pick(
                'Hệ thống tự động tải lại mỗi 10 giây sau khi PDF đã hiển thị.',
                'The system automatically reloads every 10 seconds after the PDF is displayed.',
              ),
              style: TextStyle(color: Color(0xFF64748B), height: 1.45),
            ),
            const SizedBox(height: 12),
            Expanded(
              child: WebPdfFrame(
                viewKey: 'signed-pdf-${widget.id}',
                pdfUrl: _pdfUrl!,
              ),
            ),
          ],
        ),
      );
    }

    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 560),
          child: Container(
            padding: const EdgeInsets.all(20),
            decoration: BoxDecoration(
              color: const Color(0xFFFFF7ED),
              borderRadius: BorderRadius.circular(16),
              border: Border.all(color: const Color(0xFFFED7AA)),
            ),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                const Icon(Icons.policy_outlined,
                    size: 36, color: Color(0xFFEA580C)),
                const SizedBox(height: 12),
                Text(
                  _strings.pick(
                    'Không thể xem trước PDF này',
                    'Cannot preview this PDF',
                  ),
                  style: TextStyle(fontSize: 16, fontWeight: FontWeight.w700),
                ),
                const SizedBox(height: 8),
                Text(
                  _previewError ??
                      _strings.pick(
                        'Bản xem trước hiện không khả dụng.',
                        'Preview is unavailable.',
                      ),
                  textAlign: TextAlign.center,
                  style: const TextStyle(color: Color(0xFF7C2D12)),
                ),
                const SizedBox(height: 12),
                OutlinedButton.icon(
                  onPressed: () => _load(silent: true),
                  icon: const Icon(Icons.refresh, size: 16),
                  label: Text(
                    _strings.pick('Thử tải lại PDF', 'Retry PDF load'),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  @override
  // Dựng màn: xem trước PDF + panel xác minh/người ký/timeline + nút tải.
  Widget build(BuildContext context) {
    final strings = AppStrings.of(context);
    final item = _item;
    final verification = _verification;

    // Dựng khung màn hình chính để chứa app bar, body, action và các vùng giao diện khác.

    return Scaffold(
      appBar: AppBar(
        title: Text(item?.title ?? 'Signed PDF'),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          // Điều hướng người dùng sang màn phù hợp theo kết quả thao tác hiện tại.

          onPressed: () =>
              context.canPop() ? context.pop() : context.go('/signed-pdfs'),
        ),
        actions: [
          if (item?.mailboxLatestThreadId != null)
            IconButton(
              icon: const Icon(Icons.forward_to_inbox_outlined),
              tooltip: strings.pick(
                'Mở luồng hòm thư',
                'Open mailbox thread',
              ),
              // Điều hướng người dùng sang màn phù hợp theo kết quả thao tác hiện tại.

              onPressed: () =>
                  context.go('/mailbox/${item!.mailboxLatestThreadId}'),
            ),
          IconButton(
            icon: const Icon(Icons.download),
            onPressed: item == null ||
                    (verification != null && !verification.isAccessAllowed)
                ? null
                : _download,
          ),
        ],
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
              : item == null || verification == null
                  ? Center(
                      child: Text(
                        strings.pick(
                          'Không tải được PDF đã ký.',
                          'Cannot load signed PDF.',
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
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Wrap(
                                spacing: 12,
                                runSpacing: 12,
                                children: [
                                  Text(
                                    '${strings.pick('Phiên bản', 'Version')} v${item.sourceVersionNumber}',
                                  ),
                                  Text(
                                    '${strings.pick('Chế độ', 'Mode')}: ${item.signatureMode}',
                                  ),
                                  Text(
                                    '${strings.pick('Số chữ ký', 'Signatures')}: ${item.signatureCount}',
                                  ),
                                  Text(
                                    '${strings.pick('Người ký', 'Signers')}: ${item.participantCount}',
                                  ),
                                  if (item.verificationStatus.isNotEmpty)
                                    Text(
                                      '${strings.pick('Xác minh lưu trữ', 'Stored verify')}: ${item.verificationStatus}',
                                    ),
                                  Text(
                                    '${strings.pick('Hoàn tất lúc', 'Completed')}: ${_formatDateTime(item.createdAt)}',
                                  ),
                                  if (item.ownerName.isNotEmpty)
                                    Text(
                                      '${strings.pick('Chủ sở hữu', 'Owner')}: ${item.ownerName}',
                                    ),
                                  if (item.mailboxThreadCount > 0)
                                    Text(
                                      '${strings.pick('Luồng hòm thư', 'Mailbox threads')}: ${item.mailboxThreadCount}',
                                    ),
                                ],
                              ),
                              if (item.mailboxLatestThreadId != null) ...[
                                const SizedBox(height: 12),
                                Wrap(
                                  spacing: 8,
                                  runSpacing: 8,
                                  children: [
                                    OutlinedButton.icon(
                                      // Điều hướng người dùng sang màn phù hợp theo kết quả thao tác hiện tại.

                                      onPressed: () => context.go(
                                          '/mailbox/${item.mailboxLatestThreadId}'),
                                      icon: const Icon(
                                          Icons.forward_to_inbox_outlined,
                                          size: 18),
                                      label: Text(
                                        strings.pick(
                                          'Mở luồng hòm thư',
                                          'Open mailbox thread',
                                        ),
                                      ),
                                    ),
                                  ],
                                ),
                              ],
                              const SizedBox(height: 16),
                              _buildVerificationPanel(verification),
                              const SizedBox(height: 16),
                              _buildTimelinePanel(item),
                              if (verification.signerReports.isNotEmpty) ...[
                                const SizedBox(height: 16),
                                _buildVerifySignerPanel(verification),
                              ],
                            ],
                          ),
                        ),
                        Expanded(child: _buildPreviewArea()),
                      ],
                    ),
    );
  }
}
