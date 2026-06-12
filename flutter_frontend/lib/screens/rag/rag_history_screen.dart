// === MÀN HÌNH HỎI ĐÁP TÀI LIỆU (RAG) + LỊCH SỬ ===
// Hỏi đáp dựa trên mẫu/văn bản đã đánh chỉ mục, trả lời kèm trích dẫn nguồn.
// - Sidebar phiên (_RagSidebar/_RagSessionList): _loadSessions() GET 'ai/rag/sessions/'; chọn phiên -> _loadMessages() GET '.../messages/'.
// - _send(): POST 'ai/rag/query/' với câu hỏi + chế độ nguồn (_changeMode: mẫu/văn bản). _newConversation(): mở phiên mới.

// Tệp này dùng để: dựng giao diện và orchestration UI trong flutter_frontend/lib/screens/rag/rag_history_screen.dart.
import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_markdown/flutter_markdown.dart';
import 'package:go_router/go_router.dart';

import '../../core/api_client.dart';
import '../../core/conversation_bootstrap.dart';
import '../../l10n/app_strings.dart';
import '../../models/chat.dart';
import '../../widgets/ai/chat_history_manager_dialog.dart';
import '../../widgets/ai/citation_sections.dart';

// Widget màn HỎI ĐÁP RAG / LỊCH SỬ (StatefulWidget).

class RagHistoryScreen extends StatefulWidget {
  const RagHistoryScreen({super.key});

  @override
  State<RagHistoryScreen> createState() => _RagHistoryScreenState();
}

// State màn RAG: phiên hỏi đáp, tin nhắn, gửi câu hỏi, đổi chế độ.

class _RagHistoryScreenState extends State<RagHistoryScreen> {
  final _composerCtrl = TextEditingController();
  final _scrollCtrl = ScrollController();

  List<ChatSession> _sessions = const [];
  List<ChatMessage> _messages = const [];
  int? _activeSessionId;
  bool _loadingSessions = true;
  bool _loadingMessages = false;
  bool _sending = false;
  bool _routeSynced = false;
  String _mode = 'template';
  String? _returnTo;
  String? _returnLabel;
  int? _routeFocusMessageId;

  String get _featureKey => ConversationBootstrapStore.ragFeatureForMode(_mode);

  @override
  // Khi vào màn/đổi tham số -> nạp phiên (theo deep-link).

  void didChangeDependencies() {
    super.didChangeDependencies();
    final query = GoRouterState.of(context).uri.queryParameters;
    final routeMode = query['mode'] == 'document' ? 'document' : 'template';
    final routeSessionId = int.tryParse(query['rag_session_id'] ?? '');
    final routeMessageId = int.tryParse(query['rag_message_id'] ?? '');
    final nextReturnTo = query['return_to'];
    final nextReturnLabel = query['return_label'];

    final shouldSync = !_routeSynced ||
        routeMode != _mode ||
        routeSessionId != _activeSessionId ||
        nextReturnTo != _returnTo ||
        nextReturnLabel != _returnLabel;
    if (!shouldSync) return;

    _routeSynced = true;
    _mode = routeMode;
    _returnTo = nextReturnTo;
    _returnLabel = nextReturnLabel;
    _routeFocusMessageId = routeMessageId;
    _loadSessions(preferredSessionId: routeSessionId);
  }

  @override
  // Rời màn: dọn controller.

  void dispose() {
    _composerCtrl.dispose();
    _scrollCtrl.dispose();
    super.dispose();
  }

  // Nạp danh sách phiên hỏi đáp RAG.

