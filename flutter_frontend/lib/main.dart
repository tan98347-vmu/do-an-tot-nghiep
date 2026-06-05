// Tệp này dùng để: duy trì logic trong tệp flutter_frontend/lib/main.dart.
// Cách hoạt động: được gọi từ lớp phía trên, xử lý dữ liệu theo vai trò hiện có và trả kết quả về cho luồng gọi.
// Vai trò trong hệ thống: Đây là một thành phần của hệ thống.
// Tác dụng khi hệ thống vận hành: giữ cho luồng nghiệp vụ thuộc `flutter_frontend` chạy ổn định trong runtime.

import 'package:flutter/material.dart';
import 'package:flutter_facebook_auth/flutter_facebook_auth.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_quill/flutter_quill.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'core/app_locale.dart';
import 'core/router.dart';
import 'core/theme.dart';
import 'l10n/app_strings.dart';

// Mục đích: Hàm `main` triển khai phần việc `main` trong flutter_frontend/lib/main.dart.
// Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
// Vai trò trong hệ thống: Đây là hàm thuộc một thành phần của hệ thống.
// Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  final prefs = await SharedPreferences.getInstance();

  await FacebookAuth.i.webAndDesktopInitialize(
    appId: '3613798808941390',
    cookie: true,
    xfbml: true,
    version: 'v19.0',
  );

  runApp(
    ProviderScope(
      overrides: [
        sharedPreferencesProvider.overrideWithValue(prefs),
        initialLocaleProvider.overrideWithValue(resolveInitialLocale(prefs)),
      ],
      child: const MyApp(),
    ),
  );
}

// Mục đích: Lớp `MyApp` triển khai phần việc `My App` trong flutter_frontend/lib/main.dart.
// Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
// Vai trò trong hệ thống: Đây là lớp thuộc một thành phần của hệ thống.
// Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

class MyApp extends ConsumerWidget {
  const MyApp({super.key});

  @override
  // Mục đích: Phương thức `build` triển khai phần việc `build` trong flutter_frontend/lib/main.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc một thành phần của hệ thống.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  Widget build(BuildContext context, WidgetRef ref) {
    // Lắng nghe provider để widget tự động dựng lại khi dữ liệu hoặc trạng thái thay đổi.

    final router = ref.watch(routerProvider);
    // Lắng nghe provider để widget tự động dựng lại khi dữ liệu hoặc trạng thái thay đổi.

    final locale = ref.watch(appLocaleProvider);

    // Khởi tạo khung ứng dụng theo kiểu router để toàn bộ điều hướng dùng chung một điểm vào.

    return MaterialApp.router(
      title: 'AI Document Manager',
      theme: AppTheme.light,
      routerConfig: router,
      locale: locale,
      debugShowCheckedModeBanner: false,
      localizationsDelegates: const [
        AppStrings.delegate,
        FlutterQuillLocalizations.delegate,
        GlobalMaterialLocalizations.delegate,
        GlobalWidgetsLocalizations.delegate,
        GlobalCupertinoLocalizations.delegate,
      ],
      supportedLocales: AppStrings.supportedLocales,
    );
  }
}
