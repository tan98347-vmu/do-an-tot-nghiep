// === MÀN HÌNH CHAT AI (trợ lý văn bản) ===
// Hội thoại với trợ lý: sidebar phiên (_loadSessions 'assistant/sessions/'), _loadMessages, gửi câu hỏi async (_send -> 'assistant/turn-async/', theo dõi tiến độ qua aiTaskProgressProvider).
// - Trợ lý có thể sinh văn bản / hỏi mẫu-tài liệu / chuẩn bị ký nhanh -> _applyAssistantTaskResult mở /documents/<id>, /templates/<id> hoặc chuyển RAG (_fallbackRagRoute).
// - Chọn/lưu prompt (_pickChatSavedPrompt/_saveChatPrompt), đổi model (chatAiModelProvider); link sang voice (/chat/voice).

// Tệp này dùng để: dựng giao diện và orchestration UI trong flutter_frontend/lib/screens/assistant/assistant_chat_screen.dart.
import 'dart:html' as html;

import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_markdown/flutter_markdown.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/api_client.dart';
import '../../core/conversation_bootstrap.dart';
import '../../l10n/app_strings.dart';
import '../../models/ai_task_state.dart';
import '../../models/assistant_quick_sign.dart';
import '../../models/chat.dart';
import '../../providers/ai_task_progress_provider.dart';
import '../../providers/chat_ai_model_provider.dart';
import '../../widgets/ai/chat_attachment_row.dart';
import '../../widgets/ai/prompt_picker_dialog.dart';
import '../../widgets/ai/save_prompt_dialog.dart';
import '../../widgets/ai/citation_sections.dart';
import '../../widgets/ai/chat_history_manager_dialog.dart';
import '../../widgets/ai/prefill_toggle_row.dart';
import '../../widgets/ai_loading/ai_task_circular_progress.dart';
import '../../widgets/tasks/task_done_popup.dart';

// Widget màn CHATAI VĂN BẢN (StatefulWidget).

class AssistantChatScreen extends StatefulWidget {
  final int? conversationId;

  const AssistantChatScreen({
    super.key,
    this.conversationId,
  });

  @override
  State<AssistantChatScreen> createState() => _AssistantChatScreenState();
}

// State màn chat: phiên hội thoại, tin nhắn, tác vụ AI, điều hướng theo kết quả.

class _AssistantChatScreenState extends State<AssistantChatScreen> {
  static const _featureKey = ConversationBootstrapStore.assistantTextFeature;

  final _composerCtrl = TextEditingController();
  final _scrollCtrl = ScrollController();
  final _focusNode = FocusNode();
  List<ChatSession> _sessions = const [];
  List<ChatMessage> _messages = const [];
  int? _activeSessionId;
  String? _pendingTaskId;
  String _pendingAssistantText = '';
  bool _loadingSessions = true;
  bool _loadingMessages = false;
  bool _sending = false;
  bool _autoFillProfile = true;
  bool _autoFillCompany = true;
  final List<ChatAttachmentItem> _pendingAttachments = [];

  ChatSession? get _activeSession {
    for (final session in _sessions) {
      if (session.id == _activeSessionId) return session;
    }
    return null;
  }

  @override
  // Mở màn: nạp phiên hội thoại gần nhất.

  void initState() {
    super.initState();
    _loadSessions(preferredSessionId: widget.conversationId);
  }

  // Nạp danh sách phiên chat (ưu tiên 1 phiên cụ thể nếu có).

  Future<void> _loadSessions({int? preferredSessionId}) async {
    if (!mounted) return;
    // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

    setState(() => _loadingSessions = true);
    try {
      // Gọi API hoặc tác vụ bất đồng bộ rồi chờ kết quả trước khi cập nhật giao diện.

      final resp = await ApiClient().dio.get(
        'assistant/sessions/',
        queryParameters: const {'mode': 'text'},
      );
      final sessions = (resp.data as List<dynamic>)
          .map((item) => ChatSession.fromJson(Map<String, dynamic>.from(item)))
          .toList();
      if (!mounted) return;
      // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

      setState(() {
        _sessions = sessions;
        _loadingSessions = false;
      });
      final shouldStartFresh = preferredSessionId == null &&
          await ConversationBootstrapStore.shouldStartFresh(_featureKey);
      final rememberedSessionId = shouldStartFresh
          ? null
          : await ConversationBootstrapStore.getRememberedSessionId(
              _featureKey);
      final targetSessionId = preferredSessionId != null &&
              sessions.any((item) => item.id == preferredSessionId)
          ? preferredSessionId
          : (_activeSessionId != null &&
                  sessions.any((item) => item.id == _activeSessionId)
              ? _activeSessionId
              : (rememberedSessionId != null &&
                      sessions.any((item) => item.id == rememberedSessionId)
                  ? rememberedSessionId
                  : null));
      if (targetSessionId != null) {
        await _loadMessages(targetSessionId);
      } else {
        // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

        setState(() {
          _activeSessionId = null;
          _messages = const [];
        });
        await ConversationBootstrapStore.rememberSession(_featureKey, null);
        if (shouldStartFresh) {
          await ConversationBootstrapStore.markConversationChosen(_featureKey);
        }
      }
    } catch (error) {
      if (!mounted) return;
      setState(() => _loadingSessions = false);
      // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

      _showError(_readableError(error));
    }
  }

  // Nạp tin nhắn của 1 phiên chat.

  Future<void> _loadMessages(int sessionId) async {
    if (!mounted) return;
    // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

    setState(() {
      _activeSessionId = sessionId;
      _loadingMessages = true;
    });
    try {
      // Gọi API hoặc tác vụ bất đồng bộ rồi chờ kết quả trước khi cập nhật giao diện.

      final resp =
          await ApiClient().dio.get('assistant/sessions/$sessionId/messages/');
      final messages = (resp.data as List<dynamic>)
          .map((item) => ChatMessage.fromJson(Map<String, dynamic>.from(item)))
          .toList();
      if (!mounted) return;
      // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

      setState(() {
        _messages = messages;
        _loadingMessages = false;
      });
      await ConversationBootstrapStore.markConversationChosen(_featureKey);
      await ConversationBootstrapStore.rememberSession(_featureKey, sessionId);
      _scrollToBottom(jump: true);
    } catch (error) {
      if (!mounted) return;
      setState(() => _loadingMessages = false);
      // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

      _showError(_readableError(error));
    }
  }

  // Nút Trò chuyện mới: tạo phiên chat mới.

  Future<void> _newConversation() async {
    // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

    setState(() {
      _activeSessionId = null;
      _messages = const [];
    });
    _composerCtrl.clear();
    _focusNode.requestFocus();
    await ConversationBootstrapStore.markConversationChosen(_featureKey);
    await ConversationBootstrapStore.rememberSession(_featureKey, null);
  }

  // Mở trình quản lý lịch sử chat (đổi tên/xóa phiên).

  Future<void> _openHistoryManager() async {
    final strings = AppStrings.of(context);
    await showChatHistoryManagerDialog(
      context: context,
      title: strings.pick('Lịch sử Chat AI', 'AI chat history'),
      emptyLabel: strings.pick(
        'Chưa có lịch sử Chat AI nào.',
        'No AI chat history yet.',
      ),
      listPath: 'assistant/sessions/',
      deletePath: 'assistant/sessions/',
      messagesPathBuilder: (sessionId) =>
          'assistant/sessions/$sessionId/messages/',
      listQueryParameters: const {'mode': 'text'},
      deleteDataBuilder: (sessionIds) => {
        'mode': 'text',
        'session_ids': sessionIds,
      },
      onOpenSession: (sessionId) => _loadMessages(sessionId),
      onChanged: () => _loadSessions(preferredSessionId: _activeSessionId),
    );
  }