  Future<void> _loadSessions({int? preferredSessionId}) async {
    if (!mounted) return;
    // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

    setState(() => _loadingSessions = true);
    try {
      // Gọi API hoặc tác vụ bất đồng bộ rồi chờ kết quả trước khi cập nhật giao diện.

      final resp = await ApiClient().dio.get(
        'ai/rag/sessions/',
        queryParameters: {'mode': _mode},
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
        await _loadMessages(targetSessionId,
            focusMessageId: _routeFocusMessageId);
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
      // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

      setState(() => _loadingSessions = false);
      _showError(_readableError(error));
    }
  }

  // Nạp tin nhắn của 1 phiên (có thể focus 1 tin).

  Future<void> _loadMessages(int sessionId, {int? focusMessageId}) async {
    if (!mounted) return;
    // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

    setState(() {
      _activeSessionId = sessionId;
      _loadingMessages = true;
    });
    try {
      // Gọi API hoặc tác vụ bất đồng bộ rồi chờ kết quả trước khi cập nhật giao diện.

      final resp =
          await ApiClient().dio.get('ai/rag/sessions/$sessionId/messages/');
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
      _scrollToMessage(focusMessageId);
    } catch (error) {
      if (!mounted) return;
      // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

      setState(() => _loadingMessages = false);
      _showError(_readableError(error));
    }
  }

  // Nút Gửi: gửi câu hỏi RAG và nhận trả lời kèm trích dẫn.

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

      final resp = await ApiClient().dio.post(
            'ai/rag/query/',
            data: {
              'q': text,
              'mode': _mode,
              if (_activeSessionId != null) 'session_id': _activeSessionId,
            },
            options: ApiClient.ollamaOptions(),
          );
      final sessionId = resp.data['session_id'] as int?;
      final messageId = resp.data['message_id'] as int?;
      if (sessionId == null) {
        throw Exception(AppStrings.of(context).pick(
          'Không nhận được phiên hỏi đáp từ backend.',
          'Did not receive a Q&A session from the backend.',
        ));
      }
      await _loadSessions(preferredSessionId: sessionId);
      if (messageId != null) {
        _scrollToMessage(messageId);
      }
    } catch (error) {
      if (!mounted) return;
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
      return;
    }
    if (!mounted) return;
    // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

