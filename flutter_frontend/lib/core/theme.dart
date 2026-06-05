// Tệp này dùng để: định nghĩa hạ tầng client như router, API client, theme hoặc locale trong flutter_frontend/lib/core/theme.dart.
// Cách hoạt động: được nạp sớm khi app Flutter khởi động để các màn và provider dùng chung cấu hình nền.
// Vai trò trong hệ thống: Đây là lớp lõi Flutter Web.
// Tác dụng khi hệ thống vận hành: quyết định cách frontend khởi chạy, điều hướng và gọi API.

import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

// Mục đích: Lớp `AppTheme` triển khai phần việc `App Theme` trong flutter_frontend/lib/core/theme.dart.
// Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
// Vai trò trong hệ thống: Đây là lớp thuộc lớp lõi Flutter Web.
// Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

class AppTheme {
  static final light = ThemeData(
    useMaterial3: true,
    colorScheme: ColorScheme.fromSeed(
      seedColor: const Color(0xFF1565C0),
      brightness: Brightness.light,
    ),
    textTheme: GoogleFonts.robotoTextTheme(),
    appBarTheme: const AppBarTheme(
      elevation: 0,
      centerTitle: false,
    ),
    cardTheme: CardThemeData(
      elevation: 2,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
    ),
    inputDecorationTheme: InputDecorationTheme(
      border: OutlineInputBorder(borderRadius: BorderRadius.circular(8)),
      filled: true,
    ),
    filledButtonTheme: FilledButtonThemeData(
      style: FilledButton.styleFrom(
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
        padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 12),
      ),
    ),
  );
}