  Future<void> _showSessionPickerSheet() async {
    final strings = AppStrings.of(context);
    if (_loadingSessions) {
      _showError('Đang tải lịch sử hội thoại.');
      return;
    }
    await showModalBottomSheet<void>(
      context: context,
      showDragHandle: true,
      isScrollControlled: true,
      builder: (sheetContext) {
        return SafeArea(
          child: SizedBox(
            height: MediaQuery.sizeOf(sheetContext).height * 0.72,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Padding(
                  padding: const EdgeInsets.fromLTRB(20, 8, 20, 12),
                  child: Row(
                    children: [
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              strings.pick(
                                  'Lịch sử trò chuyện', 'Conversation history'),
                              style: const TextStyle(
                                fontSize: 18,
                                fontWeight: FontWeight.w800,
                              ),
                            ),
                            const SizedBox(height: 4),
                            Text(
                              strings.pick(
                                'Chọn lại cuộc trò chuyện cũ khi cần.',
                                'Pick a previous conversation whenever needed.',
                              ),
                              style: const TextStyle(
                                color: Color(0xFF64748B),
                                height: 1.45,
                              ),
                            ),
                          ],
                        ),
                      ),
                      TextButton.icon(
                        onPressed: () {
                          Navigator.of(sheetContext).pop();
                          _openHistoryManager();
                        },
                        icon: const Icon(Icons.history),
                        label: Text(strings.pick('Quản lý', 'Manage')),
                      ),
                    ],
                  ),
                ),
                Expanded(
                  child: _sessions.isEmpty
                      ? const Center(
                          child: Padding(
                            padding: EdgeInsets.symmetric(horizontal: 24),
                            child: Text(
                              'Chưa có cuộc trò chuyện nào. Hãy bắt đầu một phiên mới.',
                              textAlign: TextAlign.center,
                              style: TextStyle(color: Color(0xFF64748B)),
                            ),
                          ),
                        )
                      : ListView.separated(
                          padding: const EdgeInsets.fromLTRB(16, 0, 16, 20),
                          itemCount: _sessions.length,
                          separatorBuilder: (_, __) =>
                              const SizedBox(height: 10),
                          itemBuilder: (_, index) {
                            final session = _sessions[index];
                            final active = session.id == _activeSessionId;
                            final stamp = session.updatedAt.isNotEmpty
                                ? session.updatedAt
                                : session.createdAt;
                            return Material(
                              color: active
                                  ? const Color(0xFFEFF6FF)
                                  : Colors.white,
                              borderRadius: BorderRadius.circular(18),
                              child: InkWell(
                                borderRadius: BorderRadius.circular(18),
                                onTap: () async {
                                  Navigator.of(sheetContext).pop();
                                  await _loadMessages(session.id);
                                },
                                child: Padding(
                                  padding: const EdgeInsets.all(14),
                                  child: Row(
                                    crossAxisAlignment:
                                        CrossAxisAlignment.start,
                                    children: [
                                      Container(
                                        width: 42,
                                        height: 42,
                                        decoration: BoxDecoration(
                                          color: active
                                              ? const Color(0xFFDBEAFE)
                                              : const Color(0xFFF1F5F9),
                                          borderRadius:
                                              BorderRadius.circular(14),
                                        ),
                                        child: Icon(
                                          active
                                              ? Icons.mark_chat_read_outlined
                                              : Icons.chat_bubble_outline,
                                          color: active
                                              ? const Color(0xFF1D4ED8)
                                              : const Color(0xFF64748B),
                                        ),
                                      ),
                                      const SizedBox(width: 12),
                                      Expanded(
                                        child: Column(
                                          crossAxisAlignment:
                                              CrossAxisAlignment.start,
                                          children: [
                                            Text(
                                              session.title,
                                              maxLines: 2,
                                              overflow: TextOverflow.ellipsis,
                                              style: TextStyle(
                                                fontWeight: FontWeight.w700,
                                                color: active
                                                    ? const Color(0xFF1D4ED8)
                                                    : const Color(0xFF0F172A),
                                              ),
                                            ),
                                            const SizedBox(height: 6),
                                            Text(
                                              strings.pick(
                                                '${session.messageCount} tin nhắn',
                                                '${session.messageCount} messages',
                                              ),
                                              style: const TextStyle(
                                                fontSize: 12.5,
                                                color: Color(0xFF64748B),
                                              ),
                                            ),
                                            const SizedBox(height: 4),
                                            Text(
                                              stamp.replaceFirst('T', ' '),
                                              maxLines: 1,
                                              overflow: TextOverflow.ellipsis,
                                              style: const TextStyle(
                                                fontSize: 11.5,
                                                color: Color(0xFF94A3B8),
                                              ),
                                            ),
                                          ],
                                        ),
                                      ),
                                      if (active)
                                        const Padding(
                                          padding: EdgeInsets.only(left: 8),
                                          child: Icon(
                                            Icons.check_circle_rounded,
                                            color: Color(0xFF2563EB),
                                            size: 20,
                                          ),
                                        ),
                                    ],
                                  ),
                                ),
                              ),
                            );
                          },
                        ),
                ),
              ],
            ),
          ),
        );
      },
    );
  }

  Future<void> _showMobileActionsSheet() async {
    final strings = AppStrings.of(context);
    await showModalBottomSheet<void>(
      context: context,
      showDragHandle: true,
      builder: (sheetContext) {
        return SafeArea(
          child: Padding(
            padding: const EdgeInsets.fromLTRB(16, 8, 16, 20),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                ListTile(
                  leading: const Icon(Icons.history),
                  title: Text(strings.pick(
                      'Lịch sử trò chuyện', 'Conversation history')),
                  subtitle: Text(strings.pick('Mở lại các cuộc trò chuyện cũ',
                      'Reopen previous conversations')),
                  onTap: () {
                    Navigator.of(sheetContext).pop();
                    _showSessionPickerSheet();
                  },
                ),
                ListTile(
                  leading: const Icon(Icons.manage_history_outlined),
                  title:
                      Text(strings.pick('Quản lý lịch sử', 'Manage history')),
                  subtitle: Text(strings.pick(
                      'Xem, mở và xóa nhiều phiên trò chuyện',
                      'Review, open, and remove multiple conversations')),
                  onTap: () {
                    Navigator.of(sheetContext).pop();
                    _openHistoryManager();
                  },
                ),
                ListTile(
                  leading: const Icon(Icons.mic_none_outlined),
                  title: Text(strings.pick(
                      'Chuyển sang giọng nói AI', 'Switch to AI voice')),
                  subtitle: Text(strings.pick(
                      'Mở chế độ tương tác bằng giọng nói',
                      'Open the voice interaction mode')),
                  onTap: () {
                    Navigator.of(sheetContext).pop();
                    context.go('/chat/voice');
                  },
                ),
              ],
            ),
          ),
        );
      },
    );
  }

  // Xử lý kết quả tác vụ trợ lý: hiển thị trả lời + điều hướng/thẻ hành động (RAG/ký nhanh...).

  void _applyAssistantTaskResult(Map<String, dynamic> result) {
    final rawSession = result['session'];
    final rawMessage = result['message'];
    final rawAction = result['action'];
    if (rawSession is! Map || rawMessage is! Map) {
      _handlePendingTaskFailure(
        AppStrings.of(context).pick(
          'Phan hoi task tro ly khong hop le.',
          'The assistant task response is invalid.',
        ),
      );
      return;
    }
    final session = ChatSession.fromJson(Map<String, dynamic>.from(rawSession));
    final message = ChatMessage.fromJson(Map<String, dynamic>.from(rawMessage));
    final action = rawAction is Map
        ? Map<String, dynamic>.from(rawAction)
        : const <String, dynamic>{};
    setState(() {
      _activeSessionId = session.id;
      _sessions = [session, ..._sessions.where((item) => item.id != session.id)];
      _messages = [..._messages, message];
      _pendingTaskId = null;
      _pendingAssistantText = '';
      _sending = false;
    });
    ConversationBootstrapStore.markConversationChosen(_featureKey);
    ConversationBootstrapStore.rememberSession(_featureKey, session.id);
    _scrollToBottom();

    final payload = message.payload ?? const <String, dynamic>{};
    final payloadKind = '${payload['kind'] ?? ''}'.trim();
    final actionType = '${action['type'] ?? ''}'.trim();
    if (actionType == 'open_rag_result' || payloadKind == 'rag_result') {
      final target = '${action['route'] ?? ''}'.trim().isNotEmpty
          ? '${action['route']}'
          : _fallbackRagRoute(payload);
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (!mounted || target.isEmpty) return;
        context.go(target);
      });
    }
  }

  void _handlePendingTaskComplete(AITaskState state) {
    final result = state.result;
    if (result == null) {
      _handlePendingTaskFailure(
        AppStrings.of(context).pick(
          'Task tro ly khong tra ve noi dung.',
          'The assistant task returned no result.',
        ),
      );
      return;
    }
    if (!mounted) return;
    _applyAssistantTaskResult(result);
  }

  void _handlePendingTaskCancelled() {
    if (!mounted) return;
    setState(() {
      _pendingTaskId = null;
      _sending = false;
      if (_pendingAssistantText.trim().isNotEmpty) {
        _messages = [
          ..._messages,
          ChatMessage(
            id: -DateTime.now().millisecondsSinceEpoch - 2,
            role: 'assistant',
            content: _pendingAssistantText.trim(),
            citations: const [],
            createdAt: '',
            payload: const {'kind': 'cancelled_stream', 'status': 'cancelled'},
          ),
        ];
      }
      _pendingAssistantText = '';
    });
    _scrollToBottom();
  }

  void _handlePendingTaskFailure(String message) {
    if (!mounted) return;
    setState(() {
      _pendingTaskId = null;
      _pendingAssistantText = '';
      _sending = false;
      _messages = [
        ..._messages,
        ChatMessage(
          id: -DateTime.now().millisecondsSinceEpoch - 1,
          role: 'assistant',
          content: message,
          citations: const [],
          createdAt: '',
        ),
      ];
    });
    _scrollToBottom();
  }

  Future<void> _pickChatSavedPrompt() async {
    final picked = await PromptPickerDialog.show(context, scope: 'chat');
    if (picked == null || !mounted) return;
    final sys = (picked.systemContent ?? '').trim();
    final rules = (picked.rulesContent ?? '').trim();
    final body = [
      if (sys.isNotEmpty) sys,
      if (rules.isNotEmpty) rules,
    ].join('\n\n').trim();
    if (body.isEmpty) return;
    setState(() {
      final existing = _composerCtrl.text.trim();
      _composerCtrl.text = existing.isEmpty ? body : '$existing\n\n$body';
    });
    _focusNode.requestFocus();
  }

  Future<void> _saveChatPrompt() async {
    final text = _composerCtrl.text.trim();
    if (text.isEmpty) return;
    final preview = text.length > 60 ? '${text.substring(0, 60)}...' : text;
    final saved = await SavePromptDialog.show(
      context,
      initialTitle: 'Prompt chat AI: $preview',
      systemContent: '',
      rulesContent: text,
      defaultScopes: const ['chat'],
    );
    if (saved == null || !mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text('Đã lưu prompt: ${saved.title}')),
    );
  }

  Future<void> _send() async {
    final text = _composerCtrl.text.trim();
    if (text.isEmpty || _sending) return;

    // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

    setState(() {
      _sending = true;
      _messages = [
        ..._messages,
        ChatMessage(
          id: -DateTime.now().millisecondsSinceEpoch,
          role: 'user',
          content: text,
          citations: const [],
          createdAt: '',
        ),
      ];
    });
    _composerCtrl.clear();
    _scrollToBottom();

    try {
      // Gọi API hoặc tác vụ bất đồng bộ rồi chờ kết quả trước khi cập nhật giao diện.

      final attachmentsSnapshot =
          List<ChatAttachmentItem>.from(_pendingAttachments);
      setState(() => _pendingAttachments.clear());

      Response<dynamic> resp;
      if (attachmentsSnapshot.isNotEmpty) {
        final pdfFiles = <MultipartFile>[];
        final imageFiles = <MultipartFile>[];
        for (final a in attachmentsSnapshot) {
          final mp = MultipartFile.fromBytes(a.bytes, filename: a.name);
          if (a.isPdf) {
            pdfFiles.add(mp);
          } else {
            imageFiles.add(mp);
          }
        }
        final fields = <String, dynamic>{
          'input': text,
          'mode': 'text',
          if (_activeSessionId != null) 'session_id': _activeSessionId,
          'auto_fill_profile': _autoFillProfile.toString(),
          'auto_fill_company': _autoFillCompany.toString(),
          if (pdfFiles.isNotEmpty) 'attachment_pdfs': pdfFiles,
          if (imageFiles.isNotEmpty) 'attachment_images': imageFiles,
        };
        resp = await ApiClient().dio.post(
              'assistant/turn-async/',
              data: FormData.fromMap(fields, ListFormat.multiCompatible),
            );
      } else {
        resp = await ApiClient().dio.post(
              'assistant/turn-async/',
              data: {
                'input': text,
                'mode': 'text',
                if (_activeSessionId != null) 'session_id': _activeSessionId,
                'auto_fill_profile': _autoFillProfile,
                'auto_fill_company': _autoFillCompany,
              },
            );
      }
      final taskId = '${resp.data['task_id'] ?? ''}'.trim();
      final sessionId = resp.data['session_id'] as int?;
      if (taskId.isEmpty) {
        throw Exception('Server khong tra ve task_id hop le.');
      }
      if (!mounted) return;
      // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

      setState(() {
        _pendingTaskId = taskId;
        _pendingAssistantText = '';
        if (sessionId != null) {
          _activeSessionId = sessionId;
        }
      });
      if (sessionId != null) {
        await ConversationBootstrapStore.markConversationChosen(_featureKey);
        await ConversationBootstrapStore.rememberSession(_featureKey, sessionId);
      }
      _scrollToBottom(); /*
            'return_label': 'Quay về Chat AI',
          // Điều hướng người dùng sang màn phù hợp theo kết quả thao tác hiện tại.

      */
    } catch (error) {
      _handlePendingTaskFailure(_readableError(error));
      return; /*
      // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

      setState(() {
        _sending = false;
        _messages = [
          ..._messages,
          ChatMessage(
            id: -DateTime.now().millisecondsSinceEpoch - 1,
            role: 'assistant',
            content: _readableError(error),
            citations: const [],
            createdAt: '',
          ),
        ];
      });
      _scrollToBottom();
      */
    }
  }

  // Suy ra route RAG dự phòng từ payload kết quả.

  String _fallbackRagRoute(Map<String, dynamic> payload) {
    final assistantSessionId =
        payload['assistant_session_id'] ?? payload['session_id'];
    final assistantMessageId =
        payload['assistant_message_id'] ?? payload['message_id'];
    if (assistantSessionId == null || assistantMessageId == null) return '';
    final mode = payload['mode'] == 'template' ? 'template' : 'document';
    final uri = Uri(
      path: '/chat/rag-result',
      queryParameters: {
        'mode': mode,
        'assistant_session_id': '$assistantSessionId',
        'assistant_message_id': '$assistantMessageId',
        'return_to': '/chat/text',
        'return_label': 'Quay về Chat AI',
      },
    );
    return uri.toString();
  }

  // Đổi lỗi thành thông điệp dễ đọc.

  String _readableError(Object error) {
    final strings = AppStrings.of(context);
    if (error is DioException) {
      final data = error.response?.data;
      if (data is Map && data['error'] != null) return '${data['error']}';
      if (data is Map && data['detail'] != null) return '${data['detail']}';
      return strings.pick(
        'Không gọi được trợ lý AI (${error.response?.statusCode ?? 'network'}).',
        'Unable to reach the AI assistant (${error.response?.statusCode ?? 'network'}).',
      );
    }
    return strings.pick('Đã xảy ra lỗi: $error', 'An error occurred: $error');
  }

  // Hiện thông báo lỗi.

  void _showError(String message) {
    ScaffoldMessenger.of(context)
        .showSnackBar(SnackBar(content: Text(message)));
  }

  // Cuộn khung chat xuống cuối (tin mới nhất).

  void _scrollToBottom({bool jump = false}) {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!_scrollCtrl.hasClients) return;
      final target = _scrollCtrl.position.maxScrollExtent;
      if (jump) {
        _scrollCtrl.jumpTo(target);
      } else {
        _scrollCtrl.animateTo(target,
            duration: const Duration(milliseconds: 250), curve: Curves.easeOut);
      }
    });
  }

  @override
  // Khung màn chat: chọn bố cục mobile/desktop.

  Widget build(BuildContext context) {
    final isWide = MediaQuery.sizeOf(context).width >= 1100;
    return TaskDonePopupHost(
      child: Container(
        color: const Color(0xFFF8FAFC),
        child: isWide
          ? Row(
              children: [
                SizedBox(
                    width: 320,
                    child: _Sidebar(
                      sessions: _sessions,
                      activeSessionId: _activeSessionId,
                      loading: _loadingSessions,
                      onNewConversation: _newConversation,
                      onOpenHistory: _openHistoryManager,
                      // Điều hướng người dùng sang màn phù hợp theo kết quả thao tác hiện tại.

                      onOpenVoice: () => context.go('/chat/voice'),
                      onSelect: _loadMessages,
                    )),
                const VerticalDivider(width: 1),
                Expanded(child: _buildConversation(context)),
              ],
            )
            : _buildMobileLayout(context),
      ),
    );
  }

  // Bố cục mobile: hội thoại toàn màn + ngăn kéo lịch sử.

  Widget _buildMobileLayout(BuildContext context) {
    final strings = AppStrings.of(context);
    final activeSession = _activeSession;
    final isNarrowPhone = MediaQuery.sizeOf(context).width < 390;
    return Column(
      children: [
        Container(
          padding: const EdgeInsets.fromLTRB(14, 12, 14, 12),
          decoration: const BoxDecoration(
            color: Colors.white,
            border: Border(bottom: BorderSide(color: Color(0xFFE2E8F0))),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          strings.pick('Chat AI', 'AI Chat'),
                          style: const TextStyle(
                            fontSize: 20,
                            fontWeight: FontWeight.w800,
                          ),
                        ),
                        const SizedBox(height: 4),
                        Text(
                          strings.pick(
                            'Tạo văn bản hoặc hỏi đáp tài liệu ngay trong một màn gọn hơn.',
                            'Create documents or ask about files from one compact screen.',
                          ),
                          style: const TextStyle(
                            color: Color(0xFF475569),
                            fontSize: 12.5,
                            height: 1.35,
                          ),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(width: 12),
                  IconButton.filledTonal(
                    onPressed: _showMobileActionsSheet,
                    icon: const Icon(Icons.more_horiz),
                    tooltip: strings.pick('Tùy chọn', 'Options'),
                  ),
                ],
              ),
              const SizedBox(height: 10),
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: [
                  FilledButton.icon(
                    onPressed: _newConversation,
                    icon: const Icon(Icons.add_comment_outlined, size: 18),
                    label: Text(strings.pick('Phiên mới', 'New session')),
                  ),
                  OutlinedButton.icon(
                    onPressed: _showSessionPickerSheet,
                    icon: const Icon(Icons.history, size: 18),
                    label: Text(strings.pick('Lịch sử', 'History')),
                  ),
                ],
              ),
              if (_loadingSessions) ...[
                const SizedBox(height: 10),
                const LinearProgressIndicator(minHeight: 3),
              ] else if (activeSession != null) ...[
                const SizedBox(height: 10),
                Material(
                  color: const Color(0xFFF8FAFC),
                  borderRadius: BorderRadius.circular(16),
                  child: InkWell(
                    borderRadius: BorderRadius.circular(16),
                    onTap: _showSessionPickerSheet,
                    child: Padding(
                      padding: const EdgeInsets.symmetric(
                        horizontal: 12,
                        vertical: 10,
                      ),
                      child: Row(
                        children: [
                          Container(
                            width: 34,
                            height: 34,
                            decoration: BoxDecoration(
                              color: const Color(0xFFDBEAFE),
                              borderRadius: BorderRadius.circular(11),
                            ),
                            child: const Icon(
                              Icons.chat_bubble_outline,
                              color: Color(0xFF2563EB),
                              size: 18,
                            ),
                          ),
                          const SizedBox(width: 10),
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(
                                  strings.pick(
                                      'Phiên hiện tại', 'Current session'),
                                  style: TextStyle(
                                    fontSize: 11.5,
                                    fontWeight: FontWeight.w700,
                                    color: Color(0xFF2563EB),
                                  ),
                                ),
                                const SizedBox(height: 2),
                                Text(
                                  activeSession.title,
                                  maxLines: 1,
                                  overflow: TextOverflow.ellipsis,
                                  style: const TextStyle(
                                    fontSize: 13.5,
                                    fontWeight: FontWeight.w700,
                                  ),
                                ),
                                if (!isNarrowPhone) ...[
                                  const SizedBox(height: 2),
                                  Text(
                                    strings.pick(
                                      '${activeSession.messageCount} tin nhắn',
                                      '${activeSession.messageCount} messages',
                                    ),
                                    style: const TextStyle(
                                      fontSize: 11.5,
                                      color: Color(0xFF64748B),
                                    ),
                                  ),
                                ],
                              ],
                            ),
                          ),
                          const Icon(
                            Icons.chevron_right_rounded,
                            color: Color(0xFF64748B),
                          ),
                        ],
                      ),
                    ),
                  ),
                ),
              ] else if (_sessions.isNotEmpty) ...[
                const SizedBox(height: 10),
                TextButton.icon(
                  onPressed: _showSessionPickerSheet,
                  icon: const Icon(Icons.schedule),
                  label: Text('Có ${_sessions.length} phiên cũ'),
                ),
              ],
            ],
          ),
        ),
        Expanded(child: _buildConversation(context, showHeader: false)),
      ],
    );
  }

  // ignore: unused_element
  Widget _buildMobileLayoutLegacy(BuildContext context) {
    final strings = AppStrings.of(context);
    return Column(
      children: [
        Container(
          padding: const EdgeInsets.fromLTRB(16, 14, 16, 14),
          decoration: const BoxDecoration(
            color: Colors.white,
            border: Border(bottom: BorderSide(color: Color(0xFFE2E8F0))),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                strings.pick('Chat AI', 'AI Chat'),
                style: TextStyle(fontSize: 22, fontWeight: FontWeight.w800),
              ),
              const SizedBox(height: 6),
              Text(
                strings.pick(
                  'Trợ lý sẽ tự điều phối tool sinh văn bản hoặc hỏi đáp theo yêu cầu của bạn.',
                  'The assistant will orchestrate document generation or Q&A tools based on your request.',
                ),
                style: TextStyle(color: Color(0xFF475569), height: 1.45),
              ),
              const SizedBox(height: 12),
              Wrap(
                spacing: 10,
                runSpacing: 10,
                children: [
                  FilledButton.icon(
                    onPressed: _newConversation,
                    icon: const Icon(Icons.add_comment_outlined),
                    label: Text(strings.pick('Phiên mới', 'New session')),
                  ),
                  OutlinedButton.icon(
                    onPressed: _openHistoryManager,
                    icon: const Icon(Icons.history),
                    label: Text(strings.pick('Lịch sử', 'History')),
                  ),
                  OutlinedButton.icon(
                    // Điều hướng người dùng sang màn phù hợp theo kết quả thao tác hiện tại.

                    onPressed: () => context.go('/chat/voice'),
                    icon: const Icon(Icons.mic_none_outlined),
                    label: Text(strings.pick('Giọng nói AI', 'AI Voice')),
                  ),
                ],
              ),
            ],
          ),
        ),
        if (_loadingSessions || _sessions.isNotEmpty)
          Container(
            height: 112,
            padding: const EdgeInsets.fromLTRB(14, 12, 14, 10),
            decoration: const BoxDecoration(
              color: Colors.white,
              border: Border(bottom: BorderSide(color: Color(0xFFE2E8F0))),
            ),
            child: _loadingSessions
                ? const Center(child: CircularProgressIndicator())
                : ListView.separated(
                    scrollDirection: Axis.horizontal,
                    itemCount: _sessions.length,
                    separatorBuilder: (_, __) => const SizedBox(width: 10),
                    itemBuilder: (_, index) {
                      final session = _sessions[index];
                      final active = session.id == _activeSessionId;
                      final time = session.updatedAt.isNotEmpty
                          ? session.updatedAt
                          : session.createdAt;
                      return SizedBox(
                        width: 240,
                        child: Material(
                          color: active
                              ? const Color(0xFFEFF6FF)
                              : const Color(0xFFF8FAFC),
                          borderRadius: BorderRadius.circular(18),
                          child: InkWell(
                            borderRadius: BorderRadius.circular(18),
                            onTap: () => _loadMessages(session.id),
                            child: Padding(
                              padding: const EdgeInsets.all(14),
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text(
                                    session.title,
                                    maxLines: 2,
                                    overflow: TextOverflow.ellipsis,
                                    style: TextStyle(
                                      fontWeight: FontWeight.w700,
                                      color: active
                                          ? const Color(0xFF1D4ED8)
                                          : const Color(0xFF0F172A),
                                    ),
                                  ),
                                  const SizedBox(height: 8),
                                  Text(
                                    '${session.messageCount} tin nhan',
                                    style: TextStyle(
                                      fontSize: 12,
                                      color: Colors.blueGrey.shade600,
                                    ),
                                  ),
                                  const SizedBox(height: 4),
                                  Text(
                                    time.replaceFirst('T', ' '),
                                    maxLines: 1,
                                    overflow: TextOverflow.ellipsis,
                                    style: TextStyle(
                                      fontSize: 11.5,
                                      color: Colors.blueGrey.shade400,
                                    ),
                                  ),
                                ],
                              ),
                            ),
                          ),
                        ),
                      );
                    },
                  ),
          ),
        Expanded(child: _buildConversation(context, showHeader: false)),
      ],
    );
  }

  // Khung hội thoại: danh sách tin nhắn + ô nhập + nút gửi.

  Widget _buildConversation(BuildContext context, {bool showHeader = true}) {
    final strings = AppStrings.of(context);
    final isCompact = MediaQuery.sizeOf(context).width < 700;
    return Padding(
      padding: EdgeInsets.fromLTRB(
        isCompact ? 12 : 20,
        showHeader ? 18 : 12,
        isCompact ? 12 : 20,
        18,
      ),
      child: Column(
        children: [
          if (showHeader) ...[
            Row(
              children: [
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        strings.pick('Tương tác bằng chat', 'Chat interaction'),
                        style: const TextStyle(
                            fontSize: 22, fontWeight: FontWeight.w800),
                      ),
                      const SizedBox(height: 4),
                      Text(
                        strings.pick(
                          'Trợ lý sẽ tự chọn tool để sinh văn bản hoặc hỏi đáp về mẫu và văn bản.',
                          'The assistant will choose the right tool to create documents or answer questions about templates and documents.',
                        ),
                      ),
                    ],
                  ),
                ),
                OutlinedButton.icon(
                  // Điều hướng người dùng sang màn phù hợp theo kết quả thao tác hiện tại.

                  onPressed: () => context.go('/chat/voice'),
                  icon: const Icon(Icons.mic_none_outlined),
                  label: Text(strings.pick('Giọng nói AI', 'AI Voice')),
                ),
              ],
            ),
            const SizedBox(height: 18),
          ],
          Expanded(
            child: Container(
              decoration: BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.circular(28),
                border: Border.all(color: const Color(0xFFE2E8F0)),
              ),
              child: Column(
                children: [
                  Expanded(
                    child: _loadingMessages
                        ? const Center(child: CircularProgressIndicator())
                        : _messages.isEmpty
                            ? _EmptyState(
                                isCompact: isCompact,
                                onUseSuggestion: (value) {
                                  _composerCtrl.text = value;
                                  _focusNode.requestFocus();
                                },
                              )
                            : ListView.builder(
                                controller: _scrollCtrl,
                                padding: EdgeInsets.fromLTRB(
                                  isCompact ? 12 : 18,
                                  isCompact ? 14 : 20,
                                  isCompact ? 12 : 18,
                                  isCompact ? 14 : 20,
                                ),
                                itemCount:
                                    _messages.length + (_pendingTaskId != null ? 1 : 0),
                                itemBuilder: (_, index) {
                                  if (_pendingTaskId != null && index == _messages.length) {
                                    return _PendingTaskCard(
                                      taskId: _pendingTaskId!,
                                      content: _pendingAssistantText,
                                      onStreamingUpdate: (chunks) {
                                        if (!mounted) return;
                                        setState(() {
                                          _pendingAssistantText = chunks.join('');
                                        });
                                        _scrollToBottom();
                                      },
                                      onComplete: _handlePendingTaskComplete,
                                      onCancelled: _handlePendingTaskCancelled,
                                      onFailed: _handlePendingTaskFailure,
                                    );
                                  }
                                  return _MessageCard(
                                      message: _messages[index]);
                                },
                              ),
                  ),
                  const Divider(height: 1),
                  // Picker + save prompt toolbar
                  Padding(
                    padding: EdgeInsets.fromLTRB(
                      isCompact ? 12 : 18,
                      6,
                      isCompact ? 12 : 18,
                      0,
                    ),
                    child: Row(children: [
                      TextButton.icon(
                        icon: const Icon(Icons.library_books_outlined, size: 15),
                        label: const Text('Prompt đã lưu',
                            style: TextStyle(fontSize: 12)),
                        onPressed: _pickChatSavedPrompt,
                        style: TextButton.styleFrom(
                          padding: const EdgeInsets.symmetric(
                              horizontal: 8, vertical: 0),
                          foregroundColor: const Color(0xFF1D4ED8),
                          minimumSize: const Size(0, 30),
                        ),
                      ),
                      const SizedBox(width: 4),
                      TextButton.icon(
                        icon: const Icon(Icons.bookmark_add_outlined, size: 15),
                        label: const Text('Lưu prompt',
                            style: TextStyle(fontSize: 12)),
                        onPressed: _composerCtrl.text.trim().isEmpty
                            ? null
                            : _saveChatPrompt,
                        style: TextButton.styleFrom(
                          padding: const EdgeInsets.symmetric(
                              horizontal: 8, vertical: 0),
                          foregroundColor: const Color(0xFF15803D),
                          minimumSize: const Size(0, 30),
                        ),
                      ),
                    ]),
                  ),
                  Padding(
                    padding: EdgeInsets.fromLTRB(
                      isCompact ? 12 : 18,
                      6,
                      isCompact ? 12 : 18,
                      6,
                    ),
                    child: PrefillToggleRow(
                      autoFillProfile: _autoFillProfile,
                      autoFillCompany: _autoFillCompany,
                      onProfileChanged: (v) =>
                          setState(() => _autoFillProfile = v),
                      onCompanyChanged: (v) =>
                          setState(() => _autoFillCompany = v),
                      compact: isCompact,
                    ),
                  ),
                  Padding(
                    padding: EdgeInsets.fromLTRB(
                      isCompact ? 12 : 18,
                      0,
                      isCompact ? 12 : 18,
                      6,
                    ),
                    child: ChatAttachmentRow(
                      items: _pendingAttachments,
                      onAdd: (item) =>
                          setState(() => _pendingAttachments.add(item)),
                      onRemove: (i) =>
                          setState(() => _pendingAttachments.removeAt(i)),
                      compact: isCompact,
                    ),
                  ),
                  Padding(
                    padding: EdgeInsets.fromLTRB(
                      isCompact ? 12 : 18,
                      6,
                      isCompact ? 12 : 18,
                      isCompact ? 12 : 18,
                    ),
                    child: Row(
                      crossAxisAlignment: CrossAxisAlignment.end,
                      children: [
                        Expanded(
                          child: TextField(
                            controller: _composerCtrl,
                            focusNode: _focusNode,
                            minLines: 1,
                            maxLines: 6,
                            decoration: InputDecoration(
                              hintText: isCompact
                                  ? 'Nhập yêu cầu tạo văn bản hoặc câu hỏi...'
                                  : 'Mô tả văn bản cần tạo hoặc đặt câu hỏi về mẫu/văn bản...',
                              filled: true,
                              fillColor: const Color(0xFFF8FAFC),
                              border: OutlineInputBorder(
                                borderRadius: BorderRadius.circular(18),
                                borderSide:
                                    const BorderSide(color: Color(0xFFE2E8F0)),
                              ),
                              enabledBorder: OutlineInputBorder(
                                borderRadius: BorderRadius.circular(18),
                                borderSide:
                                    const BorderSide(color: Color(0xFFE2E8F0)),
                              ),
                              focusedBorder: OutlineInputBorder(
                                borderRadius: BorderRadius.circular(18),
                                borderSide:
                                    const BorderSide(color: Color(0xFF2563EB)),
                              ),
                            ),
                            onSubmitted: (_) => _send(),
                            onChanged: (_) => setState(() {}),
                          ),
                        ),
                        const SizedBox(width: 12),
                        FilledButton(
                          onPressed: _sending ? null : _send,
                          style: FilledButton.styleFrom(
                            minimumSize:
                                Size(isCompact ? 50 : 58, isCompact ? 50 : 58),
                            shape: RoundedRectangleBorder(
                              borderRadius:
                                  BorderRadius.circular(isCompact ? 16 : 18),
                            ),
                          ),
                          child: _sending
                              ? const SizedBox(
                                  width: 20,
                                  height: 20,
                                  child: CircularProgressIndicator(
                                      strokeWidth: 2, color: Colors.white),
                                )
                              : const Icon(Icons.send),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  @override
  // Rời màn: dọn controller + tài nguyên.

  void dispose() {
    _composerCtrl.dispose();
    _scrollCtrl.dispose();
    _focusNode.dispose();
    super.dispose();
  }
}

// Thanh bên: danh sách phiên chat + nút tạo mới (ConsumerWidget).

class _Sidebar extends ConsumerWidget {
  final List<ChatSession> sessions;
  final int? activeSessionId;
  final bool loading;
  final VoidCallback onNewConversation;
  final VoidCallback onOpenHistory;
  final VoidCallback onOpenVoice;
  final ValueChanged<int> onSelect;

  const _Sidebar({
    required this.sessions,
    required this.activeSessionId,
    required this.loading,
    required this.onNewConversation,
    required this.onOpenHistory,
    required this.onOpenVoice,
    required this.onSelect,
  });

  @override
  // Dựng thanh bên danh sách phiên.

  Widget build(BuildContext context, WidgetRef ref) {
    final modelName =
        ref.watch(chatAiModelProvider).asData?.value ?? 'kimi-k2.6:cloud';
    return Container(
      color: Colors.white,
      padding: const EdgeInsets.fromLTRB(16, 18, 16, 16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(children: [
            Container(
              width: 44,
              height: 44,
              decoration: BoxDecoration(
                color: const Color(0xFFDBEAFE),
                borderRadius: BorderRadius.circular(14),
              ),
              child: const Icon(Icons.smart_toy_outlined,
                  color: Color(0xFF1D4ED8)),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                        AppStrings.of(context)
                            .pick('Trợ lý AI', 'AI Assistant'),
                        style: const TextStyle(
                            fontSize: 18, fontWeight: FontWeight.w800)),
                    const SizedBox(height: 2),
                    Text(
                      '$modelName · ${AppStrings.of(context).pick('cong cu tu dong', 'automatic tools')}',
                      style: const TextStyle(
                          fontSize: 12.5, color: Color(0xFF475569)),
                      overflow: TextOverflow.ellipsis,
                    ),
                  ]),
            ),
            Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                IconButton(
                    onPressed: onOpenHistory, icon: const Icon(Icons.history)),
                IconButton(
                    onPressed: onOpenVoice,
                    icon: const Icon(Icons.mic_none_outlined)),
              ],
            ),
          ]),
          const SizedBox(height: 16),
          FilledButton.icon(
            onPressed: onNewConversation,
            icon: const Icon(Icons.add_comment_outlined),
            label: Text(AppStrings.of(context)
                .pick('Cuộc trò chuyện mới', 'New conversation')),
          ),
          const SizedBox(height: 12),
          Text(
            AppStrings.of(context).pick(
              'Phiên text tách riêng với voice. Trợ lý sẽ gọi đúng flow sinh văn bản hoặc hỏi đáp theo yêu cầu.',
              'The text session is separate from voice. The assistant routes document generation or Q&A flows based on your request.',
            ),
            style: TextStyle(
                fontSize: 12.5, color: Color(0xFF475569), height: 1.5),
          ),
          const SizedBox(height: 16),
          Expanded(
            child: loading
                ? const Center(child: CircularProgressIndicator())
                : sessions.isEmpty
                    ? Center(
                        child: Text(
                          AppStrings.of(context).pick(
                              'Chưa có lịch sử text.', 'No text history yet.'),
                          style: const TextStyle(color: Color(0xFF64748B)),
                        ),
                      )
                    : ListView.separated(
                        itemCount: sessions.length,
                        separatorBuilder: (_, __) => const SizedBox(height: 10),
                        itemBuilder: (_, index) {
                          final session = sessions[index];
                          final active = session.id == activeSessionId;
                          final time = session.updatedAt.isNotEmpty
                              ? session.updatedAt
                              : session.createdAt;
                          return Material(
                            color: active
                                ? const Color(0xFFEFF6FF)
                                : const Color(0xFFF8FAFC),
                            borderRadius: BorderRadius.circular(18),
                            child: InkWell(
                              borderRadius: BorderRadius.circular(18),
                              onTap: () => onSelect(session.id),
                              child: Padding(
                                padding: const EdgeInsets.all(14),
                                child: Column(
                                    crossAxisAlignment:
                                        CrossAxisAlignment.start,
                                    children: [
                                      Text(
                                        session.title,
                                        maxLines: 2,
                                        overflow: TextOverflow.ellipsis,
                                        style: TextStyle(
                                          fontWeight: FontWeight.w700,
                                          color: active
                                              ? const Color(0xFF1D4ED8)
                                              : const Color(0xFF0F172A),
                                        ),
                                      ),
                                      const SizedBox(height: 8),
                                      Text(
                                        AppStrings.of(context).pick(
                                          '${session.messageCount} tin nhắn',
                                          '${session.messageCount} messages',
                                        ),
                                        style: TextStyle(
                                            fontSize: 12,
                                            color: Colors.blueGrey.shade600),
                                      ),
                                      const SizedBox(height: 4),
                                      Text(
                                        time.replaceFirst('T', ' '),
                                        maxLines: 1,
                                        overflow: TextOverflow.ellipsis,
                                        style: TextStyle(
                                            fontSize: 11.5,
                                            color: Colors.blueGrey.shade400),
                                      ),
                                    ]),
                              ),
                            ),
                          );
                        },
                      ),
          ),
        ],
      ),
    );
  }
}

