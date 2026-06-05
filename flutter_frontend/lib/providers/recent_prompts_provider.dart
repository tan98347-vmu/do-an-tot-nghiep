import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../core/api_client.dart';

class RecentPromptItem {
  final int id;
  final String title;
  final String rulesContentPreview;
  final String rulesContent;
  final String tags;
  final String? categoryName;
  final String? lastUsed;
  final String? createdAt;
  final int usageCount;
  final double? safetyScore;
  final String visibility;
  final String ownerName;
  final int? ownerId;
  final bool isMine;
  final int? lastUsedDocId;
  final String? lastUsedDocTitle;
  final String? lastUsedByName;

  RecentPromptItem({
    required this.id,
    required this.title,
    required this.rulesContentPreview,
    required this.rulesContent,
    required this.tags,
    required this.categoryName,
    required this.lastUsed,
    required this.createdAt,
    required this.usageCount,
    required this.safetyScore,
    required this.visibility,
    required this.ownerName,
    required this.ownerId,
    required this.isMine,
    required this.lastUsedDocId,
    required this.lastUsedDocTitle,
    required this.lastUsedByName,
  });

  factory RecentPromptItem.fromJson(Map<String, dynamic> json) {
    return RecentPromptItem(
      id: json['id'] as int,
      title: (json['title'] ?? '') as String,
      rulesContentPreview: (json['rules_content_preview'] ?? '') as String,
      rulesContent: (json['rules_content'] ?? '') as String,
      tags: (json['tags'] ?? '') as String,
      categoryName: json['category_name'] as String?,
      lastUsed: json['last_used'] as String?,
      createdAt: json['created_at'] as String?,
      usageCount: (json['usage_count'] ?? 0) as int,
      safetyScore: (json['safety_score'] as num?)?.toDouble(),
      visibility: (json['visibility'] ?? 'private') as String,
      ownerName: (json['owner_name'] ?? '') as String,
      ownerId: json['owner_id'] as int?,
      isMine: json['is_mine'] == true,
      lastUsedDocId: json['last_used_doc_id'] as int?,
      lastUsedDocTitle: json['last_used_doc_title'] as String?,
      lastUsedByName: json['last_used_by_name'] as String?,
    );
  }

  List<String> get tagList =>
      tags.split(',').map((t) => t.trim()).where((t) => t.isNotEmpty).toList();

  String matchHaystack() =>
      '$title $rulesContentPreview $ownerName ${lastUsedDocTitle ?? ''} ${lastUsedByName ?? ''} $tags ${categoryName ?? ''}'
          .toLowerCase();
}

final recentPromptsProvider = FutureProvider<List<RecentPromptItem>>((ref) async {
  final resp = await ApiClient().dio.get('prompts/recent-used/');
  return (resp.data as List)
      .map((e) => RecentPromptItem.fromJson(e as Map<String, dynamic>))
      .toList();
});
