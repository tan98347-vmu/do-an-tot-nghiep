import 'dart:async';

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../core/api_client.dart';
import 'auth_provider.dart';

const String kNotifShareApprovals = 'share_approvals';
const String kNotifSigningTasks = 'signing_tasks';
const String kNotifSigningProposals = 'signing_proposals';
const String kNotifMailbox = 'mailbox';

const List<String> kNotifCategories = [
  kNotifShareApprovals,
  kNotifSigningTasks,
  kNotifSigningProposals,
  kNotifMailbox,
];

String notifCategoryLabel(String key) => switch (key) {
      kNotifShareApprovals => 'Chia se cho duyet',
      kNotifSigningTasks => 'Yeu cau ky',
      kNotifSigningProposals => 'De xuat ky',
      kNotifMailbox => 'Hom thu ky so',
      _ => key,
    };

String notifCategoryRoute(String key) => switch (key) {
      kNotifShareApprovals => '/sharing/pending',
      kNotifSigningTasks => '/signing/tasks',
      kNotifSigningProposals => '/signing/proposals/review',
      kNotifMailbox => '/mailbox',
      _ => '/',
    };

String? notifCategoryForRoute(String route) {
  if (route.startsWith('/sharing/pending')) return kNotifShareApprovals;
  if (route.startsWith('/signing/tasks')) return kNotifSigningTasks;
  if (route.startsWith('/signing/proposals/review')) {
    return kNotifSigningProposals;
  }
  if (route.startsWith('/mailbox')) return kNotifMailbox;
  return null;
}

String? notifCategoryForSourceType(String sourceType) => switch (sourceType) {
      'share_approval' => kNotifShareApprovals,
      'signing_task' => kNotifSigningTasks,
      'signing_proposal_pending' => kNotifSigningProposals,
      'mailbox_pending' => kNotifMailbox,
      _ => null,
    };

class NotificationQueueSnapshot {
  final Map<String, Set<String>> ids;
  final Map<String, String> signatures;

  const NotificationQueueSnapshot({
    required this.ids,
    required this.signatures,
  });

  factory NotificationQueueSnapshot.fromPayload(List<dynamic> payload) {
    final ids = {
      for (final category in kNotifCategories) category: <String>[],
    };
    for (final raw in payload) {
      final item = Map<String, dynamic>.from(raw as Map);
      final category =
          notifCategoryForSourceType((item['source_type'] ?? '').toString());
      if (category == null) continue;
      ids[category]!.add(
        '${item['source_type']}:${item['source_id']}',
      );
    }

    final signatures = <String, String>{};
    for (final category in kNotifCategories) {
      final categoryIds = ids[category]!..sort();
      signatures[category] = categoryIds.join('|');
    }
    return NotificationQueueSnapshot(
      ids: {
        for (final category in kNotifCategories)
          category: ids[category]!.toSet(),
      },
      signatures: signatures,
    );
  }
}

final notificationQueueSnapshotProvider =
    StreamProvider.autoDispose<NotificationQueueSnapshot>((ref) {
  final controller = StreamController<NotificationQueueSnapshot>();
  const refreshInterval = Duration(seconds: 5);

  Timer? timer;
  var disposed = false;
  var inFlight = false;
  NotificationQueueSnapshot? latest;

  Future<void> refresh() async {
    if (disposed || inFlight) return;
    inFlight = true;
    try {
      final response = await ApiClient().dio.get(
        'notifications/aggregate/',
        queryParameters: const {
          'actionable_only': true,
          'limit': 100,
        },
      );
      latest = NotificationQueueSnapshot.fromPayload(
        response.data as List<dynamic>,
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

class NotificationQueueAckNotifier extends Notifier<Map<String, String>> {
  static const _prefix = 'notification_queue_ack';
  String _userScope = 'anonymous';

  @override
  Map<String, String> build() {
    final scope = ref.watch(
      currentUserProvider.select(
        (user) => user == null
            ? null
            : '${user.id}_${user.company?.id ?? 0}',
      ),
    );
    _userScope = scope ?? 'anonymous';
    _load(_userScope);
    return const {};
  }

  Future<void> _load(String scope) async {
    final preferences = await SharedPreferences.getInstance();
    if (scope != _userScope) return;
    final loaded = {
      for (final category in kNotifCategories)
        category:
            preferences.getString('${_prefix}_${scope}_$category') ?? '',
    };
    state = {...loaded, ...state};
  }

  Future<void> markRead(String category, String signature) async {
    state = {...state, category: signature};
    final scope = _userScope;
    final preferences = await SharedPreferences.getInstance();
    await preferences.setString(
      '${_prefix}_${scope}_$category',
      signature,
    );
  }

  Future<void> markAllRead(NotificationQueueSnapshot snapshot) async {
    state = {...state, ...snapshot.signatures};
    final scope = _userScope;
    final preferences = await SharedPreferences.getInstance();
    for (final category in kNotifCategories) {
      await preferences.setString(
        '${_prefix}_${scope}_$category',
        snapshot.signatures[category] ?? '',
      );
    }
  }
}

final notificationQueueAckProvider =
    NotifierProvider<NotificationQueueAckNotifier, Map<String, String>>(
  NotificationQueueAckNotifier.new,
);

final notificationUnreadByCategoryProvider =
    Provider<Map<String, int>>((ref) {
  final snapshot = ref.watch(notificationQueueSnapshotProvider).asData?.value;
  if (snapshot == null) {
    return {for (final category in kNotifCategories) category: 0};
  }
  final acknowledged = ref.watch(notificationQueueAckProvider);
  return {
    for (final category in kNotifCategories) category: () {
      final acknowledgedIds = (acknowledged[category] ?? '')
          .split('|')
          .where((id) => id.isNotEmpty)
          .toSet();
      return snapshot.ids[category]!.difference(acknowledgedIds).length;
    }(),
  };
});

final notificationTotalUnreadProvider = Provider<int>((ref) {
  final unread = ref.watch(notificationUnreadByCategoryProvider);
  return unread.values.fold<int>(0, (sum, value) => sum + value);
});
