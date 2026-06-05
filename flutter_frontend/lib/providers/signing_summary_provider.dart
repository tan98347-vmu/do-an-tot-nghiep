// Tệp này dùng để: điều phối state, gọi API và đồng bộ dữ liệu màn hình trong flutter_frontend/lib/providers/signing_summary_provider.dart.
// Cách hoạt động: theo dõi trạng thái, gọi backend khi cần và phát dữ liệu mới xuống widget tree.
// Vai trò trong hệ thống: Đây là lớp state management của Flutter.
// Tác dụng khi hệ thống vận hành: giữ giao diện và dữ liệu runtime đồng bộ theo từng phiên làm việc.

import 'dart:async';

import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../core/api_client.dart';
import '../models/signing.dart';

// Mục đích: Provider `signingSummaryProvider` triển khai phần việc `signing Summary Provider` trong flutter_frontend/lib/providers/signing_summary_provider.dart.
// Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
// Vai trò trong hệ thống: Đây là provider thuộc lớp state management của Flutter.
// Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

final signingSummaryProvider =
    StreamProvider.autoDispose<SigningSummary>((ref) {
  final controller = StreamController<SigningSummary>();
  const refreshInterval = Duration(seconds: 5);

  Timer? timer;
  var disposed = false;
  var inFlight = false;
  SigningSummary? latest;

  // Mục đích: Phương thức `refresh` triển khai phần việc `refresh` trong flutter_frontend/lib/providers/signing_summary_provider.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc lớp state management của Flutter.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  Future<void> refresh() async {
    if (disposed || inFlight) return;
    inFlight = true;
    try {
      // Gọi API hoặc tác vụ bất đồng bộ rồi chờ kết quả trước khi cập nhật giao diện.

      final resp = await ApiClient().dio.get('signing/summary/');
      latest = SigningSummary.fromJson(
        Map<String, dynamic>.from(resp.data as Map),
      );
      if (!disposed) controller.add(latest!);
    } catch (error, stackTrace) {
      if (disposed) return;
      if (latest != null) {
        controller.add(latest!);
      } else {
        controller.addError(error, stackTrace);
      }
    } finally {
      inFlight = false;
    }
  }

  Future.microtask(refresh);
  timer = Timer.periodic(refreshInterval, (_) => refresh());

  ref.onDispose(() {
    disposed = true;
    timer?.cancel();
    controller.close();
  });

  return controller.stream;
});
