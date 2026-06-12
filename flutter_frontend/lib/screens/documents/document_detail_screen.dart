// === MÀN HÌNH CHI TIẾT VĂN BẢN ===
// Xem nội dung + xem trước PDF (auto-reload), thông tin, version (documentVersionsProvider: ẩn/khôi phục version).
// - Thao tác: tải DOCX ('download/'), hoàn tất ('finalize/'), lưu trữ ('archive/'), yêu thích ('favorite/'), sửa thủ công (/documents/<id>/manual-edit), tóm tắt (/summaries/<id>), chỉnh bằng Word AI (_refreshAfterWordAiCompletion).
// - Khởi tạo quy trình KÝ (chọn người ký _SignerDraftRow) hoặc FORWARD hòm thư (_ForwardRecipientRow). Provider: documentDetailProvider, currentUserProvider.

// Tệp này dùng để: dựng giao diện và orchestration UI trong flutter_frontend/lib/screens/documents/document_detail_screen.dart.
import 'dart:async';
import 'dart:html' as html;
import 'dart:ui_web' as ui;
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:dio/dio.dart';
import '../../core/api_client.dart';
import '../../l10n/app_strings.dart';
import '../../providers/documents_provider.dart';
import '../../providers/auth_provider.dart';
import '../../providers/signing_summary_provider.dart';
import '../../models/ai_task_state.dart';
import '../../models/assistant_quick_sign.dart';
import '../../models/document_version.dart';
import '../../models/signing.dart';
import '../../core/iframe_blocker.dart';
import '../../widgets/ai_loading/ai_task_linear_progress.dart';
import '../../widgets/documents/assistant_quick_sign_panel.dart';
import '../../widgets/documents/document_ai_edit_panel.dart';
import '../../widgets/documents/document_manual_edit_card.dart';
import '../../widgets/documents/summary_options_dialog.dart';
import '../../widgets/documents/word_edit_history_panel.dart';
import '../../widgets/sharing/unified_share_sheet.dart';

// Widget màn CHI TIẾT VĂN BẢN (ConsumerStatefulWidget); nhận id văn bản cần xem.

class DocumentDetailScreen extends ConsumerStatefulWidget {
  final int id;
  // Widget màn CHI TIẾT VĂN BẢN; nhận id.
  const DocumentDetailScreen({super.key, required this.id});

  @override
  ConsumerState<DocumentDetailScreen> createState() =>
      _DocumentDetailScreenState();
}

// State màn chi tiết: giữ controller xem trước PDF/HTML, trạng thái tóm tắt/ký nhanh và toàn bộ thao tác trên văn bản.