// Trạng thái trống khi chưa có tin nhắn.

class _EmptyState extends StatelessWidget {
  final bool isCompact;
  final ValueChanged<String> onUseSuggestion;

  const _EmptyState({
    required this.isCompact,
    required this.onUseSuggestion,
  });

  static const _suggestions = [
    'Tạo hợp đồng thử việc cho nhân viên kế toán.',
    'Trong hệ thống có mẫu biên bản thanh lý nào không?',
    'Văn bản nào liên quan đến quyết định phân công công việc?',
  ];

  @override
  // Dựng trạng thái trống (gợi ý bắt đầu chat).

  Widget build(BuildContext context) {
    final strings = AppStrings.of(context);
    final suggestions = strings.isEnglish
        ? const [
            'Create a probation contract for an accounting employee.',
            'Do we have a liquidation report template in the system?',
            'Which documents are related to work assignment decisions?',
          ]
        : _suggestions;
    return Center(
      child: Padding(
        padding: EdgeInsets.all(isCompact ? 18 : 32),
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          Container(
            width: isCompact ? 62 : 74,
            height: isCompact ? 62 : 74,
            decoration: BoxDecoration(
              color: const Color(0xFFDBEAFE),
              borderRadius: BorderRadius.circular(24),
            ),
            child: Icon(
              Icons.smart_toy_outlined,
              size: isCompact ? 30 : 36,
              color: const Color(0xFF1D4ED8),
            ),
          ),
          SizedBox(height: isCompact ? 14 : 18),
          Text(
            isCompact
                ? strings.pick('Bắt đầu một cuộc trò chuyện mới',
                    'Start a new conversation')
                : strings.pick('Trợ lý AI sẽ tự chọn cách xử lý phù hợp',
                    'The AI assistant will choose the right flow'),
            textAlign: TextAlign.center,
            style: TextStyle(
              fontSize: isCompact ? 19 : 22,
              fontWeight: FontWeight.w800,
            ),
          ),
          SizedBox(height: isCompact ? 8 : 10),
          Text(
            isCompact
                ? strings.pick(
                    'Chọn một gợi ý nhanh hoặc nhập yêu cầu của bạn ở ô phía dưới.',
                    'Pick a quick suggestion or type your request in the composer below.',
                  )
                : strings.pick(
                    'Bạn có thể yêu cầu tạo văn bản mới hoặc hỏi về mẫu, văn bản trong hệ thống. Trợ lý sẽ tự điều phối đúng luồng xử lý.',
                    'You can request a new document or ask about templates and documents in the system. The assistant will route the correct workflow automatically.',
                  ),
            textAlign: TextAlign.center,
            style: const TextStyle(color: Color(0xFF475569), height: 1.6),
          ),
          SizedBox(height: isCompact ? 16 : 20),
          if (isCompact)
            Column(
              children: suggestions
                  .take(2)
                  .map(
                    (item) => Padding(
                      padding: const EdgeInsets.only(bottom: 10),
                      child: InkWell(
                        borderRadius: BorderRadius.circular(18),
                        onTap: () => onUseSuggestion(item),
                        child: Container(
                          width: double.infinity,
                          padding: const EdgeInsets.symmetric(
                            horizontal: 14,
                            vertical: 12,
                          ),
                          decoration: BoxDecoration(
                            color: const Color(0xFFF8FAFC),
                            borderRadius: BorderRadius.circular(18),
                            border: Border.all(color: const Color(0xFFDCE7F7)),
                          ),
                          child: Row(
                            children: [
                              const Icon(
                                Icons.bolt_outlined,
                                size: 18,
                                color: Color(0xFF1D4ED8),
                              ),
                              const SizedBox(width: 10),
                              Expanded(
                                child: Text(
                                  item,
                                  style: const TextStyle(height: 1.35),
                                ),
                              ),
                            ],
                          ),
                        ),
                      ),
                    ),
                  )
                  .toList(),
            )
          else
            Wrap(
              spacing: 10,
              runSpacing: 10,
              children: suggestions
                  .map(
                    (item) => ConstrainedBox(
                      constraints: const BoxConstraints(maxWidth: 360),
                      child: ActionChip(
                        avatar: const Icon(
                          Icons.bolt_outlined,
                          size: 18,
                          color: Color(0xFF1D4ED8),
                        ),
                        label: Text(item),
                        onPressed: () => onUseSuggestion(item),
                      ),
                    ),
                  )
                  .toList(),
            ),
        ]),
      ),
    );
  }
}

