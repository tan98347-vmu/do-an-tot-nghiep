// r2/M4 — Screen "Kiem tra van ban theo quy trinh".
//
// Route: /compliance-check
// 3 buoc:
//   1. Chon nguon (Document / Template) + chon item.
//   2. Chon prompt scope=compliance_check qua PromptPickerDialog (r1).
//   3. Bam "Kiem tra" -> goi /api/compliance-check/run/.
//
// Khi pass -> banner xanh + text CHINH XAC theo yeu cau goc.
// Khi fail -> danh sach item missing.

import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/api_client.dart';
import '../../models/compliance_result.dart';
import '../../providers/compliance_provider.dart';
import '../../providers/prompts_provider.dart';
import '../../widgets/ai/prompt_picker_dialog.dart';
import '../../widgets/ai/save_prompt_dialog.dart';
import 'widgets/compliance_result_card.dart';

const _kComplianceSuggestions = <String>[
  'Kiểm tra mẫu căn cứ pháp lý: phải trích dẫn đầy đủ tên Luật, số hiệu, ngày ban hành.',
  'Đảm bảo có đủ các phần: Mở đầu, Nội dung chính, Kết luận, Hiệu lực thi hành.',
  'Kiểm tra bố cục theo Nghị định 30/2020/NĐ-CP về công tác văn thư.',
  'Mọi danh từ riêng / tên cơ quan phải viết hoa đúng quy chuẩn.',
  'Phải có các dấu hiệu của một văn bản hành chính chính thức: quốc hiệu, số hiệu, ngày, nơi nhận, người ký.',
  'Kiểm tra trùng lặp nội dung, mâu thuẫn giữa các điều khoản.',
];

class ComplianceCheckScreen extends ConsumerStatefulWidget {
  const ComplianceCheckScreen({super.key});

  @override
  ConsumerState<ComplianceCheckScreen> createState() => _ComplianceCheckScreenState();
}

class _ComplianceCheckScreenState extends ConsumerState<ComplianceCheckScreen> {
  String _targetType = 'document'; // 'document' | 'template'
  int? _targetId;
  String _targetLabel = '';
  PromptRecord? _selectedPrompt;
  String _promptMode = 'saved'; // 'saved' | 'inline'
  final TextEditingController _inlinePromptCtrl = TextEditingController();
  ComplianceResult? _result;
  bool _loading = false;
  String? _error;

  @override
  void dispose() {
    _inlinePromptCtrl.dispose();
    super.dispose();
  }

  Future<void> _pickPrompt() async {
    final p = await PromptPickerDialog.show(
      context,
      scope: 'compliance_check',
    );
    if (p != null) setState(() => _selectedPrompt = p);
  }