class _DocumentDetailScreenState extends ConsumerState<DocumentDetailScreen>
    with TickerProviderStateMixin {
  AppStrings get _strings => AppStrings.of(context);

  // Tab điều khiển: Nội dung / Lịch sử phiên bản (giống màn chi tiết mẫu văn bản).
  late final TabController _tabController;

  // Chọn chuỗi hiển thị VI/EN (i18n).
  String _pick(String vi, String en) => _strings.pick(vi, en);

  bool _actionLoading = false;
  AssistantQuickSignPlanAction? _assistantPlanOverride;
  String? _dismissedAssistantPlanToken;
  bool _quickSignBusy = false;
  String? _quickSignBusyLabel;
  String? _contentHtml;
  String? _previewPdfUrl;
  String? _previewNotice;
  String? _previewLoadError;
  bool _contentLoading = false;
  int _iframeKey = 0;
  html.IFrameElement? _contentFrame;
  double _contentFrameHeight = 840;
  String? _currentPreviewRevision;
  String? _previewBlockedRevision;
  String? _documentSummary;
  String? _summaryError;
  String? _summaryRevisionToken;
  DateTime? _summaryUpdatedAt;
  String? _summaryTaskId;
  bool _summaryLoading = false;
  SummaryOptions? _lastSummaryOptions;
  final Set<String> _registeredViewKeys = <String>{};
  Timer? _previewAutoReloadTimer;
  Future<void> Function()? _previewAutoReloadAction;
  late final AnimationController _summaryPulseController;

  // Sau khi tác vụ Word-AI xong -> làm mới văn bản + xem trước.
  void _refreshAfterWordAiCompletion() {
    final currentRevision = _currentPreviewRevision;
    setState(() {
      _previewBlockedRevision = currentRevision;
      _summaryError = _documentSummary == null
          ? null
          : _pick(
              'Văn bản vừa thay đổi. Hãy ấn "Tóm tắt lại" để cập nhật bản tóm tắt mới nhất.',
              'The document has changed. Press "Refresh summary" to update the latest summary.',
            );
      _documentSummary = null;
      _summaryRevisionToken = null;
      _summaryUpdatedAt = null;
      _resetPreviewState();
    });
  }

  // Mở màn: nạp văn bản, bật auto-reload xem trước PDF, lắng nghe tác vụ tóm tắt/Word-AI.
  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 2, vsync: this);
    _summaryPulseController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1200),
    )..repeat(reverse: true);
  }

  @override
  // Khi đổi id (sang văn bản khác) -> nạp lại dữ liệu.
  void didUpdateWidget(covariant DocumentDetailScreen oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.id == widget.id) return;
    _assistantPlanOverride = null;
    _dismissedAssistantPlanToken = null;
    _quickSignBusy = false;
    _quickSignBusyLabel = null;
    _currentPreviewRevision = null;
    _previewBlockedRevision = null;
    _resetSummaryState();
    _resetPreviewState();
  }

  @override
  // Rời màn: dừng auto-reload, thu hồi URL blob PDF, dọn tài nguyên.
  void dispose() {
    _stopPreviewAutoReload();
    _tabController.dispose();
    _summaryPulseController.dispose();
    _resetPreviewState();
    super.dispose();
  }

  void _stopPreviewAutoReload() {
    _previewAutoReloadTimer?.cancel();
    _previewAutoReloadTimer = null;
    _previewAutoReloadAction = null;
  }

  // Khởi động lại vòng tự tải lại PDF xem trước.
  void _restartPreviewAutoReload(Future<void> Function() action) {
    _stopPreviewAutoReload();
    _previewAutoReloadAction = action;
    _previewAutoReloadTimer = Timer.periodic(const Duration(seconds: 10), (_) {
      final callback = _previewAutoReloadAction;
      if (!mounted || callback == null || _contentLoading) return;
      if (_previewPdfUrl == null || _previewPdfUrl!.isEmpty) return;
      callback();
    });
  }

  // Bật/tắt tương tác khung xem trước (chặn khi đang xử lý).
  void _setPreviewInteractivity(bool enabled) {
    final frame = _contentFrame;
    if (frame == null) return;
    frame.style.pointerEvents = enabled ? 'auto' : 'none';
  }

  // Thu hồi URL blob của PDF xem trước (giải phóng bộ nhớ).
  void _revokePreviewPdfUrl() {
    final current = _previewPdfUrl;
    if (current == null || current.isEmpty) return;
    html.Url.revokeObjectUrl(current);
    _previewPdfUrl = null;
  }

  // Reset trạng thái xem trước (thu hồi URL PDF, xóa cache HTML) khi đổi/tải lại văn bản.

  void _resetPreviewState() {
    _stopPreviewAutoReload();
    _revokePreviewPdfUrl();
    _contentFrame = null;
    _contentHtml = null;
    _previewNotice = null;
    _previewLoadError = null;
    _contentLoading = false;
    _contentFrameHeight = 840;
    _iframeKey += 1;
  }

  void _resetSummaryState() {
    _documentSummary = null;
    _summaryError = null;
    _summaryRevisionToken = null;
    _summaryUpdatedAt = null;
    _summaryTaskId = null;
    _summaryLoading = false;
  }

  // Đổi lỗi tải xem trước thành dòng thông báo nhẹ trên UI.
  String _previewNoticeFromError(Object error) {
    if (error is DioException) {
      final data = error.response?.data;
      if (data is Map && data['detail'] != null) {
        return '${data['detail']} ${_pick('Đang chuyển sang chế độ HTML.', 'Switching to HTML mode.')}';
      }
      return _pick(
        'Không tạo được bản xem PDF. Đang chuyển sang chế độ HTML.',
        'Unable to generate the PDF preview. Switching to HTML mode.',
      );
    }
    return _pick(
      'Không tạo được bản xem PDF. Đang chuyển sang chế độ HTML.',
      'Unable to generate the PDF preview. Switching to HTML mode.',
    );
  }

  // Thông điệp lỗi khi tải PDF xem trước thất bại.
  String _previewLoadErrorMessage(Object error) {
    if (error is DioException) {
      final data = error.response?.data;
      if (data is Map && data['detail'] != null) return '${data['detail']}';
      return _pick(
        'Không tải được nội dung văn bản (${error.response?.statusCode ?? 'network'}).',
        'Unable to load the document content (${error.response?.statusCode ?? 'network'}).',
      );
    }
    return _pick(
      'Không tải được nội dung văn bản: $error',
      'Unable to load the document content: $error',
    );
  }

  // Sinh token theo phiên bản tài liệu để ép tải lại đúng bản xem trước mới.
  String _previewRevisionToken(doc) {
    final updatedAt = doc.updatedAt?.toString() ?? '';
    final versionNumber = doc.versionNumber?.toString() ?? '';
    return '$versionNumber:$updatedAt';
  }

  // Tham số query cho request xem trước PDF (revision...).
  Map<String, dynamic> _previewQuery(doc) {
    return <String, dynamic>{
      'rev': _previewRevisionToken(doc),
      'ts': DateTime.now().millisecondsSinceEpoch.toString(),
    };
  }

  // Định dạng thời điểm cập nhật bản tóm tắt để hiển thị.
  String _formatSummaryUpdatedAt(DateTime value) {
    String twoDigits(int number) => number.toString().padLeft(2, '0');
    return '${twoDigits(value.hour)}:${twoDigits(value.minute)}:${twoDigits(value.second)}';
  }

  // Nút Tóm tắt: khởi chạy tác vụ AI tóm tắt văn bản.
  Future<void> _summarizeDocument(doc) async {
    if (_summaryLoading) return;
    final options = await SummaryOptionsDialog.show(
      context,
      documentId: widget.id,
      initial: _lastSummaryOptions,
    );
    if (options == null) return;
    setState(() {
      _summaryLoading = true;
      _summaryError = null;
      _summaryTaskId = null;
      _lastSummaryOptions = options;
    });

    try {
      final response = await ApiClient().dio.post(
        'documents/${widget.id}/summarize-async/',
        data: {
          'options': options.toJson(),
          if (options.userExtraRules.isNotEmpty)
            'user_extra_rules': options.userExtraRules,
          if (options.userExtraRules.isNotEmpty &&
              options.promptCheckToken != null)
            'prompt_check_token': options.promptCheckToken,
        },
      );
      final data = (response.data as Map).cast<String, dynamic>();
      final taskId = '${data['task_id'] ?? ''}'.trim();
      if (taskId.isEmpty) {
        throw Exception('Server khong tra ve task_id hop le.');
      }
      if (!mounted) return;
      setState(() {
        _summaryTaskId = taskId;
      });
    } on DioException catch (error) {
      final payload = error.response?.data;
      final detail = payload is Map && payload['detail'] != null
          ? '${payload['detail']}'
          : _pick(
              'Không thể tóm tắt văn bản lúc này. Vui lòng thử lại sau.',
              'Unable to summarize the document right now. Please try again later.',
            );
      if (!mounted) return;
      setState(() {
        _summaryLoading = false;
        _summaryTaskId = null;
        _summaryError = detail;
      });
    } catch (_) {
      if (!mounted) return;
      setState(() {
        _summaryLoading = false;
        _summaryTaskId = null;
        _summaryError = _pick(
          'Không thể tóm tắt văn bản lúc này. Vui lòng thử lại sau.',
          'Unable to summarize the document right now. Please try again later.',
        );
      });
    }
  }

  // Khi tác vụ tóm tắt xong -> đổ kết quả tóm tắt vào UI.
  void _handleSummaryTaskComplete(doc, AITaskState state) {
    final result = state.result ?? const <String, dynamic>{};
    if (!mounted) return;
    setState(() {
      _documentSummary = (result['summary'] as String? ?? '').trim();
      _summaryRevisionToken =
          result['summary_revision'] as String? ?? _previewRevisionToken(doc);
      _summaryUpdatedAt = DateTime.now();
      _summaryLoading = false;
      _summaryTaskId = null;
      _summaryError = null;
    });
  }

  // Khi tóm tắt bị hủy -> phục hồi trạng thái UI.
  void _handleSummaryTaskCancelled() {
    if (!mounted) return;
    setState(() {
      _summaryLoading = false;
      _summaryTaskId = null;
      _summaryError = null;
    });
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(_pick('Da dung tom tat van ban.', 'Summary cancelled.')),
        backgroundColor: Colors.orange,
      ),
    );
  }

  // Khi tóm tắt lỗi -> báo lỗi trên UI.
  void _handleSummaryTaskFailed(String message) {
    if (!mounted) return;
    setState(() {
      _summaryLoading = false;
      _summaryTaskId = null;
      _summaryError = message;
    });
  }

  // Nạp nội dung xem trước (HTML reader) của văn bản.
  Future<void> _loadContentPreview(doc, {bool force = false}) async {
    if (_contentLoading) return;
    if (!force && (_previewPdfUrl != null || _contentHtml != null)) return;
    // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

    setState(() => _contentLoading = true);

    try {
      String? nextPdfUrl;
      String? nextHtml;
      String? nextNotice;
      String? nextError;

      final hasFile = doc.hasFile as bool;
      final hasContent =
          doc.content != null && (doc.content as String).isNotEmpty;
      final previewRevision = _previewRevisionToken(doc);
      _currentPreviewRevision = previewRevision;
      _previewBlockedRevision = null;

      if (hasFile) {
        try {
          // Gọi API hoặc tác vụ bất đồng bộ rồi chờ kết quả trước khi cập nhật giao diện.

          final pdfResp = await ApiClient().dio.get(
                'documents/${widget.id}/preview-pdf/',
                queryParameters: _previewQuery(doc),
                options: Options(responseType: ResponseType.bytes),
              );
          final bytes = pdfResp.data as List<int>;
          final blob = html.Blob([bytes], 'application/pdf');
          nextPdfUrl = html.Url.createObjectUrlFromBlob(blob);
        } catch (error) {
          nextNotice = _previewNoticeFromError(error);
        }
      }

      if (nextPdfUrl == null && (hasFile || hasContent)) {
        // Gọi API hoặc tác vụ bất đồng bộ rồi chờ kết quả trước khi cập nhật giao diện.

        final htmlResp = await ApiClient().dio.get(
              'documents/${widget.id}/content-html/',
              queryParameters: _previewQuery(doc),
            );
        nextHtml = htmlResp.data['html'] as String? ?? '';
      }

      if (!mounted) {
        if (nextPdfUrl != null) html.Url.revokeObjectUrl(nextPdfUrl);
        return;
      }

      _revokePreviewPdfUrl();
      // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

      setState(() {
        _previewPdfUrl = nextPdfUrl;
        _contentHtml = nextHtml;
        _previewNotice = nextNotice;
        _previewLoadError = nextError;
        _contentLoading = false;
        _contentFrameHeight = 840;
        _iframeKey += 1;
      });
      if (nextPdfUrl != null && nextPdfUrl.isNotEmpty) {
        _restartPreviewAutoReload(() => _loadContentPreview(doc, force: true));
      } else {
        _stopPreviewAutoReload();
      }
    } catch (error) {
      if (!mounted) return;
      _stopPreviewAutoReload();
      // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

      setState(() {
        _contentLoading = false;
        _previewLoadError = _previewLoadErrorMessage(error);
      });
    }
  }

  // Dựng HTML hiển thị nội dung văn bản trong khung đọc.
  String _readerHtml(String rawHtml, {required bool isCompact}) {
    final readerCss = '''
<style>
html, body {
  margin: 0;
  padding: 0;
  background: #f8fafc;
}
body {
  padding: ${isCompact ? 12 : 24}px;
  color: #0f172a;
  font-family: "Segoe UI", Arial, sans-serif;
  line-height: 1.6;
}
table {
  width: 100% !important;
  max-width: 100% !important;
  display: block;
  overflow-x: auto;
  border-collapse: collapse;
}
img {
  max-width: 100% !important;
  height: auto !important;
}
p, li, span, div {
  word-break: break-word;
}
</style>
''';
    final viewport =
        '<meta name="viewport" content="width=device-width, initial-scale=1">';
    if (rawHtml.contains('</head>')) {
      return rawHtml.replaceFirst('</head>', '$viewport$readerCss</head>');
    }
    return '<html><head>$viewport$readerCss</head><body>$rawHtml</body></html>';
  }

  // Dựng khung hiển thị nội dung HTML của văn bản (khung đọc).

  Widget _buildContentFrame({
    required String htmlContent,
    required bool isCompact,
    required bool fullScreen,
  }) {
    final viewKey =
        'doc-content-${widget.id}-${isCompact ? 'compact' : 'full'}-$fullScreen-$_iframeKey';
    if (_registeredViewKeys.add(viewKey)) {
      ui.platformViewRegistry.registerViewFactory(viewKey, (int viewId) {
        final frame = html.IFrameElement()
          ..style.border = 'none'
          ..style.width = '100%'
          ..style.height = '100%'
          ..style.pointerEvents = 'auto'
          ..srcdoc = _readerHtml(htmlContent, isCompact: isCompact);
        frame.onLoad.listen((_) {
          if (!mounted || fullScreen) return;
          try {
            final contentWindow = frame.contentWindow;
            if (contentWindow is html.Window) {
              final doc = contentWindow.document as html.HtmlDocument?;
              final body = doc?.body;
              final nextHeight =
                  (body?.scrollHeight ?? body?.clientHeight ?? 0).toDouble();
              if (nextHeight > 0) {
                // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

                setState(() {
                  _contentFrameHeight =
                      nextHeight.clamp(isCompact ? 420 : 720, 3200);
                });
              }
            }
          } catch (_) {}
        });
        _contentFrame = frame;
        return frame;
      });
    }
    return _withIframeBlocker(HtmlElementView(viewType: viewKey));
  }

  Widget _withIframeBlocker(Widget iframe) {
    return ValueListenableBuilder<int>(
      valueListenable: iframeBlockerCount,
      builder: (_, count, __) {
        if (count > 0) {
          return Container(
            height: 240,
            alignment: Alignment.center,
            decoration: BoxDecoration(
              color: Colors.grey.shade100,
              borderRadius: BorderRadius.circular(8),
              border: Border.all(color: Colors.grey.shade300),
            ),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: const [
                Icon(Icons.visibility_off_outlined,
                    size: 36, color: Colors.blueGrey),
                SizedBox(height: 8),
                Text(
                  'Đang chọn đồng nghiệp...\nXem trước tạm ẩn để hộp thoại hiển thị đầy đủ.',
                  textAlign: TextAlign.center,
                  style: TextStyle(fontSize: 12, color: Colors.blueGrey),
                ),
              ],
            ),
          );
        }
        return iframe;
      },
    );
  }

  // Dựng khung iframe xem trước PDF của văn bản (auto-reload).

  Widget _buildPdfFrame({
    required String pdfUrl,
    required bool fullScreen,
  }) {
    final viewKey = 'doc-pdf-${widget.id}-$fullScreen-$_iframeKey';
    if (_registeredViewKeys.add(viewKey)) {
      ui.platformViewRegistry.registerViewFactory(viewKey, (int viewId) {
        final frame = html.IFrameElement()
          ..style.border = 'none'
          ..style.width = '100%'
          ..style.height = '100%'
          ..style.pointerEvents = 'auto'
          ..src = '$pdfUrl#toolbar=0&navpanes=0&view=FitH';
        _contentFrame = frame;
        return frame;
      });
    }
    return _withIframeBlocker(HtmlElementView(viewType: viewKey));
  }

  // Mở dialog xem trước nội dung văn bản phóng to.

  Future<void> _openContentPreviewDialog(doc) async {
    await _loadContentPreview(doc, force: true);
    if ((_previewPdfUrl == null || _previewPdfUrl!.isEmpty) &&
        (_contentHtml == null || _contentHtml!.isEmpty)) {
      return;
    }
    final isCompact = MediaQuery.of(context).size.width < 900;
    _iframeKey += 1;
    if (!mounted) return;
    await showDialog<void>(
      context: context,
      builder: (ctx) => Dialog(
        insetPadding: EdgeInsets.all(isCompact ? 10 : 24),
        child: SizedBox(
          width: double.infinity,
          height: MediaQuery.of(ctx).size.height * 0.92,
          child: Column(
            children: [
              Padding(
                padding: const EdgeInsets.fromLTRB(16, 14, 12, 10),
                child: Row(
                  children: [
                    const Expanded(
                      child: Text(
                        'Xem toàn màn hình',
                        style: TextStyle(
                            fontSize: 18, fontWeight: FontWeight.w700),
                      ),
                    ),
                    IconButton(
                      onPressed: () => Navigator.pop(ctx),
                      icon: const Icon(Icons.close),
                    ),
                  ],
                ),
              ),
              const Divider(height: 1),
              Expanded(
                child: Padding(
                  padding: const EdgeInsets.all(8),
                  child: _previewPdfUrl != null && _previewPdfUrl!.isNotEmpty
                      ? _buildPdfFrame(
                          pdfUrl: _previewPdfUrl!,
                          fullScreen: true,
                        )
                      : _buildContentFrame(
                          htmlContent: _contentHtml!,
                          isCompact: false,
                          fullScreen: true,
                        ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  List<SigningCandidate> _filterSigningCandidates(
    List<SigningCandidate> candidates,
    String query,
  ) {
    final normalized = query.trim().toLowerCase();
    if (normalized.isEmpty) {
      return candidates.take(12).toList();
    }
    return candidates
        .where((candidate) {
          final haystack = [
            candidate.fullName,
            candidate.username,
            candidate.title,
            candidate.label,
          ].join(' ').toLowerCase();
          return haystack.contains(normalized);
        })
        .take(12)
        .toList();
  }

  // Dòng phụ mô tả 1 ứng viên người ký (email/chức danh) trong danh sách chọn.

  String _candidateSubtitle(SigningCandidate candidate) {
    final parts = <String>[
      if (candidate.username.trim().isNotEmpty) '@${candidate.username.trim()}',
      if (candidate.title.trim().isNotEmpty) candidate.title.trim(),
    ];
    return parts.join(' • ');
  }

  // Nhãn hiển thị khi đã chọn 1 ứng viên người ký.

  String _candidateSelectionLabel(SigningCandidate candidate) {
    final base = candidate.fullName.trim().isEmpty
        ? candidate.username.trim()
        : candidate.fullName.trim();
    if (candidate.username.trim().isEmpty) {
      return base;
    }
    return '$base (@${candidate.username.trim()})';
  }

  // Dialog cảnh báo: quy trình ký đã bắt đầu với những người ký nào (không sửa được nữa).

  Future<void> _showStartedSignersDialog(SigningProposal proposal) async {
    if (!mounted) return;
    await showDialog<void>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text(_pick('Đã khởi tạo quy trình ký', 'Signing flow started')),
        content: SizedBox(
          width: 520,
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                _pick(
                  'Quy trình ký đã được kích hoạt ngay với ${proposal.signers.length} người ký.',
                  'The signing flow has started with ${proposal.signers.length} signers.',
                ),
                style: const TextStyle(height: 1.45),
              ),
              const SizedBox(height: 12),
              ...proposal.signers.map((signer) {
                final username = signer.signerUsername.trim();
                final title = username.isEmpty
                    ? signer.signerName
                    : '${signer.signerName} (@$username)';
                return Padding(
                  padding: const EdgeInsets.only(bottom: 8),
                  child: Text(
                    '${_pick('Bước', 'Step')} ${signer.stepNo}: $title • ${signer.displayRole}',
                    style: const TextStyle(height: 1.4),
                  ),
                );
              }),
            ],
          ),
        ),
        actions: [
          FilledButton(
            onPressed: () => Navigator.pop(ctx),
            child: Text(_pick('Đóng', 'Close')),
          ),
        ],
      ),
    );
  }

  // Khởi tạo quy trình ký: tạo đề xuất/nhiệm vụ ký với danh sách người ký đã chọn.

  Future<SigningProposal> _startSigningFlow({
    required List<Map<String, dynamic>> signers,
    String note = '',
  }) async {
    // Gọi API hoặc tác vụ bất đồng bộ rồi chờ kết quả trước khi cập nhật giao diện.

    final resp = await ApiClient().dio.post(
      'documents/${widget.id}/signing/start/',
      data: {
        'proposal_note': note,
        'signers': signers,
      },
    );
    return SigningProposal.fromJson(
        Map<String, dynamic>.from(resp.data as Map));
  }

  // Bắt đầu ký cho chính người dùng hiện tại (luồng tự ký).

  Future<void> _startSigningForCurrentUser() async {
    // Đọc provider theo nhu cầu hành động mà không buộc widget đăng ký rebuild liên tục.

    final currentUser = ref.read(currentUserProvider);
    if (currentUser == null) {
      _showSnack(
        _pick(
          'Không xác định được tài khoản hiện tại.',
          'Unable to determine the current account.',
        ),
        error: true,
      );
      return;
    }
    // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

    setState(() => _actionLoading = true);
    try {
      final proposal = await _startSigningFlow(
        signers: [
          {
            'user_id': currentUser.id,
            'display_role': 'Nguoi ky truc tiep',
            'step_no': 1,
            'required': true,
            'group_context': 'self_sign',
          },
        ],
        note: 'Khoi tao ky truc tiep tu chi tiet van ban.',
      );
      if (!mounted) return;
      _showSnack('Da tao tac vu ky cho ban.');
      if (proposal.currentUserTaskId != null) {
        // Điều hướng người dùng sang màn phù hợp theo kết quả thao tác hiện tại.

        context.go('/signing/tasks/${proposal.currentUserTaskId}');
      } else {
        await _showStartedSignersDialog(proposal);
      }
    } catch (error) {
      if (mounted) _showSnack('Loi khoi tao tac vu ky: $error', error: true);
    } finally {
      // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

      if (mounted) setState(() => _actionLoading = false);
    }
  }

  // Mở hộp thoại tìm & chọn 1 người ký (gọi 'signing/candidates/').

  Future<SigningCandidate?> _pickSigningCandidate(
    List<SigningCandidate> candidates, {
    String initialQuery = '',
  }) async {
    final searchCtrl = TextEditingController(text: initialQuery);
    return showDialog<SigningCandidate>(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, setS) {
          final matches = _filterSigningCandidates(candidates, searchCtrl.text);
          return AlertDialog(
            title: Text(_pick('Tìm người ký', 'Find signer')),
            content: SizedBox(
              width: 560,
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  TextField(
                    controller: searchCtrl,
                    autofocus: true,
                    decoration: InputDecoration(
                      labelText: _pick(
                        'Nhập tên, tài khoản hoặc chức danh',
                        'Enter name, username, or title',
                      ),
                      hintText: _pick(
                        'Ví dụ: Nguyễn Văn A, admin, trưởng phòng...',
                        'Example: John Smith, admin, team lead...',
                      ),
                      prefixIcon: Icon(Icons.search),
                      border: OutlineInputBorder(),
                    ),
                    onChanged: (_) => setS(() {}),
                  ),
                  const SizedBox(height: 12),
                  Flexible(
                    child: matches.isEmpty
                        ? Center(
                            child: Padding(
                              padding: const EdgeInsets.symmetric(vertical: 24),
                              child: Text(_pick('Không tìm thấy người phù hợp.',
                                  'No matching signer found.')),
                            ),
                          )
                        : ListView.separated(
                            shrinkWrap: true,
                            itemCount: matches.length,
                            separatorBuilder: (_, __) =>
                                const Divider(height: 1),
                            itemBuilder: (context, index) {
                              final candidate = matches[index];
                              final subtitle = _candidateSubtitle(candidate);
                              return ListTile(
                                contentPadding: EdgeInsets.zero,
                                leading: CircleAvatar(
                                  radius: 18,
                                  child: Text(
                                    (candidate.fullName.isNotEmpty
                                            ? candidate.fullName[0]
                                            : candidate.username.isNotEmpty
                                                ? candidate.username[0]
                                                : '?')
                                        .toUpperCase(),
                                  ),
                                ),
                                title: Text(candidate.fullName),
                                subtitle:
                                    subtitle.isEmpty ? null : Text(subtitle),
                                onTap: () => Navigator.pop(ctx, candidate),
                              );
                            },
                          ),
                  ),
                ],
              ),
            ),
            actions: [
              TextButton(
                onPressed: () => Navigator.pop(ctx),
                child: Text(_pick('Đóng', 'Close')),
              ),
            ],
          );
        },
      ),
    ).whenComplete(searchCtrl.dispose);
  }

  // Nút Khởi tạo ký: mở dialog chọn người ký rồi gửi đề xuất ký cho văn bản.

  Future<void> _showSigningProposalDialog(doc) async {
    List<SigningCandidate> candidates = const [];
    try {
      // Gọi API hoặc tác vụ bất đồng bộ rồi chờ kết quả trước khi cập nhật giao diện.

      final resp = await ApiClient().dio.get('signing/candidates/');
      candidates = (resp.data as List)
          .map((item) =>
              SigningCandidate.fromJson(Map<String, dynamic>.from(item as Map)))
          .toList();
    } catch (error) {
      if (mounted)
        _showSnack('Không tải được danh sách người ký: $error', error: true);
      return;
    }

    final noteCtrl = TextEditingController();
    final rows = <_SignerDraftRow>[_SignerDraftRow()];
    Map<String, dynamic>? payload;

    _setPreviewInteractivity(false);
    try {
      payload = await showDialog<Map<String, dynamic>>(
        context: context,
        builder: (ctx) => StatefulBuilder(
          builder: (ctx, setS) {
            return AlertDialog(
              title: Text(_pick('Khởi tạo quy trình ký', 'Start signing flow')),
              content: SizedBox(
                width: 620,
                child: SingleChildScrollView(
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        _pick(
                          'Văn bản sẽ được khóa phiên bản, chuyển sang PDF và kích hoạt quy trình ký ngay sau khi bạn chọn người ký.',
                          'The document will be version-locked, converted to PDF, and the signing flow will start as soon as you choose signers.',
                        ),
                        style:
                            TextStyle(height: 1.45, color: Color(0xFF475569)),
                      ),
                      const SizedBox(height: 12),
                      TextField(
                        controller: noteCtrl,
                        minLines: 2,
                        maxLines: 4,
                        decoration: InputDecoration(
                          labelText: _pick(
                              'Ghi chú cho quy trình ký', 'Signing flow note'),
                          border: OutlineInputBorder(),
                        ),
                      ),
                      const SizedBox(height: 16),
                      ...rows.asMap().entries.map((entry) {
                        final index = entry.key;
                        final row = entry.value;
                        return Container(
                          margin: const EdgeInsets.only(bottom: 12),
                          padding: const EdgeInsets.all(12),
                          decoration: BoxDecoration(
                            borderRadius: BorderRadius.circular(12),
                            border: Border.all(color: const Color(0xFFE2E8F0)),
                            color: const Color(0xFFF8FAFC),
                          ),
                          child: Column(
                            children: [
                              Row(
                                children: [
                                  Expanded(
                                    child: TextField(
                                      controller: row.signerCtrl,
                                      readOnly: true,
                                      decoration: InputDecoration(
                                        labelText: _pick(
                                          'Người ký ${index + 1}',
                                          'Signer ${index + 1}',
                                        ),
                                        hintText: _pick(
                                            'Bấm để nhập từ khóa và tìm người ký',
                                            'Tap to search and choose a signer'),
                                        border: const OutlineInputBorder(),
                                        prefixIcon: const Icon(Icons.search),
                                        suffixIcon: row.userId == null
                                            ? null
                                            : IconButton(
                                                tooltip: _pick('Xóa lựa chọn',
                                                    'Clear selection'),
                                                onPressed: () => setS(() {
                                                  row.userId = null;
                                                  row.signerCtrl.clear();
                                                }),
                                                icon: const Icon(Icons.close),
                                              ),
                                      ),
                                      onTap: () async {
                                        final selected =
                                            await _pickSigningCandidate(
                                          candidates,
                                          initialQuery: row.signerCtrl.text,
                                        );
                                        if (selected == null) return;
                                        setS(() {
                                          row.userId = selected.id;
                                          row.signerCtrl.text =
                                              _candidateSelectionLabel(
                                                  selected);
                                        });
                                      },
                                    ),
                                  ),
                                  const SizedBox(width: 8),
                                  if (rows.length > 1)
                                    IconButton(
                                      icon: const Icon(Icons.delete_outline),
                                      onPressed: () => setS(() {
                                        row.dispose();
                                        rows.removeAt(index);
                                      }),
                                    ),
                                ],
                              ),
                              const SizedBox(height: 10),
                              TextField(
                                controller: row.roleCtrl,
                                decoration: InputDecoration(
                                  labelText: _pick(
                                    'Vai trò hiển thị khi ký',
                                    'Displayed signing role',
                                  ),
                                  border: const OutlineInputBorder(),
                                ),
                              ),
                              const SizedBox(height: 10),
                              Row(
                                children: [
                                  Expanded(
                                    child: TextField(
                                      controller: row.stepCtrl,
                                      keyboardType: TextInputType.number,
                                      decoration: InputDecoration(
                                        labelText:
                                            _pick('Bước ký', 'Signing step'),
                                        border: const OutlineInputBorder(),
                                      ),
                                    ),
                                  ),
                                  const SizedBox(width: 12),
                                  Expanded(
                                    child: TextField(
                                      controller: row.groupCtrl,
                                      decoration: InputDecoration(
                                        labelText: _pick(
                                            'Ngữ cảnh nhóm', 'Group context'),
                                        border: const OutlineInputBorder(),
                                      ),
                                    ),
                                  ),
                                  const SizedBox(width: 12),
                                  Expanded(
                                    child: CheckboxListTile(
                                      value: row.required,
                                      onChanged: (value) => setS(
                                          () => row.required = value ?? true),
                                      title: Text(_pick('Bắt buộc', 'Required'),
                                          style: TextStyle(fontSize: 13)),
                                      contentPadding: EdgeInsets.zero,
                                      controlAffinity:
                                          ListTileControlAffinity.leading,
                                    ),
                                  ),
                                ],
                              ),
                            ],
                          ),
                        );
                      }),
                      Align(
                        alignment: Alignment.centerLeft,
                        child: OutlinedButton.icon(
                          onPressed: () =>
                              setS(() => rows.add(_SignerDraftRow())),
                          icon: const Icon(Icons.add, size: 18),
                          label: Text(_pick('Thêm người ký', 'Add signer')),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
              actions: [
                TextButton(
                    onPressed: () => Navigator.pop(ctx),
                    child: Text(_pick('Hủy', 'Cancel'))),
                FilledButton(
                  onPressed: () {
                    final signers = <Map<String, dynamic>>[];
                    for (final row in rows) {
                      final role = row.roleCtrl.text.trim();
                      final step = int.tryParse(row.stepCtrl.text.trim()) ?? 1;
                      if (row.userId == null || role.isEmpty) {
                        _showSnack(
                            'Mỗi người ký cần có tài khoản và vai trò hiển thị.',
                            error: true);
                        return;
                      }
                      signers.add({
                        'user_id': row.userId,
                        'display_role': role,
                        'step_no': step,
                        'required': row.required,
                        'group_context': row.groupCtrl.text.trim(),
                      });
                    }
                    Navigator.pop(ctx, {
                      'proposal_note': noteCtrl.text.trim(),
                      'signers': signers,
                    });
                  },
                  child: Text(_pick('Khởi tạo', 'Start')),
                ),
              ],
            );
          },
        ),
      );
    } finally {
      _setPreviewInteractivity(true);
      noteCtrl.dispose();
      for (final row in rows) {
        row.dispose();
      }
    }

    if (payload == null || !mounted) return;
    // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

    setState(() => _actionLoading = true);
    try {
      final proposal = await _startSigningFlow(
        signers: List<Map<String, dynamic>>.from(
            payload['signers'] as List<dynamic>),
        note: payload['proposal_note']?.toString() ?? '',
      );
      final submittedIds = (payload['signers'] as List<dynamic>)
          .map((item) => (item as Map<String, dynamic>)['user_id'] as int)
          .toSet();
      final savedIds =
          proposal.signers.map((item) => item.signerUserId).toSet();
      final hasMismatch = !setEquals(submittedIds, savedIds);
      if (mounted) {
        _showSnack(
          hasMismatch
              ? 'Quy trình ký đã được khởi tạo, nhưng danh sách người ký lưu trên server khác với lựa chọn ban đầu.'
              : 'Đã khởi tạo quy trình ký thành công.',
          error: hasMismatch,
        );
        await _showStartedSignersDialog(proposal);
      }
    } catch (error) {
      if (mounted) _showSnack('Lỗi khởi tạo quy trình ký: $error', error: true);
    } finally {
      // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

      if (mounted) setState(() => _actionLoading = false);
    }
  }

  // Nút Forward hòm thư: mở dialog chọn người nhận rồi chuyển tiếp văn bản qua hòm thư.

  Future<void> _showForwardDialog(doc) async {
    if (doc.canForwardNow != true) {
      _showSnack(
        'Văn bản này chưa được ký an toàn cho phiên bản hiện tại. Hãy ký số trước khi forward.',
        error: true,
      );
      return;
    }
    List<SigningCandidate> candidates = const [];
    try {
      // Gọi API hoặc tác vụ bất đồng bộ rồi chờ kết quả trước khi cập nhật giao diện.

      final resp = await ApiClient().dio.get('signing/candidates/');
      candidates = (resp.data as List)
          .map((item) =>
              SigningCandidate.fromJson(Map<String, dynamic>.from(item as Map)))
          .toList();
    } catch (error) {
      if (mounted)
        _showSnack('Không tải được danh sách người nhận: $error', error: true);
      return;
    }

    final noteCtrl = TextEditingController();
    final rows = <_ForwardRecipientRow>[_ForwardRecipientRow()];
    Map<String, dynamic>? payload;

    _setPreviewInteractivity(false);
    try {
      payload = await showDialog<Map<String, dynamic>>(
        context: context,
        builder: (ctx) => StatefulBuilder(
          builder: (ctx, setS) {
            return AlertDialog(
              title: Text(_pick('Forward văn bản', 'Forward document')),
              content: SizedBox(
                width: 620,
                child: SingleChildScrollView(
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        _pick(
                          'Văn bản cần có một PDF đã ký an toàn cho phiên bản hiện tại trước khi forward lần đầu. Người nhận sẽ thấy văn bản trong Hòm thư, có thể xem, ký, forward tiếp, hoàn thành hoặc từ chối.',
                          'The document must have a securely signed PDF for the current version before the first forward. Recipients will see it in the mailbox and can view, sign, forward, complete, or reject it.',
                        ),
                        style:
                            TextStyle(height: 1.45, color: Color(0xFF475569)),
                      ),
                      const SizedBox(height: 12),
                      TextField(
                        controller: noteCtrl,
                        minLines: 2,
                        maxLines: 4,
                        decoration: InputDecoration(
                          labelText: _pick('Ghi chú forward', 'Forward note'),
                          border: OutlineInputBorder(),
                        ),
                      ),
                      const SizedBox(height: 16),
                      ...rows.asMap().entries.map((entry) {
                        final index = entry.key;
                        final row = entry.value;
                        return Container(
                          margin: const EdgeInsets.only(bottom: 12),
                          padding: const EdgeInsets.all(12),
                          decoration: BoxDecoration(
                            borderRadius: BorderRadius.circular(12),
                            border: Border.all(color: const Color(0xFFE2E8F0)),
                            color: const Color(0xFFF8FAFC),
                          ),
                          child: Row(
                            children: [
                              Expanded(
                                child: TextField(
                                  controller: row.recipientCtrl,
                                  readOnly: true,
                                  decoration: InputDecoration(
                                    labelText: _pick(
                                      'Người nhận ${index + 1}',
                                      'Recipient ${index + 1}',
                                    ),
                                    hintText: _pick(
                                      'Bấm để chọn người nhận',
                                      'Tap to choose a recipient',
                                    ),
                                    border: const OutlineInputBorder(),
                                    prefixIcon: const Icon(Icons.search),
                                    suffixIcon: row.userId == null
                                        ? null
                                        : IconButton(
                                            tooltip: _pick('Xóa lựa chọn',
                                                'Clear selection'),
                                            onPressed: () => setS(() {
                                              row.userId = null;
                                              row.recipientCtrl.clear();
                                            }),
                                            icon: const Icon(Icons.close),
                                          ),
                                  ),
                                  onTap: () async {
                                    final selected =
                                        await _pickSigningCandidate(
                                      candidates,
                                      initialQuery: row.recipientCtrl.text,
                                    );
                                    if (selected == null) return;
                                    setS(() {
                                      row.userId = selected.id;
                                      row.recipientCtrl.text =
                                          _candidateSelectionLabel(selected);
                                    });
                                  },
                                ),
                              ),
                              const SizedBox(width: 8),
                              if (rows.length > 1)
                                IconButton(
                                  icon: const Icon(Icons.delete_outline),
                                  onPressed: () => setS(() {
                                    row.dispose();
                                    rows.removeAt(index);
                                  }),
                                ),
                            ],
                          ),
                        );
                      }),
                      Align(
                        alignment: Alignment.centerLeft,
                        child: OutlinedButton.icon(
                          onPressed: () =>
                              setS(() => rows.add(_ForwardRecipientRow())),
                          icon: const Icon(Icons.add, size: 18),
                          label:
                              Text(_pick('Thêm người nhận', 'Add recipient')),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
              actions: [
                TextButton(
                    onPressed: () => Navigator.pop(ctx),
                    child: Text(_pick('Hủy', 'Cancel'))),
                FilledButton(
                  onPressed: () {
                    final userIds = <int>[];
                    for (final row in rows) {
                      if (row.userId == null) {
                        _showSnack('Moi dong forward can co nguoi nhan.',
                            error: true);
                        return;
                      }
                      userIds.add(row.userId!);
                    }
                    Navigator.pop(ctx, {
                      'user_ids': userIds,
                      'note': noteCtrl.text.trim(),
                    });
                  },
                  child: Text(_pick('Forward ngay', 'Forward now')),
                ),
              ],
            );
          },
        ),
      );
    } finally {
      _setPreviewInteractivity(true);
      noteCtrl.dispose();
      for (final row in rows) {
        row.dispose();
      }
    }

    if (payload == null || !mounted) return;
    // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

    setState(() => _actionLoading = true);
    try {
      // Gọi API hoặc tác vụ bất đồng bộ rồi chờ kết quả trước khi cập nhật giao diện.

      await ApiClient()
          .dio
          .post('documents/${widget.id}/forward/', data: payload);
      ref.invalidate(signingSummaryProvider);
      if (mounted) {
        _showSnack('Đã forward văn bản vào Hòm thư.');
      }
    } catch (error) {
      if (mounted) _showSnack('Loi forward van ban: $error', error: true);
    } finally {
      // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

      if (mounted) setState(() => _actionLoading = false);
    }
  }

  // Nút Chia sẻ: mở hộp thoại cấp/quản lý quyền chia sẻ văn bản.
  Future<void> _showShareDialog(doc) async {
    // Phase 3 (sharing roadmap): mo UnifiedShareSheet thay vi dialog visibility cu.
    if (!mounted) return;
    _setPreviewInteractivity(false);
    try {
      await UnifiedShareSheet.showDialogPresentation(
        context,
        entityType: 'documents',
        entityId: widget.id,
        entityTitle: (doc.title ?? '').toString().isNotEmpty
            ? doc.title as String
            : 'Van ban #${widget.id}',
      );
      _refreshDocumentQueries();
    } finally {
      _setPreviewInteractivity(true);
    }
    return;
    // === Doan code legacy duoi day duoc giu lai tam thoi de tham khao ===
    // ignore_for_file: dead_code
    final user = ref.read(currentUserProvider);
    String selectedVisibility = doc.visibility as String;
    int? selectedGroupId = doc.groupId as int?;

    // Dùng nhóm của chính user (không cần admin API)
    final userGroups = user?.groups ?? [];

    if (!mounted) return;

    Map<String, dynamic>? result;
    _setPreviewInteractivity(false);
    try {
      result = await showDialog<Map<String, dynamic>>(
        context: context,
        builder: (ctx) => StatefulBuilder(
          builder: (ctx, setS) {
            // Xác định trạng thái approval của lựa chọn hiện tại
            final needsLeaderApproval =
                selectedVisibility == 'group' && selectedGroupId != null;
            final needsAdminApproval = selectedVisibility == 'public';

            return AlertDialog(
              title: Row(
                children: [
                  const Icon(Icons.share_outlined,
                      size: 20, color: Colors.blue),
                  const SizedBox(width: 8),
                  Text(_pick('Cài đặt quyền xem', 'View permissions')),
                ],
              ),
              content: SizedBox(
                width: 400,
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Ai có thể xem văn bản này?',
                      style:
                          TextStyle(fontSize: 13, color: Colors.grey.shade700),
                    ),
                    const SizedBox(height: 12),

                    // Option 1: Riêng tư
                    _ShareOption(
                      icon: Icons.lock_outline,
                      iconColor: Colors.grey.shade600,
                      title: 'Chỉ mình tôi',
                      subtitle:
                          'Văn bản chỉ hiển thị trong mục "Văn bản của tôi"',
                      selected: selectedVisibility == 'private',
                      onTap: () => setS(() {
                        selectedVisibility = 'private';
                        selectedGroupId = null;
                      }),
                    ),
                    const SizedBox(height: 8),

                    // Option 2: Nhóm
                    _ShareOption(
                      icon: Icons.group_outlined,
                      iconColor: Colors.blue,
                      title: 'Chia sẻ với nhóm của tôi',
                      subtitle: 'Mọi người trong cùng nhóm có thể xem. '
                          'Hiển thị ở mục "Đã chia sẻ trong nhóm".',
                      selected: selectedVisibility == 'group',
                      onTap: () => setS(() {
                        selectedVisibility = 'group';
                        // Auto-chọn nhóm đầu tiên nếu chưa chọn
                        if (selectedGroupId == null && userGroups.isNotEmpty) {
                          selectedGroupId = userGroups.first.id;
                        }
                      }),
                    ),
                    if (selectedVisibility == 'group') ...[
                      const SizedBox(height: 8),
                      Padding(
                        padding: const EdgeInsets.only(left: 16),
                        child: userGroups.isEmpty
                            ? Container(
                                padding: const EdgeInsets.all(10),
                                decoration: BoxDecoration(
                                  color: Colors.red.shade50,
                                  borderRadius: BorderRadius.circular(6),
                                  border:
                                      Border.all(color: Colors.red.shade200),
                                ),
                                child: Row(children: [
                                  Icon(Icons.warning_amber,
                                      size: 14, color: Colors.red.shade700),
                                  const SizedBox(width: 6),
                                  const Expanded(
                                      child: Text(
                                    'Bạn chưa thuộc nhóm nào. Vui lòng liên hệ Admin.',
                                    style: TextStyle(fontSize: 12),
                                  )),
                                ]),
                              )
                            : DropdownButtonFormField<int>(
                                value: selectedGroupId,
                                decoration: InputDecoration(
                                  labelText: _pick('Chọn nhóm', 'Choose group'),
                                  border: const OutlineInputBorder(),
                                  contentPadding: const EdgeInsets.symmetric(
                                      horizontal: 10, vertical: 8),
                                  isDense: true,
                                ),
                                items: userGroups
                                    .map((g) => DropdownMenuItem<int>(
                                          value: g.id,
                                          child: Text(g.name,
                                              style: const TextStyle(
                                                  fontSize: 13)),
                                        ))
                                    .toList(),
                                onChanged: (val) =>
                                    setS(() => selectedGroupId = val),
                              ),
                      ),
                      if (needsLeaderApproval) ...[
                        const SizedBox(height: 8),
                        Padding(
                          padding: const EdgeInsets.only(left: 16),
                          child: _ApprovalNote(
                            icon: Icons.supervisor_account_outlined,
                            color: Colors.amber.shade700,
                            bgColor: Colors.amber.shade50,
                            borderColor: Colors.amber.shade300,
                            text:
                                'Yêu cầu sẽ gửi đến trưởng nhóm để phê duyệt. '
                                'Văn bản chỉ hiển thị sau khi được duyệt.',
                          ),
                        ),
                      ],
                    ],
                    const SizedBox(height: 8),

                    // Option 3: Công khai
                    _ShareOption(
                      icon: Icons.public_outlined,
                      iconColor: Colors.teal,
                      title: 'Chia sẻ với tất cả mọi người',
                      subtitle: 'Toàn bộ người dùng hệ thống có thể xem. '
                          'Hiển thị ở mục "Đã chia sẻ công khai". Cần được Admin phê duyệt.',
                      selected: selectedVisibility == 'public',
                      onTap: () => setS(() {
                        selectedVisibility = 'public';
                        selectedGroupId = null;
                      }),
                    ),
                    if (needsAdminApproval) ...[
                      const SizedBox(height: 8),
                      _ApprovalNote(
                        icon: Icons.admin_panel_settings_outlined,
                        color: Colors.orange.shade700,
                        bgColor: Colors.orange.shade50,
                        borderColor: Colors.orange.shade300,
                        text: 'Yêu cầu sẽ gửi đến Quản trị viên để phê duyệt. '
                            'Văn bản chỉ hiển thị công khai sau khi Admin đồng ý.',
                      ),
                    ],
                  ],
                ),
              ),
              actions: [
                TextButton(
                    onPressed: () => Navigator.pop(ctx),
                    child: Text(_pick('Hủy', 'Cancel'))),
                FilledButton(
                  onPressed: (selectedVisibility == 'group' &&
                          (selectedGroupId == null || userGroups.isEmpty))
                      ? null
                      : () => Navigator.pop(ctx, {
                            'visibility': selectedVisibility,
                            'group_id': selectedGroupId,
                          }),
                  child: Text(selectedVisibility == 'private'
                      ? 'Xác nhận'
                      : 'Gửi yêu cầu'),
                ),
              ],
            );
          },
        ),
      );
    } finally {
      _setPreviewInteractivity(true);
    }

    if (result == null || !mounted) return;
    // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

    setState(() => _actionLoading = true);
    try {
      // Gọi API hoặc tác vụ bất đồng bộ rồi chờ kết quả trước khi cập nhật giao diện.

      await ApiClient().dio.post('documents/${widget.id}/share/', data: result);
      _refreshDocumentQueries();
      if (mounted) {
        final vis = result['visibility'];
        final msg = vis == 'private'
            ? 'Đã đặt về riêng tư.'
            : vis == 'group'
                ? 'Đã gửi yêu cầu chia sẻ đến trưởng nhóm.'
                : 'Đã gửi yêu cầu chia sẻ đến Admin.';
        _showSnack(msg);
      }
    } catch (e) {
      if (mounted) _showSnack('Lỗi: $e', error: true);
    } finally {
      // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

      if (mounted) setState(() => _actionLoading = false);
    }
  }

  // Tải file DOCX của văn bản về máy.
  Future<void> _downloadDocx({String title = 'VanBan'}) async {
    try {
      // Gọi API hoặc tác vụ bất đồng bộ rồi chờ kết quả trước khi cập nhật giao diện.

      final resp = await ApiClient().dio.get(
            'documents/${widget.id}/download/',
            options: Options(responseType: ResponseType.bytes),
          );
      final bytes = resp.data as List<int>;
      final blob = html.Blob(
        [bytes],
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
      );
      final url = html.Url.createObjectUrlFromBlob(blob);
      html.AnchorElement(href: url)
        ..setAttribute('download', '$title.docx')
        ..click();
      html.Url.revokeObjectUrl(url);
    } catch (e) {
      if (mounted) _showSnack('Lỗi tải file: $e', error: true);
    }
  }

  // Tải file PDF của văn bản về máy.
  Future<void> _downloadPdf(
      {String title = 'VanBan', int? versionNumber}) async {
    final url = versionNumber != null
        ? 'documents/${widget.id}/versions/$versionNumber/download-pdf/'
        : 'documents/${widget.id}/download-pdf/';
    if (mounted) {
      _showSnack(_pick('Đang tạo PDF...', 'Generating PDF...'));
    }
    try {
      final resp = await ApiClient().dio.get(
            url,
            options: Options(responseType: ResponseType.bytes),
          );
      final bytes = resp.data as List<int>;
      final blob = html.Blob([bytes], 'application/pdf');
      final href = html.Url.createObjectUrlFromBlob(blob);
      final filename =
          versionNumber != null ? '${title}_v$versionNumber.pdf' : '$title.pdf';
      html.AnchorElement(href: href)
        ..setAttribute('download', filename)
        ..click();
      html.Url.revokeObjectUrl(href);
    } on DioException catch (e) {
      String msg = 'Không tạo được PDF';
      final data = e.response?.data;
      if (data is Map && data['detail'] != null) {
        msg = data['detail'].toString();
      }
      if (mounted) {
        _showSnack(
          '$msg. ${_pick('Bạn có thể tải Word và xuất PDF thủ công.', 'You can download Word and export PDF manually.')}',
          error: true,
        );
      }
    } catch (e) {
      if (mounted) _showSnack('Lỗi tải PDF: $e', error: true);
    }
  }

  // Nút Hoàn tất: chốt văn bản (chuyển trạng thái cuối, khóa sửa).
  Future<void> _finalize() async {
    // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

    setState(() => _actionLoading = true);
    try {
      // Gọi API hoặc tác vụ bất đồng bộ rồi chờ kết quả trước khi cập nhật giao diện.

      await ApiClient().dio.post('documents/${widget.id}/finalize/');
      _refreshDocumentQueries();
      if (mounted) _showSnack('Đã chuyển sang trạng thái Chính thức.');
    } catch (e) {
      if (mounted) _showSnack('Lỗi: $e', error: true);
    } finally {
      // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

      if (mounted) setState(() => _actionLoading = false);
    }
  }

  // Nút Lưu trữ: đưa văn bản vào kho lưu trữ.
  Future<void> _archive() async {
    // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

    setState(() => _actionLoading = true);
    try {
      // Gọi API hoặc tác vụ bất đồng bộ rồi chờ kết quả trước khi cập nhật giao diện.

      await ApiClient().dio.post('documents/${widget.id}/archive/');
      _refreshDocumentQueries();
      if (mounted) _showSnack('Đã lưu trữ văn bản.');
    } catch (e) {
      if (mounted) _showSnack('Lỗi: $e', error: true);
    } finally {
      // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

      if (mounted) setState(() => _actionLoading = false);
    }
  }

  // Nút Bỏ lưu trữ: đưa văn bản trở lại danh sách thường.
  Future<void> _unarchive() async {
    // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

    setState(() => _actionLoading = true);
    try {
      // Gọi API hoặc tác vụ bất đồng bộ rồi chờ kết quả trước khi cập nhật giao diện.

      await ApiClient().dio.post('documents/${widget.id}/unarchive/');
      _refreshDocumentQueries();
      if (mounted) _showSnack('Đã khôi phục văn bản.');
    } catch (e) {
      if (mounted) _showSnack('Lỗi: $e', error: true);
    } finally {
      // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

      if (mounted) setState(() => _actionLoading = false);
    }
  }

  // Nút Xóa: chuyển văn bản vào thùng rác (có xác nhận).
  Future<void> _delete() async {
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text(_pick('Xác nhận xóa', 'Confirm deletion')),
        content: Text(_pick(
          'Bạn có chắc muốn xóa văn bản này? Hành động này không thể hoàn tác.',
          'Are you sure you want to delete this document? This action cannot be undone.',
        )),
        actions: [
          TextButton(
              onPressed: () => Navigator.pop(ctx, false),
              child: Text(_pick('Hủy', 'Cancel'))),
          FilledButton(
            onPressed: () => Navigator.pop(ctx, true),
            style: FilledButton.styleFrom(backgroundColor: Colors.red),
            child: Text(_pick('Xóa', 'Delete')),
          ),
        ],
      ),
    );
    if (ok != true) return;
    try {
      // Gọi API hoặc tác vụ bất đồng bộ rồi chờ kết quả trước khi cập nhật giao diện.

      await ApiClient().dio.delete('documents/${widget.id}/');
      // Điều hướng người dùng sang màn phù hợp theo kết quả thao tác hiện tại.

      if (mounted) context.go('/documents?group=private');
      refreshDocumentCollections(ref);
    } catch (e) {
      if (mounted) _showSnack('Lỗi: $e', error: true);
    }
  }

  // Làm mới các provider liên quan tới văn bản (chi tiết + danh sách) sau thao tác.

  void _refreshDocumentQueries() {
    refreshDocumentCollections(ref);
  }

  // Reset xem trước + tải lại văn bản (sau thao tác làm đổi nội dung).
  void _resetPreviewAndRefreshDocument() {
    if (mounted) {
      // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

      setState(() {
        _previewBlockedRevision = _currentPreviewRevision;
        _summaryError = _documentSummary == null
            ? null
            : 'Văn bản vừa thay đổi. Hãy bấm "Tóm tắt lại" để cập nhật bản tóm tắt mới nhất.';
        _documentSummary = null;
        _summaryRevisionToken = null;
        _summaryUpdatedAt = null;
        _resetPreviewState();
      });
    } else {
      _previewBlockedRevision = _currentPreviewRevision;
      _documentSummary = null;
      _summaryRevisionToken = null;
      _summaryUpdatedAt = null;
      _resetPreviewState();
    }
    _refreshDocumentQueries();
  }

  // Nút Yêu thích: bật/tắt đánh dấu yêu thích văn bản.
  Future<void> _toggleFavorite() async {
    try {
      // Gọi API hoặc tác vụ bất đồng bộ rồi chờ kết quả trước khi cập nhật giao diện.

      await ApiClient().dio.post('documents/${widget.id}/favorite/');
      _refreshDocumentQueries();
    } catch (e) {
      if (mounted) _showSnack('Loi: $e', error: true);
    }
  }

  // Suy ra kế hoạch 'ký nhanh qua trợ lý' phù hợp cho văn bản này.
  AssistantQuickSignPlanAction? _assistantPlanForDocument(doc) {
    final serverPlan = doc.assistantAction as AssistantQuickSignPlanAction?;
    final localPlan = _assistantPlanOverride;
    if (localPlan == null) {
      if (serverPlan?.planToken == _dismissedAssistantPlanToken) {
        return null;
      }
      return serverPlan;
    }
    if (serverPlan == null) {
      return localPlan;
    }
    if (serverPlan.planToken == _dismissedAssistantPlanToken) {
      return null;
    }
    if (serverPlan.planToken != localPlan.planToken) {
      return serverPlan;
    }
    if (serverPlan.documentVersionNumber != localPlan.documentVersionNumber) {
      return serverPlan;
    }
    if (serverPlan.isCompleted && !localPlan.isCompleted) {
      return serverPlan;
    }
    if (serverPlan.isPartial && !localPlan.isPartial) {
      return serverPlan;
    }
    if (serverPlan.hasErrorState && !localPlan.hasErrorState) {
      return serverPlan;
    }
    return localPlan;
  }

  // Sau khi ký nhanh xong -> làm mới văn bản.
  void _refreshDocumentAfterQuickSign() {
    refreshDocumentCollections(ref);
    ref.invalidate(documentDetailProvider(widget.id));
    ref.invalidate(signingSummaryProvider);
  }

  // Đặt trạng thái đang xử lý cho luồng ký nhanh (khóa nút).
  void _setQuickSignBusy(bool value, {String? label}) {
    if (!mounted) {
      return;
    }
    setState(() {
      _quickSignBusy = value;
      _quickSignBusyLabel = value ? label : null;
    });
  }

  // Rút thông điệp lỗi gọn từ lỗi API để hiển thị.
  String _apiErrorMessage(Object error, {String? fallback}) {
    final strings = AppStrings.of(context);
    final fallbackMessage = fallback ??
        strings.pick(
          'Không thể thực hiện thao tác lúc này.',
          'This action is not available right now.',
        );
    if (error is DioException) {
      final data = error.response?.data;
      if (data is Map) {
        if (data['detail'] != null) {
          return '${data['detail']}';
        }
        if (data['error'] != null) {
          return '${data['error']}';
        }
      }
      if (error.response?.statusCode != null) {
        return '$fallbackMessage (${error.response!.statusCode}).';
      }
      return fallbackMessage;
    }
    return fallbackMessage;
  }

  // Khi ký nhanh báo lỗi -> trích kế hoạch khắc phục từ phản hồi lỗi.
  AssistantQuickSignPlanAction? _assistantPlanFromError(Object error) {
    if (error is! DioException) {
      return null;
    }
    final data = error.response?.data;
    if (data is! Map || data['plan'] is! Map) {
      return null;
    }
    return AssistantQuickSignPlanAction.fromJson(
      Map<String, dynamic>.from(data['plan'] as Map),
    );
  }

  // Nhãn lý do khớp người nhận do trợ lý gợi ý.
  String _assistantMatchReasonLabel(String value) {
    final strings = AppStrings.of(context);
    switch (value) {
      case 'exact_alias':
        return strings.pick('Khớp theo alias', 'Matched by alias');
      case 'exact_employee_code':
        return strings.pick(
            'Khớp theo mã nhân viên', 'Matched by employee code');
      case 'exact_username':
        return strings.pick('Khớp theo tài khoản', 'Matched by username');
      case 'department_hint':
        return strings.pick('Khớp theo phòng ban', 'Matched by department');
      case 'fuzzy_name':
        return strings.pick('Khớp gần đúng theo tên', 'Fuzzy name match');
      default:
        return '';
    }
  }

  // Dòng mô tả chi tiết 1 ứng viên người nhận do trợ lý gợi ý.
  String _assistantCandidateDetail(AssistantRecipientCandidate candidate) {
    final strings = AppStrings.of(context);
    final parts = <String>[
      if (candidate.subtitle.isNotEmpty) candidate.subtitle,
      if (candidate.matchReason.trim().isNotEmpty)
        _assistantMatchReasonLabel(candidate.matchReason),
      if (candidate.aliasSummary.isNotEmpty)
        strings.pick(
          'Alias: ${candidate.aliasSummary}',
          'Aliases: ${candidate.aliasSummary}',
        ),
    ].where((item) => item.trim().isNotEmpty).toList();
    return parts.join('\n');
  }

  // Hỏi mật khẩu chứng thư để ký nhanh.
  Future<String?> _promptQuickSignPassword(
      AssistantQuickSignPlanAction plan) async {
    if (!plan.requiresReauthPassword || plan.alreadySigned) {
      return '';
    }
    final strings = AppStrings.of(context);
    final passwordCtrl = TextEditingController();
    bool obscure = true;
    _setPreviewInteractivity(false);
    try {
      return await showDialog<String>(
        context: context,
        builder: (ctx) => StatefulBuilder(
          builder: (ctx, setDialogState) {
            return AlertDialog(
              title:
                  Text(strings.pick('Xác nhận ký nhanh', 'Confirm quick sign')),
              content: SizedBox(
                width: 420,
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      strings.pick(
                        'Nhập mật khẩu hiện tại để ký số và chuyển tiếp văn bản ngay cho người nhận mà trợ lý đã chuẩn bị.',
                        'Enter your current password to sign and forward this document to the prepared recipient.',
                      ),
                      style: TextStyle(height: 1.5),
                    ),
                    const SizedBox(height: 14),
                    TextField(
                      controller: passwordCtrl,
                      obscureText: obscure,
                      autofocus: true,
                      decoration: InputDecoration(
                        labelText: strings.pick(
                          'Mật khẩu xác nhận',
                          'Confirmation password',
                        ),
                        border: const OutlineInputBorder(),
                        suffixIcon: IconButton(
                          onPressed: () =>
                              setDialogState(() => obscure = !obscure),
                          icon: Icon(
                            obscure
                                ? Icons.visibility_off_outlined
                                : Icons.visibility_outlined,
                          ),
                        ),
                      ),
                    ),
                  ],
                ),
              ),
              actions: [
                TextButton(
                  onPressed: () => Navigator.pop(ctx),
                  child: Text(strings.pick('Hủy', 'Cancel')),
                ),
                FilledButton(
                  onPressed: () {
                    final password = passwordCtrl.text;
                    if (password.trim().isEmpty) {
                      _showSnack(
                          strings.pick(
                            'Bạn cần nhập mật khẩu để tiếp tục ký nhanh.',
                            'Enter your password to continue quick signing.',
                          ),
                          error: true);
                      return;
                    }
                    Navigator.pop(ctx, password);
                  },
                  child: Text(strings.pick('Ký và gửi', 'Sign and send')),
                ),
              ],
            );
          },
        ),
      );
    } finally {
      passwordCtrl.dispose();
      _setPreviewInteractivity(true);
    }
  }

  // Tìm ứng viên người nhận cho ký nhanh (gọi API gợi ý).
  Future<List<AssistantRecipientCandidate>> _searchAssistantRecipients(
      String query) async {
    final response = await ApiClient().dio.get(
      'signing/candidates/',
      queryParameters: {
        if (query.trim().isNotEmpty) 'q': query.trim(),
      },
    );
    return (response.data as List<dynamic>? ?? const [])
        .map(
          (item) => AssistantRecipientCandidate.fromJson(
            Map<String, dynamic>.from(item as Map),
          ),
        )
        .toList();
  }

  // Mở hộp thoại chọn người nhận cho ký nhanh.
  Future<AssistantRecipientCandidate?> _pickAssistantRecipient(
    AssistantQuickSignPlanAction plan,
  ) async {
    final strings = AppStrings.of(context);
    final searchCtrl =
        TextEditingController(text: plan.recipient?.displayName ?? '');
    List<AssistantRecipientCandidate> matches = const [];
    bool loading = false;
    String? errorText;
    bool initialized = false;
    bool dialogActive = true;
    Timer? debounce;

    Future<void> runSearch(StateSetter setDialogState,
        {bool immediate = false}) async {
      final query = searchCtrl.text;
      if (!immediate) {
        debounce?.cancel();
        debounce = Timer(
          const Duration(milliseconds: 220),
          () => runSearch(setDialogState, immediate: true),
        );
        return;
      }
      setDialogState(() {
        loading = true;
        errorText = null;
      });
      try {
        final nextMatches = await _searchAssistantRecipients(query);
        if (!dialogActive) {
          return;
        }
        setDialogState(() {
          matches = nextMatches;
          loading = false;
        });
      } catch (error) {
        if (!dialogActive) {
          return;
        }
        setDialogState(() {
          loading = false;
          errorText = _apiErrorMessage(
            error,
            fallback: strings.pick(
              'Không tải được danh sách người nhận.',
              'Unable to load recipients.',
            ),
          );
        });
      }
    }

    _setPreviewInteractivity(false);
    try {
      return await showDialog<AssistantRecipientCandidate>(
        context: context,
        builder: (ctx) => StatefulBuilder(
          builder: (ctx, setDialogState) {
            if (!initialized) {
              initialized = true;
              Future<void>.microtask(
                  () => runSearch(setDialogState, immediate: true));
            }
            return AlertDialog(
              title: Text(
                strings.pick(
                    'Sửa người nhận quick-sign', 'Change quick-sign recipient'),
              ),
              content: SizedBox(
                width: 580,
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    TextField(
                      controller: searchCtrl,
                      autofocus: true,
                      decoration: InputDecoration(
                        labelText: strings.pick(
                          'Nhập tên, alias, tài khoản hoặc mã nhân viên',
                          'Enter a name, alias, username, or employee code',
                        ),
                        hintText: strings.pick(
                          'Ví dụ: Lan, lan.office, NV001...',
                          'Example: Lan, lan.office, NV001...',
                        ),
                        prefixIcon: Icon(Icons.search),
                        border: const OutlineInputBorder(),
                      ),
                      onChanged: (_) => runSearch(setDialogState),
                    ),
                    const SizedBox(height: 14),
                    SizedBox(
                      width: double.infinity,
                      height: 320,
                      child: loading
                          ? const Center(child: CircularProgressIndicator())
                          : errorText != null
                              ? Center(
                                  child: Text(
                                    errorText!,
                                    textAlign: TextAlign.center,
                                  ),
                                )
                              : matches.isEmpty
                                  ? const SizedBox.shrink()
                                  : ListView.separated(
                                      itemCount: matches.length,
                                      separatorBuilder: (_, __) =>
                                          const Divider(height: 1),
                                      itemBuilder: (context, index) {
                                        final candidate = matches[index];
                                        final detail =
                                            _assistantCandidateDetail(
                                                candidate);
                                        return ListTile(
                                          contentPadding: EdgeInsets.zero,
                                          leading: CircleAvatar(
                                            child: Text(
                                              (candidate.displayName.isNotEmpty
                                                      ? candidate.displayName[0]
                                                      : candidate.username
                                                              .isNotEmpty
                                                          ? candidate
                                                              .username[0]
                                                          : '?')
                                                  .toUpperCase(),
                                            ),
                                          ),
                                          title: Text(candidate.displayName),
                                          subtitle: detail.trim().isEmpty
                                              ? null
                                              : Text(detail),
                                          isThreeLine: detail.contains('\n'),
                                          onTap: () =>
                                              Navigator.pop(ctx, candidate),
                                        );
                                      },
                                    ),
                    ),
                    if (!loading && errorText == null && matches.isEmpty)
                      Padding(
                        padding: const EdgeInsets.only(top: 8),
                        child: Text(
                          strings.pick(
                            'Không tìm thấy người nhận phù hợp.',
                            'No matching recipient was found.',
                          ),
                          textAlign: TextAlign.center,
                        ),
                      ),
                  ],
                ),
              ),
              actions: [
                TextButton(
                  onPressed: () => Navigator.pop(ctx),
                  child: Text(strings.pick('Đóng', 'Close')),
                ),
              ],
            );
          },
        ),
      );
    } finally {
      dialogActive = false;
      debounce?.cancel();
      searchCtrl.dispose();
      _setPreviewInteractivity(true);
    }
  }

  // Bỏ qua gợi ý ký nhanh của trợ lý.
  Future<void> _dismissAssistantQuickSignPlan(
      AssistantQuickSignPlanAction plan) async {
    final strings = AppStrings.of(context);
    _setQuickSignBusy(
      true,
      label:
          strings.pick('Đang bỏ qua quick-sign...', 'Dismissing quick sign...'),
    );
    try {
      await ApiClient()
          .dio
          .post('signing/quick-sign/plans/${plan.planToken}/dismiss/');
      if (!mounted) {
        return;
      }
      setState(() {
        _assistantPlanOverride = null;
        _dismissedAssistantPlanToken = plan.planToken;
      });
      _refreshDocumentAfterQuickSign();
      _showSnack(
        strings.pick(
          'Đã bỏ qua quick-sign cho văn bản này.',
          'Quick sign was dismissed for this document.',
        ),
      );
    } catch (error) {
      _showSnack(
        _apiErrorMessage(
          error,
          fallback: strings.pick(
            'Không thể bỏ qua quick-sign lúc này.',
            'Unable to dismiss quick sign right now.',
          ),
        ),
        error: true,
      );
    } finally {
      _setQuickSignBusy(false);
    }
  }

  // Cập nhật người nhận đã chọn cho kế hoạch ký nhanh.
  Future<void> _updateAssistantQuickSignRecipient(
      AssistantQuickSignPlanAction plan) async {
    final strings = AppStrings.of(context);
    final selected = await _pickAssistantRecipient(plan);
    if (selected == null) {
      return;
    }
    _setQuickSignBusy(
      true,
      label:
          strings.pick('Đang cập nhật người nhận...', 'Updating recipient...'),
    );
    try {
      final response = await ApiClient().dio.post(
        'signing/quick-sign/plans/${plan.planToken}/recipient/',
        data: {'user_id': selected.id},
      );
      final payload = response.data as Map;
      final nextPlan = payload['plan'] is Map
          ? AssistantQuickSignPlanAction.fromJson(
              Map<String, dynamic>.from(payload['plan'] as Map),
            )
          : plan;
      if (!mounted) {
        return;
      }
      setState(() {
        _assistantPlanOverride = nextPlan;
        _dismissedAssistantPlanToken = null;
      });
      _refreshDocumentAfterQuickSign();
      _showSnack(
        strings.pick(
          'Đã cập nhật người nhận quick-sign.',
          'Quick-sign recipient updated.',
        ),
      );
    } catch (error) {
      final nextPlan = _assistantPlanFromError(error);
      if (mounted && nextPlan != null) {
        setState(() {
          _assistantPlanOverride = nextPlan;
          _dismissedAssistantPlanToken = null;
        });
      }
      _showSnack(
        _apiErrorMessage(
          error,
          fallback: strings.pick(
            'Không thể cập nhật người nhận lúc này.',
            'Unable to update the recipient right now.',
          ),
        ),
        error: true,
      );
    } finally {
      _setQuickSignBusy(false);
    }
  }

  // Thực thi kế hoạch ký nhanh (tạo nhiệm vụ ký + gửi).
  Future<void> _executeAssistantQuickSignPlan(
      AssistantQuickSignPlanAction plan) async {
    final strings = AppStrings.of(context);
    final password = await _promptQuickSignPassword(plan);
    if (password == null) {
      return;
    }
    final busyLabel = plan.canRetryForward || plan.alreadySigned
        ? strings.pick(
            'Đang gửi văn bản đến người nhận...',
            'Forwarding the document to the recipient...',
          )
        : strings.pick(
            'Đang ký và gửi văn bản...',
            'Signing and sending the document...',
          );
    _setQuickSignBusy(true, label: busyLabel);
    try {
      final response = await ApiClient().dio.post(
        'signing/quick-sign/plans/${plan.planToken}/execute/',
        data: {'reauth_password': password},
      );
      final payload = response.data as Map;
      final nextPlan = payload['plan'] is Map
          ? AssistantQuickSignPlanAction.fromJson(
              Map<String, dynamic>.from(payload['plan'] as Map),
            )
          : plan;
      if (!mounted) {
        return;
      }
      setState(() {
        _assistantPlanOverride = nextPlan;
        _dismissedAssistantPlanToken = null;
      });
      _refreshDocumentAfterQuickSign();
      _showSnack(nextPlan.message.isEmpty
          ? strings.pick(
              'Đã thực hiện quick-sign.',
              'Quick sign completed.',
            )
          : nextPlan.message);
    } catch (error) {
      final nextPlan = _assistantPlanFromError(error);
      if (mounted && nextPlan != null) {
        setState(() {
          _assistantPlanOverride = nextPlan;
          _dismissedAssistantPlanToken = null;
        });
      }
      _refreshDocumentAfterQuickSign();
      _showSnack(
        _apiErrorMessage(
          error,
          fallback: strings.pick(
            'Không thể ký nhanh lúc này.',
            'Unable to quick sign right now.',
          ),
        ),
        error: true,
      );
    } finally {
      _setQuickSignBusy(false);
    }
  }

  void _showSnack(String msg, {bool error = false}) {
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(
      content: Text(msg),
      backgroundColor: error ? Colors.red : Colors.green,
    ));
  }

  // Tab Phiên bản: liệt kê các version của văn bản + thao tác khôi phục/ẩn.
  Widget _buildVersionsTab(
    BuildContext context,
    int docId,
    bool canManageVersions, {
    String? blockedReason,
  }) {
    // Lắng nghe provider để widget tự động dựng lại khi dữ liệu hoặc trạng thái thay đổi.

    final asyncVersions = ref.watch(documentVersionsProvider(docId));
    return asyncVersions.when(
      loading: () => const Center(child: CircularProgressIndicator()),
      error: (e, _) => Center(child: Text('${_pick('Lỗi', 'Error')}: $e')),
      data: (versions) {
        if (versions.isEmpty) {
          return Center(
            child: Column(mainAxisSize: MainAxisSize.min, children: [
              const Icon(Icons.history, size: 48, color: Colors.grey),
              const SizedBox(height: 8),
              Text(_pick('Chưa có lịch sử phiên bản', 'No version history yet'),
                  style: const TextStyle(color: Colors.grey)),
            ]),
          );
        }
        return ListView.separated(
          padding: const EdgeInsets.all(12),
          itemCount: versions.length +
              (blockedReason?.trim().isNotEmpty == true ? 1 : 0),
          separatorBuilder: (_, __) => const Divider(height: 1),
          itemBuilder: (ctx, i) {
            final showBlockedBanner = blockedReason?.trim().isNotEmpty == true;
            if (showBlockedBanner && i == 0) {
              return Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: const Color(0xFFFFFBEB),
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(color: const Color(0xFFFDE68A)),
                ),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Icon(Icons.info_outline,
                        color: Color(0xFFD97706), size: 18),
                    const SizedBox(width: 10),
                    Expanded(
                      child: Text(
                        blockedReason!.trim(),
                        style: const TextStyle(
                          color: Color(0xFF92400E),
                          height: 1.45,
                        ),
                      ),
                    ),
                  ],
                ),
              );
            }
            final versionIndex = showBlockedBanner ? i - 1 : i;
            final ver = versions[versionIndex];
            final hidden = ver.isHidden;
            final dateStr = ver.createdAt.length >= 10
                ? ver.createdAt.substring(0, 10)
                : ver.createdAt;
            return Opacity(
              opacity: hidden ? 0.45 : 1.0,
              child: ListTile(
                leading: CircleAvatar(
                  backgroundColor:
                      hidden ? Colors.grey.shade100 : Colors.blue.shade50,
                  child: Text('v${ver.versionNumber}',
                      style: TextStyle(
                          fontSize: 10,
                          fontWeight: FontWeight.bold,
                          color: hidden ? Colors.grey : Colors.blue.shade700)),
                ),
                title: Row(children: [
                  Text(
                    'Phiên bản ${ver.versionNumber}',
                    style: TextStyle(
                      fontWeight: FontWeight.w500,
                      decoration: hidden ? TextDecoration.lineThrough : null,
                      color: hidden ? Colors.grey : null,
                    ),
                  ),
                  if (hidden) ...[
                    const SizedBox(width: 6),
                    Container(
                      padding: const EdgeInsets.symmetric(
                          horizontal: 6, vertical: 1),
                      decoration: BoxDecoration(
                        color: Colors.grey.shade200,
                        borderRadius: BorderRadius.circular(6),
                      ),
                      child: Text(_pick('Đã ẩn', 'Hidden'),
                          style:
                              const TextStyle(fontSize: 10, color: Colors.grey)),
                    ),
                  ],
                ]),
                subtitle: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const SizedBox(height: 2),
                    // Dòng riêng: thông tin người chỉnh sửa phiên bản.
                    Row(children: [
                      Icon(Icons.person_outline,
                          size: 13, color: Colors.grey.shade600),
                      const SizedBox(width: 4),
                      Expanded(
                        child: Text(
                          ver.createdByName.trim().isNotEmpty
                              ? ver.createdByName.trim()
                              : _pick('Không rõ người chỉnh sửa',
                                  'Unknown editor'),
                          style: TextStyle(
                              fontSize: 12,
                              color: Colors.grey.shade700,
                              fontWeight: FontWeight.w500),
                          overflow: TextOverflow.ellipsis,
                        ),
                      ),
                    ]),
                    const SizedBox(height: 2),
                    Row(children: [
                      Icon(Icons.schedule,
                          size: 13, color: Colors.grey.shade500),
                      const SizedBox(width: 4),
                      Text(dateStr,
                          style: TextStyle(
                              fontSize: 11.5, color: Colors.grey.shade600)),
                    ]),
                    if (ver.changeNote != null && ver.changeNote!.isNotEmpty) ...[
                      const SizedBox(height: 2),
                      Text(ver.changeNote!,
                          style: TextStyle(
                              fontSize: 12, color: Colors.grey.shade600)),
                    ],
                  ],
                ),
                isThreeLine: true,
                trailing: Row(mainAxisSize: MainAxisSize.min, children: [
                  // Xem trước nội dung phiên bản
                  IconButton(
                    visualDensity: VisualDensity.compact,
                    icon: const Icon(Icons.preview_outlined, size: 18),
                    tooltip: _pick('Xem trước nội dung', 'Preview content'),
                    onPressed: () => _showVersionPreview(context, ver),
                  ),
                  // So sánh với phiên bản sau (diff)
                  IconButton(
                    visualDensity: VisualDensity.compact,
                    icon: const Icon(Icons.difference_outlined, size: 18),
                    tooltip: _pick(
                        'So sánh với phiên bản sau', 'Compare with next version'),
                    onPressed: () => _showVersionDiff(context, docId, ver),
                  ),
                  if (!hidden)
                    IconButton(
                      visualDensity: VisualDensity.compact,
                      icon: const Icon(Icons.picture_as_pdf,
                          size: 18, color: Color(0xFFB91C1C)),
                      tooltip: _pick('Tải PDF phiên bản này',
                          'Download PDF of this version'),
                      onPressed: () => _downloadPdf(
                        title: 'doc_${widget.id}',
                        versionNumber: ver.versionNumber,
                      ),
                    ),
                  if (canManageVersions && !hidden)
                    IconButton(
                      visualDensity: VisualDensity.compact,
                      icon: const Icon(Icons.restore, size: 18),
                      tooltip: _pick(
                          'Khôi phục phiên bản này', 'Restore this version'),
                      onPressed: () => _restoreVersion(docId, ver.id),
                    ),
                  if (canManageVersions)
                    IconButton(
                      visualDensity: VisualDensity.compact,
                      icon: Icon(
                          hidden
                              ? Icons.visibility_outlined
                              : Icons.visibility_off_outlined,
                          size: 18),
                      tooltip: hidden ? _pick('Hiện', 'Show') : _pick('Ẩn', 'Hide'),
                      onPressed: () => _toggleVersionHide(docId, ver.id),
                    ),
                ]),
              ),
            );
          },
        );
      },
    );
  }

  // ── XEM TRƯỚC NỘI DUNG PHIÊN BẢN ────────────────────────────────────────────
  // Xem trước nội dung 1 phiên bản văn bản (giống màn chi tiết mẫu).
  void _showVersionPreview(BuildContext context, DocumentVersion ver) {
    showDialog(
      context: context,
      builder: (ctx) => Dialog(
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 780, maxHeight: 680),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Header
              Container(
                padding: const EdgeInsets.fromLTRB(20, 14, 12, 14),
                decoration: BoxDecoration(
                  color: Colors.blue.shade50,
                  borderRadius: const BorderRadius.only(
                    topLeft: Radius.circular(12),
                    topRight: Radius.circular(12),
                  ),
                  border:
                      Border(bottom: BorderSide(color: Colors.blue.shade100)),
                ),
                child: Row(children: [
                  const Icon(Icons.history_edu_outlined,
                      size: 20, color: Color(0xFF1565C0)),
                  const SizedBox(width: 8),
                  Text(
                    _pick('Xem trước — Phiên bản ${ver.versionNumber}',
                        'Preview — Version ${ver.versionNumber}'),
                    style: const TextStyle(
                        fontWeight: FontWeight.bold, fontSize: 15),
                  ),
                  const Spacer(),
                  IconButton(
                    icon: const Icon(Icons.close),
                    onPressed: () => Navigator.pop(ctx),
                    visualDensity: VisualDensity.compact,
                  ),
                ]),
              ),
              // Page-style content
              Expanded(
                child: Container(
                  color: const Color(0xFFE8EAED),
                  child: SingleChildScrollView(
                    padding: const EdgeInsets.symmetric(
                        horizontal: 32, vertical: 24),
                    child: Center(
                      child: Container(
                        width: double.infinity,
                        constraints: const BoxConstraints(maxWidth: 700),
                        padding: const EdgeInsets.all(32),
                        decoration: BoxDecoration(
                          color: Colors.white,
                          boxShadow: [
                            BoxShadow(
                              color: Colors.black.withOpacity(0.12),
                              blurRadius: 8,
                              offset: const Offset(0, 2),
                            ),
                          ],
                        ),
                        child: ver.content.isNotEmpty
                            ? SelectableText(
                                ver.content,
                                style: const TextStyle(
                                    fontFamily: 'Times New Roman',
                                    fontSize: 14,
                                    height: 1.6),
                              )
                            : Text(
                                _pick('(Không có nội dung)', '(No content)'),
                                style: TextStyle(
                                    color: Colors.grey.shade500,
                                    fontStyle: FontStyle.italic),
                              ),
                      ),
                    ),
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  // ── SO SÁNH DIFF ────────────────────────────────────────────────────────────
  // So sánh khác biệt giữa phiên bản này và phiên bản kế sau (diff).
  Future<void> _showVersionDiff(
      BuildContext context, int docId, DocumentVersion ver) async {
    try {
      final resp = await ApiClient()
          .dio
          .get('documents/$docId/versions/${ver.id}/diff/');
      final diffLines = List<String>.from(resp.data['diff_lines'] ?? []);
      final oldVer = resp.data['old_version'] ?? ver.versionNumber;

      if (!context.mounted) return;
      showDialog(
        context: context,
        builder: (ctx) => Dialog(
          shape:
              RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 860, maxHeight: 660),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // Header
                Container(
                  padding: const EdgeInsets.fromLTRB(20, 14, 12, 14),
                  decoration: const BoxDecoration(
                    color: Color(0xFF24292F),
                    borderRadius: BorderRadius.only(
                      topLeft: Radius.circular(12),
                      topRight: Radius.circular(12),
                    ),
                  ),
                  child: Row(children: [
                    const Icon(Icons.difference_outlined,
                        size: 18, color: Colors.white70),
                    const SizedBox(width: 8),
                    Text(
                        _pick('So sánh — v$oldVer → phiên bản sau',
                            'Compare — v$oldVer → next version'),
                        style: const TextStyle(
                            fontWeight: FontWeight.bold,
                            fontSize: 14,
                            color: Colors.white,
                            fontFamily: 'monospace')),
                    const Spacer(),
                    IconButton(
                      icon: const Icon(Icons.close,
                          color: Colors.white70, size: 18),
                      onPressed: () => Navigator.pop(ctx),
                      visualDensity: VisualDensity.compact,
                    ),
                  ]),
                ),
                // Legend bar
                Container(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 16, vertical: 6),
                  color: const Color(0xFFF6F8FA),
                  child: Row(children: [
                    _diffLegend(const Color(0xFFE6FFEC),
                        const Color(0xFF1A7F37), _pick('+ Thêm mới', '+ Added')),
                    const SizedBox(width: 20),
                    _diffLegend(const Color(0xFFFFEBE9),
                        const Color(0xFFCF222E), _pick('− Xóa bỏ', '− Removed')),
                    const SizedBox(width: 20),
                    _diffLegend(Colors.white, Colors.grey.shade500,
                        _pick('  Không đổi', '  Unchanged')),
                  ]),
                ),
                const Divider(height: 1),
                // Diff body
                if (diffLines.isEmpty)
                  Expanded(
                    child: Center(
                      child: Text(
                          _pick('Không có thay đổi nào giữa hai phiên bản.',
                              'There are no changes between the two versions.'),
                          style: const TextStyle(color: Colors.grey)),
                    ),
                  )
                else
                  Expanded(
                    child: Container(
                      color: const Color(0xFFF6F8FA),
                      child: SingleChildScrollView(
                        child: Container(
                          margin: const EdgeInsets.all(12),
                          decoration: BoxDecoration(
                            border: Border.all(color: const Color(0xFFD0D7DE)),
                            borderRadius: BorderRadius.circular(6),
                            color: Colors.white,
                          ),
                          child: ClipRRect(
                            borderRadius: BorderRadius.circular(6),
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: diffLines
                                  .map((line) => _buildDiffLine(line))
                                  .toList(),
                            ),
                          ),
                        ),
                      ),
                    ),
                  ),
              ],
            ),
          ),
        ),
      );
    } catch (e) {
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
              content: Text('${_pick('Lỗi tải diff', 'Diff load error')}: $e'),
              backgroundColor: Colors.red),
        );
      }
    }
  }

  // Render một dòng diff theo phong cách GitHub.
  Widget _buildDiffLine(String line) {
    if (line.startsWith('---') || line.startsWith('+++')) {
      return Container(
        width: double.infinity,
        color: const Color(0xFFF6F8FA),
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 3),
        child: Text(line,
            style: const TextStyle(
                fontSize: 12,
                fontFamily: 'monospace',
                color: Color(0xFF57606A),
                fontStyle: FontStyle.italic)),
      );
    }
    if (line.startsWith('@@')) {
      return Container(
        width: double.infinity,
        color: const Color(0xFFDDF4FF),
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 3),
        child: Text(line,
            style: const TextStyle(
                fontSize: 12,
                fontFamily: 'monospace',
                color: Color(0xFF0969DA))),
      );
    }
    if (line.startsWith('+')) {
      return _ghDiffRow(
        gutterBg: const Color(0xFFCCFFC1),
        gutterFg: const Color(0xFF1A7F37),
        rowBg: const Color(0xFFE6FFEC),
        prefix: '+',
        content: line.substring(1),
      );
    }
    if (line.startsWith('-')) {
      return _ghDiffRow(
        gutterBg: const Color(0xFFFFBEBC),
        gutterFg: const Color(0xFFCF222E),
        rowBg: const Color(0xFFFFEBE9),
        prefix: '-',
        content: line.substring(1),
      );
    }
    final content = line.startsWith(' ') ? line.substring(1) : line;
    return _ghDiffRow(
      gutterBg: Colors.white,
      gutterFg: const Color(0xFF57606A),
      rowBg: Colors.white,
      prefix: ' ',
      content: content,
    );
  }

  // Dựng 1 hàng diff kiểu GitHub (gutter +/- + nội dung).
  Widget _ghDiffRow({
    required Color gutterBg,
    required Color gutterFg,
    required Color rowBg,
    required String prefix,
    required String content,
  }) {
    return IntrinsicHeight(
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Container(
            width: 32,
            color: gutterBg,
            alignment: Alignment.topCenter,
            padding: const EdgeInsets.symmetric(vertical: 2),
            child: Text(
              prefix,
              style: TextStyle(
                  fontSize: 12,
                  fontFamily: 'monospace',
                  fontWeight: FontWeight.bold,
                  color: gutterFg),
            ),
          ),
          Container(width: 1, color: gutterBg.withOpacity(0.6)),
          Expanded(
            child: Container(
              color: rowBg,
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 2),
              child: SelectableText(
                content,
                style: const TextStyle(
                    fontSize: 12,
                    fontFamily: 'monospace',
                    color: Color(0xFF1F2328),
                    height: 1.6),
              ),
            ),
          ),
        ],
      ),
    );
  }

  // Dựng chú thích màu cho khung diff (thêm/xóa/không đổi).
  Widget _diffLegend(Color bg, Color fg, String label) {
    return Row(mainAxisSize: MainAxisSize.min, children: [
      Container(
        width: 14,
        height: 14,
        decoration: BoxDecoration(
          color: bg,
          border: Border.all(color: fg.withOpacity(0.4)),
        ),
      ),
      const SizedBox(width: 4),
      Text(label, style: TextStyle(fontSize: 11.5, color: fg)),
    ]);
  }

  // Khôi phục văn bản về 1 phiên bản cũ.
  Future<void> _restoreVersion(int docId, int verId) async {
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text(_pick('Khôi phục phiên bản', 'Restore version')),
        content: const Text(
            'Khôi phục sẽ tạo phiên bản mới từ nội dung cũ. Tiếp tục?'),
        actions: [
          TextButton(
              onPressed: () => Navigator.pop(ctx, false),
              child: Text(_pick('Hủy', 'Cancel'))),
          FilledButton(
              onPressed: () => Navigator.pop(ctx, true),
              child: Text(_pick('Khôi phục', 'Restore'))),
        ],
      ),
    );
    if (ok != true) return;
    try {
      // Gọi API hoặc tác vụ bất đồng bộ rồi chờ kết quả trước khi cập nhật giao diện.

      await ApiClient().dio.post('documents/$docId/versions/$verId/restore/');
      _resetPreviewAndRefreshDocument();
      if (mounted)
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
              content:
                  Text(_pick('Đã khôi phục phiên bản.', 'Version restored.')),
              backgroundColor: Colors.green),
        );
    } catch (e) {
      if (mounted)
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
              content: Text('${_pick('Lỗi', 'Error')}: $e'),
              backgroundColor: Colors.red),
        );
    }
  }

  // Ẩn/hiện 1 phiên bản trong danh sách version.
  Future<void> _toggleVersionHide(int docId, int verId) async {
    try {
      // Gọi API hoặc tác vụ bất đồng bộ rồi chờ kết quả trước khi cập nhật giao diện.

      await ApiClient().dio.post('documents/$docId/versions/$verId/hide/');
      ref.invalidate(documentVersionsProvider(docId));
    } catch (e) {
      if (mounted)
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
              content: Text('${_pick('Lỗi', 'Error')}: $e'),
              backgroundColor: Colors.red),
        );
    }
  }

  @override
  // Khung màn chi tiết (AppBar + tabs/nội dung) bao quanh _buildBody.
  Widget build(BuildContext context) {
    // Lắng nghe provider để widget tự động dựng lại khi dữ liệu hoặc trạng thái thay đổi.

    final asyncDoc = ref.watch(documentDetailProvider(widget.id));
    // Lắng nghe provider để widget tự động dựng lại khi dữ liệu hoặc trạng thái thay đổi.

    final user = ref.watch(currentUserProvider);

    return asyncDoc.when(
      // Dựng khung màn hình chính để chứa app bar, body, action và các vùng giao diện khác.

      loading: () =>
          const Scaffold(body: Center(child: CircularProgressIndicator())),
      // Dựng khung màn hình chính để chứa app bar, body, action và các vùng giao diện khác.

      error: (e, _) =>
          Scaffold(body: Center(child: Text('${_pick('Lỗi', 'Error')}: $e'))),
      data: (doc) {
        final isDraft = doc.status == 'draft';
        final isArchived = doc.isArchived;
        final isOwner = user?.id == doc.ownerId;
        final canDelete = doc.canDelete;
        final canManageVersions = doc.canEdit;
        final query = GoRouterState.of(context).uri.queryParameters;
        final returnTo = query['return_to'];
        final returnLabel = query['return_label'] ?? 'Quay về Chat AI';

        // Dựng khung màn hình chính để chứa app bar, body, action và các vùng giao diện khác.

        return Scaffold(
          appBar: AppBar(
            leading: IconButton(
              icon: const Icon(Icons.arrow_back),
              // Điều hướng người dùng sang màn phù hợp theo kết quả thao tác hiện tại.

              onPressed: () =>
                  context.go(returnTo ?? '/documents?group=private'),
            ),
            title: Text(doc.title, overflow: TextOverflow.ellipsis),
            bottom: TabBar(
              controller: _tabController,
              isScrollable: MediaQuery.sizeOf(context).width < 760,
              tabs: [
                Tab(text: _pick('Nội dung', 'Content')),
                Tab(text: _pick('Lịch sử phiên bản', 'Version history')),
              ],
            ),
            actions: [
              IconButton(
                icon: Icon(
                  doc.isFavorite
                      ? Icons.star_rounded
                      : Icons.star_outline_rounded,
                  color: doc.isFavorite ? Colors.amber : null,
                ),
                onPressed: _toggleFavorite,
                tooltip: doc.isFavorite
                    ? _pick('Bỏ yêu thích', 'Remove favorite')
                    : _pick('Yêu thích', 'Favorite'),
              ),
              if (doc.hasFile)
                Padding(
                  padding: const EdgeInsets.only(right: 4),
                  child: FilledButton.icon(
                    onPressed: () => _downloadDocx(title: doc.title),
                    icon: const Icon(Icons.download, size: 16),
                    label: Text(_pick('Tải Word', 'Download Word')),
                    style: FilledButton.styleFrom(
                      backgroundColor: const Color(0xFF2563EB),
                      foregroundColor: Colors.white,
                    ),
                  ),
                ),
              if (doc.hasFile)
                Padding(
                  padding: const EdgeInsets.only(right: 4),
                  child: FilledButton.icon(
                    onPressed: () => _downloadPdf(title: doc.title),
                    icon: const Icon(Icons.picture_as_pdf, size: 16),
                    label: Text(_pick('Tải PDF', 'Download PDF')),
                    style: FilledButton.styleFrom(
                      backgroundColor: const Color(0xFFB91C1C),
                      foregroundColor: Colors.white,
                    ),
                  ),
                ),
              PopupMenuButton<String>(
                onSelected: (v) {
                  switch (v) {
                    case 'download':
                      _downloadDocx(title: doc.title);
                      break;
                    case 'download_pdf':
                      _downloadPdf(title: doc.title);
                      break;
                    case 'share':
                      _showShareDialog(doc);
                      break;
                    case 'finalize':
                      _finalize();
                      break;
                    case 'archive':
                      _archive();
                      break;
                    case 'unarchive':
                      _unarchive();
                      break;
                    case 'delete':
                      _delete();
                      break;
                  }
                },
                itemBuilder: (_) => [
                  if (doc.hasFile)
                    PopupMenuItem(
                        value: 'download',
                        child: ListTile(
                          leading: Icon(Icons.download),
                          title: Text(_pick('Tải Word', 'Download Word')),
                        )),
                  if (doc.hasFile)
                    PopupMenuItem(
                        value: 'download_pdf',
                        child: ListTile(
                          leading: Icon(Icons.picture_as_pdf,
                              color: Color(0xFFB91C1C)),
                          title: Text(_pick('Tải PDF', 'Download PDF')),
                        )),
                  if (isOwner && !isArchived)
                    PopupMenuItem(
                        value: 'share',
                        child: ListTile(
                          leading:
                              Icon(Icons.share_outlined, color: Colors.blue),
                          title: Text(_pick('Chia sẻ', 'Share')),
                        )),
                  if (isOwner && isDraft && !isArchived)
                    PopupMenuItem(
                        value: 'finalize',
                        child: ListTile(
                          leading: Icon(Icons.check_circle_outline,
                              color: Colors.green),
                          title: Text(_pick('Chuyển Chính thức', 'Finalize')),
                        )),
                  if (isOwner && doc.visibility == 'private' && !isArchived)
                    PopupMenuItem(
                        value: 'archive',
                        child: ListTile(
                          leading: Icon(Icons.archive_outlined,
                              color: Colors.orange),
                          title: Text(_pick('Lưu trữ', 'Archive')),
                        )),
                  if (isOwner && isArchived)
                    PopupMenuItem(
                        value: 'unarchive',
                        child: ListTile(
                          leading: Icon(Icons.unarchive_outlined,
                              color: Colors.blue),
                          title: Text(_pick('Khôi phục', 'Restore')),
                        )),
                  if (canDelete)
                    PopupMenuItem(
                        value: 'delete',
                        child: ListTile(
                          leading:
                              Icon(Icons.delete_outline, color: Colors.red),
                          title: Text(_pick('Xóa', 'Delete')),
                        )),
                ],
              ),
            ],
          ),
          body: _actionLoading
              ? const Center(child: CircularProgressIndicator())
              : TabBarView(
                  controller: _tabController,
                  children: [
                    _buildBody(
                      context,
                      doc,
                      isDraft,
                      isArchived,
                      isOwner,
                      canManageVersions,
                      returnTo: returnTo,
                      returnLabel: returnLabel,
                    ),
                    // Tab Lịch sử phiên bản: danh sách đầy đủ + xem trước/so sánh/khôi phục/ẩn.
                    _buildVersionsTab(
                      context,
                      doc.id as int,
                      canManageVersions,
                      blockedReason: doc.manualEditActive == true
                          ? doc.manualEditLockMessage as String?
                          : null,
                    ),
                  ],
                ),
        );
      },
    );
  }

  // Thân màn: thông tin + xem trước PDF + tóm tắt + phiên bản + các nút thao tác/ký nhanh.
  Widget _buildBody(
    BuildContext context,
    doc,
    bool isDraft,
    bool isArchived,
    bool isOwner,
    bool canManageVersions, {
    String? returnTo,
    String? returnLabel,
  }) {
    final screenWidth = MediaQuery.of(context).size.width;
    final isWide = screenWidth >= 900;
    final returnBanner = returnTo == null
        ? null
        : _buildReturnBanner(
            context, returnTo, returnLabel ?? 'Quay về Chat AI');

    if (isWide) {
      return SingleChildScrollView(
        padding: const EdgeInsets.all(24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            if (returnBanner != null) ...[
              returnBanner,
              const SizedBox(height: 16),
            ],
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Expanded(
                  flex: 3,
                  child: _buildLeftColumn(context, doc, isDraft, isArchived,
                      isOwner, canManageVersions),
                ),
                const SizedBox(width: 24),
                SizedBox(
                  width: 280,
                  child: _buildRightColumn(context, doc, canManageVersions),
                ),
              ],
            ),
          ],
        ),
      );
    }

    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          if (returnBanner != null) ...[
            returnBanner,
            const SizedBox(height: 16),
          ],
          _buildLeftColumn(
              context, doc, isDraft, isArchived, isOwner, canManageVersions),
          const SizedBox(height: 24),
          _buildRightColumn(context, doc, canManageVersions),
        ],
      ),
    );
  }

  // Banner 'quay lại nơi đã đến từ' (deep-link returnTo).
  Widget _buildReturnBanner(
      BuildContext context, String returnTo, String returnLabel) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
      decoration: BoxDecoration(
        color: const Color(0xFFEFF6FF),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: const Color(0xFFBFDBFE)),
      ),
      child: Align(
        alignment: Alignment.centerLeft,
        child: TextButton.icon(
          // Điều hướng người dùng sang màn phù hợp theo kết quả thao tác hiện tại.

          onPressed: () => context.go(returnTo),
          icon: const Icon(Icons.arrow_back),
          label: Text(returnLabel),
        ),
      ),
    );
  }

  // Khối gợi ý ký nhanh qua trợ lý (chọn người nhận + thực thi).
  Widget _buildAssistantQuickSignSection(BuildContext context, doc) {
    final plan = _assistantPlanForDocument(doc);
    if (plan == null) {
      return const SizedBox.shrink();
    }
    return AssistantQuickSignPanel(
      plan: plan,
      compact: MediaQuery.of(context).size.width < 900,
      busy: _quickSignBusy,
      busyLabel: _quickSignBusyLabel,
      onQuickSign: () => _executeAssistantQuickSignPlan(plan),
      onEditRecipient: () => _updateAssistantQuickSignRecipient(plan),
      onDismiss: () => _dismissAssistantQuickSignPlan(plan),
    );
  }

  Widget _buildLeftColumn(
    BuildContext context,
    doc,
    bool isDraft,
    bool isArchived,
    bool isOwner,
    bool canManageVersions,
  ) {
    final isCompact = MediaQuery.of(context).size.width < 900;
    final assistantPanel = _buildAssistantQuickSignSection(context, doc);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // Meta badges row
        Wrap(
          spacing: 8,
          runSpacing: 8,
          crossAxisAlignment: WrapCrossAlignment.center,
          children: [
            if (doc.docNumber != null && doc.docNumber!.isNotEmpty)
              _MetaChip(
                icon: Icons.tag,
                label: 'Số: ${doc.docNumber}',
                color: const Color(0xFF2563EB),
              ),
            _StatusBadge(status: doc.status),
            _MetaChip(
              icon: doc.signingStatus == 'signed'
                  ? Icons.verified_outlined
                  : Icons.gpp_maybe_outlined,
              label: doc.signingStatus == 'signed' ? 'Đã ký' : 'Chưa ký',
              color: doc.signingStatus == 'signed'
                  ? const Color(0xFF166534)
                  : const Color(0xFFD97706),
            ),
            _VisibilityBadge(visibility: doc.visibility),
            _ShareStatusBadge(shareStatus: doc.shareStatus),
            if (doc.sourceType != null && doc.sourceType!.isNotEmpty)
              _MetaChip(
                icon: doc.sourceType == 'uploaded'
                    ? Icons.upload_file
                    : Icons.auto_awesome,
                label: doc.sourceType == 'uploaded' ? 'Upload' : 'Tạo từ AI',
                color: Colors.purple.shade400,
              ),
          ],
        ),

        const SizedBox(height: 16),

        if (assistantPanel is! SizedBox) ...[
          assistantPanel,
          const SizedBox(height: 16),
        ],

        // Action bar
        Wrap(
          spacing: 8,
          runSpacing: 8,
          children: [
            if (doc.hasFile)
              OutlinedButton.icon(
                onPressed: () => _downloadDocx(title: doc.title),
                icon: const Icon(Icons.description,
                    size: 16, color: Color(0xFF2563EB)),
                label: Text(_pick('Tải văn bản Word', 'Download Word document'),
                    style: TextStyle(color: Color(0xFF2563EB))),
                style: OutlinedButton.styleFrom(
                    side: const BorderSide(color: Color(0xFF2563EB))),
              ),
            if (isOwner && isDraft && !isArchived)
              OutlinedButton.icon(
                onPressed: _finalize,
                icon: const Icon(Icons.check_circle_outline,
                    size: 16, color: Colors.green),
                label: Text(_pick('Chuyển Chính thức', 'Finalize'),
                    style: TextStyle(color: Colors.green)),
                style: OutlinedButton.styleFrom(
                    side: const BorderSide(color: Colors.green)),
              ),
            if (isOwner && !isDraft && !isArchived && doc.hasFile)
              FilledButton.icon(
                onPressed: _actionLoading ? null : _startSigningForCurrentUser,
                icon: const Icon(Icons.edit_document, size: 16),
                label: Text(_pick('Ký cho tôi', 'Sign for me')),
              ),
            if (isOwner && !isDraft && !isArchived && doc.hasFile)
              OutlinedButton.icon(
                onPressed: _actionLoading
                    ? null
                    : () => _showSigningProposalDialog(doc),
                icon: const Icon(Icons.draw_outlined,
                    size: 16, color: Color(0xFF7C3AED)),
                label: Text(
                    _pick('Khởi tạo quy trình ký', 'Start signing flow'),
                    style: TextStyle(color: Color(0xFF7C3AED))),
                style: OutlinedButton.styleFrom(
                    side: const BorderSide(color: Color(0xFF7C3AED))),
              ),
            if (!isArchived && doc.hasFile)
              OutlinedButton.icon(
                onPressed:
                    _actionLoading ? null : () => _showForwardDialog(doc),
                icon: const Icon(Icons.forward_to_inbox_outlined,
                    size: 16, color: Color(0xFF0F766E)),
                label: Text(_pick('Forward vào Hòm thư', 'Forward to mailbox'),
                    style: TextStyle(color: Color(0xFF0F766E))),
                style: OutlinedButton.styleFrom(
                    side: const BorderSide(color: Color(0xFF0F766E))),
              ),
            if (isOwner && !isArchived)
              OutlinedButton.icon(
                onPressed: () => _showShareDialog(doc),
                icon: const Icon(Icons.share_outlined,
                    size: 16, color: Colors.blue),
                label: Text(_pick('Chia sẻ', 'Share'),
                    style: const TextStyle(color: Colors.blue)),
                style: OutlinedButton.styleFrom(
                    side: const BorderSide(color: Colors.blue)),
              ),
            if (isOwner && doc.visibility == 'private' && !isArchived)
              OutlinedButton.icon(
                onPressed: _archive,
                icon: const Icon(Icons.archive_outlined,
                    size: 16, color: Colors.orange),
                label: Text(_pick('Lưu trữ', 'Archive'),
                    style: TextStyle(color: Colors.orange)),
                style: OutlinedButton.styleFrom(
                    side: const BorderSide(color: Colors.orange)),
              ),
            if (isOwner && isArchived)
              OutlinedButton.icon(
                onPressed: _unarchive,
                icon: const Icon(Icons.unarchive_outlined,
                    size: 16, color: Colors.blue),
                label: Text(_pick('Khôi phục', 'Restore'),
                    style: TextStyle(color: Colors.blue)),
                style: OutlinedButton.styleFrom(
                    side: const BorderSide(color: Colors.blue)),
              ),
          ],
        ),

        const SizedBox(height: 16),
        const Divider(),
        const SizedBox(height: 12),

        Text(
          'Nội dung văn bản',
          style: Theme.of(context)
              .textTheme
              .titleMedium
              ?.copyWith(fontWeight: FontWeight.bold),
        ),
        const SizedBox(height: 12),

        // Content container
        Container(
          width: double.infinity,
          padding: EdgeInsets.all(isCompact ? 14 : 24),
          decoration: BoxDecoration(
            color: Colors.white,
            border: Border.all(color: Colors.grey.shade200),
            borderRadius: BorderRadius.circular(8),
            boxShadow: [
              BoxShadow(
                color: Colors.black.withOpacity(0.04),
                blurRadius: 8,
                offset: const Offset(0, 2),
              ),
            ],
          ),
          child: _buildContentArea(doc),
        ),
      ],
    );
  }

  // Thanh skeleton khi đang tải tóm tắt.
  Widget _buildSummarySkeletonBar(double widthFactor) {
    return FractionallySizedBox(
      widthFactor: widthFactor,
      child: Container(
        height: 12,
        decoration: BoxDecoration(
          color: const Color(0xFFE2E8F0),
          borderRadius: BorderRadius.circular(999),
        ),
      ),
    );
  }

  // Thẻ trạng thái đang tạo tóm tắt.
  Widget _buildSummaryLoadingCard() {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        gradient: const LinearGradient(
          colors: [Color(0xFFF8FAFC), Color(0xFFEFF6FF)],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: const Color(0xFFBFDBFE)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Row(
            children: [
              SizedBox(
                width: 22,
                height: 22,
                child: CircularProgressIndicator(strokeWidth: 2.4),
              ),
              SizedBox(width: 12),
              Expanded(
                child: Text(
                  'AI đang đọc toàn bộ văn bản và tạo bản tóm tắt mới...',
                  style: TextStyle(
                    fontWeight: FontWeight.w700,
                    color: Color(0xFF1E3A8A),
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 14),
          ClipRRect(
            borderRadius: BorderRadius.circular(999),
            child: const LinearProgressIndicator(
              minHeight: 6,
              backgroundColor: Color(0xFFDBEAFE),
              valueColor: AlwaysStoppedAnimation<Color>(Color(0xFF2563EB)),
            ),
          ),
          const SizedBox(height: 16),
          FadeTransition(
            opacity: Tween<double>(begin: 0.45, end: 1.0).animate(
              CurvedAnimation(
                parent: _summaryPulseController,
                curve: Curves.easeInOut,
              ),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                _buildSummarySkeletonBar(0.94),
                const SizedBox(height: 10),
                _buildSummarySkeletonBar(1.0),
                const SizedBox(height: 10),
                _buildSummarySkeletonBar(0.87),
                const SizedBox(height: 10),
                _buildSummarySkeletonBar(0.72),
              ],
            ),
          ),
        ],
      ),
    );
  }

  // Khối hiển thị bản tóm tắt văn bản (kèm nút tạo/tải).
  Widget _buildDocumentSummarySection(doc, {required bool isCompact}) {
    final currentRevision = _previewRevisionToken(doc);
    final hasSummary =
        _documentSummary != null && _documentSummary!.trim().isNotEmpty;
    final isStale = hasSummary &&
        _summaryRevisionToken != null &&
        _summaryRevisionToken != currentRevision;

    return Container(
      width: double.infinity,
      margin: const EdgeInsets.only(bottom: 16),
      padding: EdgeInsets.all(isCompact ? 14 : 18),
      decoration: BoxDecoration(
        color: const Color(0xFFF8FAFC),
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: const Color(0xFFE2E8F0)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          if (isCompact) ...[
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Container(
                  width: 38,
                  height: 38,
                  decoration: BoxDecoration(
                    color: const Color(0xFFDBEAFE),
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: const Icon(
                    Icons.auto_awesome,
                    color: Color(0xFF2563EB),
                    size: 20,
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Text(
                        'Tóm tắt nhanh nội dung văn bản',
                        style: Theme.of(context).textTheme.titleSmall?.copyWith(
                              fontWeight: FontWeight.w700,
                              color: const Color(0xFF0F172A),
                            ),
                      ),
                      Text(
                        hasSummary
                            ? 'Nhấn để yêu cầu AI tóm tắt lại toàn bộ nội dung mới nhất.'
                            : 'Nhấn để AI đọc và tóm tắt lại toàn bộ nội dung tài liệu này.',
                        style: const TextStyle(
                          color: Color(0xFF475569),
                          height: 1.4,
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12),
            SizedBox(
              width: double.infinity,
              child: FilledButton.icon(
                onPressed:
                    _summaryLoading ? null : () => _summarizeDocument(doc),
                icon: Icon(
                    _summaryLoading ? Icons.hourglass_top : Icons.auto_awesome),
                label:
                    Text(_summaryLoading ? 'Đang tóm tắt...' : 'Tóm tắt lại'),
                style: FilledButton.styleFrom(
                  backgroundColor: const Color(0xFF2563EB),
                  foregroundColor: Colors.white,
                ),
              ),
            ),
            const SizedBox(height: 10),
            SizedBox(
              width: double.infinity,
              child: OutlinedButton.icon(
                onPressed: () => context.go('/summaries/${doc.id}'),
                icon: const Icon(Icons.open_in_new),
                label: Text(_pick(
                  'Mo workspace tom tat',
                  'Open summary workspace',
                )),
              ),
            ),
          ] else ...[
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Expanded(
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Container(
                        width: 38,
                        height: 38,
                        decoration: BoxDecoration(
                          color: const Color(0xFFDBEAFE),
                          borderRadius: BorderRadius.circular(12),
                        ),
                        child: const Icon(
                          Icons.auto_awesome,
                          color: Color(0xFF2563EB),
                          size: 20,
                        ),
                      ),
                      const SizedBox(width: 12),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Text(
                              'Tóm tắt nhanh nội dung văn bản',
                              style: Theme.of(context)
                                  .textTheme
                                  .titleSmall
                                  ?.copyWith(
                                    fontWeight: FontWeight.w700,
                                    color: const Color(0xFF0F172A),
                                  ),
                            ),
                            Text(
                              hasSummary
                                  ? 'Nhấn để yêu cầu AI tóm tắt lại toàn bộ nội dung mới nhất.'
                                  : 'Nhấn để AI đọc và tóm tắt lại toàn bộ nội dung tài liệu này.',
                              style: const TextStyle(
                                color: Color(0xFF475569),
                                height: 1.4,
                              ),
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(width: 16),
                FilledButton.icon(
                  onPressed:
                      _summaryLoading ? null : () => _summarizeDocument(doc),
                  icon: Icon(_summaryLoading
                      ? Icons.hourglass_top
                      : Icons.auto_awesome),
                  label:
                      Text(_summaryLoading ? 'Đang tóm tắt...' : 'Tóm tắt lại'),
                  style: FilledButton.styleFrom(
                    backgroundColor: const Color(0xFF2563EB),
                    foregroundColor: Colors.white,
                  ),
                ),
                const SizedBox(width: 10),
                OutlinedButton.icon(
                  onPressed: () => context.go('/summaries/${doc.id}'),
                  icon: const Icon(Icons.open_in_new),
                  label: Text(_pick(
                    'Mo workspace tom tat',
                    'Open summary workspace',
                  )),
                ),
              ],
            ),
          ],
          const SizedBox(height: 14),
          if (_summaryLoading) ...[
            if (_summaryTaskId != null)
              Container(
                width: double.infinity,
                padding: EdgeInsets.symmetric(horizontal: isCompact ? 6 : 10),
                decoration: BoxDecoration(
                  color: Colors.white,
                  borderRadius: BorderRadius.circular(16),
                  border: Border.all(color: const Color(0xFFDBEAFE)),
                ),
                child: AITaskLinearProgress(
                  taskId: _summaryTaskId!,
                  onComplete: (state) => _handleSummaryTaskComplete(doc, state),
                  onCancelled: (_) => _handleSummaryTaskCancelled(),
                  onFailed: _handleSummaryTaskFailed,
                ),
              )
            else
              _buildSummaryLoadingCard(),
          ] else if (hasSummary) ...[
            if (isStale)
              Container(
                width: double.infinity,
                margin: const EdgeInsets.only(bottom: 12),
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: const Color(0xFFFFFBEB),
                  borderRadius: BorderRadius.circular(14),
                  border: Border.all(color: const Color(0xFFFDE68A)),
                ),
                child: const Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Icon(Icons.info_outline,
                        color: Color(0xFFD97706), size: 18),
                    SizedBox(width: 10),
                    Expanded(
                      child: Text(
                        'Văn bản đã thay đổi kể từ lần tóm tắt trước. Hãy bấm "Tóm tắt lại" để cập nhật nội dung mới nhất.',
                        style: TextStyle(
                          color: Color(0xFF92400E),
                          height: 1.45,
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            Container(
              width: double.infinity,
              padding: EdgeInsets.all(isCompact ? 14 : 18),
              decoration: BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.circular(16),
                border: Border.all(color: const Color(0xFFDBEAFE)),
                boxShadow: const [
                  BoxShadow(
                    color: Color(0x0D0F172A),
                    blurRadius: 10,
                    offset: Offset(0, 3),
                  ),
                ],
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      const Icon(
                        Icons.notes_rounded,
                        size: 18,
                        color: Color(0xFF2563EB),
                      ),
                      const SizedBox(width: 8),
                      const Expanded(
                        child: Text(
                          'Bản tóm tắt mới nhất',
                          style: TextStyle(
                            fontWeight: FontWeight.w700,
                            color: Color(0xFF1E3A8A),
                          ),
                        ),
                      ),
                      if (_summaryUpdatedAt != null)
                        Text(
                          'Cập nhật ${_formatSummaryUpdatedAt(_summaryUpdatedAt!)}',
                          style: const TextStyle(
                            fontSize: 12,
                            color: Color(0xFF64748B),
                          ),
                        ),
                    ],
                  ),
                  const SizedBox(height: 12),
                  Text(
                    _documentSummary!,
                    style: TextStyle(
                      fontSize: isCompact ? 14 : 15,
                      height: 1.6,
                      color: const Color(0xFF1E293B),
                    ),
                  ),
                ],
              ),
            ),
          ] else ...[
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(14),
              decoration: BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.circular(16),
                border: Border.all(color: const Color(0xFFE2E8F0)),
              ),
              child: const Text(
                'Chưa có bản tóm tắt. Hãy bấm "Tóm tắt lại" để AI đọc toàn bộ văn bản và tạo bản tóm tắt ngay tại đây.',
                style: TextStyle(
                  color: Color(0xFF475569),
                  height: 1.5,
                ),
              ),
            ),
          ],
          if (_summaryError != null && !_summaryLoading) ...[
            const SizedBox(height: 12),
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: const Color(0xFFFEF2F2),
                borderRadius: BorderRadius.circular(14),
                border: Border.all(color: const Color(0xFFFECACA)),
              ),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Icon(Icons.error_outline,
                      color: Color(0xFFDC2626), size: 18),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Text(
                      _summaryError!,
                      style: const TextStyle(
                        color: Color(0xFF991B1B),
                        height: 1.45,
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ],
        ],
      ),
    );
  }

  // Khu vực nội dung: khung đọc HTML / xem trước PDF của văn bản.
  Widget _buildContentArea(doc) {
    final hasFile = doc.hasFile as bool;
    final hasContent =
        doc.content != null && (doc.content as String).isNotEmpty;
    final isCompact = MediaQuery.of(context).size.width < 900;
    final previewHeight =
        (MediaQuery.of(context).size.height * (isCompact ? 0.72 : 0.82))
            .clamp(isCompact ? 520.0 : 760.0, 1280.0)
            .toDouble();
    final previewRevision = _previewRevisionToken(doc);
    _currentPreviewRevision = previewRevision;
    final waitingForFreshRevision = _previewBlockedRevision != null &&
        _previewBlockedRevision == previewRevision;

    if ((hasFile || hasContent) &&
        !waitingForFreshRevision &&
        _previewPdfUrl == null &&
        _contentHtml == null &&
        !_contentLoading &&
        _previewLoadError == null) {
      WidgetsBinding.instance
          .addPostFrameCallback((_) => _loadContentPreview(doc));
    }
    Widget previewBody;

    if (waitingForFreshRevision) {
      previewBody = SizedBox(
        height: 200,
        child: Center(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const CircularProgressIndicator(),
              const SizedBox(height: 12),
              Text(
                  _pick(
                      'Đang cập nhật bản xem mới...', 'Refreshing preview...'),
                  style: TextStyle(color: Colors.grey)),
            ],
          ),
        ),
      );
    } else if (_contentLoading) {
      previewBody = SizedBox(
        height: 200,
        child: Center(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const CircularProgressIndicator(),
              const SizedBox(height: 12),
              Text(_pick('Đang tải nội dung...', 'Loading content...'),
                  style: TextStyle(color: Colors.grey)),
            ],
          ),
        ),
      );
    } else if (_previewLoadError != null) {
      previewBody = Container(
        width: double.infinity,
        padding: const EdgeInsets.all(18),
        decoration: BoxDecoration(
          color: const Color(0xFFFEF2F2),
          borderRadius: BorderRadius.circular(14),
          border: Border.all(color: const Color(0xFFFECACA)),
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Icon(Icons.error_outline, color: Color(0xFFDC2626)),
                const SizedBox(width: 10),
                Expanded(
                  child: Text(
                    _pick('Không tải được bản xem văn bản',
                        'Unable to load the document preview'),
                    style: TextStyle(
                      fontWeight: FontWeight.w700,
                      color: Color(0xFF991B1B),
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 10),
            Text(
              _previewLoadError!,
              style: const TextStyle(
                color: Color(0xFF7F1D1D),
                height: 1.5,
              ),
            ),
            const SizedBox(height: 12),
            OutlinedButton.icon(
              onPressed: () => _loadContentPreview(doc, force: true),
              icon: const Icon(Icons.refresh, size: 16),
              label: Text(_pick('Tải lại PDF', 'Reload PDF')),
            ),
          ],
        ),
      );
    } else if (_previewPdfUrl != null && _previewPdfUrl!.isNotEmpty) {
      previewBody = Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            width: double.infinity,
            margin: const EdgeInsets.only(bottom: 12),
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: const Color(0xFFF8FAFC),
              borderRadius: BorderRadius.circular(14),
              border: Border.all(color: const Color(0xFFE2E8F0)),
            ),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        isCompact
                            ? 'Đang hiển thị bản xem PDF tối ưu cho màn hình dọc.'
                            : 'Đang hiển thị bản xem PDF giữ bố cục văn bản gần với file Word gốc. Hệ thống tự động tải lại mỗi 10 giây.',
                        style: const TextStyle(
                            height: 1.45, color: Color(0xFF475569)),
                      ),
                      const SizedBox(height: 12),
                      Wrap(
                        spacing: 12,
                        runSpacing: 12,
                        children: [
                          OutlinedButton.icon(
                            onPressed: () =>
                                _loadContentPreview(doc, force: true),
                            icon: const Icon(Icons.refresh, size: 16),
                            label: Text(_pick('Tải lại', 'Reload')),
                          ),
                          OutlinedButton.icon(
                            onPressed: () => _openContentPreviewDialog(doc),
                            icon: const Icon(Icons.open_in_full, size: 16),
                            label: Text(_pick('Toàn màn hình', 'Full screen')),
                          ),
                        ],
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
          if (_previewNotice != null && _previewNotice!.isNotEmpty)
            Container(
              width: double.infinity,
              margin: const EdgeInsets.only(bottom: 12),
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: const Color(0xFFFFFBEB),
                borderRadius: BorderRadius.circular(14),
                border: Border.all(color: const Color(0xFFFDE68A)),
              ),
              child: Row(
                children: [
                  const Icon(Icons.info_outline, color: Color(0xFFD97706)),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Text(
                      _previewNotice!,
                      style: const TextStyle(
                        color: Color(0xFF92400E),
                        height: 1.45,
                      ),
                    ),
                  ),
                ],
              ),
            ),
          SizedBox(
            height: previewHeight,
            child: _buildPdfFrame(
              pdfUrl: _previewPdfUrl!,
              fullScreen: false,
            ),
          ),
        ],
      );
    } else if (_contentHtml != null && _contentHtml!.isNotEmpty) {
      previewBody = Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          if (_previewNotice != null && _previewNotice!.isNotEmpty)
            Container(
              width: double.infinity,
              margin: const EdgeInsets.only(bottom: 12),
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: const Color(0xFFFFFBEB),
                borderRadius: BorderRadius.circular(14),
                border: Border.all(color: const Color(0xFFFDE68A)),
              ),
              child: Row(
                children: [
                  const Icon(Icons.info_outline, color: Color(0xFFD97706)),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Text(
                      _previewNotice!,
                      style: const TextStyle(
                        color: Color(0xFF92400E),
                        height: 1.45,
                      ),
                    ),
                  ),
                ],
              ),
            ),
          if (isCompact) ...[
            Container(
              width: double.infinity,
              margin: const EdgeInsets.only(bottom: 12),
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: const Color(0xFFF8FAFC),
                borderRadius: BorderRadius.circular(14),
                border: Border.all(color: const Color(0xFFE2E8F0)),
              ),
              child: Row(
                children: [
                  const Expanded(
                    child: Text(
                      'Chế độ đọc trên điện thoại đang tự co theo chiều ngang màn hình.',
                      style: TextStyle(height: 1.45, color: Color(0xFF475569)),
                    ),
                  ),
                  const SizedBox(width: 12),
                  OutlinedButton.icon(
                    onPressed: () => _openContentPreviewDialog(doc),
                    icon: const Icon(Icons.open_in_full, size: 16),
                    label: Text(_pick('Toàn màn hình', 'Full screen')),
                  ),
                ],
              ),
            ),
          ],
          SizedBox(
            height: _contentFrameHeight,
            child: _buildContentFrame(
              htmlContent: _contentHtml!,
              isCompact: isCompact,
              fullScreen: false,
            ),
          ),
        ],
      );
    } else if (!hasFile && !hasContent) {
      previewBody = Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          const SizedBox(height: 32),
          Icon(Icons.description_outlined,
              size: 48, color: Colors.grey.shade300),
          const SizedBox(height: 8),
          Text(_pick('Chưa có nội dung', 'No content yet'),
              style: TextStyle(color: Colors.grey.shade500, fontSize: 14)),
          const SizedBox(height: 32),
        ],
      );
    } else {
      previewBody = const SizedBox(
        height: 100,
        child: Center(child: CircularProgressIndicator()),
      );
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _buildDocumentSummarySection(doc, isCompact: isCompact),
        previewBody,
      ],
    );
  }

  // Dựng cột phải màn chi tiết: thông tin/metadata + tab phiên bản (nếu có quyền quản lý version).

  Widget _buildRightColumn(BuildContext context, doc, bool canManageVersions) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _CollapsibleSection(
          icon: Icons.info_outline,
          title: _pick('Thông tin văn bản', 'Document information'),
          accentColor: const Color(0xFF1D4ED8),
          initiallyExpanded: true,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const SizedBox(height: 4),
              _InfoRow(_pick('Mã hệ thống', 'System code'), doc.recordCode),
              _InfoRow(_pick('Tiêu đề', 'Title'), doc.title),
              if (doc.docNumber != null && doc.docNumber!.isNotEmpty)
                _InfoRow(
                    _pick('Số hiệu VB', 'Document number'), doc.docNumber!),
              _InfoRow(
                  _pick('Trạng thái', 'Status'), _strings.ui(doc.statusLabel)),
              _InfoRow(
                  _pick('Quyền xem', 'Visibility'),
                  doc.visibility == 'public'
                      ? _pick('Tất cả mọi người', 'Everyone')
                      : doc.visibility == 'group'
                          ? _pick('Trong nhóm', 'In group')
                          : _pick('Chỉ mình tôi', 'Only me')),
              _InfoRow(_pick('Chia sẻ', 'Sharing'),
                  _shareStatusLabel(doc.shareStatus)),
              if (doc.templateTitle != null)
                _InfoRow(_pick('Tạo từ mẫu', 'Created from template'),
                    doc.templateTitle!),
              _InfoRow(_pick('Người tạo', 'Created by'), doc.ownerName),
              _InfoRow(_pick('Phiên bản', 'Version'), 'v${doc.versionNumber}'),
              _InfoRow(
                  _pick('Ngày tạo', 'Created'),
                  doc.createdAt.length >= 10
                      ? doc.createdAt.substring(0, 10)
                      : doc.createdAt),
              _InfoRow(
                  _pick('Ngày cập nhật', 'Updated'),
                  doc.updatedAt.length >= 10
                      ? doc.updatedAt.substring(0, 10)
                      : doc.updatedAt),
              if (doc.notes != null && doc.notes!.isNotEmpty)
                _InfoRow(_pick('Ghi chú', 'Notes'), doc.notes!),
              if (doc.promptTitle != null && doc.promptTitle!.isNotEmpty)
                _InfoRow(_pick('Prompt đã áp dụng', 'Applied prompt'),
                    doc.promptTitle!),
              if (doc.appliedUserRules != null &&
                  doc.appliedUserRules!.isNotEmpty) ...[
                const SizedBox(height: 10),
                Container(
                  width: double.infinity,
                  padding: const EdgeInsets.all(10),
                  decoration: BoxDecoration(
                    color: Colors.blue.shade50,
                    border: Border.all(color: Colors.blue.shade200),
                    borderRadius: BorderRadius.circular(6),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(children: [
                        const Icon(Icons.tune, size: 14, color: Colors.blue),
                        const SizedBox(width: 4),
                        Text(
                          _pick('Yêu cầu bổ sung đã áp dụng',
                              'Applied user rules'),
                          style: const TextStyle(
                              fontWeight: FontWeight.bold,
                              fontSize: 12,
                              color: Colors.blue),
                        ),
                      ]),
                      const SizedBox(height: 4),
                      SelectableText(
                        doc.appliedUserRules!,
                        style: const TextStyle(fontSize: 12),
                      ),
                    ],
                  ),
                ),
              ],
            ],
          ),
        ),
        const SizedBox(height: 16),
        _CollapsibleSection(
          icon: Icons.people_alt_outlined,
          title: _pick('Chia sẻ cho đồng nghiệp', 'Share with peers'),
          accentColor: const Color(0xFF0EA5E9),
          initiallyExpanded: false,
          // Da chuyen sang he ShareGrant thong nhat (UnifiedShareSheet): chia se
          // dong nghiep khac nhom se dinh tuyen len ADMIN duyet va hien dung trong
          // man "Chia se cho duyet" (shares/pending), thay cho he peer-share cu.
          child: UnifiedShareSheet(
            entityType: 'documents',
            entityId: doc.id,
            entityTitle: doc.title,
            presentation: SharePresentation.inlinePanel,
          ),
        ),
        if (doc.hasFile) ...[
          const SizedBox(height: 16),
          Container(
            width: double.infinity,
            padding: const EdgeInsets.all(14),
            decoration: BoxDecoration(
              color: Colors.blue.shade50,
              borderRadius: BorderRadius.circular(8),
              border: Border.all(color: Colors.blue.shade200),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Icon(Icons.description,
                        color: Colors.blue.shade700, size: 18),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        _pick('Có file Word đính kèm', 'Word file attached'),
                        style: TextStyle(
                          color: Colors.blue.shade700,
                          fontWeight: FontWeight.w600,
                          fontSize: 13,
                        ),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 10),
                SizedBox(
                  width: double.infinity,
                  child: OutlinedButton.icon(
                    onPressed: () => _downloadDocx(title: doc.title),
                    icon: const Icon(Icons.download, size: 14),
                    label: Text(_pick('Tải xuống Word', 'Download Word'),
                        style: TextStyle(fontSize: 13)),
                    style: OutlinedButton.styleFrom(
                      side: BorderSide(color: Colors.blue.shade400),
                      foregroundColor: Colors.blue.shade700,
                    ),
                  ),
                ),
              ],
            ),
          ),
        ],
        const SizedBox(height: 16),
        _CollapsibleSection(
          icon: Icons.edit_note_outlined,
          title: _pick('Chỉnh sửa thủ công', 'Manual edit'),
          accentColor: const Color(0xFF7C3AED),
          initiallyExpanded: false,
          child: DocumentManualEditCard(
            document: doc,
            onOpen: () => context.go('/documents/${doc.id}/manual-edit'),
          ),
        ),
        const SizedBox(height: 16),
        _CollapsibleSection(
          icon: Icons.auto_fix_high,
          title: _pick('Chỉnh sửa bằng Word AI', 'Edit with Word AI'),
          accentColor: const Color(0xFF1D4ED8),
          initiallyExpanded: true,
          child: DocumentAiEditPanel(
            documentId: doc.id as int,
            canEdit: doc.canEdit as bool,
            disabledReason: doc.manualEditActive == true
                ? doc.manualEditLockMessage as String?
                : null,
          ),
        ),
        const SizedBox(height: 16),
        WordEditHistoryPanel(
          documentId: doc.id as int,
          onDocumentChanged: _refreshAfterWordAiCompletion,
        ),
        // Lịch sử phiên bản đã được tách hẳn sang tab riêng (giống màn chi tiết mẫu).
      ],
    );
  }

  // Nhãn trạng thái chia sẻ/phê duyệt của văn bản.

  String _shareStatusLabel(String status) {
    return switch (status) {
      'active' => _pick('Đang chia sẻ', 'Shared'),
      'pending_leader' => _pick('Chờ trưởng nhóm', 'Waiting for team leader'),
      'pending_admin' => _pick('Chờ quản trị', 'Waiting for admin'),
      'rejected' => _pick('Bị từ chối', 'Rejected'),
      _ => _pick('Không chia sẻ', 'Not shared'),
    };
  }
}

