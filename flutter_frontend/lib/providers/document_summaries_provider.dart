import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../core/api_client.dart';
import '../core/download_helper.dart';
import '../models/document_summary.dart';
import '../models/prompt.dart';

class DocumentSummaryDiscoveryParams {
  final String q;
  final String scope;
  final String status;
  final String visibility;
  final String shareStatus;
  final String signingStatus;
  final String sourceType;
  final String tag;
  final String docNumber;
  final int? categoryId;
  final int? groupId;
  final bool editableOnly;
  final int limit;
  final int offset;

  const DocumentSummaryDiscoveryParams({
    this.q = '',
    this.scope = 'all',
    this.status = '',
    this.visibility = '',
    this.shareStatus = '',
    this.signingStatus = '',
    this.sourceType = '',
    this.tag = '',
    this.docNumber = '',
    this.categoryId,
    this.groupId,
    this.editableOnly = false,
    this.limit = 24,
    this.offset = 0,
  });

  DocumentSummaryDiscoveryParams copyWith({
    String? q,
    String? scope,
    String? status,
    String? visibility,
    String? shareStatus,
    String? signingStatus,
    String? sourceType,
    String? tag,
    String? docNumber,
    int? categoryId,
    bool clearCategoryId = false,
    int? groupId,
    bool clearGroupId = false,
    bool? editableOnly,
    int? limit,
    int? offset,
  }) {
    return DocumentSummaryDiscoveryParams(
      q: q ?? this.q,
      scope: scope ?? this.scope,
      status: status ?? this.status,
      visibility: visibility ?? this.visibility,
      shareStatus: shareStatus ?? this.shareStatus,
      signingStatus: signingStatus ?? this.signingStatus,
      sourceType: sourceType ?? this.sourceType,
      tag: tag ?? this.tag,
      docNumber: docNumber ?? this.docNumber,
      categoryId: clearCategoryId ? null : (categoryId ?? this.categoryId),
      groupId: clearGroupId ? null : (groupId ?? this.groupId),
      editableOnly: editableOnly ?? this.editableOnly,
      limit: limit ?? this.limit,
      offset: offset ?? this.offset,
    );
  }

  Map<String, dynamic> toQueryParameters() {
    final params = <String, dynamic>{
      'scope': scope,
      'limit': '$limit',
      'offset': '$offset',
    };
    if (q.trim().isNotEmpty) params['q'] = q.trim();
    if (status.isNotEmpty) params['status'] = status;
    if (visibility.isNotEmpty) params['visibility'] = visibility;
    if (shareStatus.isNotEmpty) params['share_status'] = shareStatus;
    if (signingStatus.isNotEmpty) params['signing_status'] = signingStatus;
    if (sourceType.isNotEmpty) params['source_type'] = sourceType;
    if (tag.trim().isNotEmpty) params['tag'] = tag.trim();
    if (docNumber.trim().isNotEmpty) params['doc_number'] = docNumber.trim();
    if (categoryId != null) params['category_id'] = '$categoryId';
    if (groupId != null) params['group_id'] = '$groupId';
    if (editableOnly) params['editable_only'] = '1';
    return params;
  }

  Map<String, String> toRouteQueryParameters() {
    return toQueryParameters().map(
      (key, value) => MapEntry(key, value.toString()),
    );
  }

  factory DocumentSummaryDiscoveryParams.fromRouteQuery(
    Map<String, String> query,
  ) {
    int? parseInt(String key) {
      final value = query[key];
      if (value == null || value.trim().isEmpty) {
        return null;
      }
      return int.tryParse(value.trim());
    }

    return DocumentSummaryDiscoveryParams(
      q: query['q']?.trim() ?? '',
      scope: query['scope']?.trim().isNotEmpty == true
          ? query['scope']!.trim()
          : 'all',
      status: query['status']?.trim() ?? '',
      visibility: query['visibility']?.trim() ?? '',
      shareStatus: query['share_status']?.trim() ?? '',
      signingStatus: query['signing_status']?.trim() ?? '',
      sourceType: query['source_type']?.trim() ?? '',
      tag: query['tag']?.trim() ?? '',
      docNumber: query['doc_number']?.trim() ?? '',
      categoryId: parseInt('category_id'),
      groupId: parseInt('group_id'),
      editableOnly: (query['editable_only'] ?? '').trim() == '1',
      limit: int.tryParse(query['limit'] ?? '') ?? 24,
      offset: int.tryParse(query['offset'] ?? '') ?? 0,
    );
  }

  @override
  bool operator ==(Object other) {
    return other is DocumentSummaryDiscoveryParams &&
        other.q == q &&
        other.scope == scope &&
        other.status == status &&
        other.visibility == visibility &&
        other.shareStatus == shareStatus &&
        other.signingStatus == signingStatus &&
        other.sourceType == sourceType &&
        other.tag == tag &&
        other.docNumber == docNumber &&
        other.categoryId == categoryId &&
        other.groupId == groupId &&
        other.editableOnly == editableOnly &&
        other.limit == limit &&
        other.offset == offset;
  }

  @override
  int get hashCode {
    return Object.hash(
      q,
      scope,
      status,
      visibility,
      shareStatus,
      signingStatus,
      sourceType,
      tag,
      docNumber,
      categoryId,
      groupId,
      editableOnly,
      limit,
      offset,
    );
  }
}

