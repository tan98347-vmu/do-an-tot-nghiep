// ignore_for_file: avoid_web_libraries_in_flutter
import 'dart:html' as html;

import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/browser_alert.dart';
import '../../core/browser_voice_input.dart';
import '../../core/word_ai_user_messages.dart';
import '../../providers/documents_provider.dart';
import '../../providers/prompt_preflight_provider.dart';
import '../../providers/word_ai_provider.dart';
import '../ai/prompt_picker_dialog.dart';
import '../ai/save_prompt_dialog.dart';

String _describeWordAiCreateError(DioException error) {
  final responseMessage = _flattenApiError(error.response?.data);
  if (responseMessage != null && responseMessage.isNotEmpty) {
    return responseMessage;
  }
  return error.message ?? 'Không tạo được yêu cầu Word AI. Hãy thử lại sau.';
}

String? _flattenApiError(Object? value) {
  if (value == null) {
    return null;
  }
  if (value is String) {
    final trimmed = value.trim();
    return trimmed.isEmpty ? null : trimmed;
  }
  if (value is List) {
    final parts = value.map(_flattenApiError).whereType<String>().toList();
    if (parts.isEmpty) {
      return null;
    }
    return parts.join(' ');
  }
  if (value is Map) {
    final detail = _flattenApiError(value['detail']);
    if (detail != null && detail.isNotEmpty) {
      return detail;
    }
    final parts = <String>[];
    value.forEach((key, nestedValue) {
      final nestedMessage = _flattenApiError(nestedValue);
      if (nestedMessage == null || nestedMessage.isEmpty) {
        return;
      }
      final fieldName = '$key'.trim();
      parts.add(fieldName.isEmpty ? nestedMessage : '$fieldName: $nestedMessage');
    });
    if (parts.isEmpty) {
      return null;
    }
    return parts.join('\n');
  }
  return '$value';
}

class DocumentAiEditPanel extends ConsumerStatefulWidget {
  final int documentId;
  final bool canEdit;
  final String? disabledReason;

  const DocumentAiEditPanel({
    super.key,
    required this.documentId,
    required this.canEdit,
    this.disabledReason,
  });

  @override
  ConsumerState<DocumentAiEditPanel> createState() => _DocumentAiEditPanelState();
}

class _DocumentAiEditPanelState extends ConsumerState<DocumentAiEditPanel> {
  static const List<String> _editPresetPrompts = <String>[
    'Thay tất cả "Công ty A" thành "Công ty B" trong phần nội dung, đầu trang và chân trang. Giữ nguyên định dạng hiện có.',
    'Rút gọn phần mở đầu khoảng 30%, giữ nguyên ý chính và giọng văn trang trọng.',
    'Viết lại toàn văn rõ ràng, mạch lạc hơn; không thay đổi nội dung pháp lý và không đổi định dạng.',
    'Bật Track Changes rồi sửa lỗi chính tả, dấu câu và cách diễn đạt để văn bản dễ đọc hơn.',
    'Chuẩn hóa cách viết tên cơ quan, chức danh và ngày tháng trong toàn bộ văn bản; giữ nguyên bố cục hiện tại.',
    'Căn giữa các tiêu đề chính, giữ nguyên định dạng phần thân văn bản.',
    'Thêm nhận xét tại đoạn đang chọn: "Cần kiểm tra lại số liệu và căn cứ pháp lý ở mục này."',
    'Rà soát nội dung trong các bảng, chuẩn hóa cách ghi đơn vị và số tiền; giữ nguyên cấu trúc bảng.',
  ];