  Future<void> _saveInlinePrompt() async {
    final text = _inlinePromptCtrl.text.trim();
    if (text.isEmpty) return;
    final preview = text.length > 60 ? '${text.substring(0, 60)}...' : text;
    final saved = await SavePromptDialog.show(
      context,
      initialTitle: 'Prompt kiểm tra văn bản: $preview',
      systemContent: '',
      rulesContent: text,
      defaultScopes: const ['compliance_check'],
    );
    if (saved == null || !mounted) return;
    setState(() {
      _selectedPrompt = saved;
      _promptMode = 'saved';
    });
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text('Đã lưu prompt: ${saved.title}')),
    );
  }

  void _applySuggestion(String text) {
    setState(() {
      final existing = _inlinePromptCtrl.text.trim();
      _inlinePromptCtrl.text =
          existing.isEmpty ? text : '$existing\n- $text';
      _promptMode = 'inline';
    });
  }

  bool _canRun() {
    if (_targetId == null || _loading) return false;
    if (_promptMode == 'saved') return _selectedPrompt != null;
    return _inlinePromptCtrl.text.trim().isNotEmpty;
  }

  Future<void> _pickTarget() async {
    final result = await showDialog<_PickResult>(
      context: context,
      builder: (_) => _TargetPickerDialog(targetType: _targetType),
    );
    if (result != null) {
      setState(() {
        _targetId = result.id;
        _targetLabel = result.label;
      });
    }
  }

  Future<void> _runCheck({bool force = false}) async {
    if (_targetId == null) return;
    PromptRecord? promptToUse = _selectedPrompt;
    // Neu o inline mode, auto-save thanh prompt rieng truoc khi run
    if (_promptMode == 'inline') {
      final text = _inlinePromptCtrl.text.trim();
      if (text.isEmpty) {
        setState(() => _error = 'Hãy nhập nội dung yêu cầu kiểm tra hoặc chọn prompt đã lưu.');
        return;
      }
      final preview = text.length > 60 ? '${text.substring(0, 60)}...' : text;
      final saved = await SavePromptDialog.show(
        context,
        initialTitle: 'Prompt kiểm tra văn bản: $preview',
        systemContent: '',
        rulesContent: text,
        defaultScopes: const ['compliance_check'],
      );
      if (saved == null) return;
      if (!mounted) return;
      promptToUse = saved;
      setState(() {
        _selectedPrompt = saved;
        _promptMode = 'saved';
      });
    }
    if (promptToUse == null) return;
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final r = await ref.read(complianceApiProvider).run(
            targetType: _targetType,
            targetId: _targetId!,
            promptId: promptToUse.id,
            force: force,
          );
      if (!mounted) return;
      setState(() => _result = r);
      ref.invalidate(complianceHistoryProvider(
        (type: _targetType, id: _targetId!),
      ));
    } on DioException catch (e) {
      final d = e.response?.data;
      final detail = (d is Map ? d['detail']?.toString() : null) ?? e.message;
      if (!mounted) return;
      setState(() => _error = detail ?? 'Lỗi không xác định');
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Kiểm tra văn bản theo quy trình')),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // Buoc 1: chon nguon
            Card(
              child: Padding(
                padding: const EdgeInsets.all(12),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(children: const [
                      Icon(Icons.looks_one, color: Colors.blue),
                      SizedBox(width: 8),
                      Text('Bước 1: Chọn nguồn cần kiểm tra',
                          style: TextStyle(fontWeight: FontWeight.bold, fontSize: 15)),
                    ]),
                    const SizedBox(height: 12),
                    Row(children: [
                      Radio<String>(
                        value: 'document',
                        groupValue: _targetType,
                        onChanged: (v) => setState(() {
                          _targetType = v ?? 'document';
                          _targetId = null;
                          _targetLabel = '';
                        }),
                      ),
                      const Text('Văn bản'),
                      const SizedBox(width: 16),
                      Radio<String>(
                        value: 'template',
                        groupValue: _targetType,
                        onChanged: (v) => setState(() {
                          _targetType = v ?? 'document';
                          _targetId = null;
                          _targetLabel = '';
                        }),
                      ),
                      const Text('Mẫu văn bản'),
                    ]),
                    const SizedBox(height: 8),
                    OutlinedButton.icon(
                      icon: const Icon(Icons.search),
                      label: Text(_targetId == null
                          ? (_targetType == 'document' ? 'Chọn văn bản...' : 'Chọn mẫu văn bản...')
                          : 'Đã chọn: $_targetLabel'),
                      onPressed: _pickTarget,
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 12),

            // Buoc 2: chon hoac nhap prompt
            _PromptSection(
              mode: _promptMode,
              selectedPrompt: _selectedPrompt,
              inlineCtrl: _inlinePromptCtrl,
              onModeChanged: (m) => setState(() => _promptMode = m),
              onPickSaved: _pickPrompt,
              onClearSaved: () => setState(() => _selectedPrompt = null),
              onSaveInline: _saveInlinePrompt,
              onApplySuggestion: _applySuggestion,
              onTextChanged: () => setState(() {}),
            ),
            const SizedBox(height: 16),

            // Nut kiem tra
            Center(
              child: FilledButton.icon(
                style: FilledButton.styleFrom(
                  padding: const EdgeInsets.symmetric(
                      horizontal: 24, vertical: 14),
                ),
                icon: const Icon(Icons.check_circle),
                label: const Text('Kiểm tra'),
                onPressed: _canRun() ? () => _runCheck() : null,
              ),
            ),
            const SizedBox(height: 16),

            if (_loading)
              const Center(
                child: Padding(
                  padding: EdgeInsets.all(20),
                  child: Column(children: [
                    CircularProgressIndicator(),
                    SizedBox(height: 12),
                    Text('Đang phân tích văn bản…'),
                  ]),
                ),
              ),

            if (_error != null)
              Card(
                color: Colors.red.shade50,
                child: Padding(
                  padding: const EdgeInsets.all(12),
                  child: Row(children: [
                    const Icon(Icons.error_outline, color: Colors.red),
                    const SizedBox(width: 8),
                    Expanded(child: Text('Lỗi: $_error')),
                    TextButton(
                      onPressed: () => setState(() => _error = null),
                      child: const Text('Đóng'),
                    ),
                  ]),
                ),
              ),

            if (_result != null)
              ComplianceResultCard(
                result: _result!,
                onRetry: () => _runCheck(force: true),
              ),

            const SizedBox(height: 24),
            if (_targetId != null)
              _HistorySection(
                targetType: _targetType,
                targetId: _targetId!,
                onSelect: (r) => setState(() => _result = r),
              ),
          ],
        ),
      ),
    );
  }
}

