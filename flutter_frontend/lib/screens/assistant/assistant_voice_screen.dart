// === MÀN HÌNH TRỢ LÝ GIỌNG NÓI (VoiceAI) ===
// Thu âm -> nhận dạng giọng nói -> gửi cho trợ lý:
// - _initVoice/_bindVoiceEvents: cầu nối Web Speech qua _callBridge; _submitTranscript -> 'assistant/turn-async/' (hoặc 'turn/').
// - Theo dõi tiến độ (aiTaskProgressProvider), hủy tác vụ (_cancelCurrentVoiceTask 'ai-tasks/<id>/cancel/'). Vòng tròn ghi âm động (_VoiceCircle/_VoiceRingPainter). Link sang /chat.

// Tệp này dùng để: dựng giao diện và orchestration UI trong flutter_frontend/lib/screens/assistant/assistant_voice_screen.dart.
import 'dart:async';
import 'dart:html' as html;
import 'dart:js_util' as js_util;
import 'dart:math' as math;
import 'dart:typed_data';

import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/api_client.dart';
import '../../core/conversation_bootstrap.dart';
import '../../core/run_ai_task.dart';
import '../../l10n/app_strings.dart';
import '../../models/ai_task_state.dart';
import '../../models/assistant_quick_sign.dart';
import '../../models/chat.dart';
import '../../providers/ai_task_progress_provider.dart';
import '../../providers/chat_ai_model_provider.dart';
import '../../widgets/ai/chat_attachment_row.dart';
import '../../widgets/ai/chat_history_manager_dialog.dart';
import '../../widgets/ai/prefill_toggle_row.dart';
import '../../widgets/tasks/task_done_popup.dart';

// Widget màn CHATAI GIỌNG NÓI (VoiceAI) — ConsumerStatefulWidget.

class AssistantVoiceScreen extends ConsumerStatefulWidget {
  final int? conversationId;

  const AssistantVoiceScreen({
    super.key,
    this.conversationId,
  });

  @override
  ConsumerState<AssistantVoiceScreen> createState() => _AssistantVoiceScreenState();
}

// State màn voice: thu âm, nhận diện giọng nói, phát lại, tác vụ trợ lý, điều hướng.

class _AssistantVoiceScreenState extends ConsumerState<AssistantVoiceScreen> {
  static const _featureKey = ConversationBootstrapStore.assistantVoiceFeature;
  String? _currentVoiceTaskId;

  StreamSubscription<html.Event>? _statusSub;
  StreamSubscription<html.Event>? _resultSub;
  StreamSubscription<html.Event>? _readySub;
  StreamSubscription<html.Event>? _errorSub;
  StreamSubscription<html.Event>? _debugSub;
  StreamSubscription<html.Event>? _speechEndSub;
  StreamSubscription<html.Event>? _recordDataSub;
  StreamSubscription<html.Event>? _recordStopSub;

  final List<String> _debugLines = <String>[];
  final List<html.Blob> _recordedChunks = <html.Blob>[];
  List<ChatMessage> _messages = const [];
  int? _sessionId;
  bool _supported = false;
  bool _loading = true;
  bool _speakerOn = true;
  bool _requestInFlight = false;
  html.AudioElement? _messageAudioPlayer;
  int? _playingAudioAttachmentId;
  Timer? _navigationFallbackTimer;
  String _status = 'idle';
  String _liveTranscript = '';
  String? _pendingNavigationRoute;
  html.MediaRecorder? _mediaRecorder;
  dynamic _mediaStream;
  html.Blob? _pendingAudioBlob;
  double _pendingAudioDurationSeconds = 0;
  DateTime? _recordingStartedAt;
  bool _autoFillProfile = true;
  bool _autoFillCompany = true;
  final List<ChatAttachmentItem> _pendingAttachments = [];

  @override
  // Mở màn: khởi tạo voice + nạp phiên.

  void initState() {
    super.initState();
    _bindVoiceEvents();
    _initVoice();
  }

  // Ghi log debug cho luồng voice.

  void _voiceDebug(String message) {
    final line = '[assistant_voice_ui] $message';
    print(line);
    try {
      html.window.console.log(line);
    } catch (_) {}
    if (!mounted) return;
    // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

    setState(() {
      _debugLines.add(line);
      if (_debugLines.length > 80) {
        _debugLines.removeRange(0, _debugLines.length - 80);
      }
    });
  }

  // Khởi tạo cầu nối voice (bridge JS) + kiểm hỗ trợ.

  Future<void> _initVoice() async {
    final supported = _isVoiceSupported();
    _voiceDebug('init | supported=$supported');
    // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

    setState(() {
      _supported = supported;
      _loading = false;
    });
    if (!supported) return;
    await _loadSessions(preferredSessionId: widget.conversationId);
  }

  // Nạp danh sách phiên voice.

  Future<void> _loadSessions({int? preferredSessionId}) async {
    try {
      // Gọi API hoặc tác vụ bất đồng bộ rồi chờ kết quả trước khi cập nhật giao diện.

      final resp = await ApiClient().dio.get(
        'assistant/sessions/',
        queryParameters: const {'mode': 'voice'},
      );
      final sessions = (resp.data as List<dynamic>)
          .map((item) => ChatSession.fromJson(Map<String, dynamic>.from(item)))
          .toList();
      _voiceDebug('voice_sessions loaded | count=${sessions.length}');
      final shouldStartFresh = preferredSessionId == null &&
          await ConversationBootstrapStore.shouldStartFresh(_featureKey);
      final rememberedSessionId = shouldStartFresh
          ? null
          : await ConversationBootstrapStore.getRememberedSessionId(
              _featureKey);
      final targetSessionId = preferredSessionId != null &&
              sessions.any((item) => item.id == preferredSessionId)
          ? preferredSessionId
          : (_sessionId != null && sessions.any((item) => item.id == _sessionId)
              ? _sessionId
              : (rememberedSessionId != null &&
                      sessions.any((item) => item.id == rememberedSessionId)
                  ? rememberedSessionId
                  : null));
      if (targetSessionId != null) {
        await _loadMessages(targetSessionId);
      } else if (mounted) {
        // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

        setState(() {
          _sessionId = null;
          _messages = const [];
          _liveTranscript = '';
          _status = 'idle';
        });
        await ConversationBootstrapStore.rememberSession(_featureKey, null);
        if (shouldStartFresh) {
          await ConversationBootstrapStore.markConversationChosen(_featureKey);
        }
      }
    } catch (error) {
      _voiceDebug('voice_sessions error | $error');
    }
  }

  // Đăng ký các sự kiện từ bridge voice (nghe/nói/kết quả).

  void _bindVoiceEvents() {
    _statusSub =
        html.EventStreamProvider<html.Event>('ai-assistant-voice-status')
            .forTarget(html.window)
            .listen((event) {
      final detail = _detail(event);
      _voiceDebug('event status | detail=$detail');
      if (!mounted) return;
      final nextStatus = '${detail['status'] ?? 'idle'}';
      if (_status == nextStatus) return;
      // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

      setState(() => _status = nextStatus);
    });

    _resultSub =
        html.EventStreamProvider<html.Event>('ai-assistant-voice-result')
            .forTarget(html.window)
            .listen((event) {
      final detail = _detail(event);
      _voiceDebug('event result | detail=$detail');
      if (!mounted) return;
      final transcript = '${detail['transcript'] ?? ''}'.trim();
      if (_liveTranscript == transcript) return;
      // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

      setState(() => _liveTranscript = transcript);
    });

    _readySub = html.EventStreamProvider<html.Event>('ai-assistant-voice-ready')
        .forTarget(html.window)
        .listen((event) async {
      final detail = _detail(event);
      _voiceDebug('event ready | detail=$detail');
      final transcript = '${detail['transcript'] ?? ''}'.trim();
      if (!mounted || transcript.isEmpty) return;
      await _stopAudioCapture();
      if (!mounted) return;
      _submitTranscript(transcript);
    });

    _errorSub = html.EventStreamProvider<html.Event>('ai-assistant-voice-error')
        .forTarget(html.window)
        .listen((event) async {
      if (!mounted) return;
      final detail = _detail(event);
      _voiceDebug('event error | detail=$detail');
      await _stopAudioCapture();
      final message = '${detail['message'] ?? 'Lỗi giọng nói không xác định.'}';
      ScaffoldMessenger.of(context)
          .showSnackBar(SnackBar(content: Text(message)));
    });

    _debugSub = html.EventStreamProvider<html.Event>('ai-assistant-voice-debug')
        .forTarget(html.window)
        .listen((event) {
      final detail = _detail(event);
      _voiceDebug(
        'bridge debug | message=${detail['message']} | extra=${detail['extra']} | at=${detail['at']}',
      );
    });

    _speechEndSub =
        html.EventStreamProvider<html.Event>('ai-assistant-voice-speech-end')
            .forTarget(html.window)
            .listen((_) {
      _voiceDebug('event speech_end | pendingRoute=$_pendingNavigationRoute');
      _cancelNavigationFallback();
      final route = _pendingNavigationRoute;
      _pendingNavigationRoute = null;
      if (route != null && mounted) {
        // Điều hướng người dùng sang màn phù hợp theo kết quả thao tác hiện tại.

        context.go(_withVoiceReturn(route));
      }
    });
  }

