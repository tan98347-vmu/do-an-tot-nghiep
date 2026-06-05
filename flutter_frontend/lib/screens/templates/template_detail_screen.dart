// Tệp này dùng để: dựng giao diện và orchestration UI trong flutter_frontend/lib/screens/templates/template_detail_screen.dart.
// Cách hoạt động: nhận state từ provider, dựng widget, phản ứng sự kiện và gửi thao tác ngược về backend khi người dùng tương tác.
// Vai trò trong hệ thống: Đây là màn hình Flutter mà người dùng tương tác trực tiếp.
// Tác dụng khi hệ thống vận hành: biến nghiệp vụ backend thành trải nghiệm thao tác cụ thể trên web.

import 'dart:async';
import 'dart:html' as html;
import 'dart:typed_data';
import 'dart:ui_web' as ui;
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:dio/dio.dart';
import '../../core/api_client.dart';
import '../../core/iframe_blocker.dart';
import '../../l10n/app_strings.dart';
import '../../providers/templates_provider.dart';
import '../../providers/auth_provider.dart';
import '../../providers/notifications_provider.dart';
import '../../widgets/pdf/web_pdf_frame.dart';
import '../../widgets/sharing/unified_share_sheet.dart';

// Mục đích: Widget `TemplateDetailScreen` triển khai phần việc `Template Detail Screen` trong flutter_frontend/lib/screens/templates/template_detail_screen.dart.
// Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
// Vai trò trong hệ thống: Đây là widget thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
// Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

class TemplateDetailScreen extends ConsumerStatefulWidget {
  final int id;
  const TemplateDetailScreen({super.key, required this.id});

  @override
  ConsumerState<TemplateDetailScreen> createState() =>
      _TemplateDetailScreenState();
}

// Mục đích: Widget `_TemplateDetailScreenState` triển khai phần việc `Template Detail Screen State` trong flutter_frontend/lib/screens/templates/template_detail_screen.dart.
// Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
// Vai trò trong hệ thống: Đây là widget thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
// Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