// Thẻ hiệu ứng 'đang trả lời' khi AI đang sinh nội dung.

// ignore: unused_element
class _TypingCard extends ConsumerWidget {
  const _TypingCard();

  @override
  // Dựng thẻ đang gõ.

  Widget build(BuildContext context, WidgetRef ref) {
    final strings = AppStrings.of(context);
    final modelName =
        ref.watch(chatAiModelProvider).asData?.value ?? 'kimi-k2.6:cloud';
    return Align(
      alignment: Alignment.centerLeft,
      child: Container(
        margin: const EdgeInsets.only(bottom: 16),
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
        decoration: BoxDecoration(
          color: const Color(0xFFF8FAFC),
          borderRadius: BorderRadius.circular(18),
          border: Border.all(color: const Color(0xFFE2E8F0)),
        ),
        child: Row(mainAxisSize: MainAxisSize.min, children: [
          const SizedBox(
              width: 18,
              height: 18,
              child: CircularProgressIndicator(strokeWidth: 2)),
          const SizedBox(width: 12),
          Flexible(
            child: Text(
              strings.pick(
                'Đang điều phối tool với $modelName...',
                'Coordinating tools with $modelName...',
              ),
              overflow: TextOverflow.ellipsis,
            ),
          ),
        ]),
      ),
    );
  }
}

