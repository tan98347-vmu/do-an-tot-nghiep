import 'package:dio/dio.dart';
import 'package:flutter_facebook_auth/flutter_facebook_auth.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:google_sign_in/google_sign_in.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../core/api_client.dart';
import '../core/conversation_bootstrap.dart';
import '../models/user.dart';

final _googleSignIn = GoogleSignIn(
  clientId: '298318684696-0s1neh9d5t028smim9pe1epqd44mm8pc.apps.googleusercontent.com',
  scopes: ['email', 'profile'],
);

class CompanySuggestion {
  final int id;
  final String code;
  final String slug;
  final String name;

  const CompanySuggestion({
    required this.id,
    required this.code,
    required this.slug,
    required this.name,
  });

  factory CompanySuggestion.fromJson(Map<String, dynamic> json) => CompanySuggestion(
        id: json['id'] as int? ?? 0,
        code: json['code'] as String? ?? '',
        slug: json['slug'] as String? ?? '',
        name: json['name'] as String? ?? '',
      );
}

class AuthNotifier extends AsyncNotifier<AppUser?> {
  @override
  Future<AppUser?> build() async {
    final token = await ApiClient.getAccessToken();
    if (token == null) return null;
    try {
      final response = await ApiClient().dio.get('auth/me/');
      return AppUser.fromJson(Map<String, dynamic>.from(response.data as Map));
    } catch (_) {
      return null;
    }
  }

  Future<String?> login({
    required String identifier,
    required String password,
    required String loginScope,
    int? companyId,
  }) async {
    try {
      final response = await ApiClient().dio.post(
        'auth/login/',
        data: {
          'identifier': identifier,
          'password': password,
          'login_scope': loginScope,
          if (companyId != null) 'company_id': companyId,
        },
      );
      await ApiClient.saveTokens(
        response.data['access'] as String,
        response.data['refresh'] as String,
      );
      await ConversationBootstrapStore.beginLoginCycle();
      state = AsyncData(AppUser.fromJson(Map<String, dynamic>.from(response.data['user'] as Map)));
      return null;
    } on DioException catch (error) {
      final payload = error.response?.data;
      if (payload is Map && payload['detail'] is String) {
        return payload['detail'] as String;
      }
      if (error.response != null) {
        return 'Loi ${error.response?.statusCode}';
      }
      return 'Khong ket noi duoc server (${error.message}). URL: ${ApiClient.baseUrl}';
    } catch (error) {
      return 'Loi khong xac dinh: $error';
    }
  }

  Future<List<CompanySuggestion>> fetchCompanySuggestions(String query) async {
    final normalized = query.trim();
    if (normalized.isEmpty) {
      return const [];
    }
    final response = await ApiClient().dio.get(
      'public/companies/suggest/',
      queryParameters: {'q': normalized},
    );
    final data = response.data as List<dynamic>? ?? const [];
    return data
        .map((item) => CompanySuggestion.fromJson(Map<String, dynamic>.from(item as Map)))
        .toList();
  }

  Future<void> logout() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final refresh = prefs.getString('refresh_token');
      if (refresh != null && refresh.isNotEmpty) {
        await ApiClient().dio.post('auth/logout/', data: {'refresh': refresh});
      }
    } catch (_) {}
    await ApiClient.clearTokens();
    await ConversationBootstrapStore.reset();
    try {
      await _googleSignIn.signOut();
    } catch (_) {}
    state = const AsyncData(null);
  }

  Future<String?> loginWithGoogle() async {
    try {
      final account = await _googleSignIn.signIn();
      if (account == null) return null;
      final auth = await account.authentication;
      final idToken = auth.idToken;
      if (idToken == null) return 'Khong lay duoc Google ID token.';

      final response = await ApiClient().dio.post(
        'auth/social/google/',
        data: {'credential': idToken},
      );
      await ApiClient.saveTokens(
        response.data['access'] as String,
        response.data['refresh'] as String,
      );
      await ConversationBootstrapStore.beginLoginCycle();
      state = AsyncData(AppUser.fromJson(Map<String, dynamic>.from(response.data['user'] as Map)));
      return null;
    } on DioException catch (error) {
      final payload = error.response?.data;
      if (payload is Map && payload['detail'] is String) {
        return payload['detail'] as String;
      }
      return 'Dang nhap Google that bai.';
    } catch (error) {
      return 'Loi: $error';
    }
  }

  Future<String?> loginWithFacebook() async {
    try {
      final result = await FacebookAuth.i.login(permissions: ['email', 'public_profile']);
      if (result.status != LoginStatus.success) {
        if (result.status == LoginStatus.cancelled) return null;
        return result.message ?? 'Dang nhap Facebook that bai.';
      }
      final accessToken = result.accessToken?.tokenString;
      if (accessToken == null) return 'Khong lay duoc Facebook access token.';

      final response = await ApiClient().dio.post(
        'auth/social/facebook/',
        data: {'access_token': accessToken},
      );
      await ApiClient.saveTokens(
        response.data['access'] as String,
        response.data['refresh'] as String,
      );
      await ConversationBootstrapStore.beginLoginCycle();
      state = AsyncData(AppUser.fromJson(Map<String, dynamic>.from(response.data['user'] as Map)));
      return null;
    } on DioException catch (error) {
      final payload = error.response?.data;
      if (payload is Map && payload['detail'] is String) {
        return payload['detail'] as String;
      }
      return 'Dang nhap Facebook that bai.';
    } catch (error) {
      return 'Loi: $error';
    }
  }

  Future<void> refreshUser() async {
    try {
      final response = await ApiClient().dio.get('auth/me/');
      state = AsyncData(AppUser.fromJson(Map<String, dynamic>.from(response.data as Map)));
    } catch (_) {}
  }

  Future<String?> register(Map<String, String> data) async {
    try {
      final response = await ApiClient().dio.post('auth/register/', data: data);
      await ApiClient.saveTokens(
        response.data['access'] as String,
        response.data['refresh'] as String,
      );
      await ConversationBootstrapStore.beginLoginCycle();
      state = AsyncData(AppUser.fromJson(Map<String, dynamic>.from(response.data['user'] as Map)));
      return null;
    } on DioException catch (error) {
      final payload = error.response?.data;
      if (payload is Map && payload['detail'] is String) {
        return payload['detail'] as String;
      }
      if (payload is Map && payload.isNotEmpty) {
        return payload.values.first.toString();
      }
      return 'Dang ky that bai.';
    } catch (error) {
      return 'Dang ky that bai: $error';
    }
  }
}

final authProvider = AsyncNotifierProvider<AuthNotifier, AppUser?>(AuthNotifier.new);
final authStateProvider = authProvider;
final currentUserProvider = Provider<AppUser?>((ref) => ref.watch(authProvider).asData?.value);
