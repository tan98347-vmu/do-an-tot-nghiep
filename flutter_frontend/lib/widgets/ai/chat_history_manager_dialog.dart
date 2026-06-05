// Tệp này dùng để: đóng gói khối giao diện hoặc hành vi lặp lại trong flutter_frontend/lib/widgets/ai/chat_history_manager_dialog.dart.
// Cách hoạt động: được gọi từ lớp phía trên, xử lý dữ liệu theo vai trò hiện có và trả kết quả về cho luồng gọi.
// Vai trò trong hệ thống: Đây là widget tái sử dụng của Flutter.
// Tác dụng khi hệ thống vận hành: giúp các màn hình dùng lại cùng một cách hiển thị hoặc tương tác.

import 'dart:html' as html;

import 'package:dio/dio.dart';
import 'package:flutter/material.dart';

import '../../core/api_client.dart';
import '../../l10n/app_strings.dart';
import '../../models/chat.dart';

// Mục đích: Hàm `showChatHistoryManagerDialog` triển khai phần việc `show Chat History Manager Dialog` trong flutter_frontend/lib/widgets/ai/chat_history_manager_dialog.dart.
// Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
// Vai trò trong hệ thống: Đây là hàm thuộc widget tái sử dụng của Flutter.
// Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

Future<void> showChatHistoryManagerDialog({
  required BuildContext context,
  required String title,
  required String emptyLabel,
  required String listPath,
  required String deletePath,
  required String Function(int sessionId) messagesPathBuilder,
  required Map<String, dynamic> listQueryParameters,
  required Map<String, dynamic> Function(List<int> sessionIds)
      deleteDataBuilder,
  required Future<void> Function(int sessionId) onOpenSession,
  required Future<void> Function() onChanged,
}) {
  return showDialog<void>(
    context: context,
    builder: (_) => _ChatHistoryManagerDialog(
      title: title,
      emptyLabel: emptyLabel,
      listPath: listPath,
      deletePath: deletePath,
      messagesPathBuilder: messagesPathBuilder,
      listQueryParameters: listQueryParameters,
      deleteDataBuilder: deleteDataBuilder,
      onOpenSession: onOpenSession,
      onChanged: onChanged,
    ),
  );
}

// Mục đích: Lớp `_ChatHistoryManagerDialog` triển khai phần việc `Chat History Manager Dialog` trong flutter_frontend/lib/widgets/ai/chat_history_manager_dialog.dart.
// Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
// Vai trò trong hệ thống: Đây là lớp thuộc widget tái sử dụng của Flutter.
// Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

class _ChatHistoryManagerDialog extends StatefulWidget {
  final String title;
  final String emptyLabel;
  final String listPath;
  final String deletePath;
  final String Function(int sessionId) messagesPathBuilder;
  final Map<String, dynamic> listQueryParameters;
  final Map<String, dynamic> Function(List<int> sessionIds) deleteDataBuilder;
  final Future<void> Function(int sessionId) onOpenSession;
  final Future<void> Function() onChanged;

  const _ChatHistoryManagerDialog({
    required this.title,
    required this.emptyLabel,
    required this.listPath,
    required this.deletePath,
    required this.messagesPathBuilder,
    required this.listQueryParameters,
    required this.deleteDataBuilder,
    required this.onOpenSession,
    required this.onChanged,
  });

  @override
  State<_ChatHistoryManagerDialog> createState() =>
      _ChatHistoryManagerDialogState();
}

// Mục đích: Lớp `_ChatHistoryManagerDialogState` triển khai phần việc `Chat History Manager Dialog State` trong flutter_frontend/lib/widgets/ai/chat_history_manager_dialog.dart.
// Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
// Vai trò trong hệ thống: Đây là lớp thuộc widget tái sử dụng của Flutter.
// Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

class _ChatHistoryManagerDialogState extends State<_ChatHistoryManagerDialog> {
  List<ChatSession> _sessions = const [];
  final Set<int> _selectedIds = <int>{};
  bool _loading = true;
  bool _selectionMode = false;
  bool _busy = false;
  String? _error;