    setState(() => _sending = false);
  }

  // Tạo phiên hỏi đáp mới.

  Future<void> _newConversation() async {
    // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

    setState(() {
      _activeSessionId = null;
      _messages = const [];
    });
    _composerCtrl.clear();
    await ConversationBootstrapStore.markConversationChosen(_featureKey);
    await ConversationBootstrapStore.rememberSession(_featureKey, null);
  }

  // Đổi chế độ hỏi đáp (phạm vi tìm kiếm).

  void _changeMode(String mode) {
    if (_mode == mode) return;
    // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

    setState(() {
      _mode = mode;
      _activeSessionId = null;
      _messages = const [];
      _sessions = const [];
      _routeSynced = true;
    });
    // Điều hướng người dùng sang màn phù hợp theo kết quả thao tác hiện tại.

    context
        .go(_selfRoute(modeOverride: mode, sessionId: null, messageId: null));
    _loadSessions();
  }

  // Mở bảng lịch sử phiên (mobile).

  void _openHistorySheet() {
    final strings = AppStrings.of(context);
    showChatHistoryManagerDialog(
      context: context,
      title: _mode == 'document'
          ? strings.pick('Lịch sử hỏi đáp văn bản', 'Document Q&A history')
          : strings.pick('Lịch sử hỏi đáp mẫu văn bản', 'Template Q&A history'),
      emptyLabel:
          strings.pick('Chưa có lịch sử hỏi đáp nào.', 'No Q&A history yet.'),
      listPath: 'ai/rag/sessions/',
      deletePath: 'ai/rag/sessions/',
      messagesPathBuilder: (sessionId) =>
          'ai/rag/sessions/$sessionId/messages/',
      listQueryParameters: {'mode': _mode},
      deleteDataBuilder: (sessionIds) => {
        'mode': _mode,
        'session_ids': sessionIds,
      },
      onOpenSession: (sessionId) => _loadMessages(sessionId),
      onChanged: () async {
        await _loadSessions(preferredSessionId: _activeSessionId);
      },
    );
  }

  // Sinh route tới chính màn này (giữ phiên/tin nhắn).

  String _selfRoute({
    String? modeOverride,
    int? sessionId,
    int? messageId,
  }) {
    final params = <String, String>{
      'mode': (modeOverride ?? _mode) == 'document' ? 'document' : 'template',
    };
    final nextSessionId = sessionId ?? _activeSessionId;
    if (nextSessionId != null) {
      params['rag_session_id'] = '$nextSessionId';
    }
    if (messageId != null) {
      params['rag_message_id'] = '$messageId';
    }
    if (_returnTo != null) {
      params['return_to'] = _returnTo!;
    }
    if (_returnLabel != null) {
      params['return_label'] = _returnLabel!;
    }
    return Uri(path: '/rag', queryParameters: params).toString();
  }

  // Cuộn xuống tin mới nhất.

  void _scrollToBottom() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!_scrollCtrl.hasClients) return;
      _scrollCtrl.animateTo(
        _scrollCtrl.position.maxScrollExtent,
        duration: const Duration(milliseconds: 220),
        curve: Curves.easeOut,
      );
    });
  }

  // Cuộn tới 1 tin nhắn cụ thể.

  void _scrollToMessage(int? messageId) {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!_scrollCtrl.hasClients) return;
      _scrollCtrl.jumpTo(_scrollCtrl.position.maxScrollExtent);
    });
  }

  // Đổi lỗi thành thông điệp dễ đọc.

  String _readableError(Object error) {
    if (error is DioException) {
      final data = error.response?.data;
      if (data is Map && data['error'] != null) return '${data['error']}';
      if (data is Map && data['detail'] != null) return '${data['detail']}';
      return 'Không gọi được hỏi đáp văn bản (${error.response?.statusCode ?? 'network'}).';
    }
    return 'Đã xảy ra lỗi: $error';
  }

  // Hiện thông báo lỗi.

  void _showError(String message) {
    ScaffoldMessenger.of(context)
        .showSnackBar(SnackBar(content: Text(message)));
  }

  @override
  // Khung màn RAG: chọn bố cục mobile/desktop.

  Widget build(BuildContext context) {
    final isWide = MediaQuery.sizeOf(context).width >= 1100;
    return Container(
      color: const Color(0xFFF8FAFC),
      child: isWide
          ? Row(
              children: [
                SizedBox(
                  width: 320,
                  child: _RagSidebar(
                    mode: _mode,
                    sessions: _sessions,
                    activeSessionId: _activeSessionId,
                    loading: _loadingSessions,
                    onModeChanged: _changeMode,
                    onNewConversation: _newConversation,
                    onOpenHistory: _openHistorySheet,
                    onSelect: _loadMessages,
                  ),
                ),
                const VerticalDivider(width: 1),
                Expanded(child: _buildConversation(showHeader: true)),
              ],
            )
          : _buildMobileLayout(),
    );
  }

  // Bố cục mobile: hội thoại toàn màn.

  Widget _buildMobileLayout() {
    final strings = AppStrings.of(context);
    return Column(
      children: [
        Container(
          padding: const EdgeInsets.fromLTRB(14, 14, 14, 12),
          decoration: const BoxDecoration(
            color: Colors.white,
            border: Border(bottom: BorderSide(color: Color(0xFFE2E8F0))),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                strings.pick('Hỏi đáp văn bản', 'Document Q&A'),
                style: TextStyle(fontSize: 22, fontWeight: FontWeight.w800),
              ),
              const SizedBox(height: 8),
              Wrap(
                spacing: 10,
                runSpacing: 10,
                children: [
                  ChoiceChip(
                    label: Text(strings.pick('Mẫu văn bản', 'Templates')),
                    selected: _mode == 'template',
                    onSelected: (_) => _changeMode('template'),
                  ),
                  ChoiceChip(
                    label: Text(strings.pick('Văn bản', 'Documents')),
                    selected: _mode == 'document',
                    onSelected: (_) => _changeMode('document'),
                  ),
                ],
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
                    onPressed: _openHistorySheet,
                    icon: const Icon(Icons.history),
                    label: Text(strings.pick('Lịch sử', 'History')),
                  ),
                ],
              ),
            ],
          ),
        ),
        Expanded(child: _buildConversation(showHeader: false)),
      ],
    );
  }

  // Khung hội thoại RAG: tin nhắn + trích dẫn + ô hỏi.

  Widget _buildConversation({required bool showHeader}) {
    final strings = AppStrings.of(context);
    final showReturn = _returnTo != null && _returnTo!.isNotEmpty;
    return Column(
      children: [
        if (showHeader)
          Container(
            width: double.infinity,
            padding: const EdgeInsets.fromLTRB(24, 18, 24, 14),
            decoration: const BoxDecoration(
              color: Colors.white,
              border: Border(bottom: BorderSide(color: Color(0xFFE2E8F0))),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  strings.pick('Hỏi đáp văn bản', 'Document Q&A'),
                  style: TextStyle(fontSize: 24, fontWeight: FontWeight.w800),
                ),
                const SizedBox(height: 8),
                Text(
                  _mode == 'document'
                      ? strings.pick(
                          'Lịch sử hỏi đáp văn bản được lưu theo từng phiên để mở lại và hỏi tiếp.',
                          'Document Q&A history is stored by session so you can reopen and continue.',
                        )
                      : strings.pick(
                          'Lịch sử hỏi đáp mẫu văn bản được lưu theo từng phiên để mở lại và hỏi tiếp.',
                          'Template Q&A history is stored by session so you can reopen and continue.',
                        ),
                  style: const TextStyle(
                    color: Color(0xFF475569),
                    height: 1.5,
                  ),
                ),
                const SizedBox(height: 12),
                Wrap(
                  spacing: 10,
                  runSpacing: 10,
                  children: [
                    ChoiceChip(
                      label: Text(strings.pick('Mẫu văn bản', 'Templates')),
                      selected: _mode == 'template',
                      onSelected: (_) => _changeMode('template'),
                    ),
                    ChoiceChip(
                      label: Text(strings.pick('Văn bản', 'Documents')),
                      selected: _mode == 'document',
                      onSelected: (_) => _changeMode('document'),
                    ),
                  ],
                ),
              ],
            ),
          ),
        Expanded(
          child: Padding(
            padding: EdgeInsets.fromLTRB(
                showHeader ? 24 : 14, 14, showHeader ? 24 : 14, 0),
            child: Column(
              children: [
                if (showReturn)
                  Container(
                    width: double.infinity,
                    margin: const EdgeInsets.only(bottom: 12),
                    padding: const EdgeInsets.symmetric(
                        horizontal: 14, vertical: 10),
                    decoration: BoxDecoration(
                      color: const Color(0xFFEFF6FF),
                      borderRadius: BorderRadius.circular(14),
                      border: Border.all(color: const Color(0xFFBFDBFE)),
                    ),
                    child: Align(
                      alignment: Alignment.centerLeft,
                      child: TextButton.icon(
                        // Điều hướng người dùng sang màn phù hợp theo kết quả thao tác hiện tại.

                        onPressed: () => context.go(_returnTo!),
                        icon: const Icon(Icons.arrow_back),
                        label: Text(_returnLabel ??
                            strings.pick('Quay về Chat AI', 'Back to Chat AI')),
                      ),
                    ),
                  ),
                Expanded(
                  child: Container(
                    decoration: BoxDecoration(
                      color: Colors.white,
                      borderRadius: BorderRadius.circular(24),
                      border: Border.all(color: const Color(0xFFE2E8F0)),
                    ),
                    child: _loadingMessages
                        ? const Center(child: CircularProgressIndicator())
                        : _messages.isEmpty
                            ? _RagEmptyState(mode: _mode)
                            : ListView.builder(
                                controller: _scrollCtrl,
                                padding: const EdgeInsets.all(18),
                                itemCount: _messages.length,
                                itemBuilder: (_, index) {
                                  final message = _messages[index];
                                  final isUser = message.role == 'user';
                                  if (isUser) {
                                    return Align(
                                      alignment: Alignment.centerRight,
                                      child: Container(
                                        constraints:
                                            const BoxConstraints(maxWidth: 760),
                                        margin: const EdgeInsets.only(
                                            left: 42, bottom: 12),
                                        padding: const EdgeInsets.all(14),
                                        decoration: BoxDecoration(
                                          color: Theme.of(context)
                                              .colorScheme
                                              .primaryContainer,
                                          borderRadius:
                                              BorderRadius.circular(18),
                                        ),
                                        child: Text(message.content),
                                      ),
                                    );
                                  }
                                  return Card(
                                    margin: const EdgeInsets.only(bottom: 12),
                                    child: Padding(
                                      padding: const EdgeInsets.all(16),
                                      child: Column(
                                        crossAxisAlignment:
                                            CrossAxisAlignment.start,
                                        children: [
                                          MarkdownBody(data: message.content),
                                          if (message.citations.isNotEmpty) ...[
                                            const SizedBox(height: 12),
                                            Text(
                                              strings.pick('Nguồn tham khảo:',
                                                  'Sources:'),
                                              style: TextStyle(
                                                fontSize: 12,
                                                fontWeight: FontWeight.w700,
                                              ),
                                            ),
                                            const SizedBox(height: 8),
                                            CitationSections(
                                              citations: message.citations,
                                              returnTo: _selfRoute(
                                                sessionId: _activeSessionId,
                                                messageId: message.id > 0
                                                    ? message.id
                                                    : null,
                                              ),
                                              returnLabel: strings.pick(
                                                'Quay về Hỏi đáp văn bản',
                                                'Back to Document Q&A',
                                              ),
                                            ),
                                          ],
                                        ],
                                      ),
                                    ),
                                  );
                                },
                              ),
                  ),
                ),
                const SizedBox(height: 12),
                Row(
                  children: [
                    Expanded(
                      child: TextField(
                        controller: _composerCtrl,
                        minLines: 1,
                        maxLines: 4,
                        decoration: InputDecoration(
                          hintText: _mode == 'document'
                              ? strings.pick('Đặt câu hỏi về văn bản...',
                                  'Ask about a document...')
                              : strings.pick('Đặt câu hỏi về mẫu văn bản...',
                                  'Ask about a template...'),
                          border: OutlineInputBorder(
                            borderRadius: BorderRadius.circular(18),
                          ),
                        ),
                        onSubmitted: (_) => _send(),
                      ),
                    ),
                    const SizedBox(width: 10),
                    FilledButton(
                      onPressed: _sending ? null : _send,
                      style: FilledButton.styleFrom(
                        padding: const EdgeInsets.symmetric(
                            horizontal: 18, vertical: 18),
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(18),
                        ),
                      ),
                      child: _sending
                          ? const SizedBox(
                              width: 18,
                              height: 18,
                              child:
                                  CircularProgressIndicator(strokeWidth: 2.2),
                            )
                          : const Icon(Icons.send),
                    ),
                  ],
                ),
                const SizedBox(height: 14),
              ],
            ),
          ),
        ),
      ],
    );
  }
}

