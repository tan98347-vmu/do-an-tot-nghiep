// === MÀN HÌNH ĐIỀN THÔNG TIN & SINH VĂN BẢN TỪ MẪU ===
// Hiển thị các biến của mẫu (templateDetailProvider) để điền tay hoặc tự động:
// - 'Điền từ hồ sơ' (_doPrefill -> 'prefill-profile-async'), 'Điền từ ngữ cảnh công ty' (_doPrefillCompany -> 'prefill-company-async').
// - 'Trích xuất từ PDF' (_extractFromPdf -> 'extract-pdf-async'), từ ảnh/camera OCR (_pickImageFromSource -> 'extract-image-async').
// - Tùy chỉnh prompt + 'Check prompt' (kiểm an toàn) + xem trước (_showPreview 'ai/doc/preview/').
// - _createDocument: POST 'ai/doc/create-async/' rồi mở /documents/<id>. recentPromptsProvider gợi ý prompt gần đây.

// Tệp này dùng để: dựng giao diện và orchestration UI trong flutter_frontend/lib/screens/ai_doc/ai_doc_fill_screen.dart.
import 'dart:async';
import 'dart:html' as html;
import 'dart:typed_data';
// ignore: undefined_prefixed_name
import 'dart:ui_web' as ui;
import 'package:dio/dio.dart';
import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../core/api_client.dart';
import '../../core/browser_alert.dart';
import '../../core/run_ai_task.dart';
import '../../providers/documents_provider.dart';
import '../../providers/prompt_preflight_provider.dart';
import '../../providers/prompts_provider.dart';
import '../../providers/recent_prompts_provider.dart';
import '../../providers/templates_provider.dart';
import '../../widgets/ai/prompt_picker_dialog.dart';
import '../../widgets/ai/prompt_preview_dialog.dart';
import '../../widgets/ai/save_prompt_dialog.dart';

// Nguồn chọn ảnh để trích thông tin: chụp camera / chọn từ thư viện.

enum _ImagePickSource { camera, library }

// Widget màn ĐIỀN & SINH VĂN BẢN TỪ MẪU — ConsumerStatefulWidget; nhận templateId (+ prefill).

class AiDocFillScreen extends ConsumerStatefulWidget {
  final int templateId;
  final bool prefill;
  // Widget màn ĐIỀN THÔNG TIN & SINH VĂN BẢN TỪ MẪU; nhận templateId (+ prefill tùy chọn).
  const AiDocFillScreen({super.key, required this.templateId, this.prefill = false});

  @override
  ConsumerState<AiDocFillScreen> createState() => _AiDocFillScreenState();
}

// State màn điền: controller từng biến, ảnh/PDF nguồn, prompt tùy chỉnh, trạng thái tác vụ AI.

class _AiDocFillScreenState extends ConsumerState<AiDocFillScreen> {
  final _titleCtrl = TextEditingController();
  final Map<String, TextEditingController> _varCtrls = {};
  final _extraRulesCtrl = TextEditingController();
  final _promptNameCtrl = TextEditingController();
  String? _selectedPromptId;
  int? _parentDocumentId;
  bool _saving = false;
  bool _prefilling = false;
  bool _prefillingCompany = false;
  bool _previewing = false;
  PlatformFile? _pdfFile;
  bool _extracting = false;
  Uint8List? _ocrImageBytes;
  String? _ocrImageName;
  String? _ocrImageSourceLabel;
  bool _extractingImage = false;
  int _previewCounter = 0;
  String? _previewToken;
  String? _promptCheckToken;
  bool _checkingPrompt = false;
  bool _saveAsPrompt = false;

  // Trình duyệt/thiết bị có hỗ trợ chụp ảnh trực tiếp từ camera không (quyết định hiện nút chụp).
  bool _supportsDirectCameraCapture() {
    final userAgent = html.window.navigator.userAgent.toLowerCase();
    return RegExp(r'android|iphone|ipad|ipod').hasMatch(userAgent);
  }

  @override
  // Mở màn: nạp mẫu + biến, khởi tạo controller cho từng biến, nạp prompt gần đây.
  void initState() {
    super.initState();
    if (widget.prefill) {
      WidgetsBinding.instance.addPostFrameCallback((_) => _runProfilePrefill());
    }
  }

  // Reset toàn bộ state khi đổi mẫu (controller biến, ảnh/PDF đã chọn, token check prompt).
  void _resetTemplateState() {
    for (final controller in _varCtrls.values) {
      controller.dispose();
    }
    _varCtrls.clear();
    _titleCtrl.clear();
    _selectedPromptId = null;
    _promptNameCtrl.clear();
    _parentDocumentId = null;
    _pdfFile = null;
    _ocrImageBytes = null;
    _ocrImageName = null;
    _ocrImageSourceLabel = null;
    _previewCounter = 0;
    _promptCheckToken = null;
    _saving = false;
    _prefilling = false;
    _prefillingCompany = false;
    _previewing = false;
    _extracting = false;
    _extractingImage = false;
  }

