// Tệp này dùng để: điều phối state, gọi API và đồng bộ dữ liệu màn hình trong flutter_frontend/lib/providers/documents_provider.dart.
// Cách hoạt động: theo dõi trạng thái, gọi backend khi cần và phát dữ liệu mới xuống widget tree.
// Vai trò trong hệ thống: Đây là lớp state management của Flutter.
// Tác dụng khi hệ thống vận hành: giữ giao diện và dữ liệu runtime đồng bộ theo từng phiên làm việc.

import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../core/api_client.dart';
import '../models/document.dart';
import '../models/document_version.dart';

// Mục đích: Provider `documentRefreshTickProvider` triển khai phần việc `document Refresh Tick Provider` trong flutter_frontend/lib/providers/documents_provider.dart.
// Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
// Vai trò trong hệ thống: Đây là provider thuộc lớp state management của Flutter.
// Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

final documentRefreshTickProvider =
    NotifierProvider<DocumentRefreshTickNotifier, int>(
  DocumentRefreshTickNotifier.new,
);

// Mục đích: Lớp `DocumentRefreshTickNotifier` triển khai phần việc `Document Refresh Tick Notifier` trong flutter_frontend/lib/providers/documents_provider.dart.
// Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
// Vai trò trong hệ thống: Đây là lớp thuộc lớp state management của Flutter.
// Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

class DocumentRefreshTickNotifier extends Notifier<int> {
  @override
  // Mục đích: Phương thức `build` triển khai phần việc `build` trong flutter_frontend/lib/providers/documents_provider.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc lớp state management của Flutter.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  int build() => 0;

  // Mục đích: Phương thức `bump` triển khai phần việc `bump` trong flutter_frontend/lib/providers/documents_provider.dart.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là phương thức thuộc lớp state management của Flutter.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  void bump() => state++;
}

// Mục đích: Hàm `refreshDocumentCollections` triển khai phần việc `refresh Document Collections` trong flutter_frontend/lib/providers/documents_provider.dart.
// Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
// Vai trò trong hệ thống: Đây là hàm thuộc lớp state management của Flutter.
// Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

void refreshDocumentCollections(WidgetRef ref) {
  // Đọc provider theo nhu cầu hành động mà không buộc widget đăng ký rebuild liên tục.

  ref.read(documentRefreshTickProvider.notifier).bump();
}

// Mục đích: Provider `documentsProvider` triển khai phần việc `documents Provider` trong flutter_frontend/lib/providers/documents_provider.dart.
// Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
// Vai trò trong hệ thống: Đây là provider thuộc lớp state management của Flutter.
// Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

final documentsProvider = FutureProvider.autoDispose.family<List<Document>, String>((ref, group) async {
  // Lắng nghe provider để widget tự động dựng lại khi dữ liệu hoặc trạng thái thay đổi.

  ref.watch(documentRefreshTickProvider);
  // Gọi API hoặc tác vụ bất đồng bộ rồi chờ kết quả trước khi cập nhật giao diện.

  final resp = await ApiClient().dio.get('documents/', queryParameters: {'group': group});
  return (resp.data as List).map((e) => Document.fromJson(e)).toList();
});

// Mục đích: Lớp `DocumentCollectionParams` triển khai phần việc `Document Collection Params` trong flutter_frontend/lib/providers/documents_provider.dart.
// Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
// Vai trò trong hệ thống: Đây là lớp thuộc lớp state management của Flutter.
// Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

class DocumentCollectionParams {
  final String group;
  final String q;
  final bool admin;
  final String ownerId;
  final String groupId;