// Header hiển thị tác vụ AI đang chạy (tiến độ/hủy).

class _PendingTaskHeader extends ConsumerWidget {
  final String taskId;
  const _PendingTaskHeader({required this.taskId});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final asyncState = ref.watch(aiTaskProgressProvider(
      AITaskPollConfig(
        taskId: taskId,
        pollInterval: const Duration(milliseconds: 400),
      ),
    ));
    return asyncState.when(
      loading: () => const _TypingHint(label: 'Đang khởi tạo'),
      error: (_, __) => const _TypingHint(label: 'Đang xử lý'),
      data: (state) {
        final stage = state.stage.isNotEmpty ? state.stage : 'Đang khởi tạo';
        final detail = state.detail;
        final pct = state.percent;
        return Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisSize: MainAxisSize.min,
          children: [
            Row(
              crossAxisAlignment: CrossAxisAlignment.center,
              children: [
                Flexible(
                  child: AnimatedSwitcher(
                    duration: const Duration(milliseconds: 220),
                    transitionBuilder: (child, anim) => FadeTransition(
                      opacity: anim,
                      child: child,
                    ),
                    child: Text(
                      stage,
                      key: ValueKey<String>(stage),
                      style: const TextStyle(
                        fontWeight: FontWeight.w700,
                        fontSize: 13.5,
                        color: Color(0xFF0F172A),
                        height: 1.2,
                      ),
                      overflow: TextOverflow.ellipsis,
                      maxLines: 1,
                    ),
                  ),
                ),
                if (pct > 0)
                  Padding(
                    padding: const EdgeInsets.only(left: 8),
                    child: Container(
                      padding: const EdgeInsets.symmetric(
                          horizontal: 6, vertical: 1),
                      decoration: BoxDecoration(
                        color: const Color(0xFFDBEAFE),
                        borderRadius: BorderRadius.circular(8),
                      ),
                      child: Text(
                        '$pct%',
                        style: const TextStyle(
                          fontWeight: FontWeight.w800,
                          fontSize: 11,
                          color: Color(0xFF1D4ED8),
                        ),
                      ),
                    ),
                  ),
              ],
            ),
            if (detail.isNotEmpty) ...[
              const SizedBox(height: 3),
              Text(
                detail,
                style: const TextStyle(
                  fontSize: 11,
                  color: Color(0xFF64748B),
                  height: 1.3,
                ),
                overflow: TextOverflow.ellipsis,
                maxLines: 1,
              ),
            ] else if (state.isRunning) ...[
              const SizedBox(height: 4),
              const _TypingDots(),
            ],
          ],
        );
      },
    );
  }
}

