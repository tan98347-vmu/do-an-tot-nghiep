// Tệp này dùng để: dựng giao diện và orchestration UI trong flutter_frontend/lib/screens/assistant/assistant_audio_library_screen.dart.
// Cách hoạt động: nhận state từ provider, dựng widget, phản ứng sự kiện và gửi thao tác ngược về backend khi người dùng tương tác.
// Vai trò trong hệ thống: Đây là màn hình Flutter mà người dùng tương tác trực tiếp.
// Tác dụng khi hệ thống vận hành: biến nghiệp vụ backend thành trải nghiệm thao tác cụ thể trên web.

import 'dart:html' as html;

import 'package:dio/dio.dart';
import 'package:flutter/material.dart';

import '../../core/api_client.dart';
import '../../models/chat.dart';
import '../../widgets/tasks/task_done_popup.dart';

// Mục đích: Widget `AssistantAudioLibraryScreen` triển khai phần việc `Assistant Audio Library Screen` trong flutter_frontend/lib/screens/assistant/assistant_audio_library_screen.dart.
// Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
// Vai trò trong hệ thống: Đây là widget thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
// Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

class AssistantAudioLibraryScreen extends StatefulWidget {
  const AssistantAudioLibraryScreen({super.key});

  @override
  State<AssistantAudioLibraryScreen> createState() => _AssistantAudioLibraryScreenState();
}

// Mục đích: Widget `_AssistantAudioLibraryScreenState` triển khai phần việc `Assistant Audio Library Screen State` trong flutter_frontend/lib/screens/assistant/assistant_audio_library_screen.dart.
// Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
// Vai trò trong hệ thống: Đây là widget thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
// Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

class _AssistantAudioLibraryScreenState extends State<AssistantAudioLibraryScreen> {
  bool _loading = true;
  String? _error;
  List<ChatAudioAttachment> _items = const [];
  html.AudioElement? _player;
  int? _playingId;