  Map<String, dynamic> _detail(html.Event event) {
    try {
      final detail = js_util.getProperty(event, 'detail');
      if (detail == null) {
        return const <String, dynamic>{};
      }
      if (detail is Map<String, dynamic>) return detail;
      if (detail is Map) return Map<String, dynamic>.from(detail);
      final dartified = js_util.dartify(detail);
      if (dartified is Map<String, dynamic>) return dartified;
      if (dartified is Map) return Map<String, dynamic>.from(dartified);
      return {'value': '$dartified'};
    } catch (error) {
      _voiceDebug('detail parse error | $error');
    }
    return const <String, dynamic>{};
  }

  dynamic get _bridge {
    if (!js_util.hasProperty(html.window, 'aiAssistantVoice')) return null;
    return js_util.getProperty(html.window, 'aiAssistantVoice');
  }

  // Trình duyệt có hỗ trợ voice không.

  bool _isVoiceSupported() {
    final bridge = _bridge;
    if (bridge == null) {
      _voiceDebug('bridge missing on window');
      return false;
    }
    try {
      final supported =
          js_util.callMethod(bridge, 'isSupported', const []) == true;
      _voiceDebug('bridge isSupported -> $supported');
      return supported;
    } catch (error) {
      _voiceDebug('bridge isSupported error | $error');
      return false;
    }
  }

  // Nạp tin nhắn của 1 phiên voice.

  Future<void> _loadMessages(int sessionId) async {
    try {
      // Gọi API hoặc tác vụ bất đồng bộ rồi chờ kết quả trước khi cập nhật giao diện.

      final resp =
          await ApiClient().dio.get('assistant/sessions/$sessionId/messages/');
      final messages = (resp.data as List<dynamic>)
          .map((item) => ChatMessage.fromJson(Map<String, dynamic>.from(item)))
          .toList();
      _voiceDebug(
          'load_messages ok | session_id=$sessionId | count=${messages.length}');
      if (!mounted) return;
      // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

      setState(() {
        _sessionId = sessionId;
        _messages = messages;
        _liveTranscript = '';
      });
      await ConversationBootstrapStore.markConversationChosen(_featureKey);
      await ConversationBootstrapStore.rememberSession(_featureKey, sessionId);
    } catch (error) {
      _voiceDebug('load_messages error | session_id=$sessionId | $error');
    }
  }

  // Mở quản lý lịch sử phiên voice.

  Future<void> _openHistoryManager() async {
    final strings = AppStrings.of(context);
    await showChatHistoryManagerDialog(
      context: context,
      title: strings.pick('Lịch sử giọng nói AI', 'AI voice history'),
      emptyLabel: strings.pick(
          'Chưa có phiên voice nào được lưu.', 'No saved voice sessions yet.'),
      listPath: 'assistant/sessions/',
      deletePath: 'assistant/sessions/',
      messagesPathBuilder: (sessionId) =>
          'assistant/sessions/$sessionId/messages/',
      listQueryParameters: const {'mode': 'voice'},
      deleteDataBuilder: (sessionIds) => {
        'mode': 'voice',
        'session_ids': sessionIds,
      },
      onOpenSession: (sessionId) => _loadMessages(sessionId),
      onChanged: () async {
        await _loadSessions(preferredSessionId: _sessionId);
      },
    );
  }

  // Xử lý kết quả 1 lượt trợ lý: nói trả lời + điều hướng theo ý định.

  Future<void> _applyAssistantTurnResult(Map<String, dynamic> result) async {
    final rawSession = result['session'];
    final rawMessage = result['message'];
    final rawAction = result['action'];
    if (rawSession is! Map || rawMessage is! Map) {
      throw const AITaskFailedException(
        'Task tro ly giong noi khong tra ve du lieu hop le.',
      );
    }

    final session = ChatSession.fromJson(Map<String, dynamic>.from(rawSession));
    final message = ChatMessage.fromJson(Map<String, dynamic>.from(rawMessage));
    final action =
        rawAction is Map ? Map<String, dynamic>.from(rawAction) : null;
    _voiceDebug(
      'submit_transcript result | session_id=${session.id} | '
      'message_len=${message.content.length} | action=$action',
    );

    if (!mounted) return;
    setState(() {
      _currentVoiceTaskId = null;
      _requestInFlight = false;
      _sessionId = session.id;
      _messages = [..._messages, message];
    });
    await ConversationBootstrapStore.markConversationChosen(_featureKey);
    await ConversationBootstrapStore.rememberSession(_featureKey, session.id);
    if (!mounted) return;

    final speakText =
        action?['speak_text']?.toString().trim().isNotEmpty == true
            ? '${action!['speak_text']}'
            : message.content;
    final route = action?['route']?.toString().trim();

    if (_speakerOn) {
      if (route != null && route.isNotEmpty) {
        final routeWithReturn = _withVoiceReturn(route);
        _pendingNavigationRoute = routeWithReturn;
        _scheduleNavigationFallback(routeWithReturn, speakText);
      }
      _speak(speakText);
    } else if (route != null && route.isNotEmpty) {
      context.go(_withVoiceReturn(route));
    } else {
      setState(() => _status = 'idle');
    }
  }

  Future<Map<String, dynamic>> _runVoiceTaskInline({
    Map<String, dynamic>? jsonPayload,
    FormData? formPayload,
  }) async {
    final resp = await ApiClient().dio.post(
      'assistant/turn-async/',
      data: formPayload ?? jsonPayload,
    );
    final body = (resp.data as Map).cast<String, dynamic>();
    final taskId = body['task_id'] as String?;
    if (taskId == null || taskId.isEmpty) {
      throw const AITaskFailedException('Server không trả về task_id.');
    }
    if (!mounted) {
      throw const AITaskFailedException('Context unmounted');
    }
    setState(() => _currentVoiceTaskId = taskId);

    final completer = Completer<Map<String, dynamic>>();
    final sub = ref.listenManual<AsyncValue<AITaskState>>(
      aiTaskProgressProvider(
        AITaskPollConfig(
          taskId: taskId,
          pollInterval: const Duration(milliseconds: 400),
        ),
      ),
      (prev, next) {
        next.whenData((state) {
          if (completer.isCompleted) return;
          if (state.status == 'completed') {
            completer.complete(state.result ?? const <String, dynamic>{});
          } else if (state.status == 'cancelled') {
            completer.completeError(const AITaskCancelledException());
          } else if (state.status == 'failed') {
            completer.completeError(
              AITaskFailedException(state.errorMessage ?? 'AI task thất bại'),
            );
          }
        });
        next.whenOrNull(error: (err, _) {
          if (!completer.isCompleted) {
            completer.completeError(AITaskFailedException('$err'));
          }
        });
      },
      fireImmediately: true,
    );
    try {
      return await completer.future;
    } finally {
      sub.close();
    }
  }

  Future<void> _cancelCurrentVoiceTask() async {
    final taskId = _currentVoiceTaskId;
    if (taskId == null) return;
    try {
      await ApiClient().dio.post('ai-tasks/$taskId/cancel/');
      _voiceDebug('voice_task cancel requested | task=$taskId');
    } catch (e) {
      _voiceDebug('voice_task cancel error | $e');
    }
  }