// Thanh bên: danh sách phiên RAG + tạo mới.

class _RagSidebar extends StatelessWidget {
  final String mode;
  final List<ChatSession> sessions;
  final int? activeSessionId;
  final bool loading;
  final ValueChanged<String> onModeChanged;
  final VoidCallback onNewConversation;
  final VoidCallback onOpenHistory;
  final ValueChanged<int> onSelect;

  const _RagSidebar({
    required this.mode,
    required this.sessions,
    required this.activeSessionId,
    required this.loading,
    required this.onModeChanged,
    required this.onNewConversation,
    required this.onOpenHistory,
    required this.onSelect,
  });

  @override
  // Dựng thanh bên RAG.

  Widget build(BuildContext context) {
    final strings = AppStrings.of(context);
    return Container(
      color: Colors.white,
      padding: const EdgeInsets.fromLTRB(18, 18, 18, 12),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            strings.pick('Hỏi đáp văn bản', 'Document Q&A'),
            style: TextStyle(fontSize: 22, fontWeight: FontWeight.w800),
          ),
          const SizedBox(height: 10),
          Wrap(
            spacing: 10,
            runSpacing: 10,
            children: [
              ChoiceChip(
                label: Text(strings.pick('Mẫu văn bản', 'Templates')),
                selected: mode == 'template',
                onSelected: (_) => onModeChanged('template'),
              ),
              ChoiceChip(
                label: Text(strings.pick('Văn bản', 'Documents')),
                selected: mode == 'document',
                onSelected: (_) => onModeChanged('document'),
              ),
            ],
          ),
          const SizedBox(height: 14),
          SizedBox(
            width: double.infinity,
            child: FilledButton.icon(
              onPressed: onNewConversation,
              icon: const Icon(Icons.add_comment_outlined),
              label: Text(strings.pick('Phiên mới', 'New session')),
            ),
          ),
          const SizedBox(height: 10),
          SizedBox(
            width: double.infinity,
            child: OutlinedButton.icon(
              onPressed: onOpenHistory,
              icon: const Icon(Icons.history),
              label: Text(strings.pick('Quản lý lịch sử', 'Manage history')),
            ),
          ),
          const SizedBox(height: 14),
          Expanded(
            child: _RagSessionList(
              sessions: sessions,
              activeSessionId: activeSessionId,
              loading: loading,
              onNewConversation: onNewConversation,
              onSelect: onSelect,
            ),
          ),
        ],
      ),
    );
  }
}