  static const List<String> _checkPresetPrompts = <String>[
    'Kiểm tra văn bản có đầy đủ Quốc hiệu, tiêu ngữ, số hiệu, ngày tháng, cơ quan ban hành theo Nghị định 30/2020/NĐ-CP.',
    'Rà soát các điều khoản căn cứ pháp lý: phải có số hiệu, ngày ban hành, cơ quan ban hành đầy đủ.',
    'Kiểm tra bố cục có đủ Mở đầu - Nội dung - Kết luận - Hiệu lực thi hành.',
    'Soát lỗi chính tả, viết hoa danh từ riêng, chuẩn hóa tên cơ quan và chức danh.',
    'Kiểm tra mâu thuẫn nội dung giữa các điều khoản trong văn bản.',
    'Đảm bảo phần kết luận có nêu rõ trách nhiệm thực thi và thời điểm hiệu lực.',
  ];

  static const String _recentKeyEdit = 'wordai_recent_edit_prompts';
  static const String _recentKeyCheck = 'wordai_recent_check_prompts';
  static const int _recentMax = 6;

  String _activeTab = 'edit'; // 'edit' | 'check'
  List<String> _recentEditPrompts = [];
  List<String> _recentCheckPrompts = [];

  final TextEditingController _instructionController = TextEditingController();
  final FocusNode _instructionFocusNode = FocusNode();
  late final BrowserVoiceInputController _voiceInputController;
  bool _trackChanges = false;
  bool _submitting = false;
  bool _checkingPrompt = false;
  String? _promptCheckToken;
  bool _voiceListening = false;
  String _voiceStatus = 'idle';
  String _liveTranscript = '';
  String? _voiceError;

  @override
  void initState() {
    super.initState();
    _voiceInputController = createBrowserVoiceInputController();
    _instructionController.addListener(_onInstructionChanged);
    _loadRecentPrompts();
  }

  void _onInstructionChanged() {
    if (_promptCheckToken != null && mounted) {
      setState(() => _promptCheckToken = null);
    }
  }

  void _loadRecentPrompts() {
    try {
      final s = html.window.localStorage;
      final edit = s[_recentKeyEdit];
      final check = s[_recentKeyCheck];
      _recentEditPrompts = edit == null || edit.isEmpty
          ? []
          : edit.split('').where((e) => e.trim().isNotEmpty).toList();
      _recentCheckPrompts = check == null || check.isEmpty
          ? []
          : check.split('').where((e) => e.trim().isNotEmpty).toList();
    } catch (_) {
      _recentEditPrompts = [];
      _recentCheckPrompts = [];
    }
  }

  void _saveRecentPrompt(String prompt) {
    if (prompt.trim().isEmpty) return;
    final key = _activeTab == 'check' ? _recentKeyCheck : _recentKeyEdit;
    final list = _activeTab == 'check' ? _recentCheckPrompts : _recentEditPrompts;
    list.remove(prompt);
    list.insert(0, prompt);
    if (list.length > _recentMax) list.removeRange(_recentMax, list.length);
    try {
      html.window.localStorage[key] = list.join('');
    } catch (_) {}
    setState(() {});
  }

  @override
  void dispose() {
    _voiceInputController.dispose();
    _instructionFocusNode.dispose();
    _instructionController.removeListener(_onInstructionChanged);
    _instructionController.dispose();
    super.dispose();
  }

  void _applyPromptSuggestion(String prompt) {
    if (!widget.canEdit || _submitting) {
      return;
    }
    _instructionController
      ..text = prompt
      ..selection = TextSelection.collapsed(offset: prompt.length);
    _instructionFocusNode.requestFocus();
    setState(() {
      _voiceError = null;
      _liveTranscript = '';
    });
  }

  void _appendVoiceTranscript(String transcript) {
    final nextText = transcript.trim();
    if (nextText.isEmpty) {
      return;
    }
    final currentText = _instructionController.text.trim();
    final merged = currentText.isEmpty ? nextText : '$currentText\n$nextText';
    _instructionController
      ..text = merged
      ..selection = TextSelection.collapsed(offset: merged.length);
    _instructionFocusNode.requestFocus();
  }

