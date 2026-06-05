// ignore_for_file: avoid_web_libraries_in_flutter, uri_does_not_exist

import 'dart:async';
import 'dart:html' as html;
import 'dart:js_util' as js_util;

import 'browser_voice_input_base.dart';

BrowserVoiceInputController createBrowserVoiceInputController() {
  return _WebBrowserVoiceInputController();
}

class _WebBrowserVoiceInputController implements BrowserVoiceInputController {
  StreamSubscription<html.Event>? _statusSub;
  StreamSubscription<html.Event>? _resultSub;
  StreamSubscription<html.Event>? _readySub;
  StreamSubscription<html.Event>? _errorSub;

  BrowserVoiceTranscriptCallback? _onTranscript;
  BrowserVoiceStatusCallback? _onStatus;
  BrowserVoiceErrorCallback? _onError;
  bool _listening = false;
  bool _eventsBound = false;

  @override
  bool get isListening => _listening;

  dynamic get _bridge {
    if (!js_util.hasProperty(html.window, 'aiAssistantVoice')) {
      return null;
    }
    return js_util.getProperty(html.window, 'aiAssistantVoice');
  }

  @override
  bool get isSupported {
    final bridge = _bridge;
    if (bridge == null) {
      return false;
    }
    try {
      return js_util.callMethod(bridge, 'isSupported', const []) == true;
    } catch (_) {
      return false;
    }
  }

  @override
  Future<bool> start({
    required BrowserVoiceTranscriptCallback onTranscript,
    BrowserVoiceStatusCallback? onStatus,
    BrowserVoiceErrorCallback? onError,
  }) async {
    _onTranscript = onTranscript;
    _onStatus = onStatus;
    _onError = onError;
    _bindEvents();
    final bridge = _bridge;
    if (bridge == null) {
      onError?.call(
        'Không tìm thấy voice bridge trên web shell. Vui lòng reload lại trang.',
      );
      return false;
    }
    try {
      return js_util.callMethod(bridge, 'startListening', const []) == true;
    } catch (error) {
      onError?.call('$error');
      return false;
    }
  }

  @override
  Future<void> stop() async {
    final bridge = _bridge;
    if (bridge == null) {
      _listening = false;
      return;
    }
    try {
      js_util.callMethod(bridge, 'stopListening', const []);
    } catch (_) {}
  }

  void _bindEvents() {
    if (_eventsBound) {
      return;
    }
    _eventsBound = true;
    _statusSub = html.EventStreamProvider<html.Event>(
      'ai-assistant-voice-status',
    ).forTarget(html.window).listen((event) {
      final detail = _detail(event);
      final status = '${detail['status'] ?? 'idle'}'.trim();
      _listening = status == 'listening';
      _onStatus?.call(status);
    });
    _resultSub = html.EventStreamProvider<html.Event>(
      'ai-assistant-voice-result',
    ).forTarget(html.window).listen((event) {
      final detail = _detail(event);
      final transcript = '${detail['transcript'] ?? ''}'.trim();
      if (transcript.isEmpty) {
        return;
      }
      _onTranscript?.call(transcript, isFinal: false);
    });
    _readySub = html.EventStreamProvider<html.Event>(
      'ai-assistant-voice-ready',
    ).forTarget(html.window).listen((event) {
      final detail = _detail(event);
      final transcript = '${detail['transcript'] ?? ''}'.trim();
      _listening = false;
      if (transcript.isEmpty) {
        return;
      }
      _onTranscript?.call(transcript, isFinal: true);
    });
    _errorSub = html.EventStreamProvider<html.Event>(
      'ai-assistant-voice-error',
    ).forTarget(html.window).listen((event) {
      final detail = _detail(event);
      _listening = false;
      final message = '${detail['message'] ?? ''}'.trim();
      if (message.isNotEmpty) {
        _onError?.call(message);
      }
    });
  }

  Map<String, dynamic> _detail(html.Event event) {
    try {
      final detail = js_util.getProperty(event, 'detail');
      if (detail == null) {
        return const <String, dynamic>{};
      }
      if (detail is Map<String, dynamic>) {
        return detail;
      }
      if (detail is Map) {
        return detail.cast<String, dynamic>();
      }
      final dartified = js_util.dartify(detail);
      if (dartified is Map<String, dynamic>) {
        return dartified;
      }
      if (dartified is Map) {
        return Map<String, dynamic>.from(dartified);
      }
    } catch (_) {}
    return const <String, dynamic>{};
  }

  @override
  void dispose() {
    _statusSub?.cancel();
    _resultSub?.cancel();
    _readySub?.cancel();
    _errorSub?.cancel();
    _statusSub = null;
    _resultSub = null;
    _readySub = null;
    _errorSub = null;
    _eventsBound = false;
    _listening = false;
  }
}
