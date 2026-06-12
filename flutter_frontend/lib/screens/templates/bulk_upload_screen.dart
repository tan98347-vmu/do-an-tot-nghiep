// === MÀN HÌNH UPLOAD HÀNG LOẠT BIỂU MẪU ===
// Tải nhiều file DOCX cùng lúc (chọn thư mục _FolderPicker), parse Excel danh sách (_parseExcel 'templates/bulk/parse-excel/'), chọn prompt nhận diện biến (_pickDetectionPrompt/_saveDetectionPrompt).
// - _startUpload: upload từng file ('templates/bulk/upload-single/') với tiến độ từng dòng (_FileRow); xong mở /templates/<id>. _cancelUpload để dừng.

// Tệp này dùng để: dựng giao diện và orchestration UI trong flutter_frontend/lib/screens/templates/bulk_upload_screen.dart.
import 'dart:async';
import 'dart:convert';
import 'dart:html' as html;
import 'dart:typed_data';
import 'dart:ui_web' as ui_web;
import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../core/api_client.dart';
import '../../l10n/app_strings.dart';
import '../../providers/prompts_provider.dart';
import '../../widgets/ai/prompt_picker_dialog.dart';
import '../../widgets/ai/save_prompt_dialog.dart';

// ─────────────────────────────────────────────────────────────────────────────
// Singleton folder picker – registered once, reused across rebuilds
// ─────────────────────────────────────────────────────────────────────────────

// Bộ chọn thư mục (web): lấy nhiều file DOCX cùng lúc qua input HTML.

class _FolderPicker {
  static _FolderPicker? _instance;
  factory _FolderPicker() => _instance ??= _FolderPicker._internal();

  static const _viewType = 'bulk_upload_folder_picker_v2';

  late final html.FileUploadInputElement input;
  StreamSubscription? _changeSub;

  _FolderPicker._internal() {
    input = html.FileUploadInputElement()
      ..setAttribute('webkitdirectory', '')
      ..setAttribute('multiple', '');
    // Invisible overlay — covers the button so user clicks land directly on it
    input.style.cssText =
        'position:absolute;top:0;left:0;width:100%;height:100%;'
        'opacity:0;cursor:pointer;margin:0;padding:0;border:0;';

    // Register platform view factory (Flutter Web embeds HTML element here)
    ui_web.platformViewRegistry.registerViewFactory(_viewType, (int _) => input);
  }

  /// Set callback for when files are selected. Replaces any previous callback.
  // Đăng ký callback khi người dùng chọn file từ thư mục.

  void onFiles(void Function(List<html.File>) cb) {
    _changeSub?.cancel();
    _changeSub = input.onChange.listen((_) {
      final f = input.files;
      if (f != null && f.isNotEmpty) {
        cb(List<html.File>.from(f));
      }
      // Reset so the same folder can be re-selected next time
      input.value = '';
    });
  }

  // Bật/tắt bộ chọn thư mục.

