// Tệp này dùng để: điều phối state, gọi API và đồng bộ dữ liệu màn hình trong flutter_frontend/lib/providers/dashboard_provider.dart.
// Cách hoạt động: theo dõi trạng thái, gọi backend khi cần và phát dữ liệu mới xuống widget tree.
// Vai trò trong hệ thống: Đây là lớp state management của Flutter.
// Tác dụng khi hệ thống vận hành: giữ giao diện và dữ liệu runtime đồng bộ theo từng phiên làm việc.

import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../core/api_client.dart';
import '../models/dashboard_stats.dart';

// Mục đích: Provider `dashboardStatsProvider` triển khai phần việc `dashboard Stats Provider` trong flutter_frontend/lib/providers/dashboard_provider.dart.
// Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
// Vai trò trong hệ thống: Đây là provider thuộc lớp state management của Flutter.
// Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

final dashboardStatsProvider = FutureProvider<DashboardStats>((ref) async {
  // Gọi API hoặc tác vụ bất đồng bộ rồi chờ kết quả trước khi cập nhật giao diện.

  final resp = await ApiClient().dio.get('dashboard/stats/');
  return DashboardStats.fromJson(resp.data);
});

// Mục đích: Provider `orgNodeStatsProvider` triển khai phần việc `org Node Stats Provider` trong flutter_frontend/lib/providers/dashboard_provider.dart.
// Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
// Vai trò trong hệ thống: Đây là provider thuộc lớp state management của Flutter.
// Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

final orgNodeStatsProvider = FutureProvider.family<OrgNodeStats, int>((ref, userId) async {
  // Gọi API hoặc tác vụ bất đồng bộ rồi chờ kết quả trước khi cập nhật giao diện.

  final resp = await ApiClient().dio.get('dashboard/org-node-stats/$userId/');
  return OrgNodeStats.fromJson(Map<String, dynamic>.from(resp.data as Map));
});
