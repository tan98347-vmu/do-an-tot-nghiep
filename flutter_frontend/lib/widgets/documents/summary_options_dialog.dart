import 'package:flutter/material.dart';

import '../../core/browser_alert.dart';
import '../../providers/prompt_preflight_provider.dart';

class SummaryOptions {
  final int maxWords;
  final String language;
  final String style;
  final String userExtraRules;
  final String? promptCheckToken;

  const SummaryOptions({
    required this.maxWords,
    required this.language,
    required this.style,
    this.userExtraRules = '',
    this.promptCheckToken,
  });

  Map<String, dynamic> toJson() => {
        'max_words': maxWords,
        'language': language,
        'style': style,
        'length': _lengthFromMaxWords(maxWords),
      };

  static String _lengthFromMaxWords(int max) {
    if (max <= 150) return 'brief';
    if (max >= 800) return 'detailed';
    return 'standard';
  }
}

class SummaryOptionsDialog extends StatefulWidget {
  final int documentId;
  final SummaryOptions? initial;

  const SummaryOptionsDialog({
    super.key,
    required this.documentId,
    this.initial,
  });

  static Future<SummaryOptions?> show(
    BuildContext context, {
    required int documentId,
    SummaryOptions? initial,
  }) {
    return showDialog<SummaryOptions>(
      context: context,
      builder: (_) => SummaryOptionsDialog(
        documentId: documentId,
        initial: initial,
      ),
    );
  }

  @override
  State<SummaryOptionsDialog> createState() => _SummaryOptionsDialogState();
}

class _SummaryOptionsDialogState extends State<SummaryOptionsDialog> {
  late int _maxWords;
  late String _language;
  late String _style;
  late final TextEditingController _extraRulesController;
  String? _promptCheckToken;
  bool _checkingPrompt = false;

  @override
  void initState() {
    super.initState();
    _maxWords = widget.initial?.maxWords ?? 300;
    _language = widget.initial?.language ?? 'vi';
    _style = widget.initial?.style ?? 'formal';
    _extraRulesController = TextEditingController(
      text: widget.initial?.userExtraRules ?? '',
    );
    _promptCheckToken = widget.initial?.promptCheckToken;
  }

  @override
  void dispose() {
    _extraRulesController.dispose();
    super.dispose();
  }

  Future<void> _checkPrompt() async {
    final promptText = _extraRulesController.text.trim();
    if (promptText.isEmpty) {
      await showBrowserAlert(
        context,
        'Vui lòng nhập yêu cầu bổ sung trước khi kiểm tra prompt.',
      );
      return;
    }
    setState(() {
      _checkingPrompt = true;
      _promptCheckToken = null;
    });
    final result = await checkPromptPreflight(
      scope: 'summary',
      context: 'document_summary',
      promptRole: 'extra_instruction',
      promptText: promptText,
      targetId: widget.documentId,
    );
    if (!mounted) return;
    if (_extraRulesController.text.trim() != promptText) {
      setState(() {
        _checkingPrompt = false;
        _promptCheckToken = null;
      });
      return;
    }
    setState(() {
      _checkingPrompt = false;
      _promptCheckToken = result.passed ? result.promptCheckToken : null;
    });
    if (!result.passed) {
      await showBrowserAlert(context, promptPreflightFailureMessage(result));
    }
  }