  void setEnabled(bool v) {
    input.style.pointerEvents = v ? 'auto' : 'none';
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Models
// ─────────────────────────────────────────────────────────────────────────────

// Trạng thái 1 dòng file upload: chờ/đang xử lý/xong/lỗi/đã hủy.

enum _RowStatus { waiting, processing, done, error, cancelled }
// Chế độ upload hàng loạt: AI nhận diện biến / dùng biến dựng sẵn.

enum _BulkUploadMode { aiDetect, prebuiltVariables }

// Mô hình 1 dòng file trong bảng upload (tên, trạng thái, biến, lỗi).

class _FileRow {
  final String filename;
  String title;
  String description;
  String effectiveDate;
  String endDate;
  List<String> tags;
  List<String> groups;
  Uint8List? bytes;
  _RowStatus status;
  String message;
  int? createdId;
  List<String> assignedGroups;
  List<String> unmatchedGroups;

  _FileRow({
    required this.filename,
    this.title = '',
    this.description = '',
    this.effectiveDate = '',
    this.endDate = '',
    this.tags = const [],
    this.groups = const [],
    this.bytes,
    this.status = _RowStatus.waiting,
    this.message = '',
    this.createdId,
    this.assignedGroups = const [],
    this.unmatchedGroups = const [],
  });
}

// ─────────────────────────────────────────────────────────────────────────────
// Screen
// ─────────────────────────────────────────────────────────────────────────────

// Widget màn UPLOAD HÀNG LOẠT MẪU — ConsumerStatefulWidget.

class BulkUploadScreen extends ConsumerStatefulWidget {
  const BulkUploadScreen({super.key});

  @override
  ConsumerState<BulkUploadScreen> createState() => _BulkUploadScreenState();
}

// State màn upload hàng loạt: chọn file/thư mục, parse Excel, upload từng file có tiến độ.

class _BulkUploadScreenState extends ConsumerState<BulkUploadScreen> {
  List<_FileRow> _rows = [];
  bool _picking = false;       // waiting for user to select folder
  bool _loadingBytes = false;  // reading file bytes from disk
  bool _parsingExcel = false;  // sending excel to backend
  bool _uploading = false;     // uploading templates
  _BulkUploadMode _uploadMode = _BulkUploadMode.aiDetect;
  bool _cancelRequested = false;
  bool _downloadingSample = false;
  CancelToken? _activeUploadCancelToken;

  // Prompt tùy chỉnh hỗ trợ AI nhận diện biến (dùng chung cho cả lô upload).
  final TextEditingController _detectionHintCtrl = TextEditingController();
  String? _detectionPromptId;
  String _detectionPromptTitle = '';

  String? _folderName;
  String? _excelStatus;
  String? _pickError;
  int _errorCount = 0;

  late final _FolderPicker _picker;

  AppStrings get _s => AppStrings.of(context);

  @override
  // Mở màn: khởi tạo bộ chọn thư mục + lắng nghe chọn file.

  void initState() {
    super.initState();
    _picker = _FolderPicker();
    _picker.onFiles(_onFilesFromPicker);
    _picker.setEnabled(true);
  }

  @override
  // Rời màn: dọn bộ chọn + tài nguyên.

  void dispose() {
    _picker.onFiles((_) {}); // detach callback
    _detectionHintCtrl.dispose();
    super.dispose();
  }

  // ── Called when user selects a folder via the HTML overlay ────────────────
  // Khi chọn file từ thư mục -> dựng danh sách dòng + (nếu có) parse Excel kèm theo.

  void _onFilesFromPicker(List<html.File> files) async {
    // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

    setState(() {
      _picking = false;
      _loadingBytes = true;
      _rows = [];
      _folderName = null;
      _excelStatus = null;
      _pickError = null;
      _errorCount = 0;
    });
    _picker.setEnabled(false);

    // Separate Excel vs DOCX
    html.File? excelFile;
    final docxFiles = <html.File>[];

    for (final f in files) {
      final name = f.name.toLowerCase();
      if (name.endsWith('.xlsx')) {
        if (excelFile == null || name == 'upload.xlsx') excelFile = f;
      } else if (name.endsWith('.docx') && !name.startsWith(r'~$')) {
        docxFiles.add(f);
      }
    }

    if (docxFiles.isEmpty) {
      // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

      setState(() {
        _loadingBytes = false;
        _pickError = _s.pick(
          'Không tìm thấy file .docx nào. (Tổng số file trong thư mục: ${files.length})',
          'No .docx files found. (Total files in folder: ${files.length})',
        );
      });
      _picker.setEnabled(true);
      return;
    }

    // Folder display name
    final rel = _relPath(files.first);
    final folderName = rel.contains('/')
        ? rel.split('/').first
        : _s.pick('Thư mục đã chọn', 'Selected folder');

    // Read all DOCX bytes
    final rows = <_FileRow>[];
    for (final f in docxFiles) {
      final bytes = await _readBytes(f);
      rows.add(_FileRow(
        filename: f.name,
        title: f.name.replaceAll(RegExp(r'\.docx$', caseSensitive: false), ''),
        bytes: bytes,
        status: bytes == null ? _RowStatus.error : _RowStatus.waiting,
        message: bytes == null
            ? _s.pick('Không đọc được file (lỗi FileReader)',
                'Could not read file (FileReader error)')
            : '',
      ));
    }

    // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

    setState(() {
      _rows = rows;
      _loadingBytes = false;
      _folderName = _s.pick(
        '$folderName  •  ${docxFiles.length} file DOCX'
            '${excelFile != null ? "  •  upload.xlsx ✓" : ""}',
        '$folderName  •  ${docxFiles.length} DOCX file(s)'
            '${excelFile != null ? "  •  upload.xlsx ✓" : ""}',
      );
    });
    _picker.setEnabled(true);

    // Parse Excel metadata
    if (excelFile != null) {
      final eb = await _readBytes(excelFile);
      if (eb != null) await _parseExcel(eb, excelFile.name, rows);
    } else {
      // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

      setState(() {
        _excelStatus = _s.pick(
          '⚠ Không có upload.xlsx — dùng tên file làm tiêu đề, AI tự tạo tag.',
          '⚠ No upload.xlsx — using file names as titles, AI will generate tags.',
        );
      });
    }
  }

  // ── Read file bytes — dùng readAsDataUrl (base64) vì readAsArrayBuffer
  //    trả về kiểu không ổn định giữa các phiên bản Flutter Web / Dart 3
  bool get _isPrebuiltUploadMode => _uploadMode == _BulkUploadMode.prebuiltVariables;

  String get _uploadModeRequestValue =>
      _isPrebuiltUploadMode ? 'prebuilt_variables' : 'ai_detect';

  String get _processingStatusLabel => _isPrebuiltUploadMode
      ? _s.pick('Đang kiểm tra biến có sẵn...', 'Checking existing variables...')
      : _s.pick('Đang xử lý AI...', 'Running AI detection...');

  // Khối chọn chế độ upload (AI nhận diện biến / biến dựng sẵn).

  Widget _buildModeSelector() {
    final busy = _uploading || _loadingBytes || _parsingExcel;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          _s.pick('Chế độ upload', 'Upload mode'),
          style: TextStyle(
            fontSize: 13,
            fontWeight: FontWeight.w600,
            color: Colors.grey.shade700,
          ),
        ),
        const SizedBox(height: 10),
        SegmentedButton<_BulkUploadMode>(
          segments: [
            ButtonSegment<_BulkUploadMode>(
              value: _BulkUploadMode.aiDetect,
              icon: const Icon(Icons.auto_fix_high_outlined, size: 16),
              label: Text(_s.pick('AI detect biến', 'AI variable detection')),
            ),
            ButtonSegment<_BulkUploadMode>(
              value: _BulkUploadMode.prebuiltVariables,
              icon: const Icon(Icons.data_object_outlined, size: 16),
              label: Text(_s.pick('DOCX đã có {{biến}}', 'DOCX with {{variables}}')),
            ),
          ],
          selected: {_uploadMode},
          onSelectionChanged: busy
              ? null
              : (selection) {
                  if (selection.isEmpty) return;
                  // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

                  setState(() => _uploadMode = selection.first);
                },
        ),
        const SizedBox(height: 6),
        Text(
          _isPrebuiltUploadMode
              ? _s.pick(
                  'Dùng cho DOCX đã chứa sẵn placeholder {{ten_bien}}. Hệ thống bỏ qua AI detect và chỉ đọc biến có sẵn.',
                  'For DOCX files that already contain {{variable_name}} placeholders. The system skips AI detection and only reads existing variables.',
                )
              : _s.pick(
                  'Dùng cho DOCX chưa có biến. Hệ thống sẽ gọi AI để nhận diện và chuyển thành {{ten_bien}}.',
                  'For DOCX files without variables. The system runs AI detection and converts spots into {{variable_name}}.',
                ),
          style: TextStyle(fontSize: 11.5, color: Colors.grey.shade600),
        ),
      ],
    );
  }

  // Ô nhập prompt tùy chỉnh giúp AI nhận diện biến tốt hơn (chỉ hiện ở chế độ AI detect).
  Widget _buildDetectionPromptSection() {
    if (_isPrebuiltUploadMode) return const SizedBox.shrink();
    final busy = _uploading || _loadingBytes || _parsingExcel;
    final hasSavedPrompt = _detectionPromptId != null;
    return Padding(
      padding: const EdgeInsets.only(top: 14),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            _s.pick('Prompt nhận diện biến (tùy chọn)',
                'Variable-detection prompt (optional)'),
            style: TextStyle(
              fontSize: 13,
              fontWeight: FontWeight.w600,
              color: Colors.grey.shade700,
            ),
          ),
          const SizedBox(height: 6),
          Text(
            _s.pick(
              'Gợi ý cho AI cách tách/gộp biến. Ví dụ: "Các giá trị sau dấu hai chấm gộp thành 1 biến; hạn chế số biến; tập trung biến ở giữa văn bản; phần đầu hạn chế dùng biến".',
              'Hints for the AI on how to split/merge variables, e.g. "Merge values after a colon into one variable; minimize the number of variables; concentrate them in the middle; avoid variables near the top".',
            ),
            style: TextStyle(fontSize: 11.5, color: Colors.grey.shade600),
          ),
          const SizedBox(height: 8),
          if (hasSavedPrompt)
            Padding(
              padding: const EdgeInsets.only(bottom: 8),
              child: Chip(
                avatar: const Icon(Icons.bookmark, size: 16),
                label: Text(
                  _s.pick('Prompt: ', 'Prompt: ') +
                      (_detectionPromptTitle.isEmpty
                          ? '#$_detectionPromptId'
                          : _detectionPromptTitle),
                ),
                onDeleted: busy
                    ? null
                    : () => setState(() {
                          _detectionPromptId = null;
                          _detectionPromptTitle = '';
                        }),
              ),
            ),
          TextField(
            controller: _detectionHintCtrl,
            enabled: !busy,
            minLines: 2,
            maxLines: 5,
            maxLength: 2000,
            decoration: InputDecoration(
              hintText: _s.pick(
                  'Nhập gợi ý nhận diện biến...', 'Type a detection hint...'),
              border: const OutlineInputBorder(),
              isDense: true,
            ),
            onChanged: (_) {
              // Người dùng tự nhập -> dùng văn bản tự do thay cho prompt đã lưu.
              if (_detectionPromptId != null) {
                setState(() {
                  _detectionPromptId = null;
                  _detectionPromptTitle = '';
                });
              }
            },
          ),
          const SizedBox(height: 8),
          Wrap(
            spacing: 10,
            children: [
              OutlinedButton.icon(
                onPressed: busy ? null : _pickDetectionPrompt,
                icon: const Icon(Icons.folder_open, size: 16),
                label: Text(_s.pick('Chọn prompt đã lưu', 'Pick saved prompt')),
              ),
              OutlinedButton.icon(
                onPressed: busy ? null : _saveDetectionPrompt,
                icon: const Icon(Icons.save_outlined, size: 16),
                label: Text(_s.pick('Lưu prompt', 'Save prompt')),
              ),
            ],
          ),
        ],
      ),
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
          content: Text(_s.pick('Nhập nội dung prompt trước khi lưu.',
              'Enter prompt content before saving.')),
        ),
      );
      return;
    }
    final prompt = await SavePromptDialog.show(
      context,
      initialTitle: _detectionPromptTitle.isNotEmpty
          ? _detectionPromptTitle
          : _s.pick('Prompt nhận diện biến', 'Variable-detection prompt'),
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
      SnackBar(content: Text(_s.pick('Đã lưu prompt "${prompt.title}".',
          'Saved prompt "${prompt.title}".'))),
    );
  }

  // Đọc bytes 1 file (web FileReader).

  Future<Uint8List?> _readBytes(html.File file) {
    final c = Completer<Uint8List?>();
    final r = html.FileReader();
    r.onLoad.listen((_) {
      try {
        final dataUrl = r.result as String; // "data:...;base64,XXXX"
        final comma = dataUrl.indexOf(',');
        if (comma == -1) { c.complete(null); return; }
        c.complete(base64Decode(dataUrl.substring(comma + 1)));
      } catch (e) {
        c.complete(null);
      }
    });
    r.onError.listen((_) => c.complete(null));
    r.readAsDataUrl(file); // returns base64 string — always works in all browsers
    return c.future;
  }

  // Lấy đường dẫn tương đối của file trong thư mục đã chọn.

  String _relPath(html.File f) {
    try {
      final rp = (f as dynamic).webkitRelativePath as String?;
      if (rp != null && rp.isNotEmpty) return rp;
    } catch (_) {}
    return f.name;
  }

  // ── Parse Excel metadata ─────────────────────────────────────────────────
  // Parse file Excel danh sách ('templates/bulk/parse-excel/') để gán biến cho từng DOCX.

  Future<void> _parseExcel(Uint8List bytes, String name, List<_FileRow> rows) async {
    // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

    setState(() {
      _parsingExcel = true;
      _excelStatus = _s.pick('Đang đọc file upload.xlsx...', 'Reading upload.xlsx...');
    });
    try {
      // Gọi API hoặc tác vụ bất đồng bộ rồi chờ kết quả trước khi cập nhật giao diện.

      final resp = await ApiClient().dio.post(
        'templates/bulk/parse-excel/',
        data: FormData.fromMap({
          'excel_file': MultipartFile.fromBytes(bytes, filename: name),
        }),
      );
      final excelRows = (resp.data['rows'] as List? ?? []);
      final Map<String, Map<String, dynamic>> byName = {};
      for (final r in excelRows) {
        final fn = (r['filename'] as String? ?? '').toLowerCase().trim();
        if (fn.isNotEmpty) byName[fn] = r as Map<String, dynamic>;
      }

      final useOrder = byName.isEmpty;
      int matched = 0;
      // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

      setState(() {
        for (int i = 0; i < rows.length; i++) {
          Map<String, dynamic>? meta;
          if (useOrder && i < excelRows.length) {
            meta = excelRows[i] as Map<String, dynamic>;
          } else {
            final k = rows[i].filename.toLowerCase();
            meta = byName[k] ??
                byName[k.replaceAll(RegExp(r'\.docx$'), '')] ??
                byName['${k.replaceAll(RegExp(r'\.docx$'), '')}.docx'];
          }
          if (meta != null) {
            final t = (meta['title'] as String? ?? '').trim();
            if (t.isNotEmpty) rows[i].title = t;
            rows[i].description = meta['description'] as String? ?? '';
            rows[i].effectiveDate = meta['effective_date'] as String? ?? '';
            rows[i].endDate = meta['end_date'] as String? ?? '';
            rows[i].tags = List<String>.from(meta['tags'] ?? []);
            rows[i].groups = List<String>.from(meta['groups'] ?? []);
            matched++;
          }
        }
        _excelStatus = matched == rows.length
            ? _s.pick(
                '✓ Đọc upload.xlsx: tất cả ${rows.length} file đã khớp thông tin.',
                '✓ upload.xlsx loaded: all ${rows.length} files matched.',
              )
            : _s.pick(
                '✓ Đọc upload.xlsx: $matched/${rows.length} file khớp. '
                    '${rows.length - matched} file không khớp tên → dùng tên file.',
                '✓ upload.xlsx loaded: $matched/${rows.length} files matched. '
                    '${rows.length - matched} unmatched → using file names.',
              );
      });
    } catch (e) {
      // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

      setState(() => _excelStatus = _s.pick('✗ Lỗi đọc Excel: $e', '✗ Excel read error: $e'));
    } finally {
      // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

      setState(() => _parsingExcel = false);
    }
  }

  // ── Bulk upload ───────────────────────────────────────────────────────────
  // Nút Bắt đầu upload: upload từng file ('templates/bulk/upload-single/') với tiến độ từng dòng.

  Future<void> _startUpload() async {
    if (_rows.isEmpty || _uploading) return;
    // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

    setState(() {
      _uploading = true;
      _errorCount = 0;
      _cancelRequested = false;
      _activeUploadCancelToken = null;
      _picker.setEnabled(false);
      for (final r in _rows) {
        r.status = _RowStatus.waiting;
        r.message = '';
        r.createdId = null;
      }
    });

    for (int i = 0; i < _rows.length; i++) {
      if (_cancelRequested) {
        // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

        setState(() {
          for (int j = i; j < _rows.length; j++) {
            final pendingRow = _rows[j];
            if (pendingRow.status == _RowStatus.waiting) {
              pendingRow.status = _RowStatus.cancelled;
              pendingRow.message = _s.pick(
                'Đã hủy trước khi upload',
                'Cancelled before upload',
              );
            }
          }
        });
        break;
      }
      final row = _rows[i];
      if (row.bytes == null) {
        // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

        setState(() { row.status = _RowStatus.error; row.message = _s.pick('Không có dữ liệu', 'No data'); _errorCount++; });
        continue;
      }
      // Yield to the event loop so a queued tap on the Stop button can flip
      // _cancelRequested before we kick off the next request. Without this,
      // a click that lands between the previous row finishing and this one
      // starting only takes effect after the new request is in flight,
      // which makes it feel like Stop "missed" one file.
      await Future<void>.delayed(Duration.zero);
      if (_cancelRequested) {
        setState(() {
          for (int j = i; j < _rows.length; j++) {
            final pendingRow = _rows[j];
            if (pendingRow.status == _RowStatus.waiting) {
              pendingRow.status = _RowStatus.cancelled;
              pendingRow.message = _s.pick(
                'Đã hủy trước khi upload',
                'Cancelled before upload',
              );
            }
          }
        });
        break;
      }
      // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

      setState(() => row.status = _RowStatus.processing);
      try {
        final genTags = row.tags.isEmpty;
        final cancelToken = CancelToken();
        _activeUploadCancelToken = cancelToken;
        // Gọi API hoặc tác vụ bất đồng bộ rồi chờ kết quả trước khi cập nhật giao diện.

        final resp = await ApiClient().dio.post(
          'templates/bulk/upload-single/',
          data: FormData.fromMap({
            'docx_file': MultipartFile.fromBytes(row.bytes!, filename: row.filename),
            'title': row.title,
            'description': row.description,
            'effective_date': row.effectiveDate,
            'end_date': row.endDate,
            'tags': jsonEncode(row.tags),
            'groups': jsonEncode(row.groups),
            'generate_tags': genTags ? 'true' : 'false',
            'upload_mode': _uploadModeRequestValue,
            // Prompt nhận diện biến (chung cho cả lô): ưu tiên prompt đã lưu, nếu
            // không thì gửi gợi ý tự do. Chỉ áp dụng cho chế độ AI detect.
            if (!_isPrebuiltUploadMode && _detectionPromptId != null)
              'detection_prompt_id': _detectionPromptId!,
            if (!_isPrebuiltUploadMode &&
                _detectionPromptId == null &&
                _detectionHintCtrl.text.trim().isNotEmpty)
              'detection_hint': _detectionHintCtrl.text.trim(),
          }),
          cancelToken: cancelToken,
          options: ApiClient.ollamaOptions(contentType: 'multipart/form-data'),
        );
        _activeUploadCancelToken = null;
        final d = resp.data as Map<String, dynamic>;
        final newTags = List<String>.from(d['tags'] ?? []);
        final vars = (d['detected_vars'] as List? ?? []).length;
        final assigned = List<String>.from(d['assigned_groups'] ?? const []);
        final unmatched = List<String>.from(d['unmatched_groups'] ?? const []);
        final createdIds = List<int>.from(d['created_ids'] ?? const []);
        final invalidDates = (d['invalid_dates'] as List? ?? const [])
            .whereType<Map>()
            .map((m) => '${m['field']}=${m['value']}')
            .toList();
        // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

        setState(() {
          row.status = _RowStatus.done;
          row.createdId = d['id'] as int?;
          row.tags = newTags;
          row.assignedGroups = assigned;
          row.unmatchedGroups = unmatched;
          final parts = <String>[
            _s.pick('$vars biến', '$vars variable${vars == 1 ? '' : 's'}'),
            _s.pick(
              '${newTags.length} tag${genTags && newTags.isNotEmpty ? " (AI)" : ""}',
              '${newTags.length} tag${newTags.length == 1 ? '' : 's'}${genTags && newTags.isNotEmpty ? " (AI)" : ""}',
            ),
          ];
          if (createdIds.length > 1) {
            parts.add(_s.pick(
              '${createdIds.length} bản (theo nhóm)',
              '${createdIds.length} copies (per group)',
            ));
          }
          if (assigned.isNotEmpty) {
            parts.add(_s.pick(
              'Nhóm: ${assigned.join(", ")}',
              'Groups: ${assigned.join(", ")}',
            ));
          }
          if (unmatched.isNotEmpty) {
            parts.add(_s.pick(
              '⚠ Không tìm thấy nhóm: ${unmatched.join(", ")}',
              '⚠ Groups not found: ${unmatched.join(", ")}',
            ));
          }
          if (invalidDates.isNotEmpty) {
            parts.add(_s.pick(
              '⚠ Ngày không hợp lệ (bỏ qua): ${invalidDates.join(", ")}',
              '⚠ Invalid dates (ignored): ${invalidDates.join(", ")}',
            ));
          }
          row.message = parts.join(' • ');
        });
      } catch (e) {
        _activeUploadCancelToken = null;
        if (e is DioException && CancelToken.isCancel(e)) {
          // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

          setState(() {
            row.status = _RowStatus.cancelled;
            row.message = _s.pick(
              'Đã hủy trong lúc upload',
              'Cancelled during upload',
            );
          });
          continue;
        }
        String msg = e.toString();
        if (e is DioException) msg = e.response?.data?['detail'] ?? msg;
        // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

        setState(() { row.status = _RowStatus.error; row.message = msg; _errorCount++; });
      }
    }

    // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

    setState(() {
      _uploading = false;
      _activeUploadCancelToken = null;
      _picker.setEnabled(true);
    });
  }

  // Nút Hủy: dừng quá trình upload hàng loạt.

  void _cancelUpload() {
    if (!_uploading) return;
    // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

    setState(() => _cancelRequested = true);
    _activeUploadCancelToken?.cancel('user_cancelled');
  }

  Future<void> _downloadSample() async {
    if (_downloadingSample) return;
    setState(() => _downloadingSample = true);
    try {
      final resp = await ApiClient().dio.get<List<int>>(
            'templates/bulk/sample/',
            options: Options(responseType: ResponseType.bytes),
          );
      final bytes = Uint8List.fromList(resp.data ?? const []);
      final blob = html.Blob([bytes],
          'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet');
      final url = html.Url.createObjectUrlFromBlob(blob);
      final anchor = html.AnchorElement(href: url)
        ..download = 'upload.xlsx'
        ..style.display = 'none';
      html.document.body?.append(anchor);
      anchor.click();
      anchor.remove();
      html.Url.revokeObjectUrl(url);
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(
        content: Text(_s.pick(
            'Không tải được upload.xlsx mẫu: $e',
            'Failed to download sample upload.xlsx: $e')),
        backgroundColor: Colors.red.shade600,
      ));
    } finally {
      if (mounted) setState(() => _downloadingSample = false);
    }
  }

  // ─────────────────────────────────────────────────────────────────────────
  // Build
  // ─────────────────────────────────────────────────────────────────────────

  @override
  // Dựng màn: panel cấu hình + tiến độ + bảng/danh sách file.

  Widget build(BuildContext context) {
    final isMobile = MediaQuery.sizeOf(context).width < 700;
    final done = _rows.where((r) => r.status == _RowStatus.done).length;
    final processing = _rows.where((r) => r.status == _RowStatus.processing).length;
    final total = _rows.length;
    final canUpload = total > 0 && !_uploading && !_loadingBytes && !_parsingExcel;

    // Dựng khung màn hình chính để chứa app bar, body, action và các vùng giao diện khác.

    return Scaffold(
      backgroundColor: const Color(0xFFF8FAFC),
      appBar: AppBar(
        backgroundColor: Colors.white,
        elevation: 0,
        // Điều hướng người dùng sang màn phù hợp theo kết quả thao tác hiện tại.

        leading: IconButton(icon: const Icon(Icons.arrow_back), onPressed: () => context.pop()),
        title: Text(_s.pick('Tải lên nhiều mẫu', 'Bulk upload templates'),
            style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 17)),
        actions: const [],
        bottom: const PreferredSize(
          preferredSize: Size.fromHeight(1),
          child: Divider(height: 1, color: Color(0xFFE2E8F0)),
        ),
      ),
      body: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          _buildTopPanel(),
          if (total > 0) _buildProgress(done, total, processing),
          Expanded(
            child: total == 0
                ? _buildEmpty()
                : isMobile
                    ? _buildCardList()
                    : _buildTable(),
          ),
        ],
      ),
    );
  }

  // ── Top panel ─────────────────────────────────────────────────────────────
  // Panel trên: chọn chế độ, chọn thư mục/file, chọn prompt nhận diện biến.

  Widget _buildTopPanel() {
    final busy = _uploading || _loadingBytes || _parsingExcel;

    return Container(
      color: Colors.white,
      padding: const EdgeInsets.fromLTRB(20, 14, 20, 14),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        _buildModeSelector(),
        _buildDetectionPromptSection(),
        const SizedBox(height: 14),

        // Instructions
        Container(
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(
            color: Colors.blue.shade50,
            borderRadius: BorderRadius.circular(8),
            border: Border.all(color: Colors.blue.shade100),
          ),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            _Step('1', _s.pick(
              'Đặt các file .docx vào một thư mục. Thêm upload.xlsx (tuỳ chọn) với các cột: ten file · tieu de mau · mo ta · ngay hieu luc · ngay het han · tag · nhom duoc phan mau. Cột nhóm: viết có dấu ("Phòng Kế Toán") hoặc không dấu ("phong ke toan") đều khớp, ngăn cách bằng dấu phẩy. Để trống → mẫu vào "Mẫu của tôi" của admin (luồng cũ).',
              'Put .docx files in a folder. Optionally add upload.xlsx with columns (Vietnamese headers): ten file · tieu de mau · mo ta · ngay hieu luc · ngay het han · tag · nhom duoc phan mau. Group column accepts names with diacritics ("Phòng Kế Toán") or without ("phong ke toan"), comma-separated. Empty cell → template lands in admin\'s "My templates" (legacy flow).',
            )),
            const SizedBox(height: 6),
            _Step('2', _s.pick(
              'Nhấn nút bên dưới → chọn thư mục → xem danh sách file',
              'Click the button below → pick a folder → review the file list',
            )),
            const SizedBox(height: 6),
            _Step('3', _s.pick(
              'Nhấn "Bắt đầu upload" để tạo mẫu hàng loạt',
              'Click "Start upload" to create templates in bulk',
            )),
            const SizedBox(height: 10),
            Align(
              alignment: Alignment.centerLeft,
              child: OutlinedButton.icon(
                onPressed: _downloadingSample ? null : _downloadSample,
                style: OutlinedButton.styleFrom(
                  foregroundColor: Colors.blue.shade700,
                  side: BorderSide(color: Colors.blue.shade300),
                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                ),
                icon: _downloadingSample
                    ? const SizedBox(width: 14, height: 14,
                        child: CircularProgressIndicator(strokeWidth: 2))
                    : const Icon(Icons.download_outlined, size: 16),
                label: Text(
                  _downloadingSample
                      ? _s.pick('Đang tải...', 'Downloading...')
                      : _s.pick('Tải upload.xlsx mẫu', 'Download sample upload.xlsx'),
                  style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w600),
                ),
              ),
            ),
          ]),
        ),

        const SizedBox(height: 14),

        // Action row: folder picker + upload button
        Row(crossAxisAlignment: CrossAxisAlignment.center, children: [
          // The button is a Stack: Flutter container for visuals + HtmlElementView for real click
          SizedBox(
            height: 44,
            child: Stack(
              children: [
                // Visual layer (IgnorePointer so HTML element handles all events)
                IgnorePointer(
                  child: Container(
                    padding: const EdgeInsets.symmetric(horizontal: 18),
                    decoration: BoxDecoration(
                      color: busy ? Colors.grey.shade400 : const Color(0xFF3B82F6),
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: Row(mainAxisSize: MainAxisSize.min, children: [
                      if (_loadingBytes || _parsingExcel)
                        const SizedBox(width: 16, height: 16,
                            child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                      else
                        const Icon(Icons.folder_open, color: Colors.white, size: 20),
                      const SizedBox(width: 8),
                      Text(
                        _picking
                            ? _s.pick('Đang chờ chọn thư mục...', 'Waiting for folder selection...')
                            : _loadingBytes
                                ? _s.pick('Đang đọc file...', 'Reading files...')
                                : _parsingExcel
                                    ? _s.pick('Đang đọc Excel...', 'Reading Excel...')
                                    : _folderName != null
                                        ? _s.pick('Chọn lại thư mục', 'Re-select folder')
                                        : _s.pick('Chọn thư mục', 'Choose folder'),
                        style: const TextStyle(
                            color: Colors.white, fontWeight: FontWeight.w600, fontSize: 14),
                      ),
                    ]),
                  ),
                ),
                // HTML input overlay — user clicks this directly (guaranteed user gesture)
                if (!busy)
                  Positioned.fill(
                    child: GestureDetector(
                      // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

                      onTap: () => setState(() => _picking = true),
                      child: const HtmlElementView(
                          viewType: _FolderPicker._viewType),
                    ),
                  ),
              ],
            ),
          ),

          // Upload button — shown when files are ready
          if (_rows.isNotEmpty && !_uploading && !_loadingBytes && !_parsingExcel) ...[
            const SizedBox(width: 12),
            SizedBox(
              height: 44,
              child: FilledButton.icon(
                onPressed: _startUpload,
                style: FilledButton.styleFrom(
                  backgroundColor: Colors.green.shade700,
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                ),
                icon: const Icon(Icons.cloud_upload_outlined, size: 18),
                label: Text(
                    _s.pick(
                      'Bắt đầu upload (${_rows.length} file)',
                      'Start upload (${_rows.length} file${_rows.length == 1 ? '' : 's'})',
                    ),
                    style: const TextStyle(fontWeight: FontWeight.w600)),
              ),
            ),
          ],
          if (_uploading) ...[
            const SizedBox(width: 12),
            SizedBox(
              height: 44,
              child: FilledButton.icon(
                onPressed: _cancelRequested ? null : _cancelUpload,
                style: FilledButton.styleFrom(
                  backgroundColor: _cancelRequested
                      ? Colors.orange.shade700
                      : Colors.red.shade600,
                  disabledBackgroundColor: Colors.orange.shade700,
                  disabledForegroundColor: Colors.white,
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                ),
                icon: _cancelRequested
                    ? const SizedBox(width: 16, height: 16,
                        child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                    : const Icon(Icons.stop_circle_outlined, size: 18),
                label: Text(
                  _cancelRequested
                      ? _s.pick('Đang dừng...', 'Stopping...')
                      : _s.pick('Dừng upload', 'Stop upload'),
                  style: const TextStyle(color: Colors.white),
                ),
              ),
            ),
          ],

          // Folder name badge
          if (_folderName != null) ...[
            const SizedBox(width: 12),
            Expanded(
              child: Container(
                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 9),
                decoration: BoxDecoration(
                  color: Colors.blue.shade50,
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(color: Colors.blue.shade200),
                ),
                child: Row(children: [
                  Icon(Icons.folder, size: 16, color: Colors.blue.shade600),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(_folderName!,
                        style: TextStyle(fontSize: 13, color: Colors.blue.shade800,
                            fontWeight: FontWeight.w500),
                        overflow: TextOverflow.ellipsis),
                  ),
                ]),
              ),
            ),
          ],
        ]),

        // Error message
        if (_pickError != null) ...[
          const SizedBox(height: 10),
          _Banner(text: _pickError!, isError: true),
        ],

        // Excel status
        if (_excelStatus != null) ...[
          const SizedBox(height: 8),
          _Banner(
            text: _excelStatus!,
            isError: _excelStatus!.startsWith('✗'),
            isWarning: _excelStatus!.startsWith('⚠'),
          ),
        ],
      ]),
    );
  }

  // ── Progress bar ──────────────────────────────────────────────────────────
  // Thanh tiến độ tổng (done/total/đang xử lý).

  Widget _buildProgress(int done, int total, int processing) {
    final allDone = !_uploading && done > 0;
    final progress = total > 0 ? done / total : 0.0;
    final color = allDone && _errorCount == 0 ? Colors.green
        : allDone && _errorCount > 0 ? Colors.orange
        : Colors.blue;

    return Container(
      color: Colors.white,
      padding: const EdgeInsets.fromLTRB(20, 10, 20, 14),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        const Divider(height: 1, color: Color(0xFFE2E8F0)),
        const SizedBox(height: 10),
        Row(children: [
          Expanded(
            child: Text(
              _uploading
                  ? _s.pick(
                      'Đang xử lý... $done/$total hoàn thành (đang xử lý: $processing)',
                      'Processing... $done/$total done (in flight: $processing)',
                    )
                  : allDone && _errorCount == 0
                      ? _s.pick(
                          '✓ Hoàn thành: $done/$total file thành công',
                          '✓ Done: $done/$total files succeeded',
                        )
                      : allDone
                          ? _s.pick(
                              '$done thành công  •  $_errorCount lỗi  •  tổng $total',
                              '$done succeeded  •  $_errorCount failed  •  total $total',
                            )
                          : _s.pick(
                              'Sẵn sàng upload $total mẫu văn bản',
                              'Ready to upload $total template${total == 1 ? '' : 's'}',
                            ),
              style: TextStyle(
                fontSize: 13,
                fontWeight: FontWeight.w600,
                color: allDone && _errorCount == 0
                    ? Colors.green.shade700
                    : allDone ? Colors.orange.shade800
                    : Colors.grey.shade800,
              ),
            ),
          ),
          if (_uploading)
            const SizedBox(width: 18, height: 18,
                child: CircularProgressIndicator(strokeWidth: 2.5)),
        ]),
        if (_uploading || done > 0) ...[
          const SizedBox(height: 8),
          ClipRRect(
            borderRadius: BorderRadius.circular(6),
            child: LinearProgressIndicator(
              value: progress,
              minHeight: 10,
              backgroundColor: Colors.grey.shade200,
              valueColor: AlwaysStoppedAnimation<Color>(color),
            ),
          ),
          const SizedBox(height: 4),
          Row(mainAxisAlignment: MainAxisAlignment.spaceBetween, children: [
            Text(_s.pick('$done / $total file', '$done / $total file${total == 1 ? '' : 's'}'),
                style: TextStyle(fontSize: 11, color: Colors.grey.shade500)),
            Text('${(progress * 100).toStringAsFixed(0)}%',
                style: TextStyle(fontSize: 11, fontWeight: FontWeight.w600,
                    color: Colors.grey.shade600)),
          ]),
        ],
      ]),
    );
  }

  // ── Empty state ───────────────────────────────────────────────────────────
  // Trạng thái trống khi chưa chọn file.

  Widget _buildEmpty() {
    return Center(
      child: Column(mainAxisAlignment: MainAxisAlignment.center, children: [
        Icon(Icons.folder_open_outlined, size: 80, color: Colors.grey.shade200),
        const SizedBox(height: 16),
        Text(_s.pick('Chưa chọn thư mục', 'No folder selected'),
            style: TextStyle(fontSize: 18, fontWeight: FontWeight.w600,
                color: Colors.grey.shade500)),
        const SizedBox(height: 8),
        Text(_s.pick(
              'Nhấn "Chọn thư mục" ở trên để bắt đầu',
              'Click "Choose folder" above to start',
            ),
            style: TextStyle(fontSize: 13, color: Colors.grey.shade400)),
        if (_picking) ...[
          const SizedBox(height: 24),
          const CircularProgressIndicator(),
          const SizedBox(height: 12),
          Text(_s.pick(
                'Đang chờ bạn chọn thư mục...',
                'Waiting for you to pick a folder...',
              ),
              style: TextStyle(fontSize: 13, color: Colors.blue.shade400)),
        ],
      ]),
    );
  }

  // ── Desktop table ─────────────────────────────────────────────────────────
  // Bảng danh sách file upload (bố cục rộng).

  Widget _buildTable() {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(children: [
        // Header row
        Container(
          decoration: BoxDecoration(
            color: Colors.grey.shade100,
            borderRadius: const BorderRadius.vertical(top: Radius.circular(8)),
            border: Border.all(color: Colors.grey.shade200),
          ),
          child: Row(children: [
            _TH('', w: 40), _TH('', w: 32),
            _TH(_s.pick('Tên file', 'File name'), f: 3),
            _TH(_s.pick('Tiêu đề mẫu', 'Template title'), f: 4),
            _TH(_s.pick('Ngày HH', 'Validity'), f: 2),
            _TH(_s.pick('Tags', 'Tags'), f: 3),
            _TH(_s.pick('Nhóm', 'Groups'), f: 3),
            _TH(_s.pick('Kết quả', 'Result'), f: 4),
          ]),
        ),
        // Data rows
        Container(
          decoration: BoxDecoration(
            border: Border.all(color: Colors.grey.shade200),
            borderRadius: const BorderRadius.vertical(bottom: Radius.circular(8)),
          ),
          child: ListView.separated(
            physics: const NeverScrollableScrollPhysics(),
            shrinkWrap: true,
            itemCount: _rows.length,
            separatorBuilder: (_, __) => Divider(height: 1, color: Colors.grey.shade200),
            itemBuilder: (_, i) => _buildRow(i),
          ),
        ),
      ]),
    );
  }

  // Dựng 1 hàng file trong bảng.

  Widget _buildRow(int i) {
    final row = _rows[i];
    final bg = switch (row.status) {
      _RowStatus.done       => const Color(0xFFF0FDF4),
      _RowStatus.error      => const Color(0xFFFFF5F5),
      _RowStatus.processing => const Color(0xFFEFF6FF),
      _RowStatus.cancelled  => const Color(0xFFFFF7ED),
      _ => Colors.white,
    };
    return InkWell(
      // Điều hướng người dùng sang màn phù hợp theo kết quả thao tác hiện tại.

      onTap: row.createdId != null ? () => context.go('/templates/${row.createdId}') : null,
      child: Container(
        color: bg,
        child: Row(children: [
          SizedBox(width: 40, child: Center(
            child: Text('${i+1}', style: TextStyle(fontSize: 12, color: Colors.grey.shade400)))),
          SizedBox(width: 32, child: Padding(
              padding: const EdgeInsets.all(6),
              child: _StatusIcon(row.status))),
          Expanded(flex: 3, child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 10),
            child: Text(row.filename,
                style: const TextStyle(fontSize: 12, fontFamily: 'monospace'),
                overflow: TextOverflow.ellipsis))),
          Expanded(flex: 4, child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 10),
            child: Text(row.title.isEmpty ? '—' : row.title,
                style: TextStyle(fontSize: 12, fontWeight: FontWeight.w500,
                    color: row.createdId != null ? Colors.blue.shade700 : null,
                    decoration: row.createdId != null ? TextDecoration.underline : null),
                overflow: TextOverflow.ellipsis))),
          Expanded(flex: 2, child: Padding(
            padding: const EdgeInsets.all(10),
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisSize: MainAxisSize.min,
                children: [
                  if (row.effectiveDate.isNotEmpty)
                    Text(_s.pick('Từ: ${row.effectiveDate}', 'From: ${row.effectiveDate}'),
                        style: TextStyle(fontSize: 10, color: Colors.grey.shade600)),
                  if (row.endDate.isNotEmpty)
                    Text(_s.pick('Đến: ${row.endDate}', 'To: ${row.endDate}'),
                        style: TextStyle(fontSize: 10, color: Colors.red.shade400)),
                ]))),
          Expanded(flex: 3, child: Padding(
            padding: const EdgeInsets.all(8),
            child: row.tags.isEmpty
                ? Text('—', style: TextStyle(fontSize: 11, color: Colors.grey.shade300))
                : Wrap(spacing: 3, runSpacing: 3,
                    children: row.tags.take(4).map(_TagChip.new).toList()))),
          Expanded(flex: 3, child: Padding(
            padding: const EdgeInsets.all(8),
            child: row.groups.isEmpty
                ? Text('—', style: TextStyle(fontSize: 11, color: Colors.grey.shade300))
                : Wrap(spacing: 3, runSpacing: 3,
                    children: row.groups.take(5).map(_GroupChip.new).toList()))),
          Expanded(flex: 4, child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 10),
            child: _statusWidget(row))),
        ]),
      ),
    );
  }

  // Widget hiển thị trạng thái 1 dòng file (icon + nhãn).

  Widget _statusWidget(_FileRow row) {
    if (row.status == _RowStatus.processing) {
      if (_isPrebuiltUploadMode) {
        return Row(children: [
          const SizedBox(width: 14, height: 14,
              child: CircularProgressIndicator(strokeWidth: 2, color: Colors.blue)),
          const SizedBox(width: 8),
          Text(_processingStatusLabel, style: TextStyle(fontSize: 11, color: Colors.blue.shade600)),
        ]);
      }
      return Row(children: [
        const SizedBox(width: 14, height: 14,
            child: CircularProgressIndicator(strokeWidth: 2, color: Colors.blue)),
        const SizedBox(width: 8),
        Text(_s.pick('Đang xử lý AI...', 'Running AI detection...'),
            style: TextStyle(fontSize: 11, color: Colors.blue.shade600)),
      ]);
    }
    if (row.status == _RowStatus.waiting) {
      return Text(_s.pick('Chờ...', 'Waiting...'),
          style: TextStyle(fontSize: 11, color: Colors.grey.shade400));
    }
    return Text(row.message,
        style: TextStyle(fontSize: 11,
            color: row.status == _RowStatus.done
                ? Colors.green.shade700
                : row.status == _RowStatus.cancelled
                    ? Colors.orange.shade700
                    : Colors.red.shade600),
        maxLines: 2, overflow: TextOverflow.ellipsis);
  }

  // ── Mobile card list ──────────────────────────────────────────────────────
  // Danh sách file dạng thẻ (bố cục hẹp).

  Widget _buildCardList() {
    return ListView.separated(
      padding: const EdgeInsets.all(12),
      itemCount: _rows.length,
      separatorBuilder: (_, __) => const SizedBox(height: 8),
      itemBuilder: (_, i) {
        final row = _rows[i];
        final bc = switch (row.status) {
          _RowStatus.done       => Colors.green.shade300,
          _RowStatus.error      => Colors.red.shade300,
          _RowStatus.processing => Colors.blue.shade300,
          _RowStatus.cancelled  => Colors.orange.shade200,
          _ => Colors.grey.shade200,
        };
        return InkWell(
          borderRadius: BorderRadius.circular(8),
          // Điều hướng người dùng sang màn phù hợp theo kết quả thao tác hiện tại.

          onTap: row.createdId != null ? () => context.go('/templates/${row.createdId}') : null,
          child: Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: Colors.white,
              borderRadius: BorderRadius.circular(8),
              border: Border.all(color: bc, width: 1.5),
            ),
            child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Column(children: [
                Text('${i+1}', style: TextStyle(fontSize: 10, color: Colors.grey.shade400)),
                const SizedBox(height: 4),
                _StatusIcon(row.status),
              ]),
              const SizedBox(width: 12),
              Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text(row.title.isNotEmpty ? row.title : row.filename,
                    style: const TextStyle(fontSize: 13, fontWeight: FontWeight.bold)),
                const SizedBox(height: 2),
                Text(row.filename,
                    style: TextStyle(fontSize: 11, color: Colors.grey.shade500,
                        fontFamily: 'monospace')),
                if (row.tags.isNotEmpty) ...[
                  const SizedBox(height: 6),
                  Wrap(spacing: 4, runSpacing: 4,
                      children: row.tags.take(5).map(_TagChip.new).toList()),
                ],
                if (row.groups.isNotEmpty) ...[
                  const SizedBox(height: 6),
                  Wrap(spacing: 4, runSpacing: 4,
                      children: row.groups.take(6).map(_GroupChip.new).toList()),
                ],
                const SizedBox(height: 6),
                _statusWidget(row),
              ])),
            ]),
          ),
        );
      },
    );
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Small helper widgets
// ─────────────────────────────────────────────────────────────────────────────

