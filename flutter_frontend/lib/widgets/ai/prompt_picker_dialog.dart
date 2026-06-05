import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../providers/prompts_provider.dart';

class PromptPickerDialog extends ConsumerStatefulWidget {
  final String scope;
  final bool ownerOnly;

  const PromptPickerDialog({
    super.key,
    required this.scope,
    this.ownerOnly = false,
  });

  static Future<PromptRecord?> show(
    BuildContext context, {
    required String scope,
    bool ownerOnly = false,
  }) {
    return showDialog<PromptRecord>(
      context: context,
      builder: (_) => PromptPickerDialog(scope: scope, ownerOnly: ownerOnly),
    );
  }

  @override
  ConsumerState<PromptPickerDialog> createState() => _PromptPickerDialogState();
}

class _PromptPickerDialogState extends ConsumerState<PromptPickerDialog> {
  final _searchCtrl = TextEditingController();
  String _query = '';

  @override
  void dispose() {
    _searchCtrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final promptsAsync = ref.watch(
      promptQueryProvider(
        PromptListQuery(
          scopes: [widget.scope],
          owner: widget.ownerOnly ? 'mine' : 'all',
        ),
      ),
    );

    return AlertDialog(
      title: const Text('Chọn prompt đã lưu'),
      content: SizedBox(
        width: 680,
        height: 520,
        child: Column(
          children: [
            TextField(
              controller: _searchCtrl,
              decoration: const InputDecoration(
                hintText: 'Tìm theo tên, owner, rules...',
                prefixIcon: Icon(Icons.search),
                border: OutlineInputBorder(),
                isDense: true,
              ),
              onChanged: (value) => setState(() => _query = value.trim().toLowerCase()),
            ),
            const SizedBox(height: 12),
            Expanded(
              child: promptsAsync.when(
                loading: () => const Center(child: CircularProgressIndicator()),
                error: (error, _) => Center(
                  child: Text('Lỗi: $error', style: const TextStyle(color: Colors.red)),
                ),
                data: (prompts) {
                  final filtered = prompts.where((prompt) {
                    if (_query.isEmpty) return true;
                    final haystack = [
                      prompt.title,
                      prompt.ownerName,
                      prompt.rulesContent ?? '',
                      prompt.systemContent ?? '',
                      prompt.tags ?? '',
                    ].join(' ').toLowerCase();
                    return haystack.contains(_query);
                  }).toList();

                  if (filtered.isEmpty) {
                    return const Center(
                      child: Text('Không có prompt nào khớp bộ lọc.'),
                    );
                  }

                  return ListView.separated(
                    itemCount: filtered.length,
                    separatorBuilder: (_, __) => const Divider(height: 1),
                    itemBuilder: (_, index) {
                      final prompt = filtered[index];
                      return ListTile(
                        contentPadding: const EdgeInsets.symmetric(horizontal: 4, vertical: 4),
                        title: Text(
                          prompt.title,
                          style: const TextStyle(fontWeight: FontWeight.w600),
                        ),
                        subtitle: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            const SizedBox(height: 4),
                            Text(
                              prompt.rulesContent ?? prompt.systemContent ?? '',
                              maxLines: 3,
                              overflow: TextOverflow.ellipsis,
                            ),
                            const SizedBox(height: 6),
                            Wrap(
                              spacing: 6,
                              runSpacing: 6,
                              children: [
                                _badge(prompt.visibilityLabel, Colors.blue),
                                _badge(prompt.statusLabel, Colors.green),
                                _badge('Owner: ${prompt.ownerName}', Colors.grey),
                              ],
                            ),
                          ],
                        ),
                        onTap: () => Navigator.of(context).pop(prompt),
                      );
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
          onPressed: () => Navigator.of(context).pop(),
          child: const Text('Đóng'),
        ),
      ],
    );
  }

  Widget _badge(String label, Color color) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
      decoration: BoxDecoration(
        color: color.withOpacity(0.1),
        borderRadius: BorderRadius.circular(999),
      ),
      child: Text(
        label,
        style: TextStyle(fontSize: 11, color: color, fontWeight: FontWeight.w600),
      ),
    );
  }
}
