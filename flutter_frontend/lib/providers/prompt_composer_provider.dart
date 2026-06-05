import 'dart:convert';

import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../core/api_client.dart';
import '../models/composed_prompt.dart';

class ComposeArgs {
  final String scope;
  final Map<String, dynamic> options;
  final String extra;
  final int? basePromptId;
  final String _optionsSignature;

  ComposeArgs({
    required this.scope,
    required Map<String, dynamic> options,
    required this.extra,
    this.basePromptId,
  })  : options = _normalizeMap(options),
        _optionsSignature = jsonEncode(_normalizeMap(options));

  bool get isEmpty =>
      basePromptId == null &&
      options.isEmpty &&
      extra.trim().isEmpty;

  @override
  bool operator ==(Object other) {
    return other is ComposeArgs &&
        other.scope == scope &&
        other.extra == extra &&
        other.basePromptId == basePromptId &&
        other._optionsSignature == _optionsSignature;
  }

  @override
  int get hashCode => Object.hash(scope, extra, basePromptId, _optionsSignature);

  static Map<String, dynamic> _normalizeMap(Map<String, dynamic> source) {
    final keys = source.keys.toList()..sort();
    final normalized = <String, dynamic>{};
    for (final key in keys) {
      normalized[key] = _normalizeValue(source[key]);
    }
    return normalized;
  }

  static dynamic _normalizeValue(dynamic value) {
    if (value is Map<String, dynamic>) {
      return _normalizeMap(value);
    }
    if (value is Map) {
      return _normalizeMap(Map<String, dynamic>.from(value));
    }
    if (value is List) {
      return value.map(_normalizeValue).toList();
    }
    return value;
  }
}

final composerProvider = AsyncNotifierProvider.autoDispose
    .family<ComposerNotifier, ComposedPrompt, ComposeArgs>(
  ComposerNotifier.new,
);

class ComposerNotifier extends AsyncNotifier<ComposedPrompt> {
  ComposerNotifier(this.args);

  final ComposeArgs args;

  @override
  Future<ComposedPrompt> build() async {
    if (args.isEmpty) {
      return const ComposedPrompt.empty();
    }
    await Future<void>.delayed(const Duration(milliseconds: 300));
    if (!ref.mounted) {
      return const ComposedPrompt.empty();
    }
    final response = await ApiClient().dio.post(
      'prompts/compose-preview/',
      data: {
        'scope': args.scope,
        'options': args.options,
        'extra_user_text': args.extra,
        if (args.basePromptId != null) 'base_prompt_id': args.basePromptId,
      },
    );
    return ComposedPrompt.fromJson(
      Map<String, dynamic>.from(response.data as Map),
    );
  }
}