// Widget 1 bước trong chỉ dẫn quy trình.

class _Step extends StatelessWidget {
  final String n, text;
  const _Step(this.n, this.text);
  @override
  // Dựng 1 bước chỉ dẫn.

  Widget build(BuildContext ctx) => Row(
    crossAxisAlignment: CrossAxisAlignment.start,
    children: [
      Container(
        width: 18, height: 18,
        decoration: BoxDecoration(color: Colors.blue.shade600, shape: BoxShape.circle),
        alignment: Alignment.center,
        child: Text(n, style: const TextStyle(color: Colors.white, fontSize: 10, fontWeight: FontWeight.bold)),
      ),
      const SizedBox(width: 6),
      Expanded(child: Text(text, style: TextStyle(fontSize: 12, color: Colors.blue.shade800))),
    ],
  );
}

// Widget banner thông báo.

class _Banner extends StatelessWidget {
  final String text;
  final bool isError, isWarning;
  const _Banner({required this.text, this.isError = false, this.isWarning = false});
  @override
  // Dựng banner.

  Widget build(BuildContext ctx) {
    final color = isError ? Colors.red : isWarning ? Colors.orange : Colors.green;
    final icon = isError ? Icons.error_outline
        : isWarning ? Icons.warning_amber_outlined
        : Icons.check_circle_outline;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      decoration: BoxDecoration(
        color: color.shade50,
        borderRadius: BorderRadius.circular(6),
        border: Border.all(color: color.shade200),
      ),
      child: Row(children: [
        Icon(icon, size: 15, color: color.shade700),
        const SizedBox(width: 8),
        Expanded(child: Text(text,
            style: TextStyle(fontSize: 12, color: color.shade800))),
      ]),
    );
  }
}

