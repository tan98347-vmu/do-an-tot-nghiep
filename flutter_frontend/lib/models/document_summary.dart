import 'document.dart';

class DocumentSummaryFacetOption {
  final String value;
  final String label;

  const DocumentSummaryFacetOption({
    required this.value,
    required this.label,
  });

  factory DocumentSummaryFacetOption.fromJson(Map<String, dynamic> json) {
    return DocumentSummaryFacetOption(
      value: json['value']?.toString() ?? '',
      label: json['label']?.toString() ?? '',
    );
  }
}

class DocumentSummaryNamedFacetOption {
  final int id;
  final String label;

  const DocumentSummaryNamedFacetOption({
    required this.id,
    required this.label,
  });

  factory DocumentSummaryNamedFacetOption.fromJson(Map<String, dynamic> json) {
    return DocumentSummaryNamedFacetOption(
      id: json['id'] as int? ?? 0,
      label: json['label']?.toString() ?? '',
    );
  }
}

class DocumentSummaryFacets {
  final List<DocumentSummaryFacetOption> scopes;
  final List<DocumentSummaryFacetOption> statuses;
  final List<DocumentSummaryFacetOption> visibilities;
  final List<DocumentSummaryFacetOption> shareStatuses;
  final List<DocumentSummaryFacetOption> sourceTypes;
  final List<DocumentSummaryFacetOption> signingStatuses;
  final List<DocumentSummaryNamedFacetOption> categories;
  final List<DocumentSummaryNamedFacetOption> groups;
  final List<String> tags;

  const DocumentSummaryFacets({
    this.scopes = const [],
    this.statuses = const [],
    this.visibilities = const [],
    this.shareStatuses = const [],
    this.sourceTypes = const [],
    this.signingStatuses = const [],
    this.categories = const [],
    this.groups = const [],
    this.tags = const [],
  });

  factory DocumentSummaryFacets.fromJson(Map<String, dynamic> json) {
    List<DocumentSummaryFacetOption> parseFacetList(String key) {
      return ((json[key] as List?) ?? const [])
          .map(
            (item) => DocumentSummaryFacetOption.fromJson(
              Map<String, dynamic>.from(item as Map),
            ),
          )
          .toList();
    }

    List<DocumentSummaryNamedFacetOption> parseNamedFacetList(String key) {
      return ((json[key] as List?) ?? const [])
          .map(
            (item) => DocumentSummaryNamedFacetOption.fromJson(
              Map<String, dynamic>.from(item as Map),
            ),
          )
          .toList();
    }

    return DocumentSummaryFacets(
      scopes: parseFacetList('scopes'),
      statuses: parseFacetList('statuses'),
      visibilities: parseFacetList('visibilities'),
      shareStatuses: parseFacetList('share_statuses'),
      sourceTypes: parseFacetList('source_types'),
      signingStatuses: parseFacetList('signing_statuses'),
      categories: parseNamedFacetList('categories'),
      groups: parseNamedFacetList('groups'),
      tags: ((json['tags'] as List?) ?? const [])
          .map((item) => item.toString().trim())
          .where((item) => item.isNotEmpty)
          .toList(),
    );
  }
}

class DocumentSummaryDiscoveryResult {
  final List<Document> items;
  final int totalCount;
  final int limit;
  final int offset;
  final bool hasMore;
  final String scope;
  final DocumentSummaryFacets facets;

  const DocumentSummaryDiscoveryResult({
    required this.items,
    required this.totalCount,
    required this.limit,
    required this.offset,
    required this.hasMore,
    required this.scope,
    required this.facets,
  });

  factory DocumentSummaryDiscoveryResult.fromJson(Map<String, dynamic> json) {
    return DocumentSummaryDiscoveryResult(
      items: ((json['items'] as List?) ?? const [])
          .map(
            (item) => Document.fromJson(
              Map<String, dynamic>.from(item as Map),
            ),
          )
          .toList(),
      totalCount: json['total_count'] as int? ?? 0,
      limit: json['limit'] as int? ?? 24,
      offset: json['offset'] as int? ?? 0,
      hasMore: json['has_more'] as bool? ?? false,
      scope: json['scope']?.toString() ?? 'all',
      facets: DocumentSummaryFacets.fromJson(
        Map<String, dynamic>.from((json['facets'] as Map?) ?? const {}),
      ),
    );
  }
}

class DocumentSummarySuggestion {
  final String type;
  final int? documentId;
  final String value;
  final String label;
  final String caption;
  final String matchedField;

  const DocumentSummarySuggestion({
    required this.type,
    required this.value,
    required this.label,
    required this.caption,
    required this.matchedField,
    this.documentId,
  });

  factory DocumentSummarySuggestion.fromJson(Map<String, dynamic> json) {
    return DocumentSummarySuggestion(
      type: json['type']?.toString() ?? 'document',
      documentId: json['document_id'] as int?,
      value: json['value']?.toString() ?? '',
      label: json['label']?.toString() ?? '',
      caption: json['caption']?.toString() ?? '',
      matchedField: json['matched_field']?.toString() ?? '',
    );
  }
}

class DocumentSummaryOptions {
  final String length;
  final String language;
  final String style;

  const DocumentSummaryOptions({
    this.length = 'standard',
    this.language = 'source',
    this.style = 'formal',
  });

  DocumentSummaryOptions copyWith({
    String? length,
    String? language,
    String? style,
  }) {
    return DocumentSummaryOptions(
      length: length ?? this.length,
      language: language ?? this.language,
      style: style ?? this.style,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'length': length,
      'language': language,
      'style': style,
    };
  }

