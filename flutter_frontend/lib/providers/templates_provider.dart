// Tệp này dùng để: điều phối state, gọi API và đồng bộ dữ liệu màn hình trong flutter_frontend/lib/providers/templates_provider.dart.
// Cách hoạt động: theo dõi trạng thái, gọi backend khi cần và phát dữ liệu mới xuống widget tree.
// Vai trò trong hệ thống: Đây là lớp state management của Flutter.
// Tác dụng khi hệ thống vận hành: giữ giao diện và dữ liệu runtime đồng bộ theo từng phiên làm việc.

import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../core/api_client.dart';
import '../models/template.dart';

// Mục đích: Provider `templatesProvider` triển khai phần việc `templates Provider` trong flutter_frontend/lib/providers/templates_provider.dart.
// Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
// Vai trò trong hệ thống: Đây là provider thuộc lớp state management của Flutter.
// Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

final templatesProvider = FutureProvider.family<List<DocumentTemplate>, String>((ref, group) async {
  // Gọi API hoặc tác vụ bất đồng bộ rồi chờ kết quả trước khi cập nhật giao diện.

  final resp = await ApiClient().dio.get('templates/', queryParameters: {'group': group});
  return (resp.data as List).map((e) => DocumentTemplate.fromJson(e)).toList();
});

// Mục đích: Lớp `TemplateCollectionParams` triển khai phần việc `Template Collection Params` trong flutter_frontend/lib/providers/templates_provider.dart.
// Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
// Vai trò trong hệ thống: Đây là lớp thuộc lớp state management của Flutter.
// Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

class TemplateCollectionParams {
  final String group;
  final String q;
  final bool admin;
  final String ownerId;
  final String groupId;

  const TemplateCollectionParams({
    this.group = '',
    this.q = '',
    this.admin = false,
    this.ownerId = '',
    this.groupId = '',
  });

  Map<String, dynamic> toQueryParameters() {
    final params = <String, dynamic>{};
    if (group.isNotEmpty) params['group'] = group;
    if (q.isNotEmpty) params['q'] = q;
    if (admin) params['admin'] = '1';
    if (ownerId.isNotEmpty) params['owner_id'] = ownerId;
    if (groupId.isNotEmpty) params['group_id'] = groupId;
    return params;
  }

  @override
  bool operator ==(Object other) {
    return other is TemplateCollectionParams &&
        other.group == group &&
        other.q == q &&
        other.admin == admin &&
        other.ownerId == ownerId &&
        other.groupId == groupId;
  }

  @override
  int get hashCode => Object.hash(group, q, admin, ownerId, groupId);
}

// Mục đích: Provider `templateCollectionProvider` triển khai phần việc `template Collection Provider` trong flutter_frontend/lib/providers/templates_provider.dart.
// Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
// Vai trò trong hệ thống: Đây là provider thuộc lớp state management của Flutter.
// Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

final templateCollectionProvider =
    FutureProvider.autoDispose.family<List<DocumentTemplate>, TemplateCollectionParams>((ref, params) async {
  // Gọi API hoặc tác vụ bất đồng bộ rồi chờ kết quả trước khi cập nhật giao diện.

  final resp = await ApiClient().dio.get('templates/', queryParameters: params.toQueryParameters());
  return (resp.data as List).map((e) => DocumentTemplate.fromJson(e)).toList();
});

// Admin provider: superuser chỉ định owner_id/group_id để lọc
// Mục đích: Lớp `AdminTemplateParams` triển khai phần việc `Admin Template Params` trong flutter_frontend/lib/providers/templates_provider.dart.
// Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
// Vai trò trong hệ thống: Đây là lớp thuộc lớp state management của Flutter.
// Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

class AdminTemplateParams {
  final String ownerId;
  final String groupId;
  const AdminTemplateParams({this.ownerId = '', this.groupId = ''});
  @override bool operator ==(Object o) => o is AdminTemplateParams && o.ownerId == ownerId && o.groupId == groupId;
  @override int get hashCode => Object.hash(ownerId, groupId);
}