class _PickResult {
  final int id;
  final String label;
  const _PickResult({required this.id, required this.label});
}

class _TargetPickerDialog extends ConsumerStatefulWidget {
  final String targetType;
  const _TargetPickerDialog({required this.targetType});

  @override
  ConsumerState<_TargetPickerDialog> createState() => _TargetPickerDialogState();
}

class _TargetPickerDialogState extends ConsumerState<_TargetPickerDialog> {
  final _searchCtrl = TextEditingController();
  String _query = '';
  List<Map<String, dynamic>> _items = [];
  bool _loading = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    _searchCtrl.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final endpoint = widget.targetType == 'document' ? 'documents/' : 'templates/';
      final resp = await ApiClient().dio.get(
        endpoint,
        queryParameters: {
          if (_query.isNotEmpty) 'search': _query,
          'page_size': 25,
        },
      );
      final data = resp.data;
      final list = data is Map ? (data['results'] ?? []) as List : data as List;
      if (!mounted) return;
      setState(() {
        _items = list.map((e) => Map<String, dynamic>.from(e as Map)).toList();
        _loading = false;
      });
    } on DioException catch (e) {
      if (!mounted) return;
      setState(() {
        _error = e.message;
        _loading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final isDocument = widget.targetType == 'document';
    return AlertDialog(
      title: Text(isDocument ? 'Chọn văn bản' : 'Chọn mẫu văn bản'),
      content: SizedBox(
        width: 480,
        height: 400,
        child: Column(
          children: [
            TextField(
              controller: _searchCtrl,
              decoration: InputDecoration(
                prefixIcon: const Icon(Icons.search),
                hintText: isDocument ? 'Tìm văn bản theo tên...' : 'Tìm mẫu văn bản...',
                suffixIcon: IconButton(
                  icon: const Icon(Icons.refresh),
                  onPressed: _load,
                ),
              ),
              onChanged: (v) => setState(() => _query = v),
              onSubmitted: (_) => _load(),
            ),
            const SizedBox(height: 8),
            Expanded(
              child: _loading
                  ? const Center(child: CircularProgressIndicator())
                  : _error != null
                      ? Center(child: Text('Lỗi: $_error'))
                      : _items.isEmpty
                          ? const Center(child: Text('Không có dữ liệu.'))
                          : ListView.separated(
                              itemCount: _items.length,
                              separatorBuilder: (_, __) => const Divider(height: 1),
                              itemBuilder: (_, i) {
                                final item = _items[i];
                                final id = item['id'] as int;
                                final title = (item['title'] ?? item['name'] ?? '#$id') as String;
                                return ListTile(
                                  dense: true,
                                  leading: Icon(isDocument ? Icons.article : Icons.description),
                                  title: Text(title),
                                  onTap: () => Navigator.pop(
                                    context,
                                    _PickResult(id: id, label: title),
                                  ),
                                );
                              },
                            ),
            ),
          ],
        ),
      ),
      actions: [
        TextButton(onPressed: () => Navigator.pop(context), child: const Text('Hủy')),
      ],
    );
  }
}

class _HistorySection extends ConsumerWidget {
  final String targetType;
  final int targetId;
  final ValueChanged<ComplianceResult> onSelect;

  const _HistorySection({
    required this.targetType,
    required this.targetId,
    required this.onSelect,
  });

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final async = ref.watch(complianceHistoryProvider((type: targetType, id: targetId)));
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text('Lịch sử 10 lần kiểm tra gần nhất',
                style: TextStyle(fontWeight: FontWeight.bold, fontSize: 14)),
            const SizedBox(height: 8),
            async.when(
              data: (items) => items.isEmpty
                  ? const Padding(
                      padding: EdgeInsets.symmetric(vertical: 12),
                      child: Text('Chưa có lịch sử kiểm tra.', style: TextStyle(color: Colors.grey)),
                    )
                  : Column(
                      children: items
                          .map((r) => ListTile(
                                dense: true,
                                leading: Icon(
                                  r.passed ? Icons.check_circle : Icons.cancel,
                                  color: r.passed ? Colors.green : Colors.red,
                                  size: 18,
                                ),
                                title: Text(r.passed ? 'Đạt' : 'Chưa đạt (${r.itemsMissing.length} mục)'),
                                subtitle: Text(_formatDate(r.checkedAt)),
                                onTap: () => onSelect(r),
                              ))
                          .toList(),
                    ),
              loading: () => const Padding(
                padding: EdgeInsets.symmetric(vertical: 12),
                child: Center(child: CircularProgressIndicator()),
              ),
              error: (e, _) => Text('Lỗi: $e', style: const TextStyle(color: Colors.red)),
            ),
          ],
        ),
      ),
    );
  }

  String _formatDate(String? raw) {
    if (raw == null || raw.isEmpty) return '—';
    try {
      final dt = DateTime.parse(raw).toLocal();
      return '${dt.day.toString().padLeft(2, '0')}/${dt.month.toString().padLeft(2, '0')}/${dt.year} '
          '${dt.hour.toString().padLeft(2, '0')}:${dt.minute.toString().padLeft(2, '0')}';
    } catch (_) {
      return raw;
    }
  }
}