class DocumentSummaryApi {
  final Dio _dio;

  DocumentSummaryApi(this._dio);

  Future<DocumentSummaryDiscoveryResult> fetchDiscovery(
    DocumentSummaryDiscoveryParams params,
  ) async {
    final response = await _dio.get(
      'document-summaries/',
      queryParameters: params.toQueryParameters(),
    );
    return DocumentSummaryDiscoveryResult.fromJson(
      Map<String, dynamic>.from(response.data as Map),
    );
  }

  Future<List<DocumentSummarySuggestion>> fetchSuggestions({
    required String query,
    required DocumentSummaryDiscoveryParams params,
  }) async {
    if (query.trim().length < 2) {
      return const [];
    }
    final response = await _dio.get(
      'document-summaries/suggest/',
      queryParameters: {
        ...params.toQueryParameters(),
        'q': query.trim(),
        'offset': '0',
        'limit': '12',
      },
    );
    return ((response.data['items'] as List?) ?? const [])
        .map(
          (item) => DocumentSummarySuggestion.fromJson(
            Map<String, dynamic>.from(item as Map),
          ),
        )
        .toList();
  }

  Future<DocumentSummaryPromptPreview> preview({
    required int documentId,
    required DocumentSummaryOptions options,
    required String userExtraRules,
    int? promptId,
  }) async {
    final response = await _dio.post(
      'document-summaries/$documentId/preview/',
      data: {
        'options': options.toJson(),
        'user_extra_rules': userExtraRules.trim(),
        if (promptId != null) 'prompt_id': promptId,
      },
    );
    return DocumentSummaryPromptPreview.fromJson(
      Map<String, dynamic>.from(response.data as Map),
    );
  }

  Future<DocumentSummaryOutput> generate({
    required int documentId,
    required DocumentSummaryOptions options,
    required String userExtraRules,
    String? previewToken,
    int? promptId,
  }) async {
    final response = await _dio.post(
      'document-summaries/$documentId/generate/',
      data: {
        'options': options.toJson(),
        'user_extra_rules': userExtraRules.trim(),
        if ((previewToken ?? '').trim().isNotEmpty)
          'preview_token': previewToken!.trim(),
        if (promptId != null) 'prompt_id': promptId,
      },
      options: ApiClient.ollamaOptions(),
    );
    return DocumentSummaryOutput.fromJson(
      Map<String, dynamic>.from(response.data as Map),
    );
  }

  Future<List<Prompt>> searchPrompts({
    required String query,
    required String scope,
  }) async {
    final response = await _dio.get(
      'prompts/',
      queryParameters: {
        if (query.trim().isNotEmpty) 'q': query.trim(),
      },
    );
    return ((response.data as List?) ?? const [])
        .map(
          (item) => Prompt.fromJson(
            Map<String, dynamic>.from(item as Map),
          ),
        )
        .where((prompt) => _matchesPromptScope(prompt, scope))
        .take(20)
        .toList();
  }

  Future<void> downloadSummary(
    int documentId, {
    required String format,
  }) async {
    final normalizedFormat = format.trim().toLowerCase();
    final response = await _dio.get<List<int>>(
      'document-summaries/$documentId/download/',
      queryParameters: {'format': normalizedFormat},
      options: Options(responseType: ResponseType.bytes),
    );

    final bytes = response.data ?? const <int>[];
    final filename = _resolveFilename(
      response.headers.value('content-disposition'),
      fallback: 'summary.$normalizedFormat',
    );
    final mime = response.headers.value('content-type') ??
        (normalizedFormat == 'docx'
            ? 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
            : 'text/markdown; charset=utf-8');
    downloadBlob(bytes, filename, mime);
  }
}

final documentSummaryApiProvider = Provider<DocumentSummaryApi>((ref) {
  return DocumentSummaryApi(ApiClient().dio);
});

final documentSummaryDiscoveryProvider = FutureProvider.autoDispose
    .family<DocumentSummaryDiscoveryResult, DocumentSummaryDiscoveryParams>(
  (ref, params) async {
    return ref.watch(documentSummaryApiProvider).fetchDiscovery(params);
  },
);

bool _matchesPromptScope(Prompt prompt, String scope) {
  final rawTags = (prompt.tags ?? '').trim().toLowerCase();
  if (rawTags.isEmpty) {
    return true;
  }
  final tokens = rawTags
      .replaceAll(';', ',')
      .split(',')
      .map((item) => item.trim())
      .where((item) => item.isNotEmpty)
      .toSet();
  if (tokens.isEmpty) {
    return true;
  }
  return tokens.contains(scope) || tokens.contains('scope:$scope');
}

String _resolveFilename(String? contentDisposition, {required String fallback}) {
  final header = (contentDisposition ?? '').trim();
  if (header.isEmpty) {
    return fallback;
  }

  final utfMatch = RegExp(r"filename\*=UTF-8''([^;]+)", caseSensitive: false)
      .firstMatch(header);
  if (utfMatch != null) {
    return Uri.decodeComponent(utfMatch.group(1)!).trim();
  }

  final asciiMatch =
      RegExp(r'filename="([^"]+)"', caseSensitive: false).firstMatch(header);
  if (asciiMatch != null) {
    return asciiMatch.group(1)!.trim();
  }

  return fallback;
}
