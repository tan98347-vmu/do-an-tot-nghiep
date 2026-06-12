// === MÀN HÌNH KẾT QUẢ RAG TỪ TRỢ LÝ ===
// Hiển thị câu trả lời RAG (kèm trích dẫn nguồn) của một phiên trợ lý (_loadResult 'assistant/sessions/<id>/messages/'); _goBack quay lại chat.

// Tệp này dùng để: dựng giao diện và orchestration UI trong flutter_frontend/lib/screens/assistant/assistant_rag_result_screen.dart.
import 'package:flutter/material.dart';
import 'package:flutter_markdown/flutter_markdown.dart';
import 'package:go_router/go_router.dart';

import '../../core/api_client.dart';
import '../../l10n/app_strings.dart';
import '../../models/chat.dart';
import '../../widgets/ai/citation_sections.dart';
import '../../widgets/tasks/task_done_popup.dart';

// Widget màn KẾT QUẢ RAG; nhận assistantSessionId.

class AssistantRagResultScreen extends StatefulWidget {
  final int assistantSessionId;
  final int assistantMessageId;
  final String mode;
  final String? returnTo;
  final String? returnLabel;

  // Widget màn KẾT QUẢ RAG từ trợ lý; nhận assistantSessionId.
  const AssistantRagResultScreen({
    super.key,
    required this.assistantSessionId,
    required this.assistantMessageId,
    required this.mode,
    this.returnTo,
    this.returnLabel,
  });

  @override
  State<AssistantRagResultScreen> createState() => _AssistantRagResultScreenState();
}

// State màn kết quả RAG: tải câu trả lời + nguồn trích dẫn.

class _AssistantRagResultScreenState extends State<AssistantRagResultScreen> {
  bool _loading = true;
  String? _error;
  ChatMessage? _userMessage;
  ChatMessage? _assistantMessage;

  @override
  // Mở màn: nạp kết quả RAG của phiên (_loadResult).
  void initState() {
    super.initState();
    // Gọi 'assistant/sessions/<id>/messages/' lấy câu trả lời RAG + trích dẫn để hiển thị.
    _loadResult();
  }

  // Tải kết quả RAG của phiên ('assistant/sessions/<id>/messages/').