  static const _wordOptions = [100, 200, 300, 500, 800, 1200, 1500];

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: Row(children: const [
        Icon(Icons.tune, size: 20, color: Color(0xFF2563EB)),
        SizedBox(width: 8),
        Expanded(child: Text('Tuỳ chọn tóm tắt nhanh')),
      ]),
      content: SizedBox(
        width: 460,
        child: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text('Giới hạn số từ',
                  style: TextStyle(fontWeight: FontWeight.w600, fontSize: 13)),
              const SizedBox(height: 6),
              DropdownButtonFormField<int>(
                value: _maxWords,
                isDense: true,
                isExpanded: true,
                decoration: const InputDecoration(
                  border: OutlineInputBorder(),
                  isDense: true,
                  contentPadding:
                      EdgeInsets.symmetric(horizontal: 10, vertical: 10),
                ),
                items: _wordOptions
                    .map((n) => DropdownMenuItem<int>(
                          value: n,
                          child:
                              Text('≤ $n từ${n == 300 ? ' (mặc định)' : ''}'),
                        ))
                    .toList(),
                onChanged: (v) => setState(() => _maxWords = v ?? 300),
              ),
              const SizedBox(height: 14),
              const Text('Ngôn ngữ',
                  style: TextStyle(fontWeight: FontWeight.w600, fontSize: 13)),
              const SizedBox(height: 6),
              DropdownButtonFormField<String>(
                value: _language,
                isDense: true,
                isExpanded: true,
                decoration: const InputDecoration(
                  border: OutlineInputBorder(),
                  isDense: true,
                  contentPadding:
                      EdgeInsets.symmetric(horizontal: 10, vertical: 10),
                ),
                items: const [
                  DropdownMenuItem(value: 'vi', child: Text('Tiếng Việt')),
                  DropdownMenuItem(value: 'en', child: Text('Tiếng Anh')),
                  DropdownMenuItem(
                      value: 'source',
                      child: Text('Theo ngôn ngữ gốc của văn bản')),
                ],
                onChanged: (v) => setState(() => _language = v ?? 'vi'),
              ),
              const SizedBox(height: 14),
              const Text('Phong cách',
                  style: TextStyle(fontWeight: FontWeight.w600, fontSize: 13)),
              const SizedBox(height: 6),
              DropdownButtonFormField<String>(
                value: _style,
                isDense: true,
                isExpanded: true,
                decoration: const InputDecoration(
                  border: OutlineInputBorder(),
                  isDense: true,
                  contentPadding:
                      EdgeInsets.symmetric(horizontal: 10, vertical: 10),
                ),
                items: const [
                  DropdownMenuItem(
                      value: 'formal', child: Text('Trang trọng (mặc định)')),
                  DropdownMenuItem(
                      value: 'executive',
                      child: Text('Điều hành — mục đích, tác động, rủi ro')),
                  DropdownMenuItem(
                      value: 'bullet',
                      child: Text('Gạch đầu dòng — dễ quét nhanh')),
                  DropdownMenuItem(
                      value: 'action_items',
                      child: Text('Việc cần làm — danh sách action items')),
                ],
                onChanged: (v) => setState(() => _style = v ?? 'formal'),
              ),
              const SizedBox(height: 14),
              const Text(
                'Tùy chỉnh prompt (không bắt buộc)',
                style: TextStyle(fontWeight: FontWeight.w600, fontSize: 13),
              ),
              const SizedBox(height: 6),
              TextField(
                controller: _extraRulesController,
                minLines: 3,
                maxLines: 5,
                maxLength: 2000,
                onChanged: (_) {
                  setState(() => _promptCheckToken = null);
                },
                decoration: const InputDecoration(
                  hintText:
                      'Ví dụ: Nhấn mạnh rủi ro và các thời hạn cần xử lý.',
                  border: OutlineInputBorder(),
                  alignLabelWithHint: true,
                ),
              ),
              const SizedBox(height: 8),
              Row(
                children: [
                  OutlinedButton.icon(
                    onPressed: _checkingPrompt ||
                            _extraRulesController.text.trim().isEmpty
                        ? null
                        : _checkPrompt,
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
                  const SizedBox(width: 10),
                  if (_extraRulesController.text.trim().isNotEmpty &&
                      (_promptCheckToken ?? '').isEmpty)
                    const Expanded(
                      child: Text(
                        'Phải check đạt trước khi tóm tắt.',
                        style: TextStyle(
                          fontSize: 12,
                          color: Color(0xFFB45309),
                        ),
                      ),
                    ),
                ],
              ),
              const SizedBox(height: 14),
              Container(
                padding: const EdgeInsets.all(10),
                decoration: BoxDecoration(
                  color: Colors.blue.shade50,
                  borderRadius: BorderRadius.circular(6),
                ),
                child: const Row(children: [
                  Icon(Icons.info_outline,
                      size: 16, color: Color(0xFF2563EB)),
                  SizedBox(width: 6),
                  Expanded(
                    child: Text(
                      'AI sẽ tóm tắt với cấu hình này và không vượt quá số từ đã chọn.',
                      style:
                          TextStyle(fontSize: 12, color: Color(0xFF1E40AF)),
                    ),
                  ),
                ]),
              ),
            ],
          ),
        ),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.of(context).pop(),
          child: const Text('Huỷ'),
        ),
        FilledButton.icon(
          icon: const Icon(Icons.auto_awesome, size: 16),
          label: const Text('Tóm tắt'),
          onPressed: _checkingPrompt ||
                  (_extraRulesController.text.trim().isNotEmpty &&
                      (_promptCheckToken ?? '').isEmpty)
              ? null
              : () => Navigator.of(context).pop(SummaryOptions(
                    maxWords: _maxWords,
                    language: _language,
                    style: _style,
                    userExtraRules: _extraRulesController.text.trim(),
                    promptCheckToken: _promptCheckToken,
                  )),
        ),
      ],
    );
  }
}
