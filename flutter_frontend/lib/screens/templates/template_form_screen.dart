// Tệp này dùng để: dựng giao diện và orchestration UI trong flutter_frontend/lib/screens/templates/template_form_screen.dart.
// Cách hoạt động: nhận state từ provider, dựng widget, phản ứng sự kiện và gửi thao tác ngược về backend khi người dùng tương tác.
// Vai trò trong hệ thống: Đây là màn hình Flutter mà người dùng tương tác trực tiếp.
// Tác dụng khi hệ thống vận hành: biến nghiệp vụ backend thành trải nghiệm thao tác cụ thể trên web.

import 'dart:async';
import 'dart:convert';
import 'dart:html' as html;
import 'dart:typed_data';
import 'dart:ui_web' as ui;
import 'package:intl/intl.dart';
import 'package:dio/dio.dart';
import 'package:file_picker/file_picker.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../core/api_client.dart';
import '../../core/template_delete_helper.dart';
import '../../l10n/app_strings.dart';
import '../../providers/prompts_provider.dart';
import '../../providers/templates_provider.dart';
import '../../widgets/ai/prompt_picker_dialog.dart';
import '../../widgets/ai/save_prompt_dialog.dart';
import '../../widgets/pdf/web_pdf_frame.dart';
import '../../widgets/sharing/unified_share_sheet.dart';

// Mục đích: Lớp `_CreateMode` triển khai phần việc `Create Mode` trong flutter_frontend/lib/screens/templates/template_form_screen.dart.
// Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
// Vai trò trong hệ thống: Đây là lớp thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
// Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

enum _CreateMode { manual, uploadDocx, uploadDocxDetect }

// Mục đích: Lớp `_GroupMemberOption` triển khai phần việc `Group Member Option` trong flutter_frontend/lib/screens/templates/template_form_screen.dart.
// Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
// Vai trò trong hệ thống: Đây là lớp thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
// Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

class _GroupMemberOption {
  final int id;
  final String username;
  final String fullName;
  final String role;

  const _GroupMemberOption({
    required this.id,
    required this.username,
    required this.fullName,
    required this.role,
  });

  String get displayLabel => fullName.isEmpty || fullName == username
      ? username
      : '$fullName ($username)';

  factory _GroupMemberOption.fromJson(Map<String, dynamic> json) =>
      _GroupMemberOption(
        id: json['id'],
        username: json['username'] ?? '',
        fullName: json['full_name'] ?? json['username'] ?? '',
        role: json['role'] ?? 'member',
      );
}

// Mục đích: Widget `TemplateFormScreen` triển khai phần việc `Template Form Screen` trong flutter_frontend/lib/screens/templates/template_form_screen.dart.
// Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
// Vai trò trong hệ thống: Đây là widget thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
// Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

class TemplateFormScreen extends ConsumerStatefulWidget {
  final int? id;
  final String? sourceUrl;
  final String? sourceTitle;

  const TemplateFormScreen({
    super.key,
    this.id,
    this.sourceUrl,
    this.sourceTitle,
  });

  @override
  ConsumerState<TemplateFormScreen> createState() => _TemplateFormScreenState();
}

// Mục đích: Widget `_TemplateFormScreenState` triển khai phần việc `Template Form Screen State` trong flutter_frontend/lib/screens/templates/template_form_screen.dart.
// Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
// Vai trò trong hệ thống: Đây là widget thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
// Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

class _TemplateFormScreenState extends ConsumerState<TemplateFormScreen> {
  final _formKey = GlobalKey<FormState>();
  final _titleCtrl = TextEditingController();
  final _descCtrl = TextEditingController();
  final _notesCtrl = TextEditingController();
  final _changeNoteCtrl = TextEditingController();
  final _tagInputCtrl = TextEditingController();

  String _visibility = 'private';
  int? _selectedGroupId;
  final Set<int> _selectedAudienceUserIds = <int>{};
  List<_GroupMemberOption> _groupMembers = const [];
  bool _groupMembersLoading = false;
  DateTime? _effectiveDate;
  DateTime? _endDate;
  bool _loading = false;
  bool _initialized = false;
  Set<String> _detectedVars = {};
  String _editTitle = '';
  List<String> _tags = [];
  bool _generatingTags = false;
  int? _templateIdForTagGen;
  bool _replacingDocx = false;
  String? _replaceDocxStatus;
  String _editorContentFallback = '';
  bool _manualEditLaunching = false;
  String? _templatePreviewPdfUrl;
  String? _templatePreviewLoadError;
  bool _templatePreviewLoading = false;
  int _templatePreviewFrameKey = 0;
  Timer? _templatePreviewAutoReloadTimer;
  Future<void> Function()? _templatePreviewAutoReloadAction;

  // ── RICH TEXT EDITOR (iframe) ─────────────────────────────────────────────
  html.IFrameElement? _editorIframe;
  late final String _editorViewKey;
  bool _editorReady = false;
  bool _editorReadOnly = false;
  String? _pendingEditorContent;
  StreamSubscription? _editorMsgSub;

  // ── CREATE MODE ───────────────────────────────────────────────────────────
  _CreateMode _mode = _CreateMode.manual;
  bool _importing = false;
  String? _importStatus;

  // Prompt tùy chỉnh hỗ trợ AI nhận diện biến (chỉ dùng ở chế độ Upload + AI detect).
  final TextEditingController _detectionHintCtrl = TextEditingController();
  String? _detectionPromptId;
  String _detectionPromptTitle = '';
  String? _docxFileName;
  Uint8List? _docxFileBytes;
  bool _templateHasDocxSource = false;
  bool _sourceImporting = false;
  bool _sourceImportStarted = false;
  String? _sourceImportStatus;
  String? _sourceImportResolvedTitle;
  String? _sourceImportResolvedUrl;
  String? _sourceImportKind;

  AppStrings get _strings => AppStrings.of(context);

  String _pick(String vi, String en) => _strings.pick(vi, en);

  bool _looksLikeError(String? value) {
    if (value == null) return false;
    return value.startsWith('Loi') ||
        value.startsWith('Lỗi') ||
        value.startsWith('Error');
  }

  bool get _isDocxMode => _mode != _CreateMode.manual;
  bool get _hasLocalDocxBytes =>
      _docxFileBytes != null && _docxFileBytes!.isNotEmpty;