  Future<void> _loadResult() async {
    // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      // Gọi API hoặc tác vụ bất đồng bộ rồi chờ kết quả trước khi cập nhật giao diện.

      final resp = await ApiClient().dio.get(
        'assistant/sessions/${widget.assistantSessionId}/messages/',
      );
      final messages = (resp.data as List<dynamic>)
          .map((item) => ChatMessage.fromJson(Map<String, dynamic>.from(item)))
          .toList();
      final answerIndex = messages.indexWhere(
        (item) => item.id == widget.assistantMessageId && item.role == 'assistant',
      );
      if (answerIndex < 0) {
        throw Exception('Không tìm thấy kết quả hỏi đáp từ trợ lý AI.');
      }

      ChatMessage? userMessage;
      for (var index = answerIndex - 1; index >= 0; index--) {
        if (messages[index].role == 'user') {
          userMessage = messages[index];
          break;
        }
      }

      if (!mounted) return;
      // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

      setState(() {
        _userMessage = userMessage;
        _assistantMessage = messages[answerIndex];
        _loading = false;
      });
    } catch (error) {
      if (!mounted) return;
      // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

      setState(() {
        _loading = false;
        _error = '$error';
      });
    }
  }

  // Tiêu đề hiển thị cho kết quả RAG.
  String _title(BuildContext context) {
    final strings = AppStrings.of(context);
    return widget.mode == 'document'
        ? strings.documentQa
        : strings.pick('Hỏi đáp mẫu văn bản', 'Template Q&A');
  }

  // Phụ đề (mô tả nguồn/ngữ cảnh) của kết quả.
  String _subtitle(BuildContext context) {
    final strings = AppStrings.of(context);
    return widget.mode == 'document'
        ? strings.pick(
            'Kết quả được lấy từ phiên Chat AI và hiển thị theo giao diện hỏi đáp văn bản.',
            'This result comes from AI Chat and is rendered in the document Q&A view.',
          )
        : strings.pick(
            'Kết quả được lấy từ phiên Chat AI và hiển thị theo giao diện hỏi đáp mẫu văn bản.',
            'This result comes from AI Chat and is rendered in the template Q&A view.',
          );
  }

  String get _selfRoute => Uri(
        path: '/chat-rag-result',
        queryParameters: {
          'mode': widget.mode,
          'assistant_session_id': '${widget.assistantSessionId}',
          'assistant_message_id': '${widget.assistantMessageId}',
          if (widget.returnTo != null) 'return_to': widget.returnTo!,
          if (widget.returnLabel != null) 'return_label': widget.returnLabel!,
        },
      ).toString();

  // Quay lại màn chat trợ lý.
  void _goBack() {
    // Điều hướng người dùng sang màn phù hợp theo kết quả thao tác hiện tại.

    context.go(widget.returnTo ?? '/chat/text');
  }

  @override
  // Dựng màn hiển thị câu trả lời + danh sách nguồn trích dẫn.
  Widget build(BuildContext context) {
    final strings = AppStrings.of(context);

    // Dựng khung màn hình chính để chứa app bar, body, action và các vùng giao diện khác.

    return TaskDonePopupHost(
      child: Scaffold(
        appBar: AppBar(
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: _goBack,
        ),
        title: Text(_title(context)),
      ),
      body: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            TextButton.icon(
              onPressed: _goBack,
              icon: const Icon(Icons.arrow_back),
              label: Text(widget.returnLabel ?? strings.pick('Quay về Chat AI', 'Back to AI Chat')),
            ),
            const SizedBox(height: 8),
            Text(
              _subtitle(context),
              style: TextStyle(
                color: Colors.blueGrey.shade700,
                height: 1.5,
              ),
            ),
            const SizedBox(height: 16),
            Expanded(
              child: _loading
                  ? const Center(child: CircularProgressIndicator())
                  : _error != null
                      ? Center(
                          child: Column(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              const Icon(Icons.error_outline, size: 42, color: Colors.redAccent),
                              const SizedBox(height: 10),
                              Text(
                                _error!,
                                textAlign: TextAlign.center,
                              ),
                              const SizedBox(height: 14),
                              FilledButton.icon(
                                onPressed: _loadResult,
                                icon: const Icon(Icons.refresh),
                                label: Text(strings.pick('Tải lại', 'Reload')),
                              ),
                            ],
                          ),
                        )
                      : ListView(
                          children: [
                            if (_userMessage != null)
                              Align(
                                alignment: Alignment.centerRight,
                                child: Container(
                                  constraints: const BoxConstraints(maxWidth: 760),
                                  margin: const EdgeInsets.only(bottom: 12, left: 40),
                                  padding: const EdgeInsets.all(14),
                                  decoration: BoxDecoration(
                                    color: Theme.of(context).colorScheme.primaryContainer,
                                    borderRadius: BorderRadius.circular(16),
                                  ),
                                  child: Text(
                                    _userMessage!.content,
                                    style: const TextStyle(height: 1.5),
                                  ),
                                ),
                              ),
                            if (_assistantMessage != null)
                              Card(
                                child: Padding(
                                  padding: const EdgeInsets.all(16),
                                  child: Column(
                                    crossAxisAlignment: CrossAxisAlignment.start,
                                    children: [
                                      MarkdownBody(data: _assistantMessage!.content),
                                      if (_assistantMessage!.citations.isNotEmpty) ...[
                                        const SizedBox(height: 12),
                                        Text(
                                          strings.pick('Nguồn tham khảo:', 'Sources:'),
                                          style: const TextStyle(
                                            fontWeight: FontWeight.bold,
                                            fontSize: 12,
                                          ),
                                        ),
                                        const SizedBox(height: 8),
                                        CitationSections(
                                          citations: _assistantMessage!.citations,
                                          returnTo: _selfRoute,
                                          returnLabel: widget.returnLabel ??
                                              strings.pick('Quay về kết quả hỏi đáp', 'Back to Q&A result'),
                                        ),
                                      ],
                                    ],
                                  ),
                                ),
                              ),
                          ],
                        ),
            ),
          ],
        ),
        ),
      ),
    );
  }
}
