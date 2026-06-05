// Tệp này dùng để: dựng giao diện và orchestration UI trong flutter_frontend/lib/screens/assistant/assistant_rag_result_screen.dart.
// Cách hoạt động: nhận state từ provider, dựng widget, phản ứng sự kiện và gửi thao tác ngược về backend khi người dùng tương tác.
// Vai trò trong hệ thống: Đây là màn hình Flutter mà người dùng tương tác trực tiếp.
// Tác dụng khi hệ thống vận hành: biến nghiệp vụ backend thành trải nghiệm thao tác cụ thể trên web.

import 'package:flutter/material.dart';
import 'package:flutter_markdown/flutter_markdown.dart';
import 'package:go_router/go_router.dart';

import '../../core/api_client.dart';
import '../../l10n/app_strings.dart';
import '../../models/chat.dart';
import '../../widgets/ai/citation_sections.dart';
import '../../widgets/tasks/task_done_popup.dart';

// Mục đích: Widget `AssistantRagResultScreen` triển khai phần việc `Assistant Rag Result Screen` trong flutter_frontend/lib/screens/assistant/assistant_rag_result_screen.dart.
// Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
// Vai trò trong hệ thống: Đây là widget thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
// Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

class AssistantRagResultScreen extends StatefulWidget {
  final int assistantSessionId;
  final int assistantMessageId;
  final String mode;
  final String? returnTo;
  final String? returnLabel;

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

// Mục đích: Widget `_AssistantRagResultScreenState` triển khai phần việc `Assistant Rag Result Screen State` trong flutter_frontend/lib/screens/assistant/assistant_rag_result_screen.dart.
// Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
// Vai trò trong hệ thống: Đây là widget thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
// Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

class _AssistantRagResultScreenState extends State<AssistantRagResultScreen> {
  bool _loading = true;
  String? _error;
  ChatMessage? _userMessage;
  ChatMessage? _assistantMessage;

  @override
  // Mục đích: Phương thức `initState` triển khai phần việc `init State` trong flutter_frontend/lib/screens/assistant/assistant_rag_result_screen.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  void initState() {
    super.initState();
    _loadResult();
  }

  // Mục đích: Phương thức `_loadResult` triển khai phần việc `load Result` trong flutter_frontend/lib/screens/assistant/assistant_rag_result_screen.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

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

  // Mục đích: Phương thức `_title` triển khai phần việc `title` trong flutter_frontend/lib/screens/assistant/assistant_rag_result_screen.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  String _title(BuildContext context) {
    final strings = AppStrings.of(context);
    return widget.mode == 'document'
        ? strings.documentQa
        : strings.pick('Hỏi đáp mẫu văn bản', 'Template Q&A');
  }

  // Mục đích: Phương thức `_subtitle` triển khai phần việc `subtitle` trong flutter_frontend/lib/screens/assistant/assistant_rag_result_screen.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

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

  // Mục đích: Phương thức `_goBack` triển khai phần việc `go Back` trong flutter_frontend/lib/screens/assistant/assistant_rag_result_screen.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  void _goBack() {
    // Điều hướng người dùng sang màn phù hợp theo kết quả thao tác hiện tại.

    context.go(widget.returnTo ?? '/chat/text');
  }

  @override
  // Mục đích: Phương thức `build` triển khai phần việc `build` trong flutter_frontend/lib/screens/assistant/assistant_rag_result_screen.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

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