  // Mục đích: Phương thức `_clearDocxSelection` triển khai phần việc `clear Docx Selection` trong flutter_frontend/lib/screens/templates/template_form_screen.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  void _clearDocxSelection({bool clearStatus = false}) {
    _docxFileName = null;
    _docxFileBytes = null;
    if (widget.id == null) {
      _templateHasDocxSource = false;
    }
    if (clearStatus) {
      _importStatus = null;
    }
  }

  // Mục đích: Phương thức `_effectiveDocxFilename` triển khai phần việc `effective Docx Filename` trong flutter_frontend/lib/screens/templates/template_form_screen.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  String _effectiveDocxFilename([String? preferred]) {
    var filename =
        (preferred ?? _docxFileName ?? _titleCtrl.text.trim()).trim();
    if (filename.isEmpty) filename = 'template.docx';
    if (!filename.toLowerCase().endsWith('.docx')) {
      filename = '$filename.docx';
    }
    return filename;
  }

  FormData _buildDocxFormData({
    required String title,
    required String description,
    required String content,
    required String visibility,
    int? groupId,
    required List<int> audienceUserIds,
    required String notes,
    required List<String> tags,
    String? effectiveDate,
    String? endDate,
    String? changeNote,
    required Uint8List docxBytes,
    String? filename,
  }) {
    return FormData.fromMap({
      'title': title,
      'description': description,
      'content': content,
      'source_type': 'docx',
      'visibility': visibility,
      if (visibility == 'group' && groupId != null) 'group': groupId,
      if (visibility == 'group')
        'audience_user_ids': jsonEncode(audienceUserIds),
      'notes': notes,
      'tags': jsonEncode(tags),
      if (effectiveDate != null && effectiveDate.isNotEmpty)
        'effective_date': effectiveDate,
      if (endDate != null && endDate.isNotEmpty) 'end_date': endDate,
      if (changeNote != null && changeNote.isNotEmpty)
        'change_note': changeNote,
      'docx_file': MultipartFile.fromBytes(docxBytes,
          filename: _effectiveDocxFilename(filename)),
    });
  }

  // Mục đích: Phương thức `_resolveStoredDocxBytes` triển khai phần việc `resolve Stored Docx Bytes` trong flutter_frontend/lib/screens/templates/template_form_screen.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  Future<Uint8List?> _resolveStoredDocxBytes() async {
    if (_hasLocalDocxBytes) return _docxFileBytes;
    if (widget.id == null || !_templateHasDocxSource) return null;

    // Gọi API hoặc tác vụ bất đồng bộ rồi chờ kết quả trước khi cập nhật giao diện.

    final resp = await ApiClient().dio.get(
          'templates/${widget.id}/export/',
          options: Options(responseType: ResponseType.bytes),
        );
    final bytes = Uint8List.fromList(List<int>.from(resp.data as List));
    if (bytes.isEmpty) return null;

    _docxFileBytes = bytes;
    _docxFileName ??= _effectiveDocxFilename();
    return bytes;
  }

  // Mục đích: Phương thức `_refreshTemplateCollections` triển khai phần việc `refresh Template Collections` trong flutter_frontend/lib/screens/templates/template_form_screen.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  void _refreshTemplateCollections([int? detailId]) {
    if (detailId != null) {
      ref.invalidate(templateDetailProvider(detailId));
      ref.invalidate(templateVersionsProvider(detailId));
    }
    ref.invalidate(templatesProvider(''));
    ref.invalidate(templatesProvider('private'));
    ref.invalidate(templatesProvider('team'));
    ref.invalidate(templatesProvider('system'));
    ref.invalidate(templatesProvider('favorite'));
  }

  void _revokeTemplatePreviewPdfUrl() {
    final current = _templatePreviewPdfUrl;
    if (current == null || current.isEmpty) return;
    html.Url.revokeObjectUrl(current);
    _templatePreviewPdfUrl = null;
  }

  void _stopTemplatePreviewAutoReload() {
    _templatePreviewAutoReloadTimer?.cancel();
    _templatePreviewAutoReloadTimer = null;
    _templatePreviewAutoReloadAction = null;
  }

  void _restartTemplatePreviewAutoReload(Future<void> Function() action) {
    _stopTemplatePreviewAutoReload();
    _templatePreviewAutoReloadAction = action;
    _templatePreviewAutoReloadTimer =
        Timer.periodic(const Duration(seconds: 10), (_) {
      final callback = _templatePreviewAutoReloadAction;
      if (!mounted || callback == null || _templatePreviewLoading) return;
      if (_templatePreviewPdfUrl == null || _templatePreviewPdfUrl!.isEmpty)
        return;
      callback();
    });
  }

  void _resetTemplatePreviewState() {
    _stopTemplatePreviewAutoReload();
    _revokeTemplatePreviewPdfUrl();
    _templatePreviewLoadError = null;
    _templatePreviewLoading = false;
    _templatePreviewFrameKey += 1;
  }

  String _templatePreviewErrorMessage(Object error) {
    if (error is DioException) {
      final data = error.response?.data;
      if (data is Map && data['detail'] != null) {
        return '${data['detail']}';
      }
      return _pick(
        'Không tạo được bản xem PDF cho mẫu (${error.response?.statusCode ?? 'network'}).',
        'Unable to generate the template PDF preview (${error.response?.statusCode ?? 'network'}).',
      );
    }
    return _pick(
      'Không tạo được bản xem PDF cho mẫu: $error',
      'Unable to generate the template PDF preview: $error',
    );
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

  Future<void> _loadTemplatePreview(tmpl, {bool force = false}) async {
    if (widget.id == null) return;
    if (_templatePreviewLoading) return;
    if (!force &&
        _templatePreviewPdfUrl != null &&
        _templatePreviewPdfUrl!.isNotEmpty) {
      return;
    }

    final hasContent =
        tmpl.content != null && (tmpl.content as String).isNotEmpty;
    final hasDocx = tmpl.sourceType == 'docx';
    final hasDocxSource = tmpl.hasDocxSource == true;
    if (!hasContent && !hasDocx && !hasDocxSource) return;

    setState(() {
      _templatePreviewLoading = true;
      _templatePreviewLoadError = null;
    });
    try {
      final pdfResp = await ApiClient().dio.get(
            'templates/${widget.id}/preview-pdf/',
            queryParameters: _templatePreviewQuery(tmpl),
            options: Options(responseType: ResponseType.bytes),
          );
      final bytes = Uint8List.fromList(List<int>.from(pdfResp.data as List));
      final blob = html.Blob([bytes], 'application/pdf');
      final nextUrl = html.Url.createObjectUrlFromBlob(blob);
      if (!mounted) {
        html.Url.revokeObjectUrl(nextUrl);
        return;
      }
      _revokeTemplatePreviewPdfUrl();
      setState(() {
        _templatePreviewPdfUrl = nextUrl;
        _templatePreviewLoadError = null;
        _templatePreviewLoading = false;
        _templatePreviewFrameKey += 1;
      });
      _restartTemplatePreviewAutoReload(
          () => _loadTemplatePreview(tmpl, force: true));
    } catch (error) {
      if (!mounted) return;
      _stopTemplatePreviewAutoReload();
      setState(() {
        _templatePreviewLoading = false;
        _templatePreviewLoadError = _templatePreviewErrorMessage(error);
      });
    }
  }

  void _openTemplatePreviewPdfInNewTab() {
    final current = _templatePreviewPdfUrl;
    if (current == null || current.isEmpty) return;
    html.window.open(current, '_blank');
  }

  Future<void> _openTemplatePreviewDialog(tmpl) async {
    await _loadTemplatePreview(tmpl, force: true);
    final current = _templatePreviewPdfUrl;
    if (current == null || current.isEmpty) return;
    final isCompact = MediaQuery.of(context).size.width < 900;
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
                        'Ban xem PDF toan man hinh',
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
                  child: WebPdfFrame(
                    viewKey:
                        'template-form-preview-dialog-${widget.id}-$_templatePreviewFrameKey',
                    pdfUrl: current,
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  // Mục đích: Phương thức `_validateDateRange` triển khai phần việc `validate Date Range` trong flutter_frontend/lib/screens/templates/template_form_screen.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  bool _validateDateRange() {
    if (_effectiveDate != null &&
        _endDate != null &&
        _endDate!.isBefore(_effectiveDate!)) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(_pick(
            'Ngày hết hạn không được sớm hơn ngày hiệu lực.',
            'The expiration date cannot be earlier than the effective date.',
          )),
          backgroundColor: Colors.red,
        ),
      );
      return false;
    }
    return true;
  }

  @override
  // Mục đích: Phương thức `initState` triển khai phần việc `init State` trong flutter_frontend/lib/screens/templates/template_form_screen.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  void initState() {
    super.initState();
    _editorViewKey = 'tmpl-editor-${DateTime.now().millisecondsSinceEpoch}';
    ui.platformViewRegistry.registerViewFactory(_editorViewKey, (int viewId) {
      _editorIframe = html.IFrameElement()
        ..style.border = 'none'
        ..style.width = '100%'
        ..style.height = '100%'
        ..style.pointerEvents = 'auto'
        ..srcdoc = _buildEditorHtml();
      _editorIframe!.onLoad.first.then((_) => _onEditorLoaded());
      return _editorIframe!;
    });
    _editorMsgSub = html.window.onMessage.listen(_handleEditorMessage);
    _maybeImportSourceFromUrl();
  }

  @override
  void didUpdateWidget(covariant TemplateFormScreen oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.id == widget.id) return;
    _resetTemplatePreviewState();
  }

  @override
  // Mục đích: Phương thức `dispose` triển khai phần việc `dispose` trong flutter_frontend/lib/screens/templates/template_form_screen.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  void dispose() {
    _editorMsgSub?.cancel();
    _stopTemplatePreviewAutoReload();
    _revokeTemplatePreviewPdfUrl();
    _titleCtrl.dispose();
    _descCtrl.dispose();
    _notesCtrl.dispose();
    _changeNoteCtrl.dispose();
    _tagInputCtrl.dispose();
    _detectionHintCtrl.dispose();
    super.dispose();
  }

  // Mục đích: Phương thức `_maybeImportSourceFromUrl` triển khai phần việc `maybe Import Source From Url` trong flutter_frontend/lib/screens/templates/template_form_screen.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  void _maybeImportSourceFromUrl() {
    final sourceUrl = widget.sourceUrl?.trim();
    if (widget.id != null ||
        sourceUrl == null ||
        sourceUrl.isEmpty ||
        _sourceImportStarted) {
      return;
    }
    _sourceImportStarted = true;
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (mounted) {
        _importSourceFromUrl(sourceUrl);
      }
    });
  }

  // Mục đích: Phương thức `_importSourceFromUrl` triển khai phần việc `import Source From Url` trong flutter_frontend/lib/screens/templates/template_form_screen.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  Future<void> _importSourceFromUrl(String sourceUrl) async {
    final sourceTitle = widget.sourceTitle?.trim();
    // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

    setState(() {
      _sourceImporting = true;
      _sourceImportStatus = _pick(
        'Đang tải nguồn Internet và AI đang nhận diện biến...',
        'Loading the Internet source and letting AI detect variables...',
      );
      _sourceImportResolvedTitle =
          sourceTitle?.isNotEmpty == true ? sourceTitle : null;
      _sourceImportResolvedUrl = sourceUrl;
      _sourceImportKind = null;
    });

    try {
      // Gọi API hoặc tác vụ bất đồng bộ rồi chờ kết quả trước khi cập nhật giao diện.

      final resp = await ApiClient().dio.post(
            'templates/import-from-url/',
            data: {
              'source_url': sourceUrl,
              if (sourceTitle != null && sourceTitle.isNotEmpty)
                'source_title': sourceTitle,
              'auto_detect': 'true',
            },
            options: ApiClient.ollamaOptions(),
          );

      final data = Map<String, dynamic>.from(resp.data as Map);
      final content = '${data['content'] ?? ''}';
      final detectedVars = (data['detected_vars'] as List? ?? [])
          .map((e) => e.toString())
          .where((e) => e.trim().isNotEmpty)
          .toSet();
      final resolvedTitle = '${data['title'] ?? sourceTitle ?? ''}'.trim();
      final resolvedUrl = '${data['resolved_url'] ?? sourceUrl}'.trim();
      final sourceKind = '${data['source_kind'] ?? 'html'}'.trim();
      final sourceFilename = '${data['source_filename'] ?? ''}'.trim();
      Uint8List? importedDocxBytes;
      if (sourceKind == 'docx') {
        final modifiedDocx = '${data['modified_docx'] ?? ''}'.trim();
        final sourceDocx = '${data['source_docx'] ?? ''}'.trim();
        final encodedDocx = modifiedDocx.isNotEmpty ? modifiedDocx : sourceDocx;
        if (encodedDocx.isNotEmpty) {
          importedDocxBytes = Uint8List.fromList(base64Decode(encodedDocx));
        }
      }

      if (_titleCtrl.text.trim().isEmpty && resolvedTitle.isNotEmpty) {
        _titleCtrl.text = resolvedTitle;
      }

      final editorHtml = _toEditorHtml(content);
      _setEditorContent(editorHtml);

      if (!mounted) return;
      // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

      setState(() {
        _sourceImporting = false;
        _sourceImportResolvedTitle =
            resolvedTitle.isNotEmpty ? resolvedTitle : sourceTitle;
        _sourceImportResolvedUrl =
            resolvedUrl.isNotEmpty ? resolvedUrl : sourceUrl;
        _sourceImportKind = sourceKind;
        if (sourceKind == 'docx' && importedDocxBytes != null) {
          _mode = _CreateMode.uploadDocxDetect;
          _docxFileBytes = importedDocxBytes;
          _docxFileName = _effectiveDocxFilename(
            sourceFilename.isNotEmpty ? sourceFilename : resolvedTitle,
          );
          _templateHasDocxSource = true;
        }
        _sourceImportStatus = _pick(
          'Đã nhập thành công nguồn Internet và nhận diện ${detectedVars.length} biến tự động.',
          'Imported the Internet source successfully and detected ${detectedVars.length} variables.',
        );
        _detectedVars = detectedVars;
      });
      _setEditorReadOnly(_isDocxMode);
    } on DioException catch (e) {
      final serverMessage = e.response?.data is Map
          ? (e.response?.data['detail'] ?? e.response?.data['error'])
          : null;
      if (!mounted) return;
      // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

      setState(() {
        _sourceImporting = false;
        _sourceImportStatus =
            '${_pick('Lỗi nhập nguồn Internet', 'Internet import error')}: ${serverMessage ?? e.message ?? e}';
      });
    } catch (e) {
      if (!mounted) return;
      // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

      setState(() {
        _sourceImporting = false;
        _sourceImportStatus =
            '${_pick('Lỗi nhập nguồn Internet', 'Internet import error')}: $e';
      });
    }
  }

  // Mục đích: Phương thức `_onEditorLoaded` triển khai phần việc `on Editor Loaded` trong flutter_frontend/lib/screens/templates/template_form_screen.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  void _onEditorLoaded() {
    _editorReady = true;
    if (_pendingEditorContent != null) {
      _editorIframe?.contentWindow?.postMessage(
          {'type': 'set-content', 'html': _pendingEditorContent!}, '*');
      _pendingEditorContent = null;
    }
    _editorIframe?.contentWindow
        ?.postMessage({'type': 'set-read-only', 'value': _editorReadOnly}, '*');
  }

  // Mục đích: Phương thức `_setEditorContent` triển khai phần việc `set Editor Content` trong flutter_frontend/lib/screens/templates/template_form_screen.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  void _setEditorContent(String content) {
    _editorContentFallback = content;
    if (_editorReady) {
      _editorIframe?.contentWindow
          ?.postMessage({'type': 'set-content', 'html': content}, '*');
    } else {
      _pendingEditorContent = content;
    }
  }

  // Mục đích: Phương thức `_setEditorReadOnly` triển khai phần việc `set Editor Read Only` trong flutter_frontend/lib/screens/templates/template_form_screen.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  void _setEditorReadOnly(bool value) {
    _editorReadOnly = value;
    if (_editorReady) {
      _editorIframe?.contentWindow
          ?.postMessage({'type': 'set-read-only', 'value': value}, '*');
    }
  }

  // Mục đích: Phương thức `_toEditorHtml` triển khai phần việc `to Editor Html` trong flutter_frontend/lib/screens/templates/template_form_screen.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  String _toEditorHtml(String content) {
    final trimmed = content.trim();
    if (trimmed.isEmpty) return '';
    final looksLikeHtml = trimmed.contains('<p') ||
        trimmed.contains('<div') ||
        trimmed.contains('<br') ||
        trimmed.contains('<table') ||
        trimmed.contains('<span') ||
        trimmed.contains('<h1') ||
        trimmed.contains('<h2') ||
        trimmed.contains('<h3');
    if (looksLikeHtml) return content;

    final escaped = HtmlEscape(HtmlEscapeMode.element).convert(content);
    final paragraphs = escaped
        .split(RegExp(r'\r?\n\r?\n+'))
        .map((block) => block.trim())
        .where((block) => block.isNotEmpty)
        .map((block) => '<p>${block.replaceAll('\n', '<br>')}</p>')
        .join();
    return paragraphs.isNotEmpty ? paragraphs : '<p>$escaped</p>';
  }

  // Mục đích: Phương thức `_handleEditorMessage` triển khai phần việc `handle Editor Message` trong flutter_frontend/lib/screens/templates/template_form_screen.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  void _handleEditorMessage(html.MessageEvent event) {
    final data = event.data;
    if (data is! Map) return;
    final type = data['type'] as String?;
    if (type == 'content-changed') {
      final varList = data['vars'];
      if (varList is List) {
        final vars = varList.map((e) => e.toString()).toSet();
        if (mounted &&
            (vars.length != _detectedVars.length ||
                !vars.containsAll(_detectedVars))) {
          // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

          setState(() => _detectedVars = vars);
        }
      }
    } else if (type == 'request-insert-var') {
      _insertVariable();
    }
  }

  // Mục đích: Phương thức `_getContentHtml` triển khai phần việc `get Content Html` trong flutter_frontend/lib/screens/templates/template_form_screen.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  Future<String> _getContentHtml() async {
    if (!_editorReady) return '';
    final reqId = DateTime.now().millisecondsSinceEpoch.toString();
    final completer = Completer<String>();
    late StreamSubscription sub;
    sub = html.window.onMessage.listen((event) {
      final data = event.data;
      if (data is Map && data['type'] == 'content' && data['reqId'] == reqId) {
        sub.cancel();
        if (!completer.isCompleted)
          completer.complete(data['html'] as String? ?? '');
      }
    });
    _editorIframe?.contentWindow
        ?.postMessage({'type': 'get-content', 'reqId': reqId}, '*');
    return completer.future.timeout(
      const Duration(seconds: 5),
      onTimeout: () {
        sub.cancel();
        return '';
      },
    );
  }

  Future<String> _resolveTemplateContentForPersist() async {
    var content =
        _isDocxMode ? _editorContentFallback : await _getContentHtml();
    if (content.trim().isEmpty && _editorContentFallback.trim().isNotEmpty) {
      content = _editorContentFallback;
    }
    return content;
  }

  Map<String, dynamic> _buildTemplateWriteData({
    required String content,
    String? changeNote,
  }) {
    final effectiveDate = _effectiveDate?.toIso8601String().substring(0, 10);
    final endDate = _endDate?.toIso8601String().substring(0, 10);
    // Phase 3 sharing roadmap: visibility/group/audience deu duoc quan ly qua
    // ShareGrant (UnifiedShareSheet). Form nay chi luu metadata co ban.
    // Create mode mac dinh luu private de backend khong tao grant kieu cu.
    // Edit mode khong ghi de visibility hien co, tranh keo scope ve private
    // khi user dang quan ly chia se o UnifiedShareSheet.
    return <String, dynamic>{
      'title': _titleCtrl.text.trim(),
      'description': _descCtrl.text.trim(),
      'content': content,
      'source_type': _mode == _CreateMode.manual ? 'manual' : 'docx',
      if (widget.id == null) 'visibility': 'private',
      'notes': _notesCtrl.text.trim(),
      'tags': _tags,
      if (effectiveDate != null) 'effective_date': effectiveDate,
      if (endDate != null) 'end_date': endDate,
      if (widget.id != null && (changeNote ?? '').trim().isNotEmpty)
        'change_note': changeNote!.trim(),
    };
  }

  Future<int?> _persistTemplateDraft({
    required bool navigateOnSuccess,
  }) async {
    if (!_formKey.currentState!.validate()) return null;
    if (!_validateDateRange()) return null;
    // Phase 3 sharing: khong con can validate group_id boi visibility o tang form,
    // viec chia se duoc UnifiedShareSheet va backend ShareGrant lo.

    final totalStopwatch = Stopwatch()..start();
    debugPrint(
      '[template_persist] start | template_id=${widget.id} | mode=$_mode | has_local_docx=$_hasLocalDocxBytes',
    );

    final editorReadStartedMs = totalStopwatch.elapsedMilliseconds;
    final content = await _resolveTemplateContentForPersist();
    final editorReadElapsedMs =
        totalStopwatch.elapsedMilliseconds - editorReadStartedMs;
    final data = _buildTemplateWriteData(
      content: content,
      changeNote: _changeNoteCtrl.text.trim(),
    );

    if (widget.id == null) {
      if (_isDocxMode && !_hasLocalDocxBytes) {
        throw Exception(
            'Mau DOCX moi phai giu kem file DOCX goc truoc khi luu.');
      }
      final payload = _isDocxMode
          ? _buildDocxFormData(
              title: _titleCtrl.text.trim(),
              description: _descCtrl.text.trim(),
              content: content,
              visibility: 'private',
              groupId: null,
              audienceUserIds: const [],
              notes: _notesCtrl.text.trim(),
              tags: _tags,
              effectiveDate: data['effective_date'] as String?,
              endDate: data['end_date'] as String?,
              docxBytes: _docxFileBytes!,
            )
          : data;
      debugPrint(
        '[template_persist] request_prepare | template_id=${widget.id} | create=true | editor_read_elapsed_ms=$editorReadElapsedMs | content_chars=${content.length}',
      );
      final response = await ApiClient().dio.post('templates/', data: payload);
      final newId = response.data['id'] as int;
      _templateIdForTagGen = newId;
      _refreshTemplateCollections(newId);
      if (navigateOnSuccess && mounted) {
        context.go('/templates/$newId');
      }
      return newId;
    }

    debugPrint(
      '[template_persist] request_prepare | template_id=${widget.id} | create=false | editor_read_elapsed_ms=$editorReadElapsedMs | content_chars=${content.length}',
    );
    final response = await ApiClient().dio.patch(
          'templates/${widget.id}/',
          data: data,
        );
    final savedId = (response.data['id'] ?? widget.id) as int;
    _refreshTemplateCollections(widget.id!);
    if (navigateOnSuccess && mounted) {
      context.go('/templates/$savedId');
    }
    return savedId;
  }

  Future<void> _openTemplateManualEditor() async {
    if (_manualEditLaunching) return;
    setState(() => _manualEditLaunching = true);
    try {
      final templateId = await _persistTemplateDraft(navigateOnSuccess: false);
      if (templateId == null || !mounted) {
        return;
      }
      context.go('/templates/$templateId/manual-edit?return_to=edit');
    } on DioException catch (e) {
      final serverData = e.response?.data;
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(
              '${_pick('Không mở được trình chỉnh sửa thủ công', 'Unable to open the manual editor')}: ${serverData ?? e.message ?? e}',
            ),
            backgroundColor: Colors.red,
          ),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(
              '${_pick('Không mở được trình chỉnh sửa thủ công', 'Unable to open the manual editor')}: $e',
            ),
            backgroundColor: Colors.red,
          ),
        );
      }
    } finally {
      if (mounted) {
        setState(() => _manualEditLaunching = false);
      }
    }
  }

  bool get _manualEditIsBusy =>
      _loading || _manualEditLaunching || _importing || _replacingDocx;

  bool get _manualEditRequiresDraftPersist => widget.id == null || _isDocxMode;

  String _manualEditActionLabel(bool isEdit) {
    if (_manualEditLaunching) {
      return _pick('Đang mở trình chỉnh sửa...', 'Opening editor...');
    }
    if (_manualEditRequiresDraftPersist) {
      return isEdit
          ? _pick(
              'Lưu thay đổi rồi mở trình chỉnh sửa thủ công',
              'Save changes and open the manual editor',
            )
          : _pick(
              'Lưu nháp rồi mở trình chỉnh sửa thủ công',
              'Save draft and open the manual editor',
            );
    }
    return _pick('Mở trình chỉnh sửa thủ công', 'Open the manual editor');
  }

  String _manualEditSupportText(bool isEdit) {
    if (_isDocxMode) {
      return _pick(
        'Bạn có thể sửa trực tiếp nội dung mẫu DOCX bằng cùng công nghệ chỉnh sửa thủ công như văn bản, thay vì chỉ upload DOCX mới.',
        'You can edit the DOCX template content directly with the same manual editing stack used for documents, instead of only uploading a new DOCX.',
      );
    }
    if (isEdit) {
      return _pick(
        'Nếu cần chỉnh bố cục Word chi tiết hơn vùng soạn thảo HTML, hãy mở trình chỉnh sửa thủ công để sửa như một tài liệu Word thực thụ.',
        'If you need Word layout control beyond the HTML editor, open the manual editor to work with it like a real Word document.',
      );
    }
    return _pick(
      'Bạn có thể tiếp tục soạn ngay trên form này hoặc lưu nháp rồi chuyển sang trình chỉnh sửa thủ công để hoàn thiện bố cục Word chi tiết hơn.',
      'You can keep drafting in this form or save a draft first, then move to the manual editor for more detailed Word layout refinement.',
    );
  }

  Widget _buildManualEditLaunchCard(BuildContext context, bool isEdit) {
    final isCompact = MediaQuery.of(context).size.width < 720;
    final accent = const Color(0xFF0F766E);
    return Container(
      width: double.infinity,
      margin: const EdgeInsets.only(top: 12),
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: const Color(0xFFF0FDFA),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: const Color(0xFF99F6E4)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Container(
                width: 32,
                height: 32,
                decoration: BoxDecoration(
                  color: const Color(0xFFCCFBF1),
                  borderRadius: BorderRadius.circular(10),
                ),
                child: const Icon(
                  Icons.edit_document,
                  size: 18,
                  color: Color(0xFF115E59),
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Chỉnh sửa thủ công bằng Word',
                      style: Theme.of(context).textTheme.titleSmall?.copyWith(
                            fontWeight: FontWeight.w700,
                            color: const Color(0xFF134E4A),
                          ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      _manualEditSupportText(isEdit),
                      style: const TextStyle(
                        fontSize: 12.5,
                        height: 1.45,
                        color: Color(0xFF115E59),
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          Wrap(
            spacing: 10,
            runSpacing: 10,
            children: [
              SizedBox(
                width: isCompact ? double.infinity : null,
                child: FilledButton.icon(
                  onPressed:
                      _manualEditIsBusy ? null : _openTemplateManualEditor,
                  icon: _manualEditLaunching
                      ? const SizedBox(
                          width: 16,
                          height: 16,
                          child: CircularProgressIndicator(
                            strokeWidth: 2,
                            color: Colors.white,
                          ),
                        )
                      : const Icon(Icons.open_in_new, size: 16),
                  label: Text(_manualEditActionLabel(isEdit)),
                  style: FilledButton.styleFrom(
                    backgroundColor: accent,
                    padding: const EdgeInsets.symmetric(
                      horizontal: 14,
                      vertical: 12,
                    ),
                  ),
                ),
              ),
              SizedBox(
                width: isCompact ? double.infinity : null,
                child: OutlinedButton.icon(
                  onPressed: _manualEditIsBusy ? null : _save,
                  icon: const Icon(Icons.save_outlined, size: 16),
                  label: Text(
                    isEdit
                        ? _pick('Lưu mẫu hiện tại', 'Save current template')
                        : _pick('Lưu nháp trên form', 'Save draft in form'),
                  ),
                  style: OutlinedButton.styleFrom(
                    foregroundColor: accent,
                    side: const BorderSide(color: Color(0xFF5EEAD4)),
                    padding: const EdgeInsets.symmetric(
                      horizontal: 14,
                      vertical: 12,
                    ),
                  ),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildTemplatePdfPreviewCard(BuildContext context, tmpl) {
    final isCompact = MediaQuery.of(context).size.width < 720;
    final previewHeight = isCompact ? 420.0 : 560.0;

    if (_templatePreviewPdfUrl == null &&
        !_templatePreviewLoading &&
        _templatePreviewLoadError == null) {
      WidgetsBinding.instance
          .addPostFrameCallback((_) => _loadTemplatePreview(tmpl));
    }

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: const Color(0xFFE2E8F0)),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.04),
            blurRadius: 10,
            offset: const Offset(0, 3),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Wrap(
            spacing: 10,
            runSpacing: 10,
            crossAxisAlignment: WrapCrossAlignment.center,
            children: [
              Text(
                _pick('Bản xem PDF của mẫu', 'Template PDF preview'),
                style: Theme.of(context).textTheme.titleSmall?.copyWith(
                      fontWeight: FontWeight.w700,
                    ),
              ),
              OutlinedButton.icon(
                onPressed: () => _loadTemplatePreview(tmpl, force: true),
                icon: const Icon(Icons.refresh, size: 16),
                label: Text(_pick('Tải lại', 'Reload')),
              ),
              if (_templatePreviewPdfUrl != null &&
                  _templatePreviewPdfUrl!.isNotEmpty)
                OutlinedButton.icon(
                  onPressed: () => _openTemplatePreviewDialog(tmpl),
                  icon: const Icon(Icons.open_in_full, size: 16),
                  label: Text(_pick('Toàn màn hình', 'Full screen')),
                ),
              if (_templatePreviewPdfUrl != null &&
                  _templatePreviewPdfUrl!.isNotEmpty)
                OutlinedButton.icon(
                  onPressed: _openTemplatePreviewPdfInNewTab,
                  icon: const Icon(Icons.picture_as_pdf_outlined, size: 16),
                  label: Text(_pick('Mở PDF', 'Open PDF')),
                ),
            ],
          ),
          const SizedBox(height: 8),
          Text(
            _pick(
              'Bản xem này có nút tải lại thủ công và sẽ tự động cập nhật mỗi 10 giây sau khi PDF đã hiển thị thành công.',
              'This preview supports manual reload and will auto-refresh every 10 seconds after the PDF loads successfully.',
            ),
            style: TextStyle(
              fontSize: 12.5,
              height: 1.45,
              color: Colors.grey.shade700,
            ),
          ),
          const SizedBox(height: 12),
          if (_templatePreviewLoading)
            const SizedBox(
              height: 240,
              child: Center(child: CircularProgressIndicator()),
            )
          else if (_templatePreviewLoadError != null)
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(14),
              decoration: BoxDecoration(
                color: const Color(0xFFFEF2F2),
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: const Color(0xFFFECACA)),
              ),
              child: Text(
                _templatePreviewLoadError!,
                style: const TextStyle(
                  color: Color(0xFF7F1D1D),
                  height: 1.45,
                ),
              ),
            )
          else if (_templatePreviewPdfUrl != null &&
              _templatePreviewPdfUrl!.isNotEmpty)
            SizedBox(
              height: previewHeight,
              child: WebPdfFrame(
                viewKey:
                    'template-form-preview-${widget.id}-$_templatePreviewFrameKey',
                pdfUrl: _templatePreviewPdfUrl!,
              ),
            )
          else
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(14),
              decoration: BoxDecoration(
                color: const Color(0xFFF8FAFC),
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: const Color(0xFFCBD5E1)),
              ),
              child: Text(
                _pick(
                  'Lưu nháp hoặc tải lại bản xem để hệ thống tạo PDF mới nhất cho mẫu văn bản.',
                  'Save a draft or reload the preview so the system can generate the latest PDF for the template.',
                ),
                style: TextStyle(color: Color(0xFF334155), height: 1.45),
              ),
            ),
        ],
      ),
    );
  }

  static String _buildEditorHtml() => '''<!DOCTYPE html>
<html><head><meta charset="UTF-8">
<style>
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: 'Times New Roman', serif; display: flex; flex-direction: column; height: 100vh; overflow: hidden; background: #e8e8e8; }
.toolbar { background: #fff; border-bottom: 2px solid #e0e0e0; padding: 5px 10px; display: flex; flex-wrap: wrap; gap: 3px; align-items: center; flex-shrink: 0; box-shadow: 0 1px 4px rgba(0,0,0,0.08); }
.toolbar select { border: 1px solid #ccc; border-radius: 4px; padding: 1px 4px; font-size: 12px; height: 26px; background: #fff; cursor: pointer; outline: none; }
.toolbar select:hover, .toolbar select:focus { border-color: #1565c0; }
.toolbar button { background: #fff; border: 1px solid #ccc; border-radius: 4px; padding: 0 7px; cursor: pointer; font-size: 13px; height: 26px; min-width: 26px; display: inline-flex; align-items: center; justify-content: center; outline: none; }
.toolbar button:hover { background: #e8f0fe; border-color: #1565c0; color: #1565c0; }
.toolbar button.active { background: #c5d8f9; border-color: #1565c0; color: #0d47a1; }
.sep { width: 1px; height: 20px; background: #e0e0e0; margin: 0 3px; flex-shrink: 0; }
.var-btn { background: #e8f5e9 !important; border-color: #4caf50 !important; color: #2e7d32 !important; font-family: monospace; font-size: 12px; font-weight: bold; padding: 0 10px !important; }
.var-btn:hover { background: #c8e6c9 !important; }
#page-wrapper { flex: 1; overflow-y: auto; background: #e0e0e0; padding: 20px; }
#editor { background: white; min-height: calc(100vh - 80px); padding: 20mm 20mm 20mm 25mm; font-family: 'Times New Roman', Times, serif; font-size: 14pt; line-height: 1.7; outline: none; box-shadow: 0 2px 8px rgba(0,0,0,0.15); word-wrap: break-word; }
#editor p { margin: 0 0 4px 0; }
#editor:focus { outline: none; }
</style></head><body>
<div class="toolbar">
  <select id="selFont" title="Font chữ" onchange="execCmd('fontName', this.value)">
    <option value="Times New Roman" selected>Times New Roman</option>
    <option value="Arial">Arial</option><option value="Calibri">Calibri</option>
    <option value="Courier New">Courier New</option><option value="Verdana">Verdana</option>
  </select>
  <select id="selSize" title="Cỡ chữ" onchange="setFontSize(this.value)">
    <option value="10">10</option><option value="11">11</option><option value="12">12</option>
    <option value="13">13</option><option value="14" selected>14</option><option value="16">16</option>
    <option value="18">18</option><option value="24">24</option><option value="28">28</option><option value="36">36</option>
  </select>
  <div class="sep"></div>
  <button id="btnBold" onclick="execCmd('bold')" title="Đậm (Ctrl+B)"><b>B</b></button>
  <button id="btnItalic" onclick="execCmd('italic')" title="Nghiêng (Ctrl+I)"><i>I</i></button>
  <button id="btnUnder" onclick="execCmd('underline')" title="Gạch chân (Ctrl+U)"><u>U</u></button>
  <button id="btnStrike" onclick="execCmd('strikeThrough')" title="Gạch giữa"><s>S</s></button>
  <div class="sep"></div>
  <button onclick="execCmd('justifyLeft')" title="Căn trái">&#8676;</button>
  <button onclick="execCmd('justifyCenter')" title="Căn giữa">&#8803;</button>
  <button onclick="execCmd('justifyRight')" title="Căn phải">&#8677;</button>
  <button onclick="execCmd('justifyFull')" title="Căn đều">&#8801;</button>
  <div class="sep"></div>
  <button onclick="execCmd('insertUnorderedList')" title="Danh sách dấu">&#8226;&#8801;</button>
  <button onclick="execCmd('insertOrderedList')" title="Danh sách số">1&#8801;</button>
  <button onclick="execCmd('outdent')" title="Giảm thụt lề">&#8676;</button>
  <button onclick="execCmd('indent')" title="Tăng thụt lề">&#8677;</button>
  <div class="sep"></div>
  <button onclick="execCmd('undo')" title="Hoàn tác (Ctrl+Z)">&#8630;</button>
  <button onclick="execCmd('redo')" title="Làm lại (Ctrl+Y)">&#8631;</button>
  <div class="sep"></div>
  <button class="var-btn" onclick="reqVar()" title="Chèn biến tự động vào vị trí con trỏ">+&#123;&#123;biến&#125;&#125;</button>
</div>
<div id="page-wrapper"><div id="editor" contenteditable="true" spellcheck="false"></div></div>
<script>
(function(){
  var ed = document.getElementById('editor');
  var tb = document.querySelector('.toolbar');
  var nt = null;
  var readOnly = false;
  function applyReadOnly(){
    ed.contentEditable = readOnly ? 'false' : 'true';
    if(tb){
      tb.querySelectorAll('button,select').forEach(function(el){
        el.disabled = readOnly;
      });
    }
  }
  function execCmd(c,v){ ed.focus(); document.execCommand(c,false,v!==undefined?v:null); updateTb(); sched(); }
  function setFontSize(pt){
    ed.focus();
    var sel=window.getSelection();
    if(sel&&sel.rangeCount>0&&!sel.isCollapsed){
      document.execCommand('styleWithCSS',false,true);
      document.execCommand('fontSize',false,'7');
      document.execCommand('styleWithCSS',false,false);
      ed.querySelectorAll('font[size="7"]').forEach(function(f){
        var sp=document.createElement('span'); sp.style.fontSize=pt+'pt';
        while(f.firstChild) sp.appendChild(f.firstChild);
        f.parentNode.replaceChild(sp,f);
      });
    }
    updateTb(); sched();
  }
  function updateTb(){
    document.getElementById('btnBold').classList.toggle('active',document.queryCommandState('bold'));
    document.getElementById('btnItalic').classList.toggle('active',document.queryCommandState('italic'));
    document.getElementById('btnUnder').classList.toggle('active',document.queryCommandState('underline'));
    document.getElementById('btnStrike').classList.toggle('active',document.queryCommandState('strikeThrough'));
  }
  function sched(){ if(nt) clearTimeout(nt); nt=setTimeout(notify,300); }
  function notify(){
    var vars=[]; var re=/\\{\\{(\\w+)\\}\\}/g; var t=ed.innerText||''; var m;
    while((m=re.exec(t))!==null){ if(vars.indexOf(m[1])===-1) vars.push(m[1]); }
    window.parent.postMessage({type:'content-changed',html:ed.innerHTML,vars:vars},'*');
  }
  function reqVar(){ window.parent.postMessage({type:'request-insert-var'},'*'); }
  ed.addEventListener('keyup',updateTb);
  ed.addEventListener('mouseup',updateTb);
  ed.addEventListener('input',sched);
  ed.addEventListener('keydown',function(e){
    if(e.ctrlKey||e.metaKey){
      switch(e.key.toLowerCase()){
        case 'b': e.preventDefault(); execCmd('bold'); break;
        case 'i': e.preventDefault(); execCmd('italic'); break;
        case 'u': e.preventDefault(); execCmd('underline'); break;
        case 'z': e.preventDefault(); execCmd(e.shiftKey?'redo':'undo'); break;
        case 'y': e.preventDefault(); execCmd('redo'); break;
      }
    }
  });
  window.addEventListener('message',function(e){
    if(!e.data||typeof e.data!=='object') return;
    var d=e.data;
    if(d.type==='set-content'){ ed.innerHTML=d.html||''; notify(); }
    else if(d.type==='set-read-only'){ readOnly=!!d.value; applyReadOnly(); }
    else if(d.type==='insert-text'){ ed.focus(); document.execCommand('insertText',false,d.text); sched(); }
    else if(d.type==='get-content'){ window.parent.postMessage({type:'content',html:ed.innerHTML,reqId:d.reqId},'*'); }
  });
  applyReadOnly();
  window.parent.postMessage({type:'editor-ready'},'*');
})();
</script></body></html>''';

  Set<String> _detectVars(String content) {
    final re = RegExp(r'\{\{(\w+)\}\}');
    return re.allMatches(content).map((m) => m.group(1)!).toSet();
  }

  // ── PREFILL (edit mode) ───────────────────────────────────────────────────

  // Mục đích: Phương thức `_prefillFromTemplate` triển khai phần việc `prefill From Template` trong flutter_frontend/lib/screens/templates/template_form_screen.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  void _prefillFromTemplate(tmpl) {
    if (_initialized) return;
    _initialized = true;
    _mode =
        tmpl.sourceType == 'docx' ? _CreateMode.uploadDocx : _CreateMode.manual;
    _templateHasDocxSource = tmpl.hasDocxSource == true;
    _docxFileBytes = null;
    _docxFileName = null;
    _titleCtrl.text = tmpl.title;
    _descCtrl.text = tmpl.description;
    _notesCtrl.text = '';
    _visibility = tmpl.visibility;
    _selectedGroupId = tmpl.groupId;
    _selectedAudienceUserIds
      ..clear()
      ..addAll(tmpl.audienceUserIds);
    _editTitle = tmpl.title;
    _tags = List<String>.from(tmpl.tags ?? []);
    _templateIdForTagGen = tmpl.id;
    if (tmpl.effectiveDate != null)
      _effectiveDate = DateTime.tryParse(tmpl.effectiveDate!);
    if (tmpl.endDate != null) _endDate = DateTime.tryParse(tmpl.endDate!);
    final content = tmpl.content ?? '';
    _setEditorContent(content);
    _setEditorReadOnly(_isDocxMode);
    _detectedVars = _detectVars(content);
    if (_visibility == 'group' && _selectedGroupId != null) {
      unawaited(_loadGroupMembers(_selectedGroupId));
    }
    // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

    setState(() {});
  }

  // Mục đích: Phương thức `_loadGroupMembers` triển khai phần việc `load Group Members` trong flutter_frontend/lib/screens/templates/template_form_screen.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  Future<void> _loadGroupMembers(int? groupId) async {
    if (groupId == null) {
      if (!mounted) return;
      // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

      setState(() {
        _groupMembers = const [];
        _selectedAudienceUserIds.clear();
        _groupMembersLoading = false;
      });
      return;
    }
    // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

    setState(() => _groupMembersLoading = true);
    try {
      // Gọi API hoặc tác vụ bất đồng bộ rồi chờ kết quả trước khi cập nhật giao diện.

      final resp = await ApiClient().dio.get(
        'templates/group-members/',
        queryParameters: {'group_id': groupId},
      );
      final members = (resp.data as List)
          .map((item) =>
              _GroupMemberOption.fromJson(item as Map<String, dynamic>))
          .toList();
      if (!mounted) return;
      // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

      setState(() {
        _groupMembers = members;
        _selectedAudienceUserIds.removeWhere(
          (userId) => !members.any((member) => member.id == userId),
        );
        _groupMembersLoading = false;
      });
    } catch (_) {
      if (!mounted) return;
      // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

      setState(() {
        _groupMembers = const [];
        _selectedAudienceUserIds.clear();
        _groupMembersLoading = false;
      });
    }
  }

  // Mục đích: Phương thức `_pickAudienceUsers` triển khai phần việc `pick Audience Users` trong flutter_frontend/lib/screens/templates/template_form_screen.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  // ignore: unused_element
  Future<void> _pickAudienceUsers() async {
    if (_selectedGroupId == null) return;
    if (_groupMembers.isEmpty && !_groupMembersLoading) {
      await _loadGroupMembers(_selectedGroupId);
    }
    if (!mounted) return;
    final tempSelected = <int>{..._selectedAudienceUserIds};
    final searchCtrl = TextEditingController();
    await showDialog<void>(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, setModalState) {
          final query = searchCtrl.text.trim().toLowerCase();
          final filtered = _groupMembers.where((member) {
            if (query.isEmpty) return true;
            final haystack =
                '${member.username} ${member.fullName} ${member.role}'
                    .toLowerCase();
            return haystack.contains(query);
          }).toList();
          return AlertDialog(
            title:
                Text(_pick('Chọn người được dùng mẫu', 'Choose allowed users')),
            content: SizedBox(
              width: 520,
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  TextField(
                    controller: searchCtrl,
                    decoration: InputDecoration(
                      hintText: _pick(
                        'Tìm theo tên, tài khoản, vai trò...',
                        'Search by name, username, role...',
                      ),
                      prefixIcon: Icon(Icons.search),
                      border: OutlineInputBorder(),
                    ),
                    onChanged: (_) => setModalState(() {}),
                  ),
                  const SizedBox(height: 12),
                  Align(
                    alignment: Alignment.centerLeft,
                    child: TextButton.icon(
                      onPressed: () => setModalState(tempSelected.clear),
                      icon: const Icon(Icons.groups_outlined, size: 16),
                      label: Text(_pick(
                        'Để trống để cả nhóm được dùng',
                        'Leave empty to allow the whole group',
                      )),
                    ),
                  ),
                  const SizedBox(height: 8),
                  Flexible(
                    child: _groupMembersLoading
                        ? const Center(child: CircularProgressIndicator())
                        : ListView.builder(
                            shrinkWrap: true,
                            itemCount: filtered.length,
                            itemBuilder: (context, index) {
                              final member = filtered[index];
                              final selected = tempSelected.contains(member.id);
                              return CheckboxListTile(
                                value: selected,
                                dense: true,
                                controlAffinity:
                                    ListTileControlAffinity.leading,
                                title: Text(member.displayLabel),
                                subtitle: Text(
                                  member.role == 'leader'
                                      ? _pick('Trưởng nhóm', 'Leader')
                                      : _pick('Thành viên', 'Member'),
                                ),
                                onChanged: (value) {
                                  setModalState(() {
                                    if (value == true) {
                                      tempSelected.add(member.id);
                                    } else {
                                      tempSelected.remove(member.id);
                                    }
                                  });
                                },
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
                child: Text(_pick('Hủy', 'Cancel')),
              ),
              FilledButton(
                onPressed: () {
                  // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

                  setState(() {
                    _selectedAudienceUserIds
                      ..clear()
                      ..addAll(tempSelected);
                  });
                  Navigator.pop(ctx);
                },
                child: Text(_pick('Áp dụng', 'Apply')),
              ),
            ],
          );
        },
      ),
    );
    searchCtrl.dispose();
  }

  // ── AUTO-GENERATE TAGS ────────────────────────────────────────────────────

  // Mục đích: Phương thức `_generateTags` triển khai phần việc `generate Tags` trong flutter_frontend/lib/screens/templates/template_form_screen.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  Future<void> _generateTags() async {
    final id = _templateIdForTagGen ?? widget.id;
    if (id == null) {
      // Not saved yet — save first
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(_pick(
            'Hãy lưu mẫu trước khi tự động tạo tags.',
            'Save the template before generating tags automatically.',
          )),
        ),
      );
      return;
    }
    // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

    setState(() => _generatingTags = true);
    try {
      // Gọi API hoặc tác vụ bất đồng bộ rồi chờ kết quả trước khi cập nhật giao diện.

      final resp = await ApiClient().dio.post(
            'templates/$id/generate-tags/',
            options: ApiClient.ollamaOptions(),
          );
      final newTags = List<String>.from(resp.data['tags'] ?? []);
      // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

      setState(() {
        // Merge without duplicates
        for (final t in newTags) {
          if (!_tags.contains(t)) _tags.add(t);
        }
      });
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content:
                Text('${_pick('Lỗi tạo tags', 'Tag generation error')}: $e'),
            backgroundColor: Colors.red,
          ),
        );
      }
    } finally {
      // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

      if (mounted) setState(() => _generatingTags = false);
    }
  }

  // ── REPLACE WITH DOCX (edit mode) ────────────────────────────────────────

  // Mục đích: Phương thức `_replaceWithDocx` triển khai phần việc `replace With Docx` trong flutter_frontend/lib/screens/templates/template_form_screen.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  Future<void> _replaceWithDocx() async {
    final id = widget.id;
    if (id == null) return;

    final result = await FilePicker.platform.pickFiles(
      type: FileType.custom,
      allowedExtensions: ['docx'],
      withData: true,
    );
    if (result == null || result.files.isEmpty) return;
    final file = result.files.first;
    if (file.bytes == null) return;

    // Ask for change note
    final changeNoteCtrl = TextEditingController();
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text(_pick(
            'Thay thế bằng file DOCX mới', 'Replace with a new DOCX file')),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('${_pick('File', 'File')}: ${file.name}',
                style:
                    const TextStyle(fontSize: 13, fontWeight: FontWeight.w500)),
            const SizedBox(height: 4),
            Text(
              _pick(
                'Nội dung cũ sẽ được lưu thành phiên bản mới. AI sẽ tự động nhận diện biến.',
                'The current content will be saved as a new version. AI will automatically detect variables.',
              ),
              style: TextStyle(fontSize: 12, color: Colors.grey.shade600),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: changeNoteCtrl,
              decoration: InputDecoration(
                labelText: _pick(
                    'Ghi chú thay đổi (tùy chọn)', 'Change note (optional)'),
                border: OutlineInputBorder(),
                isDense: true,
              ),
            ),
          ],
        ),
        actions: [
          TextButton(
              onPressed: () => Navigator.pop(ctx, false),
              child: Text(_pick('Hủy', 'Cancel'))),
          FilledButton(
              onPressed: () => Navigator.pop(ctx, true),
              child: Text(_pick('Thay thế', 'Replace'))),
        ],
      ),
    );

    if (confirmed != true) {
      changeNoteCtrl.dispose();
      return;
    }

    // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

    setState(() {
      _replacingDocx = true;
      _replaceDocxStatus = _pick('Đang xử lý file DOCX với AI...',
          'Processing the DOCX file with AI...');
    });

    try {
      final formData = FormData.fromMap({
        'docx_file': MultipartFile.fromBytes(file.bytes!, filename: file.name),
        'change_note': changeNoteCtrl.text.trim(),
      });
      changeNoteCtrl.dispose();

      // Gọi API hoặc tác vụ bất đồng bộ rồi chờ kết quả trước khi cập nhật giao diện.

      final resp = await ApiClient().dio.post(
            'templates/$id/replace-docx/',
            data: formData,
            options:
                ApiClient.ollamaOptions(contentType: 'multipart/form-data'),
          );
      final newContent = resp.data['content'] as String? ?? '';
      final detectedVars = (resp.data['detected_vars'] as List? ?? [])
          .map((e) => e.toString())
          .toSet();
      final newVersion = resp.data['version'] as String? ?? '';

      _setEditorContent(_toEditorHtml(newContent));
      _resetTemplatePreviewState();
      // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

      setState(() {
        _detectedVars = detectedVars;
        _replaceDocxStatus = _pick(
          'Đã thay thế thành công. Phiên bản mới: $newVersion • ${detectedVars.length} biến',
          'Replacement completed. New version: $newVersion • ${detectedVars.length} variables',
        );
      });

      _refreshTemplateCollections(id);
    } catch (e) {
      if (mounted) {
        // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

        setState(() => _replaceDocxStatus = '${_pick('Lỗi', 'Error')}: $e');
      }
    } finally {
      // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

      if (mounted) setState(() => _replacingDocx = false);
    }
  }

  // ── DATE PICKER ───────────────────────────────────────────────────────────

  // Mục đích: Phương thức `_pickDate` triển khai phần việc `pick Date` trong flutter_frontend/lib/screens/templates/template_form_screen.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  Future<void> _pickDate({required bool isEffective}) async {
    final now = DateTime.now();
    final initialDate = (isEffective ? _effectiveDate : _endDate) ?? now;
    html.document.activeElement?.blur();
    await Future<void>.delayed(const Duration(milliseconds: 20));
    final picked = await _showStyledDatePicker(
      context: context,
      label: isEffective
          ? _pick('Ngày hiệu lực', 'Effective date')
          : _pick('Ngày hết hạn', 'Expiration date'),
      initialDate: initialDate,
      firstDate: DateTime(2020),
      lastDate: DateTime(2035),
    );
    if (picked != null && mounted) {
      // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

      setState(() {
        if (isEffective) {
          _effectiveDate = picked;
        } else {
          _endDate = picked;
        }
      });
    }
  }

  // Mục đích: Phương thức `_showStyledDatePicker` triển khai phần việc `show Styled Date Picker` trong flutter_frontend/lib/screens/templates/template_form_screen.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  Future<DateTime?> _showStyledDatePicker({
    required BuildContext context,
    required String label,
    required DateTime initialDate,
    required DateTime firstDate,
    required DateTime lastDate,
  }) async {
    DateTime selectedDate = initialDate;

    return showDialog<DateTime>(
      context: context,
      barrierDismissible: true,
      builder: (dialogContext) {
        final theme = Theme.of(dialogContext);

        return Dialog(
          elevation: 0,
          insetPadding:
              const EdgeInsets.symmetric(horizontal: 16, vertical: 24),
          backgroundColor: Colors.transparent,
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 420),
            child: StatefulBuilder(
              builder: (context, setDialogState) {
                return Container(
                  decoration: BoxDecoration(
                    color: Colors.white,
                    borderRadius: BorderRadius.circular(28),
                    boxShadow: const [
                      BoxShadow(
                        color: Color(0x1F102A43),
                        blurRadius: 36,
                        offset: Offset(0, 18),
                      ),
                    ],
                  ),
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Container(
                        width: double.infinity,
                        padding: const EdgeInsets.fromLTRB(20, 20, 20, 18),
                        decoration: const BoxDecoration(
                          borderRadius:
                              BorderRadius.vertical(top: Radius.circular(28)),
                          gradient: LinearGradient(
                            begin: Alignment.topLeft,
                            end: Alignment.bottomRight,
                            colors: [Color(0xFF0F4C81), Color(0xFF2B6CB0)],
                          ),
                        ),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Container(
                              padding: const EdgeInsets.symmetric(
                                  horizontal: 10, vertical: 6),
                              decoration: BoxDecoration(
                                color: Colors.white.withOpacity(0.16),
                                borderRadius: BorderRadius.circular(999),
                              ),
                              child: Text(
                                label,
                                style: const TextStyle(
                                  fontSize: 12,
                                  fontWeight: FontWeight.w700,
                                  color: Colors.white,
                                ),
                              ),
                            ),
                            const SizedBox(height: 14),
                            Text(
                              DateFormat('dd/MM/yyyy').format(selectedDate),
                              style: const TextStyle(
                                fontSize: 28,
                                fontWeight: FontWeight.w700,
                                color: Colors.white,
                                letterSpacing: -0.5,
                              ),
                            ),
                            const SizedBox(height: 4),
                            Text(
                              DateFormat('EEEE, dd MMMM yyyy')
                                  .format(selectedDate),
                              style: TextStyle(
                                fontSize: 13,
                                color: Colors.white.withOpacity(0.86),
                              ),
                            ),
                          ],
                        ),
                      ),
                      Padding(
                        padding: const EdgeInsets.fromLTRB(14, 14, 14, 8),
                        child: Theme(
                          data: theme.copyWith(
                            colorScheme: theme.colorScheme.copyWith(
                              primary: const Color(0xFF1565C0),
                              onPrimary: Colors.white,
                              surface: Colors.white,
                              onSurface: const Color(0xFF102A43),
                            ),
                            textButtonTheme: TextButtonThemeData(
                              style: TextButton.styleFrom(
                                foregroundColor: const Color(0xFF1565C0),
                                textStyle: const TextStyle(
                                    fontWeight: FontWeight.w600),
                              ),
                            ),
                          ),
                          child: CalendarDatePicker(
                            initialDate: selectedDate,
                            firstDate: firstDate,
                            lastDate: lastDate,
                            currentDate: DateTime.now(),
                            onDateChanged: (date) {
                              setDialogState(() => selectedDate = date);
                            },
                          ),
                        ),
                      ),
                      Padding(
                        padding: const EdgeInsets.fromLTRB(18, 0, 18, 18),
                        child: Row(
                          children: [
                            TextButton.icon(
                              onPressed: () {
                                final today = DateTime.now();
                                final clampedToday = today.isBefore(firstDate)
                                    ? firstDate
                                    : today.isAfter(lastDate)
                                        ? lastDate
                                        : today;
                                setDialogState(
                                    () => selectedDate = clampedToday);
                              },
                              icon: const Icon(Icons.today_outlined, size: 18),
                              label: Text(_pick('Hôm nay', 'Today')),
                            ),
                            const Spacer(),
                            TextButton(
                              onPressed: () =>
                                  Navigator.of(dialogContext).pop(),
                              child: Text(_pick('Hủy', 'Cancel')),
                            ),
                            const SizedBox(width: 8),
                            FilledButton(
                              onPressed: () =>
                                  Navigator.of(dialogContext).pop(selectedDate),
                              style: FilledButton.styleFrom(
                                backgroundColor: const Color(0xFF1565C0),
                                foregroundColor: Colors.white,
                                padding: const EdgeInsets.symmetric(
                                    horizontal: 18, vertical: 12),
                                shape: RoundedRectangleBorder(
                                  borderRadius: BorderRadius.circular(12),
                                ),
                              ),
                              child: Text(_pick('Xác nhận', 'Confirm')),
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),
                );
              },
            ),
          ),
        );
      },
    );
  }

  // Mục đích: Phương thức `_buildDateField` triển khai phần việc `build Date Field` trong flutter_frontend/lib/screens/templates/template_form_screen.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  Widget _buildDateField({
    required String label,
    required IconData icon,
    required DateTime? value,
    required VoidCallback onPick,
    required VoidCallback onClear,
  }) {
    final hasValue = value != null;
    final borderColor =
        hasValue ? const Color(0xFF8BB6FF) : const Color(0xFFD9E0EA);
    final iconBg = hasValue ? const Color(0xFFDCEAFF) : const Color(0xFFF3F5F8);
    final titleColor =
        hasValue ? const Color(0xFF1D4E89) : const Color(0xFF5E6B7A);
    final valueColor =
        hasValue ? const Color(0xFF102A43) : const Color(0xFF7B8794);
    final badgeBg =
        hasValue ? const Color(0xFFDFF3E4) : const Color(0xFFF1F3F5);
    final badgeFg =
        hasValue ? const Color(0xFF1B6E3A) : const Color(0xFF6B7280);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Material(
          color: Colors.transparent,
          child: InkWell(
            onTap: onPick,
            borderRadius: BorderRadius.circular(16),
            child: Ink(
              padding: const EdgeInsets.all(14),
              decoration: BoxDecoration(
                gradient: LinearGradient(
                  begin: Alignment.topLeft,
                  end: Alignment.bottomRight,
                  colors: hasValue
                      ? const [Color(0xFFF7FBFF), Color(0xFFEEF5FF)]
                      : const [Color(0xFFFFFFFF), Color(0xFFF7F9FC)],
                ),
                borderRadius: BorderRadius.circular(16),
                border: Border.all(color: borderColor),
                boxShadow: const [
                  BoxShadow(
                    color: Color(0x0F102A43),
                    blurRadius: 16,
                    offset: Offset(0, 8),
                  ),
                ],
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Container(
                        width: 42,
                        height: 42,
                        decoration: BoxDecoration(
                          color: iconBg,
                          borderRadius: BorderRadius.circular(12),
                        ),
                        child: Icon(icon, size: 20, color: titleColor),
                      ),
                      const SizedBox(width: 12),
                      Expanded(
                        child: Text(
                          label,
                          style: TextStyle(
                            fontSize: 13,
                            fontWeight: FontWeight.w700,
                            color: titleColor,
                          ),
                        ),
                      ),
                      Container(
                        padding: const EdgeInsets.symmetric(
                            horizontal: 10, vertical: 6),
                        decoration: BoxDecoration(
                          color: badgeBg,
                          borderRadius: BorderRadius.circular(999),
                        ),
                        child: Text(
                          hasValue ? 'Da chon' : 'Chua chon',
                          style: TextStyle(
                            fontSize: 11,
                            fontWeight: FontWeight.w700,
                            color: badgeFg,
                          ),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 14),
                  Container(
                    width: double.infinity,
                    padding: const EdgeInsets.symmetric(
                        horizontal: 14, vertical: 12),
                    decoration: BoxDecoration(
                      color: Colors.white.withOpacity(0.72),
                      borderRadius: BorderRadius.circular(12),
                      border: Border.all(color: Colors.white.withOpacity(0.9)),
                    ),
                    child: Row(
                      children: [
                        Expanded(
                          child: Text(
                            hasValue
                                ? DateFormat('dd/MM/yyyy').format(value)
                                : 'Bam de chon ngay',
                            style: TextStyle(
                              fontSize: 15,
                              fontWeight: FontWeight.w600,
                              color: valueColor,
                            ),
                          ),
                        ),
                        Icon(
                          Icons.arrow_forward_ios_rounded,
                          size: 14,
                          color: titleColor,
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
        if (hasValue) ...[
          const SizedBox(height: 6),
          Align(
            alignment: Alignment.centerRight,
            child: TextButton(
              onPressed: onClear,
              style: TextButton.styleFrom(
                foregroundColor: const Color(0xFFB42318),
                padding: EdgeInsets.zero,
                minimumSize: const Size(0, 28),
              ),
              child: Text(_pick('Xóa ngày', 'Clear date'),
                  style: const TextStyle(
                      fontSize: 12, fontWeight: FontWeight.w600)),
            ),
          ),
        ],
      ],
    );
  }

  // Mục đích: Phương thức `_pickAndImportDocx` triển khai phần việc `pick And Import Docx` trong flutter_frontend/lib/screens/templates/template_form_screen.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  Future<void> _pickAndImportDocx() async {
    final result = await FilePicker.platform.pickFiles(
      type: FileType.custom,
      allowedExtensions: ['docx'],
      withData: true,
    );
    if (result == null || result.files.isEmpty) return;
    final file = result.files.first;
    if (file.bytes == null) return;
    final fileBytes = file.bytes!;
    final autoDetect = _mode == _CreateMode.uploadDocxDetect;

    // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

    setState(() {
      _importing = true;
      _importStatus = autoDetect
          ? 'Đang phân tích và tự động nhận biến (AI)...'
          : 'Đang đọc file DOCX...';
      _docxFileName = file.name;
    });

    final stopwatch = Stopwatch()..start();
    Timer? debugTimer;
    debugPrint(
      '[template_import_docx] start | file_name=${file.name} | bytes=${fileBytes.length} | mode=$_mode | auto_detect=$autoDetect | endpoint=templates/import-docx/',
    );

    try {
      debugTimer = Timer.periodic(const Duration(seconds: 1), (_) {
        debugPrint(
          '[template_import_docx] processing | file_name=${file.name} | elapsed_s=${stopwatch.elapsed.inSeconds}',
        );
      });
      final requestStartedMs = stopwatch.elapsedMilliseconds;
      final formData = FormData.fromMap({
        'docx_file': MultipartFile.fromBytes(fileBytes, filename: file.name),
        'auto_detect': autoDetect ? 'true' : 'false',
        // Prompt nhận diện biến (chỉ ở chế độ AI detect): ưu tiên prompt đã lưu.
        if (autoDetect && _detectionPromptId != null)
          'detection_prompt_id': _detectionPromptId!,
        if (autoDetect &&
            _detectionPromptId == null &&
            _detectionHintCtrl.text.trim().isNotEmpty)
          'detection_hint': _detectionHintCtrl.text.trim(),
      });
      // Gọi API hoặc tác vụ bất đồng bộ rồi chờ kết quả trước khi cập nhật giao diện.

      final resp = await ApiClient().dio.post(
            'templates/import-docx/',
            data: formData,
            options:
                ApiClient.ollamaOptions(contentType: 'multipart/form-data'),
          );
      final requestElapsedMs = stopwatch.elapsedMilliseconds - requestStartedMs;
      final content = resp.data['content'] as String? ?? '';
      final modifiedDocx = '${resp.data['modified_docx'] ?? ''}'.trim();
      final persistedDocxBytes = modifiedDocx.isNotEmpty
          ? Uint8List.fromList(base64Decode(modifiedDocx))
          : Uint8List.fromList(fileBytes);
      final vars = (resp.data['detected_vars'] as List<dynamic>? ?? [])
          .map((e) => e.toString())
          .toList();
      debugPrint(
        '[template_import_docx] response | file_name=${file.name} | request_elapsed_ms=$requestElapsedMs | content_chars=${content.length} | detected_var_count=${vars.length} | modified_docx_chars=${modifiedDocx.length} | persisted_docx_bytes=${persistedDocxBytes.length} | response_keys=${(resp.data as Map).keys.join(',')}',
      );

      if (_titleCtrl.text.trim().isEmpty) {
        _titleCtrl.text =
            file.name.replaceAll(RegExp(r'\.docx$', caseSensitive: false), '');
      }

      final editorHtml = _toEditorHtml(content);
      _setEditorContent(editorHtml);
      debugTimer.cancel();
      stopwatch.stop();
      debugPrint(
        '[template_import_docx] done | file_name=${file.name} | total_elapsed_ms=${stopwatch.elapsed.inMilliseconds} | editor_html_chars=${editorHtml.length} | detected_vars=${vars.join(',')}',
      );

      // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

      setState(() {
        _importing = false;
        _docxFileBytes = persistedDocxBytes;
        _templateHasDocxSource = true;
        _importStatus =
            'Đã nhập thành công! Phát hiện ${vars.length} biến: ${vars.map((v) => '{{$v}}').join(', ')}';
        _detectedVars = vars.toSet();
      });
      _setEditorReadOnly(true);
    } catch (e) {
      debugTimer?.cancel();
      stopwatch.stop();
      debugPrint(
        '[template_import_docx] failed | file_name=${file.name} | total_elapsed_ms=${stopwatch.elapsed.inMilliseconds} | error=$e',
      );
      // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

      String detail = '$e';
      if (e is DioException && e.response?.data is Map) {
        final d = (e.response!.data as Map)['detail'];
        if (d != null) detail = d.toString();
      }
      setState(() {
        _importing = false;
        _importStatus = 'Lỗi nhập file: $detail';
      });
    }
  }

  // ── INSERT VARIABLE ───────────────────────────────────────────────────────

  // Mục đích: Phương thức `_insertVariable` triển khai phần việc `insert Variable` trong flutter_frontend/lib/screens/templates/template_form_screen.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  Future<void> _insertVariable() async {
    final ctrl = TextEditingController();
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text(_pick('Chèn biến tự động', 'Insert variable')),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            TextField(
              controller: ctrl,
              autofocus: true,
              decoration: InputDecoration(
                labelText: _pick('Tên biến', 'Variable name'),
                hintText: _pick(
                  'vd: ho_ten, ngay_ky, dia_chi',
                  'e.g. full_name, signed_date, address',
                ),
                prefixText: '{{',
                suffixText: '}}',
                border: OutlineInputBorder(),
              ),
              onSubmitted: (_) => Navigator.pop(ctx, true),
            ),
            const SizedBox(height: 8),
            Text(
              _pick(
                'Biến sẽ được chèn tại vị trí con trỏ dưới dạng {{tên_biến}}',
                'The variable will be inserted at the cursor as {{variable_name}}',
              ),
              style: TextStyle(fontSize: 12, color: Colors.grey.shade600),
            ),
          ],
        ),
        actions: [
          TextButton(
              onPressed: () => Navigator.pop(ctx, false),
              child: Text(_pick('Hủy', 'Cancel'))),
          FilledButton(
              onPressed: () => Navigator.pop(ctx, true),
              child: Text(_pick('Chèn', 'Insert'))),
        ],
      ),
    );
    final varName = ctrl.text.trim().replaceAll(RegExp(r'[^a-zA-Z0-9_]'), '_');
    ctrl.dispose();
    if (ok != true || varName.isEmpty) return;

    _editorIframe?.contentWindow
        ?.postMessage({'type': 'insert-text', 'text': '{{$varName}}'}, '*');
  }

  // ── SAVE ──────────────────────────────────────────────────────────────────

  // Mục đích: Phương thức `_save` triển khai phần việc `save` trong flutter_frontend/lib/screens/templates/template_form_screen.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  Future<void> _save() async {
    setState(() => _loading = true);
    try {
      await _persistTemplateDraft(navigateOnSuccess: true);
    } on DioException catch (e) {
      final serverData = e.response?.data;
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(
              '${_pick('Lỗi lưu mẫu', 'Template save error')}: ${serverData ?? e.message ?? e}',
            ),
            backgroundColor: Colors.red,
          ),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('${_pick('Lỗi lưu mẫu', 'Template save error')}: $e'),
            backgroundColor: Colors.red,
          ),
        );
      }
    } finally {
      if (mounted) setState(() => _loading = false);
    }
    return;

    // ignore: dead_code
    if (!_formKey.currentState!.validate()) return;
    if (!_validateDateRange()) return;
    if (_visibility == 'group' && _selectedGroupId == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(_pick(
            'Vui lòng chọn phòng ban/nhóm đích trước khi gửi duyệt.',
            'Choose the target department/group before submitting for approval.',
          )),
          backgroundColor: Colors.red,
        ),
      );
      return;
    }
    // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

    setState(() => _loading = true);
    final totalStopwatch = Stopwatch()..start();
    try {
      debugPrint(
        '[template_save] start | template_id=${widget.id} | mode=$_mode | visibility=$_visibility | has_local_docx=$_hasLocalDocxBytes | selected_audience=${_selectedAudienceUserIds.length} | tags=${_tags.length}',
      );
      final editorReadStartedMs = totalStopwatch.elapsedMilliseconds;
      var content =
          _isDocxMode ? _editorContentFallback : await _getContentHtml();
      final editorReadElapsedMs =
          totalStopwatch.elapsedMilliseconds - editorReadStartedMs;
      if (content.trim().isEmpty && _editorContentFallback.trim().isNotEmpty) {
        debugPrint(
          '[template_save] Editor returned empty content, using fallback html (${_editorContentFallback.length} chars)',
        );
        content = _editorContentFallback;
      }
      final effectiveDate = _effectiveDate?.toIso8601String().substring(0, 10);
      final endDate = _endDate?.toIso8601String().substring(0, 10);
      final data = <String, dynamic>{
        'title': _titleCtrl.text.trim(),
        'description': _descCtrl.text.trim(),
        'content': content,
        'source_type': _mode == _CreateMode.manual ? 'manual' : 'docx',
        'visibility': _visibility,
        if (_visibility == 'group' && _selectedGroupId != null)
          'group': _selectedGroupId,
        if (_visibility == 'group')
          'audience_user_ids': _selectedAudienceUserIds.toList(),
        'notes': _notesCtrl.text.trim(),
        'tags': _tags,
        if (effectiveDate != null) 'effective_date': effectiveDate,
        if (endDate != null) 'end_date': endDate,
        if (widget.id != null && _changeNoteCtrl.text.trim().isNotEmpty)
          'change_note': _changeNoteCtrl.text.trim(),
      };

      if (widget.id == null) {
        if (_isDocxMode && !_hasLocalDocxBytes) {
          throw Exception(
              'Mau DOCX moi phai giu kem file DOCX goc truoc khi luu.');
        }
        final payload = _isDocxMode
            ? _buildDocxFormData(
                title: _titleCtrl.text.trim(),
                description: _descCtrl.text.trim(),
                content: content,
                visibility: _visibility,
                groupId: _selectedGroupId,
                audienceUserIds: _selectedAudienceUserIds.toList(),
                notes: _notesCtrl.text.trim(),
                tags: _tags,
                effectiveDate: effectiveDate,
                endDate: endDate,
                docxBytes: _docxFileBytes!,
              )
            : data;
        debugPrint(
          '[template_save] request_prepare | template_id=${widget.id} | create=true | editor_read_elapsed_ms=$editorReadElapsedMs | content_chars=${content.length} | source_type=${data['source_type']} | has_docx_file=${_isDocxMode} | docx_bytes=${_docxFileBytes?.length ?? 0}',
        );
        final requestStartedMs = totalStopwatch.elapsedMilliseconds;
        // Gọi API hoặc tác vụ bất đồng bộ rồi chờ kết quả trước khi cập nhật giao diện.

        final resp = await ApiClient().dio.post('templates/', data: payload);
        final requestElapsedMs =
            totalStopwatch.elapsedMilliseconds - requestStartedMs;
        final newId = resp.data['id'];
        debugPrint(
          '[template_save] done | template_id=$newId | create=true | request_elapsed_ms=$requestElapsedMs | total_elapsed_ms=${totalStopwatch.elapsedMilliseconds} | response_status=${resp.statusCode}',
        );
        _templateIdForTagGen = newId;
        _refreshTemplateCollections(newId);
        // Điều hướng người dùng sang màn phù hợp theo kết quả thao tác hiện tại.

        if (mounted) context.go('/templates/$newId');
      } else {
        debugPrint(
          '[template_save] request_prepare | template_id=${widget.id} | create=false | editor_read_elapsed_ms=$editorReadElapsedMs | content_chars=${content.length} | source_type=${data['source_type']} | has_docx_file=false | docx_bytes=0',
        );
        final requestStartedMs = totalStopwatch.elapsedMilliseconds;
        // Gọi API hoặc tác vụ bất đồng bộ rồi chờ kết quả trước khi cập nhật giao diện.

        final resp =
            await ApiClient().dio.patch('templates/${widget.id}/', data: data);
        final requestElapsedMs =
            totalStopwatch.elapsedMilliseconds - requestStartedMs;
        final savedId = resp.data['id'] ?? widget.id;
        debugPrint(
          '[template_save] done | template_id=$savedId | create=false | request_elapsed_ms=$requestElapsedMs | total_elapsed_ms=${totalStopwatch.elapsedMilliseconds} | response_status=${resp.statusCode}',
        );
        _refreshTemplateCollections(widget.id!);
        // Điều hướng người dùng sang màn phù hợp theo kết quả thao tác hiện tại.

        if (mounted) context.go('/templates/$savedId');
      }
    } on DioException catch (e) {
      final serverData = e.response?.data;
      debugPrint(
        '[template_save] failed | template_id=${widget.id} | total_elapsed_ms=${totalStopwatch.elapsedMilliseconds} | status=${e.response?.statusCode} | data=$serverData',
      );
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(
              '${_pick('Lỗi lưu mẫu', 'Template save error')}: ${serverData ?? e.message ?? e}',
            ),
            backgroundColor: Colors.red,
          ),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('${_pick('Lỗi lưu mẫu', 'Template save error')}: $e'),
            backgroundColor: Colors.red,
          ),
        );
      }
    } finally {
      // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

      if (mounted) setState(() => _loading = false);
    }
  }

  // Mục đích: Phương thức `_saveAsCopy` triển khai phần việc `save As Copy` trong flutter_frontend/lib/screens/templates/template_form_screen.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  Future<void> _saveAsCopy() async {
    if (!_validateDateRange()) return;
    final titleCtrl =
        TextEditingController(text: '${_titleCtrl.text.trim()} (bản sao)');
    // Phase 3 sharing roadmap: ban sao luon tao o che do private, sau khi tao
    // user co the chia se qua UnifiedShareSheet o trang chi tiet ban sao.
    const String copyVisibility = 'private';
    const int? copyGroupId = null;

    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text(_pick('Lưu thành bản sao', 'Save as copy')),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            TextField(
              controller: titleCtrl,
              decoration: InputDecoration(
                  labelText: _pick('Tên mẫu mới *', 'New template name *')),
            ),
            const SizedBox(height: 12),
            Container(
              padding: const EdgeInsets.all(10),
              decoration: BoxDecoration(
                color: Colors.amber.shade50,
                borderRadius: BorderRadius.circular(8),
                border: Border.all(color: Colors.amber.shade200),
              ),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Icon(Icons.info_outline,
                      size: 16, color: Colors.amber.shade800),
                  const SizedBox(width: 6),
                  Expanded(
                    child: Text(
                      _pick(
                        'Bản sao se duoc luu o che do Riêng tu. Sau khi tao, ban co the chia se qua trang chi tiet.',
                        'The copy will be saved as Private. After creating, share it from the detail page.',
                      ),
                      style:
                          TextStyle(fontSize: 12, color: Colors.amber.shade900),
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
        actions: [
          TextButton(
              onPressed: () => Navigator.pop(ctx, false),
              child: Text(_pick('Hủy', 'Cancel'))),
          FilledButton(
              onPressed: () => Navigator.pop(ctx, true),
              child: Text(_pick('Tạo bản sao', 'Create copy'))),
        ],
      ),
    );

    if (ok != true) {
      titleCtrl.dispose();
      return;
    }

    // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

    setState(() => _loading = true);
    try {
      var content =
          _isDocxMode ? _editorContentFallback : await _getContentHtml();
      if (content.trim().isEmpty && _editorContentFallback.trim().isNotEmpty) {
        content = _editorContentFallback;
      }
      final effectiveDate = _effectiveDate?.toIso8601String().substring(0, 10);
      final endDate = _endDate?.toIso8601String().substring(0, 10);
      // Phase 3 sharing: ban sao mac dinh private, khong gui audience cu.
      const copyAudienceUserIds = <int>[];
      final data = {
        'title': titleCtrl.text.trim(),
        'description': _descCtrl.text.trim(),
        'content': content,
        'source_type': _mode == _CreateMode.manual ? 'manual' : 'docx',
        'visibility': copyVisibility,
        'notes': _notesCtrl.text.trim(),
        'tags': _tags,
        if (effectiveDate != null) 'effective_date': effectiveDate,
        if (endDate != null) 'end_date': endDate,
      };
      final resp = await (() async {
        if (!_isDocxMode) {
          return ApiClient().dio.post('templates/', data: data);
        }
        final resolvedDocxBytes = await _resolveStoredDocxBytes();
        if (resolvedDocxBytes == null || resolvedDocxBytes.isEmpty) {
          throw Exception(
            _pick(
              'Mẫu DOCX này không còn file DOCX gốc. Hãy upload lại file gốc trước khi lưu thành bản sao.',
              'This DOCX template no longer has its original DOCX file. Upload the original file again before saving a copy.',
            ),
          );
        }
        final formData = _buildDocxFormData(
          title: titleCtrl.text.trim(),
          description: _descCtrl.text.trim(),
          content: content,
          visibility: copyVisibility,
          groupId: copyGroupId,
          audienceUserIds: copyAudienceUserIds,
          notes: _notesCtrl.text.trim(),
          tags: _tags,
          effectiveDate: effectiveDate,
          endDate: endDate,
          docxBytes: resolvedDocxBytes,
        );
        return ApiClient().dio.post('templates/', data: formData);
      })();
      final newId = resp.data['id'];
      titleCtrl.dispose();
      _refreshTemplateCollections(newId);
      // Điều hướng người dùng sang màn phù hợp theo kết quả thao tác hiện tại.

      if (mounted) context.go('/templates/$newId');
    } catch (e) {
      titleCtrl.dispose();
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content:
                Text('${_pick('Lỗi tạo bản sao', 'Copy creation error')}: $e'),
            backgroundColor: Colors.red,
          ),
        );
      }
    } finally {
      // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

      if (mounted) setState(() => _loading = false);
    }
  }

  // Mục đích: Phương thức `_delete` triển khai phần việc `delete` trong flutter_frontend/lib/screens/templates/template_form_screen.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  Future<void> _delete() async {
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text(_pick('Xác nhận xóa', 'Confirm deletion')),
        content: Text(_pick('Bạn có chắc muốn xóa mẫu văn bản này?',
            'Are you sure you want to delete this template?')),
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
      final outcome = await deleteTemplateWithUsageGuard(context, widget.id!);
      if (outcome == TemplateDeleteOutcome.deleted && mounted) {
        context.go('/templates');
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('${_pick('Lỗi xóa', 'Delete error')}: $e'),
            backgroundColor: Colors.red,
          ),
        );
      }
    }
  }

  // ── BUILD ─────────────────────────────────────────────────────────────────

  @override
  // Mục đích: Phương thức `build` triển khai phần việc `build` trong flutter_frontend/lib/screens/templates/template_form_screen.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  Widget build(BuildContext context) {
    if (widget.id != null) {
      // Lắng nghe provider để widget tự động dựng lại khi dữ liệu hoặc trạng thái thay đổi.

      final asyncTmpl = ref.watch(templateDetailProvider(widget.id!));
      return asyncTmpl.when(
        // Dựng khung màn hình chính để chứa app bar, body, action và các vùng giao diện khác.

        loading: () =>
            const Scaffold(body: Center(child: CircularProgressIndicator())),
        // Dựng khung màn hình chính để chứa app bar, body, action và các vùng giao diện khác.

        error: (e, _) => Scaffold(
          body: Center(child: Text('${_pick('Lỗi', 'Error')}: $e')),
        ),
        data: (tmpl) {
          _prefillFromTemplate(tmpl);
          return _buildScaffold(context, tmpl: tmpl);
        },
      );
    }
    return _buildScaffold(context);
  }

  // Mục đích: Phương thức `_buildScaffold` triển khai phần việc `build Scaffold` trong flutter_frontend/lib/screens/templates/template_form_screen.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  Widget _buildScaffold(BuildContext context, {dynamic tmpl}) {
    final isEdit = widget.id != null;
    final title = isEdit
        ? _pick(
            'Chỉnh sửa: ${_editTitle.isNotEmpty ? _editTitle : ''}',
            'Edit: ${_editTitle.isNotEmpty ? _editTitle : ''}',
          )
        : _pick('Tạo mẫu văn bản', 'Create template');
    final isWide = MediaQuery.of(context).size.width >= 900 && !kIsWeb;

    // Dựng khung màn hình chính để chứa app bar, body, action và các vùng giao diện khác.

    return Scaffold(
      appBar: AppBar(
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          // Điều hướng người dùng sang màn phù hợp theo kết quả thao tác hiện tại.

          onPressed: () => context.pop(),
        ),
        title: Text(title, overflow: TextOverflow.ellipsis),
        actions: [
          Padding(
            padding: const EdgeInsets.only(right: 8),
            child: FilledButton(
              onPressed: _loading ? null : _save,
              child: _loading
                  ? const SizedBox(
                      height: 18,
                      width: 18,
                      child: CircularProgressIndicator(
                          strokeWidth: 2, color: Colors.white))
                  : Text(isEdit
                      ? _pick('Lưu', 'Save')
                      : _pick('Tạo mẫu', 'Create template')),
            ),
          ),
        ],
      ),
      body: Form(
        key: _formKey,
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(24),
          child: isWide
              ? _buildWideLayout(context, isEdit, tmpl: tmpl)
              : _buildNarrowLayout(context, isEdit, tmpl: tmpl),
        ),
      ),
    );
  }

  // Mục đích: Phương thức `_buildWideLayout` triển khai phần việc `build Wide Layout` trong flutter_frontend/lib/screens/templates/template_form_screen.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  Widget _buildWideLayout(BuildContext context, bool isEdit, {dynamic tmpl}) {
    final settingsCard =
        SizedBox(width: 280, child: _buildSettingsCard(context, isEdit));
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Expanded(child: _buildMainFields(context, isEdit, tmpl: tmpl)),
        const SizedBox(width: 24),
        settingsCard,
      ],
    );
  }

  // Mục đích: Phương thức `_buildNarrowLayout` triển khai phần việc `build Narrow Layout` trong flutter_frontend/lib/screens/templates/template_form_screen.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  Widget _buildNarrowLayout(BuildContext context, bool isEdit, {dynamic tmpl}) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _buildSettingsCard(context, isEdit),
        const SizedBox(height: 24),
        _buildMainFields(context, isEdit, tmpl: tmpl),
      ],
    );
  }

  // ── CREATE MODE SELECTOR ──────────────────────────────────────────────────

  // Mục đích: Phương thức `_buildModeSelector` triển khai phần việc `build Mode Selector` trong flutter_frontend/lib/screens/templates/template_form_screen.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  Widget _buildModeSelector() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          _pick('Cách tạo mẫu', 'Template creation mode'),
          style: TextStyle(
              fontSize: 13,
              fontWeight: FontWeight.w600,
              color: Colors.grey.shade700),
        ),
        const SizedBox(height: 10),
        SegmentedButton<_CreateMode>(
          segments: [
            ButtonSegment(
              value: _CreateMode.manual,
              icon: const Icon(Icons.edit_outlined, size: 16),
              label: Text(_pick('Tạo thủ công', 'Manual')),
            ),
            ButtonSegment(
              value: _CreateMode.uploadDocx,
              icon: const Icon(Icons.upload_file_outlined, size: 16),
              label: Text(_pick('Upload DOCX', 'Upload DOCX')),
            ),
            ButtonSegment(
              value: _CreateMode.uploadDocxDetect,
              icon: const Icon(Icons.auto_fix_high_outlined, size: 16),
              label: Text(
                  _pick('Upload + AI nhận biến', 'Upload + AI detect vars')),
            ),
          ],
          selected: {_mode},
          onSelectionChanged: (sel) {
            // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

            setState(() {
              _mode = sel.first;
              _clearDocxSelection(clearStatus: true);
            });
            _setEditorReadOnly(sel.first != _CreateMode.manual);
          },
          style: ButtonStyle(
            textStyle: WidgetStateProperty.all(const TextStyle(fontSize: 12.5)),
          ),
        ),
        const SizedBox(height: 4),
        Text(
          switch (_mode) {
            _CreateMode.manual => _pick(
                'Nhập nội dung mẫu trực tiếp vào trình soạn thảo bên dưới.',
                'Type the template content directly in the editor below.',
              ),
            _CreateMode.uploadDocx => _pick(
                'Upload file DOCX có sẵn, nội dung sẽ được điền vào trình soạn thảo.',
                'Upload an existing DOCX file and its content will be loaded into the editor.',
              ),
            _CreateMode.uploadDocxDetect => _pick(
                'Upload DOCX + AI tự động nhận diện các trường cần điền và chuyển thành {{biến}}.',
                'Upload DOCX + let AI detect fillable fields and convert them to {{variables}}.',
              ),
          },
          style: TextStyle(fontSize: 11.5, color: Colors.grey.shade500),
        ),
        const SizedBox(height: 16),
        if (_mode != _CreateMode.manual) _buildDocxImportArea(),
        if (_mode != _CreateMode.manual) const SizedBox(height: 16),
        const Divider(),
        const SizedBox(height: 8),
      ],
    );
  }

  // Mục đích: Phương thức `_buildDocxImportArea` triển khai phần việc `build Docx Import Area` trong flutter_frontend/lib/screens/templates/template_form_screen.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  // Ô nhập prompt tùy chỉnh giúp AI nhận diện biến tốt hơn (phải nhập TRƯỚC khi chọn file).
  Widget _buildDetectionPromptSection() {
    final hasSavedPrompt = _detectionPromptId != null;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          _pick('Prompt nhận diện biến (tùy chọn)',
              'Variable-detection prompt (optional)'),
          style: TextStyle(
              fontSize: 12.5,
              fontWeight: FontWeight.w600,
              color: Colors.grey.shade700),
        ),
        const SizedBox(height: 4),
        Text(
          _pick(
            'Gợi ý cho AI cách tách/gộp biến. Ví dụ: "Gộp giá trị sau dấu hai chấm thành 1 biến; hạn chế số biến; tập trung biến ở giữa văn bản". Nhập trước khi chọn file.',
            'Hints for the AI on splitting/merging variables. Enter before choosing the file.',
          ),
          style: TextStyle(fontSize: 11, color: Colors.grey.shade600),
        ),
        const SizedBox(height: 6),
        if (hasSavedPrompt)
          Padding(
            padding: const EdgeInsets.only(bottom: 6),
            child: Chip(
              avatar: const Icon(Icons.bookmark, size: 16),
              label: Text(_detectionPromptTitle.isEmpty
                  ? '#$_detectionPromptId'
                  : _detectionPromptTitle),
              onDeleted: _importing
                  ? null
                  : () => setState(() {
                        _detectionPromptId = null;
                        _detectionPromptTitle = '';
                      }),
            ),
          ),
        TextField(
          controller: _detectionHintCtrl,
          enabled: !_importing,
          minLines: 2,
          maxLines: 5,
          maxLength: 2000,
          decoration: InputDecoration(
            hintText: _pick(
                'Nhập gợi ý nhận diện biến...', 'Type a detection hint...'),
            border: const OutlineInputBorder(),
            isDense: true,
          ),
          onChanged: (_) {
            if (_detectionPromptId != null) {
              setState(() {
                _detectionPromptId = null;
                _detectionPromptTitle = '';
              });
            }
          },
        ),
        const SizedBox(height: 6),
        Wrap(
          spacing: 8,
          children: [
            OutlinedButton.icon(
              onPressed: _importing ? null : _pickDetectionPrompt,
              icon: const Icon(Icons.folder_open, size: 15),
              label: Text(_pick('Chọn prompt đã lưu', 'Pick saved prompt')),
            ),
            OutlinedButton.icon(
              onPressed: _importing ? null : _saveDetectionPrompt,
              icon: const Icon(Icons.save_outlined, size: 15),
              label: Text(_pick('Lưu prompt', 'Save prompt')),
            ),
          ],
        ),
      ],
    );
  }

  Future<void> _pickDetectionPrompt() async {
    final prompt = await PromptPickerDialog.show(
      context,
      scope: 'template_var_detect',
    );
    if (prompt == null || !mounted) return;
    setState(() {
      _detectionPromptId = prompt.id.toString();
      _detectionPromptTitle = prompt.title;
      final loaded = (prompt.rulesContent ?? '').trim().isNotEmpty
          ? prompt.rulesContent!.trim()
          : (prompt.systemContent ?? '').trim();
      _detectionHintCtrl.text = loaded;
    });
  }

  Future<void> _saveDetectionPrompt() async {
    final hint = _detectionHintCtrl.text.trim();
    if (hint.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(_pick('Nhập nội dung prompt trước khi lưu.',
              'Enter prompt content before saving.')),
        ),
      );
      return;
    }
    final prompt = await SavePromptDialog.show(
      context,
      initialTitle: _detectionPromptTitle.isNotEmpty
          ? _detectionPromptTitle
          : _pick('Prompt nhận diện biến', 'Variable-detection prompt'),
      systemContent: '',
      rulesContent: hint,
      defaultScopes: const ['template_var_detect'],
    );
    if (prompt == null || !mounted) return;
    ref.invalidate(promptsProvider);
    setState(() {
      _detectionPromptId = prompt.id.toString();
      _detectionPromptTitle = prompt.title;
    });
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
          content: Text(_pick('Đã lưu prompt "${prompt.title}".',
              'Saved prompt "${prompt.title}".'))),
    );
  }

  Widget _buildDocxImportArea() {
    final isDetect = _mode == _CreateMode.uploadDocxDetect;
    final MaterialColor accentColor = isDetect ? Colors.purple : Colors.blue;

    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: accentColor.withOpacity(0.05),
        border: Border.all(
          color: _docxFileName != null
              ? accentColor.withOpacity(0.6)
              : accentColor.withOpacity(0.25),
          width: 1.5,
        ),
        borderRadius: BorderRadius.circular(10),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(children: [
            Icon(isDetect ? Icons.auto_fix_high : Icons.upload_file,
                color: accentColor, size: 20),
            const SizedBox(width: 8),
            Text(
              isDetect
                  ? _pick('Upload DOCX + AI nhận biến',
                      'Upload DOCX + AI detect vars')
                  : _pick('Upload file DOCX', 'Upload DOCX file'),
              style: TextStyle(
                  fontWeight: FontWeight.w600,
                  color: accentColor.shade700,
                  fontSize: 13.5),
            ),
          ]),
          if (isDetect) ...[
            const SizedBox(height: 10),
            _buildDetectionPromptSection(),
          ],
          const SizedBox(height: 10),
          if (_importing)
            Row(children: [
              SizedBox(
                  width: 16,
                  height: 16,
                  child: CircularProgressIndicator(
                      strokeWidth: 2, color: accentColor)),
              const SizedBox(width: 10),
              Expanded(
                child: Text(
                  _importStatus ?? _pick('Đang xử lý...', 'Processing...'),
                  style: TextStyle(fontSize: 13, color: accentColor),
                ),
              ),
            ])
          else
            OutlinedButton.icon(
              onPressed: _pickAndImportDocx,
              icon: Icon(Icons.folder_open_outlined, color: accentColor),
              label: Text(
                  _docxFileName ??
                      _pick('Chọn file .docx', 'Choose .docx file'),
                  style: TextStyle(color: accentColor)),
              style: OutlinedButton.styleFrom(
                  side: BorderSide(color: accentColor.withOpacity(0.5))),
            ),
          if (!_importing && _importStatus != null) ...[
            const SizedBox(height: 10),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
              decoration: BoxDecoration(
                color: _importStatus!.startsWith('Lỗi')
                    ? Colors.red.shade50
                    : Colors.green.shade50,
                borderRadius: BorderRadius.circular(6),
              ),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Icon(
                    _importStatus!.startsWith('Lỗi')
                        ? Icons.error_outline
                        : Icons.check_circle_outline,
                    size: 16,
                    color: _importStatus!.startsWith('Lỗi')
                        ? Colors.red.shade700
                        : Colors.green.shade700,
                  ),
                  const SizedBox(width: 6),
                  Expanded(
                      child: Text(_importStatus!,
                          style: TextStyle(
                            fontSize: 12.5,
                            color: _importStatus!.startsWith('Lỗi')
                                ? Colors.red.shade700
                                : Colors.green.shade700,
                          ))),
                ],
              ),
            ),
          ],
        ],
      ),
    );
  }

  // ── MAIN FIELDS ───────────────────────────────────────────────────────────

  // Mục đích: Phương thức `_buildSourceImportArea` triển khai phần việc `build Source Import Area` trong flutter_frontend/lib/screens/templates/template_form_screen.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  Widget _buildSourceImportArea() {
    final hasSourceUrl = (widget.sourceUrl ?? '').trim().isNotEmpty;
    final hasResolvedUrl = (_sourceImportResolvedUrl ?? '').trim().isNotEmpty;
    final hasResolvedTitle =
        (_sourceImportResolvedTitle ?? '').trim().isNotEmpty;
    final hasSourceTitle = (widget.sourceTitle ?? '').trim().isNotEmpty;
    final hasSource = hasSourceUrl || hasResolvedUrl;
    if (!hasSource) return const SizedBox.shrink();

    final displayTitle = hasResolvedTitle
        ? _sourceImportResolvedTitle!.trim()
        : (hasSourceTitle ? widget.sourceTitle!.trim() : 'Nguon Internet');
    final displayUrl = hasResolvedUrl
        ? _sourceImportResolvedUrl!.trim()
        : (widget.sourceUrl ?? '').trim();

    return Container(
      margin: const EdgeInsets.only(bottom: 16),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: const Color(0xFFF4F8FF),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: const Color(0xFFB6CCF8)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(
                Icons.public_outlined,
                size: 18,
                color: Color(0xFF1D4E89),
              ),
              const SizedBox(width: 8),
              Text(
                _pick(
                  'Nguồn Internet đưa vào tạo mẫu',
                  'Internet source used to create the template',
                ),
                style: TextStyle(
                  fontSize: 13.5,
                  fontWeight: FontWeight.w700,
                  color: Color(0xFF1D4E89),
                ),
              ),
            ],
          ),
          const SizedBox(height: 10),
          Text(
            displayTitle,
            style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w600),
          ),
          const SizedBox(height: 4),
          SelectableText(
            displayUrl,
            style: TextStyle(fontSize: 12, color: Colors.blueGrey.shade600),
          ),
          if (_sourceImportKind?.isNotEmpty == true) ...[
            const SizedBox(height: 8),
            Text(
              '${_pick('Loại nguồn', 'Source type')}: ${_sourceImportKind!}',
              style: TextStyle(fontSize: 11.5, color: Colors.blueGrey.shade700),
            ),
          ],
          const SizedBox(height: 10),
          if (_sourceImporting)
            Row(
              children: [
                const SizedBox(
                  width: 16,
                  height: 16,
                  child: CircularProgressIndicator(strokeWidth: 2),
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: Text(
                    _pick(
                      'Đang tải nguồn và AI đang nhận diện biến...',
                      'Loading the source and letting AI detect variables...',
                    ),
                    style: TextStyle(fontSize: 12.5),
                  ),
                ),
              ],
            )
          else if (_sourceImportStatus != null)
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Icon(
                  _looksLikeError(_sourceImportStatus)
                      ? Icons.error_outline
                      : Icons.check_circle_outline,
                  size: 16,
                  color: _looksLikeError(_sourceImportStatus)
                      ? Colors.red.shade700
                      : Colors.green.shade700,
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    _sourceImportStatus!,
                    style: TextStyle(
                      fontSize: 12.5,
                      color: _looksLikeError(_sourceImportStatus)
                          ? Colors.red.shade700
                          : Colors.green.shade700,
                    ),
                  ),
                ),
              ],
            ),
        ],
      ),
    );
  }

  // Mục đích: Phương thức `_buildMainFields` triển khai phần việc `build Main Fields` trong flutter_frontend/lib/screens/templates/template_form_screen.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  Widget _buildMainFields(BuildContext context, bool isEdit, {dynamic tmpl}) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        if (!isEdit) _buildModeSelector(),
        if (!isEdit) _buildSourceImportArea(),
        if (isEdit && _isDocxMode && !_templateHasDocxSource) ...[
          Container(
            width: double.infinity,
            margin: const EdgeInsets.only(bottom: 16),
            padding: const EdgeInsets.all(14),
            decoration: BoxDecoration(
              color: const Color(0xFFFFFBEB),
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: const Color(0xFFFDE68A)),
            ),
            child: Text(
              _pick(
                'Mẫu DOCX này đã mất file DOCX gốc. Hệ thống vẫn giữ nội dung text/HTML, nhưng muốn tải xuống đúng định dạng Word thì cần upload lại file gốc.',
                'This DOCX template has lost its original DOCX file. The system still keeps the text/HTML content, but you need to upload the original file again to download the correct Word format.',
              ),
              style: TextStyle(color: Color(0xFF92400E), height: 1.45),
            ),
          ),
        ],

        TextFormField(
          controller: _titleCtrl,
          decoration: InputDecoration(
            labelText: _pick('Tiêu đề mẫu *', 'Template title *'),
            border: const OutlineInputBorder(),
          ),
          validator: (v) => (v == null || v.trim().isEmpty)
              ? _pick('Vui lòng nhập tiêu đề', 'Please enter a title')
              : null,
        ),
        const SizedBox(height: 16),

        TextFormField(
          controller: _descCtrl,
          decoration: InputDecoration(
            labelText: _pick('Mô tả', 'Description'),
            border: const OutlineInputBorder(),
          ),
          maxLines: 2,
        ),
        const SizedBox(height: 16),

        // Content editor label
        Row(children: [
          const Icon(Icons.article_outlined, size: 16, color: Colors.blueGrey),
          const SizedBox(width: 6),
          Text(
            _pick('Nội dung mẫu', 'Template content'),
            style: Theme.of(context)
                .textTheme
                .titleSmall
                ?.copyWith(fontWeight: FontWeight.w600),
          ),
          const SizedBox(width: 8),
          Text(
            _pick('(dùng {{tên_biến}} làm placeholder)',
                '(use {{variable_name}} as placeholders)'),
            style: TextStyle(fontSize: 12, color: Colors.grey.shade500),
          ),
        ]),
        const SizedBox(height: 8),

        if (isEdit && tmpl != null) ...[
          _buildTemplatePdfPreviewCard(context, tmpl),
          const SizedBox(height: 12),
        ] else if (!isEdit) ...[
          Container(
            width: double.infinity,
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: const Color(0xFFF8FAFC),
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: const Color(0xFFE2E8F0)),
            ),
            child: Text(
              _pick(
                'Sau khi lưu nháp, hệ thống sẽ tạo bản xem PDF cho mẫu văn bản để bạn kiểm tra bố cục thực tế.',
                'After saving a draft, the system will generate a PDF preview so you can review the real layout.',
              ),
              style: TextStyle(color: Color(0xFF334155), height: 1.45),
            ),
          ),
          const SizedBox(height: 12),
        ],

        if (!isEdit || !_editorReadOnly) ...[
          if (isEdit) ...[
            Text(
              _pick('Nguồn chỉnh sửa trên form', 'In-form editing source'),
              style: Theme.of(context).textTheme.labelLarge?.copyWith(
                    fontWeight: FontWeight.w600,
                    color: const Color(0xFF475569),
                  ),
            ),
            const SizedBox(height: 8),
          ],
          _buildContentEditor(),
        ],
        _buildManualEditLaunchCard(context, isEdit),
        const SizedBox(height: 12),

        _buildVarsPanel(),
        const SizedBox(height: 16),

        TextFormField(
          controller: _notesCtrl,
          decoration: InputDecoration(
            labelText: _pick('Ghi chú', 'Notes'),
            border: const OutlineInputBorder(),
          ),
        ),
        const SizedBox(height: 16),

        if (isEdit)
          TextFormField(
            controller: _changeNoteCtrl,
            decoration: InputDecoration(
              labelText: _pick(
                  'Ghi chú thay đổi (phiên bản)', 'Change note (version)'),
              hintText: _pick('Ghi rõ bạn đã thay đổi gì...',
                  'Describe what you changed...'),
              border: const OutlineInputBorder(),
            ),
          ),

        const SizedBox(height: 24),

        Wrap(
          spacing: 12,
          runSpacing: 12,
          children: [
            FilledButton(
              onPressed: _loading ? null : _save,
              child: _loading
                  ? const SizedBox(
                      height: 18,
                      width: 18,
                      child: CircularProgressIndicator(
                          strokeWidth: 2, color: Colors.white))
                  : Text(
                      isEdit
                          ? _pick('Lưu mẫu', 'Save template')
                          : _pick('Tạo mẫu', 'Create template'),
                    ),
            ),
            if (isEdit) ...[
              OutlinedButton.icon(
                onPressed: _manualEditIsBusy ? null : _openTemplateManualEditor,
                icon: _manualEditLaunching
                    ? const SizedBox(
                        height: 16,
                        width: 16,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      )
                    : const Icon(Icons.edit_document, size: 16),
                label: Text(
                  _manualEditLaunching
                      ? _pick('Đang mở trình chỉnh sửa...', 'Opening editor...')
                      : _pick('Chỉnh sửa thủ công', 'Manual edit'),
                ),
              ),
              OutlinedButton(
                onPressed: _loading ? null : _saveAsCopy,
                child: Text(_pick('Lưu thành bản sao', 'Save as copy')),
              ),
              TextButton(
                onPressed: _loading ? null : _delete,
                style: TextButton.styleFrom(foregroundColor: Colors.red),
                child: Text(_pick('Xóa mẫu', 'Delete template')),
              ),
            ],
          ],
        ),
      ],
    );
  }

  // ── CONTENT EDITOR (rich text via iframe) ────────────────────────────────

  // Mục đích: Phương thức `_buildContentEditor` triển khai phần việc `build Content Editor` trong flutter_frontend/lib/screens/templates/template_form_screen.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  Widget _buildContentEditor() {
    final editorFrame = ClipRRect(
      borderRadius: BorderRadius.circular(8),
      child: Container(
        height: 520,
        decoration: BoxDecoration(
          border: Border.all(
            color: _editorReadOnly
                ? const Color(0xFF94A3B8)
                : Colors.grey.shade300,
          ),
          borderRadius: BorderRadius.circular(8),
          boxShadow: [
            BoxShadow(
              color: Colors.black.withOpacity(0.07),
              blurRadius: 6,
              offset: const Offset(0, 2),
            ),
          ],
        ),
        child: HtmlElementView(viewType: _editorViewKey),
      ),
    );

    if (!_editorReadOnly) {
      return editorFrame;
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Container(
          width: double.infinity,
          margin: const EdgeInsets.only(bottom: 8),
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(
            color: const Color(0xFFF8FAFC),
            borderRadius: BorderRadius.circular(10),
            border: Border.all(color: const Color(0xFFCBD5E1)),
          ),
          child: Text(
            _pick(
              'Template DOCX đang ở chế độ xem trước. Bạn có thể mở trình chỉnh sửa thủ công để sửa trực tiếp nội dung DOCX, hoặc thay thế bằng file DOCX mới.',
              'This DOCX template is in preview mode. You can open the manual editor to edit the DOCX content directly, or replace it with a new DOCX file.',
            ),
            style: TextStyle(color: Color(0xFF334155), height: 1.45),
          ),
        ),
        editorFrame,
      ],
    );
  }

  // ── VARIABLES PANEL ───────────────────────────────────────────────────────

  // Mục đích: Phương thức `_buildVarsPanel` triển khai phần việc `build Vars Panel` trong flutter_frontend/lib/screens/templates/template_form_screen.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  Widget _buildVarsPanel() {
    return AnimatedContainer(
      duration: const Duration(milliseconds: 200),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: Colors.blue.shade50,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: Colors.blue.shade100),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(children: [
            Icon(Icons.auto_fix_high_outlined,
                size: 14, color: Colors.blue.shade700),
            const SizedBox(width: 6),
            Text(
              _pick(
                'Biến tự động phát hiện: ${_detectedVars.length} biến',
                'Auto-detected variables: ${_detectedVars.length}',
              ),
              style: TextStyle(
                  fontSize: 12.5,
                  color: Colors.blue.shade700,
                  fontWeight: FontWeight.w600),
            ),
          ]),
          if (_detectedVars.isNotEmpty) ...[
            const SizedBox(height: 8),
            Wrap(
              spacing: 6,
              runSpacing: 6,
              children: _detectedVars
                  .map((v) => Container(
                        padding: const EdgeInsets.symmetric(
                            horizontal: 8, vertical: 3),
                        decoration: BoxDecoration(
                          color: Colors.blue.shade100,
                          borderRadius: BorderRadius.circular(4),
                        ),
                        child: Text('{{$v}}',
                            style: TextStyle(
                                fontSize: 12,
                                color: Colors.blue.shade800,
                                fontFamily: 'monospace')),
                      ))
                  .toList(),
            ),
          ] else
            Padding(
              padding: const EdgeInsets.only(top: 4),
              child: Text(
                _pick(
                  'Nhấn "Chèn {{biến}}" để thêm placeholder tự động vào nội dung',
                  'Press "Insert variable" to add placeholders to the content',
                ),
                style: TextStyle(fontSize: 12, color: Colors.blue.shade400),
              ),
            ),
        ],
      ),
    );
  }

  // ── SETTINGS CARD ─────────────────────────────────────────────────────────

  // Mục đích: Phương thức `_buildSettingsCard` triển khai phần việc `build Settings Card` trong flutter_frontend/lib/screens/templates/template_form_screen.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  // ── KHOI CHIA SE THONG NHAT (Phase 3 sharing roadmap) ──
  // Phai duoc UnifiedShareSheet (cho edit mode) hoac info card (cho create mode).
  // Tach rieng ra de nhung helper khac trong file nay co the goi lai khi can.
  Widget _buildUnifiedSharingBlock(BuildContext context, bool isEdit) {
    if (isEdit && widget.id != null) {
      return Container(
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(8),
          border: Border.all(color: Colors.blueGrey.shade100),
        ),
        padding: const EdgeInsets.all(4),
        child: UnifiedShareSheet(
          entityType: 'templates',
          entityId: widget.id!,
          entityTitle: _titleCtrl.text.trim().isNotEmpty
              ? _titleCtrl.text.trim()
              : 'Mau van ban #${widget.id}',
          presentation: SharePresentation.inlinePanel,
        ),
      );
    }
    // Create mode - chua co id => thong bao chia se se mo sau khi luu
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: Colors.amber.shade50,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: Colors.amber.shade200),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(Icons.info_outline, size: 18, color: Colors.amber.shade800),
          const SizedBox(width: 8),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  _pick('Chia se', 'Sharing'),
                  style: TextStyle(
                    fontWeight: FontWeight.bold,
                    color: Colors.amber.shade900,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  _pick(
                    'Mau moi se duoc luu o che do Rieng tu. Sau khi luu, mo trang chi tiet de chia se voi nhom, dong nghiep cu the hoac toan bo cong ty (trong moi pham vi, ban co the cap quyen Xem, Sua, hoac Toan quyen).',
                    'New template will be saved as Private. After saving, open the detail page to share with a group, specific colleagues, or everyone (each scope supports View / Edit / Delete permissions).',
                  ),
                  style: TextStyle(fontSize: 12, color: Colors.amber.shade800),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildSettingsCard(BuildContext context, bool isEdit) {
    // Phase 3 sharing: visibility/group/audience da chuyen sang UnifiedShareSheet,
    // khong con can read groups o day.
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(_pick('Cài đặt mẫu', 'Template settings'),
                style: Theme.of(context)
                    .textTheme
                    .titleSmall
                    ?.copyWith(fontWeight: FontWeight.bold)),
            // ── KHOI CHIA SE THONG NHAT (Phase 3 cua sharing roadmap) ──
            const SizedBox(height: 12),
            _buildUnifiedSharingBlock(context, isEdit),
            const SizedBox(height: 16),

            // ── Replace DOCX (edit mode only) ──────────────────────────
            if (isEdit) ...[
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: Colors.purple.shade50,
                  border: Border.all(color: Colors.purple.shade100),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(children: [
                      Icon(Icons.upload_file_outlined,
                          size: 15, color: Colors.purple.shade700),
                      const SizedBox(width: 6),
                      Text(
                        _pick('Thay thế bằng DOCX mới',
                            'Replace with a new DOCX'),
                        style: TextStyle(
                            fontSize: 12,
                            fontWeight: FontWeight.w600,
                            color: Colors.purple.shade700),
                      ),
                    ]),
                    const SizedBox(height: 8),
                    Text(
                      _pick(
                        'Upload file DOCX để thay thế nội dung. Nội dung cũ sẽ được lưu làm phiên bản trước.',
                        'Upload a DOCX file to replace the content. The old content will be kept as the previous version.',
                      ),
                      style: TextStyle(
                          fontSize: 11, color: Colors.purple.shade500),
                    ),
                    const SizedBox(height: 10),
                    if (_replacingDocx)
                      Row(children: [
                        const SizedBox(
                            width: 14,
                            height: 14,
                            child: CircularProgressIndicator(
                                strokeWidth: 2, color: Colors.purple)),
                        const SizedBox(width: 8),
                        Expanded(
                          child: Text(
                            _replaceDocxStatus ??
                                _pick('Đang xử lý...', 'Processing...'),
                            style: TextStyle(
                                fontSize: 12, color: Colors.purple.shade600),
                          ),
                        ),
                      ])
                    else
                      OutlinedButton.icon(
                        onPressed: _replaceWithDocx,
                        icon: Icon(Icons.folder_open_outlined,
                            size: 16, color: Colors.purple.shade700),
                        label: Text(
                            _pick('Chọn file .docx', 'Choose .docx file'),
                            style: TextStyle(color: Colors.purple.shade700)),
                        style: OutlinedButton.styleFrom(
                            side: BorderSide(color: Colors.purple.shade300)),
                      ),
                    if (!_replacingDocx && _replaceDocxStatus != null) ...[
                      const SizedBox(height: 8),
                      Container(
                        padding: const EdgeInsets.symmetric(
                            horizontal: 8, vertical: 6),
                        decoration: BoxDecoration(
                          color: _looksLikeError(_replaceDocxStatus)
                              ? Colors.red.shade50
                              : Colors.green.shade50,
                          borderRadius: BorderRadius.circular(6),
                        ),
                        child: Row(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Icon(
                              _looksLikeError(_replaceDocxStatus)
                                  ? Icons.error_outline
                                  : Icons.check_circle_outline,
                              size: 14,
                              color: _looksLikeError(_replaceDocxStatus)
                                  ? Colors.red.shade700
                                  : Colors.green.shade700,
                            ),
                            const SizedBox(width: 4),
                            Expanded(
                                child: Text(_replaceDocxStatus!,
                                    style: TextStyle(
                                      fontSize: 11.5,
                                      color: _looksLikeError(_replaceDocxStatus)
                                          ? Colors.red.shade700
                                          : Colors.green.shade700,
                                    ))),
                          ],
                        ),
                      ),
                    ],
                  ],
                ),
              ),
              const SizedBox(height: 16),
            ],

            // ── DA CHUYEN sang UnifiedShareSheet (xem _buildUnifiedSharingBlock o tren) ──
            // Tu phase 3 sharing roadmap, visibility/group_id/audience_user_ids deu
            // duoc quan ly qua ShareGrant. Khi save form nay, ta gui visibility='private'
            // mac dinh; cac grant thuc te do user thao tac qua UnifiedShareSheet.
            const SizedBox(height: 8),

            _buildDateField(
              label: _pick('Ngày hiệu lực', 'Effective date'),
              icon: Icons.calendar_today_outlined,
              value: _effectiveDate,
              onPick: () => _pickDate(isEffective: true),
              // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

              onClear: () => setState(() => _effectiveDate = null),
            ),
            const SizedBox(height: 16),

            _buildDateField(
              label: _pick('Ngày hết hạn', 'Expiration date'),
              icon: Icons.event_busy_outlined,
              value: _endDate,
              onPick: () => _pickDate(isEffective: false),
              // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

              onClear: () => setState(() => _endDate = null),
            ),
            const SizedBox(height: 16),
            const Divider(),
            const SizedBox(height: 12),

            // ── TAGS ──────────────────────────────────────────────
            Row(
              children: [
                const Icon(Icons.label_outline,
                    size: 16, color: Colors.blueGrey),
                const SizedBox(width: 6),
                Text(
                  'Tags (${_tags.length})',
                  style: Theme.of(context)
                      .textTheme
                      .labelLarge
                      ?.copyWith(fontWeight: FontWeight.w600),
                ),
                const Spacer(),
                if ((_templateIdForTagGen ?? widget.id) != null)
                  (_generatingTags
                      ? const SizedBox(
                          width: 16,
                          height: 16,
                          child: CircularProgressIndicator(strokeWidth: 2),
                        )
                      : Tooltip(
                          message: _pick(
                            'Tự động tạo tags bằng AI',
                            'Generate tags automatically with AI',
                          ),
                          child: IconButton(
                            onPressed: _generateTags,
                            icon: const Icon(Icons.auto_awesome,
                                size: 18, color: Colors.purple),
                            padding: EdgeInsets.zero,
                            constraints: const BoxConstraints(
                                minWidth: 28, minHeight: 28),
                          ),
                        )),
              ],
            ),
            const SizedBox(height: 8),

            // Tag chips display
            if (_tags.isNotEmpty)
              Wrap(
                spacing: 6,
                runSpacing: 6,
                children: _tags
                    .map((tag) => Chip(
                          label:
                              Text(tag, style: const TextStyle(fontSize: 12)),
                          deleteIcon: const Icon(Icons.close, size: 14),
                          // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

                          onDeleted: () => setState(() => _tags.remove(tag)),
                          backgroundColor: Colors.blue.shade50,
                          side: BorderSide(color: Colors.blue.shade200),
                          padding: const EdgeInsets.symmetric(horizontal: 4),
                          materialTapTargetSize:
                              MaterialTapTargetSize.shrinkWrap,
                        ))
                    .toList(),
              ),

            const SizedBox(height: 8),

            // Manual tag input
            Row(
              children: [
                Expanded(
                  child: TextField(
                    controller: _tagInputCtrl,
                    decoration: InputDecoration(
                      hintText: _pick('Thêm tag...', 'Add a tag...'),
                      hintStyle: const TextStyle(fontSize: 13),
                      isDense: true,
                      contentPadding: const EdgeInsets.symmetric(
                          horizontal: 10, vertical: 8),
                      border: OutlineInputBorder(
                          borderRadius: BorderRadius.circular(6)),
                    ),
                    style: const TextStyle(fontSize: 13),
                    onSubmitted: (v) {
                      final t = v.trim();
                      if (t.isNotEmpty && !_tags.contains(t)) {
                        // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

                        setState(() => _tags.add(t));
                      }
                      _tagInputCtrl.clear();
                    },
                  ),
                ),
                const SizedBox(width: 6),
                IconButton(
                  icon: const Icon(Icons.add_circle_outline, size: 20),
                  color: Colors.blue,
                  onPressed: () {
                    final t = _tagInputCtrl.text.trim();
                    if (t.isNotEmpty && !_tags.contains(t)) {
                      // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

                      setState(() => _tags.add(t));
                    }
                    _tagInputCtrl.clear();
                  },
                  padding: EdgeInsets.zero,
                  constraints:
                      const BoxConstraints(minWidth: 32, minHeight: 32),
                ),
              ],
            ),
            Padding(
              padding: const EdgeInsets.only(top: 4),
              child: Text(
                _pick(
                  'Nhập tên tag + Enter để thêm. AI chỉ khả dụng sau khi mẫu đã được tạo.',
                  'Type a tag name and press Enter to add it. AI features are available only after the template is created.',
                ),
                style: TextStyle(fontSize: 11, color: Colors.grey.shade500),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