// Widget dòng thông tin (nhãn + giá trị) dùng trong panel chi tiết.

class _InfoRow extends StatelessWidget {
  final String label;
  final String value;
  const _InfoRow(this.label, this.value);

  @override
  // Dựng 1 dòng thông tin: nhãn bên trái, giá trị bên phải.

  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 100,
            child: Text(label,
                style: TextStyle(color: Colors.grey.shade600, fontSize: 12.5)),
          ),
          Expanded(
            child: Text(value,
                style: const TextStyle(
                    fontSize: 12.5, fontWeight: FontWeight.w500)),
          ),
        ],
      ),
    );
  }
}

// Mô hình 1 dòng nhập người ký (controller họ tên/email) trong dialog khởi tạo ký.

class _SignerDraftRow {
  int? userId;
  bool required = true;
  final TextEditingController signerCtrl;
  final TextEditingController roleCtrl;
  final TextEditingController stepCtrl;
  final TextEditingController groupCtrl;

  // Dòng nhập 1 người ký trong khối soạn nhiệm vụ ký.
  _SignerDraftRow({
    String signerLabel = '',
    String role = '',
    String step = '1',
    String groupContext = '',
  })  : signerCtrl = TextEditingController(text: signerLabel),
        roleCtrl = TextEditingController(text: role),
        stepCtrl = TextEditingController(text: step),
        groupCtrl = TextEditingController(text: groupContext);