  const DocumentCollectionParams({
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
    return other is DocumentCollectionParams &&
        other.group == group &&
        other.q == q &&
        other.admin == admin &&
        other.ownerId == ownerId &&
        other.groupId == groupId;
  }

  @override
  int get hashCode => Object.hash(group, q, admin, ownerId, groupId);
}

// Mục đích: Provider `documentCollectionProvider` triển khai phần việc `document Collection Provider` trong flutter_frontend/lib/providers/documents_provider.dart.
// Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
// Vai trò trong hệ thống: Đây là provider thuộc lớp state management của Flutter.
// Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

final documentCollectionProvider =
    FutureProvider.autoDispose.family<List<Document>, DocumentCollectionParams>((ref, params) async {
  // Lắng nghe provider để widget tự động dựng lại khi dữ liệu hoặc trạng thái thay đổi.

  ref.watch(documentRefreshTickProvider);
  // Gọi API hoặc tác vụ bất đồng bộ rồi chờ kết quả trước khi cập nhật giao diện.

  final resp = await ApiClient().dio.get('documents/', queryParameters: params.toQueryParameters());
  return (resp.data as List).map((e) => Document.fromJson(e)).toList();
});

// Mục đích: Lớp `AdminDocParams` triển khai phần việc `Admin Doc Params` trong flutter_frontend/lib/providers/documents_provider.dart.
// Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
// Vai trò trong hệ thống: Đây là lớp thuộc lớp state management của Flutter.
// Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

class AdminDocParams {
  final String ownerId;
  final String groupId;
  const AdminDocParams({this.ownerId = '', this.groupId = ''});
  @override bool operator ==(Object o) => o is AdminDocParams && o.ownerId == ownerId && o.groupId == groupId;
  @override int get hashCode => Object.hash(ownerId, groupId);
}

// Mục đích: Provider `adminDocumentsProvider` triển khai phần việc `admin Documents Provider` trong flutter_frontend/lib/providers/documents_provider.dart.
// Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
// Vai trò trong hệ thống: Đây là provider thuộc lớp state management của Flutter.
// Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

final adminDocumentsProvider = FutureProvider.autoDispose.family<List<Document>, AdminDocParams>((ref, params) async {
  // Lắng nghe provider để widget tự động dựng lại khi dữ liệu hoặc trạng thái thay đổi.

  ref.watch(documentRefreshTickProvider);
  final qp = <String, dynamic>{'admin': '1'};
  if (params.ownerId.isNotEmpty) qp['owner_id'] = params.ownerId;
  if (params.groupId.isNotEmpty) qp['group_id'] = params.groupId;
  // Gọi API hoặc tác vụ bất đồng bộ rồi chờ kết quả trước khi cập nhật giao diện.

  final resp = await ApiClient().dio.get('documents/', queryParameters: qp);
  return (resp.data as List).map((e) => Document.fromJson(e)).toList();
});

// Mục đích: Provider `documentDetailProvider` triển khai phần việc `document Detail Provider` trong flutter_frontend/lib/providers/documents_provider.dart.
// Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
// Vai trò trong hệ thống: Đây là provider thuộc lớp state management của Flutter.
// Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

final documentDetailProvider = FutureProvider.autoDispose.family<Document, int>((ref, id) async {
  // Lắng nghe provider để widget tự động dựng lại khi dữ liệu hoặc trạng thái thay đổi.

  ref.watch(documentRefreshTickProvider);
  // Gọi API hoặc tác vụ bất đồng bộ rồi chờ kết quả trước khi cập nhật giao diện.

  final resp = await ApiClient().dio.get('documents/$id/');
  return Document.fromJson(resp.data);
});

// Mục đích: Provider `documentVersionsProvider` triển khai phần việc `document Versions Provider` trong flutter_frontend/lib/providers/documents_provider.dart.
// Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
// Vai trò trong hệ thống: Đây là provider thuộc lớp state management của Flutter.
// Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

final documentVersionsProvider = FutureProvider.autoDispose.family<List<DocumentVersion>, int>((ref, docId) async {
  // Lắng nghe provider để widget tự động dựng lại khi dữ liệu hoặc trạng thái thay đổi.

  ref.watch(documentRefreshTickProvider);
  // Gọi API hoặc tác vụ bất đồng bộ rồi chờ kết quả trước khi cập nhật giao diện.

  final resp = await ApiClient().dio.get('documents/$docId/versions/');
  return (resp.data as List).map((e) => DocumentVersion.fromJson(e)).toList();
});