  factory DocumentSummaryOptions.fromJson(Map<String, dynamic> json) {
    return DocumentSummaryOptions(
      length: json['length']?.toString() ?? 'standard',
      language: json['language']?.toString() ?? 'source',
      style: json['style']?.toString() ?? 'formal',
    );
  }

  @override
  bool operator ==(Object other) {
    return other is DocumentSummaryOptions &&
        other.length == length &&
        other.language == language &&
        other.style == style;
  }

  @override
  int get hashCode => Object.hash(length, language, style);
}

class DocumentSummaryPreviewSegment {
  final String type;
  final String label;
  final String preview;
  final String? trust;
  final bool masked;

  const DocumentSummaryPreviewSegment({
    required this.type,
    required this.label,
    required this.preview,
    this.trust,
    this.masked = false,
  });

  factory DocumentSummaryPreviewSegment.fromJson(Map<String, dynamic> json) {
    return DocumentSummaryPreviewSegment(
      type: json['type']?.toString() ?? 'unknown',
      label: json['label']?.toString() ?? '',
      preview: json['preview']?.toString() ?? '',
      trust: json['trust']?.toString(),
      masked: json['masked'] == true,
    );
  }
}

class DocumentSummaryPromptPreview {
  final String previewToken;
  final DocumentSummaryOptions options;
  final String summaryRevision;
  final String sourceKind;
  final int sourceLength;
  final int chunkCount;
  final double guardScore;
  final List<String> guardFlags;
  final List<String> guardModifications;
  final List<DocumentSummaryPreviewSegment> systemSegments;

  const DocumentSummaryPromptPreview({
    required this.previewToken,
    required this.options,
    required this.summaryRevision,
    required this.sourceKind,
    required this.sourceLength,
    required this.chunkCount,
    required this.guardScore,
    required this.guardFlags,
    required this.guardModifications,
    required this.systemSegments,
  });

  factory DocumentSummaryPromptPreview.fromJson(Map<String, dynamic> json) {
    final preview =
        Map<String, dynamic>.from((json['preview'] as Map?) ?? const {});
    final sanitizeReport = Map<String, dynamic>.from(
      (preview['sanitize_report'] as Map?) ?? const {},
    );
    return DocumentSummaryPromptPreview(
      previewToken: json['preview_token']?.toString() ?? '',
      options: DocumentSummaryOptions.fromJson(
        Map<String, dynamic>.from((json['options'] as Map?) ?? const {}),
      ),
      summaryRevision: json['summary_revision']?.toString() ?? '',
      sourceKind: json['source_kind']?.toString() ?? '',
      sourceLength: json['source_length'] as int? ?? 0,
      chunkCount: json['chunk_count'] as int? ?? 0,
      guardScore: (sanitizeReport['score'] as num?)?.toDouble() ?? 0,
      guardFlags: ((sanitizeReport['flags'] as List?) ?? const [])
          .map((item) => item.toString())
          .toList(),
      guardModifications:
          ((sanitizeReport['modifications'] as List?) ?? const [])
              .map((item) => item.toString())
              .toList(),
      systemSegments: ((preview['system_segments'] as List?) ?? const [])
          .map(
            (item) => DocumentSummaryPreviewSegment.fromJson(
              Map<String, dynamic>.from(item as Map),
            ),
          )
          .toList(),
    );
  }
}

class DocumentSummaryOutput {
  final String summary;
  final String summaryRevision;
  final String sourceKind;
  final int sourceLength;
  final int chunkCount;
  final DocumentSummaryOptions appliedOptions;
  final int? selectedPromptId;
  final String? selectedPromptTitle;
  final double? guardScore;
  final List<String> guardFlags;
  final List<String> guardModifications;

  const DocumentSummaryOutput({
    required this.summary,
    required this.summaryRevision,
    required this.sourceKind,
    required this.sourceLength,
    required this.chunkCount,
    required this.appliedOptions,
    this.selectedPromptId,
    this.selectedPromptTitle,
    this.guardScore,
    this.guardFlags = const [],
    this.guardModifications = const [],
  });

  factory DocumentSummaryOutput.fromJson(Map<String, dynamic> json) {
    final guardReport = Map<String, dynamic>.from(
      (json['guard_report'] as Map?) ?? const {},
    );
    return DocumentSummaryOutput(
      summary: json['summary']?.toString() ?? '',
      summaryRevision: json['summary_revision']?.toString() ?? '',
      sourceKind: json['source_kind']?.toString() ?? '',
      sourceLength: json['source_length'] as int? ?? 0,
      chunkCount: json['chunk_count'] as int? ?? 0,
      appliedOptions: DocumentSummaryOptions.fromJson(
        Map<String, dynamic>.from(
            (json['applied_options'] as Map?) ?? const {}),
      ),
      selectedPromptId: (json['selected_prompt'] as Map?)?['id'] as int?,
      selectedPromptTitle:
          (json['selected_prompt'] as Map?)?['title']?.toString(),
      guardScore: guardReport.isEmpty
          ? null
          : (guardReport['score'] as num?)?.toDouble(),
      guardFlags: ((guardReport['flags'] as List?) ?? const [])
          .map((item) => item.toString())
          .toList(),
      guardModifications: ((guardReport['modifications'] as List?) ?? const [])
          .map((item) => item.toString())
          .toList(),
    );
  }
}