class _TemplateDetailScreenState extends ConsumerState<TemplateDetailScreen>
    with SingleTickerProviderStateMixin {
  late final TabController _tabController;
  bool _actionLoading = false;
  String? _lastMarkedReviewToken;
  int? _lastMarkedNotificationTemplateId;

  AppStrings get _strings => AppStrings.of(context);

  String _pick(String vi, String en) => _strings.pick(vi, en);

  // Preview form controllers
  final Map<String, TextEditingController> _previewControllers = {};

  // Content HTML lazy load
  String? _contentHtml;
  String? _previewPdfUrl;
  String? _previewNotice;
  String? _previewLoadError;
  bool _contentLoading = false;
  int _contentIframeKey = 0;
  final Set<String> _registeredPreviewViewKeys = <String>{};
  Timer? _previewAutoReloadTimer;
  Future<void> Function()? _previewAutoReloadAction;

  // Mục đích: Phương thức `_revokePreviewPdfUrl` triển khai phần việc `revoke Preview Pdf Url` trong flutter_frontend/lib/screens/templates/template_detail_screen.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  void _revokePreviewPdfUrl() {
    final current = _previewPdfUrl;
    if (current == null || current.isEmpty) return;
    html.Url.revokeObjectUrl(current);
    _previewPdfUrl = null;
  }

  void _stopPreviewAutoReload() {
    _previewAutoReloadTimer?.cancel();
    _previewAutoReloadTimer = null;
    _previewAutoReloadAction = null;
  }

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

  // Mục đích: Phương thức `_openPreviewPdfInNewTab` triển khai phần việc `open Preview Pdf In New Tab` trong flutter_frontend/lib/screens/templates/template_detail_screen.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  void _openPreviewPdfInNewTab() {
    final current = _previewPdfUrl;
    if (current == null || current.isEmpty) return;
    html.window.open(current, '_blank');
  }

  // Mục đích: Phương thức `_resetTemplatePreviewState` triển khai phần việc `reset Template Preview State` trong flutter_frontend/lib/screens/templates/template_detail_screen.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  void _resetTemplatePreviewState() {
    _stopPreviewAutoReload();
    _revokePreviewPdfUrl();
    _contentHtml = null;
    _previewNotice = null;
    _previewLoadError = null;
    _contentLoading = false;
    _contentIframeKey += 1;
  }

  String _templatePreviewRevisionToken(tmpl) {
    final updatedAt = tmpl.updatedAt?.toString() ?? '';
    final sourceType = tmpl.sourceType?.toString() ?? '';
    final hasDocxSource = tmpl.hasDocxSource == true ? '1' : '0';
    return '$updatedAt:$sourceType:$hasDocxSource';
  }

  Map<String, dynamic> _templatePreviewQuery(tmpl) {
    return <String, dynamic>{
      'rev': _templatePreviewRevisionToken(tmpl),
      'ts': DateTime.now().millisecondsSinceEpoch.toString(),
    };
  }

  // Mục đích: Phương thức `_refreshTemplateCollections` triển khai phần việc `refresh Template Collections` trong flutter_frontend/lib/screens/templates/template_detail_screen.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  void _refreshTemplateCollections() {
    ref.invalidate(templateDetailProvider(widget.id));
    ref.invalidate(templatesProvider(''));
    ref.invalidate(templatesProvider('private'));
    ref.invalidate(templatesProvider('team'));
    ref.invalidate(templatesProvider('system'));
    ref.invalidate(templatesProvider('favorite'));
  }

  // Mục đích: Phương thức `_reviewStorageKey` triển khai phần việc `review Storage Key` trong flutter_frontend/lib/screens/templates/template_detail_screen.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  String _reviewStorageKey(int templateId) =>
      'template_review_seen:$templateId';

  String? _reviewTokenForTemplate(dynamic tmpl) {
    final action = tmpl.lastReviewAction as String?;
    final at = tmpl.lastReviewAt as String?;
    if (action == null || at == null || at.isEmpty) return null;
    if (action != 'approve' && action != 'reject') return null;
    return '$action@$at';
  }

  // Mục đích: Phương thức `_hasUnreadReviewForOwner` triển khai phần việc `has Unread Review For Owner` trong flutter_frontend/lib/screens/templates/template_detail_screen.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  bool _hasUnreadReviewForOwner(dynamic tmpl, dynamic user) {
    if (user == null || user.id != tmpl.ownerId) return false;
    final token = _reviewTokenForTemplate(tmpl);
    if (token == null) return false;
    return html.window.localStorage[_reviewStorageKey(tmpl.id)] != token;
  }

  // Mục đích: Phương thức `_markReviewSeen` triển khai phần việc `mark Review Seen` trong flutter_frontend/lib/screens/templates/template_detail_screen.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  void _markReviewSeen(dynamic tmpl, dynamic user) {
    if (user == null || user.id != tmpl.ownerId) return;
    final token = _reviewTokenForTemplate(tmpl);
    if (token == null || token == _lastMarkedReviewToken) return;
    html.window.localStorage[_reviewStorageKey(tmpl.id)] = token;
    _lastMarkedReviewToken = token;
  }

  // Mục đích: Phương thức `_markTemplateNotificationsRead` triển khai phần việc `mark Template Notifications Read` trong flutter_frontend/lib/screens/templates/template_detail_screen.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  void _markTemplateNotificationsRead(dynamic tmpl, dynamic user) {
    if (user == null || user.id != tmpl.ownerId) return;
    if (_lastMarkedNotificationTemplateId == tmpl.id) return;
    _lastMarkedNotificationTemplateId = tmpl.id;
    ApiClient().dio.post(
      'notifications/read-template/',
      data: {'template_id': tmpl.id},
    ).then((_) {
      if (!mounted) return;
      ref.invalidate(unreadNotificationCountProvider);
      ref.invalidate(templateDetailProvider(widget.id));
      ref.invalidate(templatesProvider(''));
      ref.invalidate(templatesProvider('private'));
      ref.invalidate(templatesProvider('team'));
      ref.invalidate(templatesProvider('system'));
      ref.invalidate(templatesProvider('favorite'));
    }).catchError((_) {});
  }

  String? _reviewSummary(dynamic tmpl) {
    final action = tmpl.lastReviewAction as String?;
    if (action == null) return null;
    final actor = (tmpl.lastReviewActorName as String?)?.trim();
    final rawAt = (tmpl.lastReviewAt as String?)?.trim();
    final at =
        rawAt != null && rawAt.length >= 10 ? rawAt.substring(0, 10) : rawAt;
    switch (action) {
      case 'approve':
        return _pick(
          'Cập nhật gần nhất: ${actor?.isNotEmpty == true ? actor : 'Hệ thống'} đã duyệt${at != null && at.isNotEmpty ? ' ngày $at' : ''}.',
          'Latest update: ${actor?.isNotEmpty == true ? actor : 'System'} approved${at != null && at.isNotEmpty ? ' on $at' : ''}.',
        );
      case 'reject':
        return _pick(
          'Cập nhật gần nhất: ${actor?.isNotEmpty == true ? actor : 'Hệ thống'} đã từ chối${at != null && at.isNotEmpty ? ' ngày $at' : ''}.',
          'Latest update: ${actor?.isNotEmpty == true ? actor : 'System'} rejected${at != null && at.isNotEmpty ? ' on $at' : ''}.',
        );
      case 'submit':
        return _pick(
          'Đã gửi duyệt${at != null && at.isNotEmpty ? ' ngày $at' : ''}.',
          'Submitted for approval${at != null && at.isNotEmpty ? ' on $at' : ''}.',
        );
      default:
        return null;
    }
  }

  // Mục đích: Phương thức `_previewNoticeFromError` triển khai phần việc `preview Notice From Error` trong flutter_frontend/lib/screens/templates/template_detail_screen.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  String _previewNoticeFromError(Object error) {
    if (error is DioException) {
      final data = error.response?.data;
      if (data is Map && data['detail'] != null) {
        return '${data['detail']} ${_pick('Đang chuyển sang chế độ HTML.', 'Switching to HTML mode.')}';
      }
      return _pick(
        'Không tạo được bản xem PDF cho mẫu. Đang chuyển sang chế độ HTML.',
        'Unable to generate the template PDF preview. Switching to HTML mode.',
      );
    }
    return _pick(
      'Không tạo được bản xem PDF cho mẫu. Đang chuyển sang chế độ HTML.',
      'Unable to generate the template PDF preview. Switching to HTML mode.',
    );
  }

  // Mục đích: Phương thức `_previewLoadErrorMessage` triển khai phần việc `preview Load Error Message` trong flutter_frontend/lib/screens/templates/template_detail_screen.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  String _previewLoadErrorMessage(Object error) {
    if (error is DioException) {
      final data = error.response?.data;
      if (data is Map && data['detail'] != null) return '${data['detail']}';
      return _pick(
        'Không tải được nội dung mẫu văn bản (${error.response?.statusCode ?? 'network'}).',
        'Unable to load the template content (${error.response?.statusCode ?? 'network'}).',
      );
    }
    return _pick(
      'Không tải được nội dung mẫu văn bản: $error',
      'Unable to load the template content: $error',
    );
  }

  // Mục đích: Phương thức `_loadTemplateContentPreview` triển khai phần việc `load Template Content Preview` trong flutter_frontend/lib/screens/templates/template_detail_screen.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  Future<void> _loadTemplateContentPreview(tmpl, {bool force = false}) async {
    if (_contentLoading) return;
    if (!force && (_previewPdfUrl != null || _contentHtml != null)) return;
    // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

    setState(() => _contentLoading = true);
    try {
      String? nextPdfUrl;
      String? nextHtml;
      String? nextNotice;

      final hasContent =
          tmpl.content != null && (tmpl.content as String).isNotEmpty;
      final hasDocx = tmpl.sourceType == 'docx';
      final hasDocxSource = tmpl.hasDocxSource == true;

      if (hasContent || hasDocxSource || hasDocx) {
        try {
          // Gọi API hoặc tác vụ bất đồng bộ rồi chờ kết quả trước khi cập nhật giao diện.

          final pdfResp = await ApiClient().dio.get(
                'templates/${widget.id}/preview-pdf/',
                queryParameters: _templatePreviewQuery(tmpl),
                options: Options(responseType: ResponseType.bytes),
              );
          final bytes = List<int>.from(pdfResp.data as List);
          final pdfBytes = Uint8List.fromList(bytes);
          final blob = html.Blob([pdfBytes], 'application/pdf');
          nextPdfUrl = html.Url.createObjectUrlFromBlob(blob);
          debugPrint(
            '[template_preview] pdf_ready | template_id=${widget.id} | bytes=${pdfBytes.length} | status=${pdfResp.statusCode} | content_type=${pdfResp.headers.value('content-type')} | blob_url=$nextPdfUrl',
          );
        } catch (error) {
          debugPrint(
              '[template_preview] pdf_failed | template_id=${widget.id} | error=$error');
          nextNotice = _previewNoticeFromError(error);
        }
      } else if (hasDocx && !hasDocxSource) {
        nextNotice = _pick(
          'Mẫu DOCX này không còn file DOCX gốc. Hệ thống đang hiển thị bản xem HTML từ nội dung đã lưu.',
          'This DOCX template no longer has its original DOCX file. The system is showing an HTML preview from the saved content.',
        );
      }

      if (nextPdfUrl == null && (hasContent || hasDocx)) {
        // Gọi API hoặc tác vụ bất đồng bộ rồi chờ kết quả trước khi cập nhật giao diện.

        final resp = await ApiClient().dio.get(
              'templates/${widget.id}/content-html/',
              queryParameters: _templatePreviewQuery(tmpl),
            );
        nextHtml = resp.data['html'] as String? ?? '';
        debugPrint(
          '[template_preview] html_fallback | template_id=${widget.id} | html_chars=${nextHtml.length}',
        );
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
        _previewLoadError = null;
        _contentLoading = false;
        _contentIframeKey += 1;
      });
      if (nextPdfUrl != null && nextPdfUrl.isNotEmpty) {
        _restartPreviewAutoReload(
            () => _loadTemplateContentPreview(tmpl, force: true));
      } else {
        _stopPreviewAutoReload();
      }
      debugPrint(
        '[template_preview] state_ready | template_id=${widget.id} | has_pdf=${nextPdfUrl != null && nextPdfUrl.isNotEmpty} | has_html=${nextHtml != null && nextHtml.isNotEmpty} | iframe_key=$_contentIframeKey | notice=${nextNotice ?? ''}',
      );
    } catch (error) {
      debugPrint(
          '[template_preview] load_failed | template_id=${widget.id} | error=$error');
      if (!mounted) return;
      _stopPreviewAutoReload();
      // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

      setState(() {
        _contentLoading = false;
        _previewLoadError = _previewLoadErrorMessage(error);
      });
    }
  }

  @override
  // Mục đích: Phương thức `initState` triển khai phần việc `init State` trong flutter_frontend/lib/screens/templates/template_detail_screen.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  void initState() {
    super.initState();
    _tabController = TabController(length: 2, vsync: this);
  }

  @override
  // Mục đích: Phương thức `didUpdateWidget` triển khai phần việc `did Update Widget` trong flutter_frontend/lib/screens/templates/template_detail_screen.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  void didUpdateWidget(covariant TemplateDetailScreen oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.id == widget.id) return;
    _resetTemplatePreviewState();
  }

  @override
  // Mục đích: Phương thức `dispose` triển khai phần việc `dispose` trong flutter_frontend/lib/screens/templates/template_detail_screen.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  void dispose() {
    _stopPreviewAutoReload();
    _revokePreviewPdfUrl();
    _tabController.dispose();
    for (final c in _previewControllers.values) {
      c.dispose();
    }
    super.dispose();
  }

  // Mục đích: Phương thức `_readerHtml` triển khai phần việc `reader Html` trong flutter_frontend/lib/screens/templates/template_detail_screen.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

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

  // Mục đích: Phương thức `_buildTemplateHtmlFrame` triển khai phần việc `build Template Html Frame` trong flutter_frontend/lib/screens/templates/template_detail_screen.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  Widget _buildTemplateHtmlFrame({
    required String htmlContent,
    required bool isCompact,
    required bool fullScreen,
  }) {
    final viewKey =
        'tmpl-content-${widget.id}-${isCompact ? 'compact' : 'full'}-$fullScreen-$_contentIframeKey';
    if (_registeredPreviewViewKeys.add(viewKey)) {
      ui.platformViewRegistry.registerViewFactory(viewKey, (int viewId) {
        return html.IFrameElement()
          ..style.border = 'none'
          ..style.width = '100%'
          ..style.height = '100%'
          ..srcdoc = _readerHtml(htmlContent, isCompact: isCompact);
      });
    }
    return IframeBlocker(child: HtmlElementView(viewType: viewKey));
  }

  // Mục đích: Phương thức `_buildTemplatePdfFrame` triển khai phần việc `build Template Pdf Frame` trong flutter_frontend/lib/screens/templates/template_detail_screen.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  Widget _buildTemplatePdfFrame({
    required String pdfUrl,
    required bool fullScreen,
  }) {
    final viewKey = 'tmpl-pdf-${widget.id}-$fullScreen-$_contentIframeKey';
    return WebPdfFrame(
      viewKey: viewKey,
      pdfUrl: pdfUrl,
    );
  }

  // Mục đích: Phương thức `_openTemplateContentPreviewDialog` triển khai phần việc `open Template Content Preview Dialog` trong flutter_frontend/lib/screens/templates/template_detail_screen.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  Future<void> _openTemplateContentPreviewDialog(tmpl) async {
    await _loadTemplateContentPreview(tmpl, force: true);
    if ((_previewPdfUrl == null || _previewPdfUrl!.isEmpty) &&
        (_contentHtml == null || _contentHtml!.isEmpty)) {
      return;
    }
    final isCompact = MediaQuery.of(context).size.width < 900;
    _contentIframeKey += 1;
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
                        'Xem toan man hinh',
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
                      ? _buildTemplatePdfFrame(
                          pdfUrl: _previewPdfUrl!,
                          fullScreen: true,
                        )
                      : _buildTemplateHtmlFrame(
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

  // Mục đích: Phương thức `_toggleFavorite` triển khai phần việc `toggle Favorite` trong flutter_frontend/lib/screens/templates/template_detail_screen.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  Future<void> _toggleFavorite(int tmplId, bool isFav) async {
    try {
      // Gọi API hoặc tác vụ bất đồng bộ rồi chờ kết quả trước khi cập nhật giao diện.

      await ApiClient().dio.post('templates/$tmplId/favorite/');
      ref.invalidate(templateDetailProvider(tmplId));
    } catch (e) {
      if (mounted) _showSnack('Lỗi: $e', error: true);
    }
  }

  // Mục đích: Phương thức `_exportDocx` triển khai phần việc `export Docx` trong flutter_frontend/lib/screens/templates/template_detail_screen.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  Future<void> _exportDocx(tmpl) async {
    if (tmpl.sourceType == 'docx' && tmpl.hasDocxSource != true) {
      _showSnack(
        'Mau DOCX nay khong con file DOCX goc. Hay upload lai file goc de tai xuong dung dinh dang Word.',
        error: true,
      );
      return;
    }
    try {
      // Gọi API hoặc tác vụ bất đồng bộ rồi chờ kết quả trước khi cập nhật giao diện.

      final resp = await ApiClient().dio.get(
            'templates/${tmpl.id}/export/',
            options: Options(responseType: ResponseType.bytes),
          );
      final bytes = resp.data as List<int>;
      final blob = html.Blob(
        [bytes],
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
      );
      final url = html.Url.createObjectUrlFromBlob(blob);
      html.AnchorElement(href: url)
        ..setAttribute('download', '${tmpl.title}.docx')
        ..click();
      html.Url.revokeObjectUrl(url);
    } catch (e) {
      if (mounted) _showSnack('Lỗi xuất DOCX: $e', error: true);
    }
  }

  // Mục đích: Phương thức `_delete` triển khai phần việc `delete` trong flutter_frontend/lib/screens/templates/template_detail_screen.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  Future<void> _delete(int tmplId) async {
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text(_pick('Xác nhận xóa', 'Confirm deletion')),
        content: Text(_pick(
          'Bạn có chắc muốn xóa mẫu văn bản này? Hành động này không thể hoàn tác.',
          'Are you sure you want to delete this template? This action cannot be undone.',
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
    await _performDelete(tmplId, force: false);
  }

  Future<void> _performDelete(int tmplId, {required bool force}) async {
    try {
      await ApiClient().dio.delete(
            'templates/$tmplId/',
            queryParameters: force ? {'force': 'true'} : null,
          );
      if (mounted) context.go('/templates');
    } on DioException catch (e) {
      // 409 = mẫu đang được dùng trong các văn bản đã sinh -> hỏi xác nhận xóa.
      if (e.response?.statusCode == 409 && !force) {
        final data = e.response?.data;
        final usage = (data is Map ? data['usage_count'] : null);
        if (!mounted) return;
        final confirmForce = await showDialog<bool>(
          context: context,
          builder: (ctx) => AlertDialog(
            title: Text(_pick('Mẫu đang được sử dụng', 'Template in use')),
            content: Text(_pick(
              'Mẫu này đang được dùng trong ${usage ?? 'một số'} văn bản đã sinh. '
                  'Các văn bản đã tạo sẽ không bị ảnh hưởng. Bạn vẫn muốn xóa mẫu?',
              'This template is used by ${usage ?? 'some'} generated document(s). '
                  'Existing documents are not affected. Delete anyway?',
            )),
            actions: [
              TextButton(
                onPressed: () => Navigator.pop(ctx, false),
                child: Text(_pick('Hủy', 'Cancel')),
              ),
              FilledButton(
                onPressed: () => Navigator.pop(ctx, true),
                style: FilledButton.styleFrom(backgroundColor: Colors.red),
                child: Text(_pick('Vẫn xóa', 'Delete anyway')),
              ),
            ],
          ),
        );
        if (confirmForce == true) {
          await _performDelete(tmplId, force: true);
        }
        return;
      }
      if (mounted) {
        _showSnack('${_pick('Lỗi', 'Error')}: ${e.message}', error: true);
      }
    } catch (e) {
      if (mounted) {
        _showSnack('${_pick('Lỗi', 'Error')}: $e', error: true);
      }
    }
  }

  // Mục đích: Phương thức `_submitForApproval` triển khai phần việc `submit For Approval` trong flutter_frontend/lib/screens/templates/template_detail_screen.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  Future<void> _submitForApproval(int tmplId) async {
    final noteCtrl = TextEditingController();
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text(_pick('Gửi duyệt', 'Submit for approval')),
        content: TextField(
          controller: noteCtrl,
          decoration: InputDecoration(
              labelText: _pick('Ghi chú (tùy chọn)', 'Note (optional)')),
          maxLines: 3,
        ),
        actions: [
          TextButton(
              onPressed: () => Navigator.pop(ctx, false),
              child: Text(_pick('Hủy', 'Cancel'))),
          FilledButton(
              onPressed: () => Navigator.pop(ctx, true),
              child: Text(_pick('Gửi', 'Submit'))),
        ],
      ),
    );
    if (ok != true) {
      noteCtrl.dispose();
      return;
    }
    final note = noteCtrl.text.trim();
    noteCtrl.dispose();
    // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

    setState(() => _actionLoading = true);
    try {
      // Gọi API hoặc tác vụ bất đồng bộ rồi chờ kết quả trước khi cập nhật giao diện.

      await ApiClient()
          .dio
          .post('templates/$tmplId/submit/', data: {'note': note});
      _refreshTemplateCollections();
      if (mounted)
        _showSnack(_pick('Đã gửi yêu cầu duyệt.', 'Approval request sent.'));
    } catch (e) {
      if (mounted) _showSnack('${_pick('Lỗi', 'Error')}: $e', error: true);
    } finally {
      // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

      if (mounted) setState(() => _actionLoading = false);
    }
  }

  // Mục đích: Phương thức `_approve` triển khai phần việc `approve` trong flutter_frontend/lib/screens/templates/template_detail_screen.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  Future<void> _approve(int tmplId) async {
    final noteCtrl = TextEditingController();
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text(_pick('Phê duyệt mẫu', 'Approve template')),
        content: TextField(
          controller: noteCtrl,
          decoration: InputDecoration(
              labelText: _pick('Nhận xét (tùy chọn)', 'Comment (optional)')),
          maxLines: 3,
        ),
        actions: [
          TextButton(
              onPressed: () => Navigator.pop(ctx, false),
              child: Text(_pick('Hủy', 'Cancel'))),
          FilledButton(
            onPressed: () => Navigator.pop(ctx, true),
            style: FilledButton.styleFrom(backgroundColor: Colors.green),
            child: Text(_pick('Duyệt', 'Approve')),
          ),
        ],
      ),
    );
    if (ok != true) {
      noteCtrl.dispose();
      return;
    }
    final note = noteCtrl.text.trim();
    noteCtrl.dispose();
    // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

    setState(() => _actionLoading = true);
    try {
      // Gọi API hoặc tác vụ bất đồng bộ rồi chờ kết quả trước khi cập nhật giao diện.

      await ApiClient()
          .dio
          .post('templates/$tmplId/approve/', data: {'approver_note': note});
      _refreshTemplateCollections();
      if (mounted) _showSnack(_pick('Đã phê duyệt mẫu.', 'Template approved.'));
    } catch (e) {
      if (mounted) _showSnack('${_pick('Lỗi', 'Error')}: $e', error: true);
    } finally {
      // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

      if (mounted) setState(() => _actionLoading = false);
    }
  }

  // Mục đích: Phương thức `_reject` triển khai phần việc `reject` trong flutter_frontend/lib/screens/templates/template_detail_screen.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  Future<void> _reject(int tmplId) async {
    final reasonCtrl = TextEditingController();
    String? err;
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx2, setS) => AlertDialog(
          title: Text(_pick('Từ chối mẫu', 'Reject template')),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              TextField(
                controller: reasonCtrl,
                decoration: InputDecoration(
                  labelText: _pick('Lý do từ chối *', 'Rejection reason *'),
                  errorText: err,
                ),
                maxLines: 3,
              ),
            ],
          ),
          actions: [
            TextButton(
                onPressed: () => Navigator.pop(ctx, false),
                child: Text(_pick('Hủy', 'Cancel'))),
            FilledButton(
              onPressed: () {
                if (reasonCtrl.text.trim().isEmpty) {
                  setS(() => err =
                      _pick('Vui lòng nhập lý do', 'Please enter a reason'));
                  return;
                }
                Navigator.pop(ctx, true);
              },
              style: FilledButton.styleFrom(backgroundColor: Colors.red),
              child: Text(_pick('Từ chối', 'Reject')),
            ),
          ],
        ),
      ),
    );
    if (ok != true) {
      reasonCtrl.dispose();
      return;
    }
    final reason = reasonCtrl.text;
    reasonCtrl.dispose();
    // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

    setState(() => _actionLoading = true);
    try {
      // Gọi API hoặc tác vụ bất đồng bộ rồi chờ kết quả trước khi cập nhật giao diện.

      await ApiClient()
          .dio
          .post('templates/$tmplId/reject/', data: {'approver_note': reason});
      _refreshTemplateCollections();
      if (mounted) {
        _showSnack(_pick('Đã từ chối mẫu.', 'Template rejected.'));
        // Sau khi từ chối, mẫu chuyển về riêng tư (group=None) nên người duyệt
        // (vd: trưởng nhóm) có thể không còn quyền xem chi tiết -> quay lại danh
        // sách để tránh màn hình trắng do tải lại chi tiết bị 403/404.
        if (context.canPop()) {
          context.pop();
        } else {
          context.go('/templates');
        }
      }
    } catch (e) {
      if (mounted) _showSnack('${_pick('Lỗi', 'Error')}: $e', error: true);
    } finally {
      // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

      if (mounted) setState(() => _actionLoading = false);
    }
  }

  // Mục đích: Phương thức `_restoreVersion` triển khai phần việc `restore Version` trong flutter_frontend/lib/screens/templates/template_detail_screen.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  Future<void> _restoreVersion(int tmplId, int verId) async {
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text(_pick('Khôi phục phiên bản', 'Restore version')),
        content: Text(_pick(
          'Khôi phục phiên bản này sẽ tạo một phiên bản mới từ nội dung cũ. Bạn có muốn tiếp tục?',
          'Restoring this version will create a new version from the old content. Do you want to continue?',
        )),
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

      await ApiClient().dio.post('templates/$tmplId/versions/$verId/restore/');
      _refreshTemplateCollections();
      ref.invalidate(templateVersionsProvider(tmplId));
      if (mounted)
        _showSnack(_pick('Đã khôi phục phiên bản.', 'Version restored.'));
    } catch (e) {
      if (mounted) _showSnack('${_pick('Lỗi', 'Error')}: $e', error: true);
    }
  }

  // Mục đích: Phương thức `_showSnack` triển khai phần việc `show Snack` trong flutter_frontend/lib/screens/templates/template_detail_screen.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  void _showSnack(String msg, {bool error = false}) {
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(
      content: Text(msg),
      backgroundColor: error ? Colors.red : Colors.green,
    ));
  }

  void _openManualEdit(int templateId, {String returnTo = 'detail'}) {
    context.go('/templates/$templateId/manual-edit?return_to=$returnTo');
  }

  // Mục đích: Phương thức `_buildTemplateContentView` triển khai phần việc `build Template Content View` trong flutter_frontend/lib/screens/templates/template_detail_screen.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  Widget _buildTemplateContentView(tmpl) {
    final hasContent =
        tmpl.content != null && (tmpl.content as String).isNotEmpty;
    final hasDocx = tmpl.sourceType == 'docx';
    final isCompact = MediaQuery.of(context).size.width < 900;
    final previewHeight =
        (MediaQuery.of(context).size.height * (isCompact ? 0.7 : 0.8))
            .clamp(isCompact ? 520.0 : 680.0, 1200.0)
            .toDouble();

    if (!hasContent && !hasDocx) {
      return Container(
        width: double.infinity,
        padding: const EdgeInsets.all(20),
        decoration: BoxDecoration(
          color: Colors.white,
          border: Border.all(color: Colors.grey.shade200),
          borderRadius: BorderRadius.circular(8),
        ),
        child: Text(
          _pick('Chưa có nội dung', 'No content yet'),
          style: TextStyle(color: Colors.grey.shade500),
        ),
      );
    }

    if (_previewPdfUrl == null &&
        _contentHtml == null &&
        !_contentLoading &&
        _previewLoadError == null) {
      WidgetsBinding.instance
          .addPostFrameCallback((_) => _loadTemplateContentPreview(tmpl));
    }

    if (_contentLoading) {
      return const SizedBox(
          height: 200, child: Center(child: CircularProgressIndicator()));
    }

    if (_previewLoadError != null) {
      return Container(
        width: double.infinity,
        padding: const EdgeInsets.all(18),
        decoration: BoxDecoration(
          color: const Color(0xFFFEF2F2),
          border: Border.all(color: const Color(0xFFFECACA)),
          borderRadius: BorderRadius.circular(14),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(
              _previewLoadError!,
              style: const TextStyle(color: Color(0xFF7F1D1D), height: 1.5),
            ),
            const SizedBox(height: 12),
            OutlinedButton.icon(
              onPressed: () => _loadTemplateContentPreview(tmpl, force: true),
              icon: const Icon(Icons.refresh, size: 16),
              label: Text(_pick('Tải lại PDF', 'Reload PDF')),
            ),
          ],
        ),
      );
    }

    if (_previewPdfUrl != null && _previewPdfUrl!.isNotEmpty) {
      return Column(
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
                        _previewNotice != null && _previewNotice!.isNotEmpty
                            ? _previewNotice!
                            : isCompact
                                ? 'Dang hien thi ban xem PDF toi uu cho man hinh doc.'
                                : 'Dang hien thi ban xem PDF giu bo cuc mau van ban gan voi file Word goc. He thong tu dong tai lai moi 10 giay.',
                        style: const TextStyle(
                            height: 1.45, color: Color(0xFF475569)),
                      ),
                      const SizedBox(height: 12),
                      Wrap(
                        spacing: 12,
                        runSpacing: 12,
                        children: [
                          if (_previewPdfUrl != null &&
                              _previewPdfUrl!.isNotEmpty)
                            OutlinedButton.icon(
                              onPressed: () => _loadTemplateContentPreview(tmpl,
                                  force: true),
                              icon: const Icon(Icons.refresh, size: 16),
                              label: Text(_pick('Tải lại', 'Reload')),
                            ),
                          if (_previewPdfUrl != null &&
                              _previewPdfUrl!.isNotEmpty)
                            OutlinedButton.icon(
                              onPressed: _openPreviewPdfInNewTab,
                              icon: const Icon(Icons.picture_as_pdf_outlined,
                                  size: 16),
                              label: Text(_pick('Mở PDF', 'Open PDF')),
                            ),
                          OutlinedButton.icon(
                            onPressed: () =>
                                _openTemplateContentPreviewDialog(tmpl),
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
          SizedBox(
            height: previewHeight,
            child: _buildTemplatePdfFrame(
              pdfUrl: _previewPdfUrl!,
              fullScreen: false,
            ),
          ),
        ],
      );
    }

    if (_contentHtml != null && _contentHtml!.isNotEmpty) {
      return Column(
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
              children: [
                Expanded(
                  child: Text(
                    _previewNotice != null && _previewNotice!.isNotEmpty
                        ? _previewNotice!
                        : 'Dang hien thi che do tuong thich HTML cho mau van ban nay.',
                    style:
                        const TextStyle(height: 1.45, color: Color(0xFF475569)),
                  ),
                ),
                const SizedBox(width: 12),
                OutlinedButton.icon(
                  onPressed: () => _openTemplateContentPreviewDialog(tmpl),
                  icon: const Icon(Icons.open_in_full, size: 16),
                  label: Text(_pick('Toàn màn hình', 'Full screen')),
                ),
              ],
            ),
          ),
          SizedBox(
            height: previewHeight,
            child: _buildTemplateHtmlFrame(
              htmlContent: _contentHtml!,
              isCompact: isCompact,
              fullScreen: false,
            ),
          ),
        ],
      );
    }

    return const SizedBox(
        height: 150, child: Center(child: CircularProgressIndicator()));
  }

  // Mục đích: Phương thức `_showPreviewDialog` triển khai phần việc `show Preview Dialog` trong flutter_frontend/lib/screens/templates/template_detail_screen.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  void _showPreviewDialog(
      BuildContext context, String title, List<String> variables) {
    // Build preview HTML with filled variables for the dialog
    _showIframePreviewDialog(context, title, variables);
  }

  // Mục đích: Phương thức `_showIframePreviewDialog` triển khai phần việc `show Iframe Preview Dialog` trong flutter_frontend/lib/screens/templates/template_detail_screen.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  Future<void> _showIframePreviewDialog(
      BuildContext context, String title, List<String> variables) async {
    // Show loading dialog, call preview API with variables filled
    final vars = <String, String>{};
    for (final v in variables) {
      vars[v] = _previewControllers[v]?.text ?? '';
    }
    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (ctx) => AlertDialog(
        content: Row(mainAxisSize: MainAxisSize.min, children: [
          const CircularProgressIndicator(),
          const SizedBox(width: 16),
          Text(_pick('Đang tải xem trước...', 'Loading preview...')),
        ]),
      ),
    );

    try {
      // Gọi API hoặc tác vụ bất đồng bộ rồi chờ kết quả trước khi cập nhật giao diện.

      final resp = await ApiClient().dio.post('ai/doc/preview/', data: {
        'template_id': widget.id,
        'variables': vars,
      });
      final htmlContent = resp.data['html'] as String? ?? '';
      if (!mounted) return;
      Navigator.pop(context); // close loading

      final viewKey =
          'tmpl-preview-${widget.id}-${DateTime.now().millisecondsSinceEpoch}';
      ui.platformViewRegistry.registerViewFactory(viewKey, (int viewId) {
        return html.IFrameElement()
          ..style.border = 'none'
          ..style.width = '100%'
          ..style.height = '100%'
          ..srcdoc = htmlContent;
      });

      showDialog(
        context: context,
        builder: (ctx) => Dialog(
          insetPadding: const EdgeInsets.all(16),
          child: SizedBox(
            width: double.infinity,
            height: MediaQuery.of(ctx).size.height * 0.92,
            child: Column(children: [
              Container(
                padding:
                    const EdgeInsets.symmetric(horizontal: 20, vertical: 14),
                decoration: BoxDecoration(
                  color: Theme.of(ctx).colorScheme.primary,
                  borderRadius:
                      const BorderRadius.vertical(top: Radius.circular(12)),
                ),
                child: Row(children: [
                  const Icon(Icons.preview_outlined,
                      color: Colors.white, size: 20),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Text('${_pick('Xem trước', 'Preview')}: $title',
                        style: const TextStyle(
                            color: Colors.white,
                            fontWeight: FontWeight.bold,
                            fontSize: 15),
                        overflow: TextOverflow.ellipsis),
                  ),
                  IconButton(
                    icon:
                        const Icon(Icons.close, color: Colors.white, size: 20),
                    onPressed: () => Navigator.pop(ctx),
                    padding: EdgeInsets.zero,
                    constraints: const BoxConstraints(),
                  ),
                ]),
              ),
              Expanded(child: IframeBlocker(child: HtmlElementView(viewType: viewKey))),
              Container(
                padding:
                    const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
                decoration: BoxDecoration(
                    border:
                        Border(top: BorderSide(color: Colors.grey.shade200))),
                child: Row(mainAxisAlignment: MainAxisAlignment.end, children: [
                  OutlinedButton(
                      onPressed: () => Navigator.pop(ctx),
                      child: Text(_pick('Đóng', 'Close'))),
                ]),
              ),
            ]),
          ),
        ),
      );
    } catch (e) {
      if (mounted) {
        Navigator.pop(context);
        _showSnack('${_pick('Lỗi tải xem trước', 'Preview load error')}: $e',
            error: true);
      }
    }
  }

  @override
  // Mục đích: Phương thức `build` triển khai phần việc `build` trong flutter_frontend/lib/screens/templates/template_detail_screen.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  Widget build(BuildContext context) {
    // Lắng nghe provider để widget tự động dựng lại khi dữ liệu hoặc trạng thái thay đổi.

    final asyncTmpl = ref.watch(templateDetailProvider(widget.id));
    // Lắng nghe provider để widget tự động dựng lại khi dữ liệu hoặc trạng thái thay đổi.

    final user = ref.watch(currentUserProvider);

    return asyncTmpl.when(
      // Dựng khung màn hình chính để chứa app bar, body, action và các vùng giao diện khác.

      loading: () =>
          const Scaffold(body: Center(child: CircularProgressIndicator())),
      // Dựng khung màn hình chính để chứa app bar, body, action và các vùng giao diện khác.

      error: (e, _) => Scaffold(
        body: Center(child: Text('${_pick('Lỗi', 'Error')}: $e')),
      ),
      data: (tmpl) {
        // Prepare preview controllers for variables
        for (final v in tmpl.variables) {
          _previewControllers.putIfAbsent(v, () => TextEditingController());
        }
        _markReviewSeen(tmpl, user);
        _markTemplateNotificationsRead(tmpl, user);

        final isSuperuser = user?.isSuperuser ?? false;
        final isOwner = user?.id == tmpl.ownerId;
        final canEdit = tmpl.canEdit;
        final canDelete = tmpl.canDelete;
        final isMobile = MediaQuery.sizeOf(context).width < 760;
        final query = GoRouterState.of(context).uri.queryParameters;
        final returnTo = query['return_to'];
        final returnLabel = query['return_label'] ??
            _pick('Quay về Chat AI', 'Back to AI Chat');

        // Dựng khung màn hình chính để chứa app bar, body, action và các vùng giao diện khác.

        return Scaffold(
          appBar: AppBar(
            leading: IconButton(
              icon: const Icon(Icons.arrow_back),
              // Điều hướng người dùng sang màn phù hợp theo kết quả thao tác hiện tại.

              onPressed: () => context.canPop()
                  ? context.pop()
                  : context.go(returnTo ?? '/templates'),
            ),
            title: isMobile
                ? Text(tmpl.title, overflow: TextOverflow.ellipsis)
                : Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Flexible(
                          child: Text(tmpl.title,
                              overflow: TextOverflow.ellipsis)),
                      const SizedBox(width: 8),
                      Container(
                        padding: const EdgeInsets.symmetric(
                            horizontal: 7, vertical: 2),
                        decoration: BoxDecoration(
                          color: Colors.blue.shade100,
                          borderRadius: BorderRadius.circular(10),
                        ),
                        child: Text('v${tmpl.version}',
                            style: TextStyle(
                                fontSize: 11,
                                color: Colors.blue.shade700,
                                fontWeight: FontWeight.w600)),
                      ),
                    ],
                  ),
            bottom: TabBar(
              controller: _tabController,
              isScrollable: isMobile,
              tabs: const [
                Tab(text: 'Nội dung'),
                Tab(text: 'Lịch sử phiên bản'),
              ],
            ),
            actions: [
              IconButton(
                icon: const Icon(Icons.share_outlined),
                tooltip: _pick('Chia sẻ', 'Share'),
                onPressed: () async {
                  await UnifiedShareSheet.showDialogPresentation(
                    context,
                    entityType: 'templates',
                    entityId: tmpl.id,
                    entityTitle: tmpl.title,
                  );
                  _refreshTemplateCollections();
                },
              ),
              IconButton(
                icon: Icon(tmpl.isFavorite ? Icons.star : Icons.star_border,
                    color: tmpl.isFavorite ? Colors.amber : null),
                onPressed: () => _toggleFavorite(tmpl.id, tmpl.isFavorite),
                tooltip: tmpl.isFavorite
                    ? _pick('Bỏ yêu thích', 'Remove favorite')
                    : _pick('Yêu thích', 'Favorite'),
              ),
              if (!isMobile && tmpl.status == 'approved')
                Padding(
                  padding: const EdgeInsets.only(right: 4),
                  child: FilledButton.icon(
                    // Điều hướng người dùng sang màn phù hợp theo kết quả thao tác hiện tại.

                    onPressed: () => context.go('/ai-doc/${tmpl.id}'),
                    icon: const Icon(Icons.auto_awesome, size: 16),
                    label: Text(
                        _pick('Tạo VB từ mẫu', 'Create doc from template')),
                    style: FilledButton.styleFrom(
                      backgroundColor: const Color(0xFF2563EB),
                    ),
                  ),
                ),
              // Download DOCX button — prominent in AppBar
              if (!isMobile)
                Padding(
                  padding: const EdgeInsets.only(right: 4),
                  child: OutlinedButton.icon(
                    onPressed: () => _exportDocx(tmpl),
                    icon: const Icon(Icons.download_outlined, size: 16),
                    label: Text(_pick('Tải DOCX', 'Download DOCX')),
                    style: OutlinedButton.styleFrom(
                      side: const BorderSide(color: Colors.white54),
                      foregroundColor: Colors.white,
                      padding: const EdgeInsets.symmetric(
                          horizontal: 12, vertical: 6),
                    ),
                  ),
                ),
              if (!isMobile && canEdit)
                Padding(
                  padding: const EdgeInsets.only(right: 4),
                  child: OutlinedButton.icon(
                    onPressed: () => _openManualEdit(tmpl.id),
                    icon: const Icon(Icons.edit_document, size: 16),
                    label: Text(_pick('Sửa thủ công', 'Manual edit')),
                    style: OutlinedButton.styleFrom(
                      side: const BorderSide(color: Colors.white54),
                      foregroundColor: Colors.white,
                      padding: const EdgeInsets.symmetric(
                          horizontal: 12, vertical: 6),
                    ),
                  ),
                ),
              if (!isMobile && canEdit)
                IconButton(
                  icon: const Icon(Icons.edit_outlined),
                  // Điều hướng người dùng sang màn phù hợp theo kết quả thao tác hiện tại.

                  onPressed: () => context.go('/templates/${tmpl.id}/edit'),
                  tooltip: _pick('Chỉnh sửa', 'Edit'),
                ),
              if (isMobile || canDelete)
                PopupMenuButton<String>(
                  onSelected: (v) {
                    // Điều hướng người dùng sang màn phù hợp theo kết quả thao tác hiện tại.

                    if (v == 'create') context.go('/ai-doc/${tmpl.id}');
                    if (v == 'download') _exportDocx(tmpl);
                    // Điều hướng người dùng sang màn phù hợp theo kết quả thao tác hiện tại.

                    if (v == 'edit') context.go('/templates/${tmpl.id}/edit');
                    if (v == 'manual-edit') _openManualEdit(tmpl.id);
                    if (v == 'delete') _delete(tmpl.id);
                  },
                  itemBuilder: (_) => [
                    if (isMobile && tmpl.status == 'approved')
                      PopupMenuItem(
                          value: 'create',
                          child: ListTile(
                            leading: Icon(Icons.auto_awesome),
                            title: Text(_pick('Tạo văn bản từ mẫu',
                                'Create doc from template')),
                          )),
                    if (isMobile)
                      PopupMenuItem(
                          value: 'download',
                          child: ListTile(
                            leading: Icon(Icons.download_outlined),
                            title: Text(_pick('Tải DOCX', 'Download DOCX')),
                          )),
                    if (isMobile && canEdit)
                      PopupMenuItem(
                          value: 'edit',
                          child: ListTile(
                            leading: Icon(Icons.edit_outlined),
                            title: Text(_pick('Chỉnh sửa', 'Edit')),
                          )),
                    if (canEdit)
                      PopupMenuItem(
                          value: 'manual-edit',
                          child: ListTile(
                            leading: Icon(Icons.edit_document),
                            title: Text(
                                _pick('Chỉnh sửa thủ công', 'Manual edit')),
                          )),
                    if (canDelete)
                      PopupMenuItem(
                          value: 'delete',
                          child: ListTile(
                            leading:
                                Icon(Icons.delete_outline, color: Colors.red),
                            title: Text(_pick('Xóa mẫu', 'Delete template')),
                          )),
                  ],
                ),
            ],
          ),
          body: _actionLoading
              ? const Center(child: CircularProgressIndicator())
              : Column(
                  children: [
                    if (returnTo != null)
                      Padding(
                        padding: const EdgeInsets.fromLTRB(16, 12, 16, 0),
                        child:
                            _buildReturnBanner(context, returnTo, returnLabel),
                      ),
                    _buildApprovalBannerV2(
                        context, tmpl, user, isOwner, isSuperuser),
                    Expanded(
                      child: TabBarView(
                        controller: _tabController,
                        children: [
                          _buildContentTab(context, tmpl),
                          _buildVersionsTab(context, tmpl.id),
                        ],
                      ),
                    ),
                  ],
                ),
        );
      },
    );
  }

  // Mục đích: Phương thức `_buildReturnBanner` triển khai phần việc `build Return Banner` trong flutter_frontend/lib/screens/templates/template_detail_screen.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

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

  // Mục đích: Phương thức `_buildApprovalBanner` triển khai phần việc `build Approval Banner` trong flutter_frontend/lib/screens/templates/template_detail_screen.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  Widget _buildApprovalBanner(BuildContext context, tmpl, dynamic user,
      bool isOwner, bool isSuperuser) {
    final canApproveAsLeader = user?.isLeaderOf(tmpl.groupId ?? -1) ?? false;

    if (tmpl.status == 'draft' && isOwner) {
      return Container(
        width: double.infinity,
        color: Colors.amber.shade50,
        padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 10),
        child: Row(
          children: [
            Icon(Icons.edit_note, color: Colors.amber.shade700),
            const SizedBox(width: 12),
            Expanded(
              child: Text(
                _pick('Mẫu đang ở trạng thái Bản nháp.',
                    'The template is currently in draft status.'),
                style: TextStyle(color: Colors.amber.shade800),
              ),
            ),
            TextButton(
              onPressed: () => _submitForApproval(tmpl.id),
              child: Text(_pick('Gửi duyệt', 'Submit')),
            ),
          ],
        ),
      );
    }

    if (tmpl.status == 'pending' || tmpl.status == 'pending_leader') {
      final isLeaderPending = tmpl.status == 'pending_leader';
      final canApprove = isSuperuser || (isLeaderPending && canApproveAsLeader);
      return Container(
        width: double.infinity,
        color: (isLeaderPending ? Colors.amber : Colors.orange).shade50,
        padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 10),
        child: Row(
          children: [
            Icon(Icons.hourglass_empty,
                color:
                    (isLeaderPending ? Colors.amber : Colors.orange).shade700),
            const SizedBox(width: 12),
            Expanded(
              child: Text(
                isLeaderPending
                    ? _pick('Đang chờ trưởng nhóm phê duyệt.',
                        'Waiting for team leader approval.')
                    : _pick('Đang chờ quản trị phê duyệt.',
                        'Waiting for admin approval.'),
                style: TextStyle(
                    color: (isLeaderPending ? Colors.amber : Colors.orange)
                        .shade800),
              ),
            ),
            if (canApprove) ...[
              TextButton(
                onPressed: () => _approve(tmpl.id),
                style: TextButton.styleFrom(foregroundColor: Colors.green),
                child: Text(_pick('Duyệt', 'Approve')),
              ),
              const SizedBox(width: 8),
              TextButton(
                onPressed: () => _reject(tmpl.id),
                style: TextButton.styleFrom(foregroundColor: Colors.red),
                child: Text(_pick('Từ chối', 'Reject')),
              ),
            ],
          ],
        ),
      );
    }

    if (tmpl.status == 'rejected') {
      return Container(
        width: double.infinity,
        color: Colors.red.shade50,
        padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 10),
        child: Row(
          children: [
            Icon(Icons.cancel_outlined, color: Colors.red.shade700),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(
                    _pick('Bị từ chối.', 'Rejected.'),
                    style: TextStyle(
                        color: Colors.red.shade800,
                        fontWeight: FontWeight.w600),
                  ),
                  if (tmpl.approverNote != null &&
                      tmpl.approverNote!.isNotEmpty)
                    Text(
                      '${_pick('Lý do', 'Reason')}: ${tmpl.approverNote}',
                      style:
                          TextStyle(color: Colors.red.shade700, fontSize: 12.5),
                    ),
                ],
              ),
            ),
            if (isOwner)
              TextButton(
                onPressed: () => _submitForApproval(tmpl.id),
                child: Text(_pick('Gửi lại duyệt', 'Resubmit')),
              ),
          ],
        ),
      );
    }

    if (tmpl.status == 'approved') {
      final approverText =
          (tmpl.approvedBy != null && tmpl.approvedBy!.isNotEmpty)
              ? _pick('Đã được phê duyệt bởi ${tmpl.approvedBy}',
                  'Approved by ${tmpl.approvedBy}')
              : _pick('Đã được phê duyệt', 'Approved');
      return Container(
        width: double.infinity,
        color: Colors.green.shade50,
        padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 10),
        child: Row(
          children: [
            Icon(Icons.check_circle_outline, color: Colors.green.shade700),
            const SizedBox(width: 12),
            Text(approverText, style: TextStyle(color: Colors.green.shade800)),
          ],
        ),
      );
    }

    return const SizedBox.shrink();
  }

  // Mục đích: Phương thức `_buildApprovalBannerV2` triển khai phần việc `build Approval Banner V2` trong flutter_frontend/lib/screens/templates/template_detail_screen.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  Widget _buildApprovalBannerV2(BuildContext context, tmpl, dynamic user,
      bool isOwner, bool isSuperuser) {
    final canApproveAsLeader = user?.isLeaderOf(tmpl.groupId ?? -1) ?? false;
    final reviewSummary = _reviewSummary(tmpl);
    final hasUnreadReview = _hasUnreadReviewForOwner(tmpl, user);

    if (tmpl.status == 'draft' && isOwner) {
      return _buildApprovalBanner(context, tmpl, user, isOwner, isSuperuser);
    }

    if (tmpl.status == 'pending' || tmpl.status == 'pending_leader') {
      final isLeaderPending = tmpl.status == 'pending_leader';
      final canApprove = isSuperuser || (isLeaderPending && canApproveAsLeader);
      return Container(
        width: double.infinity,
        color: (isLeaderPending ? Colors.amber : Colors.orange).shade50,
        padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 10),
        child: Row(
          children: [
            Icon(Icons.hourglass_empty,
                color:
                    (isLeaderPending ? Colors.amber : Colors.orange).shade700),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(
                    isLeaderPending
                        ? _pick('Đang chờ trưởng nhóm phê duyệt.',
                            'Waiting for team leader approval.')
                        : _pick('Đang chờ quản trị phê duyệt.',
                            'Waiting for admin approval.'),
                    style: TextStyle(
                        color: (isLeaderPending ? Colors.amber : Colors.orange)
                            .shade800),
                  ),
                  if (reviewSummary != null)
                    Text(
                      reviewSummary,
                      style: TextStyle(
                        color: (isLeaderPending ? Colors.amber : Colors.orange)
                            .shade800,
                        fontSize: 12.5,
                      ),
                    ),
                ],
              ),
            ),
            if (canApprove) ...[
              TextButton(
                onPressed: () => _approve(tmpl.id),
                style: TextButton.styleFrom(foregroundColor: Colors.green),
                child: Text(_pick('Duyệt', 'Approve')),
              ),
              const SizedBox(width: 8),
              TextButton(
                onPressed: () => _reject(tmpl.id),
                style: TextButton.styleFrom(foregroundColor: Colors.red),
                child: Text(_pick('Từ chối', 'Reject')),
              ),
            ],
          ],
        ),
      );
    }

    if (tmpl.status == 'rejected') {
      return Container(
        width: double.infinity,
        color: Colors.red.shade50,
        padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 10),
        child: Row(
          children: [
            Icon(Icons.cancel_outlined, color: Colors.red.shade700),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(
                    _pick('Bị từ chối.', 'Rejected.'),
                    style: TextStyle(
                        color: Colors.red.shade800,
                        fontWeight: FontWeight.w600),
                  ),
                  if (reviewSummary != null)
                    Text(
                      reviewSummary,
                      style:
                          TextStyle(color: Colors.red.shade700, fontSize: 12.5),
                    ),
                  if (tmpl.approverNote != null &&
                      tmpl.approverNote!.isNotEmpty)
                    Text(
                      '${_pick('Lý do', 'Reason')}: ${tmpl.approverNote}',
                      style:
                          TextStyle(color: Colors.red.shade700, fontSize: 12.5),
                    ),
                ],
              ),
            ),
            if (hasUnreadReview)
              Container(
                margin: const EdgeInsets.only(right: 8),
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                decoration: BoxDecoration(
                  color: Colors.red.shade100,
                  borderRadius: BorderRadius.circular(999),
                ),
                child: Text(
                  _pick('Mới', 'New'),
                  style: TextStyle(
                    color: Colors.red.shade800,
                    fontSize: 11,
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ),
            if (isOwner)
              TextButton(
                onPressed: () => _submitForApproval(tmpl.id),
                child: Text(_pick('Gửi lại duyệt', 'Resubmit')),
              ),
          ],
        ),
      );
    }

    if (tmpl.status == 'approved') {
      final approverText =
          (tmpl.approvedBy != null && tmpl.approvedBy!.isNotEmpty)
              ? _pick('Đã được phê duyệt bởi ${tmpl.approvedBy}',
                  'Approved by ${tmpl.approvedBy}')
              : _pick('Đã được phê duyệt', 'Approved');
      return Container(
        width: double.infinity,
        color: Colors.green.shade50,
        padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 10),
        child: Row(
          children: [
            Icon(Icons.check_circle_outline, color: Colors.green.shade700),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(approverText,
                      style: TextStyle(color: Colors.green.shade800)),
                  if (reviewSummary != null)
                    Text(
                      reviewSummary,
                      style: TextStyle(
                          color: Colors.green.shade700, fontSize: 12.5),
                    ),
                ],
              ),
            ),
            if (hasUnreadReview)
              Container(
                margin: const EdgeInsets.only(left: 8),
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                decoration: BoxDecoration(
                  color: Colors.green.shade100,
                  borderRadius: BorderRadius.circular(999),
                ),
                child: Text(
                  _pick('Mới', 'New'),
                  style: TextStyle(
                    color: Colors.green.shade800,
                    fontSize: 11,
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ),
          ],
        ),
      );
    }

    return _buildApprovalBanner(context, tmpl, user, isOwner, isSuperuser);
  }

  // Mục đích: Phương thức `_buildContentTab` triển khai phần việc `build Content Tab` trong flutter_frontend/lib/screens/templates/template_detail_screen.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  Widget _buildContentTab(BuildContext context, tmpl) {
    final screenWidth = MediaQuery.of(context).size.width;
    final isWide = screenWidth >= 900;

    final mainContent = Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        if (tmpl.description.isNotEmpty) ...[
          Text(tmpl.description,
              style: TextStyle(color: Colors.grey.shade600, fontSize: 14)),
          const SizedBox(height: 16),
        ],
        // Meta chips
        Wrap(
          spacing: 8,
          runSpacing: 6,
          children: [
            if (tmpl.categoryName != null)
              _MetaChip(
                  icon: Icons.category_outlined,
                  label: tmpl.categoryName!,
                  color: Colors.teal),
            _MetaChip(
              icon: Icons.visibility_outlined,
              label: _strings.ui(tmpl.visibilityLabel),
              color: Colors.blueGrey,
            ),
            if (tmpl.effectiveDate != null)
              _MetaChip(
                  icon: Icons.calendar_today_outlined,
                  label: 'Hiệu lực: ${tmpl.effectiveDate!.substring(0, 10)}',
                  color: Colors.green),
            if (tmpl.endDate != null)
              _MetaChip(
                  icon: Icons.event_busy_outlined,
                  label: 'Hết hạn: ${tmpl.endDate!.substring(0, 10)}',
                  color: Colors.red),
          ],
        ),
        const SizedBox(height: 16),
        const Divider(),
        const SizedBox(height: 12),
        Text(
          _pick('Nội dung mẫu', 'Template content'),
          style: Theme.of(context)
              .textTheme
              .titleMedium
              ?.copyWith(fontWeight: FontWeight.bold),
        ),
        const SizedBox(height: 12),
        _buildTemplateContentView(tmpl),
        if (tmpl.variables.isNotEmpty) ...[
          const SizedBox(height: 20),
          Text(
            _pick(
              'Biến tự động (${tmpl.variables.length} biến)',
              'Detected variables (${tmpl.variables.length} variables)',
            ),
            style: Theme.of(context)
                .textTheme
                .titleSmall
                ?.copyWith(fontWeight: FontWeight.w600),
          ),
          const SizedBox(height: 8),
          Wrap(
            spacing: 6,
            runSpacing: 6,
            children: tmpl.variables
                .map<Widget>((v) => Container(
                      padding: const EdgeInsets.symmetric(
                          horizontal: 10, vertical: 4),
                      decoration: BoxDecoration(
                        color: Colors.blue.shade50,
                        borderRadius: BorderRadius.circular(6),
                        border: Border.all(color: Colors.blue.shade200),
                      ),
                      child: Text('{{$v}}',
                          style: TextStyle(
                              fontSize: 12,
                              color: Colors.blue.shade700,
                              fontFamily: 'monospace')),
                    ))
                .toList(),
          ),
        ],
      ],
    );

    final rightCard = Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Card(
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(_pick('Thông tin', 'Information'),
                    style: Theme.of(context)
                        .textTheme
                        .titleSmall
                        ?.copyWith(fontWeight: FontWeight.bold)),
                const SizedBox(height: 12),
                _InfoRow(_pick('Trạng thái', 'Status'),
                    _strings.ui(tmpl.statusLabel)),
                _InfoRow(_pick('Hiển thị', 'Visibility'),
                    _strings.ui(tmpl.visibilityLabel)),
                _InfoRow(_pick('Phiên bản', 'Version'), tmpl.version),
                if (tmpl.categoryName != null)
                  _InfoRow(_pick('Danh mục', 'Category'), tmpl.categoryName!),
                _InfoRow(_pick('Chủ sở hữu', 'Owner'), tmpl.ownerName),
                _InfoRow(
                    _pick('Ngày tạo', 'Created'),
                    tmpl.createdAt.length >= 10
                        ? tmpl.createdAt.substring(0, 10)
                        : tmpl.createdAt),
                _InfoRow(
                    _pick('Cập nhật', 'Updated'),
                    tmpl.updatedAt.length >= 10
                        ? tmpl.updatedAt.substring(0, 10)
                        : tmpl.updatedAt),
                const SizedBox(height: 14),
                const Divider(),
                const SizedBox(height: 8),
                SizedBox(
                  width: double.infinity,
                  child: FilledButton.tonalIcon(
                    onPressed: () => _exportDocx(tmpl),
                    icon: const Icon(Icons.download_outlined, size: 16),
                    label: Text(_pick('Tải về DOCX', 'Download DOCX')),
                  ),
                ),
              ],
            ),
          ),
        ),
        if (tmpl.variables.isNotEmpty) ...[
          const SizedBox(height: 16),
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(_pick('Xem trước', 'Preview'),
                      style: Theme.of(context)
                          .textTheme
                          .titleSmall
                          ?.copyWith(fontWeight: FontWeight.bold)),
                  const SizedBox(height: 8),
                  Text(
                      _pick('Điền giá trị để xem trước:',
                          'Fill values to preview:'),
                      style:
                          TextStyle(fontSize: 12, color: Colors.grey.shade600)),
                  const SizedBox(height: 10),
                  ...tmpl.variables.map<Widget>((v) => Padding(
                        padding: const EdgeInsets.only(bottom: 8),
                        child: TextField(
                          controller: _previewControllers[v],
                          decoration: InputDecoration(
                            labelText: v,
                            isDense: true,
                            border: const OutlineInputBorder(),
                            contentPadding: const EdgeInsets.symmetric(
                                horizontal: 10, vertical: 8),
                          ),
                          style: const TextStyle(fontSize: 13),
                        ),
                      )),
                  const SizedBox(height: 8),
                  SizedBox(
                    width: double.infinity,
                    child: OutlinedButton.icon(
                      onPressed: () => _showPreviewDialog(
                          context, tmpl.title as String, tmpl.variables),
                      icon: const Icon(Icons.preview, size: 16),
                      label: Text(_pick('Xem trước', 'Preview')),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ],
      ],
    );

    if (isWide) {
      return SingleChildScrollView(
        padding: const EdgeInsets.all(24),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Expanded(flex: 3, child: mainContent),
            const SizedBox(width: 24),
            SizedBox(width: 260, child: rightCard),
          ],
        ),
      );
    }

    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          mainContent,
          const SizedBox(height: 24),
          rightCard,
        ],
      ),
    );
  }

  // Mục đích: Phương thức `_buildVersionsTab` triển khai phần việc `build Versions Tab` trong flutter_frontend/lib/screens/templates/template_detail_screen.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  Widget _buildVersionsTab(BuildContext context, int tmplId) {
    // Lắng nghe provider để widget tự động dựng lại khi dữ liệu hoặc trạng thái thay đổi.

    final user = ref.watch(currentUserProvider);
    final isOwnerOrStaff = user?.isStaff == true;
    // Owner/staff dùng provider "all" để thấy cả phiên bản ẩn
    final asyncVersions = isOwnerOrStaff
        // Lắng nghe provider để widget tự động dựng lại khi dữ liệu hoặc trạng thái thay đổi.

        ? ref.watch(templateVersionsAllProvider(tmplId))
        // Lắng nghe provider để widget tự động dựng lại khi dữ liệu hoặc trạng thái thay đổi.

        : ref.watch(templateVersionsProvider(tmplId));

    return asyncVersions.when(
      loading: () => const Center(child: CircularProgressIndicator()),
      error: (e, _) => Center(
          child:
              Text('${_pick('Lỗi tải phiên bản', 'Version load error')}: $e')),
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
          itemCount: versions.length,
          separatorBuilder: (_, __) => const Divider(height: 1),
          itemBuilder: (ctx, i) {
            final ver = versions[i];
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
                  child: Text(
                    'v${ver.versionNumber}',
                    style: TextStyle(
                      fontSize: 10,
                      fontWeight: FontWeight.bold,
                      color: hidden ? Colors.grey : Colors.blue.shade700,
                    ),
                  ),
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
                          style: const TextStyle(
                              fontSize: 10, color: Colors.grey)),
                    ),
                  ],
                ]),
                subtitle: Text(
                  '${ver.createdByName ?? ''} — $dateStr'
                  '${ver.changeNote?.isNotEmpty == true ? '\n${ver.changeNote}' : ''}',
                  style: TextStyle(fontSize: 12, color: Colors.grey.shade600),
                ),
                isThreeLine: ver.changeNote?.isNotEmpty == true,
                trailing: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    // Xem trước nội dung
                    IconButton(
                      icon: const Icon(Icons.preview_outlined, size: 18),
                      tooltip: _pick('Xem trước nội dung', 'Preview content'),
                      onPressed: () => _showVersionPreview(context, ver),
                    ),
                    // Xem diff
                    IconButton(
                      icon: const Icon(Icons.difference_outlined, size: 18),
                      tooltip: _pick('So sánh với phiên bản sau',
                          'Compare with next version'),
                      onPressed: () => _showVersionDiff(context, tmplId, ver),
                    ),
                    // Ẩn/hiện (chỉ owner/staff)
                    if (isOwnerOrStaff)
                      IconButton(
                        icon: Icon(
                          hidden
                              ? Icons.visibility_outlined
                              : Icons.visibility_off_outlined,
                          size: 18,
                          color: hidden ? Colors.green : Colors.grey,
                        ),
                        tooltip: hidden
                            ? _pick('Hiện phiên bản', 'Show version')
                            : _pick('Ẩn phiên bản', 'Hide version'),
                        onPressed: () =>
                            _toggleHideVersion(tmplId, ver.id, isOwnerOrStaff),
                      ),
                    // Khôi phục
                    if (!hidden)
                      TextButton(
                        onPressed: () => _restoreVersion(tmplId, ver.id),
                        style: TextButton.styleFrom(
                          padding: const EdgeInsets.symmetric(horizontal: 8),
                          textStyle: const TextStyle(fontSize: 12),
                        ),
                        child: Text(_pick('Khôi phục', 'Restore')),
                      ),
                  ],
                ),
              ),
            );
          },
        );
      },
    );
  }

  // ── XEM TRƯỚC NỘI DUNG PHIÊN BẢN ────────────────────────────────────────────

  // Mục đích: Phương thức `_showVersionPreview` triển khai phần việc `show Version Preview` trong flutter_frontend/lib/screens/templates/template_detail_screen.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  void _showVersionPreview(BuildContext context, TemplateVersion ver) {
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
                    'Xem trước — Phiên bản ${ver.versionNumber}',
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

              // Page-style content (same as main content tab)
              Expanded(
                child: Container(
                  color: const Color(0xFFE8EAED), // grey page background
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
                        child: (ver.content != null && ver.content!.isNotEmpty)
                            ? SelectableText(
                                ver.content!,
                                style: const TextStyle(
                                    fontFamily: 'Times New Roman',
                                    fontSize: 14,
                                    height: 1.6),
                              )
                            : Text(
                                '(Không có nội dung)',
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

  // ── SO SÁNH DIFF ──────────────────────────────────────────────────────────────

  // Mục đích: Phương thức `_showVersionDiff` triển khai phần việc `show Version Diff` trong flutter_frontend/lib/screens/templates/template_detail_screen.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  Future<void> _showVersionDiff(
      BuildContext context, int tmplId, TemplateVersion ver) async {
    try {
      // Gọi API hoặc tác vụ bất đồng bộ rồi chờ kết quả trước khi cập nhật giao diện.

      final resp = await ApiClient()
          .dio
          .get('templates/$tmplId/versions/${ver.id}/diff/');
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
                // ── Header ───────────────────────────────────────────────
                Container(
                  padding: const EdgeInsets.fromLTRB(20, 14, 12, 14),
                  decoration: const BoxDecoration(
                    color: Color(0xFF24292F), // GitHub dark header
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

                // ── Legend bar ───────────────────────────────────────────
                Container(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 16, vertical: 6),
                  color: const Color(0xFFF6F8FA),
                  child: Row(children: [
                    _diffLegend(
                        const Color(0xFFE6FFEC),
                        const Color(0xFF1A7F37),
                        _pick('+ Thêm mới', '+ Added')),
                    const SizedBox(width: 20),
                    _diffLegend(
                        const Color(0xFFFFEBE9),
                        const Color(0xFFCF222E),
                        _pick('− Xóa bỏ', '− Removed')),
                    const SizedBox(width: 20),
                    _diffLegend(Colors.white, Colors.grey.shade500,
                        _pick('  Không đổi', '  Unchanged')),
                  ]),
                ),
                const Divider(height: 1),

                // ── Diff body ────────────────────────────────────────────
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

  /// Render một dòng diff theo phong cách GitHub:
  /// gutter (±/space) màu đậm hơn, nội dung có nền màu tương ứng.
  // Mục đích: Phương thức `_buildDiffLine` triển khai phần việc `build Diff Line` trong flutter_frontend/lib/screens/templates/template_detail_screen.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  Widget _buildDiffLine(String line) {
    // File headers (--- / +++)
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

    // Hunk header (@@ ... @@)
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

    // Added line
    if (line.startsWith('+')) {
      return _ghDiffRow(
        gutterBg: const Color(0xFFCCFFC1), // GitHub green gutter
        gutterFg: const Color(0xFF1A7F37),
        rowBg: const Color(0xFFE6FFEC), // GitHub green row
        prefix: '+',
        content: line.substring(1),
      );
    }

    // Removed line
    if (line.startsWith('-')) {
      return _ghDiffRow(
        gutterBg: const Color(0xFFFFBEBC), // GitHub red gutter
        gutterFg: const Color(0xFFCF222E),
        rowBg: const Color(0xFFFFEBE9), // GitHub red row
        prefix: '-',
        content: line.substring(1),
      );
    }

    // Unchanged line (starts with space or empty)
    final content = line.startsWith(' ') ? line.substring(1) : line;
    return _ghDiffRow(
      gutterBg: Colors.white,
      gutterFg: const Color(0xFF57606A),
      rowBg: Colors.white,
      prefix: ' ',
      content: content,
    );
  }

  // Mục đích: Phương thức `_ghDiffRow` triển khai phần việc `gh Diff Row` trong flutter_frontend/lib/screens/templates/template_detail_screen.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

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
          // Gutter column (±/space)
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
          // Separator line
          Container(width: 1, color: gutterBg.withOpacity(0.6)),
          // Content
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

  // Mục đích: Phương thức `_diffLegend` triển khai phần việc `diff Legend` trong flutter_frontend/lib/screens/templates/template_detail_screen.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

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

  // ── ẨN / HIỆN PHIÊN BẢN ─────────────────────────────────────────────────────

  // Mục đích: Phương thức `_toggleHideVersion` triển khai phần việc `toggle Hide Version` trong flutter_frontend/lib/screens/templates/template_detail_screen.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  Future<void> _toggleHideVersion(
      int tmplId, int verId, bool isOwnerOrStaff) async {
    if (!isOwnerOrStaff) return;
    try {
      // Gọi API hoặc tác vụ bất đồng bộ rồi chờ kết quả trước khi cập nhật giao diện.

      await ApiClient().dio.post('templates/$tmplId/versions/$verId/hide/');
      ref.invalidate(templateVersionsAllProvider(tmplId));
      ref.invalidate(templateVersionsProvider(tmplId));
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('${_pick('Lỗi', 'Error')}: $e'),
            backgroundColor: Colors.red,
          ),
        );
      }
    }
  }
}

