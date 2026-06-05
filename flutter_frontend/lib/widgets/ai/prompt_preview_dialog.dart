import 'dart:convert';

import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import '../../core/api_client.dart';

class PromptPreviewResult {
  final String previewToken;
  final double score;
  final List<String> flags;
  final List<String> modifications;

  PromptPreviewResult({
    required this.previewToken,
    required this.score,
    required this.flags,
    required this.modifications,
  });
}

class PromptPreviewDialog extends StatefulWidget {
  final int templateId;
  final Map<String, dynamic> variables;
  final String userExtraRules;
  final String? promptId;

  const PromptPreviewDialog({
    super.key,
    required this.templateId,
    required this.variables,
    required this.userExtraRules,
    this.promptId,
  });

  @override
  State<PromptPreviewDialog> createState() => _PromptPreviewDialogState();
}

class _PromptPreviewDialogState extends State<PromptPreviewDialog> {
  bool _loading = true;
  String? _error;
  Map<String, dynamic>? _data;
  String? _previewToken;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final resp = await ApiClient().dio.post(
        'ai/doc/preview-prompt/',
        data: {
          'template_id': widget.templateId,
          'variables': widget.variables,
          'user_extra_rules': widget.userExtraRules,
          if (widget.promptId != null) 'prompt_id': widget.promptId,
        },
      );
      setState(() {
        _data = Map<String, dynamic>.from(resp.data as Map);
        _previewToken = _data!['preview_token'] as String?;
        _loading = false;
      });
    } on DioException catch (e) {
      final data = e.response?.data;
      String msg = 'Không xem trước được prompt';
      String? incidentId;
      if (data is Map) {
        msg = (data['detail'] ?? msg).toString();
        incidentId = data['incident_id']?.toString();
      }
      setState(() {
        _error = incidentId != null ? '$msg (su co: $incidentId)' : msg;
        _loading = false;
      });
    } catch (e) {
      setState(() {
        _error = e.toString();
        _loading = false;
      });
    }
  }

  Widget _buildSegment(Map<String, dynamic> seg) {
    final type = seg['type'] as String? ?? 'unknown';
    final masked = seg['masked'] == true;
    final label = (seg['label'] ?? type) as String;
    final preview = (seg['preview'] ?? '') as String;
    final trust = seg['trust'] as String?;

    Color bg;
    Color border;
    IconData icon;
    if (type == 'user_rules') {
      bg = Colors.blue.shade50;
      border = Colors.blue.shade300;
      icon = Icons.edit;
    } else if (masked) {
      bg = Colors.grey.shade300;
      border = Colors.grey.shade500;
      icon = Icons.lock_outline;
    } else {
      bg = Colors.grey.shade100;
      border = Colors.grey.shade400;
      icon = Icons.description_outlined;
    }

    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: bg,
        border: Border.all(color: border),
        borderRadius: BorderRadius.circular(6),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(icon, size: 16, color: border),
              const SizedBox(width: 6),
              Expanded(
                child: Text(
                  label,
                  style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 13),
                ),
              ),
              if (trust == 'untrusted')
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                  decoration: BoxDecoration(
                    color: Colors.orange.shade100,
                    borderRadius: BorderRadius.circular(4),
                  ),
                  child: const Text(
                    'Untrusted - cach ly',
                    style: TextStyle(fontSize: 10, color: Colors.deepOrange),
                  ),
                ),
            ],
          ),
          const SizedBox(height: 8),
          SelectableText(
            preview,
            style: const TextStyle(fontSize: 12, fontFamily: 'monospace'),
          ),
        ],
      ),
    );
  }

  Widget _buildSanitizeReport(Map<String, dynamic> report) {
    final score = (report['score'] as num?)?.toDouble() ?? 0.0;
    final flags = (report['flags'] as List?)?.cast<String>() ?? [];
    final mods = (report['modifications'] as List?)?.cast<String>() ?? [];

    final List<Widget> children = [];

    if (mods.isNotEmpty) {
      children.add(Container(
        padding: const EdgeInsets.all(10),
        margin: const EdgeInsets.only(bottom: 8),
        color: Colors.amber.shade50,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text('Hệ thống đã chỉnh sửa nội dung:',
                style: TextStyle(fontWeight: FontWeight.bold, fontSize: 12)),
            const SizedBox(height: 4),
            ...mods.map((m) => Text('• $m', style: const TextStyle(fontSize: 12))),
          ],
        ),
      ));
    }

    if (score >= 2.0) {
      children.add(Container(
        padding: const EdgeInsets.all(10),
        margin: const EdgeInsets.only(bottom: 8),
        color: Colors.red.shade50,
        child: Row(
          children: [
            const Icon(Icons.warning, color: Colors.red),
            const SizedBox(width: 8),
            Expanded(
              child: Text(
                'Yeu cau co dau hieu rui ro (score=${score.toStringAsFixed(2)}). Vui long don gian hoa.',
                style: const TextStyle(fontSize: 12, color: Colors.red),
              ),
            ),
          ],
        ),
      ));
    }

    if (flags.isNotEmpty) {
      children.add(Wrap(
        spacing: 4,
        runSpacing: 4,
        children: flags
            .map((f) => Chip(
                  label: Text(f, style: const TextStyle(fontSize: 10)),
                  visualDensity: VisualDensity.compact,
                  backgroundColor: Colors.grey.shade200,
                ))
            .toList(),
      ));
    }

    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: children);
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: const Text('Xem prompt cuối trước khi tạo văn bản'),
      content: SizedBox(
        width: 700,
        height: 500,
        child: _loading
            ? const Center(child: CircularProgressIndicator())
            : _error != null
                ? Center(
                    child: Padding(
                      padding: const EdgeInsets.all(16),
                      child: Text(
                        _error!,
                        style: const TextStyle(color: Colors.red),
                        textAlign: TextAlign.center,
                      ),
                    ),
                  )
                : _buildBody(),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.of(context).pop(null),
          child: const Text('Hủy'),
        ),
        if (!_loading && _error == null && _previewToken != null)
          ElevatedButton.icon(
            icon: const Icon(Icons.check),
            label: const Text('Xác nhận & Tạo văn bản'),
            onPressed: () {
              final preview = (_data?['preview'] as Map?) ?? {};
              final report = (preview['sanitize_report'] as Map?) ?? {};
              Navigator.of(context).pop(PromptPreviewResult(
                previewToken: _previewToken!,
                score: (report['score'] as num?)?.toDouble() ?? 0.0,
                flags: ((report['flags'] as List?) ?? []).cast<String>(),
                modifications: ((report['modifications'] as List?) ?? []).cast<String>(),
              ));
            },
          ),
      ],
    );
  }

  Widget _buildVariablesBlock() {
    final vars = widget.variables;
    final entries = vars.entries
        .where((e) => e.value != null && '${e.value}'.trim().isNotEmpty)
        .toList();
    if (entries.isEmpty) return const SizedBox.shrink();
    return Container(
      width: double.infinity,
      margin: const EdgeInsets.only(bottom: 10),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: const Color(0xFFEFF6FF),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: const Color(0xFFBFDBFE)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(children: const [
            Icon(Icons.tune, size: 16, color: Color(0xFF1D4ED8)),
            SizedBox(width: 6),
            Text('Biến đã điền (từ form/nút lựa chọn)',
                style: TextStyle(
                    fontSize: 13,
                    fontWeight: FontWeight.w800,
                    color: Color(0xFF1E3A8A))),
          ]),
          const SizedBox(height: 4),
          const Text(
            'Các giá trị này được nhúng vào template trước khi gửi cho AI.',
            style: TextStyle(fontSize: 11, color: Color(0xFF64748B)),
          ),
          const SizedBox(height: 8),
          Wrap(
            spacing: 6,
            runSpacing: 6,
            children: entries.map((e) {
              final v = '${e.value}';
              final shown = v.length > 80 ? '${v.substring(0, 80)}...' : v;
              return Container(
                padding: const EdgeInsets.symmetric(
                    horizontal: 10, vertical: 6),
                decoration: BoxDecoration(
                  color: Colors.white,
                  borderRadius: BorderRadius.circular(20),
                  border: Border.all(color: const Color(0xFFBFDBFE)),
                ),
                child: RichText(
                  text: TextSpan(
                    style: const TextStyle(
                        fontSize: 11, color: Color(0xFF0F172A)),
                    children: [
                      TextSpan(
                          text: '${e.key}: ',
                          style: const TextStyle(
                              color: Color(0xFF64748B),
                              fontWeight: FontWeight.w600)),
                      TextSpan(
                          text: shown,
                          style: const TextStyle(
                              fontWeight: FontWeight.w700)),
                    ],
                  ),
                ),
              );
            }).toList(),
          ),
        ],
      ),
    );
  }

  Widget _buildJsonPayloadBlock(List segments, int? estTokens) {
    final messages = <Map<String, dynamic>>[];
    for (final raw in segments) {
      final seg = Map<String, dynamic>.from(raw as Map);
      final type = (seg['type'] ?? '').toString();
      final label = (seg['label'] ?? type).toString();
      final content = (seg['preview'] ?? '').toString();
      if (type == 'user_rules') {
        messages.add({
          'role': 'user',
          'content_kind': label,
          'content': content,
        });
      } else {
        messages.add({
          'role': 'system',
          'content_kind': label,
          'content': '••• [ẩn vì lý do bảo mật hệ thống] •••',
          'redacted': true,
        });
      }
    }
    final filledVars = <String, dynamic>{};
    widget.variables.forEach((k, v) {
      if (v != null && '$v'.trim().isNotEmpty) filledVars[k] = '$v';
    });
    final payload = <String, dynamic>{
      'task': 'fill_template',
      'template_id': widget.templateId,
      'variables': filledVars,
      'messages': messages,
      if (estTokens != null) 'estimated_tokens': estTokens,
    };
    final jsonStr = const JsonEncoder.withIndent('  ').convert(payload);
    return Container(
      width: double.infinity,
      margin: const EdgeInsets.only(bottom: 10),
      decoration: BoxDecoration(
        color: const Color(0xFF0F172A),
        borderRadius: BorderRadius.circular(10),
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
                  'Payload JSON gui cho AI',
                  style: TextStyle(
                    fontSize: 12.5,
                    fontWeight: FontWeight.w800,
                    color: Color(0xFFE2E8F0),
                  ),
                ),
              ),
              IconButton(
                visualDensity: VisualDensity.compact,
                tooltip: 'Sao chep JSON',
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
          const Padding(
            padding: EdgeInsets.fromLTRB(12, 0, 12, 10),
            child: Text(
              'Hệ thống "system" được ẩn để bảo mật prompt cốt lõi. Các biến và ý/câu hỏi nhập tay vẫn hiển thị nguyên văn.',
              style: TextStyle(
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

  Widget _buildBody() {
    final preview = (_data?['preview'] as Map?) ?? {};
    final segments = (preview['system_segments'] as List?) ?? [];
    final report = (preview['sanitize_report'] as Map?) ?? {};
    final estTokens = preview['estimated_tokens'] as int?;

    return SingleChildScrollView(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          if (estTokens != null)
            Padding(
              padding: const EdgeInsets.only(bottom: 8),
              child: Text(
                'Token uoc luong: ~$estTokens',
                style: const TextStyle(fontSize: 12, color: Colors.grey),
              ),
            ),
          _buildVariablesBlock(),
          _buildJsonPayloadBlock(segments, estTokens),
          _buildSanitizeReport(Map<String, dynamic>.from(report)),
          ...segments.map((s) => _buildSegment(Map<String, dynamic>.from(s as Map))),
        ],
      ),
    );
  }
}
