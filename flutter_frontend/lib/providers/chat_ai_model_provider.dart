import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../core/api_client.dart';

/// Returns the chat AI model name resolved for the current user.
/// Falls back to 'kimi-k2.6:cloud' if the endpoint is unavailable or empty.
final chatAiModelProvider = FutureProvider.autoDispose<String>((ref) async {
  try {
    final resp = await ApiClient().dio.get('ai/chat-model/');
    final data = (resp.data as Map).cast<String, dynamic>();
    final name = (data['model'] ?? data['display_name'] ?? '').toString().trim();
    if (name.isEmpty) return 'kimi-k2.6:cloud';
    return name;
  } catch (_) {
    return 'kimi-k2.6:cloud';
  }
});