class _TypingHint extends StatelessWidget {
  final String label;
  const _TypingHint({required this.label});

  @override
  Widget build(BuildContext context) {
    return Row(children: [
      Text(
        label,
        style: const TextStyle(
          fontWeight: FontWeight.w700,
          fontSize: 13.5,
          color: Color(0xFF0F172A),
        ),
      ),
      const SizedBox(width: 6),
      const _TypingDots(),
    ]);
  }
}

class _TypingDots extends StatefulWidget {
  const _TypingDots();
  @override
  State<_TypingDots> createState() => _TypingDotsState();
}

class _TypingDotsState extends State<_TypingDots>
    with SingleTickerProviderStateMixin {
  late final AnimationController _ctrl = AnimationController(
    vsync: this,
    duration: const Duration(milliseconds: 900),
  )..repeat();

  @override
  void dispose() {
    _ctrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: _ctrl,
      builder: (_, __) {
        return Row(
          mainAxisSize: MainAxisSize.min,
          children: List.generate(3, (i) {
            final phase = (_ctrl.value + i * 0.18) % 1.0;
            final scale = 0.6 + 0.5 *
                (phase < 0.5 ? phase * 2 : (1 - phase) * 2);
            return Padding(
              padding: const EdgeInsets.symmetric(horizontal: 1.5),
              child: Transform.scale(
                scale: scale,
                child: Container(
                  width: 5,
                  height: 5,
                  decoration: const BoxDecoration(
                    color: Color(0xFF3B82F6),
                    shape: BoxShape.circle,
                  ),
                ),
              ),
            );
          }),
        );
      },
    );
  }
}


class _PendingTaskCard extends StatelessWidget {
  final String taskId;
  final String content;
  final void Function(List<String> chunks) onStreamingUpdate;
  final void Function(AITaskState state) onComplete;
  final VoidCallback onCancelled;
  final void Function(String message) onFailed;

  const _PendingTaskCard({
    required this.taskId,
    required this.content,
    required this.onStreamingUpdate,
    required this.onComplete,
    required this.onCancelled,
    required this.onFailed,
  });