class _PromptSection extends StatelessWidget {
  final String mode;
  final PromptRecord? selectedPrompt;
  final TextEditingController inlineCtrl;
  final ValueChanged<String> onModeChanged;
  final VoidCallback onPickSaved;
  final VoidCallback onClearSaved;
  final VoidCallback onSaveInline;
  final ValueChanged<String> onApplySuggestion;
  final VoidCallback onTextChanged;

  const _PromptSection({
    required this.mode,
    required this.selectedPrompt,
    required this.inlineCtrl,
    required this.onModeChanged,
    required this.onPickSaved,
    required this.onClearSaved,
    required this.onSaveInline,
    required this.onApplySuggestion,
    required this.onTextChanged,
  });

  @override
  Widget build(BuildContext context) {
    final isMobile = MediaQuery.sizeOf(context).width < 720;
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(children: const [
              Icon(Icons.looks_two, color: Colors.blue),
              SizedBox(width: 8),
              Expanded(
                child: Text('Bước 2: Yêu cầu kiểm tra (prompt quy trình)',
                    style: TextStyle(
                        fontWeight: FontWeight.bold, fontSize: 15)),
              ),
            ]),
            const SizedBox(height: 8),
            const Text(
              'Chọn prompt đã lưu để dùng lại quy chuẩn cũ, hoặc nhập trực tiếp bộ tiêu chí mới. Khi nhập trực tiếp, hệ thống sẽ yêu cầu lưu thành Prompt riêng trước khi chạy.',
              style: TextStyle(fontSize: 12, color: Color(0xFF64748B)),
            ),
            const SizedBox(height: 12),
            SegmentedButton<String>(
              segments: const [
                ButtonSegment(
                  value: 'saved',
                  icon: Icon(Icons.library_books_outlined, size: 16),
                  label: Text('Prompt đã lưu'),
                ),
                ButtonSegment(
                  value: 'inline',
                  icon: Icon(Icons.edit_note_outlined, size: 16),
                  label: Text('Nhập trực tiếp'),
                ),
              ],
              selected: {mode},
              onSelectionChanged: (s) => onModeChanged(s.first),
              showSelectedIcon: false,
              style: ButtonStyle(
                visualDensity: VisualDensity.compact,
                textStyle: WidgetStateProperty.all(
                    const TextStyle(fontSize: 13)),
              ),
            ),
            const SizedBox(height: 14),
            if (mode == 'saved')
              _SavedPromptBlock(
                prompt: selectedPrompt,
                onPick: onPickSaved,
                onClear: onClearSaved,
              )
            else
              _InlinePromptBlock(
                ctrl: inlineCtrl,
                onSave: onSaveInline,
                onTextChanged: onTextChanged,
                isMobile: isMobile,
                onApplySuggestion: onApplySuggestion,
              ),
          ],
        ),
      ),
    );
  }
}

