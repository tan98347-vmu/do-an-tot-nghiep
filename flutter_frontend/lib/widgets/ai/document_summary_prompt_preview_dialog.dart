import 'dart:convert';

import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../../l10n/app_strings.dart';
import '../../models/document_summary.dart';
import '../../providers/document_summaries_provider.dart';

class DocumentSummaryPromptPreviewDialog extends StatefulWidget {
  final int documentId;
  final DocumentSummaryOptions options;
  final String userExtraRules;
  final int? promptId;
  final DocumentSummaryApi api;

  const DocumentSummaryPromptPreviewDialog({
    super.key,
    required this.documentId,
    required this.options,
    required this.userExtraRules,
    this.promptId,
    required this.api,
  });

  @override
  State<DocumentSummaryPromptPreviewDialog> createState() =>
      _DocumentSummaryPromptPreviewDialogState();
}

class _DocumentSummaryPromptPreviewDialogState
    extends State<DocumentSummaryPromptPreviewDialog> {
  bool _loading = true;
  String? _error;
  DocumentSummaryPromptPreview? _preview;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final preview = await widget.api.preview(
        documentId: widget.documentId,
        options: widget.options,
        userExtraRules: widget.userExtraRules,
        promptId: widget.promptId,
      );
      if (!mounted) {
        return;
      }
      setState(() {
        _preview = preview;
        _loading = false;
      });
    } on DioException catch (error) {
      final data = error.response?.data;
      var detail = 'Khong xem truoc duoc prompt tom tat.';
      if (data is Map && data['detail'] != null) {
        detail = data['detail'].toString();
      }
      if (!mounted) {
        return;
      }
      setState(() {
        _error = detail;
        _loading = false;
      });
    } catch (error) {
      if (!mounted) {
        return;
      }
      setState(() {
        _error = error.toString();
        _loading = false;
      });
    }
  }

  Widget _buildOptionsBlock(AppStrings strings) {
    final preview = _preview;
    if (preview == null) return const SizedBox.shrink();
    final opts = preview.options;
    String lengthLabel = switch (opts.length) {
      'brief' => strings.pick('Ngắn gọn', 'Brief'),
      'standard' => strings.pick('Tiêu chuẩn', 'Standard'),
      'detailed' => strings.pick('Chi tiết', 'Detailed'),
      _ => opts.length,
    };
    String languageLabel = switch (opts.language) {
      'source' => strings.pick('Giữ ngôn ngữ gốc', 'Keep source language'),
      'vi' => strings.pick('Dịch sang tiếng Việt', 'Translate to Vietnamese'),
      'en' => strings.pick('Dịch sang tiếng Anh', 'Translate to English'),
      _ => opts.language,
    };
    String styleLabel = switch (opts.style) {
      'formal' => strings.pick('Trang trọng', 'Formal'),
      'casual' => strings.pick('Thân thiện', 'Casual'),
      'bullet' => strings.pick('Gạch đầu dòng', 'Bullet points'),
      _ => opts.style,
    };
    final chips = <_OptChip>[
      _OptChip(
          icon: Icons.straighten,
          title: strings.pick('Độ dài', 'Length'),
          value: lengthLabel),
      _OptChip(
          icon: Icons.translate,
          title: strings.pick('Ngôn ngữ', 'Language'),
          value: languageLabel),
      _OptChip(
          icon: Icons.format_paint_outlined,
          title: strings.pick('Phong cách', 'Style'),
          value: styleLabel),
    ];
    return Container(
      width: double.infinity,
      margin: const EdgeInsets.only(bottom: 12),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: const Color(0xFFF1F5F9),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: const Color(0xFFCBD5E1)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(children: [
            const Icon(Icons.tune_outlined,
                size: 16, color: Color(0xFF334155)),
            const SizedBox(width: 6),
            Text(
              strings.pick(
                  'Tùy chọn bạn đã chọn (từ các nút)', 'Selected options (from buttons)'),
              style: const TextStyle(
                  fontSize: 13,
                  fontWeight: FontWeight.w800,
                  color: Color(0xFF0F172A)),
            ),
          ]),
          const SizedBox(height: 4),
          Text(
            strings.pick(
              'Các giá trị này được nối vào prompt cuối cùng bên dưới.',
              'These values are concatenated into the final prompt below.',
            ),
            style: const TextStyle(fontSize: 11, color: Color(0xFF64748B)),
          ),
          const SizedBox(height: 10),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: chips
                .map(
                  (c) => Container(
                    padding: const EdgeInsets.symmetric(
                        horizontal: 10, vertical: 6),
                    decoration: BoxDecoration(
                      color: Colors.white,
                      borderRadius: BorderRadius.circular(20),
                      border: Border.all(color: const Color(0xFFCBD5E1)),
                    ),
                    child: Row(mainAxisSize: MainAxisSize.min, children: [
                      Icon(c.icon,
                          size: 14, color: const Color(0xFF1D4ED8)),
                      const SizedBox(width: 6),
                      Text('${c.title}: ',
                          style: const TextStyle(
                              fontSize: 11, color: Color(0xFF64748B))),
                      Text(c.value,
                          style: const TextStyle(
                              fontSize: 11,
                              fontWeight: FontWeight.w700,
                              color: Color(0xFF0F172A))),
                    ]),
                  ),
                )
                .toList(),
          ),
        ],
      ),
    );
  }

  Widget _buildJsonPayloadBlock(AppStrings strings) {
    final preview = _preview;
    if (preview == null) return const SizedBox.shrink();
    // Build masked JSON payload — system segments hidden, user inputs in clear.
    final messages = <Map<String, dynamic>>[];
    for (final seg in preview.systemSegments) {
      if (seg.type == 'user_rules') {
        messages.add({
          'role': 'user',
          'content_kind': seg.label,
          'content': seg.preview,
        });
      } else {
        messages.add({
          'role': 'system',
          'content_kind': seg.label,
          'content': '••• [ẩn vì lý do bảo mật hệ thống] •••',
          'redacted': true,
        });
      }
    }
    final opts = preview.options;
    final payload = <String, dynamic>{
      'task': 'summarize_document',
      'options': {
        'length': opts.length,
        'language': opts.language,
        'style': opts.style,
      },
      'source': {
        'kind': preview.sourceKind,
        'length_chars': preview.sourceLength,
        'chunk_count': preview.chunkCount,
      },
      'messages': messages,
    };
    final encoder = const JsonEncoder.withIndent('  ');
    final jsonStr = encoder.convert(payload);

    return Container(
      width: double.infinity,
      margin: const EdgeInsets.only(bottom: 12),
      decoration: BoxDecoration(
        color: const Color(0xFF0F172A),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(12, 10, 8, 6),
            child: Row(children: [
              const Icon(Icons.data_object,
                  size: 16, color: Color(0xFF60A5FA)),
              const SizedBox(width: 6),
              const Expanded(
                child: Text(
                  'Payload JSON gửi cho AI',
                  style: TextStyle(
                    fontSize: 12.5,
                    fontWeight: FontWeight.w800,
                    color: Color(0xFFE2E8F0),
                  ),
                ),
              ),
              Tooltip(
                message: strings.pick(
                    'Sao chép JSON', 'Copy JSON'),
                child: IconButton(
                  visualDensity: VisualDensity.compact,
                  icon: const Icon(Icons.copy,
                      size: 14, color: Color(0xFF94A3B8)),
                  onPressed: () {
                    Clipboard.setData(ClipboardData(text: jsonStr));
                    ScaffoldMessenger.of(context).showSnackBar(
                      const SnackBar(
                        content: Text('Đã copy JSON vào clipboard'),
                        duration: Duration(seconds: 2),
                      ),
                    );
                  },
                ),
              ),
            ]),
          ),
          ConstrainedBox(
            constraints: const BoxConstraints(maxHeight: 220),
            child: SingleChildScrollView(
              padding: const EdgeInsets.fromLTRB(12, 0, 12, 12),
              child: SelectableText(
                jsonStr,
                style: const TextStyle(
                  fontSize: 11.5,
                  height: 1.45,
                  fontFamily: 'monospace',
                  color: Color(0xFFE2E8F0),
                ),
              ),
            ),
          ),
          Padding(
            padding: const EdgeInsets.fromLTRB(12, 0, 12, 10),
            child: Text(
              'Phần "system" được ẩn để bảo mật prompt cốt lõi. Phần "user" + options + source là thông tin bạn cung cấp.',
              style: const TextStyle(
                fontSize: 10.5,
                color: Color(0xFF94A3B8),
                fontStyle: FontStyle.italic,
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildGuardBlock(AppStrings strings) {
    final preview = _preview;
    if (preview == null) {
      return const SizedBox.shrink();
    }

    final widgets = <Widget>[];
    if (preview.guardModifications.isNotEmpty) {
      widgets.add(
        Container(
          width: double.infinity,
          margin: const EdgeInsets.only(bottom: 12),
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(
            color: const Color(0xFFFFF7ED),
            borderRadius: BorderRadius.circular(12),
            border: Border.all(color: const Color(0xFFF59E0B)),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                strings.pick('He thong da lam sach prompt bo sung:',
                    'The system sanitized your extra prompt:'),
                style: const TextStyle(
                  fontWeight: FontWeight.w700,
                  color: Color(0xFF92400E),
                ),
              ),
              const SizedBox(height: 8),
              ...preview.guardModifications.map(
                (item) => Padding(
                  padding: const EdgeInsets.only(bottom: 4),
                  child: Text('• $item'),
                ),
              ),
            ],
          ),
        ),
      );
    }

    if (preview.guardFlags.isNotEmpty) {
      widgets.add(
        Wrap(
          spacing: 8,
          runSpacing: 8,
          children: preview.guardFlags
              .map(
                (item) => Chip(
                  label: Text(item),
                  visualDensity: VisualDensity.compact,
                ),
              )
              .toList(),
        ),
      );
    }

    if (widgets.isEmpty) {
      return const SizedBox.shrink();
    }
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: widgets,
    );
  }

  Widget _buildSegment(
    BuildContext context,
    AppStrings strings,
    DocumentSummaryPreviewSegment segment,
  ) {
    final isUserRules = segment.type == 'user_rules';
    final isUntrusted = segment.trust == 'untrusted';
    final borderColor = isUserRules
        ? const Color(0xFF2563EB)
        : isUntrusted
            ? const Color(0xFFF59E0B)
            : const Color(0xFFCBD5E1);
    final backgroundColor = isUserRules
        ? const Color(0xFFEFF6FF)
        : isUntrusted
            ? const Color(0xFFFFFBEB)
            : const Color(0xFFF8FAFC);

    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: backgroundColor,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: borderColor),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(
                isUserRules
                    ? Icons.edit_note_outlined
                    : isUntrusted
                        ? Icons.shield_outlined
                        : Icons.description_outlined,
                size: 18,
                color: borderColor,
              ),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  segment.label,
                  style: Theme.of(context).textTheme.titleSmall?.copyWith(
                        fontWeight: FontWeight.w700,
                      ),
                ),
              ),
              if (isUntrusted)
                Container(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 8,
                    vertical: 4,
                  ),
                  decoration: BoxDecoration(
                    color: const Color(0xFFFDE68A),
                    borderRadius: BorderRadius.circular(999),
                  ),
                  child: Text(
                    strings.pick('Nguon khong tin cay', 'Untrusted source'),
                    style: const TextStyle(
                      fontSize: 11,
                      fontWeight: FontWeight.w600,
                      color: Color(0xFF92400E),
                    ),
                  ),
                ),
            ],
          ),
          const SizedBox(height: 10),
          SelectableText(
            segment.preview,
            style: const TextStyle(
              fontSize: 12.5,
              height: 1.45,
              fontFamily: 'monospace',
            ),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final strings = AppStrings.of(context);
    return AlertDialog(
      title: Text(
        strings.pick('Xem prompt tom tat cuoi cung', 'Preview summary prompt'),
      ),
      content: SizedBox(
        width: 760,
        height: 540,
        child: _loading
            ? const Center(child: CircularProgressIndicator())
            : _error != null
                ? Center(
                    child: Text(
                      _error!,
                      textAlign: TextAlign.center,
                      style: const TextStyle(color: Color(0xFFB91C1C)),
                    ),
                  )
                : SingleChildScrollView(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        if (_preview != null)
                          Padding(
                            padding: const EdgeInsets.only(bottom: 12),
                            child: Text(
                              strings.pick(
                                'Nguon: ${_preview!.sourceKind} • Do dai: ${_preview!.sourceLength} ky tu • So chunk: ${_preview!.chunkCount}',
                                'Source: ${_preview!.sourceKind} • Length: ${_preview!.sourceLength} chars • Chunks: ${_preview!.chunkCount}',
                              ),
                              style: const TextStyle(
                                fontSize: 12,
                                color: Color(0xFF64748B),
                              ),
                            ),
                          ),
                        _buildOptionsBlock(strings),
                        _buildJsonPayloadBlock(strings),
                        _buildGuardBlock(strings),
                        ...?_preview?.systemSegments.map(
                          (segment) => _buildSegment(context, strings, segment),
                        ),
                      ],
                    ),
                  ),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.of(context).pop(),
          child: Text(strings.pick('Dong', 'Close')),
        ),
        if (!_loading && _error == null && _preview != null)
          FilledButton.icon(
            onPressed: () => Navigator.of(context).pop(_preview),
            icon: const Icon(Icons.check_circle_outline),
            label: Text(strings.pick('Xac nhan preview', 'Approve preview')),
          ),
      ],
    );
  }
}

class _OptChip {
  final IconData icon;
  final String title;
  final String value;
  const _OptChip({required this.icon, required this.title, required this.value});
}