  Future<void> _submitTranscript(String transcript) async {
    if (transcript.isEmpty || _requestInFlight) {
      _voiceDebug(
        'submit_transcript skip | empty=${transcript.isEmpty} | requestInFlight=$_requestInFlight',
      );
      return;
    }
    _voiceDebug('submit_transcript start | text="$transcript"');

    // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

    setState(() {
      _requestInFlight = true;
      _status = 'processing';
      _liveTranscript = '';
      _messages = [
        ..._messages,
        ChatMessage(
          id: -DateTime.now().millisecondsSinceEpoch,
          role: 'user',
          content: transcript,
          citations: const [],
          createdAt: '',
        ),
      ];
    });

    try {
      _pendingNavigationRoute = null;
      _cancelNavigationFallback();
      final audioBlob = _pendingAudioBlob;
      final audioDuration = _pendingAudioDurationSeconds;
      _pendingAudioBlob = null;
      _pendingAudioDurationSeconds = 0;

      final attachmentsSnapshot = List<ChatAttachmentItem>.from(_pendingAttachments);
      setState(() => _pendingAttachments.clear());

      final attachmentFields = <String, dynamic>{};
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
      if (pdfFiles.isNotEmpty) {
        attachmentFields['attachment_pdfs'] = pdfFiles;
      }
      if (imageFiles.isNotEmpty) {
        attachmentFields['attachment_images'] = imageFiles;
      }

      FormData? formPayload;
      Map<String, dynamic>? jsonPayload;
      if (audioBlob != null || attachmentsSnapshot.isNotEmpty) {
        final fields = <String, dynamic>{
          'input': transcript,
          'mode': 'voice',
          if (_sessionId != null) 'session_id': _sessionId,
          'voice_duration_seconds': audioDuration,
          'auto_fill_profile': _autoFillProfile.toString(),
          'auto_fill_company': _autoFillCompany.toString(),
          ...attachmentFields,
        };
        if (audioBlob != null) {
          final audioBytes = await _blobToBytes(audioBlob);
          fields['voice_audio'] = MultipartFile.fromBytes(
            audioBytes,
            filename: 'voice_${DateTime.now().millisecondsSinceEpoch}.webm',
          );
        }
        formPayload = FormData.fromMap(fields, ListFormat.multiCompatible);
      } else {
        jsonPayload = {
          'input': transcript,
          'mode': 'voice',
          if (_sessionId != null) 'session_id': _sessionId,
          'auto_fill_profile': _autoFillProfile,
          'auto_fill_company': _autoFillCompany,
        };
      }
      if (!mounted) return;
      final strings = AppStrings.of(context);

      // Gọi API hoặc tác vụ bất đồng bộ rồi chờ kết quả trước khi cập nhật giao diện.

      try {
        final result = await _runVoiceTaskInline(
          jsonPayload: jsonPayload,
          formPayload: formPayload,
        );
        if (!mounted) return;
        await _applyAssistantTurnResult(result);
      } on AITaskCancelledException {
        _voiceDebug('submit_transcript cancelled');
        if (!mounted) return;
        setState(() {
          _currentVoiceTaskId = null;
          _requestInFlight = false;
          _status = 'idle';
        });
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(
              strings.pick(
                'Da dung xu ly giong noi.',
                'Voice assistant cancelled.',
              ),
            ),
            backgroundColor: Colors.orange,
          ),
        );
      }
      return; /*

      final resp = await ApiClient().dio.post(
            'assistant/turn/',
            data: requestData,
            options: ApiClient.ollamaOptions(),
          );

      final session = ChatSession.fromJson(
          Map<String, dynamic>.from(resp.data['session'] as Map));
      final message = ChatMessage.fromJson(
          Map<String, dynamic>.from(resp.data['message'] as Map));
      final action = resp.data['action'] is Map
          ? Map<String, dynamic>.from(resp.data['action'] as Map)
          : null;
      _voiceDebug(
        'submit_transcript response | session_id=${session.id} | '
        'message_len=${message.content.length} | action=$action',
      );

      if (!mounted) return;
      // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

      setState(() {
        _requestInFlight = false;
        _sessionId = session.id;
        _messages = [..._messages, message];
      });
      await ConversationBootstrapStore.markConversationChosen(_featureKey);
      await ConversationBootstrapStore.rememberSession(_featureKey, session.id);

      final speakText =
          action?['speak_text']?.toString().trim().isNotEmpty == true
              ? '${action!['speak_text']}'
              : message.content;
      final route = action?['route']?.toString().trim();

      if (_speakerOn) {
        if (route != null && route.isNotEmpty) {
          final routeWithReturn = _withVoiceReturn(route);
          _pendingNavigationRoute = routeWithReturn;
          _scheduleNavigationFallback(routeWithReturn, speakText);
        }
        _speak(speakText);
      } else if (route != null && route.isNotEmpty) {
        // Điều hướng người dùng sang màn phù hợp theo kết quả thao tác hiện tại.

        context.go(_withVoiceReturn(route));
      } else {
        // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

        setState(() => _status = 'idle');
      } */
    } catch (error) {
      _voiceDebug('submit_transcript error | $error');
      if (!mounted) return;
      final message = _readableError(error);
      // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

      setState(() {
        _currentVoiceTaskId = null;
        _requestInFlight = false;
        _status = 'idle';
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
      ScaffoldMessenger.of(context)
          .showSnackBar(SnackBar(content: Text(message)));
    }
  }

  // Đổi lỗi thành thông điệp dễ đọc.

  String _readableError(Object error) {
    final strings = AppStrings.of(context);
    if (error is DioException) {
      final data = error.response?.data;
      if (data is Map && data['error'] != null) return '${data['error']}';
      if (data is Map && data['detail'] != null) return '${data['detail']}';
      return strings.pick(
        'Không gọi được trợ lý giọng nói (${error.response?.statusCode ?? 'network'}).',
        'Unable to reach the voice assistant (${error.response?.statusCode ?? 'network'}).',
      );
    }
    return strings.pick('Đã xảy ra lỗi: $error', 'An error occurred: $error');
  }

  // Gọi 1 phương thức của bridge voice (JS).

  void _callBridge(String method, [List<dynamic> args = const []]) {
    final bridge = _bridge;
    if (bridge == null) {
      _voiceDebug('call_bridge skipped | method=$method | bridge=null');
      return;
    }
    _voiceDebug('call_bridge | method=$method | args=$args');
    js_util.callMethod(bridge, method, args);
  }

  // Hủy điều hướng dự phòng đang chờ.

  void _cancelNavigationFallback() {
    _navigationFallbackTimer?.cancel();
    _navigationFallbackTimer = null;
  }

  // Hẹn điều hướng dự phòng (nếu lệnh nói không tự điều hướng).

  void _scheduleNavigationFallback(String route, String speakText) {
    _cancelNavigationFallback();
    const fallbackMs = 4500;
    _voiceDebug(
      'navigation_fallback armed | route=$route | delay_ms=$fallbackMs | speak_len=${speakText.length}',
    );
    _navigationFallbackTimer =
        Timer(const Duration(milliseconds: fallbackMs), () {
      if (!mounted) return;
      if (_pendingNavigationRoute != route) {
        _voiceDebug('navigation_fallback skipped | reason=route_changed');
        return;
      }
      _voiceDebug('navigation_fallback fired | route=$route | status=$_status');
      _pendingNavigationRoute = null;
      // Điều hướng người dùng sang màn phù hợp theo kết quả thao tác hiện tại.

      context.go(_withVoiceReturn(route));
    });
  }

  // Gắn tham số 'quay lại voice' vào route.

  String _withVoiceReturn(String route) {
    final strings = AppStrings.of(context);
    final uri = Uri.parse(route);
    final params = Map<String, String>.from(uri.queryParameters);
    params['return_to'] = '/chat/voice';
    params['return_label'] =
        strings.pick('Quay về Giọng nói AI', 'Back to AI Voice');
    return uri.replace(queryParameters: params).toString();
  }

  // Phát giọng nói đọc 1 đoạn text (TTS).

  void _speak(String text) {
    _voiceDebug('speak request | text_len=${text.length}');
    _callBridge('speak', [text]);
  }

  // Tạo phiên voice mới.

  void _newVoiceSession() {
    _pendingNavigationRoute = null;
    _cancelNavigationFallback();
    _callBridge('stopListening');
    _callBridge('stopSpeaking');
    _disposeAudioCapture();
    // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

    setState(() {
      _sessionId = null;
      _messages = const [];
      _debugLines.clear();
      _requestInFlight = false;
      _liveTranscript = '';
      _status = 'idle';
    });
    _voiceDebug('new_voice_session');
    ConversationBootstrapStore.markConversationChosen(_featureKey);
    ConversationBootstrapStore.rememberSession(_featureKey, null);
  }

  // Bắt đầu thu âm từ micro.

  Future<void> _startAudioCapture() async {
    if (_mediaRecorder != null) return;
    try {
      final mediaDevices =
          js_util.getProperty(html.window.navigator, 'mediaDevices');
      if (mediaDevices == null) return;
      final stream = await js_util.promiseToFuture<dynamic>(
        js_util.callMethod(mediaDevices, 'getUserMedia', [
          {'audio': true}
        ]),
      );
      final recorder = html.MediaRecorder(stream as html.MediaStream);
      _recordedChunks.clear();
      _recordingStartedAt = DateTime.now();
      _recordDataSub = html.EventStreamProvider<html.Event>('dataavailable')
          .forTarget(recorder)
          .listen((event) {
        final blob = js_util.getProperty<Object?>(event, 'data');
        if (blob is html.Blob && blob.size > 0) {
          _recordedChunks.add(blob);
        }
      });
      _recordStopSub = html.EventStreamProvider<html.Event>('stop')
          .forTarget(recorder)
          .listen((_) {
        if (_recordedChunks.isNotEmpty) {
          _pendingAudioBlob = html.Blob(_recordedChunks, 'audio/webm');
        }
        if (_recordingStartedAt != null) {
          _pendingAudioDurationSeconds =
              DateTime.now().difference(_recordingStartedAt!).inMilliseconds /
                  1000;
        }
        _recordedChunks.clear();
      });
      recorder.start();
      _mediaRecorder = recorder;
      _mediaStream = stream;
      _voiceDebug('audio_capture started');
    } catch (error) {
      _voiceDebug('audio_capture start error | $error');
    }
  }

  // Dừng thu âm.

  Future<void> _stopAudioCapture() async {
    final recorder = _mediaRecorder;
    if (recorder == null) return;
    try {
      if (recorder.state != 'inactive') {
        recorder.stop();
      }
    } catch (_) {}
    await Future<void>.delayed(const Duration(milliseconds: 150));
    _recordDataSub?.cancel();
    _recordStopSub?.cancel();
    _recordDataSub = null;
    _recordStopSub = null;
    _disposeAudioStreamTracks();
    _mediaRecorder = null;
  }

  // Giải phóng các track âm thanh đang thu.

  void _disposeAudioStreamTracks() {
    final stream = _mediaStream;
    if (stream == null) return;
    try {
      final tracks =
          js_util.callMethod<List<dynamic>>(stream, 'getTracks', const []);
      for (final track in tracks) {
        js_util.callMethod(track, 'stop', const []);
      }
    } catch (_) {}
    _mediaStream = null;
  }

  // Giải phóng tài nguyên thu âm.

  void _disposeAudioCapture() {
    try {
      _mediaRecorder?.stop();
    } catch (_) {}
    _recordDataSub?.cancel();
    _recordStopSub?.cancel();
    _recordDataSub = null;
    _recordStopSub = null;
    _mediaRecorder = null;
    _recordedChunks.clear();
    _disposeAudioStreamTracks();
    _pendingAudioBlob = null;
    _pendingAudioDurationSeconds = 0;
    _recordingStartedAt = null;
  }

  // Phát/dừng nghe lại 1 file audio đính kèm.

  Future<void> _toggleAttachmentPlayback(ChatAudioAttachment item) async {
    try {
      if (_playingAudioAttachmentId == item.id && _messageAudioPlayer != null) {
        _messageAudioPlayer!.pause();
        if (!mounted) return;
        // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

        setState(() => _playingAudioAttachmentId = null);
        return;
      }
      _messageAudioPlayer?.pause();
      final nextPlayer = html.AudioElement(item.downloadUrl)
        ..autoplay = true
        ..controls = false;
      nextPlayer.onEnded.listen((_) {
        if (!mounted) return;
        // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

        setState(() => _playingAudioAttachmentId = null);
      });
      await nextPlayer.play();
      if (!mounted) return;
      // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

      setState(() {
        _messageAudioPlayer = nextPlayer;
        _playingAudioAttachmentId = item.id;
      });
    } catch (error) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Không phát được audio: $error')),
      );
    }
  }

  // Tải file audio đính kèm về máy.

  Future<void> _downloadAttachment(ChatAudioAttachment item) async {
    try {
      // Gọi API hoặc tác vụ bất đồng bộ rồi chờ kết quả trước khi cập nhật giao diện.

      final resp = await ApiClient().dio.get(
            'assistant/audio/${item.id}/download/',
            options: Options(responseType: ResponseType.bytes),
          );
      final bytes = resp.data as List<int>;
      final blob = html.Blob(
          [bytes], item.mimeType.isEmpty ? 'audio/webm' : item.mimeType);
      final url = html.Url.createObjectUrlFromBlob(blob);
      html.AnchorElement(href: url)
        ..setAttribute('download',
            item.title.isEmpty ? 'audio_${item.id}.webm' : item.title)
        ..click();
      html.Url.revokeObjectUrl(url);
    } on DioException catch (error) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
            content: Text(error.response?.data?['detail']?.toString() ??
                'Không tải được audio.')),
      );
    }
  }

  // Đọc blob audio thành bytes.

  Future<Uint8List> _blobToBytes(html.Blob blob) {
    final completer = Completer<Uint8List>();
    final reader = html.FileReader();
    reader.readAsArrayBuffer(blob);
    reader.onLoad.listen((_) {
      final result = reader.result;
      if (result is ByteBuffer) {
        completer.complete(result.asUint8List());
      } else if (result is Uint8List) {
        completer.complete(result);
      } else {
        completer.complete(Uint8List(0));
      }
    });
    reader.onError.listen((_) {
      completer.completeError(reader.error ?? 'blob read failed');
    });
    return completer.future;
  }

  void _openVoiceRoute(String route) {
    final target = route.trim();
    if (target.isEmpty) return;
    _pendingNavigationRoute = null;
    _cancelNavigationFallback();
    context.go(_withVoiceReturn(target));
  }

  Widget? _buildVoicePayloadCard(
    ChatMessage message, {
    required bool isCompact,
  }) {
    final payload = message.payload;
    if (payload == null || payload.isEmpty) {
      return null;
    }
    final kind = '${payload['kind'] ?? ''}'.trim();
    switch (kind) {
      case 'recipient_resolution':
        return _buildRecipientResolutionPayloadCard(payload,
            isCompact: isCompact);
      case 'assistant_quick_sign_plan':
        return _buildQuickSignPayloadCard(payload);
      case 'document_result':
        return _buildDocumentResultPayloadCard(payload);
      default:
        return null;
    }
  }

  Widget _buildPayloadSurface({required Widget child}) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: Colors.white.withOpacity(0.08),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: Colors.white.withOpacity(0.12)),
      ),
      child: child,
    );
  }

  Widget _buildPayloadHeader({
    required IconData icon,
    required String title,
    required String subtitle,
  }) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Container(
          width: 30,
          height: 30,
          decoration: BoxDecoration(
            color: Colors.white.withOpacity(0.1),
            borderRadius: BorderRadius.circular(10),
          ),
          child: Icon(icon, size: 17, color: Colors.white),
        ),
        const SizedBox(width: 10),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                title,
                style: const TextStyle(
                  color: Colors.white,
                  fontWeight: FontWeight.w700,
                ),
              ),
              if (subtitle.trim().isNotEmpty) ...[
                const SizedBox(height: 3),
                Text(
                  subtitle,
                  style: const TextStyle(
                    color: Color(0xFFCBD5E1),
                    height: 1.45,
                  ),
                ),
              ],
            ],
          ),
        ),
      ],
    );
  }

  Widget _buildRecipientResolutionPayloadCard(
    Map<String, dynamic> payload, {
    required bool isCompact,
  }) {
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

    return _buildPayloadSurface(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _buildPayloadHeader(
            icon:
                isAmbiguous ? Icons.help_outline : Icons.person_search_outlined,
            title: isAmbiguous
                ? strings.pick(
                    'Cần xác nhận người nhận', 'Recipient confirmation needed')
                : strings.pick(
                    'Chưa tìm thấy người nhận', 'Recipient not found'),
            subtitle: prompt,
          ),
          if (candidates.isNotEmpty) ...[
            const SizedBox(height: 12),
            ...candidates.map(
              (candidate) => Container(
                width: double.infinity,
                margin: const EdgeInsets.only(bottom: 8),
                padding: const EdgeInsets.all(10),
                decoration: BoxDecoration(
                  color: Colors.white.withOpacity(0.05),
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(color: Colors.white.withOpacity(0.08)),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      candidate.displayName,
                      style: const TextStyle(
                        color: Colors.white,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                    if (candidate.subtitle.isNotEmpty) ...[
                      const SizedBox(height: 4),
                      Text(
                        candidate.subtitle,
                        style: const TextStyle(
                          color: Color(0xFFCBD5E1),
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
                          color: Color(0xFF94A3B8),
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
                color: Color(0xFF94A3B8),
                fontSize: 12.5,
                height: 1.45,
              ),
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildQuickSignPayloadCard(Map<String, dynamic> payload) {
    final strings = AppStrings.of(context);
    final plan = AssistantQuickSignPlanAction.fromJson(payload);
    final recipient = plan.recipient;
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

    return _buildPayloadSurface(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _buildPayloadHeader(
            icon: plan.isCompleted
                ? Icons.verified_outlined
                : plan.isPartial
                    ? Icons.forward_to_inbox_outlined
                    : plan.isFailed
                        ? Icons.error_outline
                        : plan.isBlocked
                            ? Icons.lock_outline
                            : Icons.bolt_outlined,
            title: title,
            subtitle: summary,
          ),
          if (recipient != null) ...[
            const SizedBox(height: 12),
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(10),
              decoration: BoxDecoration(
                color: Colors.white.withOpacity(0.05),
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: Colors.white.withOpacity(0.08)),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    strings.pick('Người nhận dự kiến', 'Planned recipient'),
                    style: const TextStyle(
                      color: Color(0xFF94A3B8),
                      fontSize: 12.5,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    recipient.displayName,
                    style: const TextStyle(
                      color: Colors.white,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                  if (recipient.subtitle.isNotEmpty) ...[
                    const SizedBox(height: 4),
                    Text(
                      recipient.subtitle,
                      style: const TextStyle(
                        color: Color(0xFFCBD5E1),
                        height: 1.4,
                      ),
                    ),
                  ],
                ],
              ),
            ),
          ],
          if (plan.route.trim().isNotEmpty) ...[
            const SizedBox(height: 12),
            Align(
              alignment: Alignment.centerLeft,
              child: TextButton.icon(
                onPressed: () => _openVoiceRoute(plan.route),
                icon: const Icon(Icons.open_in_new, size: 18),
                label: Text(
                  plan.isCompleted
                      ? strings.pick('Mở văn bản', 'Open document')
                      : strings.pick(
                          'Mở văn bản để xử lý', 'Open document to continue'),
                ),
                style: TextButton.styleFrom(foregroundColor: Colors.white),
              ),
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildDocumentResultPayloadCard(Map<String, dynamic> payload) {
    final strings = AppStrings.of(context);
    final route = payload['route']?.toString().trim() ?? '';
    final title = payload['title']?.toString().trim() ?? '';
    return _buildPayloadSurface(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _buildPayloadHeader(
            icon: Icons.description_outlined,
            title: strings.pick('Văn bản đã được tạo', 'Document created'),
            subtitle: title.isEmpty
                ? strings.pick(
                    'Trợ lý đã tạo văn bản và có thể mở trang chi tiết ngay bây giờ.',
                    'The assistant created the document and can open the detail page now.',
                  )
                : title,
          ),
          if (route.isNotEmpty) ...[
            const SizedBox(height: 12),
            Align(
              alignment: Alignment.centerLeft,
              child: TextButton.icon(
                onPressed: () => _openVoiceRoute(route),
                icon: const Icon(Icons.open_in_new, size: 18),
                label: Text(strings.pick('Mở văn bản', 'Open document')),
                style: TextButton.styleFrom(foregroundColor: Colors.white),
              ),
            ),
          ],
        ],
      ),
    );
  }

  // Nút micro: bật/tắt lắng nghe giọng nói.

  Future<void> _toggleListening() async {
    if (_status == 'processing' || _status == 'speaking') return;
    if (_status == 'listening') {
      _callBridge('stopListening');
      await _stopAudioCapture();
      return;
    }
    _pendingAudioBlob = null;
    _pendingAudioDurationSeconds = 0;
    await _startAudioCapture();
    _callBridge('startListening');
  }

  @override
  // Dựng màn voice: khu hội thoại + nút micro + trạng thái nghe/nói; báo nếu trình duyệt không hỗ trợ.

  Widget build(BuildContext context) {
    final strings = AppStrings.of(context);
    if (_loading) {
      return const TaskDonePopupHost(
        child: Center(child: CircularProgressIndicator()),
      );
    }
    if (!_supported) {
      // Điều hướng người dùng sang màn phù hợp theo kết quả thao tác hiện tại.

      return TaskDonePopupHost(
        child: _VoiceUnsupported(onOpenTextMode: () => context.go('/chat')),
      );
    }

    final statusLabel = switch (_status) {
      'listening' => strings.pick('Đang nghe', 'Listening'),
      'processing' => strings.pick('Đang xử lý', 'Processing'),
      'speaking' => strings.pick('Đang nói', 'Speaking'),
      _ => strings.pick('Sẵn sàng', 'Ready'),
    };
    final isCompact = MediaQuery.sizeOf(context).width < 760;
    final modelName =
        ref.watch(chatAiModelProvider).asData?.value ?? 'kimi-k2.6:cloud';

    return TaskDonePopupHost(
      child: Container(
        decoration: const BoxDecoration(
          gradient: LinearGradient(
            colors: [Color(0xFF020617), Color(0xFF0F172A), Color(0xFF172554)],
            begin: Alignment.topCenter,
            end: Alignment.bottomCenter,
          ),
        ),
        child: SafeArea(
          child: LayoutBuilder(
            builder: (context, constraints) => SingleChildScrollView(
              physics: const BouncingScrollPhysics(),
              padding: EdgeInsets.fromLTRB(
                isCompact ? 14 : 24,
                isCompact ? 14 : 20,
                isCompact ? 14 : 24,
                isCompact ? 20 : 24,
              ),
              child: ConstrainedBox(
                constraints: BoxConstraints(minHeight: constraints.maxHeight),
                child: Column(
                  children: [
                  if (isCompact)
                    Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(children: [
                          IconButton(
                            onPressed: () => context.go('/chat'),
                            icon: const Icon(Icons.arrow_back,
                                color: Colors.white),
                          ),
                          const SizedBox(width: 4),
                          Expanded(
                            child: Text(
                              strings.pick('Giọng nói AI', 'AI Voice'),
                              style: const TextStyle(
                                color: Colors.white,
                                fontSize: 22,
                                fontWeight: FontWeight.w800,
                              ),
                            ),
                          ),
                        ]),
                        const SizedBox(height: 6),
                        Text(
                          strings.pick(
                            '$modelName sẽ điều phối tool tự động trong phiên voice.',
                            '$modelName will orchestrate tools automatically during the voice session.',
                          ),
                          style: const TextStyle(
                            color: Color(0xFFCBD5E1),
                            height: 1.45,
                          ),
                        ),
                        const SizedBox(height: 12),
                        Wrap(
                          spacing: 8,
                          runSpacing: 8,
                          children: [
                            FilledButton.tonalIcon(
                              onPressed: _newVoiceSession,
                              icon: const Icon(Icons.restart_alt),
                              label: Text(
                                  strings.pick('Phiên mới', 'New session')),
                            ),
                            OutlinedButton.icon(
                              onPressed: _openHistoryManager,
                              icon: const Icon(Icons.history),
                              label: Text(strings.pick('Lịch sử', 'History')),
                              style: OutlinedButton.styleFrom(
                                foregroundColor: Colors.white,
                              ),
                            ),
                          ],
                        ),
                      ],
                    )
                  else
                    Row(children: [
                      IconButton(
                        onPressed: () => context.go('/chat'),
                        icon: const Icon(Icons.arrow_back, color: Colors.white),
                      ),
                      const SizedBox(width: 8),
                      Expanded(
                        child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(strings.pick('Giọng nói AI', 'AI Voice'),
                                  style: const TextStyle(
                                      color: Colors.white,
                                      fontSize: 24,
                                      fontWeight: FontWeight.w800)),
                              const SizedBox(height: 4),
                              Text(
                                  strings.pick(
                                    '$modelName sẽ điều phối tool tự động trong phiên voice.',
                                    '$modelName will orchestrate tools automatically during the voice session.',
                                  ),
                                  style: const TextStyle(
                                      color: Color(0xFFCBD5E1))),
                            ]),
                      ),
                      FilledButton.tonalIcon(
                        onPressed: _newVoiceSession,
                        icon: const Icon(Icons.restart_alt),
                        label: Text(strings.pick('Phiên mới', 'New session')),
                      ),
                      const SizedBox(width: 8),
                      OutlinedButton.icon(
                        onPressed: _openHistoryManager,
                        icon: const Icon(Icons.history),
                        label: Text(strings.pick('Lịch sử', 'History')),
                        style: OutlinedButton.styleFrom(
                            foregroundColor: Colors.white),
                      ),
                    ]),
                  SizedBox(height: isCompact ? 22 : 28),
                  _VoiceCircle(
                    isCompact: isCompact,
                    status: _status,
                    statusLabel: statusLabel,
                    fallbackDetail: _liveTranscript.isEmpty
                        ? strings.pick(
                            'Nói tự nhiên như khi dùng ChatGPT Voice.',
                            'Speak naturally, as if you were using ChatGPT Voice.',
                          )
                        : _liveTranscript,
                    taskId: _currentVoiceTaskId,
                    onStop: _cancelCurrentVoiceTask,
                  ),
                  SizedBox(height: isCompact ? 16 : 20),
                  ConstrainedBox(
                    constraints: const BoxConstraints(maxWidth: 640),
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
                  SizedBox(height: isCompact ? 10 : 12),
                  ConstrainedBox(
                    constraints: const BoxConstraints(maxWidth: 640),
                    child: ChatAttachmentRow(
                      items: _pendingAttachments,
                      onAdd: (item) =>
                          setState(() => _pendingAttachments.add(item)),
                      onRemove: (i) =>
                          setState(() => _pendingAttachments.removeAt(i)),
                      compact: isCompact,
                    ),
                  ),
                  SizedBox(height: isCompact ? 16 : 20),
                  Wrap(
                    alignment: WrapAlignment.center,
                    spacing: 12,
                    runSpacing: 12,
                    children: [
                      FilledButton.icon(
                        onPressed: _toggleListening,
                        icon: Icon(_status == 'listening'
                            ? Icons.stop_circle_outlined
                            : Icons.mic_none_outlined),
                        label: Text(_status == 'listening'
                            ? strings.pick('Dừng nghe', 'Stop listening')
                            : strings.pick('Bắt đầu nghe', 'Start listening')),
                      ),
                      OutlinedButton.icon(
                        onPressed: () {
                          // Cập nhật state cục bộ để giao diện phản ánh ngay dữ liệu hoặc trạng thái mới.

                          setState(() => _speakerOn = !_speakerOn);
                          if (!_speakerOn) {
                            _callBridge('stopSpeaking');
                          }
                        },
                        icon: Icon(_speakerOn
                            ? Icons.volume_up_outlined
                            : Icons.volume_off_outlined),
                        label: Text(
                          _speakerOn
                              ? strings.pick('Đang bật loa', 'Speaker on')
                              : strings.pick('Đang tắt loa', 'Speaker off'),
                        ),
                        style: OutlinedButton.styleFrom(
                            foregroundColor: Colors.white),
                      ),
                      OutlinedButton.icon(
                        onPressed: () => _callBridge('stopSpeaking'),
                        icon: const Icon(Icons.stop_circle_outlined),
                        label: Text(strings.pick('Dừng nói', 'Stop speaking')),
                        style: OutlinedButton.styleFrom(
                            foregroundColor: Colors.white),
                      ),
                    ],
                  ),
                  SizedBox(height: isCompact ? 24 : 32),
                  ConstrainedBox(
                    constraints: const BoxConstraints(maxWidth: 880),
                    child: Container(
                      width: double.infinity,
                      padding: EdgeInsets.all(isCompact ? 14 : 18),
                      decoration: BoxDecoration(
                        color: Colors.white.withOpacity(0.08),
                        borderRadius: BorderRadius.circular(24),
                        border:
                            Border.all(color: Colors.white.withOpacity(0.12)),
                      ),
                      child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                                strings.pick(
                                    'Transcript gần đây', 'Recent transcript'),
                                style: const TextStyle(
                                    color: Colors.white,
                                    fontSize: 14,
                                    fontWeight: FontWeight.w800)),
                            const SizedBox(height: 12),
                            if (_messages.isEmpty)
                              Text(
                                strings.pick(
                                  'Chưa có transcript. Bấm "Bắt đầu nghe" để mở phiên voice.',
                                  'No transcript yet. Tap "Start listening" to begin a voice session.',
                                ),
                                style: const TextStyle(
                                    color: Color(0xFFCBD5E1), height: 1.5),
                              )
                            else
                              ..._messages.reversed
                                  .take(6)
                                  .toList()
                                  .reversed
                                  .map((message) {
                                final payloadCard = _buildVoicePayloadCard(
                                  message,
                                  isCompact: isCompact,
                                );
                                return Padding(
                                  padding: const EdgeInsets.only(bottom: 10),
                                  child: Row(
                                    crossAxisAlignment:
                                        CrossAxisAlignment.start,
                                    children: [
                                      Container(
                                        width: 32,
                                        height: 32,
                                        decoration: BoxDecoration(
                                          color: message.role == 'user'
                                              ? const Color(0xFF0EA5E9)
                                              : const Color(0xFF1D4ED8),
                                          borderRadius:
                                              BorderRadius.circular(12),
                                        ),
                                        child: Icon(
                                          message.role == 'user'
                                              ? Icons.person_outline
                                              : Icons.auto_awesome,
                                          size: 18,
                                          color: Colors.white,
                                        ),
                                      ),
                                      const SizedBox(width: 10),
                                      Expanded(
                                        child: Column(
                                          crossAxisAlignment:
                                              CrossAxisAlignment.start,
                                          children: [
                                            Text(message.content,
                                                style: const TextStyle(
                                                    color: Colors.white,
                                                    height: 1.55)),
                                            if (payloadCard != null) ...[
                                              const SizedBox(height: 10),
                                              payloadCard,
                                            ],
                                            if (message.audioAttachments
                                                .isNotEmpty) ...[
                                              const SizedBox(height: 8),
                                              Wrap(
                                                spacing: 8,
                                                runSpacing: 8,
                                                children: message
                                                    .audioAttachments
                                                    .map((attachment) {
                                                  final isPlaying =
                                                      _playingAudioAttachmentId ==
                                                          attachment.id;
                                                  return Container(
                                                    padding: const EdgeInsets
                                                        .symmetric(
                                                        horizontal: 10,
                                                        vertical: 8),
                                                    decoration: BoxDecoration(
                                                      color: Colors.white
                                                          .withOpacity(0.08),
                                                      borderRadius:
                                                          BorderRadius.circular(
                                                              12),
                                                      border: Border.all(
                                                          color: Colors.white
                                                              .withOpacity(
                                                                  0.12)),
                                                    ),
                                                    child: Row(
                                                      mainAxisSize:
                                                          MainAxisSize.min,
                                                      children: [
                                                        IconButton(
                                                          onPressed: () =>
                                                              _toggleAttachmentPlayback(
                                                                  attachment),
                                                          icon: Icon(
                                                            isPlaying
                                                                ? Icons
                                                                    .pause_circle_outline
                                                                : Icons
                                                                    .play_circle_outline,
                                                            color: Colors.white,
                                                            size: 20,
                                                          ),
                                                          tooltip: isPlaying
                                                              ? strings.pick(
                                                                  'Tạm dừng',
                                                                  'Pause')
                                                              : strings.pick(
                                                                  'Phát lại',
                                                                  'Play again'),
                                                        ),
                                                        Text(
                                                          attachment
                                                                  .title.isEmpty
                                                              ? 'Audio ${attachment.id}'
                                                              : attachment
                                                                  .title,
                                                          style:
                                                              const TextStyle(
                                                                  color: Colors
                                                                      .white),
                                                        ),
                                                        IconButton(
                                                          onPressed: () =>
                                                              _downloadAttachment(
                                                                  attachment),
                                                          icon: const Icon(
                                                              Icons
                                                                  .download_outlined,
                                                              color:
                                                                  Colors.white,
                                                              size: 20),
                                                          tooltip: strings.pick(
                                                              'Tải audio',
                                                              'Download audio'),
                                                        ),
                                                      ],
                                                    ),
                                                  );
                                                }).toList(),
                                              ),
                                            ],
                                          ],
                                        ),
                                      ),
                                    ],
                                  ),
                                );
                              }),
                          ]),
                    ),
                  ),
                  const SizedBox(height: 18),
                  ConstrainedBox(
                    constraints: const BoxConstraints(maxWidth: 880),
                    child: Container(
                      width: double.infinity,
                      padding: const EdgeInsets.all(18),
                      decoration: BoxDecoration(
                        color: Colors.black.withOpacity(0.28),
                        borderRadius: BorderRadius.circular(24),
                        border:
                            Border.all(color: Colors.white.withOpacity(0.12)),
                      ),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                            children: [
                              Expanded(
                                child: Text(
                                  strings.pick(
                                      'Debug thời gian thực', 'Realtime debug'),
                                  style: const TextStyle(
                                    color: Colors.white,
                                    fontSize: 14,
                                    fontWeight: FontWeight.w800,
                                  ),
                                ),
                              ),
                              Text(
                                '$_status | ${_debugLines.length} log',
                                style: const TextStyle(
                                  color: Color(0xFF94A3B8),
                                  fontSize: 12,
                                  fontWeight: FontWeight.w600,
                                ),
                              ),
                            ],
                          ),
                          const SizedBox(height: 12),
                          Container(
                            height: 200,
                            width: double.infinity,
                            padding: const EdgeInsets.all(12),
                            decoration: BoxDecoration(
                              color: Colors.black.withOpacity(0.24),
                              borderRadius: BorderRadius.circular(16),
                              border: Border.all(
                                  color: Colors.white.withOpacity(0.08)),
                            ),
                            child: _debugLines.isEmpty
                                ? Align(
                                    alignment: Alignment.centerLeft,
                                    child: Text(
                                      strings.pick(
                                        'Chưa có log. Bấm "Bắt đầu nghe" để xem toàn bộ luồng realtime.',
                                        'No logs yet. Tap "Start listening" to inspect the full realtime flow.',
                                      ),
                                      style: const TextStyle(
                                        color: Color(0xFFCBD5E1),
                                        height: 1.5,
                                      ),
                                    ),
                                  )
                                : ListView.builder(
                                    itemCount: _debugLines.length,
                                    itemBuilder: (context, index) {
                                      return Padding(
                                        padding:
                                            const EdgeInsets.only(bottom: 6),
                                        child: Text(
                                          _debugLines[index],
                                          style: const TextStyle(
                                            color: Color(0xFFE2E8F0),
                                            fontSize: 12,
                                            height: 1.45,
                                          ),
                                        ),
                                      );
                                    },
                                  ),
                          ),
                        ],
                      ),
                    ),
                  ),
                  const SizedBox(height: 24),
                  ],
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }

  @override
  // Rời màn: dừng voice, giải phóng micro/audio.

  void dispose() {
    _cancelNavigationFallback();
    _statusSub?.cancel();
    _resultSub?.cancel();
    _readySub?.cancel();
    _errorSub?.cancel();
    _debugSub?.cancel();
    _speechEndSub?.cancel();
    _disposeAudioCapture();
    _messageAudioPlayer?.pause();
    _messageAudioPlayer = null;
    super.dispose();
  }
}

// Widget thông báo trình duyệt không hỗ trợ voice.

class _VoiceUnsupported extends StatelessWidget {
  final VoidCallback onOpenTextMode;

  const _VoiceUnsupported({required this.onOpenTextMode});

  @override
  // Dựng thông báo không hỗ trợ voice.

  Widget build(BuildContext context) {
    final strings = AppStrings.of(context);
    return Center(
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 640),
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Container(
            padding: const EdgeInsets.all(24),
            decoration: BoxDecoration(
              color: Colors.white,
              borderRadius: BorderRadius.circular(28),
              border: Border.all(color: const Color(0xFFE2E8F0)),
            ),
            child: Column(mainAxisSize: MainAxisSize.min, children: [
              const Icon(Icons.mic_off_outlined,
                  size: 54, color: Color(0xFFDC2626)),
              const SizedBox(height: 16),
              Text(
                strings.pick(
                  'Trình duyệt hiện tại không hỗ trợ Web Speech API',
                  'Your current browser does not support the Web Speech API',
                ),
                textAlign: TextAlign.center,
                style:
                    const TextStyle(fontSize: 24, fontWeight: FontWeight.w800),
              ),
              const SizedBox(height: 12),
              Text(
                strings.pick(
                  'Chế độ voice cần SpeechRecognition và speechSynthesis của trình duyệt. Bạn vẫn có thể dùng đầy đủ trợ lý AI bằng giao diện chat text.',
                  'Voice mode requires browser SpeechRecognition and speechSynthesis support. You can still use the full assistant in text chat mode.',
                ),
                textAlign: TextAlign.center,
                style: const TextStyle(color: Color(0xFF475569), height: 1.6),
              ),
              const SizedBox(height: 18),
              FilledButton.icon(
                onPressed: onOpenTextMode,
                icon: const Icon(Icons.smart_toy_outlined),
                label: Text(strings.pick(
                    'Mở trợ lý AI dạng chat', 'Open AI chat assistant')),
              ),
            ]),
          ),
        ),
      ),
    );
  }
}

class _VoiceCircle extends ConsumerStatefulWidget {
  final bool isCompact;
  final String status;
  final String statusLabel;
  final String fallbackDetail;
  final String? taskId;
  final Future<void> Function() onStop;

  const _VoiceCircle({
    required this.isCompact,
    required this.status,
    required this.statusLabel,
    required this.fallbackDetail,
    required this.taskId,
    required this.onStop,
  });

  @override
  ConsumerState<_VoiceCircle> createState() => _VoiceCircleState();
}

class _VoiceCircleState extends ConsumerState<_VoiceCircle>
    with TickerProviderStateMixin {
  late final AnimationController _pulse = AnimationController(
    vsync: this,
    duration: const Duration(milliseconds: 1600),
  )..repeat(reverse: true);
  late final AnimationController _spin = AnimationController(
    vsync: this,
    duration: const Duration(seconds: 14),
  )..repeat();
  double _displayedPercent = 0;

  @override
  void dispose() {
    _pulse.dispose();
    _spin.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final size = widget.status == 'listening'
        ? (widget.isCompact ? 210.0 : 240.0)
        : (widget.isCompact ? 190.0 : 220.0);
    final tid = widget.taskId;
    if (tid == null) {
      return _buildCircle(
        size: size,
        accent: _accentForStatus(widget.status),
        percent: null,
        stageLabel: widget.statusLabel,
        detailLine: widget.fallbackDetail,
        streamingText: '',
        showStop: false,
        showRing: false,
      );
    }
    final asyncState = ref.watch(aiTaskProgressProvider(
      AITaskPollConfig(
        taskId: tid,
        pollInterval: const Duration(milliseconds: 400),
      ),
    ));
    return asyncState.when(
      loading: () => _buildCircle(
        size: size,
        accent: const Color(0xFFF97316),
        percent: 0,
        stageLabel: 'Đang khởi tạo…',
        detailLine: widget.fallbackDetail,
        streamingText: '',
        showStop: true,
        showRing: true,
      ),
      error: (_, __) => _buildCircle(
        size: size,
        accent: const Color(0xFFF97316),
        percent: null,
        stageLabel: widget.statusLabel,
        detailLine: widget.fallbackDetail,
        streamingText: '',
        showStop: true,
        showRing: false,
      ),
      data: (s) {
        final stage = s.stage.isNotEmpty ? s.stage : widget.statusLabel;
        final detail =
            s.detail.isNotEmpty ? s.detail : widget.fallbackDetail;
        final accent = s.status == 'completed'
            ? const Color(0xFF22C55E)
            : s.status == 'failed'
                ? const Color(0xFFEF4444)
                : s.status == 'cancelled'
                    ? const Color(0xFFF59E0B)
                    : const Color(0xFFF97316);
        return _buildCircle(
          size: size,
          accent: accent,
          percent: s.percent,
          stageLabel: stage,
          detailLine: detail,
          streamingText: s.streamingText,
          showStop: s.status == 'running' || s.status == 'queued',
          showRing: true,
        );
      },
    );
  }

  Color _accentForStatus(String s) {
    return s == 'processing'
        ? const Color(0xFFF97316)
        : s == 'speaking'
            ? const Color(0xFF22C55E)
            : const Color(0xFF38BDF8);
  }

  Widget _buildCircle({
    required double size,
    required Color accent,
    required int? percent,
    required String stageLabel,
    required String detailLine,
    required String streamingText,
    required bool showStop,
    required bool showRing,
  }) {
    final ringStroke = widget.isCompact ? 6.0 : 8.0;
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        SizedBox(
          width: size + 28,
          height: size + 28,
          child: Stack(
            alignment: Alignment.center,
            children: [
              AnimatedBuilder(
                animation: _pulse,
                builder: (_, __) {
                  final pulse =
                      0.85 + 0.15 * math.sin(_pulse.value * math.pi);
                  return Container(
                    width: (size + 24) * pulse,
                    height: (size + 24) * pulse,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: RadialGradient(
                        colors: [
                          accent.withOpacity(0.28),
                          accent.withOpacity(0.0),
                        ],
                      ),
                    ),
                  );
                },
              ),
              AnimatedContainer(
                duration: const Duration(milliseconds: 240),
                width: size,
                height: size,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  gradient: RadialGradient(
                    colors: [
                      accent,
                      const Color(0xFF1D4ED8),
                      const Color(0xFF0F172A),
                    ],
                  ),
                  boxShadow: [
                    BoxShadow(
                      color: accent.withOpacity(0.42),
                      blurRadius: 60,
                      spreadRadius: 8,
                    ),
                  ],
                ),
              ),
              if (showRing && percent != null)
                TweenAnimationBuilder<double>(
                  tween: Tween<double>(
                    begin: _displayedPercent,
                    end: percent.toDouble(),
                  ),
                  duration: const Duration(milliseconds: 380),
                  curve: Curves.easeOutCubic,
                  onEnd: () =>
                      _displayedPercent = percent.toDouble(),
                  builder: (context, value, _) {
                    return AnimatedBuilder(
                      animation: _spin,
                      builder: (_, __) {
                        return Transform.rotate(
                          angle: _spin.value * math.pi * 2,
                          child: SizedBox(
                            width: size - 4,
                            height: size - 4,
                            child: CustomPaint(
                              painter: _VoiceRingPainter(
                                value:
                                    (value / 100.0).clamp(0.0, 1.0),
                                strokeWidth: ringStroke,
                                trackColor:
                                    Colors.white.withOpacity(0.16),
                                glow: Colors.white,
                              ),
                            ),
                          ),
                        );
                      },
                    );
                  },
                ),
              Padding(
                padding: EdgeInsets.symmetric(
                    horizontal: widget.isCompact ? 18 : 24),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    if (percent != null) ...[
                      AnimatedSwitcher(
                        duration: const Duration(milliseconds: 200),
                        child: Text(
                          '$percent%',
                          key: ValueKey<int>(percent),
                          style: TextStyle(
                            color: Colors.white,
                            fontSize:
                                widget.isCompact ? 28 : 34,
                            fontWeight: FontWeight.w900,
                            height: 1.05,
                            letterSpacing: -0.6,
                          ),
                        ),
                      ),
                      const SizedBox(height: 2),
                    ],
                    AnimatedSwitcher(
                      duration: const Duration(milliseconds: 240),
                      child: Text(
                        stageLabel,
                        key: ValueKey<String>(stageLabel),
                        textAlign: TextAlign.center,
                        maxLines: 2,
                        overflow: TextOverflow.ellipsis,
                        style: TextStyle(
                          color: Colors.white,
                          fontSize: percent != null
                              ? (widget.isCompact ? 12.5 : 14)
                              : (widget.isCompact ? 22 : 26),
                          fontWeight: percent != null
                              ? FontWeight.w700
                              : FontWeight.w800,
                          height: 1.25,
                        ),
                      ),
                    ),
                  ],
                ),
              ),
              if (showStop)
                Positioned(
                  top: 12,
                  right: 12,
                  child: Tooltip(
                    message: 'Dừng tiến trình AI',
                    child: Material(
                      color: Colors.black.withOpacity(0.6),
                      shape: const CircleBorder(),
                      elevation: 4,
                      child: InkWell(
                        customBorder: const CircleBorder(),
                        onTap: widget.onStop,
                        child: const Padding(
                          padding: EdgeInsets.all(7),
                          child: Icon(
                            Icons.close_rounded,
                            size: 18,
                            color: Colors.white,
                          ),
                        ),
                      ),
                    ),
                  ),
                ),
            ],
          ),
        ),
        if (detailLine.isNotEmpty) ...[
          SizedBox(height: widget.isCompact ? 10 : 14),
          AnimatedSwitcher(
            duration: const Duration(milliseconds: 220),
            child: Text(
              detailLine,
              key: ValueKey<String>(detailLine),
              textAlign: TextAlign.center,
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
              style: TextStyle(
                color: const Color(0xFFCBD5E1),
                fontSize: widget.isCompact ? 13 : 14.5,
                height: 1.45,
              ),
            ),
          ),
        ],
        if (streamingText.trim().isNotEmpty) ...[
          SizedBox(height: widget.isCompact ? 10 : 12),
          ConstrainedBox(
            constraints: BoxConstraints(
              maxWidth: widget.isCompact ? 320 : 420,
              maxHeight: widget.isCompact ? 80 : 120,
            ),
            child: Container(
              padding: const EdgeInsets.symmetric(
                  horizontal: 14, vertical: 10),
              decoration: BoxDecoration(
                color: Colors.white.withOpacity(0.06),
                borderRadius: BorderRadius.circular(14),
                border: Border.all(
                  color: Colors.white.withOpacity(0.12),
                ),
              ),
              child: SingleChildScrollView(
                reverse: true,
                child: Text(
                  streamingText,
                  textAlign: TextAlign.center,
                  style: const TextStyle(
                    color: Color(0xFFE2E8F0),
                    fontSize: 12.5,
                    height: 1.55,
                    fontStyle: FontStyle.italic,
                  ),
                ),
              ),
            ),
          ),
        ],
      ],
    );
  }
}