  Future<void> _toggleVoiceInput() async {
    if (!widget.canEdit || _submitting) {
      return;
    }
    if (_voiceListening) {
      await _voiceInputController.stop();
      return;
    }
    setState(() {
      _voiceError = null;
      _liveTranscript = '';
      _voiceStatus = 'idle';
    });
    final started = await _voiceInputController.start(
      onTranscript: (transcript, {required isFinal}) {
        if (!mounted) {
          return;
        }
        if (isFinal) {
          setState(() {
            _voiceListening = false;
            _voiceStatus = 'processing';
            _liveTranscript = '';
          });
          _appendVoiceTranscript(transcript);
          return;
        }
        setState(() => _liveTranscript = transcript);
      },
      onStatus: (status) {
        if (!mounted) {
          return;
        }
        setState(() {
          _voiceStatus = status;
          _voiceListening = status == 'listening';
          if (status == 'idle' && !_voiceListening) {
            _liveTranscript = '';
          }
        });
      },
      onError: (message) {
        if (!mounted) {
          return;
        }
        setState(() {
          _voiceListening = false;
          _voiceStatus = 'idle';
          _voiceError = message.trim().isEmpty ? null : message.trim();
          _liveTranscript = '';
        });
        if (_voiceError != null) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text(_voiceError!)),
          );
        }
      },
    );
    if (!mounted || started) {
      return;
    }
    setState(() => _voiceListening = false);
  }

  Future<void> _pickSavedPrompt() async {
    final picked = await PromptPickerDialog.show(
      context,
      scope: 'word_ai_edit',
    );
    if (picked == null || !mounted) return;
    final sys = (picked.systemContent ?? '').trim();
    final rules = (picked.rulesContent ?? '').trim();
    final body = [
      if (sys.isNotEmpty) sys,
      if (rules.isNotEmpty) rules,
    ].join('\n\n').trim();
    if (body.isEmpty) return;
    setState(() {
      final existing = _instructionController.text.trim();
      _instructionController.text =
          existing.isEmpty ? body : '$existing\n\n$body';
    });
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text('Đã chèn prompt: ${picked.title}')),
    );
  }

  Future<void> _saveCurrentPrompt() async {
    final text = _instructionController.text.trim();
    if (text.isEmpty) return;
    final preview = text.length > 60 ? '${text.substring(0, 60)}...' : text;
    final saved = await SavePromptDialog.show(
      context,
      initialTitle: 'Prompt sửa văn bản: $preview',
      systemContent: '',
      rulesContent: text,
      defaultScopes: const ['word_ai_edit'],
    );
    if (saved == null || !mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text('Đã lưu prompt: ${saved.title}')),
    );
  }

  Future<void> _checkInstructionPrompt() async {
    final instruction = _instructionController.text.trim();
    if (instruction.isEmpty) {
      await showBrowserAlert(context, 'Vui lòng nhập yêu cầu cho Word AI trước khi kiểm tra prompt.');
      return;
    }
    setState(() {
      _checkingPrompt = true;
      _promptCheckToken = null;
    });
    final result = await checkPromptPreflight(
      scope: 'word_ai_edit',
      context: 'document_ai_edit',
      promptRole: 'main_instruction',
      promptText: instruction,
      targetId: widget.documentId,
    );
    if (!mounted) return;
    if (_instructionController.text.trim() != instruction) {
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

  Future<void> _submit() async {
    final instruction = _instructionController.text.trim();
    if (instruction.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Hãy nhập yêu cầu cho Word AI trước khi chạy.')),
      );
      return;
    }
    if ((_promptCheckToken ?? '').isEmpty) {
      await showBrowserAlert(
        context,
        'Hãy bấm "Check prompt" và sửa yêu cầu nếu cần trước khi chạy Word AI.',
      );
      return;
    }
    setState(() => _submitting = true);
    _saveRecentPrompt(instruction);
    try {
      final job = await createWordAiJob(
        documentId: widget.documentId,
        instruction: instruction,
        promptCheckToken: _promptCheckToken!,
        trackChanges: _trackChanges,
      );
      if (!mounted) return;
      _instructionController.clear();
      refreshWordAiJobs(ref);
      refreshDocumentCollections(ref);
      final latestMessage = job.latestEvent?.message.trim() ?? '';
      final latestIsWarning = job.latestEvent?.level == 'warning' && latestMessage.isNotEmpty;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            latestIsWarning
                ? wordAiQueuedMessageForUser(job)
                : 'Đã gửi yêu cầu cho Word AI. Bạn có thể theo dõi tiến độ ở mục Lịch sử Word AI ngay bên dưới.',
          ),
        ),
      );
    } on DioException catch (error) {
      final detail = _describeWordAiCreateError(error);
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(detail)),
      );
    } finally {
      if (mounted) {
        setState(() => _submitting = false);
      }
    }
  }

  Widget _buildFeaturePill(BuildContext context, IconData icon, String label) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
      decoration: BoxDecoration(
        color: const Color(0xFFF8FAFC),
        borderRadius: BorderRadius.circular(999),
        border: Border.all(color: const Color(0xFFE2E8F0)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 14, color: const Color(0xFF334155)),
          const SizedBox(width: 6),
          Text(
            label,
            style: Theme.of(context).textTheme.labelMedium?.copyWith(
                  color: const Color(0xFF334155),
                  fontWeight: FontWeight.w600,
                ),
          ),
        ],
      ),
    );
  }

  Widget _buildQuickPromptChips(BuildContext context) {
    final recents = _activeTab == 'check'
        ? _recentCheckPrompts
        : _recentEditPrompts;
    final presets = _activeTab == 'check'
        ? _checkPresetPrompts
        : _editPresetPrompts;
    // Hien recent truoc; chi bu preset cho du recentMax slot.
    final remaining = (_recentMax - recents.length).clamp(0, presets.length);
    final fillFromPreset = presets
        .where((p) => !recents.contains(p))
        .take(remaining)
        .toList();
    final accent = _activeTab == 'check'
        ? const Color(0xFFD97706)
        : const Color(0xFF1D4ED8);

    Widget chip(String prompt, {required bool isRecent}) {
      return ActionChip(
        onPressed: widget.canEdit && !_submitting
            ? () => _applyPromptSuggestion(prompt)
            : null,
        avatar: Icon(
          isRecent ? Icons.history_toggle_off : Icons.bolt,
          size: 16,
          color: accent,
        ),
        label: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 280),
          child: Text(
            prompt,
            maxLines: 2,
            overflow: TextOverflow.ellipsis,
          ),
        ),
        labelStyle: Theme.of(context).textTheme.bodySmall?.copyWith(
              fontWeight: FontWeight.w600,
              color: const Color(0xFF0F172A),
            ),
        backgroundColor:
            isRecent ? accent.withOpacity(0.08) : const Color(0xFFF8FAFC),
        side: BorderSide(
          color: isRecent ? accent.withOpacity(0.4) : const Color(0xFFE2E8F0),
        ),
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 10),
      );
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        SegmentedButton<String>(
          segments: const [
            ButtonSegment(
              value: 'edit',
              icon: Icon(Icons.auto_fix_high, size: 16),
              label: Text('Sửa văn bản với AI'),
            ),
            ButtonSegment(
              value: 'check',
              icon: Icon(Icons.fact_check_outlined, size: 16),
              label: Text('Quy trình kiểm tra văn bản'),
            ),
          ],
          selected: {_activeTab},
          onSelectionChanged: (s) =>
              setState(() => _activeTab = s.first),
          showSelectedIcon: false,
          style: ButtonStyle(
            visualDensity: VisualDensity.compact,
            textStyle:
                WidgetStateProperty.all(const TextStyle(fontSize: 12.5)),
          ),
        ),
        const SizedBox(height: 12),
        if (recents.isNotEmpty) ...[
          Row(children: [
            Icon(Icons.history_toggle_off, size: 14, color: accent),
            const SizedBox(width: 4),
            Text(
              'Lệnh dùng gần đây',
              style: TextStyle(
                fontSize: 11,
                fontWeight: FontWeight.w800,
                letterSpacing: 0.5,
                color: accent,
              ),
            ),
          ]),
          const SizedBox(height: 6),
        ],
        if (recents.isEmpty && fillFromPreset.isNotEmpty)
          Padding(
            padding: const EdgeInsets.only(bottom: 6),
            child: Text(
              'Chưa có lệnh dùng gần đây — gợi ý mặc định bên dưới.',
              style: TextStyle(
                fontSize: 11.5,
                fontStyle: FontStyle.italic,
                color: const Color(0xFF64748B),
              ),
            ),
          ),
        Wrap(
          spacing: 10,
          runSpacing: 10,
          children: [
            for (final p in recents) chip(p, isRecent: true),
            for (final p in fillFromPreset) chip(p, isRecent: false),
          ],
        ),
      ],
    );
  }

  Widget _buildVoiceComposerHint(BuildContext context) {
    if (_voiceError == null && _liveTranscript.isEmpty && _voiceStatus == 'idle') {
      return const SizedBox.shrink();
    }
    final isError = _voiceError != null;
    final message = isError
        ? _voiceError!
        : _liveTranscript.isNotEmpty
            ? _liveTranscript
            : 'Đang xử lý nội dung giọng nói để chèn vào ô nhập...';
    final accent = isError ? const Color(0xFFB91C1C) : const Color(0xFF0F766E);
    final bg = isError ? const Color(0xFFFEF2F2) : const Color(0xFFF0FDFA);
    final border = isError ? const Color(0xFFFECACA) : const Color(0xFF99F6E4);
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: bg,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: border),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(
            isError ? Icons.error_outline : Icons.graphic_eq,
            size: 18,
            color: accent,
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  isError ? 'Nhập giọng nói gặp vấn đề' : 'Bản ghi tạm thời',
                  style: Theme.of(context).textTheme.labelLarge?.copyWith(
                        color: accent,
                        fontWeight: FontWeight.w700,
                      ),
                ),
                const SizedBox(height: 4),
                Text(
                  message,
                  style: TextStyle(
                    color: accent,
                    height: 1.45,
                    fontSize: 12.5,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final disabledReason = widget.disabledReason?.trim() ?? '';
    return LayoutBuilder(
      builder: (context, constraints) {
        final compact = constraints.maxWidth < 760;
        final voiceSupported = _voiceInputController.isSupported;
        final canCompose = widget.canEdit && !_submitting;
        final canRun =
            canCompose && (_promptCheckToken ?? '').trim().isNotEmpty;

        final actionButtons = compact
            ? Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  if (voiceSupported)
                    OutlinedButton.icon(
                      onPressed: canCompose ? _toggleVoiceInput : null,
                      icon: Icon(
                        _voiceListening ? Icons.mic_off : Icons.mic_none,
                      ),
                      label: Text(
                        _voiceListening ? 'Dừng ghi giọng nói' : 'Nói để điền vào ô nhập',
                      ),
                    ),
                  if (!voiceSupported)
                    Text(
                      'Nhập bằng giọng nói hiện hỗ trợ trên Flutter Web với Chrome hoặc Edge có SpeechRecognition.',
                      style: const TextStyle(
                        fontSize: 12,
                        color: Color(0xFF64748B),
                        height: 1.45,
                      ),
                    ),
                  if (voiceSupported) const SizedBox(height: 12),
                  FilledButton.icon(
                    onPressed: canRun ? _submit : null,
                    icon: _submitting
                        ? const SizedBox(
                            width: 16,
                            height: 16,
                            child: CircularProgressIndicator(strokeWidth: 2),
                          )
                        : const Icon(Icons.auto_awesome),
                    label: Text(_submitting ? 'Đang gửi yêu cầu...' : 'Gửi cho Word AI'),
                  ),
                ],
              )
            : Row(
                children: [
                  Expanded(
                    child: voiceSupported
                        ? OutlinedButton.icon(
                            onPressed: canCompose ? _toggleVoiceInput : null,
                            icon: Icon(
                              _voiceListening ? Icons.mic_off : Icons.mic_none,
                            ),
                            label: Text(
                              _voiceListening
                                  ? 'Dừng ghi giọng nói'
                                  : 'Nói để chèn vào ô nhập',
                            ),
                          )
                        : const Text(
                            'Nhập bằng giọng nói hiện hỗ trợ trên Flutter Web với Chrome hoặc Edge có SpeechRecognition.',
                            style: TextStyle(
                              fontSize: 12,
                              color: Color(0xFF64748B),
                              height: 1.45,
                            ),
                          ),
                  ),
                  const SizedBox(width: 12),
                  FilledButton.icon(
                    onPressed: canRun ? _submit : null,
                    icon: _submitting
                        ? const SizedBox(
                            width: 16,
                            height: 16,
                            child: CircularProgressIndicator(strokeWidth: 2),
                          )
                        : const Icon(Icons.auto_awesome),
                    label: Text(_submitting ? 'Đang gửi yêu cầu...' : 'Gửi cho Word AI'),
                  ),
                ],
              );

        return Card(
          clipBehavior: Clip.antiAlias,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Container(
                width: double.infinity,
                padding: const EdgeInsets.all(20),
                decoration: const BoxDecoration(
                  gradient: LinearGradient(
                    colors: [Color(0xFFF8FAFC), Color(0xFFE0F2FE)],
                    begin: Alignment.topLeft,
                    end: Alignment.bottomRight,
                  ),
                ),
                child: compact
                    ? Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Container(
                            width: 44,
                            height: 44,
                            decoration: BoxDecoration(
                              color: Colors.white,
                              borderRadius: BorderRadius.circular(14),
                            ),
                            child: const Icon(
                              Icons.auto_awesome,
                              color: Color(0xFF0369A1),
                            ),
                          ),
                          const SizedBox(height: 14),
                          Text(
                            'Chỉnh sửa bằng Word AI',
                            style: Theme.of(context)
                                .textTheme
                                .titleMedium
                                ?.copyWith(fontWeight: FontWeight.w800),
                          ),
                          const SizedBox(height: 8),
                          const Text(
                            'Nhập yêu cầu hoặc nói trực tiếp để Word AI chỉnh sửa văn bản từng bước, tự kiểm tra lại kết quả rồi mới lưu thành phiên bản mới.',
                            style: TextStyle(
                              height: 1.5,
                              color: Color(0xFF334155),
                            ),
                          ),
                        ],
                      )
                    : Row(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Container(
                            width: 52,
                            height: 52,
                            decoration: BoxDecoration(
                              color: Colors.white,
                              borderRadius: BorderRadius.circular(16),
                            ),
                            child: const Icon(
                              Icons.auto_awesome,
                              color: Color(0xFF0369A1),
                            ),
                          ),
                          const SizedBox(width: 16),
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(
                                  'Chỉnh sửa bằng Word AI',
                                  style: Theme.of(context)
                                      .textTheme
                                      .titleMedium
                                      ?.copyWith(fontWeight: FontWeight.w800),
                                ),
                                const SizedBox(height: 8),
                                const Text(
                                  'Nhập yêu cầu hoặc nói trực tiếp để Word AI chỉnh sửa văn bản từng bước, tự kiểm tra lại kết quả rồi mới lưu thành phiên bản mới.',
                                  style: TextStyle(
                                    height: 1.5,
                                    color: Color(0xFF334155),
                                  ),
                                ),
                              ],
                            ),
                          ),
                          Container(
                            padding: const EdgeInsets.symmetric(
                              horizontal: 12,
                              vertical: 8,
                            ),
                            decoration: BoxDecoration(
                              color: Colors.white.withValues(alpha: 0.8),
                              borderRadius: BorderRadius.circular(999),
                              border: Border.all(color: const Color(0xFFBAE6FD)),
                            ),
                            child: const Text(
                              'Xử lý trực tiếp trong Word',
                              style: TextStyle(
                                fontSize: 12,
                                color: Color(0xFF0C4A6E),
                                fontWeight: FontWeight.w700,
                              ),
                            ),
                          ),
                        ],
                      ),
              ),
              Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Wrap(
                      spacing: 8,
                      runSpacing: 8,
                      children: [
                        _buildFeaturePill(context, Icons.smart_toy_outlined, 'Xử lý từng bước'),
                        _buildFeaturePill(context, Icons.fact_check_outlined, 'Tự kiểm tra kết quả'),
                        _buildFeaturePill(context, Icons.history_toggle_off, 'Tạo phiên bản mới'),
                        _buildFeaturePill(context, Icons.description_outlined, 'Chạy trực tiếp trong Word'),
                      ],
                    ),
                    if (!widget.canEdit && disabledReason.isNotEmpty) ...[
                      const SizedBox(height: 14),
                      Container(
                        width: double.infinity,
                        padding: const EdgeInsets.all(12),
                        decoration: BoxDecoration(
                          color: Colors.amber.shade50,
                          borderRadius: BorderRadius.circular(10),
                          border: Border.all(color: Colors.amber.shade200),
                        ),
                        child: Text(
                          disabledReason,
                          style: TextStyle(
                            fontSize: 12.5,
                            color: Colors.amber.shade900,
                          ),
                        ),
                      ),
                    ],
                    const SizedBox(height: 18),
                    Text(
                      'Gợi ý lệnh nhanh',
                      style: Theme.of(context).textTheme.titleSmall?.copyWith(
                            fontWeight: FontWeight.w800,
                          ),
                    ),
                    const SizedBox(height: 6),
                    const Text(
                      'Chạm vào một gợi ý để đổ nhanh vào ô nhập, sau đó chỉnh lại cho đúng với tài liệu của bạn.',
                      style: TextStyle(
                        color: Color(0xFF64748B),
                        height: 1.45,
                      ),
                    ),
                    const SizedBox(height: 12),
                    _buildQuickPromptChips(context),
                    const SizedBox(height: 18),
                    Text(
                      'Yêu cầu dành cho Word AI',
                      style: Theme.of(context).textTheme.titleSmall?.copyWith(
                            fontWeight: FontWeight.w800,
                          ),
                    ),
                    const SizedBox(height: 10),
                    const SizedBox(height: 10),
                    Container(
                      width: double.infinity,
                      padding: const EdgeInsets.all(12),
                      decoration: BoxDecoration(
                        color: const Color(0xFFF8FAFC),
                        borderRadius: BorderRadius.circular(12),
                        border: Border.all(color: const Color(0xFFE2E8F0)),
                      ),
                      child: const Text(
                        'Mẹo viết lệnh hiệu quả: nêu rõ phạm vi cần sửa (toàn văn bản, đoạn đang chọn, đầu trang, chân trang, bảng), nội dung cần thay đổi và chỉ nhắc đến định dạng khi bạn thực sự muốn đổi định dạng.',
                        style: TextStyle(
                          color: Color(0xFF475569),
                          height: 1.45,
                        ),
                      ),
                    ),
                    const SizedBox(height: 12),
                    Row(children: [
                      OutlinedButton.icon(
                        onPressed: canCompose ? _pickSavedPrompt : null,
                        icon: const Icon(Icons.library_books_outlined, size: 16),
                        label: const Text('Chọn prompt đã lưu'),
                        style: OutlinedButton.styleFrom(
                          foregroundColor: const Color(0xFF1D4ED8),
                          side: const BorderSide(color: Color(0xFFBFDBFE)),
                          padding: const EdgeInsets.symmetric(
                              horizontal: 12, vertical: 6),
                        ),
                      ),
                      const SizedBox(width: 8),
                      OutlinedButton.icon(
                        onPressed: canCompose &&
                                _instructionController.text.trim().isNotEmpty
                            ? _saveCurrentPrompt
                            : null,
                        icon: const Icon(Icons.bookmark_add_outlined, size: 16),
                        label: const Text('Lưu prompt'),
                        style: OutlinedButton.styleFrom(
                          foregroundColor: const Color(0xFF15803D),
                          side: const BorderSide(color: Color(0xFFBBF7D0)),
                          padding: const EdgeInsets.symmetric(
                              horizontal: 12, vertical: 6),
                        ),
                      ),
                    ]),
                    const SizedBox(height: 10),
                    TextField(
                      controller: _instructionController,
                      focusNode: _instructionFocusNode,
                      minLines: compact ? 4 : 5,
                      maxLines: compact ? 8 : 7,
                      enabled: canCompose,
                      onChanged: (_) => setState(() {}),
                      decoration: InputDecoration(
                        hintText:
                            'Ví dụ: Thay tất cả "Công ty A" thành "Công ty B" trong phần nội dung, giữ nguyên định dạng và bật Track Changes.',
                        border: OutlineInputBorder(
                          borderRadius: BorderRadius.circular(14),
                        ),
                        filled: true,
                        fillColor: const Color(0xFFFAFCFF),
                        alignLabelWithHint: true,
                      ),
                    ),
                    const SizedBox(height: 10),
                    Align(
                      alignment: Alignment.centerLeft,
                      child: OutlinedButton.icon(
                        onPressed: !canCompose ||
                                _checkingPrompt ||
                                _instructionController.text.trim().isEmpty
                            ? null
                            : _checkInstructionPrompt,
                        icon: _checkingPrompt
                            ? const SizedBox(
                                width: 14,
                                height: 14,
                                child:
                                    CircularProgressIndicator(strokeWidth: 2),
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
                    ),
                    const SizedBox(height: 12),
                    AnimatedSwitcher(
                      duration: const Duration(milliseconds: 180),
                      child: _buildVoiceComposerHint(context),
                    ),
                    if (_voiceListening || _voiceStatus == 'processing') ...[
                      const SizedBox(height: 10),
                      Row(
                        children: [
                          Icon(
                            _voiceListening ? Icons.graphic_eq : Icons.sync,
                            size: 16,
                            color: const Color(0xFF0F766E),
                          ),
                          const SizedBox(width: 8),
                          Text(
                            _voiceListening
                                ? 'Đang nghe... Nói xong thì chờ hệ thống chèn vào ô nhập.'
                                : 'Đang xử lý nội dung vừa ghi âm...',
                            style: const TextStyle(
                              fontSize: 12.5,
                              color: Color(0xFF0F766E),
                              fontWeight: FontWeight.w600,
                            ),
                          ),
                        ],
                      ),
                    ],
                    const SizedBox(height: 10),
                    SwitchListTile(
                      value: _trackChanges,
                      onChanged: canCompose
                          ? (value) => setState(() => _trackChanges = value)
                          : null,
                      title: const Text('Giữ lại dấu vết thay đổi (Track Changes)'),
                      subtitle: const Text(
                        'Phù hợp khi cần giữ lại dấu vết để đối chiếu trước khi chấp nhận.',
                      ),
                      contentPadding: EdgeInsets.zero,
                    ),
                    const SizedBox(height: 12),
                    actionButtons,
                  ],
                ),
              ),
            ],
          ),
        );
      },
    );
  }
}
