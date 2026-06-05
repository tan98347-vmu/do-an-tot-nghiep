import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';

import '../../l10n/app_strings.dart';
import '../../models/document.dart';
import '../../models/document_summary.dart';
import '../../models/prompt.dart';
import '../../providers/document_summaries_provider.dart';
import '../../providers/documents_provider.dart';
import '../../providers/prompts_provider.dart';
import '../../widgets/ai/document_summary_prompt_preview_dialog.dart';
import '../../widgets/ai/prompt_picker_dialog.dart';
import '../../widgets/ai/save_prompt_dialog.dart';
// === BEGIN R4: PromptToggleSection import ===
import '../../widgets/ai/prompt_toggle_section.dart';
// === END R4 ===

class DocumentSummaryWorkspaceScreen extends ConsumerStatefulWidget {
  final int documentId;

  const DocumentSummaryWorkspaceScreen({
    super.key,
    required this.documentId,
  });

  @override
  ConsumerState<DocumentSummaryWorkspaceScreen> createState() =>
      _DocumentSummaryWorkspaceScreenState();
}

class _DocumentSummaryWorkspaceScreenState
    extends ConsumerState<DocumentSummaryWorkspaceScreen> {
  final TextEditingController _extraRulesController = TextEditingController();

  DocumentSummaryOptions _options = const DocumentSummaryOptions();
  DocumentSummaryOutput? _summaryOutput;
  Prompt? _selectedPrompt;
  String? _previewToken;
  String? _summaryError;
  bool _previewLoading = false;
  bool _summaryLoading = false;
  String? _summarySourceUpdatedAt;
  DateTime? _summaryGeneratedAt;

  AppStrings get _strings => AppStrings.of(context);
  String _tr(String vi, String en) => _strings.pick(vi, en);

  @override
  void dispose() {
    _extraRulesController.dispose();
    super.dispose();
  }

  String _formatDateTime(String rawValue) {
    try {
      final parsed = DateTime.parse(rawValue).toLocal();
      return DateFormat('dd/MM/yyyy HH:mm').format(parsed);
    } catch (_) {
      return rawValue;
    }
  }

  void _invalidatePreviewToken() {
    if (_previewToken == null) {
      return;
    }
    setState(() {
      _previewToken = null;
    });
  }

  void _updateOptions(DocumentSummaryOptions nextOptions) {
    if (nextOptions == _options) {
      return;
    }
    setState(() {
      _options = nextOptions;
    });
    _invalidatePreviewToken();
  }

  void _setSelectedPrompt(Prompt? prompt) {
    setState(() {
      _selectedPrompt = prompt;
    });
    _invalidatePreviewToken();
  }

  Future<DocumentSummaryPromptPreview?> _openPreviewDialog() async {
    setState(() => _previewLoading = true);
    final preview = await showDialog<DocumentSummaryPromptPreview>(
      context: context,
      builder: (context) => DocumentSummaryPromptPreviewDialog(
        documentId: widget.documentId,
        options: _options,
        userExtraRules: _extraRulesController.text,
        promptId: _selectedPrompt?.id,
        api: ref.read(documentSummaryApiProvider),
      ),
    );
    if (!mounted) {
      return preview;
    }
    setState(() {
      _previewLoading = false;
      if (preview != null) {
        _previewToken = preview.previewToken;
      }
    });
    return preview;
  }

  Future<bool> _ensurePreviewToken() async {
    if (_extraRulesController.text.trim().isEmpty) {
      return true;
    }
    if ((_previewToken ?? '').trim().isNotEmpty) {
      return true;
    }
    final preview = await _openPreviewDialog();
    return preview != null && (_previewToken ?? '').trim().isNotEmpty;
  }

  // === BEGIN R2: M2 download summary ===
  Future<void> _downloadSummary(Document document, String format) async {
    try {
      await ref
          .read(documentSummaryApiProvider)
          .downloadSummary(document.id, format: format);
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(_tr(
            'Đã tải xuống bản tóm tắt (.$format).',
            'Summary downloaded (.$format).',
          )),
          backgroundColor: Colors.green,
        ),
      );
    } on DioException catch (e) {
      if (!mounted) return;
      final d = e.response?.data;
      final detail =
          (d is Map ? d['detail']?.toString() : null) ?? e.message ?? '';
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(_tr(
            'Tải tóm tắt thất bại: $detail',
            'Download failed: $detail',
          )),
          backgroundColor: Colors.red,
        ),
      );
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Lỗi: $e'), backgroundColor: Colors.red),
      );
    }
  }
  // === END R2 ===

  Future<void> _generateSummary(Document document) async {
    if (_summaryLoading) {
      return;
    }
    final hasPreviewToken = await _ensurePreviewToken();
    if (!hasPreviewToken) {
      return;
    }

    setState(() {
      _summaryLoading = true;
      _summaryError = null;
    });

    try {
      final output = await ref.read(documentSummaryApiProvider).generate(
          documentId: document.id,
          options: _options,
          userExtraRules: _extraRulesController.text,
          previewToken: _previewToken,
          promptId: _selectedPrompt?.id,
        );
      if (!mounted) {
        return;
      }
      setState(() {
        _summaryOutput = output;
        if (_selectedPrompt == null &&
            output.selectedPromptId != null &&
            (output.selectedPromptTitle ?? '').isNotEmpty) {
          _selectedPrompt = Prompt(
            id: output.selectedPromptId!,
            title: output.selectedPromptTitle!,
            status: 'approved',
            visibility: 'private',
            ownerName: '',
            createdAt: '',
          );
        }
        _summaryGeneratedAt = DateTime.now();
        _summarySourceUpdatedAt = document.updatedAt;
        _summaryLoading = false;
      });
    } on DioException catch (error) {
      final data = error.response?.data;
      var detail = _tr(
        'Không thể tạo bản tóm tắt lúc này.',
        'Unable to generate the summary right now.',
      );
      if (data is Map && data['detail'] != null) {
        detail = data['detail'].toString();
      }
      if (!mounted) {
        return;
      }
      setState(() {
        _summaryError = detail;
        _summaryLoading = false;
      });
    } catch (error) {
      if (!mounted) {
        return;
      }
      setState(() {
        _summaryError = error.toString();
        _summaryLoading = false;
      });
    }
  }

  Widget _buildOptionGroup({
    required String label,
    required List<_SummaryChoice> choices,
    required String selectedValue,
    required ValueChanged<String> onSelected,
  }) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          label,
          style: Theme.of(context).textTheme.titleSmall?.copyWith(
                fontWeight: FontWeight.w700,
              ),
        ),
        const SizedBox(height: 10),
        Wrap(
          spacing: 10,
          runSpacing: 10,
          children: choices
              .map(
                (choice) => ChoiceChip(
                  label: Text(choice.label),
                  selected: selectedValue == choice.value,
                  onSelected: (_) => onSelected(choice.value),
                ),
              )
              .toList(),
        ),
      ],
    );
  }

  Widget _buildControlPanel(Document document, bool isWide) {
    final previewRequired = _extraRulesController.text.trim().isNotEmpty &&
        (_previewToken ?? '').trim().isEmpty;

    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(24),
        border: Border.all(color: const Color(0xFFE2E8F0)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            _tr('Thiết lập bản tóm tắt', 'Summary controls'),
            style: Theme.of(context).textTheme.titleLarge?.copyWith(
                  fontWeight: FontWeight.w800,
                ),
          ),
          const SizedBox(height: 10),
          Text(
            _tr(
              'Prompt lõi của tính năng được khóa ở backend. Bạn chỉ được bổ sung yêu cầu ở vùng an toàn bên dưới, luôn qua lớp chống prompt injection.',
              'The core prompt stays locked on the backend. You can only add extra instructions in the safe block below, always protected by prompt-injection guardrails.',
            ),
            style: const TextStyle(
              color: Color(0xFF475569),
              height: 1.55,
            ),
          ),
          const SizedBox(height: 18),
          Text(
            _strings.r2_summaryChoosePrompt,
            style: Theme.of(context).textTheme.titleSmall?.copyWith(
                  fontWeight: FontWeight.w700,
                ),
          ),
          const SizedBox(height: 10),
          Wrap(
            spacing: 10,
            runSpacing: 10,
            children: [
              OutlinedButton.icon(
                onPressed: () async {
                  // r1 contract: PromptPickerDialog with scope='summary'
                  final record = await PromptPickerDialog.show(
                    context,
                    scope: 'summary',
                  );
                  if (record != null) {
                    _setSelectedPrompt(Prompt(
                      id: record.id,
                      title: record.title,
                      systemContent: record.systemContent,
                      rulesContent: record.rulesContent,
                      status: record.status,
                      visibility: record.visibility,
                      ownerId: record.ownerId,
                      ownerName: record.ownerName,
                      categoryName: record.categoryName,
                      groupId: record.groupId,
                      groupName: record.groupName,
                      tags: record.tags,
                      source: record.source,
                      usageCount: record.usageCount,
                      approverNote: record.approverNote,
                      isMine: record.isMine,
                      canApprove: record.canApprove,
                      canEdit: record.canEdit,
                      peerShareStatus: record.peerShareStatus,
                      peerAudienceCount: record.peerAudienceCount,
                      isPeerSharedToMe: record.isPeerSharedToMe,
                      createdAt: record.createdAt,
                      updatedAt: record.updatedAt,
                    ));
                  }
                },
                icon: const Icon(Icons.psychology_outlined),
                label: Text(
                  _selectedPrompt == null
                      ? _strings.r2_summaryChoosePrompt
                      : _strings.r2_summarySelectedPrompt(_selectedPrompt!.title),
                ),
              ),
              if (_selectedPrompt != null)
                OutlinedButton.icon(
                  onPressed: () => _setSelectedPrompt(null),
                  icon: const Icon(Icons.clear),
                  label: Text(_strings.r2_summaryClearPrompt),
                ),
              OutlinedButton.icon(
                onPressed: _extraRulesController.text.trim().isEmpty
                    ? null
                    : () async {
                        final text = _extraRulesController.text.trim();
                        if (text.isEmpty) return;
                        final preview = text.length > 60
                            ? '${text.substring(0, 60)}...'
                            : text;
                        final saved = await SavePromptDialog.show(
                          context,
                          initialTitle: 'Prompt tóm tắt: $preview',
                          systemContent: '',
                          rulesContent: text,
                          defaultScopes: const ['summary'],
                        );
                        if (saved != null && mounted) {
                          ScaffoldMessenger.of(context).showSnackBar(
                            SnackBar(
                                content:
                                    Text('Đã lưu prompt: ${saved.title}')),
                          );
                        }
                      },
                icon: const Icon(Icons.bookmark_add_outlined),
                label: const Text('Lưu prompt'),
              ),
            ],
          ),
          const SizedBox(height: 18),
          _buildOptionGroup(
            label: _tr('Độ dài', 'Length'),
            selectedValue: _options.length,
            onSelected: (value) =>
                _updateOptions(_options.copyWith(length: value)),
            choices: [
              _SummaryChoice('brief', _tr('Ngắn', 'Brief')),
              _SummaryChoice('standard', _tr('Chuẩn', 'Standard')),
              _SummaryChoice('detailed', _tr('Chi tiết', 'Detailed')),
            ],
          ),
          const SizedBox(height: 18),
          _buildOptionGroup(
            label: _tr('Ngôn ngữ đầu ra', 'Output language'),
            selectedValue: _options.language,
            onSelected: (value) =>
                _updateOptions(_options.copyWith(language: value)),
            choices: [
              _SummaryChoice('source', _tr('Giữ theo nguồn', 'Match source')),
              _SummaryChoice('vi', _tr('Tiếng Việt', 'Vietnamese')),
              _SummaryChoice('en', _tr('Tiếng Anh', 'English')),
            ],
          ),
          const SizedBox(height: 18),
          _buildOptionGroup(
            label: _tr('Phong cách', 'Style'),
            selectedValue: _options.style,
            onSelected: (value) =>
                _updateOptions(_options.copyWith(style: value)),
            choices: [
              _SummaryChoice('formal', _tr('Trang trọng', 'Formal')),
              _SummaryChoice('executive', _tr('Điều hành', 'Executive')),
              _SummaryChoice('bullet', _tr('Dạng bullet', 'Bullet list')),
              _SummaryChoice(
                  'action_items', _tr('Việc cần làm', 'Action items')),
            ],
          ),
          const SizedBox(height: 18),
          // === BEGIN R4: wrap extra rules editor in toggle ===
          PromptToggleSection(
            storageKey: 'prompt_toggle_summary_workspace',
            labelHidden: _tr('Tùy chỉnh prompt', 'Customize prompt'),
            labelShown: _tr('Ẩn tùy chỉnh', 'Hide customization'),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  _tr('Yêu cầu bổ sung an toàn', 'Safe extra instructions'),
                  style: Theme.of(context).textTheme.titleSmall?.copyWith(
                        fontWeight: FontWeight.w700,
                      ),
                ),
                const SizedBox(height: 10),
                TextField(
                  controller: _extraRulesController,
                  onChanged: (_) {
                    _invalidatePreviewToken();
                    setState(() {});
                  },
                  minLines: 5,
                  maxLines: 8,
                  decoration: InputDecoration(
                    hintText: _tr(
                      'Ví dụ: nhấn mạnh thời hạn, tách riêng rủi ro, hoặc viết ngắn gọn hơn cho lãnh đạo.',
                      'Example: emphasize deadlines, separate risks, or keep the wording shorter for executives.',
                    ),
                    border: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(16),
                    ),
                    filled: true,
                    fillColor: const Color(0xFFF8FAFC),
                  ),
                ),
              ],
            ),
          ),
          // === END R4 ===
          const SizedBox(height: 10),
          if (previewRequired)
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: const Color(0xFFFFFBEB),
                borderRadius: BorderRadius.circular(14),
                border: Border.all(color: const Color(0xFFF59E0B)),
              ),
              child: Text(
                _tr(
                  'Bạn đã chỉnh prompt bổ sung. Hãy preview lại trước khi tạo bản tóm tắt.',
                  'You changed the extra prompt. Preview it again before generating the summary.',
                ),
                style: const TextStyle(color: Color(0xFF92400E)),
              ),
            ),
          const SizedBox(height: 18),
          if (_summaryError != null)
            Container(
              width: double.infinity,
              margin: const EdgeInsets.only(bottom: 14),
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: const Color(0xFFFEF2F2),
                borderRadius: BorderRadius.circular(14),
                border: Border.all(color: const Color(0xFFFCA5A5)),
              ),
              child: Text(
                _summaryError!,
                style: const TextStyle(color: Color(0xFFB91C1C)),
              ),
            ),
          Wrap(
            spacing: 10,
            runSpacing: 10,
            children: [
              OutlinedButton.icon(
                onPressed: _previewLoading ? null : _openPreviewDialog,
                icon: _previewLoading
                    ? const SizedBox(
                        width: 16,
                        height: 16,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      )
                    : const Icon(Icons.visibility_outlined),
                label: Text(_tr('Preview prompt', 'Preview prompt')),
              ),
              FilledButton.icon(
                onPressed:
                    _summaryLoading ? null : () => _generateSummary(document),
                icon: _summaryLoading
                    ? const SizedBox(
                        width: 16,
                        height: 16,
                        child: CircularProgressIndicator(
                          strokeWidth: 2,
                          color: Colors.white,
                        ),
                      )
                    : const Icon(Icons.summarize_outlined),
                label: Text(
                  _summaryLoading
                      ? _tr('Đang tóm tắt...', 'Generating summary...')
                      : _tr('Tạo bản tóm tắt', 'Generate summary'),
                ),
              ),
            ],
          ),
          if (!isWide) ...[
            const SizedBox(height: 16),
            OutlinedButton.icon(
              onPressed: () => context.push('/documents/${document.id}'),
              icon: const Icon(Icons.open_in_new),
              label: Text(_tr('Mở văn bản gốc', 'Open original document')),
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildDocumentSnapshot(Document document) {
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(24),
        border: Border.all(color: const Color(0xFFE2E8F0)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              Chip(label: Text(_tr('Văn bản nguồn', 'Source document'))),
              if ((document.docNumber ?? '').trim().isNotEmpty)
                Chip(label: Text(document.docNumber!.trim())),
              if (document.tags.isNotEmpty)
                ...document.tags
                    .take(4)
                    .map((tag) => Chip(label: Text('#$tag'))),
            ],
          ),
          const SizedBox(height: 12),
          Text(
            document.title,
            style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                  fontWeight: FontWeight.w800,
                  color: const Color(0xFF0F172A),
                ),
          ),
          const SizedBox(height: 10),
          Text(
            _tr(
              'Chủ sở hữu: ${document.ownerName} • Cập nhật ${_formatDateTime(document.updatedAt)}',
              'Owner: ${document.ownerName} • Updated ${_formatDateTime(document.updatedAt)}',
            ),
            style: const TextStyle(
              color: Color(0xFF475569),
            ),
          ),
          const SizedBox(height: 10),
          Text(
            _tr(
              'Workspace này đọc chính document bạn chọn, sau đó áp các tham số tóm tắt và prompt bổ sung an toàn lên cùng một prompt lõi bất biến.',
              'This workspace reads the selected document, then applies summary options and safe extra instructions on top of one immutable core prompt.',
            ),
            style: const TextStyle(
              color: Color(0xFF334155),
              height: 1.55,
            ),
          ),
          const SizedBox(height: 16),
          Wrap(
            spacing: 10,
            runSpacing: 10,
            children: [
              FilledButton.tonalIcon(
                onPressed: () => context.push('/documents/${document.id}'),
                icon: const Icon(Icons.article_outlined),
                label: Text(_tr('Mở văn bản gốc', 'Open original document')),
              ),
              OutlinedButton.icon(
                onPressed: () =>
                    ref.invalidate(documentDetailProvider(document.id)),
                icon: const Icon(Icons.refresh),
                label:
                    Text(_tr('Làm mới dữ liệu nguồn', 'Refresh source data')),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildSummaryOutput(Document document) {
    final output = _summaryOutput;
    final isStale = output != null &&
        _summarySourceUpdatedAt != null &&
        _summarySourceUpdatedAt != document.updatedAt;

    if (_summaryLoading && output == null) {
      return Container(
        padding: const EdgeInsets.all(28),
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(24),
          border: Border.all(color: const Color(0xFFE2E8F0)),
        ),
        child: const Center(child: CircularProgressIndicator()),
      );
    }

    if (output == null) {
      return Container(
        padding: const EdgeInsets.all(28),
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(24),
          border: Border.all(color: const Color(0xFFE2E8F0)),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              _tr('Bản tóm tắt sẽ hiển thị tại đây',
                  'The generated summary will appear here'),
              style: Theme.of(context).textTheme.titleLarge?.copyWith(
                    fontWeight: FontWeight.w800,
                  ),
            ),
            const SizedBox(height: 10),
            Text(
              _tr(
                'Chọn độ dài, ngôn ngữ, phong cách và bấm "Tạo bản tóm tắt". Nếu bạn thêm yêu cầu riêng, hệ thống sẽ bắt preview prompt trước khi gọi AI.',
                'Choose the length, language, and style, then press "Generate summary". If you add custom instructions, the system will require a prompt preview before invoking AI.',
              ),
              style: const TextStyle(
                color: Color(0xFF475569),
                height: 1.6,
              ),
            ),
          ],
        ),
      );
    }

    return Container(
      padding: const EdgeInsets.all(22),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(24),
        border: Border.all(color: const Color(0xFFE2E8F0)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      _tr('Bản tóm tắt hiện tại', 'Current summary'),
                      style: Theme.of(context).textTheme.titleLarge?.copyWith(
                            fontWeight: FontWeight.w800,
                          ),
                    ),
                    const SizedBox(height: 8),
                    Text(
                      _tr(
                        'Nguồn: ${output.sourceKind} • Chunk: ${output.chunkCount} • Cập nhật ${_summaryGeneratedAt == null ? "-" : DateFormat("dd/MM/yyyy HH:mm").format(_summaryGeneratedAt!)}',
                        'Source: ${output.sourceKind} • Chunks: ${output.chunkCount} • Generated ${_summaryGeneratedAt == null ? "-" : DateFormat("dd/MM/yyyy HH:mm").format(_summaryGeneratedAt!)}',
                      ),
                      style: const TextStyle(
                        color: Color(0xFF64748B),
                        fontSize: 12.5,
                      ),
                    ),
                  ],
                ),
              ),
              Wrap(
                spacing: 6,
                children: [
                  // === BEGIN R2: M2 download buttons ===
                  OutlinedButton.icon(
                    onPressed: _summaryLoading
                        ? null
                        : () => _downloadSummary(document, 'docx'),
                    icon: const Icon(Icons.description, size: 16),
                    label: Text(_tr('Tải .docx', 'Download .docx')),
                  ),
                  OutlinedButton.icon(
                    onPressed: _summaryLoading
                        ? null
                        : () => _downloadSummary(document, 'md'),
                    icon: const Icon(Icons.code, size: 16),
                    label: Text(_tr('Tải .md', 'Download .md')),
                  ),
                  // === END R2 ===
                  FilledButton.tonalIcon(
                    onPressed: _summaryLoading
                        ? null
                        : () => _generateSummary(document),
                    icon: const Icon(Icons.refresh),
                    label: Text(_tr('Tóm tắt lại', 'Refresh summary')),
                  ),
                ],
              ),
            ],
          ),
          const SizedBox(height: 14),
          if (isStale)
            Container(
              width: double.infinity,
              margin: const EdgeInsets.only(bottom: 14),
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: const Color(0xFFFFFBEB),
                borderRadius: BorderRadius.circular(14),
                border: Border.all(color: const Color(0xFFF59E0B)),
              ),
              child: Text(
                _tr(
                  'Văn bản nguồn đã thay đổi kể từ lần tóm tắt trước. Hãy tóm tắt lại để đồng bộ nội dung mới nhất.',
                  'The source document changed since the previous summary. Regenerate the summary to sync with the latest content.',
                ),
                style: const TextStyle(color: Color(0xFF92400E)),
              ),
            ),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              Chip(
                  label: Text(_tr('Độ dài: ${output.appliedOptions.length}',
                      'Length: ${output.appliedOptions.length}'))),
              Chip(
                  label: Text(_tr('Ngôn ngữ: ${output.appliedOptions.language}',
                      'Language: ${output.appliedOptions.language}'))),
              Chip(
                  label: Text(_tr('Phong cách: ${output.appliedOptions.style}',
                      'Style: ${output.appliedOptions.style}'))),
            ],
          ),
          const SizedBox(height: 16),
          SelectableText(
            output.summary,
            style: const TextStyle(
              fontSize: 15,
              height: 1.7,
              color: Color(0xFF0F172A),
            ),
          ),
          if (output.guardScore != null || output.guardFlags.isNotEmpty) ...[
            const SizedBox(height: 18),
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(14),
              decoration: BoxDecoration(
                color: const Color(0xFFF8FAFC),
                borderRadius: BorderRadius.circular(16),
                border: Border.all(color: const Color(0xFFE2E8F0)),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    _tr('Báo cáo an toàn cho prompt bổ sung',
                        'Safety report for extra prompt'),
                    style: const TextStyle(
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                  const SizedBox(height: 8),
                  if (output.guardScore != null)
                    Text(
                      _tr(
                        'Điểm guard: ${output.guardScore!.toStringAsFixed(2)}',
                        'Guard score: ${output.guardScore!.toStringAsFixed(2)}',
                      ),
                    ),
                  if (output.guardFlags.isNotEmpty) ...[
                    const SizedBox(height: 8),
                    Wrap(
                      spacing: 8,
                      runSpacing: 8,
                      children: output.guardFlags
                          .map((flag) => Chip(label: Text(flag)))
                          .toList(),
                    ),
                  ],
                  if (output.guardModifications.isNotEmpty) ...[
                    const SizedBox(height: 8),
                    ...output.guardModifications.map((item) => Text('• $item')),
                  ],
                ],
              ),
            ),
          ],
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final documentAsync = ref.watch(documentDetailProvider(widget.documentId));
    final isWide = MediaQuery.sizeOf(context).width >= 1140;

    return Container(
      decoration: const BoxDecoration(
        gradient: LinearGradient(
          colors: [
            Color(0xFFF8FAFC),
            Color(0xFFE0F2FE),
            Color(0xFFDBEAFE),
          ],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
      ),
      child: SafeArea(
        child: RefreshIndicator(
          onRefresh: () =>
              ref.refresh(documentDetailProvider(widget.documentId).future),
          child: SingleChildScrollView(
            physics: const AlwaysScrollableScrollPhysics(),
            padding: EdgeInsets.fromLTRB(
              isWide ? 24 : 16,
              18,
              isWide ? 24 : 16,
              28,
            ),
            child: Center(
              child: ConstrainedBox(
                constraints: const BoxConstraints(maxWidth: 1400),
                child: documentAsync.when(
                  loading: () => const Padding(
                    padding: EdgeInsets.symmetric(vertical: 120),
                    child: Center(child: CircularProgressIndicator()),
                  ),
                  error: (error, _) => Container(
                    padding: const EdgeInsets.all(24),
                    decoration: BoxDecoration(
                      color: Colors.white,
                      borderRadius: BorderRadius.circular(24),
                      border: Border.all(color: const Color(0xFFFCA5A5)),
                    ),
                    child: Column(
                      children: [
                        const Icon(
                          Icons.error_outline,
                          color: Color(0xFFDC2626),
                          size: 36,
                        ),
                        const SizedBox(height: 12),
                        Text(
                          _tr(
                            'Không tải được văn bản nguồn cho workspace tóm tắt.',
                            'Unable to load the source document for the summary workspace.',
                          ),
                          textAlign: TextAlign.center,
                        ),
                        const SizedBox(height: 8),
                        Text(
                          error.toString(),
                          textAlign: TextAlign.center,
                          style: const TextStyle(color: Color(0xFFB91C1C)),
                        ),
                      ],
                    ),
                  ),
                  data: (document) {
                    final content = <Widget>[
                      Text(
                        _tr('Workspace tóm tắt văn bản',
                            'Document summary workspace'),
                        style: Theme.of(context)
                            .textTheme
                            .headlineMedium
                            ?.copyWith(
                              fontWeight: FontWeight.w800,
                              color: const Color(0xFF0F172A),
                            ),
                      ),
                      const SizedBox(height: 10),
                      Text(
                        _tr(
                          'Tinh chỉnh độ dài, ngôn ngữ, phong cách và prompt bổ sung an toàn cho riêng văn bản này.',
                          'Tune length, language, style, and safe extra instructions for this specific document.',
                        ),
                        style: const TextStyle(
                          color: Color(0xFF334155),
                          height: 1.6,
                        ),
                      ),
                      const SizedBox(height: 18),
                      _buildDocumentSnapshot(document),
                      const SizedBox(height: 18),
                    ];

                    if (isWide) {
                      content.add(
                        Row(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            SizedBox(
                              width: 420,
                              child: _buildControlPanel(document, true),
                            ),
                            const SizedBox(width: 18),
                            Expanded(child: _buildSummaryOutput(document)),
                          ],
                        ),
                      );
                    } else {
                      content.addAll([
                        _buildControlPanel(document, false),
                        const SizedBox(height: 18),
                        _buildSummaryOutput(document),
                      ]);
                    }

                    return Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: content,
                    );
                  },
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class _SummaryChoice {
  final String value;
  final String label;

  const _SummaryChoice(this.value, this.label);
}