// Danh sách phiên hỏi đáp.

class _RagSessionList extends StatelessWidget {
  final List<ChatSession> sessions;
  final int? activeSessionId;
  final bool loading;
  final VoidCallback onNewConversation;
  final ValueChanged<int> onSelect;

  const _RagSessionList({
    required this.sessions,
    required this.activeSessionId,
    required this.loading,
    required this.onNewConversation,
    required this.onSelect,
  });

  @override
  // Dựng danh sách phiên.

  Widget build(BuildContext context) {
    final strings = AppStrings.of(context);
    if (loading) {
      return const Center(child: CircularProgressIndicator());
    }
    if (sessions.isEmpty) {
      return Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.history_toggle_off,
                size: 42, color: Color(0xFF94A3B8)),
            const SizedBox(height: 10),
            Text(
              strings.pick('Chưa có lịch sử hỏi đáp', 'No Q&A history yet'),
              style: TextStyle(fontWeight: FontWeight.w700),
            ),
            const SizedBox(height: 6),
            Text(
              strings.pick(
                'Bắt đầu một phiên mới để lưu lịch sử vào đây.',
                'Start a new session to store history here.',
              ),
              textAlign: TextAlign.center,
              style: TextStyle(color: Color(0xFF64748B), height: 1.5),
            ),
            const SizedBox(height: 12),
            OutlinedButton.icon(
              onPressed: onNewConversation,
              icon: const Icon(Icons.add),
              label: Text(strings.pick('Phiên mới', 'New session')),
            ),
          ],
        ),
      );
    }
    return ListView.separated(
      itemCount: sessions.length,
      separatorBuilder: (_, __) => const SizedBox(height: 10),
      itemBuilder: (_, index) {
        final session = sessions[index];
        final active = session.id == activeSessionId;
        final time = session.updatedAt.isNotEmpty
            ? session.updatedAt
            : session.createdAt;
        return Material(
          color: active ? const Color(0xFFEFF6FF) : const Color(0xFFF8FAFC),
          borderRadius: BorderRadius.circular(18),
          child: InkWell(
            borderRadius: BorderRadius.circular(18),
            onTap: () => onSelect(session.id),
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
                    strings.pick(
                      '${session.messageCount} tin nhắn',
                      '${session.messageCount} messages',
                    ),
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
        );
      },
    );
  }
}