  // Giải phóng các controller của dòng người ký.

  void dispose() {
    signerCtrl.dispose();
    roleCtrl.dispose();
    stepCtrl.dispose();
    groupCtrl.dispose();
  }
}

// Mô hình 1 dòng nhập người nhận forward (controller).

class _ForwardRecipientRow {
  int? userId;
  final TextEditingController recipientCtrl;

  // Dòng nhập 1 người nhận forward.
  _ForwardRecipientRow({
    String recipientLabel = '',
  }) : recipientCtrl = TextEditingController(text: recipientLabel);

  // Giải phóng các controller của dòng người nhận forward.

  void dispose() {
    recipientCtrl.dispose();
  }
}

// Widget chip hiển thị 1 mẩu metadata (icon + nhãn) của văn bản.

class _MetaChip extends StatelessWidget {
  final IconData icon;
  final String label;
  final Color color;
  const _MetaChip(
      {required this.icon, required this.label, required this.color});

  @override
  // Dựng chip metadata (icon + nhãn).

  Widget build(BuildContext context) {
    final strings = AppStrings.of(context);
    return Row(mainAxisSize: MainAxisSize.min, children: [
      Icon(icon, size: 13, color: color),
      const SizedBox(width: 4),
      Text(strings.ui(label), style: TextStyle(fontSize: 12.5, color: color)),
    ]);
  }
}