  @override
  Widget build(BuildContext context) {
    final width = MediaQuery.sizeOf(context).width;
    final isCompact = width < 700;
    final maxBubble = isCompact ? width * 0.9 : 640.0;
    return Align(
      alignment: Alignment.centerLeft,
      child: ConstrainedBox(
        constraints: BoxConstraints(maxWidth: maxBubble),
        child: Container(
          margin: EdgeInsets.only(bottom: 14, right: isCompact ? 12 : 36),
          padding: EdgeInsets.fromLTRB(
            isCompact ? 12 : 14,
            isCompact ? 10 : 12,
            isCompact ? 12 : 16,
            isCompact ? 10 : 12,
          ),
          decoration: BoxDecoration(
            gradient: const LinearGradient(
              colors: [Color(0xFFF8FAFC), Color(0xFFF1F5F9)],
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
            ),
            borderRadius: BorderRadius.circular(isCompact ? 16 : 20),
            border: Border.all(color: const Color(0xFFE2E8F0)),
            boxShadow: [
              BoxShadow(
                color: const Color(0xFF1D4ED8).withOpacity(0.04),
                blurRadius: 12,
                offset: const Offset(0, 4),
              ),
            ],
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: [
              Row(
                crossAxisAlignment: CrossAxisAlignment.center,
                children: [
                  Padding(
                    padding: const EdgeInsets.only(right: 12, top: 2),
                    child: AITaskCircularProgress(
                      taskId: taskId,
                      size: CircularSize.compact,
                      onStreamingUpdate: onStreamingUpdate,
                      onComplete: onComplete,
                      onCancelled: (_) => onCancelled(),
                      onFailed: onFailed,
                    ),
                  ),
                  Expanded(child: _PendingTaskHeader(taskId: taskId)),
                ],
              ),
              if (content.trim().isNotEmpty) ...[
                const SizedBox(height: 10),
                Container(
                  padding: const EdgeInsets.only(left: 2),
                  decoration: const BoxDecoration(
                    border: Border(
                      left: BorderSide(
                        color: Color(0xFFCBD5E1),
                        width: 2,
                      ),
                    ),
                  ),
                  child: Padding(
                    padding: const EdgeInsets.only(left: 10),
                    child: MarkdownBody(data: content),
                  ),
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}

class _MessageCard extends StatelessWidget {
  final ChatMessage message;

  const _MessageCard({required this.message});

  @override
  // Dựng header tác vụ đang chạy.

  Widget build(BuildContext context) {
    final strings = AppStrings.of(context);
    final width = MediaQuery.sizeOf(context).width;
    final isCompact = width < 700;
    if (message.role == 'user') {
      return Align(
        alignment: Alignment.centerRight,
        child: Container(
          constraints: BoxConstraints(maxWidth: isCompact ? width * 0.9 : 760),
          margin: EdgeInsets.only(bottom: 16, left: isCompact ? 28 : 48),
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            color: const Color(0xFF1D4ED8),
            borderRadius: BorderRadius.circular(isCompact ? 18 : 22),
          ),
          child: Text(message.content,
              style: const TextStyle(color: Colors.white, height: 1.5)),
        ),
      );
    }

    final payload = message.payload ?? const <String, dynamic>{};
    final route = '${payload['route'] ?? ''}'.trim();
    return Align(
      alignment: Alignment.centerLeft,
      child: Container(
        constraints: BoxConstraints(maxWidth: isCompact ? width * 0.95 : 860),
        margin: EdgeInsets.only(bottom: 18, right: isCompact ? 20 : 48),
        padding: EdgeInsets.all(isCompact ? 14 : 18),
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(isCompact ? 18 : 24),
          border: Border.all(color: const Color(0xFFE2E8F0)),
        ),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            const Icon(Icons.auto_awesome, size: 18, color: Color(0xFF1D4ED8)),
            const SizedBox(width: 8),
            Text(strings.pick('Trợ lý AI', 'AI Assistant'),
                style:
                    const TextStyle(fontSize: 13, fontWeight: FontWeight.w800)),
          ]),
          const SizedBox(height: 12),
          MarkdownBody(data: message.content),
          if (payload['kind'] == 'document_result' && route.isNotEmpty) ...[
            const SizedBox(height: 16),
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(14),
              decoration: BoxDecoration(
                color: const Color(0xFFF8FAFC),
                borderRadius: BorderRadius.circular(18),
                border: Border.all(color: const Color(0xFFDCE7F7)),
              ),
              child: isCompact
                  ? Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(children: [
                          const Icon(
                            Icons.description_outlined,
                            color: Color(0xFF1D4ED8),
                          ),
                          const SizedBox(width: 12),
                          Expanded(
                            child: Text(
                              '${payload['title'] ?? strings.pick('Văn bản đã tạo', 'Generated document')}',
                              style:
                                  const TextStyle(fontWeight: FontWeight.w700),
                            ),
                          ),
                        ]),
                        const SizedBox(height: 12),
                        FilledButton.tonalIcon(
                          onPressed: () =>
                              context.go(_withAssistantReturn(context, route)),
                          icon: const Icon(Icons.open_in_new),
                          label:
                              Text(strings.pick('Mở văn bản', 'Open document')),
                        ),
                      ],
                    )
                  : Row(children: [
                      const Icon(
                        Icons.description_outlined,
                        color: Color(0xFF1D4ED8),
                      ),
                      const SizedBox(width: 12),
                      Expanded(
                        child: Text(
                          '${payload['title'] ?? strings.pick('Văn bản đã tạo', 'Generated document')}',
                          style: const TextStyle(fontWeight: FontWeight.w700),
                        ),
                      ),
                      FilledButton.tonalIcon(
                        onPressed: () =>
                            context.go(_withAssistantReturn(context, route)),
                        icon: const Icon(Icons.open_in_new),
                        label:
                            Text(strings.pick('Mở văn bản', 'Open document')),
                      ),
                    ]),
            ),
          ],
          if (payload['kind'] == 'assistant_quick_sign_plan') ...[
            const SizedBox(height: 16),
            _buildQuickSignCard(context, payload, isCompact),
          ],
          if (payload['kind'] == 'recipient_resolution') ...[
            const SizedBox(height: 16),
            _buildRecipientResolutionCard(context, payload, isCompact),
          ],
          if (message.citations.isNotEmpty) ...[
            const SizedBox(height: 16),
            Text(
              strings.pick('Nguồn tham khảo:', 'Sources:'),
              style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w700),
            ),
            const SizedBox(height: 10),
            CitationSections(
              citations: message.citations,
              returnTo: '/chat/text',
              returnLabel: strings.pick('Quay về Chat AI', 'Back to AI Chat'),
            ),
          ],
        ]),
      ),
    );
  }

  // Dựng thẻ quick-sign trong chat text: hiển thị văn bản đã sinh + nút 'Mở văn bản' (đồng bộ màn Giọng nói AI).
  Widget _buildQuickSignCard(
    BuildContext context,
    Map<String, dynamic> payload,
    bool isCompact,
  ) {
    final strings = AppStrings.of(context);
    final plan = AssistantQuickSignPlanAction.fromJson(payload);
    final recipient = plan.recipient;
    final route = plan.route.trim();
    final title = plan.isCompleted
        ? strings.pick('Quick-sign đã hoàn tất', 'Quick sign completed')
        : plan.isPartial
            ? strings.pick(
                'Đã ký xong, cần gửi lại', 'Signed, forward retry needed')
            : plan.isFailed
                ? strings.pick('Quick-sign gặp lỗi', 'Quick sign failed')
                : plan.isBlocked
                    ? strings.pick(
                        'Quick-sign chưa sẵn sàng', 'Quick sign is not ready')
                    : strings.pick(
                        'Quick-sign đã sẵn sàng', 'Quick sign is ready');
    final summary = plan.blockingReason.trim().isNotEmpty
        ? plan.blockingReason
        : plan.lastErrorMessage.trim().isNotEmpty
            ? plan.lastErrorMessage
            : plan.message;
    final icon = plan.isCompleted
        ? Icons.verified_outlined
        : plan.isPartial
            ? Icons.forward_to_inbox_outlined
            : plan.isFailed
                ? Icons.error_outline
                : plan.isBlocked
                    ? Icons.lock_outline
                    : Icons.bolt_outlined;

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: const Color(0xFFF8FAFC),
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: const Color(0xFFDCE7F7)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Icon(icon, color: const Color(0xFF1D4ED8)),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      title,
                      style: const TextStyle(
                        fontWeight: FontWeight.w700,
                        color: Color(0xFF0F172A),
                      ),
                    ),
                    if (summary.trim().isNotEmpty) ...[
                      const SizedBox(height: 3),
                      Text(
                        summary,
                        style: const TextStyle(
                          color: Color(0xFF475569),
                          height: 1.45,
                        ),
                      ),
                    ],
                  ],
                ),
              ),
            ],
          ),
          if (recipient != null) ...[
            const SizedBox(height: 12),
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(10),
              decoration: BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: const Color(0xFFE2E8F0)),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    strings.pick('Người nhận dự kiến', 'Planned recipient'),
                    style: const TextStyle(
                      color: Color(0xFF64748B),
                      fontSize: 12.5,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    recipient.displayName,
                    style: const TextStyle(
                      fontWeight: FontWeight.w700,
                      color: Color(0xFF0F172A),
                    ),
                  ),
                  if (recipient.subtitle.isNotEmpty) ...[
                    const SizedBox(height: 4),
                    Text(
                      recipient.subtitle,
                      style: const TextStyle(
                        color: Color(0xFF475569),
                        height: 1.4,
                      ),
                    ),
                  ],
                ],
              ),
            ),
          ],
          if (route.isNotEmpty) ...[
            const SizedBox(height: 12),
            Align(
              alignment: Alignment.centerLeft,
              child: FilledButton.tonalIcon(
                onPressed: () =>
                    context.go(_withAssistantReturn(context, route)),
                icon: const Icon(Icons.open_in_new),
                label: Text(
                  plan.isCompleted
                      ? strings.pick('Mở văn bản', 'Open document')
                      : strings.pick(
                          'Mở văn bản để ký nhanh', 'Open document to sign'),
                ),
              ),
            ),
          ],
        ],
      ),
    );
  }

  // Dựng thẻ xác nhận/đề xuất người nhận trong chat text (đồng bộ màn Giọng nói AI).
  Widget _buildRecipientResolutionCard(
    BuildContext context,
    Map<String, dynamic> payload,
    bool isCompact,
  ) {
    final strings = AppStrings.of(context);
    final resolution = payload['recipient_resolution'] is Map
        ? QuickSignRecipientResolution.fromJson(
            Map<String, dynamic>.from(payload['recipient_resolution'] as Map),
          )
        : const QuickSignRecipientResolution(
            status: 'not_found', recipient: null);
    final prompt = (payload['clarification_prompt']?.toString() ??
            payload['message']?.toString() ??
            '')
        .trim();
    final isAmbiguous = resolution.status == 'ambiguous';
    final candidates = resolution.candidates.take(isCompact ? 2 : 3).toList();

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: const Color(0xFFF8FAFC),
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: const Color(0xFFDCE7F7)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Icon(
                isAmbiguous
                    ? Icons.help_outline
                    : Icons.person_search_outlined,
                color: const Color(0xFF1D4ED8),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      isAmbiguous
                          ? strings.pick('Cần xác nhận người nhận',
                              'Recipient confirmation needed')
                          : strings.pick('Chưa tìm thấy người nhận',
                              'Recipient not found'),
                      style: const TextStyle(
                        fontWeight: FontWeight.w700,
                        color: Color(0xFF0F172A),
                      ),
                    ),
                    if (prompt.isNotEmpty) ...[
                      const SizedBox(height: 3),
                      Text(
                        prompt,
                        style: const TextStyle(
                          color: Color(0xFF475569),
                          height: 1.45,
                        ),
                      ),
                    ],
                  ],
                ),
              ),
            ],
          ),
          if (candidates.isNotEmpty) ...[
            const SizedBox(height: 12),
            ...candidates.map(
              (candidate) => Container(
                width: double.infinity,
                margin: const EdgeInsets.only(bottom: 8),
                padding: const EdgeInsets.all(10),
                decoration: BoxDecoration(
                  color: Colors.white,
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(color: const Color(0xFFE2E8F0)),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      candidate.displayName,
                      style: const TextStyle(
                        fontWeight: FontWeight.w700,
                        color: Color(0xFF0F172A),
                      ),
                    ),
                    if (candidate.subtitle.isNotEmpty) ...[
                      const SizedBox(height: 4),
                      Text(
                        candidate.subtitle,
                        style: const TextStyle(
                          color: Color(0xFF475569),
                          height: 1.4,
                        ),
                      ),
                    ],
                    if (candidate.aliasSummary.isNotEmpty) ...[
                      const SizedBox(height: 4),
                      Text(
                        strings.pick(
                          'Alias: ${candidate.aliasSummary}',
                          'Aliases: ${candidate.aliasSummary}',
                        ),
                        style: const TextStyle(
                          color: Color(0xFF64748B),
                          fontSize: 12.5,
                        ),
                      ),
                    ],
                  ],
                ),
              ),
            ),
          ],
          if (isAmbiguous) ...[
            const SizedBox(height: 4),
            Text(
              strings.pick(
                'Trả lời tiếp bằng tên, phòng ban, tài khoản hoặc alias của người dùng cần gửi.',
                'Reply with the recipient name, department, username, or alias.',
              ),
              style: const TextStyle(
                color: Color(0xFF64748B),
                fontSize: 12.5,
                height: 1.45,
              ),
            ),
          ],
        ],
      ),
    );
  }

  // Gắn tham số 'quay lại chat' vào route khi điều hướng đi nơi khác.

  String _withAssistantReturn(BuildContext context, String route) {
    final strings = AppStrings.of(context);
    final uri = Uri.parse(route);
    final params = Map<String, String>.from(uri.queryParameters);
    params['return_to'] = '/chat/text';
    params['return_label'] = strings.pick('Quay về Chat AI', 'Back to AI Chat');
    return uri.replace(queryParameters: params).toString();
  }

  // Suy ra route RAG dự phòng từ payload (bản có context, hiện không dùng).

  // ignore: unused_element
  String _fallbackRagRoute(BuildContext context, Map<String, dynamic> payload) {
    final strings = AppStrings.of(context);
    final ragSessionId = '${payload['rag_session_id'] ?? ''}'.trim();
    if (ragSessionId.isEmpty) {
      return '';
    }
    final params = <String, String>{
      'mode': '${payload['source_mode'] ?? 'template'}'.trim().toLowerCase() ==
              'document'
          ? 'document'
          : 'template',
      'rag_session_id': ragSessionId,
      'return_to': '/chat/text',
      'return_label': strings.pick('Quay về Chat AI', 'Back to AI Chat'),
    };
    final ragMessageId = '${payload['rag_message_id'] ?? ''}'.trim();
    if (ragMessageId.isNotEmpty) {
      params['rag_message_id'] = ragMessageId;
    }
    return Uri(path: '/rag', queryParameters: params).toString();
  }

  // ignore: unused_element
  List<Widget> _buildCitationGroups(
      BuildContext context, List<dynamic> citations) {
    final items = citations
        .whereType<Map>()
        .map((item) => Map<String, dynamic>.from(item))
        .toList();
    final local = items
        .where((item) =>
            '${item['source_group'] ?? item['type'] ?? ''}' != 'internet')
        .toList();
    final internet = items
        .where((item) =>
            '${item['source_group'] ?? item['type'] ?? ''}' == 'internet')
        .toList();
    final bieuMau = internet
        .where(
            (item) => '${item['source_type'] ?? ''}'.toLowerCase() != 'hopdong')
        .toList();
    final hopDong = internet
        .where(
            (item) => '${item['source_type'] ?? ''}'.toLowerCase() == 'hopdong')
        .toList();
    return [
      if (local.isNotEmpty)
        _CitationSection(
            title: 'Kết quả local',
            icon: Icons.folder_open_outlined,
            citations: local),
      if (bieuMau.isNotEmpty) ...[
        if (local.isNotEmpty) const SizedBox(height: 12),
        _CitationSection(
            title: 'Biểu mẫu từ THƯ VIỆN PHÁP LUẬT',
            icon: Icons.description_outlined,
            citations: bieuMau),
      ],
      if (hopDong.isNotEmpty) ...[
        if (local.isNotEmpty || bieuMau.isNotEmpty) const SizedBox(height: 12),
        _CitationSection(
            title: 'Hợp đồng từ THƯ VIỆN PHÁP LUẬT',
            icon: Icons.public_outlined,
            citations: hopDong),
      ],
    ];
  }
}

