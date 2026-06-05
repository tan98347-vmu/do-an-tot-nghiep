// Tệp này dùng để: định nghĩa hạ tầng client như router, API client, theme hoặc locale trong flutter_frontend/lib/core/api_client.dart.
// Cách hoạt động: được nạp sớm khi app Flutter khởi động để các màn và provider dùng chung cấu hình nền.
// Vai trò trong hệ thống: Đây là lớp lõi Flutter Web.
// Tác dụng khi hệ thống vận hành: quyết định cách frontend khởi chạy, điều hướng và gọi API.

import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';

// Khi Django serve Flutter (cùng server) → tự động dùng same origin
// Khi chạy native (mobile/desktop) → dùng hardcoded URL
String get _backendUrl {
  if (kIsWeb) {
    return '${Uri.base.origin}/api/';
  }
  return 'http://192.168.1.5:8000/api/';
}

// Mục đích: Lớp `ApiClient` triển khai phần việc `Api Client` trong flutter_frontend/lib/core/api_client.dart.
// Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
// Vai trò trong hệ thống: Đây là lớp thuộc lớp lõi Flutter Web.
// Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

class ApiClient {
  static String get baseUrl => _backendUrl;
  static const Duration ollamaTimeout = Duration(minutes: 20);
  static final ApiClient _instance = ApiClient._internal();
  factory ApiClient() => _instance;

  late final Dio dio;

  ApiClient._internal() {
    dio = Dio(BaseOptions(
      baseUrl: _backendUrl,
      connectTimeout: const Duration(seconds: 30),
      receiveTimeout: const Duration(seconds: 60),
      headers: {'Content-Type': 'application/json'},
    ));

    dio.interceptors.add(InterceptorsWrapper(
      onRequest: (options, handler) async {
        final token = await _readToken('access_token');
        if (token != null) {
          options.headers['Authorization'] = 'Bearer $token';
        }
        if (_isOllamaEndpoint(options.path)) {
          options.connectTimeout = ollamaTimeout;
          options.receiveTimeout = ollamaTimeout;
          options.sendTimeout = ollamaTimeout;
        }
        handler.next(options);
      },
      onError: (error, handler) async {
        if (error.response?.statusCode == 401) {
          final refreshed = await _refreshToken();
          if (refreshed) {
            final token = await _readToken('access_token');
            error.requestOptions.headers['Authorization'] = 'Bearer $token';
            try {
              // Gọi API hoặc tác vụ bất đồng bộ rồi chờ kết quả trước khi cập nhật giao diện.

              final response = await dio.fetch(error.requestOptions);
              return handler.resolve(response);
            } catch (_) {}
          }
          await clearTokens();
        }
        handler.next(error);
      },
    ));
  }

  static Future<String?> _readToken(String key) async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString(key);
  }

  static Future<void> _writeToken(String key, String value) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(key, value);
  }

  static Future<void> _removeToken(String key) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(key);
  }

  // Mục đích: Phương thức `_refreshToken` triển khai phần việc `refresh Token` trong flutter_frontend/lib/core/api_client.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc lớp lõi Flutter Web.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  Future<bool> _refreshToken() async {
    try {
      final refresh = await _readToken('refresh_token');
      if (refresh == null) return false;
      // Gọi API hoặc tác vụ bất đồng bộ rồi chờ kết quả trước khi cập nhật giao diện.

      final resp = await Dio().post(
        '${_backendUrl}auth/refresh/',
        data: {'refresh': refresh},
        options: Options(headers: {'Content-Type': 'application/json'}),
      );
      await _writeToken('access_token', resp.data['access'] as String);
      return true;
    } catch (_) {
      return false;
    }
  }

  static Future<void> saveTokens(String access, String refresh) async {
    await _writeToken('access_token', access);
    await _writeToken('refresh_token', refresh);
  }

  static Future<void> clearTokens() async {
    await _removeToken('access_token');
    await _removeToken('refresh_token');
  }

  static Future<String?> getAccessToken() => _readToken('access_token');

  static Options ollamaOptions({
    String? contentType,
    Map<String, dynamic>? headers,
    ResponseType? responseType,
  }) {
    return Options(
      connectTimeout: ollamaTimeout,
      receiveTimeout: ollamaTimeout,
      sendTimeout: ollamaTimeout,
      contentType: contentType,
      headers: headers,
      responseType: responseType,
    );
  }

  static bool _isOllamaEndpoint(String rawPath) {
    final uri = Uri.tryParse(rawPath);
    var path = uri?.path ?? rawPath;
    if (path.startsWith('/api/')) {
      path = path.substring(5);
    } else if (path.startsWith('/')) {
      path = path.substring(1);
    }

    final exactMatches = <String>{
      'ai/chat/',
      'assistant/turn/',
      'ai/rag/query/',
      'ai/doc/create/',
      'ai/doc/extract-pdf/',
      'ai/doc/extract-image/',
      'ai/doc/prefill-profile/',
      'ai/doc/prefill-company/',
      'templates/import-docx/',
      'templates/import-from-url/',
      'templates/bulk/upload-single/',
      'guest/parse/',
      'guest/parse-pdf/',
      'auth/me/prefill-from-bio/',
    };
    if (exactMatches.contains(path)) {
      return true;
    }

    return RegExp(r'^templates/\d+/(generate-tags|replace-docx)/$')
            .hasMatch(path) ||
        RegExp(r'^documents/\d+/summarize/$').hasMatch(path) ||
        RegExp(r'^document-summaries/\d+/generate/$').hasMatch(path);
  }
}