// Mục đích: Lớp `_MetaChip` triển khai phần việc `Meta Chip` trong flutter_frontend/lib/screens/templates/template_detail_screen.dart.
// Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
// Vai trò trong hệ thống: Đây là lớp thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
// Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

class _MetaChip extends StatelessWidget {
  final IconData icon;
  final String label;
  final Color color;
  const _MetaChip(
      {required this.icon, required this.label, required this.color});

  @override
  // Mục đích: Phương thức `build` triển khai phần việc `build` trong flutter_frontend/lib/screens/templates/template_detail_screen.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  Widget build(BuildContext context) {
    return Row(mainAxisSize: MainAxisSize.min, children: [
      Icon(icon, size: 13, color: color),
      const SizedBox(width: 4),
      Text(label, style: TextStyle(fontSize: 12.5, color: color)),
    ]);
  }
}

// Mục đích: Lớp `_InfoRow` triển khai phần việc `Info Row` trong flutter_frontend/lib/screens/templates/template_detail_screen.dart.
// Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
// Vai trò trong hệ thống: Đây là lớp thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
// Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

class _InfoRow extends StatelessWidget {
  final String label;
  final String value;
  const _InfoRow(this.label, this.value);

  @override
  // Mục đích: Phương thức `build` triển khai phần việc `build` trong flutter_frontend/lib/screens/templates/template_detail_screen.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 90,
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
