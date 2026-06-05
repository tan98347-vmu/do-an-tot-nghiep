import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../core/api_client.dart';
import '../models/template_manual_edit_session.dart';

class TemplateManualEditApi {
  const TemplateManualEditApi();

  Future<TemplateManualEditSession> ensureSession(int templateId) async {
    final response = await ApiClient().dio.post(
      'templates/$templateId/manual-edit/session/',
      data: const <String, dynamic>{},
    );
    return TemplateManualEditSession.fromJson(
      response.data['session'] as Map<String, dynamic>,
    );
  }

  Future<TemplateManualEditSession> getSession(int sessionId) async {
    final response = await ApiClient().dio.get(
      'templates/manual-edit/sessions/$sessionId/',
    );
    return TemplateManualEditSession.fromJson(
      response.data as Map<String, dynamic>,
    );
  }

  Future<TemplateManualEditSession> heartbeatSession(int sessionId) async {
    final response = await ApiClient().dio.post(
      'templates/manual-edit/sessions/$sessionId/heartbeat/',
      data: const <String, dynamic>{},
    );
    return TemplateManualEditSession.fromJson(
      response.data as Map<String, dynamic>,
    );
  }

  Future<TemplateManualEditFinishResponse> finishSession(
    int sessionId, {
    String changeNote = '',
  }) async {
    final response = await ApiClient().dio.post(
      'templates/manual-edit/sessions/$sessionId/finish/',
      data: <String, dynamic>{'change_note': changeNote},
    );
    return TemplateManualEditFinishResponse.fromJson(
      response.data as Map<String, dynamic>,
    );
  }

  Future<TemplateManualEditSession> cancelSession(int sessionId) async {
    final response = await ApiClient().dio.post(
      'templates/manual-edit/sessions/$sessionId/cancel/',
      data: const <String, dynamic>{},
    );
    return TemplateManualEditSession.fromJson(
      response.data as Map<String, dynamic>,
    );
  }
}

final templateManualEditApiProvider = Provider<TemplateManualEditApi>(
  (_) => const TemplateManualEditApi(),
);

String describeTemplateManualEditError(Object error) {
  if (error is DioException) {
    final data = error.response?.data;
    if (data is Map && data['detail'] != null) {
      return '${data['detail']}';
    }
    return 'Khong mo duoc trinh sua thu cong cua mau (${error.response?.statusCode ?? 'network'}).';
  }
  if (error is StateError) {
    final message = '$error';
    return message.replaceFirst('Bad state: ', '').trim();
  }
  return '$error';
}