  @override
  // Khi đổi templateId (điều hướng sang mẫu khác) -> reset state và nạp lại mẫu.
  void didUpdateWidget(covariant AiDocFillScreen oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.templateId == widget.templateId && oldWidget.prefill == widget.prefill) {
      return;
    }
    _resetTemplateState();
    if (widget.prefill) {
      WidgetsBinding.instance.addPostFrameCallback((_) => _runProfilePrefill());
    }
  }

  // Định dạng thời gian đã trôi của tác vụ AI (mm:ss) để hiển thị tiến độ.
  String _fmtElapsed(Duration duration) {
    final minutes = duration.inMinutes.remainder(60).toString().padLeft(2, '0');
    final seconds = duration.inSeconds.remainder(60).toString().padLeft(2, '0');
    return '${duration.inHours > 0 ? '${duration.inHours.toString().padLeft(2, '0')}:' : ''}$minutes:$seconds';
  }

  // Ghi log mốc thời gian các bước luồng AI (prefill/extract/create) để chẩn đoán.
  void _logAiFlow(String flow, String message, Stopwatch stopwatch, [Map<String, Object?> extra = const {}]) {
    final suffix = extra.entries
        .where((entry) => entry.value != null)
        .map((entry) => '${entry.key}=${entry.value}')
        .join(' | ');
    debugPrint(
      '[$flow] $message | elapsed=${_fmtElapsed(stopwatch.elapsed)}${suffix.isNotEmpty ? ' | $suffix' : ''}',
    );
  }

  // Tạo Options Dio (timeout dài, content-type) cho các request AI nặng.
  Options _aiRequestOptions({String? contentType}) =>
      ApiClient.ollamaOptions(contentType: contentType);

  // Bọc 1 tác vụ AI: bấm giờ + log + xử lý hủy/lỗi chung.
  Future<T> _runTimedAiTask<T>({
    required String flow,
    required Future<T> Function(Stopwatch stopwatch) action,
  }) async {
    final stopwatch = Stopwatch()..start();
    _logAiFlow(flow, 'start', stopwatch);
    final ticker = Timer.periodic(const Duration(seconds: 1), (_) {
      _logAiFlow(flow, 'processing', stopwatch);
    });

    try {
      final result = await action(stopwatch);
      _logAiFlow(flow, 'success', stopwatch);
      return result;
    } catch (e, st) {
      _logAiFlow(flow, 'error', stopwatch, {'error': e});
      debugPrint('[$flow] stacktrace=$st');
      rethrow;
    } finally {
      ticker.cancel();
      stopwatch.stop();
    }
  }

  @override
  // Dựng màn: danh sách ô nhập biến + nút điền tự động (hồ sơ/công ty), trích từ PDF/ảnh, ô prompt tùy chỉnh, nút Xem trước & Tạo văn bản.
  Widget build(BuildContext context) {
    // Lắng nghe provider để widget tự động dựng lại khi dữ liệu hoặc trạng thái thay đổi.

    final tmplAsync = ref.watch(templateDetailProvider(widget.templateId));
    final isMobile = MediaQuery.sizeOf(context).width < 700;

    return tmplAsync.when(
      // Dựng khung màn hình chính để chứa app bar, body, action và các vùng giao diện khác.

      loading: () => const Scaffold(body: Center(child: CircularProgressIndicator())),
      // Dựng khung màn hình chính để chứa app bar, body, action và các vùng giao diện khác.

      error: (e, _) => Scaffold(body: Center(child: Text('Lỗi: $e'))),
      data: (tmpl) {
        if (!tmpl.canUse) {
          // Dựng khung màn hình chính để chứa app bar, body, action và các vùng giao diện khác.

          return Scaffold(
            appBar: AppBar(
              title: const Text('Không có quyền sử dụng mẫu'),
              leading: IconButton(
                icon: const Icon(Icons.arrow_back),
                // Điều hướng người dùng sang màn phù hợp theo kết quả thao tác hiện tại.

                onPressed: () => context.go('/ai-doc'),
              ),
            ),
            body: Center(
              child: Padding(
                padding: const EdgeInsets.all(24),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Icon(Icons.lock_outline, size: 56, color: Colors.orange.shade300),
                    const SizedBox(height: 12),
                    const Text(
                      'Bạn chỉ có quyền xem mẫu này, không có quyền dùng nó để sinh văn bản.',
                      textAlign: TextAlign.center,
                    ),
                    const SizedBox(height: 12),
                    FilledButton.icon(
                      // Điều hướng người dùng sang màn phù hợp theo kết quả thao tác hiện tại.

                      onPressed: () => context.go('/ai-doc'),
                      icon: const Icon(Icons.arrow_back, size: 18),
                      label: const Text('Quay về danh sách mẫu'),
                    ),
                  ],
                ),
              ),
            ),
          );
        }
        for (final v in tmpl.variables) {
          _varCtrls.putIfAbsent(v, () => TextEditingController());
        }
        if (_titleCtrl.text.isEmpty) {
          _titleCtrl.text = 'Văn bản từ ${tmpl.title}';
        }

        // ── MOBILE LAYOUT ───────────────────────────────────────────────────
        if (isMobile) {
          // Dựng khung màn hình chính để chứa app bar, body, action và các vùng giao diện khác.

          return Scaffold(
            appBar: AppBar(
              title: const Text('Điền thông tin văn bản'),
              leading: IconButton(
                icon: const Icon(Icons.arrow_back),
                // Điều hướng người dùng sang màn phù hợp theo kết quả thao tác hiện tại.

                onPressed: () => context.go('/ai-doc'),
              ),
            ),
            body: SafeArea(
              child: SingleChildScrollView(
                padding: const EdgeInsets.fromLTRB(16, 12, 16, 24),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    // Template banner
                    Container(
                      padding: const EdgeInsets.all(12),
                      decoration: BoxDecoration(
                        color: Colors.blue.shade50,
                        borderRadius: BorderRadius.circular(8),
                      ),
                      child: Row(children: [
                        const Icon(Icons.file_copy_outlined, color: Colors.blue, size: 18),
                        const SizedBox(width: 10),
                        Expanded(child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(tmpl.title,
                                style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 13),
                                maxLines: 2, overflow: TextOverflow.ellipsis),
                            if ((tmpl.description as String).isNotEmpty)
                              Text(tmpl.description as String,
                                  style: TextStyle(fontSize: 11, color: Colors.grey.shade600),
                                  maxLines: 2, overflow: TextOverflow.ellipsis),
                          ],
                        )),
                      ]),
                    ),
                    const SizedBox(height: 16),

                    // Title
                    TextField(
                      controller: _titleCtrl,
                      decoration: const InputDecoration(
                        labelText: 'Tiêu đề văn bản *',
                        border: OutlineInputBorder(),
                        isDense: true,
                      ),
                    ),

                    // Variable fields
                    if ((tmpl.variables as List).isNotEmpty) ...[
                      const SizedBox(height: 16),
                      Row(children: [
                        Text('Điền thông tin vào mẫu',
                            style: Theme.of(context).textTheme.titleSmall
                                ?.copyWith(fontWeight: FontWeight.bold)),
                        const SizedBox(width: 8),
                        Container(
                          padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 2),
                          decoration: BoxDecoration(
                            color: Colors.blue, borderRadius: BorderRadius.circular(12)),
                          child: Text('${(tmpl.variables as List).length} trường',
                              style: const TextStyle(color: Colors.white, fontSize: 11)),
                        ),
                      ]),
                      const SizedBox(height: 10),
                      ...(tmpl.variables as List).map((v) => Padding(
                        padding: const EdgeInsets.only(bottom: 10),
                        child: TextField(
                          controller: _varCtrls[v as String],
                          decoration: InputDecoration(
                            labelText: (v as String).replaceAll('_', ' ').toUpperCase(),
                            border: const OutlineInputBorder(),
                            isDense: true,
                          ),
                        ),
                      )),
                    ],
                    const SizedBox(height: 16),

                    // AI Tools — collapsible tiles
                    Card(
                      margin: EdgeInsets.zero,
                      child: ExpansionTile(
                        leading: const Icon(Icons.person_outline, color: Colors.green, size: 20),
                        title: const Text('Điền từ hồ sơ',
                            style: TextStyle(fontSize: 13, fontWeight: FontWeight.w600)),
                        tilePadding: const EdgeInsets.symmetric(horizontal: 12),
                        childrenPadding: const EdgeInsets.fromLTRB(12, 0, 12, 12),
                        children: [
                          Text('AI đọc hồ sơ cá nhân và tự động điền các trường.',
                              style: TextStyle(fontSize: 12, color: Colors.grey.shade600)),
                          const SizedBox(height: 10),
                          SizedBox(
                            width: double.infinity,
                            child: OutlinedButton.icon(
                              onPressed: _prefilling ? null : _runProfilePrefill,
                              icon: _prefilling
                                  ? const SizedBox(width: 14, height: 14,
                                      child: CircularProgressIndicator(strokeWidth: 2))
                                  : const Icon(Icons.auto_awesome, size: 16),
                              label: Text(_prefilling ? 'Đang điền...' : 'Tự động điền'),
                            ),
                          ),
                        ],
                      ),
                    ),
                    Card(
                      margin: EdgeInsets.zero,
                      child: ExpansionTile(
                        leading: const Icon(Icons.business_outlined,
                            color: Color(0xFF1565C0), size: 20),
                        title: const Text('Điền từ ngữ cảnh công ty',
                            style: TextStyle(fontSize: 13, fontWeight: FontWeight.w600)),
                        tilePadding: const EdgeInsets.symmetric(horizontal: 12),
                        childrenPadding: const EdgeInsets.fromLTRB(12, 0, 12, 12),
                        children: [
                          Text('AI đọc thông tin công ty và điền các trường liên quan.',
                              style: TextStyle(fontSize: 12, color: Colors.grey.shade600)),
                          const SizedBox(height: 10),
                          SizedBox(
                            width: double.infinity,
                            child: OutlinedButton.icon(
                              onPressed: _prefillingCompany ? null : _runCompanyPrefill,
                              icon: _prefillingCompany
                                  ? const SizedBox(width: 14, height: 14,
                                      child: CircularProgressIndicator(strokeWidth: 2))
                                  : const Icon(Icons.auto_awesome, size: 16),
                              label: Text(_prefillingCompany ? 'Đang điền...' : 'Tự động điền'),
                            ),
                          ),
                        ],
                      ),
                    ),
                    Card(
                      margin: EdgeInsets.zero,
                      child: ExpansionTile(
                        leading: const Icon(Icons.picture_as_pdf, color: Colors.red, size: 20),
                        title: const Text('Trích xuất từ PDF',
                            style: TextStyle(fontSize: 13, fontWeight: FontWeight.w600)),
                        tilePadding: const EdgeInsets.symmetric(horizontal: 12),
                        childrenPadding: const EdgeInsets.fromLTRB(12, 0, 12, 12),
                        children: [
                          Text('Upload file PDF — AI tự động điền các trường.',
                              style: TextStyle(fontSize: 12, color: Colors.grey.shade600)),
                          const SizedBox(height: 10),
                          if (_pdfFile != null) ...[
                            Container(
                              width: double.infinity,
                              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
                              margin: const EdgeInsets.only(bottom: 8),
                              decoration: BoxDecoration(
                                color: Colors.red.shade50,
                                borderRadius: BorderRadius.circular(6),
                                border: Border.all(color: Colors.red.shade200),
                              ),
                              child: Row(children: [
                                const Icon(Icons.insert_drive_file_outlined, size: 14, color: Colors.red),
                                const SizedBox(width: 6),
                                Expanded(child: Text(_pdfFile!.name,
                                    style: const TextStyle(fontSize: 12),
                                    overflow: TextOverflow.ellipsis)),
                                GestureDetector(
                                  // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

                                  onTap: () => setState(() => _pdfFile = null),
                                  child: const Icon(Icons.close, size: 14, color: Colors.red),
                                ),
                              ]),
                            ),
                          ],
                          SizedBox(
                            width: double.infinity,
                            child: OutlinedButton.icon(
                              onPressed: _extracting ? null : _pickPdf,
                              icon: const Icon(Icons.upload_file, size: 16),
                              label: Text(_pdfFile == null ? 'Chọn file PDF' : 'Đổi file PDF'),
                            ),
                          ),
                          if (_pdfFile != null) ...[
                            const SizedBox(height: 8),
                            SizedBox(
                              width: double.infinity,
                              child: FilledButton.icon(
                                onPressed: _extracting ? null : () => _extractFromPdf(tmpl),
                                icon: _extracting
                                    ? const SizedBox(width: 16, height: 16,
                                        child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                                    : const Icon(Icons.document_scanner_outlined, size: 16),
                                label: Text(_extracting ? 'Đang trích xuất...' : 'Trích xuất & Điền'),
                                style: FilledButton.styleFrom(backgroundColor: Colors.red.shade600),
                              ),
                            ),
                          ],
                        ],
                      ),
                    ),
                    const SizedBox(height: 8),
                    _buildImageExtractionPanel(tmpl, compact: true),
                    const SizedBox(height: 8),
                    /*
                    Card(
                      margin: EdgeInsets.zero,
                      child: ExpansionTile(
                        leading: const Icon(Icons.bolt, color: Colors.orange, size: 20),
                        title: const Text('Prompt tùy chỉnh',
                            style: TextStyle(fontSize: 13, fontWeight: FontWeight.w600)),
                        tilePadding: const EdgeInsets.symmetric(horizontal: 12),
                        childrenPadding: const EdgeInsets.fromLTRB(12, 0, 12, 12),
                        children: [
                          promptsAsync.when(
                            loading: () => const LinearProgressIndicator(),
                            error: (_, __) => const Text('Không tải được prompts',
                                style: TextStyle(fontSize: 12)),
                            data: (prompts) => DropdownButtonFormField<String>(
                              value: _selectedPromptId,
                              isExpanded: true,
                              decoration: const InputDecoration(
                                labelText: 'Chọn prompt',
                                isDense: true,
                                border: OutlineInputBorder(),
                              ),
                              items: [
                                const DropdownMenuItem(value: null, child: Text('-- Không dùng --')),
                                ...prompts.map((p) => DropdownMenuItem(
                                  value: p.id.toString(),
                                  child: Text(p.title, overflow: TextOverflow.ellipsis),
                                )),
                              ],
                              // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

                              onChanged: (v) => setState(() => _selectedPromptId = v),
                            ),
                          ),
                        ],
                      ),
                    ),
                    */
                    const SizedBox(height: 20),

                    // Status
                    if (_prefilling || _prefillingCompany) Padding(
                      padding: const EdgeInsets.only(bottom: 12),
                      child: Row(children: [
                        const SizedBox(width: 18, height: 18,
                            child: CircularProgressIndicator(strokeWidth: 2)),
                        const SizedBox(width: 10),
                        Expanded(child: Text(
                          _prefillingCompany
                              ? 'AI đang điền từ ngữ cảnh công ty...'
                              : 'AI đang điền từ hồ sơ...',
                          style: const TextStyle(fontSize: 13),
                        )),
                      ]),
                    ),

                    _buildExtraRulesBlock(tmpl),

                    // Action buttons — full width on mobile
                    SizedBox(
                      width: double.infinity,
                      child: OutlinedButton.icon(
                        onPressed: (_previewing || _saving) ? null : () => _showPreview(tmpl),
                        icon: _previewing
                            ? const SizedBox(width: 16, height: 16,
                                child: CircularProgressIndicator(strokeWidth: 2))
                            : const Icon(Icons.preview_outlined, size: 18),
                        label: Text(_previewing ? 'Đang tải...' : 'Xem trước'),
                      ),
                    ),
                    const SizedBox(height: 10),
                    SizedBox(
                      width: double.infinity,
                      child: FilledButton.icon(
                        onPressed: _saving ||
                                (_extraRulesCtrl.text.trim().isNotEmpty &&
                                    (_promptCheckToken ?? '').isEmpty)
                            ? null
                            : () => _createDoc(tmpl),
                        icon: _saving
                            ? const SizedBox(width: 18, height: 18,
                                child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                            : const Icon(Icons.auto_awesome, size: 18),
                        label: Text(_saving
                            ? (_selectedPromptId != null ? 'AI đang xử lý...' : 'Đang tạo...')
                            : 'Tạo văn bản'),
                      ),
                    ),
                  ],
                ),
              ),
            ),
          );
        }

        // ── DESKTOP LAYOUT (giữ nguyên cấu trúc gốc) ─────────────────────
        return Scaffold(
          appBar: AppBar(
            title: const Text('Điền thông tin văn bản'),
            leading: IconButton(
              icon: const Icon(Icons.arrow_back),
              // Điều hướng người dùng sang màn phù hợp theo kết quả thao tác hiện tại.

              onPressed: () => context.go('/ai-doc'),
            ),
          ),
          body: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Left: form
              Expanded(
                flex: 2,
                child: SingleChildScrollView(
                  padding: const EdgeInsets.all(24),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      // Template info banner
                      Container(
                        padding: const EdgeInsets.all(16),
                        decoration: BoxDecoration(
                          color: Colors.blue.shade50,
                          borderRadius: BorderRadius.circular(8),
                        ),
                        child: Row(children: [
                          const Icon(Icons.file_copy_outlined, color: Colors.blue),
                          const SizedBox(width: 12),
                          Expanded(child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(tmpl.title,
                                  style: const TextStyle(fontWeight: FontWeight.bold)),
                              if ((tmpl.description as String).isNotEmpty)
                                Text(tmpl.description as String,
                                    style: TextStyle(fontSize: 12, color: Colors.grey.shade600)),
                            ],
                          )),
                        ]),
                      ),
                      const SizedBox(height: 20),

                      TextFormField(
                        controller: _titleCtrl,
                        decoration: const InputDecoration(labelText: 'Tiêu đề văn bản *'),
                      ),

                      if ((tmpl.variables as List).isNotEmpty) ...[
                        const SizedBox(height: 24),
                        Row(children: [
                          Text('Điền thông tin vào mẫu',
                              style: Theme.of(context).textTheme.titleMedium
                                  ?.copyWith(fontWeight: FontWeight.bold)),
                          const SizedBox(width: 8),
                          Container(
                            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                            decoration: BoxDecoration(
                              color: Colors.blue, borderRadius: BorderRadius.circular(12)),
                            child: Text('${(tmpl.variables as List).length} trường',
                                style: const TextStyle(color: Colors.white, fontSize: 12)),
                          ),
                        ]),
                        const SizedBox(height: 12),
                        ...(tmpl.variables as List).map((v) => Padding(
                          padding: const EdgeInsets.only(bottom: 12),
                          child: TextFormField(
                            controller: _varCtrls[v as String],
                            decoration: InputDecoration(
                              labelText: (v as String).replaceAll('_', ' ').toUpperCase(),
                              prefixText: '{{$v}}  ',
                              prefixStyle: TextStyle(
                                color: Colors.blue.shade400, fontSize: 11,
                                fontFamily: 'monospace'),
                            ),
                          ),
                        )),
                      ],

                      const SizedBox(height: 24),

                      if (_prefilling || _prefillingCompany) Padding(
                        padding: const EdgeInsets.only(bottom: 16),
                        child: Row(children: [
                          const SizedBox(width: 20, height: 20,
                              child: CircularProgressIndicator(strokeWidth: 2)),
                          const SizedBox(width: 12),
                          Text(_prefillingCompany
                              ? 'AI đang điền thông tin từ ngữ cảnh công ty...'
                              : 'AI đang điền thông tin từ hồ sơ...'),
                        ]),
                      ),

                      _buildExtraRulesBlock(tmpl),

                      // Action buttons
                      Row(children: [
                        OutlinedButton.icon(
                          onPressed: (_previewing || _saving) ? null : () => _showPreview(tmpl),
                          icon: _previewing
                              ? const SizedBox(width: 16, height: 16,
                                  child: CircularProgressIndicator(strokeWidth: 2))
                              : const Icon(Icons.preview_outlined, size: 18),
                          label: Text(_previewing ? 'Đang tải...' : 'Xem trước'),
                        ),
                        const SizedBox(width: 12),
                        FilledButton.icon(
                          onPressed: _saving ||
                                  (_extraRulesCtrl.text.trim().isNotEmpty &&
                                      (_promptCheckToken ?? '').isEmpty)
                              ? null
                              : () => _createDoc(tmpl),
                          icon: _saving
                              ? const SizedBox(width: 18, height: 18,
                                  child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                              : const Icon(Icons.auto_awesome, size: 18),
                          label: Text(_saving
                              ? (_selectedPromptId != null ? 'AI đang xử lý prompt...' : 'Đang tạo...')
                              : 'Tạo văn bản'),
                        ),
                      ]),
                    ],
                  ),
                ),
              ),

              // Right: tools panel (desktop only)
              SizedBox(
                width: 300,
                child: SingleChildScrollView(
                  padding: const EdgeInsets.all(16),
                  child: Column(children: [
                    // Prefill from profile
                    Card(
                      child: Padding(
                        padding: const EdgeInsets.all(16),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            const Row(children: [
                              Icon(Icons.person_outline, color: Colors.green),
                              SizedBox(width: 8),
                              Text('Điền từ hồ sơ',
                                  style: TextStyle(fontWeight: FontWeight.bold)),
                            ]),
                            const SizedBox(height: 8),
                            const Text('AI đọc hồ sơ và điền các trường phù hợp.',
                                style: TextStyle(fontSize: 12)),
                            const SizedBox(height: 12),
                            SizedBox(
                              width: double.infinity,
                              child: OutlinedButton.icon(
                                onPressed: _prefilling ? null : _runProfilePrefill,
                                icon: const Icon(Icons.auto_awesome, size: 16),
                                label: const Text('Tự động điền'),
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                    const SizedBox(height: 12),

                    // Prefill from company context
                    Card(
                      child: Padding(
                        padding: const EdgeInsets.all(16),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            const Row(children: [
                              Icon(Icons.business_outlined, color: Color(0xFF1565C0)),
                              SizedBox(width: 8),
                              Text('Điền từ ngữ cảnh công ty',
                                  style: TextStyle(fontWeight: FontWeight.bold)),
                            ]),
                            const SizedBox(height: 8),
                            const Text('AI đọc thông tin công ty và điền các trường liên quan.',
                                style: TextStyle(fontSize: 12)),
                            const SizedBox(height: 12),
                            SizedBox(
                              width: double.infinity,
                              child: OutlinedButton.icon(
                                onPressed: _prefillingCompany ? null : _runCompanyPrefill,
                                icon: _prefillingCompany
                                    ? const SizedBox(width: 14, height: 14,
                                        child: CircularProgressIndicator(strokeWidth: 2))
                                    : const Icon(Icons.auto_awesome, size: 16),
                                label: Text(_prefillingCompany ? 'Đang điền...' : 'Tự động điền'),
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                    const SizedBox(height: 12),

                    // PDF extraction
                    Card(
                      child: Padding(
                        padding: const EdgeInsets.all(16),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            const Row(children: [
                              Icon(Icons.picture_as_pdf, color: Colors.red),
                              SizedBox(width: 8),
                              Text('Trích xuất từ PDF',
                                  style: TextStyle(fontWeight: FontWeight.bold)),
                            ]),
                            const SizedBox(height: 6),
                            Text('Upload file PDF — AI tự động điền các trường.',
                                style: TextStyle(fontSize: 12, color: Colors.grey.shade600)),
                            const SizedBox(height: 12),
                            if (_pdfFile != null)
                              Container(
                                width: double.infinity,
                                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
                                margin: const EdgeInsets.only(bottom: 10),
                                decoration: BoxDecoration(
                                  color: Colors.red.shade50,
                                  borderRadius: BorderRadius.circular(6),
                                  border: Border.all(color: Colors.red.shade200),
                                ),
                                child: Row(children: [
                                  const Icon(Icons.insert_drive_file_outlined,
                                      size: 15, color: Colors.red),
                                  const SizedBox(width: 6),
                                  Expanded(child: Text(_pdfFile!.name,
                                      style: const TextStyle(fontSize: 12),
                                      overflow: TextOverflow.ellipsis)),
                                  GestureDetector(
                                    // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

                                    onTap: () => setState(() => _pdfFile = null),
                                    child: const Icon(Icons.close, size: 14, color: Colors.red),
                                  ),
                                ]),
                              ),
                            SizedBox(
                              width: double.infinity,
                              child: OutlinedButton.icon(
                                onPressed: _extracting ? null : _pickPdf,
                                icon: const Icon(Icons.upload_file, size: 16),
                                label: Text(_pdfFile == null ? 'Chọn file PDF' : 'Đổi file PDF'),
                              ),
                            ),
                            if (_pdfFile != null) ...[
                              const SizedBox(height: 8),
                              SizedBox(
                                width: double.infinity,
                                child: FilledButton.icon(
                                  onPressed: _extracting ? null : () => _extractFromPdf(tmpl),
                                  icon: _extracting
                                      ? const SizedBox(width: 16, height: 16,
                                          child: CircularProgressIndicator(
                                              strokeWidth: 2, color: Colors.white))
                                      : const Icon(Icons.document_scanner_outlined, size: 16),
                                  label: Text(_extracting ? 'Đang trích xuất...' : 'Trích xuất & Điền'),
                                  style: FilledButton.styleFrom(backgroundColor: Colors.red.shade600),
                                ),
                              ),
                            ],
                          ],
                        ),
                      ),
                    ),
                    const SizedBox(height: 12),
                    _buildImageExtractionPanel(tmpl, compact: false),
                    const SizedBox(height: 12),
                    /*
                    // Custom prompt
                    Card(
                      child: Padding(
                        padding: const EdgeInsets.all(16),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            const Row(children: [
                              Icon(Icons.bolt, color: Colors.orange),
                              SizedBox(width: 8),
                              Text('Prompt tùy chỉnh',
                                  style: TextStyle(fontWeight: FontWeight.bold)),
                            ]),
                            const SizedBox(height: 12),
                            promptsAsync.when(
                              loading: () => const LinearProgressIndicator(),
                              error: (_, __) => const Text('Không tải được prompts'),
                              data: (prompts) => DropdownButtonFormField<String>(
                                value: _selectedPromptId,
                                decoration: const InputDecoration(
                                    labelText: 'Chọn prompt', isDense: true),
                                items: [
                                  const DropdownMenuItem(
                                      value: null, child: Text('-- Không dùng --')),
                                  ...prompts.map((p) => DropdownMenuItem(
                                    value: p.id.toString(),
                                    child: Text(p.title, overflow: TextOverflow.ellipsis),
                                  )),
                                ],
                                // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

                                onChanged: (v) => setState(() => _selectedPromptId = v),
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                    */
                  ]),
                ),
              ),
            ],
          ),
        );
      },
    );
  }

  // ── Preview ────────────────────────────────────────────────────────────────

  // Nút Xem trước: hiển thị bản xem trước văn bản với giá trị biến hiện tại.
  Future<void> _showPreview(dynamic tmpl) async {
    // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

    setState(() => _previewing = true);
    try {
      final vars = <String, String>{};
      _varCtrls.forEach((k, ctrl) => vars[k] = ctrl.text);
      // Gọi API hoặc tác vụ bất đồng bộ rồi chờ kết quả trước khi cập nhật giao diện.

      final resp = await ApiClient().dio.post('ai/doc/preview/', data: {
        'template_id': widget.templateId,
        'variables': vars,
      });
      final htmlContent = resp.data['html'] as String? ?? '';
      if (!mounted) return;
      _openPreviewDialog(htmlContent, tmpl.title as String);
    } catch (e) {
      final message = _extractAiDocActionError(
        e,
        fallback: 'Không thể tự động điền từ hồ sơ lúc này.',
        serverFallback: 'Không thể tự động điền từ hồ sơ lúc này. Vui lòng thử lại sau ít phút.',
      );
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(message), backgroundColor: Colors.red),
        );
      }
      return;
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Lỗi tải xem trước: $e'), backgroundColor: Colors.red));
    } finally {
      // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

      if (mounted) setState(() => _previewing = false);
    }
  }

  // Mở dialog xem trước nội dung văn bản (HTML) phóng to.

  void _openPreviewDialog(String htmlContent, String title) {
    final viewKey = 'doc-preview-${widget.templateId}-${_previewCounter++}';
    // ignore: undefined_prefixed_name
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
              padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 14),
              decoration: BoxDecoration(
                color: Theme.of(ctx).colorScheme.primary,
                borderRadius: const BorderRadius.vertical(top: Radius.circular(12)),
              ),
              child: Row(children: [
                const Icon(Icons.preview_outlined, color: Colors.white, size: 20),
                const SizedBox(width: 10),
                Expanded(
                  child: Text('Xem trước: $title',
                      style: const TextStyle(
                          color: Colors.white, fontWeight: FontWeight.bold, fontSize: 15),
                      overflow: TextOverflow.ellipsis),
                ),
                IconButton(
                  icon: const Icon(Icons.close, color: Colors.white, size: 20),
                  onPressed: () => Navigator.pop(ctx),
                  padding: EdgeInsets.zero,
                  constraints: const BoxConstraints(),
                ),
              ]),
            ),
            // Không bọc IframeBlocker ở đây: iframe NÀY chính là nội dung của dialog
            // xem trước, nên không được tạm ẩn khi dialog mở (nếu bọc sẽ luôn hiện
            // placeholder "tạm ẩn"). Các màn khác vẫn giữ IframeBlocker như cũ.
            Expanded(child: HtmlElementView(viewType: viewKey)),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
              decoration: BoxDecoration(
                border: Border(top: BorderSide(color: Colors.grey.shade200)),
              ),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.end,
                children: [
                  OutlinedButton(
                    onPressed: () => Navigator.pop(ctx),
                    child: const Text('Đóng'),
                  ),
                ],
              ),
            ),
          ]),
        ),
      ),
    );
  }

  // ── Prefill from profile ───────────────────────────────────────────────────

  // Điền tự động từ hồ sơ (phương thức cũ, hiện không dùng).

  // ignore: unused_element
  Future<void> _doPrefill() async {
    // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

    setState(() => _prefilling = true);
    try {
      final vars = await _runTimedAiTask<Map<String, dynamic>>(
        flow: 'prefill-profile',
        action: (stopwatch) async {
          _logAiFlow('prefill-profile', 'request prepared', stopwatch, {
            'template_id': widget.templateId,
          });
          // Gọi API hoặc tác vụ bất đồng bộ rồi chờ kết quả trước khi cập nhật giao diện.

          final resp = await ApiClient().dio.get(
            'ai/doc/prefill-profile/',
            queryParameters: {'template_id': widget.templateId},
            options: _aiRequestOptions(),
          );
          final result = Map<String, dynamic>.from(resp.data['variables'] ?? {});
          _logAiFlow('prefill-profile', 'response received', stopwatch, {
            'field_count': result.length,
          });
          return result;
        },
      );
      final result = _applyPrefillVariables(vars);
      debugPrint('[prefill-profile] applied_fields=${result.applied} | skipped_fields=${result.skipped}');
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(
              result.applied > 0
                  ? 'Da dien ${result.applied} truong trong tu ho so.${result.skipped > 0 ? ' Bo qua ${result.skipped} truong ban da nhap san.' : ''}'
                  : (result.skipped > 0
                      ? 'Khong co truong trong de dien them. Cac truong phu hop da co du lieu san.'
                      : 'Khong tim thay thong tin phu hop tu ho so.'),
            ),
            backgroundColor: result.applied > 0 ? Colors.green : Colors.orange,
          ),
        );
      }
      return;
      vars.forEach((k, v) {
        if (_varCtrls.containsKey(k) && v.toString().isNotEmpty) {
          _varCtrls[k]!.text = v.toString();
        }
      });
      debugPrint('[prefill-profile] applied_fields=${vars.values.where((v) => v.toString().isNotEmpty).length}');
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(
            'Đã điền ${vars.values.where((v) => v.toString().isNotEmpty).length} trường từ hồ sơ.')),
      );
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Lỗi: $e')));
    } finally {
      // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

      if (mounted) setState(() => _prefilling = false);
    }
  }

  // ── Prefill from company context ──────────────────────────────────────────

  // Điền tự động từ ngữ cảnh công ty (phương thức cũ, hiện không dùng).

  // ignore: unused_element
  Future<void> _doPrefillCompany() async {
    // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

    setState(() => _prefillingCompany = true);
    try {
      final vars = await _runTimedAiTask<Map<String, dynamic>>(
        flow: 'prefill-company',
        action: (stopwatch) async {
          _logAiFlow('prefill-company', 'request prepared', stopwatch, {
            'template_id': widget.templateId,
          });
          // Gọi API hoặc tác vụ bất đồng bộ rồi chờ kết quả trước khi cập nhật giao diện.

          final resp = await ApiClient().dio.get(
            'ai/doc/prefill-company/',
            queryParameters: {'template_id': widget.templateId},
            options: _aiRequestOptions(),
          );
          final result = Map<String, dynamic>.from(resp.data['variables'] ?? {});
          _logAiFlow('prefill-company', 'response received', stopwatch, {
            'field_count': result.length,
          });
          return result;
        },
      );
      final result = _applyPrefillVariables(vars);
      debugPrint('[prefill-company] applied_fields=${result.applied} | skipped_fields=${result.skipped}');
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(
              result.applied > 0
                  ? 'Da dien ${result.applied} truong trong tu ngu canh cong ty.${result.skipped > 0 ? ' Bo qua ${result.skipped} truong ban da nhap san.' : ''}'
                  : (result.skipped > 0
                      ? 'Khong co truong trong de dien them. Cac truong phu hop da co du lieu san.'
                      : 'Khong tim thay thong tin phu hop tu ngu canh cong ty.'),
            ),
            backgroundColor: result.applied > 0 ? Colors.green : Colors.orange,
          ),
        );
      }
      return;
      int filled = 0;
      vars.forEach((k, v) {
        if (_varCtrls.containsKey(k) && v.toString().isNotEmpty) {
          _varCtrls[k]!.text = v.toString();
          filled++;
        }
      });
      debugPrint('[prefill-company] applied_fields=$filled');
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(filled > 0
              ? 'Đã điền $filled trường từ ngữ cảnh công ty.'
              : 'Không tìm thấy thông tin phù hợp từ ngữ cảnh công ty.'),
          backgroundColor: filled > 0 ? Colors.green : Colors.orange,
        ),
      );
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Lỗi: $e')));
    } finally {
      // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

      if (mounted) setState(() => _prefillingCompany = false);
    }
  }

  // ── PDF extraction ────────────────────────────────────────────────────────

  // Nút chọn file PDF nguồn để trích thông tin điền biến.
  Future<void> _pickPdf() async {
    final result = await FilePicker.platform.pickFiles(
      type: FileType.custom,
      allowedExtensions: ['pdf'],
      withData: true,
    );
    if (result != null && result.files.isNotEmpty) {
      // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

      setState(() => _pdfFile = result.files.first);
    }
  }

  // Trích thông tin từ PDF đã chọn (OCR/đọc text) -> điền vào các biến.
  Future<void> _extractFromPdf(dynamic tmpl) async {
    if (_pdfFile == null || _pdfFile!.bytes == null) return;
    // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

    setState(() => _extracting = true);
    try {
      final taskResult = await _runTimedAiTask<Map<String, dynamic>>(
        flow: 'extract-pdf',
        action: (stopwatch) async {
          _logAiFlow('extract-pdf', 'building multipart payload', stopwatch, {
            'template_id': widget.templateId,
            'file_name': _pdfFile!.name,
            'file_size_bytes': _pdfFile!.bytes!.length,
          });
          final formData = FormData.fromMap({
            'template_id': widget.templateId.toString(),
            'pdf_file': MultipartFile.fromBytes(_pdfFile!.bytes!, filename: _pdfFile!.name),
          });
          _logAiFlow('extract-pdf', 'sending request', stopwatch);
          // Gọi API hoặc tác vụ bất đồng bộ rồi chờ kết quả trước khi cập nhật giao diện.

          final result = await runAITask(
            context: context,
            endpoint: 'ai/doc/extract-pdf-async/',
            formPayload: formData,
            style: AITaskDialogStyle.linear,
            dialogTitle: 'Trích xuất từ PDF',
            dialogSubtitle: 'AI đang đọc PDF, OCR nếu cần, rồi điền vào các biến của mẫu.',
          );
          _logAiFlow('extract-pdf', 'response received', stopwatch, {
            'field_count': _taskVariables(result).length,
          });
          return result;
        },
      );
      final vars = _taskVariables(taskResult);
      int filled = 0;
      vars.forEach((k, v) {
        if (_varCtrls.containsKey(k) && v.toString().isNotEmpty) {
          _varCtrls[k]!.text = v.toString();
          filled++;
        }
      });
      debugPrint('[extract-pdf] applied_fields=$filled');
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(
        content: Text(filled > 0
            ? 'Đã trích xuất và điền $filled trường từ PDF.'
            : 'Không tìm thấy thông tin phù hợp trong PDF.'),
        backgroundColor: filled > 0 ? Colors.green : Colors.orange,
      ));
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Lỗi trích xuất PDF: $e'), backgroundColor: Colors.red));
    } finally {
      // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

      if (mounted) setState(() => _extracting = false);
    }
  }

  // ── Create document ───────────────────────────────────────────────────────

  // Mở lựa chọn nguồn ảnh (chụp camera / chọn từ máy) để trích thông tin.
  Future<void> _showImageSourcePicker() async {
    final source = await showModalBottomSheet<_ImagePickSource>(
      context: context,
      builder: (ctx) => SafeArea(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            if (_supportsDirectCameraCapture())
              ListTile(
                leading: const Icon(Icons.photo_camera_back_outlined),
                title: const Text('Trích xuất thông tin điền vào từ camera sau'),
                subtitle: const Text('Mở camera sau để chụp giấy tờ hoặc văn bản.'),
                onTap: () => Navigator.pop(ctx, _ImagePickSource.camera),
              )
            else
              ListTile(
                leading: const Icon(Icons.photo_camera_back_outlined),
                title: const Text('Camera không hỗ trợ trên thiết bị này'),
                subtitle: const Text('Desktop/web sẽ dùng chọn file ảnh thay cho camera.'),
                onTap: () => Navigator.pop(ctx, _ImagePickSource.library),
              ),
            ListTile(
              leading: const Icon(Icons.photo_library_outlined),
              title: const Text('Trích xuất thông tin điền vào từ thư viện'),
              subtitle: const Text('Chọn ảnh có sẵn trong thư viện để OCR.'),
              onTap: () => Navigator.pop(ctx, _ImagePickSource.library),
            ),
          ],
        ),
      ),
    );
    if (source != null) {
      await _pickImageFromSource(source);
    }
  }

  // Chọn ảnh từ nguồn (camera/thư viện) để trích thông tin điền biến.

  Future<void> _pickImageFromSource(_ImagePickSource source) async {
    if (source == _ImagePickSource.camera && !_supportsDirectCameraCapture()) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Trình duyệt này không mở được camera trực tiếp. Đã chuyển sang chọn file ảnh.'),
            backgroundColor: Colors.orange,
          ),
        );
      }
      source = _ImagePickSource.library;
    }

    if (source == _ImagePickSource.library) {
      final result = await FilePicker.platform.pickFiles(
        type: FileType.image,
        withData: true,
      );
      final file = result?.files.isNotEmpty == true ? result!.files.first : null;
      if (file == null || file.bytes == null) return;

      if (!mounted) return;
      // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

      setState(() {
        _ocrImageBytes = file.bytes!;
        _ocrImageName = file.name;
        _ocrImageSourceLabel = 'Thu vien anh';
      });
      return;
    }

    final input = html.FileUploadInputElement()..accept = 'image/*';
    if (source == _ImagePickSource.camera) {
      input.setAttribute('capture', 'environment');
    }

    final completer = Completer<void>();
    input.onChange.listen((_) {
      if (!completer.isCompleted) {
        completer.complete();
      }
    });
    input.click();
    await completer.future;

    final file = input.files?.isNotEmpty == true ? input.files!.first : null;
    if (file == null) return;

    final reader = html.FileReader();
    reader.readAsArrayBuffer(file);
    await reader.onLoad.first;

    final result = reader.result;
    Uint8List bytes;
    if (result is ByteBuffer) {
      bytes = Uint8List.view(result);
    } else if (result is Uint8List) {
      bytes = result;
    } else if (result is List<int>) {
      bytes = Uint8List.fromList(result);
    } else {
      throw Exception('Khong doc duoc du lieu anh.');
    }

    if (!mounted) return;
    // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

    setState(() {
      _ocrImageBytes = bytes;
      _ocrImageName = file.name;
      _ocrImageSourceLabel =
          source == _ImagePickSource.camera ? 'Camera sau' : 'Thu vien anh';
    });
  }

  // Xóa ảnh đang chọn (hủy trích từ ảnh).
  void _clearSelectedImage() {
    // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

    setState(() {
      _ocrImageBytes = null;
      _ocrImageName = null;
      _ocrImageSourceLabel = null;
    });
  }

  // Đoán chuỗi trả về có phải HTML (trang lỗi) thay vì dữ liệu hợp lệ không.
  bool _looksLikeHtmlPayload(String value) {
    final normalized = value.trimLeft().toLowerCase();
    return normalized.startsWith('<!doctype html') || normalized.startsWith('<html');
  }

  // Làm sạch thông báo lỗi trước khi hiển thị cho người dùng (bỏ HTML/kỹ thuật).
  String _sanitizeUiErrorMessage(String value, {required String fallback}) {
    final trimmed = value.trim();
    if (trimmed.isEmpty) return fallback;
    if (_looksLikeHtmlPayload(trimmed)) {
      return 'Dich vu OCR tra ve HTML khong hop le. Kiem tra log runserver/Ollama de debug.';
    }
    if (trimmed.length > 280) {
      return '${trimmed.substring(0, 280)}...';
    }
    return trimmed;
  }

  // Rút thông điệp lỗi gọn từ lỗi Dio để hiển thị.
  String _extractDioMessage(Object error, {required String fallback}) {
    if (error is DioException) {
      final data = error.response?.data;
      if (data is Map<String, dynamic>) {
        final detail = data['detail'];
        if (detail is String && detail.trim().isNotEmpty) {
          debugPrint('[extract-image] raw_error_detail=$detail');
          return _sanitizeUiErrorMessage(detail, fallback: fallback);
        }
      }
      if (data is String && data.trim().isNotEmpty) {
        debugPrint('[extract-image] raw_error_body=$data');
        return _sanitizeUiErrorMessage(data, fallback: fallback);
      }
    }
    return fallback;
  }

  // Rút thông điệp lỗi cụ thể cho thao tác sinh văn bản (prefill/extract/create).
  String _extractAiDocActionError(
    Object error, {
    required String fallback,
    required String serverFallback,
  }) {
    if (error is DioException) {
      final statusCode = error.response?.statusCode;
      if (statusCode == 404) {
        return 'Khong tim thay mau van ban hoac ban khong con quyen su dung.';
      }
      final detail = _extractDioMessage(error, fallback: '');
      if (detail.isNotEmpty) {
        return detail;
      }
      if (statusCode != null && statusCode >= 500) {
        return serverFallback;
      }
    }
    return fallback;
  }

  ({int applied, int skipped}) _applyPrefillVariables(Map<String, dynamic> vars) {
    var applied = 0;
    var skipped = 0;
    vars.forEach((key, value) {
      final controller = _varCtrls[key];
      final nextValue = value.toString().trim();
      if (controller == null || nextValue.isEmpty) {
        return;
      }
      if (controller.text.trim().isNotEmpty) {
        skipped += 1;
        return;
      }
      controller.text = nextValue;
      applied += 1;
    });
    return (applied: applied, skipped: skipped);
  }

  // Lấy map biến->giá trị từ kết quả tác vụ AI (để đổ vào controller).
  Map<String, dynamic> _taskVariables(Map<String, dynamic> result) {
    final raw = result['variables'];
    if (raw is Map) {
      return Map<String, dynamic>.from(raw);
    }
    return Map<String, dynamic>.from(result);
  }

  // Báo snackbar khi người dùng hủy tác vụ AI đang chạy.
  void _showTaskCancelledSnackBar(String message) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(message),
        backgroundColor: Colors.orange,
      ),
    );
  }

  // Thực thi điền từ hồ sơ qua AI task (có tiến độ/hủy).
  Future<void> _runProfilePrefill() async {
    setState(() => _prefilling = true);
    try {
      final taskResult = await _runTimedAiTask<Map<String, dynamic>>(
        flow: 'prefill-profile',
        action: (stopwatch) async {
          _logAiFlow('prefill-profile', 'request prepared', stopwatch, {
            'template_id': widget.templateId,
          });
          final result = await runAITask(
            context: context,
            endpoint: 'ai/doc/prefill-profile-async/',
            jsonPayload: {'template_id': widget.templateId},
            style: AITaskDialogStyle.linear,
            dialogTitle: 'Tự động điền từ hồ sơ',
            dialogSubtitle: 'AI đang đọc hồ sơ và điền vào các trường trống.',
          );
          _logAiFlow('prefill-profile', 'response received', stopwatch, {
            'field_count': _taskVariables(result).length,
          });
          return result;
        },
      );
      final vars = _taskVariables(taskResult);
      final result = _applyPrefillVariables(vars);
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            result.applied > 0
                ? 'Đã điền ${result.applied} trường trống từ hồ sơ.${result.skipped > 0 ? ' Bỏ qua ${result.skipped} trường bạn đã nhập sẵn.' : ''}'
                : (result.skipped > 0
                    ? 'Không có trường trống để điền thêm. Các trường phù hợp đã có dữ liệu sẵn.'
                    : 'Không tìm thấy thông tin phù hợp từ hồ sơ.'),
          ),
          backgroundColor: result.applied > 0 ? Colors.green : Colors.orange,
        ),
      );
    } on AITaskCancelledException {
      _showTaskCancelledSnackBar('Đã dừng tự động điền từ hồ sơ.');
    } catch (e) {
      final message = _extractAiDocActionError(
        e,
        fallback: 'Không thể tự động điền từ hồ sơ lúc này.',
        serverFallback: 'Không thể tự động điền từ hồ sơ lúc này. Vui lòng thử lại sau ít phút.',
      );
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(message), backgroundColor: Colors.red),
      );
    } finally {
      if (mounted) setState(() => _prefilling = false);
    }
  }

  // Thực thi điền từ ngữ cảnh công ty qua AI task (có tiến độ/hủy).
  Future<void> _runCompanyPrefill() async {
    setState(() => _prefillingCompany = true);
    try {
      final taskResult = await _runTimedAiTask<Map<String, dynamic>>(
        flow: 'prefill-company',
        action: (stopwatch) async {
          _logAiFlow('prefill-company', 'request prepared', stopwatch, {
            'template_id': widget.templateId,
          });
          final result = await runAITask(
            context: context,
            endpoint: 'ai/doc/prefill-company-async/',
            jsonPayload: {'template_id': widget.templateId},
            style: AITaskDialogStyle.linear,
            dialogTitle: 'Tự động điền từ công ty',
            dialogSubtitle: 'AI đang đọc ngữ cảnh công ty và điền vào biểu mẫu.',
          );
          _logAiFlow('prefill-company', 'response received', stopwatch, {
            'field_count': _taskVariables(result).length,
          });
          return result;
        },
      );
      final vars = _taskVariables(taskResult);
      final result = _applyPrefillVariables(vars);
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            result.applied > 0
                ? 'Da dien ${result.applied} truong trong tu ngu canh cong ty.${result.skipped > 0 ? ' Bo qua ${result.skipped} truong ban da nhap san.' : ''}'
                : (result.skipped > 0
                    ? 'Khong co truong trong de dien them. Cac truong phu hop da co du lieu san.'
                    : 'Khong tim thay thong tin phu hop tu ngu canh cong ty.'),
          ),
          backgroundColor: result.applied > 0 ? Colors.green : Colors.orange,
        ),
      );
    } on AITaskCancelledException {
      _showTaskCancelledSnackBar('Da dung tu dong dien tu ngu canh cong ty.');
    } catch (e) {
      final message = _extractAiDocActionError(
        e,
        fallback: 'Khong the tu dong dien tu ngu canh cong ty luc nay.',
        serverFallback: 'Khong the tu dong dien tu ngu canh cong ty luc nay. Vui long thu lai sau it phut.',
      );
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(message), backgroundColor: Colors.red),
      );
    } finally {
      if (mounted) setState(() => _prefillingCompany = false);
    }
  }

  // Trích thông tin từ ảnh đã chọn (OCR) -> điền vào các biến.
  Future<void> _extractFromImage(dynamic tmpl) async {
    if (_ocrImageBytes == null || _ocrImageName == null) return;
    // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

    setState(() => _extractingImage = true);
    try {
      final taskResult = await _runTimedAiTask<Map<String, dynamic>>(
        flow: 'extract-image',
        action: (stopwatch) async {
          _logAiFlow('extract-image', 'building multipart payload', stopwatch, {
            'template_id': widget.templateId,
            'file_name': _ocrImageName,
            'file_size_bytes': _ocrImageBytes!.length,
            'source': _ocrImageSourceLabel,
          });
          final formData = FormData.fromMap({
            'template_id': widget.templateId.toString(),
            'image_file': MultipartFile.fromBytes(
              _ocrImageBytes!,
              filename: _ocrImageName!,
            ),
          });
          _logAiFlow('extract-image', 'sending request', stopwatch);
          // Gọi API hoặc tác vụ bất đồng bộ rồi chờ kết quả trước khi cập nhật giao diện.

          final result = await runAITask(
            context: context,
            endpoint: 'ai/doc/extract-image-async/',
            formPayload: formData,
            style: AITaskDialogStyle.linear,
            dialogTitle: 'Trich xuat tu anh',
            dialogSubtitle: 'AI đang OCR ảnh và điền vào các biến của mẫu.',
          );
          _logAiFlow('extract-image', 'response received', stopwatch, {
            'field_count': _taskVariables(result).length,
          });
          return result;
        },
      );
      final vars = _taskVariables(taskResult);
      int filled = 0;
      vars.forEach((k, v) {
        if (_varCtrls.containsKey(k) && v.toString().isNotEmpty) {
          _varCtrls[k]!.text = v.toString();
          filled++;
        }
      });
      debugPrint('[extract-image] applied_fields=$filled');
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(
              filled > 0
                  ? 'Da trich xuat va dien $filled truong tu anh.'
                  : 'Khong tim thay thong tin phu hop trong anh.',
            ),
            backgroundColor: filled > 0 ? Colors.green : Colors.orange,
          ),
        );
      }
    } on AITaskCancelledException {
      _showTaskCancelledSnackBar('Da dung trich xuat anh.');
    } catch (e) {
      debugPrint('[extract-image] error=$e');
      final message = _extractDioMessage(
        e,
        fallback: 'Loi trich xuat anh: $e',
      );
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(message),
            backgroundColor: Colors.red,
          ),
        );
      }
    } finally {
      // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

      if (mounted) setState(() => _extractingImage = false);
    }
  }

  // Panel chọn ảnh + nút trích thông tin từ ảnh (OCR).

  Widget _buildImageExtractionPanel(dynamic tmpl, {required bool compact}) {
    final titleStyle = compact
        ? const TextStyle(fontSize: 13, fontWeight: FontWeight.w600)
        : const TextStyle(fontWeight: FontWeight.bold);
    final helperStyle = TextStyle(fontSize: 12, color: Colors.grey.shade600);
    final actionSpacing = compact ? 8.0 : 12.0;

    final content = Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'GLM OCR doc thong tin tren anh, sau do LLM xu ly va dien vao cac tham so cua mau van ban.',
          style: helperStyle,
        ),
        SizedBox(height: actionSpacing),
        if (_ocrImageName != null)
          Container(
            width: double.infinity,
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
            margin: EdgeInsets.only(bottom: actionSpacing),
            decoration: BoxDecoration(
              color: Colors.teal.shade50,
              borderRadius: BorderRadius.circular(6),
              border: Border.all(color: Colors.teal.shade200),
            ),
            child: Row(
              children: [
                const Icon(Icons.image_outlined, size: 15, color: Colors.teal),
                const SizedBox(width: 6),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        _ocrImageName!,
                        style: const TextStyle(fontSize: 12),
                        overflow: TextOverflow.ellipsis,
                      ),
                      if (_ocrImageSourceLabel != null)
                        Text(
                          _ocrImageSourceLabel!,
                          style: TextStyle(fontSize: 11, color: Colors.grey.shade600),
                        ),
                    ],
                  ),
                ),
                GestureDetector(
                  onTap: _clearSelectedImage,
                  child: const Icon(Icons.close, size: 14, color: Colors.teal),
                ),
              ],
            ),
          ),
        SizedBox(
          width: double.infinity,
          child: OutlinedButton.icon(
            onPressed: _extractingImage ? null : _showImageSourcePicker,
            icon: const Icon(Icons.add_a_photo_outlined, size: 16),
            label: Text(_ocrImageName == null ? 'Chon nguon anh' : 'Chon lai nguon anh'),
          ),
        ),
        if (_ocrImageName != null) ...[
          SizedBox(height: actionSpacing),
          SizedBox(
            width: double.infinity,
            child: FilledButton.icon(
              onPressed: _extractingImage ? null : () => _extractFromImage(tmpl),
              icon: _extractingImage
                  ? const SizedBox(
                      width: 16,
                      height: 16,
                      child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white),
                    )
                  : const Icon(Icons.document_scanner_outlined, size: 16),
              label: Text(
                _extractingImage ? 'Dang trich xuat...' : 'Trich xuat & Dien',
              ),
              style: FilledButton.styleFrom(backgroundColor: Colors.teal.shade600),
            ),
          ),
        ],
      ],
    );

    if (compact) {
      return Card(
        margin: EdgeInsets.zero,
        child: ExpansionTile(
          leading: const Icon(Icons.photo_camera_back_outlined, color: Colors.teal, size: 20),
          title: Text('Trich xuat tu Camera / Thu vien anh', style: titleStyle),
          tilePadding: const EdgeInsets.symmetric(horizontal: 12),
          childrenPadding: const EdgeInsets.fromLTRB(12, 0, 12, 12),
          children: [content],
        ),
      );
    }

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Icon(Icons.photo_camera_back_outlined, color: Colors.teal),
                const SizedBox(width: 8),
                Text('Trich xuat tu Camera / Thu vien anh', style: titleStyle),
              ],
            ),
            const SizedBox(height: 8),
            content,
          ],
        ),
      ),
    );
  }

  // Tải file DOCX của văn bản vừa tạo về máy.
  Future<void> _downloadDocx(int docId, String title) async {
    try {
      // Gọi API hoặc tác vụ bất đồng bộ rồi chờ kết quả trước khi cập nhật giao diện.

      final resp = await ApiClient().dio.get('documents/$docId/download/',
          options: Options(responseType: ResponseType.bytes));
      final bytes = resp.data as List<int>;
      final blob = html.Blob([bytes],
          'application/vnd.openxmlformats-officedocument.wordprocessingml.document');
      final url = html.Url.createObjectUrlFromBlob(blob);
      html.AnchorElement(href: url)
        ..setAttribute('download', '$title.docx')
        ..click();
      html.Url.revokeObjectUrl(url);
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Lỗi tải file: $e'), backgroundColor: Colors.red));
    }
  }

  // Nút TẠO VĂN BẢN: (kiểm prompt tùy chỉnh nếu có + kiểm định dạng biến/cảnh báo) rồi gọi tạo bất đồng bộ, xong mở /documents/<id>.
  Future<void> _createDoc(dynamic tmpl) async {
    if (_titleCtrl.text.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Vui lòng nhập tiêu đề.')));
      return;
    }
    // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

    setState(() => _saving = true);
    try {
      // Check title conflict
      final titleToCheck = _titleCtrl.text.trim();
      debugPrint('[create-ai-document] step=check-title-conflict | title=$titleToCheck');
      try {
        // Gọi API hoặc tác vụ bất đồng bộ rồi chờ kết quả trước khi cập nhật giao diện.

        final checkResp = await ApiClient().dio.get(
          'documents/check-title/',
          queryParameters: {'title': titleToCheck},
        );
        final match = checkResp.data['match'];
        debugPrint('[create-ai-document] step=check-title-conflict-done | has_match=${match != null}');
        if (match != null && mounted) {
          final matchId = match['id'] as int;
          final matchVer = match['version_number'] as int;
          final confirmed = await showDialog<String>(
            context: context,
            barrierDismissible: false,
            builder: (ctx) => AlertDialog(
              title: const Text('Trùng tên văn bản'),
              content: Text(
                'Đã tồn tại văn bản "$titleToCheck" (phiên bản $matchVer).\n\nBạn muốn làm gì?',
              ),
              actions: [
                TextButton(
                  onPressed: () => Navigator.pop(ctx, 'cancel'),
                  child: const Text('Hủy'),
                ),
                OutlinedButton(
                  onPressed: () => Navigator.pop(ctx, 'rename'),
                  child: const Text('Đổi tên VB'),
                ),
                FilledButton(
                  onPressed: () => Navigator.pop(ctx, 'update'),
                  child: const Text('Lưu phiên bản mới'),
                ),
              ],
            ),
          );
          if (confirmed == 'cancel' || confirmed == null) {
            // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

            if (mounted) setState(() => _saving = false);
            return;
          }
          if (confirmed == 'rename') {
            final renameCtrl = TextEditingController(text: titleToCheck);
            final newTitle = await showDialog<String>(
              context: context,
              builder: (ctx) => AlertDialog(
                title: const Text('Đổi tên văn bản'),
                content: TextField(
                  controller: renameCtrl,
                  autofocus: true,
                  decoration: const InputDecoration(labelText: 'Tên mới *'),
                ),
                actions: [
                  TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('Hủy')),
                  FilledButton(
                    onPressed: () {
                      if (renameCtrl.text.trim().isNotEmpty) {
                        Navigator.pop(ctx, renameCtrl.text.trim());
                      }
                    },
                    child: const Text('OK'),
                  ),
                ],
              ),
            );
            renameCtrl.dispose();
            if (newTitle == null || newTitle.isEmpty) {
              // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

              if (mounted) setState(() => _saving = false);
              return;
            }
            _titleCtrl.text = newTitle;
          } else if (confirmed == 'update') {
            _parentDocumentId = matchId;
          }
        }
      } catch (_) {}

      final vars = <String, String>{};
      _varCtrls.forEach((k, ctrl) => vars[k] = ctrl.text);
      debugPrint('[create-ai-document] step=collect-variables | variable_count=${vars.length}');
      final extraRules = _extraRulesCtrl.text.trim();
      if (extraRules.isNotEmpty && (_promptCheckToken ?? '').isEmpty) {
        await showBrowserAlert(
          context,
          'Hãy bấm "Check prompt" và sửa yêu cầu bổ sung nếu cần trước khi tạo văn bản.',
        );
        setState(() => _saving = false);
        return;
      }

      // Kiem tra dinh dang bien bang LLM (CHI canh bao, KHONG chan tao). Rieng
      // luong sinh van ban tu mau. LLM loi -> available=false: bao nhe roi tao tiep.
      bool acceptInvalidVariables = false;
      final varCheck = await checkVariableFormats(
        templateId: widget.templateId,
        variables: vars,
      );
      if (!mounted) return;
      if (varCheck.hasIssues) {
        final proceed = await showDialog<bool>(
          context: context,
          barrierDismissible: false,
          builder: (ctx) => AlertDialog(
            title: const Row(children: [
              Icon(Icons.warning_amber_rounded, color: Colors.orange, size: 26),
              SizedBox(width: 8),
              Expanded(child: Text('Một số biến có thể chưa hợp lệ')),
            ]),
            content: SingleChildScrollView(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text('AI nhận thấy các biến sau có thể chưa đúng với kiểu biến:'),
                  const SizedBox(height: 8),
                  ...varCheck.issues.map((issue) => Padding(
                        padding: const EdgeInsets.only(bottom: 8),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text('• ${issue.name}: "${issue.value}"',
                                style: const TextStyle(fontWeight: FontWeight.bold)),
                            if (issue.reason.isNotEmpty)
                              Padding(
                                padding: const EdgeInsets.only(left: 12),
                                child: Text(issue.reason),
                              ),
                          ],
                        ),
                      )),
                  const SizedBox(height: 4),
                  const Text('Bạn có chắc chắn bỏ qua và tiếp tục tạo văn bản?'),
                ],
              ),
            ),
            actions: [
              TextButton(
                onPressed: () => Navigator.pop(ctx, false),
                child: const Text('Sửa lại'),
              ),
              ElevatedButton(
                onPressed: () => Navigator.pop(ctx, true),
                child: const Text('Bỏ qua & tiếp tục'),
              ),
            ],
          ),
        );
        if (proceed != true) {
          setState(() => _saving = false);
          return;
        }
        acceptInvalidVariables = true;
      } else if (!varCheck.available && mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Không kiểm tra được định dạng biến, vẫn tạo bình thường.'),
          ),
        );
      }

      final result = await _runTimedAiTask<Map<String, dynamic>>(
        flow: 'create-ai-document',
        action: (stopwatch) async {
          _logAiFlow('create-ai-document', 'payload prepared', stopwatch, {
            'template_id': widget.templateId,
            'title': _titleCtrl.text.trim(),
            'variable_count': vars.length,
            'prompt_id': _selectedPromptId,
            'parent_document_id': _parentDocumentId,
          });
          _logAiFlow('create-ai-document', 'sending request', stopwatch);
          // Gọi API hoặc tác vụ bất đồng bộ rồi chờ kết quả trước khi cập nhật giao diện.

          final promptName = _promptNameCtrl.text.trim();
          final response = await runAITask(
            context: context,
            endpoint: 'ai/doc/create-async/',
            jsonPayload: {
              'template_id': widget.templateId,
              'variables': vars,
              'doc_title': _titleCtrl.text,
              if (acceptInvalidVariables) 'accept_invalid_variables': true,
              if (_selectedPromptId != null) 'prompt_id': _selectedPromptId,
              if (_parentDocumentId != null) 'parent_document_id': _parentDocumentId,
              if (extraRules.isNotEmpty) 'user_extra_rules': extraRules,
              if (extraRules.isNotEmpty && _promptCheckToken != null)
                'prompt_check_token': _promptCheckToken,
              if (extraRules.isNotEmpty && _previewToken != null) 'preview_token': _previewToken,
              if (extraRules.isNotEmpty && _saveAsPrompt && promptName.isNotEmpty)
                'save_as_prompt_title': promptName,
            },
            style: AITaskDialogStyle.linear,
            dialogTitle: 'Tạo văn bản AI',
            dialogSubtitle: 'AI đang điền biến, render DOCX và lưu văn bản mới.',
          );
          _logAiFlow('create-ai-document', 'response received', stopwatch, {
            'document_id': response['document_id'],
            'has_file': response['has_file'],
          });
          return response;
        },
      );
      final docId = result['document_id'] as int;
      final hasFile = result['has_file'] == true;
      debugPrint('[create-ai-document] result | document_id=$docId | has_file=$hasFile');
      _parentDocumentId = null;
      _previewToken = null;
      _promptCheckToken = null;
      if (!mounted) return;
      refreshDocumentCollections(ref);
      ref.invalidate(recentPromptsProvider);
      await showDialog(
        context: context,
        barrierDismissible: false,
        builder: (ctx) => AlertDialog(
          title: const Row(children: [
            Icon(Icons.check_circle, color: Colors.green, size: 28),
            SizedBox(width: 10),
            Text('Tạo văn bản thành công!'),
          ]),
          content: const Text('Văn bản đã được tạo. Bạn có thể xem trước hoặc tải file Word.'),
          actions: [
            // Chỉ còn 2 lựa chọn: Xem trước (mở chi tiết kèm preview) và Tải file Word.
            OutlinedButton.icon(
              onPressed: () { Navigator.pop(ctx); context.go('/documents/$docId'); },
              icon: const Icon(Icons.visibility, size: 16),
              label: const Text('Xem trước'),
            ),
            if (hasFile)
              FilledButton.icon(
                onPressed: () => _downloadDocx(docId, _titleCtrl.text),
                icon: const Icon(Icons.description, size: 16),
                label: const Text('Tải file Word'),
              ),
          ],
        ),
      );
    } on AITaskCancelledException {
      _showTaskCancelledSnackBar('Da dung tao van ban.');
    } on DioException catch (e) {
      if (!mounted) return;
      final data = e.response?.data;
      String msg = 'Loi: ${e.message}';
      String? incidentId;
      if (data is Map) {
        msg = (data['detail'] ?? msg).toString();
        incidentId = data['incident_id']?.toString();
      }
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(
        backgroundColor: incidentId != null ? Colors.red : null,
        content: Row(
          children: [
            Expanded(child: Text(incidentId != null ? '$msg (su co: $incidentId)' : msg)),
            if (incidentId != null)
              TextButton(
                onPressed: () => html.window.navigator.clipboard?.writeText(incidentId!),
                child: const Text('Sao chep ID', style: TextStyle(color: Colors.white)),
              ),
          ],
        ),
      ));
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Lỗi: $e')));
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  // Xem trước prompt cuối cùng sẽ gửi cho AI (gồm rule tùy chỉnh).
  Future<void> _openPromptPreview(dynamic tmpl) async {
    final rules = _extraRulesCtrl.text.trim();
    final name = _promptNameCtrl.text.trim();
    if (_saveAsPrompt && rules.isNotEmpty && name.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(
        content: Text('Vui lòng đặt tên cho prompt trước khi lưu lại.'),
      ));
      return;
    }
    final vars = <String, dynamic>{};
    for (final entry in _varCtrls.entries) {
      vars[entry.key] = entry.value.text;
    }
    final result = await showDialog<PromptPreviewResult?>(
      context: context,
      builder: (_) => PromptPreviewDialog(
        templateId: widget.templateId,
        variables: vars,
        userExtraRules: _extraRulesCtrl.text.trim(),
        promptId: _selectedPromptId,
      ),
    );
    if (result != null) {
      setState(() => _previewToken = result.previewToken);
      if (mounted) await _createDoc(tmpl);
    }
  }

  // Chọn 1 prompt đã lưu để áp vào ô prompt tùy chỉnh.
  Future<void> _pickSavedPrompt() async {
    final prompt = await PromptPickerDialog.show(
      context,
      scope: 'template_fill',
    );
    if (prompt == null) return;
    setState(() {
      _selectedPromptId = prompt.id.toString();
      _promptNameCtrl.text = prompt.title;
      _previewToken = null;
    });
  }

  // Lưu prompt tùy chỉnh hiện tại để tái dùng lần sau.
  Future<void> _saveCurrentPrompt() async {
    final rules = _extraRulesCtrl.text.trim();
    if (rules.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Vui lòng nhập yêu cầu bổ sung trước khi lưu prompt.')),
      );
      return;
    }

    final prompt = await SavePromptDialog.show(
      context,
      initialTitle: _promptNameCtrl.text.trim().isNotEmpty
          ? _promptNameCtrl.text.trim()
          : 'Prompt tu ${_titleCtrl.text.trim().isNotEmpty ? _titleCtrl.text.trim() : 'mau hien tai'}',
      systemContent: '',
      rulesContent: rules,
      defaultScopes: const ['template_fill'],
    );
    if (prompt == null || !mounted) return;

    ref.invalidate(promptsProvider);
    ref.invalidate(recentPromptsProvider);
    setState(() {
      _selectedPromptId = prompt.id.toString();
      _promptNameCtrl.text = prompt.title;
      _previewToken = null;
    });
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text('Đã lưu prompt "${prompt.title}".')),
    );
  }

  // Hủy hiệu lực token đã kiểm prompt khi prompt tùy chỉnh bị sửa (bắt kiểm lại).
  void _invalidateExtraPromptChecks() {
    _previewToken = null;
    _promptCheckToken = null;
  }

  // Nút 'Kiểm tra prompt': chạy kiểm an toàn prompt tùy chỉnh, lấy prompt_check_token/preview_token.
  Future<void> _checkExtraRulesPrompt() async {
    final rules = _extraRulesCtrl.text.trim();
    if (rules.isEmpty) {
      await showBrowserAlert(context, 'Vui lòng nhập yêu cầu bổ sung trước khi kiểm tra prompt.');
      return;
    }
    setState(() {
      _checkingPrompt = true;
      _promptCheckToken = null;
    });
    final result = await checkPromptPreflight(
      scope: 'template_fill',
      context: 'ai_doc_fill',
      promptRole: 'extra_instruction',
      promptText: rules,
      targetId: widget.templateId,
    );
    if (!mounted) return;
    if (_extraRulesCtrl.text.trim() != rules) {
      setState(() {
        _checkingPrompt = false;
        _promptCheckToken = null;
      });
      return;
    }
    setState(() {
      _checkingPrompt = false;
      _promptCheckToken = result.promptCheckToken;
    });
    if (!result.passed) {
      await showBrowserAlert(context, promptPreflightFailureMessage(result));
    }
  }

  Widget _buildExtraRulesBlock(dynamic tmpl) {
    return _buildExtraRulesInnerCard(tmpl);
  }

  Widget _buildExtraRulesInnerCard(dynamic tmpl) {
    return Card(
      margin: const EdgeInsets.symmetric(vertical: 8),
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Row(
              children: [
                Icon(Icons.tune, size: 18, color: Colors.blue),
                SizedBox(width: 8),
                Text('Tùy chỉnh prompt và kiểm tra trước khi tạo',
                    style: TextStyle(fontWeight: FontWeight.bold)),
              ],
            ),
            const SizedBox(height: 8),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: [
                OutlinedButton.icon(
                  onPressed: _saving ? null : _pickSavedPrompt,
                  icon: const Icon(Icons.folder_open, size: 16),
                  label: const Text('Chọn prompt đã lưu'),
                ),
                OutlinedButton.icon(
                  onPressed: _saving ? null : _saveCurrentPrompt,
                  icon: const Icon(Icons.save_outlined, size: 16),
                  label: const Text('Lưu thành prompt mới'),
                ),
                if (_selectedPromptId != null)
                  TextButton.icon(
                    onPressed: _saving
                        ? null
                        : () {
                            setState(() {
                              _selectedPromptId = null;
                              _promptNameCtrl.clear();
                              _invalidateExtraPromptChecks();
                            });
                          },
                    icon: const Icon(Icons.close, size: 16),
                    label: const Text('Bỏ prompt đã chọn'),
                  ),
              ],
            ),
            if (_selectedPromptId != null) ...[
              const SizedBox(height: 8),
              Container(
                width: double.infinity,
                padding: const EdgeInsets.all(10),
                decoration: BoxDecoration(
                  color: Colors.blue.shade50,
                  border: Border.all(color: Colors.blue.shade100),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Text(
                  'Đang dùng prompt: ${_promptNameCtrl.text.trim().isEmpty ? '#$_selectedPromptId' : _promptNameCtrl.text.trim()}',
                  style: const TextStyle(fontWeight: FontWeight.w600),
                ),
              ),
            ],
            const SizedBox(height: 8),
            _RecentPromptPicker(
              onSelected: (p) {
                setState(() {
                  _invalidateExtraPromptChecks();
                  if (p != null) {
                    _extraRulesCtrl.text =
                        p.rulesContent.isNotEmpty ? p.rulesContent : p.rulesContentPreview;
                    if (_promptNameCtrl.text.trim().isEmpty) {
                      _promptNameCtrl.text = p.title;
                    }
                  }
                });
              },
            ),
            TextField(
              controller: _extraRulesCtrl,
              maxLines: 5,
              maxLength: 2000,
              decoration: const InputDecoration(
                labelText: 'Mô tả phong cách / yêu cầu',
                helperText: 'Ví dụ: "Giữ văn phong trang trọng, viết hoa tên người nhận"',
                border: OutlineInputBorder(),
              ),
              onChanged: (_) {
                setState(() {
                  _invalidateExtraPromptChecks();
                  if (_extraRulesCtrl.text.trim().isEmpty && _saveAsPrompt) {
                    _saveAsPrompt = false;
                    _promptNameCtrl.clear();
                  }
                });
              },
            ),
            OutlinedButton.icon(
              onPressed: _saving || _checkingPrompt || _extraRulesCtrl.text.trim().isEmpty
                  ? null
                  : _checkExtraRulesPrompt,
              icon: _checkingPrompt
                  ? const SizedBox(
                      width: 14,
                      height: 14,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    )
                  : Icon(
                      (_promptCheckToken ?? '').isEmpty
                          ? Icons.fact_check_outlined
                          : Icons.verified_user_outlined,
                      size: 16,
                    ),
              label: Text(
                _checkingPrompt
                    ? 'Đang kiểm tra...'
                    : (_promptCheckToken ?? '').isEmpty
                        ? 'Check prompt'
                        : 'Prompt đạt yêu cầu',
              ),
            ),
            const SizedBox(height: 8),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
              decoration: BoxDecoration(
                color: _saveAsPrompt ? Colors.blue.shade50 : Colors.grey.shade50,
                border: Border.all(
                    color: _saveAsPrompt ? Colors.blue.shade200 : Colors.grey.shade300),
                borderRadius: BorderRadius.circular(6),
              ),
              child: Column(
                children: [
                  SwitchListTile.adaptive(
                    contentPadding: EdgeInsets.zero,
                    dense: true,
                    title: const Text(
                      'Lưu prompt này để dùng lại sau',
                      style: TextStyle(fontWeight: FontWeight.w600, fontSize: 13),
                    ),
                    subtitle: const Text(
                      'Mặc định không lưu. Bật để lưu vào "Prompt riêng tư" — sau đó có thể vào Quản lý Prompt để chia sẻ cho nhóm hoặc tất cả.',
                      style: TextStyle(fontSize: 11),
                    ),
                    value: _saveAsPrompt,
                    onChanged: _extraRulesCtrl.text.trim().isEmpty
                        ? null
                        : (v) {
                            setState(() {
                              _saveAsPrompt = v;
                              if (!v) _promptNameCtrl.clear();
                              _invalidateExtraPromptChecks();
                            });
                          },
                  ),
                  if (_saveAsPrompt) ...[
                    const SizedBox(height: 4),
                    TextField(
                      controller: _promptNameCtrl,
                      maxLength: 120,
                      decoration: const InputDecoration(
                        labelText: 'Tên prompt *',
                        helperText: 'Bắt buộc khi lưu. Không trùng với prompt khác của bạn.',
                        border: OutlineInputBorder(),
                        prefixIcon: Icon(Icons.label_outline, size: 18),
                        isDense: true,
                      ),
                      onChanged: (_) {
                        if (_previewToken != null) {
                          setState(() => _previewToken = null);
                        }
                      },
                    ),
                    const SizedBox(height: 8),
                  ],
                ],
              ),
            ),
            const SizedBox(height: 8),
            Row(
              children: [
                ElevatedButton.icon(
                  icon: const Icon(Icons.preview, size: 16),
                  label: const Text('Xem prompt cuối & Tạo văn bản'),
                  onPressed: _saving ||
                          (_extraRulesCtrl.text.trim().isNotEmpty &&
                              (_promptCheckToken ?? '').isEmpty)
                      ? null
                      : () => _openPromptPreview(tmpl),
                ),
                const SizedBox(width: 8),
                if (_extraRulesCtrl.text.trim().isEmpty)
                  const Text(
                    '(Để trống nếu không cần bổ sung)',
                    style: TextStyle(fontSize: 11, color: Colors.grey),
                  ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  @override
  // Rời màn: giải phóng các controller biến + tài nguyên.
  void dispose() {
    _titleCtrl.dispose();
    _extraRulesCtrl.dispose();
    _promptNameCtrl.dispose();
    for (final c in _varCtrls.values) c.dispose();
    super.dispose();
  }
}


class _RecentPromptPicker extends ConsumerStatefulWidget {
  final void Function(RecentPromptItem?) onSelected;
  const _RecentPromptPicker({required this.onSelected});

  @override
  ConsumerState<_RecentPromptPicker> createState() => _RecentPromptPickerState();
}

class _RecentPromptPickerState extends ConsumerState<_RecentPromptPicker> {
  final _searchCtrl = TextEditingController();
  int? _selectedId;
  String _visibilityFilter = 'all';
  String _ownerFilter = 'all';
  String _sortMode = 'usage';
  String? _selectedTag;
  bool _expanded = true;

  @override
  void dispose() {
    _searchCtrl.dispose();
    super.dispose();
  }

  // Định dạng mốc thời gian của prompt đã lưu để hiển thị.
  String _formatTime(String? iso) {
    if (iso == null || iso.isEmpty) return '';
    try {
      final dt = DateTime.parse(iso).toLocal();
      final d = dt.day.toString().padLeft(2, '0');
      final m = dt.month.toString().padLeft(2, '0');
      final h = dt.hour.toString().padLeft(2, '0');
      final mi = dt.minute.toString().padLeft(2, '0');
      return '$d/$m/${dt.year} $h:$mi';
    } catch (_) {
      return iso;
    }
  }

  // Màu badge theo phạm vi hiển thị của prompt (riêng tư/nhóm/công khai).
  Color _visibilityColor(String v) {
    switch (v) {
      case 'public':
        return Colors.green;
      case 'group':
        return Colors.blue;
      default:
        return Colors.grey;
    }
  }

  // Nhãn phạm vi hiển thị của prompt đã lưu.
  String _visibilityLabel(String v) {
    switch (v) {
      case 'public':
        return 'Công khai';
      case 'group':
        return 'Phòng ban';
      default:
        return 'Riêng tư';
    }
  }

  // Lọc danh sách prompt đã lưu theo tìm kiếm/tag/phạm vi.
  List<RecentPromptItem> _applyFilters(List<RecentPromptItem> list) {
    final q = _searchCtrl.text.trim().toLowerCase();
    final filtered = list.where((p) {
      if (_visibilityFilter != 'all' && p.visibility != _visibilityFilter) return false;
      if (_ownerFilter == 'mine' && !p.isMine) return false;
      if (_ownerFilter == 'others' && p.isMine) return false;
      if (_selectedTag != null && _selectedTag!.isNotEmpty) {
        if (!p.tagList.any((t) => t.toLowerCase() == _selectedTag!.toLowerCase())) return false;
      }
      if (q.isNotEmpty && !p.matchHaystack().contains(q)) return false;
      return true;
    }).toList();

    switch (_sortMode) {
      case 'recent':
        filtered.sort((a, b) => (b.lastUsed ?? '').compareTo(a.lastUsed ?? ''));
        break;
      case 'alphabet':
        filtered.sort((a, b) => a.title.toLowerCase().compareTo(b.title.toLowerCase()));
        break;
      case 'newest':
        filtered.sort((a, b) => (b.createdAt ?? '').compareTo(a.createdAt ?? ''));
        break;
      case 'usage':
      default:
        filtered.sort((a, b) => b.usageCount.compareTo(a.usageCount));
        break;
    }
    return filtered;
  }

  // Gom tập tag từ danh sách prompt (cho bộ lọc tag).
  List<String> _collectTags(List<RecentPromptItem> list) {
    final set = <String>{};
    for (final p in list) {
      for (final t in p.tagList) {
        if (t.isNotEmpty) set.add(t);
      }
    }
    final tags = set.toList()..sort();
    return tags;
  }

  // Đang có bộ lọc prompt nào được bật không (để hiện nút xóa lọc).
  bool _hasActiveFilter() =>
      _searchCtrl.text.trim().isNotEmpty ||
      _visibilityFilter != 'all' ||
      _ownerFilter != 'all' ||
      _selectedTag != null;

  // Xóa toàn bộ bộ lọc prompt đã lưu.
  void _resetFilters() {
    setState(() {
      _searchCtrl.clear();
      _visibilityFilter = 'all';
      _ownerFilter = 'all';
      _selectedTag = null;
      _sortMode = 'usage';
    });
  }

  // Dựng thanh lọc cho danh sách prompt đã lưu (tìm/tag/phạm vi).
  Widget _buildFilterBar(List<RecentPromptItem> allList, int filteredCount) {
    final tags = _collectTags(allList);
    return Padding(
      padding: const EdgeInsets.fromLTRB(10, 0, 10, 6),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          TextField(
            controller: _searchCtrl,
            decoration: InputDecoration(
              isDense: true,
              hintText: 'Tìm theo tên, nội dung, người dùng, văn bản...',
              prefixIcon: const Icon(Icons.search, size: 16),
              suffixIcon: _searchCtrl.text.isEmpty
                  ? null
                  : IconButton(
                      icon: const Icon(Icons.clear, size: 14),
                      onPressed: () => setState(() => _searchCtrl.clear()),
                    ),
              contentPadding: const EdgeInsets.symmetric(horizontal: 8, vertical: 8),
              border: const OutlineInputBorder(),
            ),
            style: const TextStyle(fontSize: 12),
            onChanged: (_) => setState(() {}),
          ),
          const SizedBox(height: 6),
          Row(children: [
            Expanded(
              child: DropdownButtonFormField<String>(
                value: _visibilityFilter,
                isDense: true,
                decoration: const InputDecoration(
                  labelText: 'Phạm vi',
                  border: OutlineInputBorder(),
                  isDense: true,
                  contentPadding: EdgeInsets.symmetric(horizontal: 8, vertical: 6),
                ),
                style: const TextStyle(fontSize: 12, color: Colors.black87),
                items: const [
                  DropdownMenuItem(value: 'all', child: Text('Tất cả', style: TextStyle(fontSize: 12))),
                  DropdownMenuItem(value: 'private', child: Text('Riêng tư', style: TextStyle(fontSize: 12))),
                  DropdownMenuItem(value: 'group', child: Text('Phòng ban', style: TextStyle(fontSize: 12))),
                  DropdownMenuItem(value: 'public', child: Text('Công khai', style: TextStyle(fontSize: 12))),
                ],
                onChanged: (v) => setState(() => _visibilityFilter = v ?? 'all'),
              ),
            ),
            const SizedBox(width: 6),
            Expanded(
              child: DropdownButtonFormField<String>(
                value: _ownerFilter,
                isDense: true,
                decoration: const InputDecoration(
                  labelText: 'Chủ sở hữu',
                  border: OutlineInputBorder(),
                  isDense: true,
                  contentPadding: EdgeInsets.symmetric(horizontal: 8, vertical: 6),
                ),
                style: const TextStyle(fontSize: 12, color: Colors.black87),
                items: const [
                  DropdownMenuItem(value: 'all', child: Text('Tất cả', style: TextStyle(fontSize: 12))),
                  DropdownMenuItem(value: 'mine', child: Text('Của tôi', style: TextStyle(fontSize: 12))),
                  DropdownMenuItem(value: 'others', child: Text('Người khác', style: TextStyle(fontSize: 12))),
                ],
                onChanged: (v) => setState(() => _ownerFilter = v ?? 'all'),
              ),
            ),
            const SizedBox(width: 6),
            Expanded(
              child: DropdownButtonFormField<String>(
                value: _sortMode,
                isDense: true,
                decoration: const InputDecoration(
                  labelText: 'Sắp xếp',
                  border: OutlineInputBorder(),
                  isDense: true,
                  contentPadding: EdgeInsets.symmetric(horizontal: 8, vertical: 6),
                ),
                style: const TextStyle(fontSize: 12, color: Colors.black87),
                items: const [
                  DropdownMenuItem(value: 'usage', child: Text('Dùng nhiều nhất', style: TextStyle(fontSize: 12))),
                  DropdownMenuItem(value: 'recent', child: Text('Mới dùng', style: TextStyle(fontSize: 12))),
                  DropdownMenuItem(value: 'newest', child: Text('Mới tạo', style: TextStyle(fontSize: 12))),
                  DropdownMenuItem(value: 'alphabet', child: Text('A → Z', style: TextStyle(fontSize: 12))),
                ],
                onChanged: (v) => setState(() => _sortMode = v ?? 'usage'),
              ),
            ),
          ]),
          if (tags.isNotEmpty) ...[
            const SizedBox(height: 6),
            SingleChildScrollView(
              scrollDirection: Axis.horizontal,
              child: Row(children: [
                const Padding(
                  padding: EdgeInsets.only(right: 6),
                  child: Text('Tag:', style: TextStyle(fontSize: 11, color: Colors.grey)),
                ),
                ChoiceChip(
                  label: const Text('Tất cả', style: TextStyle(fontSize: 11)),
                  selected: _selectedTag == null,
                  visualDensity: VisualDensity.compact,
                  onSelected: (_) => setState(() => _selectedTag = null),
                ),
                const SizedBox(width: 4),
                ...tags.map((t) => Padding(
                      padding: const EdgeInsets.only(right: 4),
                      child: ChoiceChip(
                        label: Text(t, style: const TextStyle(fontSize: 11)),
                        selected: _selectedTag == t,
                        visualDensity: VisualDensity.compact,
                        onSelected: (sel) => setState(() => _selectedTag = sel ? t : null),
                      ),
                    )),
              ]),
            ),
          ],
          const SizedBox(height: 4),
          Row(children: [
            Text(
              'Hiển thị $filteredCount / ${allList.length} prompt',
              style: const TextStyle(fontSize: 11, color: Colors.grey),
            ),
            const Spacer(),
            if (_hasActiveFilter())
              TextButton.icon(
                onPressed: _resetFilters,
                icon: const Icon(Icons.filter_alt_off, size: 14),
                label: const Text('Xóa bộ lọc', style: TextStyle(fontSize: 11)),
                style: TextButton.styleFrom(
                  padding: const EdgeInsets.symmetric(horizontal: 6),
                  minimumSize: const Size(0, 28),
                ),
              ),
          ]),
        ],
      ),
    );
  }

  // Dựng 1 dòng prompt đã lưu trong danh sách chọn.
  Widget _buildPromptItem(RecentPromptItem p) {
    final selected = p.id == _selectedId;
    return InkWell(
      onTap: () {
        setState(() => _selectedId = p.id);
        widget.onSelected(p);
      },
      child: Container(
        color: selected ? Colors.blue.shade50 : null,
        padding: const EdgeInsets.fromLTRB(10, 8, 10, 8),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(children: [
              Expanded(
                child: Text(
                  p.title,
                  style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 13),
                  overflow: TextOverflow.ellipsis,
                ),
              ),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                decoration: BoxDecoration(
                  color: _visibilityColor(p.visibility).withOpacity(0.15),
                  borderRadius: BorderRadius.circular(4),
                ),
                child: Text(
                  _visibilityLabel(p.visibility),
                  style: TextStyle(
                    fontSize: 10,
                    color: _visibilityColor(p.visibility),
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ),
            ]),
            const SizedBox(height: 2),
            Text(
              p.rulesContentPreview,
              style: const TextStyle(fontSize: 11, color: Colors.black87),
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
            ),
            if (p.tagList.isNotEmpty) ...[
              const SizedBox(height: 4),
              Wrap(
                spacing: 4,
                runSpacing: 2,
                children: p.tagList
                    .take(5)
                    .map((t) => Container(
                          padding: const EdgeInsets.symmetric(horizontal: 5, vertical: 1),
                          decoration: BoxDecoration(
                            color: Colors.indigo.shade50,
                            borderRadius: BorderRadius.circular(3),
                          ),
                          child: Text('#$t',
                              style: TextStyle(fontSize: 9.5, color: Colors.indigo.shade700)),
                        ))
                    .toList(),
              ),
            ],
            const SizedBox(height: 3),
            DefaultTextStyle(
              style: const TextStyle(fontSize: 10.5, color: Colors.grey),
              child: Wrap(
                spacing: 10,
                runSpacing: 2,
                children: [
                  Row(mainAxisSize: MainAxisSize.min, children: [
                    const Icon(Icons.repeat, size: 11, color: Colors.grey),
                    const SizedBox(width: 2),
                    Text('Dùng ${p.usageCount} lần'),
                  ]),
                  if (p.lastUsed != null)
                    Row(mainAxisSize: MainAxisSize.min, children: [
                      const Icon(Icons.access_time, size: 11, color: Colors.grey),
                      const SizedBox(width: 2),
                      Text('Lần cuối: ${_formatTime(p.lastUsed)}'),
                    ]),
                  if (p.lastUsedDocTitle != null && p.lastUsedDocTitle!.isNotEmpty)
                    Row(mainAxisSize: MainAxisSize.min, children: [
                      const Icon(Icons.description_outlined, size: 11, color: Colors.grey),
                      const SizedBox(width: 2),
                      ConstrainedBox(
                        constraints: const BoxConstraints(maxWidth: 200),
                        child: Text(
                          'Tại: ${p.lastUsedDocTitle}',
                          overflow: TextOverflow.ellipsis,
                        ),
                      ),
                    ]),
                  Row(mainAxisSize: MainAxisSize.min, children: [
                    Icon(p.isMine ? Icons.person : Icons.group, size: 11, color: Colors.grey),
                    const SizedBox(width: 2),
                    Text(p.isMine ? 'Của bạn' : 'Bởi: ${p.ownerName}'),
                  ]),
                  if (p.categoryName != null && p.categoryName!.isNotEmpty)
                    Row(mainAxisSize: MainAxisSize.min, children: [
                      const Icon(Icons.category_outlined, size: 11, color: Colors.grey),
                      const SizedBox(width: 2),
                      Text(p.categoryName!),
                    ]),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final asyncList = ref.watch(recentPromptsProvider);

    return Container(
      margin: const EdgeInsets.only(bottom: 10),
      decoration: BoxDecoration(
        border: Border.all(color: Colors.grey.shade300),
        borderRadius: BorderRadius.circular(6),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          InkWell(
            onTap: () => setState(() => _expanded = !_expanded),
            child: Padding(
              padding: const EdgeInsets.fromLTRB(10, 8, 6, 8),
              child: Row(children: [
                const Icon(Icons.history, size: 16, color: Colors.blueGrey),
                const SizedBox(width: 6),
                const Expanded(
                  child: Text('Tái dùng prompt đã có',
                      style: TextStyle(fontWeight: FontWeight.bold, fontSize: 13)),
                ),
                IconButton(
                  icon: const Icon(Icons.refresh, size: 16),
                  visualDensity: VisualDensity.compact,
                  tooltip: 'Tải lại',
                  onPressed: () => ref.invalidate(recentPromptsProvider),
                ),
                Icon(_expanded ? Icons.expand_less : Icons.expand_more, size: 18),
              ]),
            ),
          ),
          if (_expanded)
            asyncList.when(
              data: (list) {
                final filtered = _applyFilters(list);
                return Column(children: [
                  _buildFilterBar(list, filtered.length),
                  if (list.isEmpty)
                    const Padding(
                      padding: EdgeInsets.fromLTRB(10, 4, 10, 12),
                      child: Text(
                        'Chưa có prompt nào. Tạo prompt mới bằng cách nhập "Tên prompt" và "Yêu cầu bổ sung" bên dưới.',
                        style: TextStyle(fontSize: 11, color: Colors.grey),
                      ),
                    )
                  else if (filtered.isEmpty)
                    const Padding(
                      padding: EdgeInsets.fromLTRB(10, 4, 10, 12),
                      child: Text(
                        'Không có prompt nào khớp bộ lọc. Thử xóa bộ lọc.',
                        style: TextStyle(fontSize: 11, color: Colors.grey),
                      ),
                    )
                  else
                    ConstrainedBox(
                      constraints: const BoxConstraints(minHeight: 380, maxHeight: 520),
                      child: Scrollbar(
                        thumbVisibility: true,
                        child: ListView.separated(
                          shrinkWrap: true,
                          itemCount: filtered.length,
                          separatorBuilder: (_, __) => const Divider(height: 1),
                          itemBuilder: (_, i) => _buildPromptItem(filtered[i]),
                        ),
                      ),
                    ),
                  if (_selectedId != null)
                    Padding(
                      padding: const EdgeInsets.fromLTRB(10, 0, 10, 6),
                      child: TextButton.icon(
                        icon: const Icon(Icons.clear, size: 14),
                        label: const Text('Bỏ chọn', style: TextStyle(fontSize: 11)),
                        style: TextButton.styleFrom(
                            padding: const EdgeInsets.symmetric(horizontal: 6),
                            minimumSize: const Size(0, 28)),
                        onPressed: () {
                          setState(() => _selectedId = null);
                          widget.onSelected(null);
                        },
                      ),
                    ),
                ]);
              },
              loading: () => const Padding(
                padding: EdgeInsets.all(10),
                child: LinearProgressIndicator(),
              ),
              error: (e, _) => Padding(
                padding: const EdgeInsets.all(10),
                child: Text('Không tải được: $e',
                    style: const TextStyle(fontSize: 11, color: Colors.red)),
              ),
            ),
        ],
      ),
    );
  }
}