// Mục đích: Provider `adminTemplatesProvider` triển khai phần việc `admin Templates Provider` trong flutter_frontend/lib/providers/templates_provider.dart.
// Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
// Vai trò trong hệ thống: Đây là provider thuộc lớp state management của Flutter.
// Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

final adminTemplatesProvider = FutureProvider.family<List<DocumentTemplate>, AdminTemplateParams>((ref, params) async {
  final qp = <String, dynamic>{'admin': '1'};
  if (params.ownerId.isNotEmpty) qp['owner_id'] = params.ownerId;
  if (params.groupId.isNotEmpty) qp['group_id'] = params.groupId;
  // Gọi API hoặc tác vụ bất đồng bộ rồi chờ kết quả trước khi cập nhật giao diện.

  final resp = await ApiClient().dio.get('templates/', queryParameters: qp);
  return (resp.data as List).map((e) => DocumentTemplate.fromJson(e)).toList();
});

// Mục đích: Provider `templateDetailProvider` triển khai phần việc `template Detail Provider` trong flutter_frontend/lib/providers/templates_provider.dart.
// Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
// Vai trò trong hệ thống: Đây là provider thuộc lớp state management của Flutter.
// Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

final templateDetailProvider = FutureProvider.family<DocumentTemplate, int>((ref, id) async {
  // Gọi API hoặc tác vụ bất đồng bộ rồi chờ kết quả trước khi cập nhật giao diện.

  final resp = await ApiClient().dio.get('templates/$id/');
  return DocumentTemplate.fromJson(resp.data);
});

// Mục đích: Lớp `TemplateVersion` triển khai phần việc `Template Version` trong flutter_frontend/lib/providers/templates_provider.dart.
// Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
// Vai trò trong hệ thống: Đây là lớp thuộc lớp state management của Flutter.
// Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

class TemplateVersion {
  final int id;
  final String versionNumber;
  final String? content;
  final String? changeNote;
  final String? createdByName;
  final String createdAt;
  final bool isHidden;

  const TemplateVersion({
    required this.id,
    required this.versionNumber,
    this.content,
    this.changeNote,
    this.createdByName,
    required this.createdAt,
    this.isHidden = false,
  });

  factory TemplateVersion.fromJson(Map<String, dynamic> json) => TemplateVersion(
    id: json['id'],
    versionNumber: json['version_number'] ?? '',
    content: json['content'],
    changeNote: json['change_note'],
    createdByName: json['created_by_name'],
    createdAt: json['created_at'] ?? '',
    isHidden: json['is_hidden'] ?? false,
  );
}

// Provider lấy tất cả versions (kể cả ẩn) — dùng cho owner/staff
// Mục đích: Provider `templateVersionsAllProvider` triển khai phần việc `template Versions All Provider` trong flutter_frontend/lib/providers/templates_provider.dart.
// Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
// Vai trò trong hệ thống: Đây là provider thuộc lớp state management của Flutter.
// Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

final templateVersionsAllProvider = FutureProvider.family<List<TemplateVersion>, int>((ref, templateId) async {
  // Gọi API hoặc tác vụ bất đồng bộ rồi chờ kết quả trước khi cập nhật giao diện.

  final resp = await ApiClient().dio.get('templates/$templateId/versions/', queryParameters: {'all': '1'});
  return (resp.data as List).map((e) => TemplateVersion.fromJson(e)).toList();
});

// Provider mặc định (chỉ hiện versions không ẩn)
// Mục đích: Provider `templateVersionsProvider` triển khai phần việc `template Versions Provider` trong flutter_frontend/lib/providers/templates_provider.dart.
// Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
// Vai trò trong hệ thống: Đây là provider thuộc lớp state management của Flutter.
// Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

final templateVersionsProvider = FutureProvider.family<List<TemplateVersion>, int>((ref, templateId) async {
  // Gọi API hoặc tác vụ bất đồng bộ rồi chờ kết quả trước khi cập nhật giao diện.

  final resp = await ApiClient().dio.get('templates/$templateId/versions/');
  return (resp.data as List).map((e) => TemplateVersion.fromJson(e)).toList();
});