class _SavedPromptBlock extends StatelessWidget {
  final PromptRecord? prompt;
  final VoidCallback onPick;
  final VoidCallback onClear;
  const _SavedPromptBlock({
    required this.prompt,
    required this.onPick,
    required this.onClear,
  });

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        if (prompt == null)
          OutlinedButton.icon(
            icon: const Icon(Icons.psychology),
            label: const Text('Chọn prompt scope "compliance_check"...'),
            onPressed: onPick,
          )
        else
          Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: const Color(0xFFEFF6FF),
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: const Color(0xFFBFDBFE)),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(children: [
                  const Icon(Icons.psychology,
                      color: Color(0xFF1D4ED8), size: 20),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(prompt!.title,
                        style: const TextStyle(
                            fontWeight: FontWeight.w800,
                            fontSize: 14,
                            color: Color(0xFF1E3A8A))),
                  ),
                  TextButton.icon(
                    onPressed: onPick,
                    icon: const Icon(Icons.swap_horiz, size: 14),
                    label: const Text('Đổi'),
                  ),
                  TextButton.icon(
                    onPressed: onClear,
                    icon: const Icon(Icons.clear, size: 14),
                    label: const Text('Xoá'),
                    style: TextButton.styleFrom(
                        foregroundColor: Colors.red),
                  ),
                ]),
                if ((prompt!.rulesContent ?? '').trim().isNotEmpty) ...[
                  const SizedBox(height: 6),
                  Text(
                    prompt!.rulesContent ?? '',
                    maxLines: 4,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(
                        fontSize: 12, color: Color(0xFF475569)),
                  ),
                ],
              ],
            ),
          ),
      ],
    );
  }
}

class _InlinePromptBlock extends StatelessWidget {
  final TextEditingController ctrl;
  final VoidCallback onSave;
  final VoidCallback onTextChanged;
  final ValueChanged<String> onApplySuggestion;
  final bool isMobile;
  const _InlinePromptBlock({
    required this.ctrl,
    required this.onSave,
    required this.onTextChanged,
    required this.onApplySuggestion,
    required this.isMobile,
  });

  @override
  Widget build(BuildContext context) {
    final hasText = ctrl.text.trim().isNotEmpty;
    final input = TextField(
      controller: ctrl,
      minLines: 4,
      maxLines: 10,
      onChanged: (_) => onTextChanged(),
      decoration: InputDecoration(
        hintText:
            'Liệt kê các yêu cầu/quy trình cần kiểm tra (mỗi dòng 1 yêu cầu).',
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
        ),
        filled: true,
        fillColor: const Color(0xFFFAFCFF),
      ),
    );
    final suggestions = Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: const Color(0xFFFEF3C7),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: const Color(0xFFFCD34D)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Row(children: [
            Icon(Icons.lightbulb_outline,
                size: 16, color: Color(0xFF92400E)),
            SizedBox(width: 6),
            Text('Gợi ý yêu cầu kiểm tra',
                style: TextStyle(
                    fontSize: 12,
                    fontWeight: FontWeight.w800,
                    color: Color(0xFF92400E))),
          ]),
          const SizedBox(height: 8),
          Wrap(
            spacing: 6,
            runSpacing: 6,
            children: _kComplianceSuggestions
                .map(
                  (s) => ActionChip(
                    backgroundColor: Colors.white,
                    side: const BorderSide(color: Color(0xFFFCD34D)),
                    label: Text(
                      s.length > 60 ? '${s.substring(0, 60)}...' : s,
                      style: const TextStyle(
                          fontSize: 11, color: Color(0xFF78350F)),
                    ),
                    onPressed: () => onApplySuggestion(s),
                  ),
                )
                .toList(),
          ),
        ],
      ),
    );
    final saveBtn = OutlinedButton.icon(
      onPressed: hasText ? onSave : null,
      icon: const Icon(Icons.bookmark_add_outlined, size: 16),
      label: const Text('Lưu thành Prompt quản lý'),
      style: OutlinedButton.styleFrom(
        foregroundColor: const Color(0xFF15803D),
        side: const BorderSide(color: Color(0xFFBBF7D0)),
      ),
    );
    if (isMobile) {
      return Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          input,
          const SizedBox(height: 10),
          Align(alignment: Alignment.centerLeft, child: saveBtn),
          const SizedBox(height: 12),
          suggestions,
        ],
      );
    }
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Expanded(
          flex: 7,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              input,
              const SizedBox(height: 10),
              Align(alignment: Alignment.centerLeft, child: saveBtn),
            ],
          ),
        ),
        const SizedBox(width: 14),
        Expanded(flex: 5, child: suggestions),
      ],
    );
  }
}