// Widget badge trạng thái văn bản (nháp/hoàn tất/lưu trữ...).

class _StatusBadge extends StatelessWidget {
  final String status;
  const _StatusBadge({required this.status});

  @override
  // Dựng badge trạng thái với màu theo trạng thái.

  Widget build(BuildContext context) {
    final strings = AppStrings.of(context);
    final (label, color) = switch (status) {
      'final' => (strings.pick('Chính thức', 'Final'), Colors.green),
      'archived' => (strings.pick('Lưu trữ', 'Archived'), Colors.grey),
      _ => (strings.pick('Nháp', 'Draft'), Colors.orange),
    };
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
      decoration: BoxDecoration(
        color: color.withOpacity(0.1),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: color.withOpacity(0.4)),
      ),
      child: Text(label,
          style: TextStyle(
              fontSize: 11.5, color: color, fontWeight: FontWeight.w600)),
    );
  }
}

// Widget badge phạm vi hiển thị (riêng tư/nhóm/công khai).

class _VisibilityBadge extends StatelessWidget {
  final String visibility;
  const _VisibilityBadge({required this.visibility});

  @override
  // Dựng badge phạm vi hiển thị.

  Widget build(BuildContext context) {
    final strings = AppStrings.of(context);
    final (label, icon, color) = switch (visibility) {
      'public' => (
          strings.pick('Chia sẻ công khai', 'Publicly shared'),
          Icons.public,
          Colors.teal
        ),
      'group' => (
          strings.pick('Chia sẻ trong nhóm', 'Shared in group'),
          Icons.group,
          Colors.blue
        ),
      _ => (
          strings.pick('Chỉ mình tôi', 'Private'),
          Icons.lock_outline,
          Colors.grey
        ),
    };
    return Row(mainAxisSize: MainAxisSize.min, children: [
      Icon(icon, size: 13, color: color),
      const SizedBox(width: 4),
      Text(label, style: TextStyle(fontSize: 12.5, color: color)),
    ]);
  }
}

