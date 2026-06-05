// Tệp này dùng để: định nghĩa hạ tầng client như router, API client, theme hoặc locale trong flutter_frontend/lib/core/app_locale.dart.
// Cách hoạt động: được nạp sớm khi app Flutter khởi động để các màn và provider dùng chung cấu hình nền.
// Vai trò trong hệ thống: Đây là lớp lõi Flutter Web.
// Tác dụng khi hệ thống vận hành: quyết định cách frontend khởi chạy, điều hướng và gọi API.

import 'dart:ui';

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';

const _localeStorageKey = 'app_locale';

// Mục đích: Provider `sharedPreferencesProvider` triển khai phần việc `shared Preferences Provider` trong flutter_frontend/lib/core/app_locale.dart.
// Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
// Vai trò trong hệ thống: Đây là provider thuộc lớp lõi Flutter Web.
// Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

final sharedPreferencesProvider = Provider<SharedPreferences>((ref) {
  throw UnimplementedError('sharedPreferencesProvider must be overridden in main().');
});

// Mục đích: Provider `initialLocaleProvider` triển khai phần việc `initial Locale Provider` trong flutter_frontend/lib/core/app_locale.dart.
// Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
// Vai trò trong hệ thống: Đây là provider thuộc lớp lõi Flutter Web.
// Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

final initialLocaleProvider = Provider<Locale>((ref) => const Locale('vi'));

// Mục đích: Lớp `AppLocaleNotifier` triển khai phần việc `App Locale Notifier` trong flutter_frontend/lib/core/app_locale.dart.
// Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
// Vai trò trong hệ thống: Đây là lớp thuộc lớp lõi Flutter Web.
// Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

class AppLocaleNotifier extends Notifier<Locale> {
  // Lắng nghe provider để widget tự động dựng lại khi dữ liệu hoặc trạng thái thay đổi.

  SharedPreferences get _prefs => ref.watch(sharedPreferencesProvider);

  @override
  // Mục đích: Phương thức `build` triển khai phần việc `build` trong flutter_frontend/lib/core/app_locale.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc lớp lõi Flutter Web.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  // Lắng nghe provider để widget tự động dựng lại khi dữ liệu hoặc trạng thái thay đổi.

  Locale build() => ref.watch(initialLocaleProvider);

  // Mục đích: Phương thức `setLanguageCode` triển khai phần việc `set Language Code` trong flutter_frontend/lib/core/app_locale.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc lớp lõi Flutter Web.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  void setLanguageCode(String languageCode) {
    final normalized = languageCode.toLowerCase() == 'en' ? 'en' : 'vi';
    state = Locale(normalized);
    _prefs.setString(_localeStorageKey, normalized);
  }

  // Mục đích: Phương thức `toggle` triển khai phần việc `toggle` trong flutter_frontend/lib/core/app_locale.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc lớp lõi Flutter Web.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  void toggle() {
    setLanguageCode(state.languageCode == 'en' ? 'vi' : 'en');
  }
}

// Mục đích: Provider `appLocaleProvider` triển khai phần việc `app Locale Provider` trong flutter_frontend/lib/core/app_locale.dart.
// Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
// Vai trò trong hệ thống: Đây là provider thuộc lớp lõi Flutter Web.
// Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

final appLocaleProvider = NotifierProvider<AppLocaleNotifier, Locale>(
  AppLocaleNotifier.new,
);

// Mục đích: Hàm `resolveInitialLocale` triển khai phần việc `resolve Initial Locale` trong flutter_frontend/lib/core/app_locale.dart.
// Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
// Vai trò trong hệ thống: Đây là hàm thuộc lớp lõi Flutter Web.
// Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

Locale resolveInitialLocale(SharedPreferences prefs) {
  final saved = (prefs.getString(_localeStorageKey) ?? 'vi').trim().toLowerCase();
  return Locale(saved == 'en' ? 'en' : 'vi');
}
