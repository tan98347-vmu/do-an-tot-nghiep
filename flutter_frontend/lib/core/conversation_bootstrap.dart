import 'package:shared_preferences/shared_preferences.dart';

class ConversationBootstrapStore {
  static const assistantTextFeature = 'assistant_text';
  static const assistantVoiceFeature = 'assistant_voice';
  static const ragTemplateFeature = 'rag_template';
  static const ragDocumentFeature = 'rag_document';

  static const _loginMarkerKey = 'conversation_login_marker';
  static const _features = <String>[
    assistantTextFeature,
    assistantVoiceFeature,
    ragTemplateFeature,
    ragDocumentFeature,
  ];

  static String ragFeatureForMode(String mode) {
    return mode == 'document' ? ragDocumentFeature : ragTemplateFeature;
  }

  static Future<void> beginLoginCycle() async {
    final prefs = await SharedPreferences.getInstance();
    final marker = DateTime.now().microsecondsSinceEpoch;
    await prefs.setInt(_loginMarkerKey, marker);
    for (final feature in _features) {
      await prefs.remove(_consumedKey(feature));
      await prefs.remove(_activeKey(feature));
    }
  }

  static Future<void> reset() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(_loginMarkerKey);
    for (final feature in _features) {
      await prefs.remove(_consumedKey(feature));
      await prefs.remove(_activeKey(feature));
    }
  }

  static Future<bool> shouldStartFresh(String feature) async {
    final prefs = await SharedPreferences.getInstance();
    final loginMarker = prefs.getInt(_loginMarkerKey);
    if (loginMarker == null) {
      return false;
    }
    return prefs.getInt(_consumedKey(feature)) != loginMarker;
  }

  static Future<void> markConversationChosen(String feature) async {
    final prefs = await SharedPreferences.getInstance();
    final loginMarker = prefs.getInt(_loginMarkerKey);
    if (loginMarker == null) {
      return;
    }
    await prefs.setInt(_consumedKey(feature), loginMarker);
  }

  static Future<int?> getRememberedSessionId(String feature) async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getInt(_activeKey(feature));
  }

  static Future<void> rememberSession(String feature, int? sessionId) async {
    final prefs = await SharedPreferences.getInstance();
    if (sessionId == null) {
      await prefs.remove(_activeKey(feature));
      return;
    }
    await prefs.setInt(_activeKey(feature), sessionId);
  }

  static String _consumedKey(String feature) =>
      'conversation_login_consumed_$feature';

  static String _activeKey(String feature) =>
      'conversation_active_session_$feature';
}