// Widget badge trạng thái chia sẻ/phê duyệt.

class _ShareStatusBadge extends StatelessWidget {
  final String shareStatus;
  const _ShareStatusBadge({required this.shareStatus});

  @override
  // Dựng badge trạng thái chia sẻ.

  Widget build(BuildContext context) {
    if (shareStatus == 'active') return const SizedBox.shrink();
    final strings = AppStrings.of(context);
    final (label, color) = switch (shareStatus) {
      'pending_leader' => (
          strings.pick(
              'Chờ trưởng nhóm duyệt', 'Waiting for team lead approval'),
          Colors.amber
        ),
      'pending_admin' => (
          strings.pick('Chờ Admin duyệt', 'Waiting for admin approval'),
          Colors.orange
        ),
      'rejected' => (strings.pick('Bị từ chối', 'Rejected'), Colors.red),
      _ => ('', Colors.transparent),
    };
    if (label.isEmpty) return const SizedBox.shrink();
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
      decoration: BoxDecoration(
        color: color.withOpacity(0.1),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: color.withOpacity(0.4)),
      ),
      child: Text(label,
          style: TextStyle(
              fontSize: 11.5, color: color, fontWeight: FontWeight.w600)),
    );
  }
}

// ─── Share dialog helper widgets ────────────────────────────────────────────

