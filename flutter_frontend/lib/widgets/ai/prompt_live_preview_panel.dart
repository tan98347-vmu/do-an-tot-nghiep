import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../models/composed_prompt.dart';
import '../../providers/prompt_composer_provider.dart';

class PromptLivePreviewPanel extends ConsumerWidget {
  final Map<String, dynamic> options;
  final String extraText;
  final String scope;
  final int? basePromptId;

  const PromptLivePreviewPanel({
    super.key,
    required this.options,
    required this.extraText,
    required this.scope,
    this.basePromptId,
  });

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final args = ComposeArgs(
      scope: scope,
      options: options,
      extra: extraText,
      basePromptId: basePromptId,
    );
    final composedPromptAsync = ref.watch(composerProvider(args));

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Đây là nội dung AI sẽ nhận (không sửa được ở đây — chỉnh ở các tùy chọn phía trên)',
              style: TextStyle(
                fontStyle: FontStyle.italic,
                color: Colors.grey,
              ),
            ),
            const SizedBox(height: 8),
            composedPromptAsync.when(
              data: (composedPrompt) => _PreviewBody(
                composedPrompt: composedPrompt,
                onRetry: () => ref.invalidate(composerProvider(args)),
              ),
              loading: () => Column(
                children: List.generate(
                  3,
                  (_) => Container(
                    height: 16,
                    margin: const EdgeInsets.symmetric(vertical: 4),
                    decoration: BoxDecoration(
                      color: Colors.grey.shade300,
                      borderRadius: BorderRadius.circular(4),
                    ),
                  ),
                ),
              ),
              error: (error, _) => Row(
                children: [
                  const Icon(Icons.error_outline, color: Colors.red),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      'Lỗi: $error',
                      style: const TextStyle(color: Colors.red),
                    ),
                  ),
                  TextButton(
                    onPressed: () => ref.invalidate(composerProvider(args)),
                    child: const Text('Thử lại'),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _PreviewBody extends StatelessWidget {
  final ComposedPrompt composedPrompt;
  final VoidCallback onRetry;

  const _PreviewBody({
    required this.composedPrompt,
    required this.onRetry,
  });

  @override
  Widget build(BuildContext context) {
    if (composedPrompt.isEmpty) {
      return Container(
        width: double.infinity,
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          border: Border.all(color: Colors.grey.shade300),
          borderRadius: BorderRadius.circular(8),
        ),
        child: const Text(
          'Chưa có nội dung prompt được tạo từ các lựa chọn hiện tại.',
          style: TextStyle(color: Color(0xFF64748B)),
        ),
      );
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Container(
          constraints: const BoxConstraints(maxHeight: 320),
          decoration: BoxDecoration(
            border: Border.all(color: Colors.grey.shade300),
            borderRadius: BorderRadius.circular(8),
          ),
          padding: const EdgeInsets.all(12),
          child: SingleChildScrollView(
            child: SelectableText.rich(
              _buildSpans(composedPrompt, context),
            ),
          ),
        ),
        const SizedBox(height: 8),
        Row(
          children: [
            Chip(label: Text('~ ${composedPrompt.tokenEstimate} tokens')),
            const Spacer(),
            TextButton.icon(
              onPressed: () async {
                await Clipboard.setData(
                  ClipboardData(text: composedPrompt.composedText),
                );
                if (!context.mounted) {
                  return;
                }
                ScaffoldMessenger.of(context).showSnackBar(
                  const SnackBar(content: Text('Đã sao chép')),
                );
              },
              icon: const Icon(Icons.copy_outlined),
              label: const Text('Sao chép'),
            ),
          ],
        ),
      ],
    );
  }

  TextSpan _buildSpans(ComposedPrompt prompt, BuildContext context) {
    final spans = <InlineSpan>[];
    for (final section in prompt.sections) {
      spans.add(
        TextSpan(
          text: '### ${section.label}\n',
          style: TextStyle(
            fontFamily: 'monospace',
            fontWeight: FontWeight.bold,
            color: Theme.of(context).colorScheme.primary,
          ),
        ),
      );
      spans.add(
        TextSpan(
          text: '${section.content}\n\n',
          style: const TextStyle(fontFamily: 'monospace'),
        ),
      );
    }
    return TextSpan(
      style: DefaultTextStyle.of(context).style,
      children: spans,
    );
  }
}
