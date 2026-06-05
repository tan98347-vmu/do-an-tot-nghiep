import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../core/api_client.dart';
import '../models/notification_item.dart';

final notificationsProvider =
    FutureProvider.autoDispose<List<AggregateNotificationItem>>((ref) async {
  final resp = await ApiClient().dio.get(
    'notifications/aggregate/',
    queryParameters: {'limit': 30},
  );
  return (resp.data as List)
      .map(
        (item) => AggregateNotificationItem.fromJson(
          Map<String, dynamic>.from(item as Map),
        ),
      )
      .toList();
});

final unreadNotificationCountProvider =
    FutureProvider.autoDispose<int>((ref) async {
  final resp = await ApiClient().dio.get(
    'notifications/aggregate/unread-count/',
  );
  return resp.data['count'] ?? 0;
});

Future<void> markAggregateNotificationRead(
  String sourceType,
  String sourceId,
) async {
  await ApiClient().dio.post(
    'notifications/aggregate/read/',
    data: {
      'source_type': sourceType,
      'source_id': sourceId,
    },
  );
}

/// Danh dau da doc tat ca thong bao tong hop. Tra ve so muc da cap nhat.
Future<int> markAllAggregateNotificationsRead() async {
  final resp = await ApiClient().dio.post('notifications/aggregate/read-all/');
  final data = resp.data;
  if (data is Map && data['updated'] is int) {
    return data['updated'] as int;
  }
  return 0;
}