  @override
  // Mục đích: Phương thức `initState` triển khai phần việc `init State` trong flutter_frontend/lib/widgets/ai/chat_history_manager_dialog.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc widget tái sử dụng của Flutter.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  void initState() {
    super.initState();
    _loadSessions();
  }

  // Mục đích: Phương thức `_loadSessions` triển khai phần việc `load Sessions` trong flutter_frontend/lib/widgets/ai/chat_history_manager_dialog.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc widget tái sử dụng của Flutter.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  Future<void> _loadSessions() async {
    if (!mounted) return;
    // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      // Gọi API hoặc tác vụ bất đồng bộ rồi chờ kết quả trước khi cập nhật giao diện.

      final resp = await ApiClient().dio.get(
            widget.listPath,
            queryParameters: widget.listQueryParameters,
          );
      final sessions = (resp.data as List<dynamic>)
          .map((item) => ChatSession.fromJson(Map<String, dynamic>.from(item)))
          .toList();
      if (!mounted) return;
      // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

      setState(() {
        _sessions = sessions;
        _selectedIds
            .removeWhere((id) => !sessions.any((item) => item.id == id));
        _loading = false;
      });
    } catch (error) {
      if (!mounted) return;
      // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

      setState(() {
        _loading = false;
        _error = _readableError(error);
      });
    }
  }

  // Mục đích: Phương thức `_readableError` triển khai phần việc `readable Error` trong flutter_frontend/lib/widgets/ai/chat_history_manager_dialog.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc widget tái sử dụng của Flutter.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  String _readableError(Object error) {
    final strings = AppStrings.of(context);
    if (error is DioException) {
      final data = error.response?.data;
      if (data is Map && data['detail'] != null) return '${data['detail']}';
      if (data is Map && data['error'] != null) return '${data['error']}';
      return strings.pick(
        'Không thể tải lịch sử (${error.response?.statusCode ?? 'network'}).',
        'Unable to load history (${error.response?.statusCode ?? 'network'}).',
      );
    }
    return strings.pick(
      'Không thể tải lịch sử: $error',
      'Unable to load history: $error',
    );
  }

  // Mục đích: Phương thức `_deleteSelected` triển khai phần việc `delete Selected` trong flutter_frontend/lib/widgets/ai/chat_history_manager_dialog.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc widget tái sử dụng của Flutter.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  Future<void> _deleteSelected() async {
    final strings = AppStrings.of(context);
    final ids = _selectedIds.toList();
    if (ids.isEmpty || _busy) return;
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text(strings.pick('Chuyển vào thùng rác', 'Move to trash')),
        content: Text(
          ids.length == 1
              ? strings.pick(
                  'Phiên đã chọn sẽ được đưa vào thùng rác và có thể khôi phục lại trong 30 ngày.',
                  'The selected session will be moved to trash and can be restored within 30 days.',
                )
              : strings.pick(
                  '${ids.length} phiên đã chọn sẽ được đưa vào thùng rác và có thể khôi phục lại trong 30 ngày.',
                  '${ids.length} selected sessions will be moved to trash and can be restored within 30 days.',
                ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx, false),
            child: Text(strings.pick('Hủy', 'Cancel')),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(ctx, true),
            child: Text(strings.pick('Chuyển vào thùng rác', 'Move to trash')),
          ),
        ],
      ),
    );
    if (ok != true) return;

    // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

    setState(() => _busy = true);
    try {
      // Gọi API hoặc tác vụ bất đồng bộ rồi chờ kết quả trước khi cập nhật giao diện.

      await ApiClient().dio.delete(
            widget.deletePath,
            data: widget.deleteDataBuilder(ids),
          );
      if (!mounted) return;
      // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

      setState(() {
        _selectedIds.clear();
        _selectionMode = false;
      });
      await widget.onChanged();
      await _loadSessions();
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            ids.length == 1
                ? strings.pick(
                    'Đã chuyển 1 phiên vào thùng rác.',
                    'Moved 1 session to trash.',
                  )
                : strings.pick(
                    'Đã chuyển ${ids.length} phiên vào thùng rác.',
                    'Moved ${ids.length} sessions to trash.',
                  ),
          ),
        ),
      );
    } catch (error) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(_readableError(error)),
          backgroundColor: Colors.red,
        ),
      );
    } finally {
      // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

      if (mounted) setState(() => _busy = false);
    }
  }

  // Mục đích: Phương thức `_openSessionDetail` triển khai phần việc `open Session Detail` trong flutter_frontend/lib/widgets/ai/chat_history_manager_dialog.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc widget tái sử dụng của Flutter.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  Future<void> _openSessionDetail(ChatSession session) async {
    final strings = AppStrings.of(context);
    List<ChatMessage> messages = const [];
    String? error;
    try {
      // Gọi API hoặc tác vụ bất đồng bộ rồi chờ kết quả trước khi cập nhật giao diện.

      final resp =
          await ApiClient().dio.get(widget.messagesPathBuilder(session.id));
      messages = (resp.data as List<dynamic>)
          .map((item) => ChatMessage.fromJson(Map<String, dynamic>.from(item)))
          .toList();
    } catch (err) {
      error = _readableError(err);
    }
    if (!mounted) return;
    await showDialog<void>(
      context: context,
      builder: (ctx) => Dialog(
        child: SizedBox(
          width: 720,
          height: MediaQuery.of(ctx).size.height * 0.8,
          child: Column(
            children: [
              Padding(
                padding: const EdgeInsets.fromLTRB(18, 14, 12, 10),
                child: Row(
                  children: [
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            session.title,
                            style: const TextStyle(
                                fontSize: 18, fontWeight: FontWeight.w700),
                          ),
                          const SizedBox(height: 4),
                          Text(
                            strings.pick(
                              '${session.messageCount} tin nhắn',
                              '${session.messageCount} messages',
                            ),
                            style: const TextStyle(color: Color(0xFF64748B)),
                          ),
                        ],
                      ),
                    ),
                    IconButton(
                      onPressed: () => Navigator.pop(ctx),
                      icon: const Icon(Icons.close),
                    ),
                  ],
                ),
              ),
              const Divider(height: 1),
              Expanded(
                child: error != null
                    ? Center(child: Text(error))
                    : messages.isEmpty
                        ? Center(
                            child: Text(
                              strings.pick(
                                'Phiên này chưa có nội dung.',
                                'This session has no content yet.',
                              ),
                            ),
                          )
                        : ListView.separated(
                            padding: const EdgeInsets.all(16),
                            itemCount: messages.length,
                            separatorBuilder: (_, __) =>
                                const SizedBox(height: 10),
                            itemBuilder: (context, index) {
                              final message = messages[index];
                              final isUser = message.role == 'user';
                              return Align(
                                alignment: isUser
                                    ? Alignment.centerRight
                                    : Alignment.centerLeft,
                                child: Container(
                                  constraints:
                                      const BoxConstraints(maxWidth: 560),
                                  padding: const EdgeInsets.all(14),
                                  decoration: BoxDecoration(
                                    color: isUser
                                        ? const Color(0xFFDBEAFE)
                                        : const Color(0xFFF8FAFC),
                                    borderRadius: BorderRadius.circular(16),
                                    border: Border.all(
                                        color: const Color(0xFFE2E8F0)),
                                  ),
                                  child: Column(
                                    crossAxisAlignment:
                                        CrossAxisAlignment.start,
                                    children: [
                                      Text(
                                        isUser
                                            ? strings.pick('Người dùng', 'User')
                                            : 'AI',
                                        style: const TextStyle(
                                          fontSize: 12,
                                          fontWeight: FontWeight.w700,
                                          color: Color(0xFF475569),
                                        ),
                                      ),
                                      const SizedBox(height: 8),
                                      SelectableText(message.content),
                                      if (message
                                          .audioAttachments.isNotEmpty) ...[
                                        const SizedBox(height: 10),
                                        Wrap(
                                          spacing: 8,
                                          runSpacing: 8,
                                          children: message.audioAttachments
                                              .map((attachment) {
                                            return OutlinedButton.icon(
                                              onPressed: () => html.window.open(
                                                  attachment.downloadUrl,
                                                  '_blank'),
                                              icon: const Icon(
                                                  Icons.download_outlined,
                                                  size: 18),
                                              label: Text(
                                                attachment.title.isEmpty
                                                    ? 'Audio ${attachment.id}'
                                                    : attachment.title,
                                              ),
                                            );
                                          }).toList(),
                                        ),
                                      ],
                                    ],
                                  ),
                                ),
                              );
                            },
                          ),
              ),
              const Divider(height: 1),
              Padding(
                padding: const EdgeInsets.all(12),
                child: Row(
                  children: [
                    TextButton(
                      onPressed: () => Navigator.pop(ctx),
                      child: Text(strings.pick('Đóng', 'Close')),
                    ),
                    const Spacer(),
                    FilledButton.icon(
                      onPressed: () async {
                        Navigator.pop(ctx);
                        Navigator.pop(context);
                        await widget.onOpenSession(session.id);
                      },
                      icon: const Icon(Icons.open_in_new),
                      label: Text(
                          strings.pick('Mở phiên này', 'Open this session')),
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

  @override
  // Mục đích: Phương thức `build` triển khai phần việc `build` trong flutter_frontend/lib/widgets/ai/chat_history_manager_dialog.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc widget tái sử dụng của Flutter.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  Widget build(BuildContext context) {
    final strings = AppStrings.of(context);
    final allSelected = _sessions.isNotEmpty &&
        _sessions.every((session) => _selectedIds.contains(session.id));
    return Dialog(
      child: SizedBox(
        width: 760,
        height: MediaQuery.of(context).size.height * 0.82,
        child: Column(
          children: [
            Padding(
              padding: const EdgeInsets.fromLTRB(18, 16, 12, 12),
              child: Row(
                children: [
                  Expanded(
                    child: Text(
                      widget.title,
                      style: const TextStyle(
                          fontSize: 20, fontWeight: FontWeight.w800),
                    ),
                  ),
                  if (_selectionMode) ...[
                    TextButton(
                      onPressed: _sessions.isEmpty
                          ? null
                          : () {
                              // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

                              setState(() {
                                if (allSelected) {
                                  _selectedIds.clear();
                                } else {
                                  _selectedIds
                                    ..clear()
                                    ..addAll(_sessions.map((item) => item.id));
                                }
                              });
                            },
                      child: Text(
                        allSelected
                            ? strings.pick('Bỏ chọn tất cả', 'Clear all')
                            : strings.pick('Chọn tất cả', 'Select all'),
                      ),
                    ),
                    const SizedBox(width: 8),
                    FilledButton.tonalIcon(
                      onPressed: _selectedIds.isEmpty || _busy
                          ? null
                          : _deleteSelected,
                      icon: const Icon(Icons.delete_outline),
                      label: Text(strings.pick(
                          'Chuyển vào thùng rác', 'Move to trash')),
                    ),
                    const SizedBox(width: 8),
                    TextButton(
                      onPressed: _busy
                          ? null
                          : () {
                              // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

                              setState(() {
                                _selectionMode = false;
                                _selectedIds.clear();
                              });
                            },
                      child: Text(strings.pick('Xong', 'Done')),
                    ),
                  ] else ...[
                    OutlinedButton.icon(
                      onPressed: _busy
                          ? null
                          // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

                          : () => setState(() => _selectionMode = true),
                      icon: const Icon(Icons.checklist),
                      label: Text(strings.pick('Chọn', 'Select')),
                    ),
                  ],
                  IconButton(
                    onPressed: () => Navigator.pop(context),
                    icon: const Icon(Icons.close),
                  ),
                ],
              ),
            ),
            const Divider(height: 1),
            Expanded(
              child: _loading
                  ? const Center(child: CircularProgressIndicator())
                  : _error != null
                      ? Center(child: Text(_error!))
                      : _sessions.isEmpty
                          ? Center(child: Text(widget.emptyLabel))
                          : ListView.separated(
                              padding: const EdgeInsets.all(16),
                              itemCount: _sessions.length,
                              separatorBuilder: (_, __) =>
                                  const SizedBox(height: 10),
                              itemBuilder: (context, index) {
                                final session = _sessions[index];
                                final selected =
                                    _selectedIds.contains(session.id);
                                final time = session.updatedAt.isNotEmpty
                                    ? session.updatedAt
                                    : session.createdAt;
                                return Material(
                                  color: selected
                                      ? const Color(0xFFEFF6FF)
                                      : const Color(0xFFF8FAFC),
                                  borderRadius: BorderRadius.circular(16),
                                  child: InkWell(
                                    borderRadius: BorderRadius.circular(16),
                                    onTap: () {
                                      if (_selectionMode) {
                                        // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

                                        setState(() {
                                          if (selected) {
                                            _selectedIds.remove(session.id);
                                          } else {
                                            _selectedIds.add(session.id);
                                          }
                                        });
                                        return;
                                      }
                                      _openSessionDetail(session);
                                    },
                                    child: Padding(
                                      padding: const EdgeInsets.all(14),
                                      child: Row(
                                        children: [
                                          if (_selectionMode)
                                            Checkbox(
                                              value: selected,
                                              onChanged: (value) {
                                                // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

                                                setState(() {
                                                  if (value == true) {
                                                    _selectedIds
                                                        .add(session.id);
                                                  } else {
                                                    _selectedIds
                                                        .remove(session.id);
                                                  }
                                                });
                                              },
                                            ),
                                          Expanded(
                                            child: Column(
                                              crossAxisAlignment:
                                                  CrossAxisAlignment.start,
                                              children: [
                                                Text(
                                                  session.title,
                                                  maxLines: 2,
                                                  overflow:
                                                      TextOverflow.ellipsis,
                                                  style: const TextStyle(
                                                      fontWeight:
                                                          FontWeight.w700),
                                                ),
                                                const SizedBox(height: 6),
                                                Text(
                                                  strings.pick(
                                                    '${session.messageCount} tin nhắn${session.audioCount > 0 ? ' • ${session.audioCount} audio' : ''}',
                                                    '${session.messageCount} messages${session.audioCount > 0 ? ' • ${session.audioCount} audio' : ''}',
                                                  ),
                                                  style: const TextStyle(
                                                    fontSize: 12,
                                                    color: Color(0xFF64748B),
                                                  ),
                                                ),
                                                const SizedBox(height: 4),
                                                Text(
                                                  time.replaceFirst('T', ' '),
                                                  style: const TextStyle(
                                                    fontSize: 12,
                                                    color: Color(0xFF94A3B8),
                                                  ),
                                                ),
                                              ],
                                            ),
                                          ),
                                          if (!_selectionMode)
                                            IconButton(
                                              onPressed: () =>
                                                  _openSessionDetail(session),
                                              icon: const Icon(
                                                  Icons.chevron_right),
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
  }
}
