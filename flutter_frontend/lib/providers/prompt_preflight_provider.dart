import 'package:dio/dio.dart';

import '../core/api_client.dart';

class PromptPreflightResult {
  final String verdict;
  final String? promptCheckToken;
  final String message;
  final String reason;
  final List<String> flags;
  final List<String> suggestions;

  const PromptPreflightResult({
    required this.verdict,
    this.promptCheckToken,
    this.message = '',
    this.reason = '',
    this.flags = const [],
    this.suggestions = const [],
  });

  bool get passed => verdict == 'pass' && (promptCheckToken ?? '').isNotEmpty;

  factory PromptPreflightResult.fromJson(Map<String, dynamic> json) {
    return PromptPreflightResult(
      verdict: (json['verdict'] ?? '').toString(),
      promptCheckToken: json['prompt_check_token']?.toString(),
      message: (json['message'] ?? '').toString(),
      reason: (json['reason'] ?? json['detail'] ?? '').toString(),
      flags: ((json['flags'] as List?) ?? const [])
          .map((item) => item.toString())
          .toList(),
      suggestions: ((json['suggestions'] as List?) ?? const [])
          .map((item) => item.toString())
          .toList(),
    );
  }
}

Future<PromptPreflightResult> checkPromptPreflight({
  required String scope,
  required String context,
  required String promptRole,
  required String promptText,
  Object? targetId,
}) async {
  try {
    final response = await ApiClient().dio.post(
      'prompts/check/',
      data: {
        'scope': scope,
        'context': context,
        'prompt_role': promptRole,
        'prompt_text': promptText.trim(),
        if (targetId != null) 'target_id': targetId,
      },
    );
    return PromptPreflightResult.fromJson(
      Map<String, dynamic>.from(response.data as Map),
    );
  } on DioException catch (error) {
    final data = error.response?.data;
    if (data is Map) {
      return PromptPreflightResult.fromJson(
        Map<String, dynamic>.from(data),
      );
    }
    return PromptPreflightResult(
      verdict: 'block',
      reason: error.message ?? 'Không thể kiểm tra prompt.',
      flags: const ['request_error'],
    );
  }
}

/// Mot bien dien tay bi LLM danh gia la khong phu hop kieu bien (suy tu ten).
class VariableFormatIssue {
  final String name;
  final String value;
  final String reason;

  const VariableFormatIssue({
    required this.name,
    required this.value,
    required this.reason,
  });

  factory VariableFormatIssue.fromJson(Map<String, dynamic> json) {
    return VariableFormatIssue(
      name: (json['name'] ?? '').toString(),
      value: (json['value'] ?? '').toString(),
      reason: (json['reason'] ?? '').toString(),
    );
  }
}

/// Ket qua kiem tra dinh dang bien (CHI canh bao, khong chan). `available=false`
/// nghia la khong kiem tra duoc (LLM loi) -> frontend bao nhe roi van cho tao.
class VariableFormatCheckResult {
  final bool available;
  final List<VariableFormatIssue> issues;

  const VariableFormatCheckResult({
    required this.available,
    this.issues = const [],
  });

  bool get hasIssues => available && issues.isNotEmpty;
}

/// Kiem tra dinh dang bien bang LLM cho rieng luong sinh van ban tu mau.
/// Fail-open: moi loi mang/HTTP -> available=false (khong chan tao van ban).
Future<VariableFormatCheckResult> checkVariableFormats({
  required Object templateId,
  required Map<String, String> variables,
}) async {
  try {
    final response = await ApiClient().dio.post(
      'ai/doc/check-variables/',
      data: {
        'template_id': templateId,
        'variables': variables,
      },
    );
    final data = Map<String, dynamic>.from(response.data as Map);
    final issues = ((data['issues'] as List?) ?? const [])
        .map((item) =>
            VariableFormatIssue.fromJson(Map<String, dynamic>.from(item as Map)))
        .toList();
    return VariableFormatCheckResult(
      available: data['available'] == true,
      issues: issues,
    );
  } catch (_) {
    return const VariableFormatCheckResult(available: false);
  }
}

String promptPreflightFailureMessage(PromptPreflightResult result) {
  final buffer = StringBuffer();
  final reason = result.reason.trim();
  buffer.writeln(reason.isEmpty ? 'Prompt không đạt yêu cầu.' : reason);
  if (result.flags.isNotEmpty) {
    buffer.writeln();
    buffer.writeln('Dấu hiệu: ${result.flags.join(', ')}');
  }
  if (result.suggestions.isNotEmpty) {
    buffer.writeln();
    buffer.writeln('Gợi ý sửa:');
    for (final suggestion in result.suggestions) {
      buffer.writeln('- $suggestion');
    }
  }
  return buffer.toString().trim();
}