  @override
  // Mục đích: Phương thức `initState` triển khai phần việc `init State` trong flutter_frontend/lib/screens/assistant/assistant_audio_library_screen.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  void initState() {
    super.initState();
    _load();
  }

  // Mục đích: Phương thức `_load` triển khai phần việc `load` trong flutter_frontend/lib/screens/assistant/assistant_audio_library_screen.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  Future<void> _load() async {
    // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      // Gọi API hoặc tác vụ bất đồng bộ rồi chờ kết quả trước khi cập nhật giao diện.

      final resp = await ApiClient().dio.get('assistant/audio/');
      final items = (resp.data as List<dynamic>)
          .map((item) => ChatAudioAttachment.fromJson(Map<String, dynamic>.from(item as Map)))
          .toList();
      if (!mounted) return;
      // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

      setState(() {
        _items = items;
        _loading = false;
      });
    } on DioException catch (error) {
      if (!mounted) return;
      // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

      setState(() {
        _error = error.response?.data?['detail']?.toString() ?? error.message;
        _loading = false;
      });
    } catch (error) {
      if (!mounted) return;
      // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

      setState(() {
        _error = error.toString();
        _loading = false;
      });
    }
  }

  // Mục đích: Phương thức `_downloadAudio` triển khai phần việc `download Audio` trong flutter_frontend/lib/screens/assistant/assistant_audio_library_screen.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  Future<void> _downloadAudio(ChatAudioAttachment item) async {
    try {
      // Gọi API hoặc tác vụ bất đồng bộ rồi chờ kết quả trước khi cập nhật giao diện.

      final resp = await ApiClient().dio.get(
        'assistant/audio/${item.id}/download/',
        options: Options(responseType: ResponseType.bytes),
      );
      final bytes = resp.data as List<int>;
      final blob = html.Blob([bytes], item.mimeType.isEmpty ? 'audio/webm' : item.mimeType);
      final url = html.Url.createObjectUrlFromBlob(blob);
      html.AnchorElement(href: url)
        ..setAttribute('download', item.title.isEmpty ? 'audio_${item.id}.webm' : item.title)
        ..click();
      html.Url.revokeObjectUrl(url);
    } on DioException catch (error) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(error.response?.data?['detail']?.toString() ?? 'Khong tai duoc file audio.')),
      );
    }
  }

  // Mục đích: Phương thức `_togglePlayback` triển khai phần việc `toggle Playback` trong flutter_frontend/lib/screens/assistant/assistant_audio_library_screen.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  Future<void> _togglePlayback(ChatAudioAttachment item) async {
    try {
      if (_playingId == item.id && _player != null) {
        _player!.pause();
        if (!mounted) return;
        // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

        setState(() => _playingId = null);
        return;
      }
      _player?.pause();
      final nextPlayer = html.AudioElement(item.downloadUrl)
        ..autoplay = true
        ..controls = false;
      nextPlayer.onEnded.listen((_) {
        if (!mounted) return;
        // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

        setState(() => _playingId = null);
      });
      await nextPlayer.play();
      if (!mounted) return;
      // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

      setState(() {
        _player = nextPlayer;
        _playingId = item.id;
      });
    } catch (error) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Không phát được audio: $error')),
      );
    }
  }

  // Mục đích: Phương thức `_formatDateTime` triển khai phần việc `format Date Time` trong flutter_frontend/lib/screens/assistant/assistant_audio_library_screen.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  String _formatDateTime(String value) {
    if (value.trim().isEmpty) return '—';
    try {
      final d = DateTime.parse(value).toLocal();
      final day = d.day.toString().padLeft(2, '0');
      final month = d.month.toString().padLeft(2, '0');
      final hour = d.hour.toString().padLeft(2, '0');
      final minute = d.minute.toString().padLeft(2, '0');
      return '$day/$month/${d.year} $hour:$minute';
    } catch (_) {
      return value;
    }
  }

  @override
  // Mục đích: Phương thức `dispose` triển khai phần việc `dispose` trong flutter_frontend/lib/screens/assistant/assistant_audio_library_screen.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  void dispose() {
    _player?.pause();
    _player = null;
    super.dispose();
  }

  @override
  // Mục đích: Phương thức `build` triển khai phần việc `build` trong flutter_frontend/lib/screens/assistant/assistant_audio_library_screen.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc màn hình Flutter mà người dùng tương tác trực tiếp.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  Widget build(BuildContext context) {
    // Dựng khung màn hình chính để chứa app bar, body, action và các vùng giao diện khác.

    return TaskDonePopupHost(
      child: Scaffold(
        appBar: AppBar(
          title: const Text('Thu vien audio Chat AI'),
          actions: [
            IconButton(onPressed: _load, icon: const Icon(Icons.refresh)),
          ],
        ),
        body: RefreshIndicator(
          onRefresh: _load,
          child: _loading
              ? const Center(child: CircularProgressIndicator())
              : _error != null
                  ? ListView(
                      children: [
                        Padding(
                          padding: const EdgeInsets.all(24),
                          child: Text('Loi: $_error'),
                        ),
                      ],
                    )
                  : ListView(
                      padding: const EdgeInsets.all(16),
                      children: [
                        if (_items.isEmpty)
                          const Card(
                            child: Padding(
                              padding: EdgeInsets.all(20),
                              child: Text(
                                  'Chua co file audio nao duoc luu tu Chat AI.'),
                            ),
                          )
                        else
                          ..._items.map((item) => Card(
                                margin: const EdgeInsets.only(bottom: 12),
                                child: Padding(
                                  padding: const EdgeInsets.all(16),
                                  child: Column(
                                    crossAxisAlignment:
                                        CrossAxisAlignment.start,
                                    children: [
                                      Row(
                                        children: [
                                          const Icon(Icons.audiotrack_outlined),
                                          const SizedBox(width: 8),
                                          Expanded(
                                            child: Text(
                                              item.title.isEmpty
                                                  ? 'Voice ${item.id}'
                                                  : item.title,
                                              style: const TextStyle(
                                                fontSize: 16,
                                                fontWeight: FontWeight.w700,
                                              ),
                                            ),
                                          ),
                                        ],
                                      ),
                                      const SizedBox(height: 10),
                                      Text(
                                        'Session: ${item.sessionTitle.isEmpty ? 'Session ${item.sessionId}' : item.sessionTitle}',
                                      ),
                                      Text(
                                          'Thoi gian: ${_formatDateTime(item.createdAt)}'),
                                      if (item.durationSeconds > 0)
                                        Text(
                                            'Do dai: ${item.durationSeconds.toStringAsFixed(1)} giay'),
                                      if (item.transcript.trim().isNotEmpty) ...[
                                        const SizedBox(height: 10),
                                        const Text(
                                          'Transcript',
                                          style: TextStyle(
                                              fontWeight: FontWeight.w700),
                                        ),
                                        const SizedBox(height: 6),
                                        Text(item.transcript),
                                      ],
                                      const SizedBox(height: 12),
                                      Wrap(
                                        spacing: 8,
                                        runSpacing: 8,
                                        children: [
                                          FilledButton.icon(
                                            onPressed: () =>
                                                _togglePlayback(item),
                                            icon: Icon(
                                              _playingId == item.id
                                                  ? Icons.pause_circle_outline
                                                  : Icons.play_circle_outline,
                                            ),
                                            label: Text(
                                              _playingId == item.id
                                                  ? 'Tam dung'
                                                  : 'Phat lai',
                                            ),
                                          ),
                                          OutlinedButton.icon(
                                            onPressed: () =>
                                                _downloadAudio(item),
                                            icon: const Icon(
                                                Icons.download_outlined),
                                            label:
                                                const Text('Tai file audio'),
                                          ),
                                        ],
                                      ),
                                    ],
                                  ),
                                ),
                              )),
                      ],
                    ),
        ),
      ),
    );
  }
}