// Trạng thái trống khi chưa hỏi gì.

class _RagEmptyState extends StatelessWidget {
  final String mode;

  const _RagEmptyState({required this.mode});

  @override
  // Dựng trạng thái trống.

  Widget build(BuildContext context) {
    final strings = AppStrings.of(context);
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              mode == 'document'
                  ? Icons.article_outlined
                  : Icons.description_outlined,
              size: 58,
              color: const Color(0xFF94A3B8),
            ),
            const SizedBox(height: 14),
            Text(
              mode == 'document'
                  ? strings.pick(
                      'Đặt câu hỏi về văn bản để bắt đầu một phiên mới.',
                      'Ask about a document to start a new session.',
                    )
                  : strings.pick(
                      'Đặt câu hỏi về mẫu văn bản để bắt đầu một phiên mới.',
                      'Ask about a template to start a new session.',
                    ),
              textAlign: TextAlign.center,
              style: const TextStyle(
                fontWeight: FontWeight.w700,
                fontSize: 16,
              ),
            ),
            const SizedBox(height: 10),
            Text(
              strings.pick(
                'Các phiên từ chức năng này và kết quả hỏi đáp từ Chat AI sẽ được lưu chung vào lịch sử.',
                'Sessions from this view and Chat AI Q&A results are stored together in history.',
              ),
              textAlign: TextAlign.center,
              style: const TextStyle(color: Color(0xFF64748B), height: 1.6),
            ),
          ],
        ),
      ),
    );
  }
}
