import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../core/api_client.dart';
import '../models/document_manual_edit_session.dart';

class DocumentManualEditApi {
  const DocumentManualEditApi();

  Future<DocumentManualEditSession> ensureSession(int documentId) async {
    final response = await ApiClient().dio.post(
      'documents/$documentId/manual-edit/session/',
      data: const <String, dynamic>{},
    );
    return DocumentManualEditSession.fromJson(
      response.data['session'] as Map<String, dynamic>,
    );
  }

  Future<DocumentManualEditSession> getSession(int sessionId) async {
    final response = await ApiClient().dio.get(
          'documents/manual-edit/sessions/$sessionId/',
        );
    return DocumentManualEditSession.fromJson(
        response.data as Map<String, dynamic>);
  }

  Future<DocumentManualEditSession> heartbeatSession(int sessionId) async {
    final response = await ApiClient().dio.post(
      'documents/manual-edit/sessions/$sessionId/heartbeat/',
      data: const <String, dynamic>{},
    );
    return DocumentManualEditSession.fromJson(
        response.data as Map<String, dynamic>);
  }

  Future<DocumentManualEditFinishResponse> finishSession(
    int sessionId, {
    String changeNote = '',
  }) async {
    final response = await ApiClient().dio.post(
      'documents/manual-edit/sessions/$sessionId/finish/',
      data: <String, dynamic>{'change_note': changeNote},
    );
    return DocumentManualEditFinishResponse.fromJson(
      response.data as Map<String, dynamic>,
    );
  }

  Future<DocumentManualEditSession> cancelSession(int sessionId) async {
    final response = await ApiClient().dio.post(
      'documents/manual-edit/sessions/$sessionId/cancel/',
      data: const <String, dynamic>{},
    );
    return DocumentManualEditSession.fromJson(
        response.data as Map<String, dynamic>);
  }
}

final documentManualEditApiProvider = Provider<DocumentManualEditApi>(
  (_) => const DocumentManualEditApi(),
);

String describeManualEditError(Object error) {
  if (error is DioException) {
    final data = error.response?.data;
    if (data is Map && data['detail'] != null) {
      return '${data['detail']}';
    }
    return 'Khong mo duoc trinh sua thu cong (${error.response?.statusCode ?? 'network'}).';
  }
  if (error is StateError) {
    final message = '$error';
    return message.replaceFirst('Bad state: ', '').trim();
  }
  return '$error';
}