class _VoiceRingPainter extends CustomPainter {
  final double value;
  final double strokeWidth;
  final Color trackColor;
  final Color glow;

  _VoiceRingPainter({
    required this.value,
    required this.strokeWidth,
    required this.trackColor,
    required this.glow,
  });

  @override
  void paint(Canvas canvas, Size size) {
    final center = Offset(size.width / 2, size.height / 2);
    final radius = (math.min(size.width, size.height) - strokeWidth) / 2;
    final rect = Rect.fromCircle(center: center, radius: radius);

    final trackPaint = Paint()
      ..color = trackColor
      ..style = PaintingStyle.stroke
      ..strokeWidth = strokeWidth
      ..strokeCap = StrokeCap.round;
    canvas.drawArc(rect, 0, math.pi * 2, false, trackPaint);

    if (value > 0) {
      final sweep = math.pi * 2 * value;
      final start = -math.pi / 2;
      final shader = SweepGradient(
        startAngle: start,
        endAngle: start + sweep,
        tileMode: TileMode.clamp,
        colors: [
          glow.withOpacity(0.0),
          glow.withOpacity(0.6),
          glow,
        ],
        stops: const [0.0, 0.4, 1.0],
      ).createShader(rect);
      final progressPaint = Paint()
        ..shader = shader
        ..style = PaintingStyle.stroke
        ..strokeWidth = strokeWidth
        ..strokeCap = StrokeCap.round
        ..maskFilter = const MaskFilter.blur(BlurStyle.solid, 0.6);
      canvas.drawArc(rect, start, sweep, false, progressPaint);
    }
  }

  @override
  bool shouldRepaint(_VoiceRingPainter old) =>
      old.value != value ||
      old.strokeWidth != strokeWidth ||
      old.trackColor != trackColor ||
      old.glow != glow;
}
