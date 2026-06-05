typedef BrowserVoiceTranscriptCallback = void Function(
  String transcript, {
  required bool isFinal,
});

typedef BrowserVoiceStatusCallback = void Function(String status);
typedef BrowserVoiceErrorCallback = void Function(String message);

abstract class BrowserVoiceInputController {
  bool get isSupported;
  bool get isListening;

  Future<bool> start({
    required BrowserVoiceTranscriptCallback onTranscript,
    BrowserVoiceStatusCallback? onStatus,
    BrowserVoiceErrorCallback? onError,
  });

  Future<void> stop();
  void dispose();
}
