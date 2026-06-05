enum SearchResultType {
  template,
  document,
  prompt,
  summary,
  conversation,
}

class GlobalSearchItem {
  final int id;
  final SearchResultType type;
  final String title;
  final String snippet;
  final String deeplink;
  final DateTime updatedAt;

  const GlobalSearchItem({
    required this.id,
    required this.type,
    required this.title,
    required this.snippet,
    required this.deeplink,
    required this.updatedAt,
  });

  /// Parse ten type mot cach an toan: neu backend tra ve type khong khop enum
  /// thi tra ve null thay vi nem ArgumentError (tranh lam vo toan bo ket qua).
  static SearchResultType? parseType(String? name) {
    final key = (name ?? '').trim();
    for (final value in SearchResultType.values) {
      if (value.name == key) {
        return value;
      }
    }
    return null;
  }

  factory GlobalSearchItem.fromJson(Map<String, dynamic> json) {
    return GlobalSearchItem(
      id: (json['id'] ?? 0) as int,
      type: parseType((json['type'] ?? '').toString()) ??
          SearchResultType.document,
      title: (json['title'] ?? '') as String,
      snippet: (json['snippet'] ?? '') as String,
      deeplink: (json['deeplink'] ?? '') as String,
      updatedAt: DateTime.tryParse((json['updated_at'] ?? '').toString()) ??
          DateTime.fromMillisecondsSinceEpoch(0),
    );
  }
}

class GlobalSearchSection {
  final SearchResultType type;
  final List<GlobalSearchItem> items;

  const GlobalSearchSection({
    required this.type,
    required this.items,
  });
}

class GlobalSearchResults {
  final Map<SearchResultType, List<GlobalSearchItem>> bySection;
  final int tookMs;

  const GlobalSearchResults({
    required this.bySection,
    required this.tookMs,
  });

  factory GlobalSearchResults.fromJson(Map<String, dynamic> json) {
    final rawResults = Map<String, dynamic>.from(
      (json['results'] as Map?) ?? const {},
    );
    final bySection = <SearchResultType, List<GlobalSearchItem>>{};
    for (final entry in rawResults.entries) {
      final type = GlobalSearchItem.parseType(entry.key);
      if (type == null) {
        // Bo qua section co type khong xac dinh thay vi nem loi.
        continue;
      }
      final items = ((entry.value as List?) ?? const [])
          .map(
            (item) =>
                GlobalSearchItem.fromJson(Map<String, dynamic>.from(item as Map)),
          )
          .toList();
      bySection[type] = items;
    }
    return GlobalSearchResults(
      bySection: bySection,
      tookMs: (json['took_ms'] ?? 0) as int,
    );
  }

  List<GlobalSearchSection> get sections {
    return SearchResultType.values
        .where(bySection.containsKey)
        .map(
          (type) => GlobalSearchSection(
            type: type,
            items: bySection[type] ?? const [],
          ),
        )
        .toList();
  }

  List<GlobalSearchItem> flatten() {
    return sections.expand((section) => section.items).toList();
  }

  bool get isEmpty => flatten().isEmpty;
}