// Widget chip hiển thị 1 biến/tag.

class _TagChip extends StatelessWidget {
  final String label;
  const _TagChip(this.label);
  @override
  // Dựng chip tag.

  Widget build(BuildContext ctx) => Container(
    padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
    decoration: BoxDecoration(
      color: Colors.indigo.shade50, borderRadius: BorderRadius.circular(4)),
    child: Text(label, style: TextStyle(fontSize: 10, color: Colors.indigo.shade700)),
  );
}

class _GroupChip extends StatelessWidget {
  final String label;
  const _GroupChip(this.label);
  @override
  Widget build(BuildContext ctx) => Container(
    padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
    decoration: BoxDecoration(
      color: Colors.green.shade50,
      borderRadius: BorderRadius.circular(4),
      border: Border.all(color: Colors.green.shade200, width: 0.5),
    ),
    child: Row(mainAxisSize: MainAxisSize.min, children: [
      Icon(Icons.group_outlined, size: 10, color: Colors.green.shade700),
      const SizedBox(width: 3),
      Text(label, style: TextStyle(fontSize: 10, color: Colors.green.shade800)),
    ]),
  );
}

// Widget icon theo trạng thái dòng file.

class _StatusIcon extends StatelessWidget {
  final _RowStatus s;
  const _StatusIcon(this.s);
  @override
  // Dựng icon trạng thái.

  Widget build(BuildContext ctx) => switch (s) {
    _RowStatus.done       => const Icon(Icons.check_circle, color: Colors.green, size: 20),
    _RowStatus.error      => const Icon(Icons.cancel, color: Colors.red, size: 20),
    _RowStatus.cancelled  => const Icon(Icons.stop_circle_outlined, color: Colors.orange, size: 20),
    _RowStatus.processing => const SizedBox(width: 18, height: 18,
        child: CircularProgressIndicator(strokeWidth: 2.5, color: Colors.blue)),
    _ => Icon(Icons.radio_button_unchecked, color: Colors.grey.shade300, size: 20),
  };
}

// Widget ô tiêu đề cột bảng.

class _TH extends StatelessWidget {
  final String label;
  final int f;
  final double? w;
  const _TH(this.label, {this.f = 1, this.w});
  @override
  // Dựng ô tiêu đề cột.

  Widget build(BuildContext ctx) {
    final child = Padding(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 9),
      child: Text(label, style: TextStyle(fontSize: 11, fontWeight: FontWeight.w700,
          color: Colors.grey.shade600)),
    );
    return w != null ? SizedBox(width: w, child: child) : Expanded(flex: f, child: child);
  }
}