// Widget 1 lựa chọn chia sẻ (icon + mô tả) trong sheet chia sẻ.

class _ShareOption extends StatelessWidget {
  final IconData icon;
  final Color iconColor;
  final String title;
  final String subtitle;
  final bool selected;
  final VoidCallback onTap;

  const _ShareOption({
    required this.icon,
    required this.iconColor,
    required this.title,
    required this.subtitle,
    required this.selected,
    required this.onTap,
  });

  @override
  // Dựng 1 lựa chọn chia sẻ.

  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 150),
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
        decoration: BoxDecoration(
          color: selected ? iconColor.withOpacity(0.06) : Colors.grey.shade50,
          borderRadius: BorderRadius.circular(8),
          border: Border.all(
            color: selected ? iconColor : Colors.grey.shade300,
            width: selected ? 1.5 : 1,
          ),
        ),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Icon(icon,
                size: 18, color: selected ? iconColor : Colors.grey.shade500),
            const SizedBox(width: 10),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(title,
                      style: TextStyle(
                        fontSize: 13,
                        fontWeight: FontWeight.w600,
                        color: selected ? iconColor : Colors.black87,
                      )),
                  const SizedBox(height: 2),
                  Text(
                    subtitle,
                    style:
                        TextStyle(fontSize: 11.5, color: Colors.grey.shade600),
                  ),
                ],
              ),
            ),
            Radio<bool>(
              value: true,
              groupValue: selected,
              onChanged: (_) => onTap(),
              materialTapTargetSize: MaterialTapTargetSize.shrinkWrap,
              visualDensity: VisualDensity.compact,
              activeColor: iconColor,
            ),
          ],
        ),
      ),
    );
  }
}