// Khối nguồn trích dẫn (citations) dưới câu trả lời RAG.

class _CitationSection extends StatelessWidget {
  final String title;
  final IconData icon;
  final List<Map<String, dynamic>> citations;

  const _CitationSection({
    required this.title,
    required this.icon,
    required this.citations,
  });

  @override
  // Dựng danh sách nguồn trích dẫn.

  Widget build(BuildContext context) {
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Row(children: [
        Icon(icon, size: 14, color: Colors.blueGrey.shade700),
        const SizedBox(width: 6),
        Text(title,
            style: TextStyle(
                fontSize: 12,
                fontWeight: FontWeight.w800,
                color: Colors.blueGrey.shade700)),
      ]),
      const SizedBox(height: 8),
      ...citations.map((citation) => Padding(
            padding: const EdgeInsets.only(bottom: 8),
            child: Material(
              color: const Color(0xFFF8FAFC),
              borderRadius: BorderRadius.circular(14),
              child: InkWell(
                borderRadius: BorderRadius.circular(14),
                onTap: () => _openCitation(context, citation),
                child: Padding(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                  child: Row(children: [
                    Icon(_iconForCitation(citation),
                        size: 18, color: Colors.blueGrey.shade700),
                    const SizedBox(width: 10),
                    Expanded(
                      child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              '${citation['title'] ?? ''}',
                              maxLines: 2,
                              overflow: TextOverflow.ellipsis,
                              style: const TextStyle(
                                  fontSize: 12.5, fontWeight: FontWeight.w700),
                            ),
                            if (_meta(citation).isNotEmpty) ...[
                              const SizedBox(height: 3),
                              Text(_meta(citation),
                                  style: TextStyle(
                                      fontSize: 11.5,
                                      color: Colors.blueGrey.shade600)),
                            ],
                          ]),
                    ),
                    const SizedBox(width: 8),
                    Icon(Icons.open_in_new,
                        size: 16, color: Colors.blueGrey.shade500),
                  ]),
                ),
              ),
            ),
          )),
    ]);
  }

  IconData _iconForCitation(Map<String, dynamic> citation) {
    switch ('${citation['type'] ?? ''}') {
      case 'template':
        return Icons.description_outlined;
      case 'document':
        return Icons.article_outlined;
      case 'internet':
        return Icons.public_outlined;
      default:
        return Icons.link_outlined;
    }
  }

  // Chuỗi metadata 1 trích dẫn (nguồn/trang).

  String _meta(Map<String, dynamic> citation) {
    final parts = <String>[
      if ('${citation['status'] ?? ''}'.isNotEmpty) '${citation['status']}',
      if ('${citation['category'] ?? ''}'.isNotEmpty) '${citation['category']}',
      if ('${citation['doc_number'] ?? ''}'.isNotEmpty)
        '${citation['doc_number']}',
    ];
    return parts.join(' | ');
  }

  // Mở tài liệu nguồn của 1 trích dẫn.

  void _openCitation(BuildContext context, Map<String, dynamic> citation) {
    final external =
        '${citation['external_url'] ?? citation['url'] ?? ''}'.trim();
    if (external.startsWith('http://') || external.startsWith('https://')) {
      html.window.open(external, '_blank');
      return;
    }

    final routeValue = '${citation['route'] ?? ''}'.trim();
    if (routeValue.isNotEmpty) {
      // Điều hướng người dùng sang màn phù hợp theo kết quả thao tác hiện tại.

      context.go(routeValue.endsWith('/') && routeValue.length > 1
          ? routeValue.substring(0, routeValue.length - 1)
          : routeValue);
      return;
    }

    final id = citation['id'];
    final type = '${citation['type'] ?? ''}';
    if (id != null && type == 'template') {
      // Điều hướng người dùng sang màn phù hợp theo kết quả thao tác hiện tại.

      context.go('/templates/$id');
      return;
    }
    if (id != null && type == 'document') {
      // Điều hướng người dùng sang màn phù hợp theo kết quả thao tác hiện tại.

      context.go('/documents/$id');
      return;
    }
    ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Không mở được nguồn tham khảo này.')));
  }
}
