import 'package:dio/dio.dart';
import 'package:flutter/material.dart';

import '../../core/api_client.dart';
import '../../core/browser_alert.dart';
import '../../providers/prompt_preflight_provider.dart';
import '../../providers/prompts_provider.dart';

class SavePromptDialog extends StatefulWidget {
  final String initialTitle;
  final String systemContent;
  final String rulesContent;
  final List<String> defaultScopes;

  const SavePromptDialog({
    super.key,
    required this.initialTitle,
    required this.systemContent,
    required this.rulesContent,
    required this.defaultScopes,
  });

  static Future<PromptRecord?> show(
    BuildContext context, {
    required String initialTitle,
    required String systemContent,
    required String rulesContent,
    required List<String> defaultScopes,
  }) {
    return showDialog<PromptRecord>(
      context: context,
      builder: (_) => SavePromptDialog(
        initialTitle: initialTitle,
        systemContent: systemContent,
        rulesContent: rulesContent,
        defaultScopes: defaultScopes,
      ),
    );
  }

  @override
  State<SavePromptDialog> createState() => _SavePromptDialogState();
}

class _SavePromptDialogState extends State<SavePromptDialog> {
  late final TextEditingController _titleCtrl;
  late final Set<String> _scopes;
  bool _saving = false;
  bool _checkingPrompt = false;
  String? _promptCheckToken;
  String? _error;

  @override
  void initState() {
    super.initState();
    _titleCtrl = TextEditingController(text: widget.initialTitle);
    _scopes = {...widget.defaultScopes};
    if (_scopes.isEmpty) _scopes.add('template_fill');
  }

  @override
  void dispose() {
    _titleCtrl.dispose();
    super.dispose();
  }

  String get _promptText => [
        widget.systemContent.trim(),
        widget.rulesContent.trim(),
      ].where((part) => part.isNotEmpty).join('\n\n');

  Future<void> _checkPrompt() async {
    final promptText = _promptText;
    if (promptText.isEmpty) {
      await showBrowserAlert(context, 'Vui lòng nhập nội dung prompt trước khi kiểm tra.');
      return;
    }
    setState(() {
      _checkingPrompt = true;
      _error = null;
    });
    final result = await checkPromptPreflight(
      scope: 'saved_prompt',
      context: 'prompt_library',
      promptRole: 'saved_prompt',
      promptText: promptText,
    );
    if (!mounted) return;
    setState(() {
      _checkingPrompt = false;
      _promptCheckToken = result.promptCheckToken;
    });
    if (!result.passed) {
      await showBrowserAlert(context, promptPreflightFailureMessage(result));
    }
  }

  Future<void> _save() async {
    final title = _titleCtrl.text.trim();
    if (title.isEmpty) {
      setState(() => _error = 'Vui lòng nhập tên prompt.');
      return;
    }
    if ((_promptCheckToken ?? '').isEmpty) {
      await showBrowserAlert(context, 'Hãy bấm "Check prompt" và sửa prompt nếu cần trước khi lưu.');
      return;
    }

    setState(() {
      _saving = true;
      _error = null;
    });

    try {
      final resp = await ApiClient().dio.post(
        'prompts/',
        data: {
          'title': title,
          'system_content': widget.systemContent,
          'rules_content': widget.rulesContent,
          'usage_scope': _scopes.toList(),
          'visibility': 'private',
          'prompt_check_token': _promptCheckToken,
        },
      );
      if (!mounted) return;
      Navigator.of(context).pop(
        PromptRecord.fromJson(Map<String, dynamic>.from(resp.data as Map)),
      );
    } on DioException catch (error) {
      final data = error.response?.data;
      String message = error.message ?? 'Khong luu duoc prompt.';
      if (data is Map) {
        if (data['title'] != null) message = data['title'].toString();
        if (data['usage_scope'] != null) message = data['usage_scope'].toString();
        if (data['detail'] != null) message = data['detail'].toString();
      }
      if (!mounted) return;
      setState(() => _error = message);
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: const Text('Lưu prompt mới'),
      content: SizedBox(
        width: 520,
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            if (_error != null)
              Padding(
                padding: const EdgeInsets.only(bottom: 8),
                child: Text(_error!, style: const TextStyle(color: Colors.red)),
              ),
            TextField(
              controller: _titleCtrl,
              maxLength: 120,
              decoration: const InputDecoration(
                labelText: 'Tên prompt *',
                border: OutlineInputBorder(),
              ),
            ),
            const SizedBox(height: 12),
            const Text(
              'Phạm vi sử dụng',
              style: TextStyle(fontWeight: FontWeight.w600),
            ),
            const SizedBox(height: 8),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: promptScopeLabels.entries.map((entry) {
                final selected = _scopes.contains(entry.key);
                return FilterChip(
                  label: Text(entry.value),
                  selected: selected,
                  onSelected: (value) {
                    setState(() {
                      if (value) {
                        _scopes.add(entry.key);
                      } else if (_scopes.length > 1) {
                        _scopes.remove(entry.key);
                      }
                    });
                  },
                );
              }).toList(),
            ),
            const SizedBox(height: 12),
            OutlinedButton.icon(
              onPressed: _checkingPrompt || _saving ? null : _checkPrompt,
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
          ],
        ),
      ),
      actions: [
        TextButton(
          onPressed: _saving ? null : () => Navigator.of(context).pop(),
          child: const Text('Hủy'),
        ),
        FilledButton.icon(
          onPressed: _saving || (_promptCheckToken ?? '').isEmpty
              ? null
              : _save,
          icon: _saving
              ? const SizedBox(
                  width: 14,
                  height: 14,
                  child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white),
                )
              : const Icon(Icons.save, size: 16),
          label: const Text('Lưu prompt'),
        ),
      ],
    );
  }
}
