import 'browser_voice_input_base.dart';

BrowserVoiceInputController createBrowserVoiceInputController() {
  return _UnsupportedBrowserVoiceInputController();
}

class _UnsupportedBrowserVoiceInputController
    implements BrowserVoiceInputController {
  @override
  bool get isListening => false;

  @override
  bool get isSupported => false;

  @override
  void dispose() {}

  @override
  Future<bool> start({
    required BrowserVoiceTranscriptCallback onTranscript,
    BrowserVoiceStatusCallback? onStatus,
    BrowserVoiceErrorCallback? onError,
  }) async {
    onError?.call(
      'Nhap giong noi chi ho tro tren Flutter Web voi trinh duyet co SpeechRecognition.',
    );
    return false;
  }

  @override
  Future<void> stop() async {}
}
