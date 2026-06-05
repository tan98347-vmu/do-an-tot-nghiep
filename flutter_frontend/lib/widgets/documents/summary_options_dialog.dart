import 'package:flutter/material.dart';

class SummaryOptions {
  final int maxWords;
  final String language;
  final String style;

  const SummaryOptions({
    required this.maxWords,
    required this.language,
    required this.style,
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
  final SummaryOptions? initial;

  const SummaryOptionsDialog({super.key, this.initial});

  static Future<SummaryOptions?> show(BuildContext context, {SummaryOptions? initial}) {
    return showDialog<SummaryOptions>(
      context: context,
      builder: (_) => SummaryOptionsDialog(initial: initial),
    );
  }

  @override
  State<SummaryOptionsDialog> createState() => _SummaryOptionsDialogState();
}

class _SummaryOptionsDialogState extends State<SummaryOptionsDialog> {
  late int _maxWords;
  late String _language;
  late String _style;

  @override
  void initState() {
    super.initState();
    _maxWords = widget.initial?.maxWords ?? 300;
    _language = widget.initial?.language ?? 'vi';
    _style = widget.initial?.style ?? 'formal';
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
                contentPadding: EdgeInsets.symmetric(horizontal: 10, vertical: 10),
              ),
              items: _wordOptions
                  .map((n) => DropdownMenuItem<int>(
                        value: n,
                        child: Text('≤ $n từ' + (n == 300 ? ' (mặc định)' : '')),
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
                contentPadding: EdgeInsets.symmetric(horizontal: 10, vertical: 10),
              ),
              items: const [
                DropdownMenuItem(value: 'vi', child: Text('Tiếng Việt')),
                DropdownMenuItem(value: 'en', child: Text('Tiếng Anh')),
                DropdownMenuItem(value: 'source', child: Text('Theo ngôn ngữ gốc của văn bản')),
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
                contentPadding: EdgeInsets.symmetric(horizontal: 10, vertical: 10),
              ),
              items: const [
                DropdownMenuItem(value: 'formal', child: Text('Trang trọng (mặc định)')),
                DropdownMenuItem(value: 'executive', child: Text('Điều hành — mục đích, tác động, rủi ro')),
                DropdownMenuItem(value: 'bullet', child: Text('Gạch đầu dòng — dễ quét nhanh')),
                DropdownMenuItem(value: 'action_items', child: Text('Việc cần làm — danh sách action items')),
              ],
              onChanged: (v) => setState(() => _style = v ?? 'formal'),
            ),
            const SizedBox(height: 14),
            Container(
              padding: const EdgeInsets.all(10),
              decoration: BoxDecoration(
                color: Colors.blue.shade50,
                borderRadius: BorderRadius.circular(6),
              ),
              child: const Row(children: [
                Icon(Icons.info_outline, size: 16, color: Color(0xFF2563EB)),
                SizedBox(width: 6),
                Expanded(
                  child: Text(
                    'AI sẽ tóm tắt với cấu hình này và không vượt quá số từ đã chọn.',
                    style: TextStyle(fontSize: 12, color: Color(0xFF1E40AF)),
                  ),
                ),
              ]),
            ),
          ],
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
          onPressed: () => Navigator.of(context).pop(SummaryOptions(
            maxWords: _maxWords,
            language: _language,
            style: _style,
          )),
        ),
      ],
    );
  }
}