// Widget hiển thị ghi chú phê duyệt/từ chối.

class _ApprovalNote extends StatelessWidget {
  final IconData icon;
  final Color color;
  final Color bgColor;
  final Color borderColor;
  final String text;

  const _ApprovalNote({
    required this.icon,
    required this.color,
    required this.bgColor,
    required this.borderColor,
    required this.text,
  });

  @override
  // Dựng khối ghi chú phê duyệt.

  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(10),
      decoration: BoxDecoration(
        color: bgColor,
        borderRadius: BorderRadius.circular(6),
        border: Border.all(color: borderColor),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(icon, size: 15, color: color),
          const SizedBox(width: 8),
          Expanded(
              child: Text(text, style: TextStyle(fontSize: 12, color: color))),
        ],
      ),
    );
  }
}

class _CollapsibleSection extends StatefulWidget {
  final IconData icon;
  final String title;
  final Color accentColor;
  final bool initiallyExpanded;
  final Widget child;

  const _CollapsibleSection({
    required this.icon,
    required this.title,
    required this.accentColor,
    required this.child,
    this.initiallyExpanded = true,
  });

  @override
  State<_CollapsibleSection> createState() => _CollapsibleSectionState();
}

class _CollapsibleSectionState extends State<_CollapsibleSection>
    with SingleTickerProviderStateMixin {
  late bool _expanded = widget.initiallyExpanded;

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: const Color(0xFFE2E8F0)),
        boxShadow: [
          BoxShadow(
            color: widget.accentColor.withOpacity(0.06),
            blurRadius: 8,
            offset: const Offset(0, 2),
          ),
        ],
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          InkWell(
            borderRadius: BorderRadius.vertical(
              top: const Radius.circular(13),
              bottom: Radius.circular(_expanded ? 0 : 13),
            ),
            onTap: () => setState(() => _expanded = !_expanded),
            child: Padding(
              padding: const EdgeInsets.fromLTRB(14, 12, 10, 12),
              child: Row(
                children: [
                  Container(
                    padding: const EdgeInsets.all(6),
                    decoration: BoxDecoration(
                      color: widget.accentColor.withOpacity(0.13),
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child:
                        Icon(widget.icon, size: 16, color: widget.accentColor),
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Text(
                      widget.title,
                      style: const TextStyle(
                        fontSize: 14,
                        fontWeight: FontWeight.w800,
                        color: Color(0xFF0F172A),
                      ),
                    ),
                  ),
                  AnimatedRotation(
                    turns: _expanded ? 0.5 : 0,
                    duration: const Duration(milliseconds: 200),
                    child: Icon(
                      Icons.keyboard_arrow_down_rounded,
                      color: widget.accentColor,
                      size: 22,
                    ),
                  ),
                ],
              ),
            ),
          ),
          AnimatedSize(
            duration: const Duration(milliseconds: 220),
            curve: Curves.easeInOut,
            child: _expanded
                ? Padding(
                    padding: const EdgeInsets.fromLTRB(14, 0, 14, 14),
                    child: widget.child,
                  )
                : const SizedBox(width: double.infinity, height: 0),
          ),
        ],
      ),
    );
  }
}
