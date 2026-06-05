class AggregateNotificationItem {
  final String sourceType;
  final String sourceId;
  final String category;
  final String title;
  final String summary;
  final String status;
  final bool isRead;
  final bool supportsRead;
  final bool countsAsUnread;
  final bool isActionable;
  final String createdAt;
  final String updatedAt;
  final String deeplink;
  final String actionLabel;
  final String reason;
  final String actorName;

  const AggregateNotificationItem({
    required this.sourceType,
    required this.sourceId,
    required this.category,
    required this.title,
    required this.summary,
    required this.status,
    required this.isRead,
    required this.supportsRead,
    required this.countsAsUnread,
    required this.isActionable,
    required this.createdAt,
    required this.updatedAt,
    required this.deeplink,
    required this.actionLabel,
    this.reason = '',
    this.actorName = '',
  });

  factory AggregateNotificationItem.fromJson(Map<String, dynamic> json) {
    return AggregateNotificationItem(
      sourceType: (json['source_type'] ?? '') as String,
      sourceId: (json['source_id'] ?? '') as String,
      category: (json['category'] ?? '') as String,
      title: (json['title'] ?? '') as String,
      summary: (json['summary'] ?? '') as String,
      status: (json['status'] ?? '') as String,
      isRead: json['is_read'] == true,
      supportsRead: json['supports_read'] == true,
      countsAsUnread: json['counts_as_unread'] == true,
      isActionable: json['is_actionable'] == true,
      createdAt: (json['created_at'] ?? '') as String,
      updatedAt: (json['updated_at'] ?? '') as String,
      deeplink: (json['deeplink'] ?? '/dashboard') as String,
      actionLabel: (json['action_label'] ?? 'Mo') as String,
      reason: (json['reason'] ?? '') as String,
      actorName: (json['actor_name'] ?? '') as String,
    );
  }

  String get displayTime {
    final raw = updatedAt.isNotEmpty ? updatedAt : createdAt;
    if (raw.length < 16) {
      return raw.replaceFirst('T', ' ');
    }
    return raw.replaceFirst('T', ' ').substring(0, 16);
  }

  bool get highlight => countsAsUnread || isActionable;
}
